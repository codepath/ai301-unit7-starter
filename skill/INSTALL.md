# Installing the ship-gate (one unit, and what the script does)

This install puts a gate on your PR-opening doorway: before any pull
request of yours goes out, the gate runs the repo's own checks from a
manifest you write, then your own pr-precheck in live mode on your
real branch, and blocks the ship quoting exactly what failed. It is an
**overlay onto what you already own**, stated in every direction:

- **Added:** the gate, as one folder at `~/.claude/ship-gate/`: the
  runner `check_gate.py` (both doorways), one hook entry in your Claude
  Code settings (`hooks-settings.json` is the block), the manifest
  template `gate-manifest-template.md`, and the real-world scope file.
  All staff-complete; you write no code.
- **Replaced:** pr-precheck's `scope.md`, the unit-4 sandbox scope for
  the real-world one (`scope-live.md`, staff-complete; unit 4's staff
  materials were written for exactly this swap). Your previous scope
  is kept beside it as `scope.md.sandbox`, and the copy you submitted in
  Module 1 stays untouched in your course repo's `tools/pr-precheck/`.
- **Promoted:** nothing this week. Your voice guide moved to its one
  canonical home in unit 6; the gate reads it there, through the link
  in pr-precheck's own folder.
- **Yours and untouched:** every file of pr-precheck as you wrote it
  (`SKILL.md`, `rubric.md`, `procedure.md`, your evidence guide, your
  voice guide), the scout, the voice-guard, the unit-1 harness, and
  every Module 1 skill folder in your course repo's `tools/` exactly
  as submitted.

The gate never runs in eval mode. Nothing here touches how the unit-1
or unit-4 harness measures your rubric, and nothing here edits a
judgment file of yours: if the gate ever blocks a ship, the words it
quotes are the repo's own check or your own rubric, nothing else.

## 1. Run the install

From the folder where you unpacked the Unit 7 materials, with your
clone's root as the argument:

```
python3 skill/install.py --repo <path to your clone>
```

What the script does, in order (the numbers match its output):

0. **Preflight, changing nothing.** Your pr-precheck must be installed
   at `~/.claude/skills/pr-precheck/` (the gate wraps YOUR tool and
   nothing else; a still-empty tool installs fine and the gate will
   refuse honestly until you finish it). It then reads the three
   sandbox scopes, repro-check, plan-check, and pr-precheck, for the
   Path Review placeholder: pr-precheck's swap is step 3 below; a
   missing unit-6 swap for the other two is printed as the exact copy
   command, so a live run in the wild never refuses on you later. The
   command runs from your unpacked Unit 6 materials; if those are gone,
   the Unit 6 materials link in course chat downloads them again.
1. **Copies the package** into `~/.claude/ship-gate/`, all six files,
   so the folder is self-contained and uploads as one unit.
2. **Merges the hook entry** into `~/.claude/settings.json`. A dated
   backup of your settings is written first; the merge is a JSON merge,
   never a text edit; the unit-6 voice-guard's entry is left exactly as
   it is; a second run finds the entry present and changes nothing.
   The install writes your absolute home path into the hook command,
   which is what unit 6's wiring fix did by hand.
3. **Swaps pr-precheck's scope**: your installed `scope.md` is kept as
   `scope.md.sandbox` and the real-world scope takes its place. From
   now on pr-precheck's field of view is any public repository.
4. **Places your manifest**: `ship-manifest.md` is created at your
   clone's root from the template (never overwriting one you already
   have) and added to `.git/info/exclude`, the mechanism your
   `CLAUDE.local.md` already uses, so it never enters your diff. The
   three working files, `plan.md`, `test_evidence.md`, and
   `pr_draft.md`, go on the same list: they are working notes by the
   unit-4 rule, and the exclude line means a `git status` slip cannot
   commit them. No `--repo`? The script prints the commands to run from
   the clone root later.

If the script stops, it says why and changes nothing: pr-precheck not
installed (install its shell from your Unit 4 materials first), a
`settings.json` it cannot parse or whose `hooks` block has the wrong
shape (fix the JSON, then re-run), or a package file missing (run it
from the unpacked materials). Every stop happens in the preflight,
before anything is copied.

Then **start a fresh `claude` session**: settings load at startup.

## 2. Prove the latch is on (expect two stops)

The wiring canary costs nothing and should be STOPPED. The activity has
you write the manifest first and run the canary second; either order
works, because the canary stops before the manifest is read:

```
claude "run this command: gh pr create --help"
```

Expect **two** stops on this door, and that is correct. Since unit 6
your voice-guard also fires on `gh pr create`: it reads the words (the
PR body against your voice guide), and a body-less command has none, so
it stops. The ship-gate reads readiness (the branch against your
manifest and your rubric), and a command with no title and no body is
stopped at the door on purpose, before any check runs and before any
model call, so it stops too. The guard owns voice; the gate owns
readiness; each quotes its own reason. Read the gate's: its line
starts with `ship-gate: STOP.` Both stops together are the pass. Real
ships always carry `--title` and `--body-file`, and a plain terminal
still runs `gh pr create --help` fine.

If the command runs unblocked instead: you are in the session that was
open during the install (start a fresh one), or step 2's merge did not
land (check that `~/.claude/settings.json` is valid JSON and lists a
`PreToolUse` entry whose command names `ship-gate/check_gate.py`).
Those two cover nearly every miss.

## 3. The manual doorway

For a pull request you will open in the browser, and for dry runs at
any branch state, the same gate runs by hand. From your clone, on your
branch:

```
python3 ~/.claude/ship-gate/check_gate.py --branch --title "<your PR title>" --body-file pr_draft.md
```

