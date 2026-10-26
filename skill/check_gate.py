#!/usr/bin/env python3
"""ship-gate: your own readiness check, on the PR-opening doorway.

Unit 4 made you write every file of pr-precheck, the tool that answers
one question about one branch: is this ready to submit? Unit 6 put a
latch on your posting doorway (the voice-guard: fire on the doorway
every time, stop quoting the exact reason, log every check). This
runner connects the two and adds the repo's own checks. Before any
pull request of yours goes out, the gate runs the checks YOUR manifest
names, in order, then YOUR pr-precheck in live mode on YOUR branch,
and blocks the ship quoting exactly what failed. Staff wrote the
wiring, never the judgment: every word a block quotes is the repo's
own check or your own rubric.

Two doorways, one contract:

  hook mode (no arguments): invoked by Claude Code as a PreToolUse hook
    with the tool-call JSON on stdin (see hooks-settings.json). Commands
    that do not open a pull request pass through untouched and cost
    nothing. A `gh pr create` runs the gate on the branch it would ship;
    its --title and --body-file are the draft the gate reads. A pass
    lets the command through; a block stops it (exit 2) with the reason
    quoted.

  manual mode (--branch [NAME]): the same gate on the current (or named)
    branch, for pull requests you will open in the browser and for dry
    runs at any branch state. --title and --body-file carry the draft.
    Exit 0 on pass, 2 on block.

A pass carries between the doorways: a manual PASS from the last 30
minutes on the identical package (same commit, same title, same body,
same manifest, matched by the fingerprints the log records) is honored
at the hook doorway, which skips the repo checks and the rubric pass;
the manual doorway is the same gate, so a fresh pass is not re-rolled.
Anything changed, and the gate runs fresh. Every setup stop still
stops: a broken manifest, tool, scope, or voice guide fails closed on
both doorways, honored pass or not.

Two latches, one door: since unit 6 the voice-guard also fires on
`gh pr create`. The guard owns the words (the PR body against your
voice guide); the gate owns readiness (the branch against your manifest
and your rubric). Each stops quoting its own reason, so a body-less
`gh pr create` gets two stops, and the one to read for readiness is
this one.

Fail closed, always with the route named: no manifest, or a manifest
still a template; a pr-precheck that is missing or still templates (its
own unit-4 refusal rule, reported honestly, with the unit-4-debt route
named); a scope still pointing at the sandbox; a voice guide with no
canonical home. There is no override flag. The escape valves are all
legitimate and all leave a trail: fix the thing named, patch your own
rubric, or record a dated exclusion in the manifest.

What the gate learned running the manifest travels with the diff: the
pr-precheck prompt carries the checks that ran with their outcomes and
the exclusions with their dates and reasons, so your rubric can read
what was green and what you excluded without you restating it. Manifest
commands run in a fresh shell at the clone root (never your activated
terminal), so a row is written in the form that runs cold.

Every run, both doorways, appends a dated block to gate-log.md next to
this file: timestamp, repo, branch, manifest checks with outcomes,
verdict, quoted reasons. A passing run also records the package it
passed (the commit sha and content fingerprints of the title, body,
and manifest), which is how the hook doorway recognizes a fresh manual
pass. That log is your gate transcript, Assignment 5's evidence that
the gate was on the door.

The gate is a live-mode-only seam: nothing invokes it in eval mode, and
it never reads or changes pr-precheck's eval mode or the unit-1 and
unit-4 harness interfaces. It runs the commands in your manifest on
your machine exactly as you wrote them, the same as typing them.

Honesty note: the gate reads the commands it can see. Opening a pull
request from the browser without the manual doorway, or from a bare
terminal, walks around it, exactly like not running a skill. The
honored pass trusts your own log the same way. It is your own judgment
with a latch on the door, not a security system.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path

# (os is used for the environment the model call inherits and for
# expanding a pointer-line path; nothing here reads HOME to find tools.)

# The course model pin: every stated behavior was built and checked on
# Sonnet. Do not add a model flag.
MODEL = "sonnet"

# Paths resolve from where this file is installed (~/.claude/ship-gate/,
# where install.py puts it), the same convention as the unit-6 guard:
# the runner's home is the .claude directory it sits in.
GATE_DIR = Path(__file__).resolve().parent
CLAUDE_DIR = GATE_DIR.parent
LOG_PATH = GATE_DIR / "gate-log.md"
TEMPLATE_PATH = GATE_DIR / "gate-manifest-template.md"
TOOL_DIR = CLAUDE_DIR / "skills" / "pr-precheck"
CANONICAL_GUIDE = CLAUDE_DIR / "voice-guard" / "voice-guide.md"
MANIFEST_NAME = "ship-manifest.md"

CHECK_TIMEOUT_S = 1500        # per manifest check
MODEL_TIMEOUT_S = 900         # the one rubric pass
FRESH_PASS_WINDOW_S = 30 * 60  # a manual PASS carries to the hook this long
GH_TIMEOUT_S = 45             # issue-thread fetch
PARENT_TIMEOUT_S = 15         # asking GitHub what a fork was forked from
MAX_DIFF_CHARS = 120_000
MAX_DOC_CHARS = 20_000
MAX_ISSUE_CHARS = 30_000
TAIL_LINES = 20

# The contract's fixed layout (CONTRACT.md): file label -> path.
TOOL_FILES = {
    "skill": "SKILL.md",
    "rubric": "rubric.md",
    "procedure": "procedure.md",
    "evidence": "references/evidence-guide.md",
}

WEEK4_INSTALL = ("copy the whole skill/ folder from your Unit 4 "
                 "materials to ~/.claude/skills/pr-precheck/ and write "
                 "its four files")
WEEK6_LINK = ("mv ~/.claude/skills/repro-check/voice-guide.md "
              "~/.claude/voice-guard/voice-guide.md  then  "
              "ln -sf ~/.claude/voice-guard/voice-guide.md "
              "~/.claude/skills/pr-precheck/voice-guide.md  "
              "(Unit 6 materials, INSTALL.md step 3)")


class GateStop(Exception):
    """A block. kind is one of setup / refusal / block; message names
    the route out."""

    def __init__(self, kind: str, message: str):
        super().__init__(message)
        self.kind = kind
        self.message = message


class Report:
    def __init__(self, mode: str):
        self.mode = mode
        self.repo = "unknown"
        self.branch = "unknown"
        self.base = "unknown"
        self.checks: list[tuple[str, str, str]] = []   # name, cmd, outcome
        self.precheck: list[dict] = []
        self.summary = ""
        self.verdict = ""
        self.reasons: list[str] = []
        self.package: dict | None = None               # the fingerprints


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def sh(args: list[str], cwd=None, timeout: int = 60):
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True,
                          timeout=timeout)


def git(root, *args, ok: bool = False):
    """Run git; return stdout stripped. With ok=True return None on
    failure instead of raising."""
    try:
        proc = sh(["git", *args], cwd=root)
    except (OSError, subprocess.TimeoutExpired) as e:
        if ok:
            return None
        raise GateStop("setup", f"git failed ({e}); is git installed?")
    if proc.returncode != 0:
        if ok:
            return None
        raise GateStop("setup", f"git {' '.join(args)} failed: "
                                f"{proc.stderr.strip()[:300]}")
    return proc.stdout.strip()


def tail(text: str, n: int = TAIL_LINES) -> str:
    lines = text.rstrip().splitlines()
    return "\n".join(lines[-n:]) if lines else "(no output)"


def clip(text: str, limit: int, label: str) -> str:
    if len(text) <= limit:
        return text
    return (text[:limit] + f"\n\n[... {label} truncated by the gate at "
            f"{limit} characters; the rubric judges what is shown ...]")


def strip_comments(text: str) -> str:
    return re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)


def read_first(root: Path, candidates: list[str]):
    for rel in candidates:
        p = root / rel
        if p.is_file():
            try:
                return rel, p.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
    return None, None


# ---------------------------------------------------------------------------
# Install state, manifest, tool, scope, voice guide
# ---------------------------------------------------------------------------

def ensure_installed() -> None:
    if GATE_DIR.name != "ship-gate" or CLAUDE_DIR.name != ".claude":
        raise GateStop("setup",
                       "the ship-gate is not installed: this copy of "
                       f"check_gate.py sits in {GATE_DIR}, not in "
                       "~/.claude/ship-gate/, so its paths cannot reach "
                       "your tools. From your unpacked Unit 7 materials "
                       "run `python3 skill/install.py` (INSTALL.md "
                       "explains every step it performs), then run the "
                       "installed copy: python3 "
                       "~/.claude/ship-gate/check_gate.py --branch")


def repo_root(cwd: Path) -> Path:
    top = git(cwd, "rev-parse", "--show-toplevel", ok=True)
    if not top:
        raise GateStop("setup",
                       f"{cwd} is not inside a git clone. Run the gate "
                       "from the clone of the repository your branch "
                       "lives in; the manifest sits at its root.")
    return Path(top)


def _table_rows(section: str) -> list[list[str]]:
    rows = []
    for line in section.splitlines():
        s = line.strip()
        if not s.startswith("|"):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if all(re.fullmatch(r":?-{3,}:?", c) for c in cells if c):
            continue                                    # separator row
        rows.append(cells)
    return rows[1:] if rows else []                     # drop the header


def _sections(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    current = None
    for line in text.splitlines():
        m = re.match(r"^##\s+(.+?)\s*$", line)
        if m:
            current = m.group(1).lower()
            out[current] = ""
            continue
        if current is not None:
            out[current] += line + "\n"
    return out


def _clean_cmd(cell: str) -> str:
    return cell.strip().strip("`").strip()


def load_manifest(root: Path) -> dict:
    p = root / MANIFEST_NAME
    if not p.is_file():
        raise GateStop("setup",
                       f"no {MANIFEST_NAME} at {root}. Create it from the "
                       "template and keep it out of your diff:\n"
                       f"  cp {TEMPLATE_PATH} {MANIFEST_NAME}\n"
                       f"  echo {MANIFEST_NAME} >> .git/info/exclude\n"
                       "then fill it: the repo's own checks, one row each, "
                       "with the source line each came from.")
    raw = p.read_text(encoding="utf-8", errors="replace")
    text = strip_comments(raw)
    m = re.search(r"^#\s*Ship manifest:\s*(.+?)\s*$", text, re.MULTILINE)
    repo = m.group(1) if m else ""
    header_placeholder = (not repo or "<" in repo
                          or "owner/repo" in repo.lower())

    sections = _sections(text)
    must_key = next((k for k in sections if k.startswith("must pass")), None)
    excl_key = next((k for k in sections if k.startswith("excluded")), None)
    must_rows = _table_rows(sections[must_key]) if must_key else []
    excl_rows = _table_rows(sections[excl_key]) if excl_key else []

    checks: list[tuple[str, str, str]] = []
    for cells in must_rows:
        cells += [""] * (3 - len(cells))
        name, cmd, source = cells[0], _clean_cmd(cells[1]), cells[2]
        if not name and not cmd and not source:
            continue
        if not cmd:
            continue
        if not source:
            raise GateStop("setup",
                           f"{MANIFEST_NAME}: the check `{name or cmd}` "
                           "has a command but no source line. Every "
                           "check names where it came from (the repo's "
                           "CONTRIBUTING.md, its CI config, your "
                           "CLAUDE.local.md's build-and-test section); "
                           "that is the manifest's discipline, and a "
                           "check with no source is a guess.")
        if cmd.lower() == "none":
            continue
        checks.append((name or cmd, cmd, source))

    filled_rows = [c for c in must_rows if any(c)]
    if header_placeholder or not filled_rows:
        raise GateStop("setup",
                       f"{MANIFEST_NAME} is still the template: "
                       + ("the repo line still reads as a placeholder"
                          if header_placeholder else
                          "no must-pass check has a command yet")
                       + ". The manifest is your judgment about which "
                       "of the repo's OWN checks must pass before a "
                       "ship: mine them from CONTRIBUTING.md and the "
                       "Build and test commands section of your "
                       "CLAUDE.local.md, one row each with its source. "
                       "A repo whose docs name no checks gets one row "
                       "whose command is the word none, with the source "
                       "saying where you looked.")

    exclusions = []
    for cells in excl_rows:
        cells += [""] * (4 - len(cells))
        name, cmd, since, why = (cells[0], _clean_cmd(cells[1]),
                                 cells[2], cells[3])
        if not any((name, cmd, since, why)):
            continue
        if name.lower() == "none":
            continue
        if not since or not why:
            raise GateStop("setup",
                           f"{MANIFEST_NAME}: the exclusion `{name or cmd}`"
                           " needs both a date and the reason it does "
                           "not gate this ship. Silence is never an "
                           "option: an excluded check is a recorded "
                           "judgment, dated, or it is a hole.")
        exclusions.append((name or cmd, cmd, since, why))
    return {"repo": repo, "checks": checks, "exclusions": exclusions}


# Template detection, ported from the unit-4 harness so the gate and the
# harness agree on what "still a template" means.

def _strip_scaffolding(text: str) -> str:
    body = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    body = re.sub(r"\A---\n.*?\n---\n", "", body, flags=re.DOTALL)
    body = re.sub(r"^```.*?^```\s*$", "", body,
                  flags=re.DOTALL | re.MULTILINE)
    return body


def rubric_has_checks(text: str) -> bool:
    body = strip_comments(text)
    for line in body.splitlines():
        cells = [c.strip().lower()
                 for c in line.strip().strip("|").split("|")]
        if len(cells) >= 4 and cells[-1] in ("required", "preferred"):
            return True
    return False


def rubric_has_verdict_rule(text: str) -> bool:
    body = strip_comments(text)
    return any(line.strip() and not line.lstrip().startswith(("#", "|"))
               for line in body.splitlines())


def doc_has_content(text: str) -> bool:
    body = strip_comments(text)
    return any(line.strip() and not line.lstrip().startswith("#")
               for line in body.splitlines())


def frame_has_content(text: str) -> bool:
    body = _strip_scaffolding(text)
    return any(line.strip() and not line.lstrip().startswith("#")
               for line in body.splitlines())


def load_tool() -> dict[str, str]:
    if not TOOL_DIR.is_dir():
        raise GateStop("refusal",
                       f"your pr-precheck is not installed at {TOOL_DIR}. "
                       "The gate wraps YOUR unit-4 tool and nothing else, "
                       f"so there is nothing to run yet: {WEEK4_INSTALL}, "
                       "then run the gate again. Until then this is a "
                       "Module 1 item still open, and finishing it is "
                       "Assignment 5 working time.")
    texts: dict[str, str] = {}
    missing = []
    for label, rel in TOOL_FILES.items():
        p = TOOL_DIR / rel
        if not p.is_file():
            missing.append(rel)
            continue
        texts[label] = p.read_text(encoding="utf-8", errors="replace")
    if missing:
        raise GateStop("refusal",
                       "your pr-precheck is missing "
                       f"{', '.join(missing)} (CONTRACT.md's fixed layout). "
                       f"{WEEK4_INSTALL}; the gate cannot grade readiness "
                       "with part of the tool absent.")
    empty = []
    if not frame_has_content(texts["skill"]):
        empty.append("SKILL.md (the frame)")
    if not rubric_has_checks(texts["rubric"]):
        empty.append("rubric.md (no checks)")
    elif not rubric_has_verdict_rule(texts["rubric"]):
        empty.append("rubric.md (no verdict rule)")
    if not doc_has_content(texts["procedure"]):
        empty.append("procedure.md")
    if not doc_has_content(texts["evidence"]):
        empty.append("references/evidence-guide.md")
    if empty:
        raise GateStop("refusal",
                       "REFUSAL. Your pr-precheck still has template "
                       "files with no content of yours: "
                       f"{'; '.join(empty)}. The gate cannot grade "
                       "readiness with an empty tool, and that is your "
                       "tool's own unit-4 design telling the truth, not "
                       "the gate breaking. The sanctioned route is "
                       "finishing your own pr-precheck (your frame, your "
                       "rubric, your procedure, your evidence guide) as "
                       "Assignment 5 working time; TFs route this. Never "
                       "copy a master: the gate quotes your rubric, so "
                       "the rubric has to be yours.")
    return texts


def load_scope() -> str:
    p = TOOL_DIR / "scope.md"
    text = p.read_text(encoding="utf-8", errors="replace") if p.is_file() \
        else ""
    # A cohort fills the staff placeholder before the term starts, so the
    # brackets alone cannot tell a sandbox scope from a real-world one; the
    # sentence naming the classroom repo survives the fill and does.
    sandbox = ("PATH-REVIEW" in text or "<ORG>" in text
               or "the course's Path Review repository" in text)
    if not text.strip() or sandbox:
        raise GateStop("setup",
                       "pr-precheck's scope.md is "
                       + ("missing" if not text.strip() else
                          "still the unit-4 sandbox scope (its field of "
                          "view is the Path Review repo, not the wild)")
                       + ". Run the ship-gate install (`python3 "
                       "skill/install.py` from your Unit 7 materials); it "
                       "places the real-world scope over it and keeps "
                       "the sandbox copy beside it. The gate never edits "
                       "your tool's judgment files.")
    return text


_POINTER_RE = re.compile(r"lives at\s+(\S+?)(?:[;,\s]|$)")


def load_voice() -> tuple[str, str]:
    """Return (guide text, note). Resolves pr-precheck's voice-guide.md
    through the unit-6 symlink, its documented pointer-line fallback,
    or the canonical home directly; fails closed when the file is still
    the frozen unit-4 carry-over with no canonical home."""
    p = TOOL_DIR / "voice-guide.md"
    canonical = CANONICAL_GUIDE
    if p.is_symlink():
        target = p.resolve()
        if target.is_file():
            return (target.read_text(encoding="utf-8", errors="replace"),
                    f"read through the symlink at {p} -> {target}")
        raise GateStop("setup",
                       f"pr-precheck's voice-guide.md links to {target}, "
                       "which does not exist. Finish the unit-6 "
                       f"promotion: {WEEK6_LINK}.")
    if p.is_file():
        text = p.read_text(encoding="utf-8", errors="replace")
        m = _POINTER_RE.search(text)
        if m and len(strip_comments(text).strip().splitlines()) <= 3:
            target = Path(os.path.expanduser(m.group(1))).resolve()
            if target.is_file():
                return (target.read_text(encoding="utf-8",
                                         errors="replace"),
                        f"followed the pointer line in {p} to {target}")
            raise GateStop("setup",
                           f"pr-precheck's voice-guide.md points at "
                           f"{target}, which does not exist. Finish the "
                           f"unit-6 promotion: {WEEK6_LINK}.")
        if canonical.is_file():
            return (canonical.read_text(encoding="utf-8", errors="replace"),
                    f"read the canonical guide at {canonical}; your "
                    f"pr-precheck copy at {p} is not linked to it (the "
                    "unit-6 `ln -sf` line fixes that)")
        raise GateStop("setup",
                       "pr-precheck's voice-guide.md is still the frozen "
                       "unit-4 carry-over and no canonical guide exists "
                       f"at {canonical}. The gate reads the guide of "
                       "record, not a historical copy. Finish the unit-6 "
                       f"install step 3 first: {WEEK6_LINK}.")
    if canonical.is_file():
        return (canonical.read_text(encoding="utf-8", errors="replace"),
                f"read the canonical guide at {canonical}; pr-precheck "
                "has no voice-guide.md of its own (the unit-6 `ln -sf` "
                "line adds the link)")
    raise GateStop("setup",
                   "no voice guide anywhere: pr-precheck has no "
                   f"voice-guide.md and {canonical} does not exist. "
                   f"Finish the unit-6 install: {WEEK6_LINK}.")


# ---------------------------------------------------------------------------
# Branch, base, repo
# ---------------------------------------------------------------------------

def detect_base(root: Path, override) -> str:
    if override:
        if git(root, "rev-parse", "--verify", "--quiet", override,
               ok=True) is None:
            raise GateStop("setup", f"base branch {override} not found "
                                    f"in the clone at {root}.")
        return override
    for cand in ("main", "master"):
        if git(root, "rev-parse", "--verify", "--quiet",
               f"refs/heads/{cand}", ok=True) is not None:
            return cand
    ref = git(root, "symbolic-ref", "-q", "refs/remotes/origin/HEAD",
              ok=True)
    if ref and ref.startswith("refs/remotes/"):
        return ref[len("refs/remotes/"):]
    raise GateStop("setup",
                   "could not tell the base branch of the clone at "
                   f"{root} (no main or master, no origin HEAD). "
                   "Pass --base NAME.")


def resolve_branch(root: Path, wanted, base: str) -> str:
    if wanted in (None, "HEAD"):
        branch = git(root, "rev-parse", "--abbrev-ref", "HEAD")
        if branch == "HEAD":
            raise GateStop("setup",
                           "the clone is in detached HEAD state; check "
                           "out your branch (or name it with --branch "
                           "NAME) and run again.")
    else:
        branch = wanted
        if git(root, "rev-parse", "--verify", "--quiet", branch,
               ok=True) is None:
            raise GateStop("setup", f"branch {branch} not found in this "
                                    "clone.")
    if branch == base or branch == base.split("/", 1)[-1]:
        raise GateStop("block",
                       f"you are on {branch}, the base branch itself. "
                       "Nothing here is a pull request: check out your "
                       "fix branch and run again.")
    return branch


def fork_parent(repo: str) -> str | None:
    """The repo this one was forked from, or None (not a fork, or GitHub
    could not be asked)."""
    try:
        proc = sh(["gh", "api", f"repos/{repo}", "--jq",
                   ".parent.full_name // empty"], timeout=PARENT_TIMEOUT_S)
    except (OSError, subprocess.TimeoutExpired):
        return None
    name = proc.stdout.strip() if proc.returncode == 0 else ""
    return name if re.fullmatch(r"[\w.-]+/[\w.-]+", name) else None


def repo_name(root: Path, fallback: str) -> str:
    """The repo the pull request is for. Students clone their fork, so
    origin is usually the fork; its parent on GitHub is the repo whose
    issue the PR fixes."""
    for remote in ("upstream", "origin"):
        url = git(root, "remote", "get-url", remote, ok=True)
        if url:
            m = re.search(r"github\.com[:/]([^/\s]+/[^/\s]+?)(?:\.git)?/?$",
                          url)
            if m:
                name = m.group(1)
                if remote == "origin":
                    return fork_parent(name) or name
                return name
    return fallback or root.name


# ---------------------------------------------------------------------------
# The repo's own checks
# ---------------------------------------------------------------------------

def run_checks(root: Path, checks: list[tuple[str, str, str]],
               report: Report) -> None:
    n = len(checks)
    if not n:
        print("ship-gate: the manifest names no repo checks (the `none` "
              "row); on to your pr-precheck.", file=sys.stderr)
        return
    for i, (name, cmd, source) in enumerate(checks, 1):
        print(f"ship-gate: repo check {i}/{n} `{name}`: {cmd}",
              file=sys.stderr, flush=True)
        t0 = time.monotonic()
        try:
            proc = subprocess.run(cmd, shell=True, cwd=root,
                                  capture_output=True, text=True,
                                  timeout=CHECK_TIMEOUT_S)
        except subprocess.TimeoutExpired:
            outcome = f"timed out after {CHECK_TIMEOUT_S}s"
            report.checks.append((name, cmd, outcome))
            raise GateStop("block",
                           f"the repo's own check `{name}` {outcome}: "
                           f"`{cmd}`. Source of this check: {source}. A "
                           "check that cannot finish here is a judgment "
                           "call for your manifest: scope it down, or "
                           "record a dated exclusion with the reason.")
        secs = time.monotonic() - t0
        if proc.returncode != 0:
            out = tail((proc.stdout or "") + "\n" + (proc.stderr or ""))
            report.checks.append((name, cmd,
                                  f"FAILED (exit {proc.returncode}, "
                                  f"{secs:.0f}s)"))
            hint = ""
            if proc.returncode == 127 or "command not found" in out:
                hint = (" Exit 127 means the command was not found in a "
                        "fresh shell at the clone root: the gate never "
                        "runs in your activated terminal, on either "
                        "doorway, so write the row in the form that runs "
                        "cold (`uv run pytest`, `.venv/bin/ruff check .`, "
                        "`npx eslint .`), still mined from the repo's "
                        "setup, still sourced.")
            elif re.search(r"(?i)cannot find module|not found|"
                           r"no module named|command .* does not exist",
                           out):
                hint = (" A module-not-found error from a package runner "
                        "usually means the repo's setup step has not run "
                        "in this clone (`npm install`, `uv sync`, `pip "
                        "install -e .[dev]`, whichever its guide names). "
                        "That setup step belongs in your manifest as its "
                        "own first must-pass row, sourced to the same "
                        "guide.")
            raise GateStop("block",
                           f"the repo's own check `{name}` failed: `{cmd}` "
                           f"exited {proc.returncode}. Output tail:\n{out}\n"
                           f"Source of this check: {source}. Fix what it "
                           "names; if you judge it must not gate this "
                           "ship (red on main for reasons your PR never "
                           "touches, a toolchain or service you lack "
                           "here, a check that rewrites tracked files), "
                           f"record a dated exclusion in {MANIFEST_NAME} "
                           "instead of deleting the row." + hint)
        report.checks.append((name, cmd, f"ok ({secs:.0f}s)"))


# ---------------------------------------------------------------------------
# Live inputs for pr-precheck
# ---------------------------------------------------------------------------

_ISSUE_URL_RE = re.compile(
    r"https://github\.com/[\w.-]+/[\w.-]+/issues/\d+")
_ISSUE_REF_RE = re.compile(r"(?i)\b(?:fixes|closes|resolves)\s+#(\d+)")

PR_TEMPLATE_PATHS = [
    ".github/PULL_REQUEST_TEMPLATE.md", ".github/pull_request_template.md",
    "PULL_REQUEST_TEMPLATE.md", "pull_request_template.md",
    "docs/PULL_REQUEST_TEMPLATE.md", "docs/pull_request_template.md",
]
CONTRIBUTING_PATHS = [
    "CONTRIBUTING.md", ".github/CONTRIBUTING.md", "docs/CONTRIBUTING.md",
    "CONTRIBUTING.rst", ".github/CONTRIBUTING.rst", "CONTRIBUTING",
]
POLICY_PATHS = [
    "AI_POLICY.md", ".github/AI_POLICY.md", "AI_USAGE_POLICY.md",
    ".github/AI_USAGE_POLICY.md", "docs/AI_POLICY.md",
]


def find_issue(root: Path, repo: str, explicit, *texts) -> str | None:
    if explicit:
        return explicit
    joined = "\n".join(t for t in texts if t)
    m = _ISSUE_URL_RE.search(joined)
    if m:
        return m.group(0)
    m = _ISSUE_REF_RE.search(joined)
    if m and "/" in repo:
        return f"https://github.com/{repo}/issues/{m.group(1)}"
    return None


def fetch_issue(url: str) -> str:
    try:
        head = sh(["gh", "issue", "view", url], timeout=GH_TIMEOUT_S)
        comments = sh(["gh", "issue", "view", url, "--comments"],
                      timeout=GH_TIMEOUT_S)
    except FileNotFoundError:
        return ("(the issue thread could not be fetched: the gh CLI is "
                "not on PATH; treat thread evidence as absent)")
    except subprocess.TimeoutExpired:
        return ("(the issue thread could not be fetched: gh timed out; "
                "treat thread evidence as absent)")
    if head.returncode != 0:
        return (f"(the issue thread could not be fetched: "
                f"{head.stderr.strip()[:200]}; treat thread evidence as "
                "absent)")
    text = head.stdout
    if comments.returncode == 0 and comments.stdout.strip():
        text += "\n\n--- comments ---\n" + comments.stdout
    return clip(text, MAX_ISSUE_CHARS, "issue thread")


def gather_live(root: Path, base: str, branch: str, repo: str,
                title, body, issue, plan_path, evidence_path) -> dict:
    live: dict[str, str] = {}
    diff = git(root, "diff", f"{base}...{branch}")
    if not diff.strip():
        raise GateStop("block",
                       f"the branch {branch} has no changes against "
                       f"{base} (git diff {base}...{branch} is empty). "
                       "There is nothing to ship yet.")
    live["diff"] = clip(diff, MAX_DIFF_CHARS, "diff")
    live["stat"] = git(root, "diff", "--stat", f"{base}...{branch}")
    live["commits"] = git(root, "log", "--oneline", f"{base}..{branch}") \
        or "(no commits on the branch beyond the base)"

    plan_p = Path(plan_path) if plan_path else root / "plan.md"
    if plan_p.is_file():
        live["plan"] = clip(plan_p.read_text(encoding="utf-8",
                                             errors="replace"),
                            MAX_DOC_CHARS, "plan")
        live["plan_src"] = str(plan_p)
    else:
        live["plan"] = ("(no plan file: nothing at "
                        f"{plan_p}; pass --plan FILE if it lives "
                        "elsewhere. House-chain students: the house plan "
                        "goes here.)")
        live["plan_src"] = "absent"

    ev_p = Path(evidence_path) if evidence_path else root / "test_evidence.md"
    if ev_p.is_file():
        live["evidence"] = clip(ev_p.read_text(encoding="utf-8",
                                               errors="replace"),
                                MAX_DOC_CHARS, "test evidence")
        live["evidence_src"] = str(ev_p)
    else:
        live["evidence"] = (f"(no test evidence file: nothing at {ev_p}; "
                            "pass --evidence FILE if it lives elsewhere)")
        live["evidence_src"] = "absent"

    live["title"] = title or ("(no title supplied: no --title on the "
                              "command or the doorway)")
    live["body"] = body or ("(no description supplied: no --body-file on "
                            "the command or the doorway)")

    rel, text = read_first(root, PR_TEMPLATE_PATHS)
    if text is None:
        tdir = root / ".github" / "PULL_REQUEST_TEMPLATE"
        if tdir.is_dir():
            files = sorted(f for f in tdir.iterdir() if f.is_file())
            if files:
                rel = str(files[0].relative_to(root))
                text = files[0].read_text(encoding="utf-8",
                                          errors="replace")
    live["pr_template"] = clip(text, MAX_DOC_CHARS, "PR template") \
        if text is not None else "(the repo ships no PR template)"
    live["pr_template_src"] = rel or "none"

    rel, text = read_first(root, CONTRIBUTING_PATHS)
    live["contributing"] = clip(text, MAX_DOC_CHARS, "CONTRIBUTING") \
        if text is not None else "(the repo ships no CONTRIBUTING file)"
    live["contributing_src"] = rel or "none"

    policies = []
    for rel in POLICY_PATHS:
        p = root / rel
        if p.is_file():
            policies.append(f"### {rel}\n\n" + clip(
                p.read_text(encoding="utf-8", errors="replace"),
                MAX_DOC_CHARS, rel))
    live["policies"] = "\n\n".join(policies) if policies else \
        "(no separate policy file found; any stated policy is in the " \
        "template or CONTRIBUTING above)"

    url = find_issue(root, repo, issue, body, live.get("plan"))
    live["issue_url"] = url or "none found"
    live["issue"] = fetch_issue(url) if url else \
        ("(no issue reference found in the PR text or plan and no --issue "
         "given; treat thread evidence as absent)")
    return live


PROMPT_TEMPLATE = """\
{skill}

