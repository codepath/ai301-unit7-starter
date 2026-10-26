#!/usr/bin/env python3
"""ship-gate install.

Installs the ship-gate in one step. What it does, in order (INSTALL.md
has the same steps, and how to do them by hand):

  0. Checks first, changing nothing. Your pr-precheck must be at
     ~/.claude/skills/pr-precheck/, because the ship-gate runs it. It
     also checks that repro-check and plan-check have the scopes for
     real repos from unit 6, and prints the copy command for any that
     don't.
  1. Copies the ship-gate's files into ~/.claude/ship-gate/.
  2. Adds the hook to ~/.claude/settings.json. It saves a dated backup
     first and merges the JSON rather than editing it as text. A second
     run finds the hook already there and changes nothing.
  3. Swaps pr-precheck's scope.md for the scope for real repos and keeps
     the old one beside it as scope.md.sandbox. The copy of pr-precheck
     in your course repo's tools/ folder isn't touched.
  4. With --repo PATH (the top folder of your clone): creates
     ship-manifest.md there from the template, never overwriting one you
     already have, and adds it and the three working files (plan.md,
     test_evidence.md, pr_draft.md) to .git/info/exclude, so they stay
     out of your commits. Without --repo, it prints those commands.

Run it from your Unit 7 materials folder:

  python3 skill/install.py --repo <path to your clone>

It never edits the files you wrote (SKILL.md, rubric.md, procedure.md,
your evidence guide, your voice guide) or any other skill.
"""

from __future__ import annotations

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
# Two families of tell, because a cohort fills the placeholder before the
# term starts: an unfilled sandbox scope still carries the staff brackets,
# and a filled one still carries the sentence that names the classroom repo.
# Sniffing only the brackets read a correctly configured sandbox scope as
# already swapped, which is the one case this preflight exists for.
SANDBOX_TELLS = ("PATH-REVIEW", "<ORG>",
                 "the course's Path Review repository")
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
    if skill == "pr-precheck":
        # Answer the way step 3 answers, by comparing content against the
        # copy this package ships, so the preflight and the swap can never
        # disagree about the same file.
        live = (SRC / "scope-live.md").read_text(encoding="utf-8",
                                                 errors="replace")
        return "wild" if text == live else "sandbox"
    if any(t in text for t in SANDBOX_TELLS):
        return "sandbox"
    return "wild"


def preflight() -> int | None:
    if not TOOL_DIR.is_dir():
        return stop(f"your pr-precheck is not installed at {TOOL_DIR}. The "
                    "ship-gate runs your unit 4 tool, so install it "
                    "first: copy the whole skill/ folder from your Unit 4 "
                    "materials to that path. It can be unfinished for "
                    "now; the ship-gate says what's missing when it "
                    "runs.")
    for f in PACKAGE_FILES:
        if not (SRC / f).is_file():
            return stop(f"{SRC / f} is missing. Run this script from your "
                        "Unit 7 materials folder: python3 "
                        "skill/install.py --repo <path to your clone>")
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
    say("step 0: checking the scopes of repro-check, plan-check, and "
        "pr-precheck (nothing changes yet)")
    for skill in ("repro-check", "plan-check", "pr-precheck"):
        st = scope_state(skill)
        if skill == "pr-precheck":
            note = {"sandbox": "still the sandbox scope; step 3 swaps in "
                               "the scope for real repos and keeps your "
                               "copy",
                    "no-scope": "no scope.md yet; step 3 adds the scope "
                                "for real repos",
                    "wild": "already has the scope for real repos"}[st]
        elif st == "not-installed":
            note = "not installed, so there's nothing to check"
        elif st == "wild":
            note = "has the scope for real repos"
        else:
            note = ("doesn't have the scope for real repos yet, so it "
                    "will refuse real issues. From your Unit 6 materials "
                    f"folder, run:  cp skill/{WILD_SWAPS[skill]} "
                    f"~/.claude/skills/{skill}/scope.md  (deleted that "
                    "folder? Clone "
                    "https://github.com/codepath/ai301-unit6-starter "
                    "again.)")
        say(f"  {skill}: {note}")
    return None


