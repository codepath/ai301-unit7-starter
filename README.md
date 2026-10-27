# AI301 Unit 7 materials: the ship-gate

The ship-gate is a hook that runs before Claude Code opens a pull
request. It runs the project's own checks from a manifest you write,
then your pr-precheck from unit 4, and stops the PR if anything fails.

The steps are on the Unit 7 **Assignment** tab in the course portal.
This repo holds the files those steps use.

## Get it

```
git clone https://github.com/codepath/ai301-unit7-starter.git
```

Or click **Code**, then **Download ZIP**, on this page. Then follow the
Assignment tab, starting with the install:

```
python3 skill/install.py --repo <path to your clone>
```

You need Python 3.8 or newer (`python3 --version`).

## What's here

- `skill/install.py`: the install. It copies the ship-gate into
  `~/.claude/ship-gate/`, adds the hook to `~/.claude/settings.json`
  after saving a backup, swaps pr-precheck's scope for the scope for
  real repos, and creates `ship-manifest.md` in your clone.
- `skill/INSTALL.md`: what the install does, how to test the hook, how
  to run the ship-gate by hand, and what to do when it stops.
- `skill/check_gate.py`: the ship-gate itself. Claude Code runs it
  before `gh pr create`, and you can run it by hand with `--branch`.
- `skill/gate-manifest-template.md`: the starting point for your
  `ship-manifest.md`, the list of the project's checks that must pass.
- `skill/scope-live.md`: pr-precheck's scope for real repos.
- `skill/hooks-settings.json`: the hook entry the install adds.

You write no code this unit. What you write is your manifest, plus any
fixes your rubric needs once it checks a real branch.

There's no eval set this unit, because the ship-gate only runs on real
branches.
