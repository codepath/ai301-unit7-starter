# Installing the ship-gate

The ship-gate is a hook. Before Claude Code runs `gh pr create`, it
runs the checks in your ship manifest (the project's own tests and
lint), then your pr-precheck from unit 4 on your branch. If anything
fails, it stops the PR and tells you why. You can also run it by hand
on your branch before you open the PR.

The Unit 7 Assignment tab walks you through the install and everything
after it. This file explains what the install does, and what to do when
something stops.

What the install changes:

- **Adds** a `~/.claude/ship-gate/` folder with the ship-gate's six
  files, and one hook entry in `~/.claude/settings.json`.
- **Replaces** pr-precheck's `scope.md` (the unit 4 sandbox scope) with
  the scope for real repos. Your old scope is kept beside it as
  `scope.md.sandbox`.
- **Adds to your clone** a `ship-manifest.md` for you to fill in. It
  lists that file and your three working files (`plan.md`,
  `test_evidence.md`, and `pr_draft.md`) in `.git/info/exclude`, so they
  stay out of your commits.

It doesn't touch anything else: your rubric and the rest of
pr-precheck, your other skills, your voice guard, or the copies in your
course repo's `tools/` folder. The ship-gate never runs during eval
runs, so it doesn't change how your eval harness grades your rubric.

You need Python 3.8 or newer (`python3 --version`) and `gh`, logged in.

## 1. Run the install

From your Unit 7 materials folder, with the full path to your clone of
your issue's repo:

```
python3 skill/install.py --repo <path to your clone>
```

It works through these steps and prints a line for each:

0. **Checks first, changing nothing.** pr-precheck has to be at
   `~/.claude/skills/pr-precheck/`. It can be unfinished for now; the
   ship-gate says what's missing when it runs. The install also checks
   that repro-check and plan-check have the scopes for real repos from
   unit 6. If one doesn't, it prints a `cp` command. Run that from your
   Unit 6 materials folder (deleted it? Clone
   `https://github.com/codepath/ai301-unit6-starter` again).
1. **Copies the ship-gate's files** into `~/.claude/ship-gate/`.
2. **Adds the hook** to `~/.claude/settings.json`. It saves a dated
   backup of your settings first and leaves your voice guard's entry as
   it is. Running the install again doesn't add a second copy.
3. **Swaps pr-precheck's scope** for the scope for real repos, and
   keeps your old one as `scope.md.sandbox`.
4. **Creates `ship-manifest.md`** in the top folder of your clone,
   unless one is already there, and adds it and the three working files
   to `.git/info/exclude`. Without `--repo`, it prints the two commands
   to run from your clone instead.

If it stops, it says why and changes nothing. It stops when:

- pr-precheck isn't installed. Copy the `skill/` folder from your Unit 4
  materials to `~/.claude/skills/pr-precheck/`, then run the install
  again.
- `~/.claude/settings.json` isn't valid JSON, or its `hooks` part has
  the wrong shape. `python3 -m json.tool ~/.claude/settings.json` shows
  where it breaks. Fix it, then run the install again.
- One of its files is missing. Run it from your Unit 7 materials folder.

If `--repo` isn't the top folder of your clone, steps 1 to 3 still run,
and it stops at step 4. Run it again with the right path. Running it
twice is safe.

Then quit any open `claude` session. Claude Code only loads hooks when a
session starts.

## 2. Test the hook (expect two stops)

From your clone:

```
claude "run this command: gh pr create --help"
```

You should see two stops. Your voice guard from unit 6 stops it because
there's no PR description to check, and the ship-gate stops it because
there's no title or description for your pr-precheck to read. The
ship-gate's line starts with `ship-gate: STOP.` Two stops means both
hooks work. This test doesn't run any checks or use any course credit.

If the command runs instead:

- You're in a `claude` session that was open during the install. Quit
  it and start a new one.
- The hook wasn't added. Check that `~/.claude/settings.json` is valid
  JSON and that its `PreToolUse` list has an entry whose command names
  `ship-gate/check_gate.py`.

Only one stop? One hook is missing. If it's the voice guard's, finish
section 4 of INSTALL.md in your Unit 6 materials.

## 3. Run the ship-gate by hand

Run it on your branch before you open the PR. From your clone, on your
branch:

```
python3 ~/.claude/ship-gate/check_gate.py --branch --title "<your PR title>" --body-file pr_draft.md
```

It runs your manifest's checks, then your pr-precheck on your branch,
`plan.md`, `test_evidence.md`, and `pr_draft.md`. It either says
`ship-gate: PASS` or stops and says why. Each run takes a few minutes
and uses some course credit.

- `--branch` alone checks the branch you're on. `--branch NAME` checks
  another one.
- `--base NAME` sets the branch your PR goes into. The default is
  `main`, then `master`. Add it if the repo takes PRs on another branch,
  like `dev`.
- `--plan FILE` and `--evidence FILE` point at your plan and test
  evidence if they aren't `plan.md` and `test_evidence.md` in the top
  folder of your clone.
- `--issue URL` names the issue. You only need it if your description
  has no `Fixes #<issue number>` line. The ship-gate looks that number
  up on the repo your fork came from.

A pass lasts 30 minutes. If you open the PR through Claude Code within
30 minutes, with the same commit, base, title, description, manifest,
plan, and test evidence, the hook lets it through without running
everything again. Change any of those and it runs fresh.