def install_package() -> None:
    GATE_DIR.mkdir(parents=True, exist_ok=True)
    for f in PACKAGE_FILES:
        shutil.copy2(SRC / f, GATE_DIR / f)
    say(f"step 1: copied the ship-gate's {len(PACKAGE_FILES)} files into "
        f"{GATE_DIR}")


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
        say("step 2: the hook is already in settings.json, so nothing "
            "changed")
        return None

    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    CLAUDE_DIR.mkdir(parents=True, exist_ok=True)
    if SETTINGS.is_file():
        backup = SETTINGS.with_name(f"settings.json.bak-{stamp}")
        shutil.copy2(SETTINGS, backup)
        say(f"step 2: saved a backup of your settings as {backup.name}")
    else:
        say("step 2: no settings.json yet; creating one")
    pre.append(entry)
    SETTINGS.write_text(json.dumps(settings, indent=2) + "\n",
                        encoding="utf-8")
    say(f"step 2: added the hook to {SETTINGS} (your voice guard's entry "
        "is unchanged)")
    return None


def swap_scope() -> None:
    live = (SRC / "scope-live.md").read_text(encoding="utf-8")
    target = TOOL_DIR / "scope.md"
    if target.is_file():
        current = target.read_text(encoding="utf-8", errors="replace")
        if current == live:
            say("step 3: pr-precheck already has the scope for real "
                "repos, so nothing changed")
            return
        keep = TOOL_DIR / "scope.md.sandbox"
        if keep.exists():
            stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            keep = TOOL_DIR / f"scope.md.sandbox-{stamp}"
        shutil.copy2(target, keep)
        say(f"step 3: kept your old scope as {keep.name}")
    target.write_text(live, encoding="utf-8")
    say(f"step 3: put the scope for real repos at {target}, so "
        "pr-precheck can check a branch on any public repo (eval runs "
        "never read it)")


def place_manifest(repo: str | None) -> bool:
    """Step 4. True when the clone has its manifest and exclude lines."""
    template = GATE_DIR / "gate-manifest-template.md"
    if not repo:
        names = " ".join([MANIFEST_NAME, *WORKING_FILES])
        say("step 4: no --repo given. From the top folder of your clone, "
            "run:\n"
            f"    cp {template} {MANIFEST_NAME}\n"
            f"    printf '%s\\n' {names} >> .git/info/exclude")
        return False
    root = Path(repo).expanduser().resolve()
    try:
        top = subprocess.run(["git", "-C", str(root), "rev-parse",
                              "--show-toplevel"], capture_output=True,
                             text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        top = None
    if top is None or top.returncode != 0 \
            or Path(top.stdout.strip()).resolve() != root:
        say(f"step 4: {root} isn't the top folder of a git clone, so no "
            "manifest was created.")
        return False
    manifest = root / MANIFEST_NAME
    if manifest.exists():
        say(f"step 4: {manifest} already exists, so it was left as it is")
    else:
        shutil.copy2(template, manifest)
        say(f"step 4: created {MANIFEST_NAME} in {root}. Fill it in next; "
            "the comment at its top explains how.")
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
        say(f"step 4: added {', '.join(missing)} to .git/info/exclude, so "
            "they stay out of your commits")
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description=(
        "Install the ship-gate (INSTALL.md explains each step and how to "
        "do it by hand)."))
    ap.add_argument("--repo", metavar="PATH",
                    help="the top folder of your clone: creates "
                         "ship-manifest.md there and keeps it out of your "
                         "commits")
    args = ap.parse_args()

    rc = preflight()
    if rc is not None:
        return rc
    install_package()
    rc = merge_hook()
    if rc is not None:
        return rc
    swap_scope()
    placed = place_manifest(args.repo)
    if args.repo and not placed:
        say("steps 1 to 3 are done, but there's no ship-manifest.md yet. "
            "Run the install again with --repo set to the top folder of "
            "your clone (inside your clone, `git rev-parse "
            "--show-toplevel` prints it). Running it again is safe.")
        return 2
    manifest_step = ("Fill in ship-manifest.md in your clone." if placed
                     else "Create ship-manifest.md with the two commands "
                     "above, then fill it in.")
    say("done. Next:\n"
        "  1. Quit any open `claude` session. Claude Code only loads hooks "
        "when a session starts.\n"
        f"  2. {manifest_step} The comment at its top explains how.\n"
        "  3. Test the hook from your clone: claude \"run this command: "
        "gh pr create --help\". You should see two stops, one from your "
        "voice guard and one that starts with `ship-gate: STOP.`")
    return 0


if __name__ == "__main__":
    sys.exit(main())
