#!/usr/bin/env python3
"""ship-gate install: the packaging beat, as a script.

Unit 6's install was hand motions: make a folder, copy two files, move
the guide, three symlinks, a JSON block merged by hand, a scope file
copied over. It worked, by hand. This week the package installs itself
as one unit. What the script does, in order (INSTALL.md carries the same
steps as the manual fallback and explains each one):

  0. Preflight, changing nothing. Your pr-precheck must be installed at
     ~/.claude/skills/pr-precheck/ (the gate wraps YOUR tool and nothing
     else). The three sandbox scopes (repro-check, plan-check,
     pr-precheck) are checked for the Path Review placeholder: the
     pr-precheck swap is this install's own step 3; a missing unit-6
     swap for the other two is printed as the exact copy command.
  1. Copies the package (runner, hook block, manifest template, scope
     file, install, INSTALL.md) into ~/.claude/ship-gate/, so the folder
     is self-contained and travels as one unit.
  2. Merges the hook entry into ~/.claude/settings.json. A dated backup
     is written first; the merge is a JSON merge, never a text edit; a
     second run finds the entry present and changes nothing.
  3. Swaps pr-precheck's scope: the installed scope.md is kept beside it
     as scope.md.sandbox and the real-world scope takes its place. Your
     submitted Module 1 copy in your course repo's tools/ is never touched.
  4. With --repo PATH (the root of your clone): creates ship-manifest.md
     there from the template, never overwriting one you already have,
     and adds it, plus the three working files (plan.md,
     test_evidence.md, pr_draft.md), to .git/info/exclude so none of
     them ever enters your diff. Without --repo: prints those commands
     for later.

Run it from anywhere:  python3 skill/install.py [--repo PATH]

Nothing here edits your tool's judgment files (SKILL.md, rubric.md,
procedure.md, the evidence guide, the voice guide) or any other skill.
"""

import argparse
import datetime
import json
import shutil
import subprocess
import sys
from pathlib import Path

HOME = Path.home()
CLAUDE_DIR = HOME / ".claude"
GATE_DIR = CLAUDE_DIR / "ship-gate"
SETTINGS = CLAUDE_DIR / "settings.json"
SKILLS = CLAUDE_DIR / "skills"
TOOL_DIR = SKILLS / "pr-precheck"
SRC = Path(__file__).resolve().parent

PACKAGE_FILES = ["check_gate.py", "hooks-settings.json",
                 "gate-manifest-template.md", "scope-live.md",
                 "install.py", "INSTALL.md"]
MARKER = "ship-gate/check_gate.py"
MANIFEST_NAME = "ship-manifest.md"
# The three working files (unit 4's rule: working notes never enter a
# diff) join the manifest on the exclude list, so a `git status` slip
# cannot commit them.
WORKING_FILES = ["plan.md", "test_evidence.md", "pr_draft.md"]
SANDBOX_TELLS = ("PATH-REVIEW", "<ORG>")
WILD_SWAPS = {
    "repro-check": "repro-check-scope-wild.md",
    "plan-check": "plan-check-scope-wild.md",
}


def say(msg: str) -> None:
    print(f"ship-gate install: {msg}")


def stop(msg: str) -> int:
    print(f"ship-gate install: STOPPED. {msg}\nNothing was changed.",
          file=sys.stderr)
    return 2


def scope_state(skill: str) -> str:
    d = SKILLS / skill
    if not d.is_dir():
        return "not-installed"
    p = d / "scope.md"
    if not p.is_file():
        return "no-scope"
    text = p.read_text(encoding="utf-8", errors="replace")
    if any(t in text for t in SANDBOX_TELLS):
        return "sandbox"
    return "wild"