Through the hook, a run has 29 minutes. Claude Code ends a hook at 30,
and an ended hook would let the PR through, so the ship-gate stops the
PR itself first. If your checks are slow, run the ship-gate by hand,
which has no time limit, then open the PR within 30 minutes.

## 4. What stops the ship-gate, and what to do

There's no way to skip the ship-gate. Every stop says what to fix.

- **No manifest, or it's still the template.** Fill in
  `ship-manifest.md` in the top folder of your clone. The comment at its
  top explains how. A check with no command or no source stops it too,
  and so does a row in the second table without a date and a reason.
- **A repo check failed.** It shows the command, its exit code, and the
  end of its output. Fix your code. If the check also fails on main,
  for a reason your fix doesn't touch, move it to the manifest's second
  table with a date and the reason instead of deleting it.
  - **`exited 127`** means the command wasn't found. The ship-gate runs
    each row in a fresh terminal at the top folder of your clone, not in
    your terminal where your virtual environment is active. Rewrite the
    row so it runs there: `uv run pytest` if the project uses uv,
    `.venv/bin/pytest` if you made a virtual environment, `npx eslint .`
    for an npm project.
  - **A "not found" error from inside the command** (like `jest` not
    found under `npm run test`) usually means the project's setup step
    hasn't run in this clone. Add that step (like `uv sync`,
    `.venv/bin/pip install -e ".[dev]"`, or `npm install`) as the first
    row of your manifest, with the same source.
  - **`timed out`** means the check ran for 25 minutes, or used up what
    was left of the hook's 29. Use a quicker command the project names,
    if it names one, or move the check to the second table with the
    reason. **"ran out of time"** means the whole run reached 29 minutes
    through the hook: run it by hand (section 3), then open the PR.
- **Your pr-precheck said reject.** It lists the checks your branch
  failed, in your rubric's words. Fix your branch. If a check asks for
  something this repo doesn't ask for, fix that check in your rubric
  instead, and say so in your Unit 7 Toolkit entry. A reject right after
  a pass means something changed (a commit, the base, the title, the
  description, the manifest, the plan, or the test evidence), or the
  pass is more than 30 minutes old. Fix what
  it names instead of running it again and hoping for a pass.
- **REFUSAL.** Your pr-precheck still has template files with nothing of
  yours in them, and the message names them. Fill them in yourself,
  then run the ship-gate again. Ask your TF if you need help finishing
  them.
- **pr-precheck's scope is still the sandbox one.** Run the install
  again. Step 3 swaps it.
- **No voice guide where the ship-gate looks.** It reads the guide your
  voice guard uses, at `~/.claude/voice-guard/voice-guide.md`. Finish
  section 3 of INSTALL.md in your Unit 6 materials.
- **It names a folder or repo you didn't expect.** The hook checks the
  folder your `claude` session started in, not the repo in the command.
  Start `claude` from inside your clone, or run the ship-gate by hand
  from there (section 3).
- **Other stops about your branch or setup.** You're on `main` instead
  of your branch, the branch has no changes yet, the clone isn't on any
  branch, the base branch can't be found (add `--base`), the `claude`
  command isn't found, a pr-precheck file is missing, or you used
  `gh pr create --web`. Each message says what to do.
- **pr-precheck couldn't finish its run.** Nothing was checked, so the
  PR didn't open. Run it again, and ask your TF if it keeps happening.
- **The ship-gate crashed.** Nothing was checked, so the PR didn't open.
  Run the ship-gate by hand on your branch (section 3) to see the full
  error, and show it to your TF.
- **It couldn't read the command.** Usually an apostrophe in a heredoc
  that writes the PR description. Write the description to a file
  first, then run `gh pr create --title "..." --body-file pr_draft.md`
  as a command of its own.
- **Your voice guard stopped a PR the ship-gate passed.** pr-precheck
  notes voice problems but doesn't reject over them unless your rubric
  says to. Your voice guard does stop on them. Fix the line it quotes in
  `pr_draft.md`, and run the command again.

## 5. Installing by hand

If the install script won't run on your computer, do the same steps
yourself. From your Unit 7 materials folder:

```
mkdir -p ~/.claude/ship-gate
cp skill/check_gate.py skill/hooks-settings.json skill/gate-manifest-template.md skill/scope-live.md skill/install.py skill/INSTALL.md ~/.claude/ship-gate/
cp ~/.claude/skills/pr-precheck/scope.md ~/.claude/skills/pr-precheck/scope.md.sandbox
cp skill/scope-live.md ~/.claude/skills/pr-precheck/scope.md
```

Then add the hook from `skill/hooks-settings.json` to
`~/.claude/settings.json`, the way you added your voice guard's in
unit 6. If there's no `hooks` key yet, paste in the whole block. If there
is, add the entry to its `PreToolUse` list. Replace `$HOME` in the
command with the full path to your home folder. Then, from the top
folder of your clone:

```
cp ~/.claude/ship-gate/gate-manifest-template.md ship-manifest.md
printf '%s\n' ship-manifest.md plan.md test_evidence.md pr_draft.md >> .git/info/exclude
```

Quit any open `claude` session, and run the test in section 2.

## 6. The log

Every run, by hand or through the hook, adds a dated entry to
`~/.claude/ship-gate/gate-log.md`: the repo, the branch, each check and
how it went, the result, and the reasons. A pass also records the
commits and fingerprints of the title, description, manifest, plan,
test evidence, and issue, which is how the hook knows a pass is still
good.

The log and your manifest stay on your computer, and nothing collects
them. Use them when you write your Unit 7 Toolkit entry, and again for
your unit 9 portfolio.