`--branch` alone means the branch you are on; `--branch NAME` names
another. `--title` and `--body-file` carry the draft your pr-precheck
reads: the title on the flag, the description in the file (leave them
off for a dry run and the report will say the draft is absent).
`--base NAME` overrides the base branch (the default is `main`, then
`master`, then origin's HEAD; pass it whenever the repo's contributing
guide sends pull requests at another branch, such as `dev`). `--plan
FILE` and `--evidence FILE` point at a plan or test-evidence file that
does not sit at the clone root as `plan.md` and `test_evidence.md`,
and `--issue URL` names the issue when the PR text and plan do not.
You get the same verdict shape either doorway: pass, or the exact
reason quoted. A pass here carries to the hook doorway for 30
minutes: on the identical package (same commit, same title, same
description, same manifest) a `gh pr create` goes straight through
without a second run, because the manual doorway is the same gate.

## 4. What stops the gate, and the route out

There is no override flag, by design. Every stop names its route:

- **No manifest, or a manifest still the template.** Fill
  `ship-manifest.md` at the clone root: the repo's own checks, one row
  each, with the source it came from. A row with a command and no
  source stops the gate too; so does an exclusion without a date and a
  reason.
- **Your pr-precheck is missing or still templates.** The gate reports
  the REFUSAL honestly: that is your tool's own unit-4 design telling
  the truth, not the gate breaking. The sanctioned route is finishing
  your own pr-precheck as Assignment 5 working time; TFs route this.
  Never copy a master: the gate quotes your rubric, so it has to be
  yours.
- **pr-precheck's scope is still the sandbox.** Run the install (step
  3 places the real-world scope).
- **Your voice guide has no canonical home.** The gate reads the guide
  of record, never the frozen unit-4 copy: finish unit 6's INSTALL
  step 3 (the `mv` to `~/.claude/voice-guard/` and the `ln -sf` back
  into pr-precheck). The documented pointer-line fallback works too.
- **A manifest check failed.** The gate quotes the command, its exit
  code, and the tail of its output. Fix what it names; if you decide it
  must not gate this ship, record a dated exclusion in the manifest
  instead of deleting the row. The legal reasons are the template's:
  red on main for reasons your PR never touches; a check you cannot
  run here (a toolchain or a service you lack, named); a check that
  rewrites tracked files and would dirty your diff. Exit 127 (`command
  not found`) means the row was written for your activated terminal:
  the gate runs a fresh shell at the clone root on both doorways, so
  write the form that runs there (`uv run pytest`, `.venv/bin/ruff
  check .`, `npx eslint .`), still mined from the repo's setup, still
  sourced. A module-not-found error from a package runner (`jest` not
  found under `npm run test`) is the second tell in the same family:
  the repo's setup step (`npm install`, `uv sync`, `pip install -e
  .[dev]`) has not run in this clone, and that step belongs in your
  manifest as its own first must-pass row, sourced to the same guide.
- **Your pr-precheck said reject.** The gate quotes the checks that did
  not pass, in your rubric's words, with their evidence lines: that is
  your next-step list, in order. Fix what it names, or, if a check is
  wrong, patch your rubric (it is yours; note the patch and what drove
  it in your Toolkit entry). A fresh manual pass is honored at the
  door (section 3), so a reject here right after one means something
  changed: a new commit, an edited title or description, an edited
  manifest, or a pass older than 30 minutes. On the changed package
  one model pass on a check near the line your rubric drew can land
  differently, and the route is the same, fix what it names or
  tighten the evidence it points at; never re-roll until it passes.
- **The guard stopped a ship the gate passed.** By contract: your
  pr-precheck reads your voice guide as feedback and never changes its
  verdict on it, the unit-6 guard blocks on the same guide. The voice
  notes in a passing gate report are the preview; fix the line, then
  ship.

## 5. The manual fallback

If the script cannot run on your machine, the same install by hand is
unit 6's practiced motion:

```
mkdir -p ~/.claude/ship-gate
cp skill/check_gate.py skill/hooks-settings.json skill/gate-manifest-template.md skill/scope-live.md skill/install.py skill/INSTALL.md ~/.claude/ship-gate/
cp ~/.claude/skills/pr-precheck/scope.md ~/.claude/skills/pr-precheck/scope.md.sandbox
cp skill/scope-live.md ~/.claude/skills/pr-precheck/scope.md
```

Then merge the block in `skill/hooks-settings.json` into
`~/.claude/settings.json` exactly as you did in unit 6 (no `hooks` key
yet: paste the whole block; hooks already there: add the `PreToolUse`
entry to the list), replacing `$HOME` in its command with your absolute
home directory path. Finally, from your clone's root:

```
cp ~/.claude/ship-gate/gate-manifest-template.md ship-manifest.md
printf '%s\n' ship-manifest.md plan.md test_evidence.md pr_draft.md >> .git/info/exclude
```

Start a fresh `claude` session and run section 2's canary.

## 6. The evidence trail

Every run, both doorways, appends a dated block to
`~/.claude/ship-gate/gate-log.md`: repo, branch, each manifest check
with its outcome, the verdict, the reasons quoted. A passing run also
records the package it passed (the commit sha and content
fingerprints of the title, description, and manifest); that line is
how the hook doorway recognizes a fresh manual pass. That file is
your gate transcript. The log, your manifest as run, and the package
files from this folder stay on your machine as one self-contained
unit: the unit-7 Toolkit entry in your round-1 README, in your own
words, is what Assignment 5 reads, and the packaged gate is unit-9
portfolio material.