def preflight() -> int | None:
    if not TOOL_DIR.is_dir():
        return stop(f"your pr-precheck is not installed at {TOOL_DIR}. The "
                    "gate wraps YOUR unit-4 tool, so install its shell "
                    "first: copy the whole skill/ folder from your Unit 4 "
                    "materials to that path and write its four files "
                    "(a still-empty tool installs fine; the gate will "
                    "refuse honestly until you finish it).")
    for f in PACKAGE_FILES:
        if not (SRC / f).is_file():
            return stop(f"{SRC / f} is missing; run this script from the "
                        "unpacked Unit 7 materials (skill/install.py).")
    if SETTINGS.is_file():
        raw = SETTINGS.read_text(encoding="utf-8")
        try:
            parsed = json.loads(raw) if raw.strip() else {}
        except json.JSONDecodeError as e:
            return stop(f"{SETTINGS} is not valid JSON ({e}). Fix it first "
                        "(python3 -m json.tool on the file shows where), "
                        "then run the install again; the script never "
                        "edits a settings file it cannot parse.")
        if not isinstance(parsed, dict):
            return stop(f"{SETTINGS} does not hold a JSON object.")
        hooks = parsed.get("hooks", {})
        if not isinstance(hooks, dict):
            return stop(f"the \"hooks\" key in {SETTINGS} is not an object; "
                        "fix the shape, then run the install again.")
        if not isinstance(hooks.get("PreToolUse", []), list):
            return stop(f"\"hooks\".\"PreToolUse\" in {SETTINGS} is not a "
                        "list; fix the shape, then run the install again.")
    say("preflight: the three sandbox scopes")
    for skill in ("repro-check", "plan-check", "pr-precheck"):
        st = scope_state(skill)
        if skill == "pr-precheck":
            note = {"sandbox": "sandbox placeholder; this install swaps it "
                               "in step 3",
                    "no-scope": "no scope.md; this install places the "
                                "real-world one in step 3",
                    "wild": "already the real-world scope"}[st]
        elif st == "not-installed":
            note = ("not installed (a Module 1 item still open; nothing "
                    "to swap)")
        elif st == "wild":
            note = "real-world scope in place"
        else:
            note = ("STILL THE SANDBOX SCOPE: your live runs there will "
                    "refuse in the wild. From your unpacked Unit 6 "
                    f"materials run:  cp skill/{WILD_SWAPS[skill]} "
                    f"~/.claude/skills/{skill}/scope.md  (no longer "
                    "unpacked? the Unit 6 materials link in course chat "
                    "downloads them again)")
        say(f"  {skill}: {note}")
    return None


def install_package() -> None:
    GATE_DIR.mkdir(parents=True, exist_ok=True)
    for f in PACKAGE_FILES:
        shutil.copy2(SRC / f, GATE_DIR / f)
    say(f"step 1: package copied into {GATE_DIR} ({len(PACKAGE_FILES)} "
        "files)")


def merge_hook() -> int | None:
    block = json.loads((SRC / "hooks-settings.json").read_text(
        encoding="utf-8"))
    entry = block["hooks"]["PreToolUse"][0]
    for h in entry["hooks"]:
        h["command"] = h["command"].replace("$HOME", str(HOME))

    if SETTINGS.is_file():
        raw = SETTINGS.read_text(encoding="utf-8")
        try:
            settings = json.loads(raw) if raw.strip() else {}
        except json.JSONDecodeError as e:
            return stop(f"{SETTINGS} is not valid JSON ({e}). Fix it first "
                        "(python3 -m json.tool on the file shows where), "
                        "then run the install again; the script never "
                        "edits a settings file it cannot parse.")
    else:
        settings = {}
    if not isinstance(settings, dict):
        return stop(f"{SETTINGS} does not hold a JSON object.")
    hooks = settings.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        return stop(f"the \"hooks\" key in {SETTINGS} is not an object.")
    pre = hooks.setdefault("PreToolUse", [])
    if not isinstance(pre, list):
        return stop(f"\"hooks\".\"PreToolUse\" in {SETTINGS} is not a list.")

    def has_marker(group) -> bool:
        return isinstance(group, dict) and any(
            isinstance(h, dict) and MARKER in str(h.get("command", ""))
            for h in group.get("hooks", []))

    if any(has_marker(g) for g in pre):
        say("step 2: the hook entry is already in settings.json; nothing "
            "to merge (safe re-run)")
        return None

    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    CLAUDE_DIR.mkdir(parents=True, exist_ok=True)
    if SETTINGS.is_file():
        backup = SETTINGS.with_name(f"settings.json.bak-{stamp}")
        shutil.copy2(SETTINGS, backup)
        say(f"step 2: backup written to {backup.name}")
    else:
        say("step 2: no settings.json yet; creating one")
    pre.append(entry)
    SETTINGS.write_text(json.dumps(settings, indent=2) + "\n",
                        encoding="utf-8")
    say(f"step 2: hook entry merged into {SETTINGS} (JSON merge; the "
        "voice-guard's entry, if present, is untouched)")
    return None