----------------------------------------------------------------------
# Rubric (rubric.md)

{rubric}

----------------------------------------------------------------------
# Evidence guide (references/evidence-guide.md)

{evidence}

----------------------------------------------------------------------
# Procedure (procedure.md)

{procedure}

----------------------------------------------------------------------
# Scope (scope.md)

{scope}

----------------------------------------------------------------------
# Voice guide (voice-guide.md)

{voice}

----------------------------------------------------------------------
# Live inputs, gathered by the ship-gate for {item}

The gate ran from the clone at {root}. Base branch: {base}. Branch
under review: {branch}. Repository the pull request is for: {repo}.

## Draft PR title

{title}

## Draft PR description

{body}

## Commit list (git log --oneline {base}..{branch})

{commits}

## Diff stat (git diff --stat {base}...{branch})

{stat}

## The diff (git diff {base}...{branch})

{diff}

## The ship manifest ({manifest_name} at the clone root), as the gate ran it

{manifest}

## plan.md ({plan_src})

{plan}

## Test evidence ({evidence_src})

{test_evidence}

## The repo's PR template ({pr_template_src})

{pr_template}

## The repo's contributing instructions ({contributing_src})

{contributing}

## Stated policy files

{policies}

## The issue thread ({issue_url})

{issue}

----------------------------------------------------------------------
Run the pr-precheck skill above in LIVE MODE on this branch. The inputs
above are everything you may read: the gate gathered the live evidence
for you, so do not fetch or run anything; where a block says a source
was unavailable or absent, treat that evidence as absent and let the
rubric's verdict rule (and the frame's rule for unclear) decide. Read
scope.md first and apply its rules to this repository. Hold the draft
title and description against voice-guide.md and report any rule they
break in your summary (the voice guide changes no verdict unless the
rubric says so). Execute the procedure as written, grade every check
in the rubric using the evidence guide's map, apply the verdict rule,
and end your reply with the fenced JSON block the skill's output format
requires, using "{item}" as the item id.
"""

JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*\n(.*?)```", re.DOTALL)


def manifest_block(manifest: dict, checks_run: list) -> str:
    """The manifest as the gate ran it, for the pr-precheck prompt: every
    must-pass check with its outcome and source, and every dated
    exclusion with its reason. The student's rubric reads what was
    green and what was excluded without the student restating it."""
    lines = []
    if checks_run:
        lines.append("Must-pass checks the gate ran, in order (all green, "
                     "or the gate would have stopped before this call):")
        sources = {cmd: src for _, cmd, src in manifest["checks"]}
        for name, cmd, outcome in checks_run:
            lines.append(f"- {name}: `{cmd}` -> {outcome}; source: "
                         f"{sources.get(cmd, 'as listed in the manifest')}")
    else:
        lines.append("The manifest names no repo checks (the `none` row): "
                     "the repo's own docs state no checks, per the row's "
                     "source line.")
    if manifest["exclusions"]:
        lines.append("")
        lines.append("Checks excluded by dated judgment (the author's "
                     "recorded reason each must not gate this ship):")
        for name, cmd, since, why in manifest["exclusions"]:
            lines.append(f"- {name}: `{cmd or '(no command)'}`, since "
                         f"{since}: {why}")
    else:
        lines.append("")
        lines.append("No checks are excluded.")
    return "\n".join(lines)


def run_precheck(tool: dict, scope: str, voice: str, live: dict,
                 item: str, root: Path, base: str, branch: str,
                 repo: str) -> tuple[dict, str]:
    """One Sonnet call carrying the student's tool and the gathered live
    inputs, the way the harnesses always have. Returns (verdict object,
    readable summary)."""
    prompt = PROMPT_TEMPLATE.format(
        skill=tool["skill"], rubric=tool["rubric"],
        evidence=tool["evidence"], procedure=tool["procedure"],
        scope=scope, voice=voice, item=item, root=root, base=base,
        branch=branch, repo=repo, title=live["title"], body=live["body"],
        commits=live["commits"], stat=live["stat"], diff=live["diff"],
        manifest_name=MANIFEST_NAME, manifest=live["manifest"],
        plan_src=live["plan_src"], plan=live["plan"],
        evidence_src=live["evidence_src"], test_evidence=live["evidence"],
        pr_template_src=live["pr_template_src"],
        pr_template=live["pr_template"],
        contributing_src=live["contributing_src"],
        contributing=live["contributing"], policies=live["policies"],
        issue_url=live["issue_url"], issue=live["issue"])
    # Spawn on the subscription login, never an API key (the course's
    # standing headless-spawn convention).
    env = {k: v for k, v in os.environ.items()
           if k not in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")}
    print("ship-gate: running your pr-precheck in live mode on "
          f"{branch} (one {MODEL} call)...", file=sys.stderr, flush=True)
    last_err = None
    for _ in range(2):
        try:
            proc = subprocess.run(["claude", "-p", "--model", MODEL],
                                  input=prompt, capture_output=True,
                                  text=True, timeout=MODEL_TIMEOUT_S,
                                  env=env)
        except FileNotFoundError:
            raise GateStop("block", "the claude CLI is not on PATH, so "
                                    "your pr-precheck cannot run. The door "
                                    "stays shut until it can.")
        except subprocess.TimeoutExpired:
            last_err = f"the rubric pass timed out after {MODEL_TIMEOUT_S}s"
            continue
        if proc.returncode != 0:
            said = (proc.stderr or proc.stdout or "").strip()
            last_err = f"claude exited {proc.returncode}: {said[-240:]}"
            continue
        blocks = JSON_BLOCK_RE.findall(proc.stdout)
        if not blocks:
            last_err = "no fenced JSON block in the pr-precheck output"
            continue
        try:
            data = json.loads(blocks[-1])
        except ValueError as e:
            last_err = f"bad JSON in the pr-precheck output: {e}"
            continue
        verdict = str(data.get("verdict", "")).lower()
        if verdict not in ("accept", "reject"):
            last_err = f"pr-precheck verdict was {verdict!r}, not " \
                       "accept/reject"
            continue
        summary = proc.stdout[:proc.stdout.rfind("```json")] \
            if "```json" in proc.stdout else proc.stdout
        return data, summary.strip()
    raise GateStop("block",
                   f"your pr-precheck could not complete its run ({last_err})."
                   " Nothing was judged; the door stays shut until the "
                   "check can read your branch. Re-run, or flag a TF if "
                   "it repeats.")


# ---------------------------------------------------------------------------
# The package fingerprints (a manual PASS carries to the hook doorway)
# ---------------------------------------------------------------------------

def _fingerprint(text) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()[:12]


def package_fingerprints(root: Path, branch: str, title, body):
    """The four fingerprints that pin one package: the branch's commit
    sha and content hashes of the draft title, the draft body, and the
    manifest as it sits on disk. None when any of them cannot be read;
    the gate then simply runs."""
    head = git(root, "rev-parse", branch, ok=True)
    if not head:
        return None
    try:
        manifest_raw = (root / MANIFEST_NAME).read_text(encoding="utf-8",
                                                        errors="replace")
    except OSError:
        return None
    return {"head": head, "title": _fingerprint(title),
            "body": _fingerprint(body),
            "manifest": _fingerprint(manifest_raw)}


_LOG_HEADER_RE = re.compile(r"^## (\d{4}-\d{2}-\d{2} \d{2}:\d{2}) \[(\w+)\]")
_LOG_PACKAGE_RE = re.compile(r"^- package: head (\S+) title (\S+) body (\S+) "
                             r"manifest (\S+)$")


def fresh_manual_pass(pkg: dict):
    """The stamp of the newest manual PASS inside the window whose
    logged fingerprints match this package, or None. This trusts the
    log the way the whole gate does: your own judgment with a latch on
    the door, not a security system."""
    try:
        text = LOG_PATH.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    now = datetime.datetime.now()
    found = None
    stamp = mode = None
    passed = False
    for line in text.splitlines():
        m = _LOG_HEADER_RE.match(line)
        if m:
            stamp, mode = m.group(1), m.group(2)
            passed = False
            continue
        if line.strip() == "- verdict: PASS":
            passed = True
            continue
        m = _LOG_PACKAGE_RE.match(line)
        if m and mode == "manual" and passed and stamp:
            if (m.group(1), m.group(2), m.group(3), m.group(4)) == \
                    (pkg["head"], pkg["title"], pkg["body"],
                     pkg["manifest"]):
                try:
                    when = datetime.datetime.strptime(stamp,
                                                      "%Y-%m-%d %H:%M")
                except ValueError:
                    continue
                if 0 <= (now - when).total_seconds() <= FRESH_PASS_WINDOW_S:
                    found = stamp
    return found


# ---------------------------------------------------------------------------
# The log (the gate transcript)
# ---------------------------------------------------------------------------

def log_run(report: Report) -> None:
    if GATE_DIR.name != "ship-gate" or CLAUDE_DIR.name != ".claude":
        return          # an uninstalled copy never writes a log beside itself
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [f"## {stamp} [{report.mode}] {report.repo} @ {report.branch} "
             f"(base {report.base})", "",
             f"- verdict: {report.verdict}"]
    if report.package and report.verdict.startswith("PASS"):
        p = report.package
        lines.append(f"- package: head {p['head']} title {p['title']} "
                     f"body {p['body']} manifest {p['manifest']}")
    if report.checks:
        lines.append("- manifest checks:")
        for name, cmd, outcome in report.checks:
            lines.append(f"  - {name}: `{cmd}` -> {outcome}")
    else:
        lines.append("- manifest checks: none ran")
    if report.precheck:
        lines.append("- pr-precheck checks:")
        for c in report.precheck:
            lines.append(f"  - {c.get('name', '?')} [{c.get('grade', '?')}]: "
                         f"{c.get('evidence', '')}")
    if report.reasons:
        lines.append("- reasons quoted:")
        for r in report.reasons:
            for i, ln in enumerate(r.strip().splitlines()):
                lines.append(("  - " if i == 0 else "    ") + ln)
    lines.append("")
    try:
        GATE_DIR.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as f:
            if f.tell() == 0:
                f.write("# ship-gate log (one dated block per run, both "
                        "doorways; this file is your gate transcript)\n\n")
            f.write("\n".join(lines) + "\n")
    except OSError:
        pass


# ---------------------------------------------------------------------------
# The gate
# ---------------------------------------------------------------------------

def run_gate(mode: str, cwd: Path, branch_wanted, base_wanted, title,
             body, issue, plan_path, evidence_path) -> int:
    report = Report(mode)
    try:
        ensure_installed()
        # Repo, base, and branch resolve first, before the manifest and
        # tool loads, so every logged block (a setup stop, a refusal)
        # names them in the transcript instead of `unknown @ unknown`.
        root = repo_root(cwd)
        repo = repo_name(root, "")
        report.repo = repo
        base = detect_base(root, base_wanted)
        report.base = base
        branch = resolve_branch(root, branch_wanted, base)
        report.branch = branch
        manifest = load_manifest(root)
        if repo == root.name and manifest["repo"] and \
                "<" not in manifest["repo"]:
            repo = manifest["repo"]
            report.repo = repo
        tool = load_tool()
        scope = load_scope()
        voice, voice_note = load_voice()
        print(f"ship-gate: {repo} @ {branch} against {base}; voice guide "
              f"{voice_note}.", file=sys.stderr, flush=True)
        report.package = package_fingerprints(root, branch, title, body)
        if mode == "hook" and report.package:
            stamp = fresh_manual_pass(report.package)
            if stamp:
                report.verdict = f"PASS (honored the manual pass at {stamp})"
                log_run(report)
                print(f"ship-gate: pass on {branch}; honoring your manual "
                      f"pass at {stamp} on the identical package (same "
                      "commit, title, body, and manifest); opening the "
                      "pull request.")
                return 0
        run_checks(root, manifest["checks"], report)
        live = gather_live(root, base, branch, repo, title, body, issue,
                           plan_path, evidence_path)
        live["manifest"] = manifest_block(manifest, report.checks)
        item = f"{repo}#{branch}"
        data, summary = run_precheck(tool, scope, voice, live, item, root,
                                     base, branch, repo)
        report.precheck = data.get("checks", [])
        report.summary = summary
        if data["verdict"] != "accept":
            not_pass = [c for c in report.precheck
                        if str(c.get("grade", "")).lower() != "pass"]
            quoted = "\n".join(
                f"  - {c.get('name', '?')} [{c.get('grade', '?')}]: "
                f"{c.get('evidence', '')}" for c in not_pass) \
                or "  (the verdict was reject with no failing check " \
                   "listed; read the summary in the gate log)"
            raise GateStop("block",
                           f"your own pr-precheck held {branch}: verdict "
                           "reject. The checks that did not pass, in your "
                           f"rubric's words:\n{quoted}\nThat list is your "
                           "next-step list. Fix what it names, or, if a "
                           "check is wrong, patch your rubric (it is "
                           "yours; note the patch and what drove it).")
    except GateStop as e:
        message = e.message
        if mode == "hook" and e.kind == "setup":
            # The hook doorway resolves the clone from the Claude Code
            # session's working directory, not from the repository named
            # in the command it is gating. Say which directory was read,
            # so a setup stop is never a true statement about the wrong
            # repository.
            message += (f" (The hook doorway graded {cwd}, the session's "
                        "working directory. If that is not the clone your "
                        "branch lives in, start a session there, or run "
                        "the manual doorway from the clone: check_gate.py "
                        "--branch NAME --title ... --body-file ...)")
        report.verdict = f"BLOCK ({e.kind})"
        report.reasons.append(message)
        log_run(report)
        print(f"ship-gate: STOP. {message}", file=sys.stderr)
        return 2
    report.verdict = "PASS"
    log_run(report)
    if mode == "manual":
        print(f"ship-gate: PASS. {report.branch} clears your manifest and "
              "your own rubric; the ship decision is now yours.")
        for name, cmd, outcome in report.checks:
            print(f"  repo check {name}: {outcome}")
        for c in report.precheck:
            print(f"  {c.get('name', '?')} [{c.get('grade', '?')}]: "
                  f"{c.get('evidence', '')}")
        if report.summary:
            print("\n" + "\n".join(report.summary.splitlines()[-30:]))
    else:
        print(f"ship-gate: pass on {report.branch}; opening the pull "
              "request.")
    return 0


# ---------------------------------------------------------------------------
# Hook doorway
# ---------------------------------------------------------------------------

def find_pr_create(tokens: list[str]):
    for j in range(len(tokens) - 2):
        if tokens[j] == "gh" and tokens[j + 1] == "pr" \
                and tokens[j + 2] == "create":
            return j + 3
    return None


NO_TEXT_MSG = ("no PR text the gate can read (interactive, --help, and "
               "--fill forms are stopped at this door on purpose): write "
               "the title and body to a file and pass --title and "
               "--body-file, or run the manual doorway first "
               "(check_gate.py --branch --title ... --body-file ...).")


def parse_pr_flags(tokens: list[str], start: int, cwd: str) -> dict:
    """Return the draft and branch flags of a gh pr create command, or a
    problem string when the form carries no text the gate can read."""
    out = {"title": None, "body": None, "head": None, "base": None,
           "problem": None}

    def value(i):
        return tokens[i + 1] if i + 1 < len(tokens) else None

    i = start
    while i < len(tokens):
        t = tokens[i]
        if t in ("--web", "-w"):
            out["problem"] = ("browser ships skip the gate. Run the manual "
                              "doorway first (check_gate.py --branch "
                              "--title ... --body-file ...), then open "
                              "the pull request in the browser with the "
                              "checked text.")
            return out
        if t in ("--fill", "-f", "--fill-first", "--fill-verbose",
                 "--editor", "-e", "--help", "-h"):
            out["problem"] = NO_TEXT_MSG
            return out
        if t in ("--title", "-t"):
            out["title"] = value(i)
            i += 2
            continue
        if t.startswith("--title="):
            out["title"] = t.split("=", 1)[1]
        elif t in ("--body", "-b"):
            out["body"] = value(i)
            i += 2
            continue
        elif t.startswith("--body="):
            out["body"] = t.split("=", 1)[1]
        elif t in ("--body-file", "-F") or t.startswith("--body-file="):
            path = t.split("=", 1)[1] if "=" in t else value(i)
            if not t.startswith("--body-file="):
                i += 1
            if path == "-" or path is None:
                out["problem"] = ("--body-file - reads stdin, which the "
                                  "gate cannot see. Post from a real file.")
                return out
            try:
                out["body"] = (Path(cwd or ".") / path).read_text(
                    encoding="utf-8", errors="replace")
            except OSError as e:
                out["problem"] = f"could not read the body file: {e}"
                return out
        elif t in ("--head", "-H"):
            out["head"] = value(i)
            i += 2
            continue
        elif t.startswith("--head="):
            out["head"] = t.split("=", 1)[1]
        elif t in ("--base", "-B"):
            out["base"] = value(i)
            i += 2
            continue
        elif t.startswith("--base="):
            out["base"] = t.split("=", 1)[1]
        i += 1
    if not out["title"] or not out["body"]:
        out["problem"] = NO_TEXT_MSG
    return out


def hook_main() -> int:
    if sys.stdin.isatty():
        print("ship-gate: hook mode reads Claude Code's tool-call JSON on "
              "stdin. For a run by hand use the manual doorway: "
              "check_gate.py --branch [NAME] [--title ... --body-file ...]",
              file=sys.stderr)
        return 2
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    if payload.get("tool_name") != "Bash":
        return 0
    command = (payload.get("tool_input") or {}).get("command", "")
    try:
        tokens = shlex.split(command)
    except ValueError:
        return 0
    start = find_pr_create(tokens)
    if start is None:
        return 0
    cwd = payload.get("cwd") or os.getcwd()
    flags = parse_pr_flags(tokens, start, cwd)
    if flags["problem"]:
        report = Report("hook")
        report.verdict = "BLOCK (setup)"
        report.reasons.append(flags["problem"])
        report.branch = flags["head"] or "(current)"
        # Inside a clone the repo, base, and branch are knowable even on
        # a doorway-form stop; name them in the transcript when they are.
        try:
            root = repo_root(Path(cwd))
            report.repo = repo_name(root, "")
            report.base = detect_base(root, flags["base"])
            if not flags["head"]:
                report.branch = git(root, "rev-parse", "--abbrev-ref",
                                    "HEAD", ok=True) or "(current)"
        except GateStop:
            pass
        log_run(report)
        print(f"ship-gate: STOP. {flags['problem']}", file=sys.stderr)
        return 2
    branch = None
    if flags["head"]:
        # gh accepts OWNER:BRANCH for cross-fork heads; the local branch
        # is the part after the colon.
        branch = flags["head"].split(":", 1)[-1]
    return run_gate("hook", Path(cwd), branch, flags["base"],
                    flags["title"], flags["body"], None, None, None)


# ---------------------------------------------------------------------------
# Entry
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description=(
        "ship-gate runner: hook mode (no args, Claude Code tool-call JSON "
        "on stdin) or the manual doorway (--branch [NAME])."))
    ap.add_argument("--branch", nargs="?", const="HEAD", default=None,
                    metavar="NAME",
                    help="run the gate on the current branch (or NAME): "
                         "the manual doorway for browser ships and dry runs")
    ap.add_argument("--base", metavar="NAME",
                    help="the base branch (default: main, then master, "
                         "then origin's HEAD)")
    ap.add_argument("--title", metavar="TEXT",
                    help="the draft PR title")
    ap.add_argument("--body-file", metavar="FILE",
                    help="the draft PR description, as a file")
    ap.add_argument("--issue", metavar="URL",
                    help="the issue this branch addresses (default: found "
                         "in the PR text or plan.md)")
    ap.add_argument("--plan", metavar="FILE",
                    help="your plan file (default: plan.md at the clone "
                         "root)")
    ap.add_argument("--evidence", metavar="FILE",
                    help="your captured test evidence (default: "
                         "test_evidence.md at the clone root)")
    args = ap.parse_args()

    if args.branch is None:
        if any((args.base, args.title, args.body_file, args.issue,
                args.plan, args.evidence)):
            ap.error("the manual doorway needs --branch (add it, alone "
                     "for the current branch or with a name)")
        return hook_main()

    body = None
    if args.body_file:
        try:
            body = Path(args.body_file).read_text(encoding="utf-8",
                                                  errors="replace")
        except OSError as e:
            print(f"ship-gate: cannot read {args.body_file}: {e}",
                  file=sys.stderr)
            return 2
    return run_gate("manual", Path.cwd(),
                    None if args.branch == "HEAD" else args.branch,
                    args.base, args.title, body, args.issue, args.plan,
                    args.evidence)


if __name__ == "__main__":
    sys.exit(main())