def swap_scope() -> None:
    live = (SRC / "scope-live.md").read_text(encoding="utf-8")
    target = TOOL_DIR / "scope.md"
    if target.is_file():
        current = target.read_text(encoding="utf-8", errors="replace")
        if current == live:
            say("step 3: pr-precheck's scope.md is already the real-world "
                "scope; nothing to swap")
            return
        keep = TOOL_DIR / "scope.md.sandbox"
        if keep.exists():
            stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            keep = TOOL_DIR / f"scope.md.sandbox-{stamp}"
        shutil.copy2(target, keep)
        say(f"step 3: your previous scope kept as {keep.name}")
    target.write_text(live, encoding="utf-8")
    say(f"step 3: real-world scope placed at {target} (pr-precheck's field "
        "of view is now any public repository; eval mode never reads it)")


def place_manifest(repo: str | None) -> int | None:
    template = GATE_DIR / "gate-manifest-template.md"
    if not repo:
        names = " ".join([MANIFEST_NAME, *WORKING_FILES])
        say("step 4: no --repo given. From the root of your clone, run:\n"
            f"    cp {template} {MANIFEST_NAME}\n"
            f"    printf '%s\\n' {names} >> .git/info/exclude")
        return None
    root = Path(repo).expanduser().resolve()
    try:
        top = subprocess.run(["git", "-C", str(root), "rev-parse",
                              "--show-toplevel"], capture_output=True,
                             text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        top = None
    if top is None or top.returncode != 0 \
            or Path(top.stdout.strip()).resolve() != root:
        say(f"step 4: {root} is not the root of a git clone; the manifest "
            "was not placed. Re-run with --repo pointing at the clone "
            "root, or use the two commands above there.")
        return None
    manifest = root / MANIFEST_NAME
    if manifest.exists():
        say(f"step 4: {manifest} already exists; left exactly as it is")
    else:
        shutil.copy2(template, manifest)
        say(f"step 4: {MANIFEST_NAME} created at {root} from the template; "
            "fill it (it is the judgment part)")
    exclude = root / ".git" / "info" / "exclude"
    exclude.parent.mkdir(parents=True, exist_ok=True)
    raw = exclude.read_text(encoding="utf-8") if exclude.is_file() else ""
    present = [ln.strip() for ln in raw.splitlines()]
    missing = [n for n in [MANIFEST_NAME, *WORKING_FILES]
               if n not in present]
    if not missing:
        say("step 4: .git/info/exclude already lists the manifest and "
            "the three working files")
    else:
        with exclude.open("a", encoding="utf-8") as f:
            if raw and not raw.endswith("\n"):
                f.write("\n")
            for n in missing:
                f.write(n + "\n")
        say(f"step 4: {', '.join(missing)} added to .git/info/exclude "
            "(the manifest and your working notes never enter your diff)")
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=(
        "Install the ship-gate package as one unit (see INSTALL.md for "
        "what each step does and the manual fallback)."))
    ap.add_argument("--repo", metavar="PATH",
                    help="the root of your clone: create ship-manifest.md "
                         "there from the template and exclude it from the "
                         "diff")
    args = ap.parse_args()

    rc = preflight()
    if rc is not None:
        return rc
    install_package()
    rc = merge_hook()
    if rc is not None:
        return rc
    swap_scope()
    place_manifest(args.repo)
    say("done. Two things remain, both yours, in either order:\n"
        "  - Start a fresh `claude` session (settings load at startup), "
        "then prove the latch: `claude \"run this command: gh pr create "
        "--help\"` must be STOPPED. Expect TWO stops on that door: the "
        "unit-6 voice-guard (no body it can read) and this gate (no PR "
        "text it can read). Both stops are the pass; read the gate's.\n"
        "  - Fill ship-manifest.md at your clone root (the repo's own "
        "checks, each with its source, each written in the form that "
        "runs from a fresh shell), then run the gate in anger: "
        f"`python3 {GATE_DIR / 'check_gate.py'} --branch` from the clone, "
        "with --title and --body-file (the description) when you have a "
        "draft.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
