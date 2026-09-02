# AI301 Unit 7 starter: the ship-gate

Materials for Unit 7 of AI301 (shipping it). This repo holds the
unit's runnable package: the ship-gate, one installable unit that puts
your own pr-precheck, plus a gate manifest you write, on your
PR-opening doorway. All instructions live on the course portal
(Overview, Activity, and Check-In tabs for Unit 7); this repo is the
package those pages tell you to install.

## What's here

- `skill/INSTALL.md`: what the install does step by step, the wiring
  canary (expect two stops), the manual doorway, the fail-closed list
  with the route out of each stop, the manual install fallback, and
  the evidence trail.
- `skill/install.py`: the packaged install (staff-complete; you write
  no code). A preflight that changes nothing, the package copied into
  `~/.claude/ship-gate/`, the hook entry merged into your Claude Code
  settings with a dated backup written first, pr-precheck's scope
  swapped to the real-world one with the sandbox copy kept beside it,
  and `ship-manifest.md` placed at your clone root and kept out of
  your diff.
- `skill/check_gate.py`: the gate runner, both doorways. Hook mode
  gates `gh pr create`; manual mode (`--branch`) is the same gate for
  browser ships and dry runs. A manual pass from the last 30 minutes
  carries to the hook doorway when the package is identical (same
  commit, title, body, and manifest).
- `skill/hooks-settings.json`: the hook entry the install merges into
  `~/.claude/settings.json`.
- `skill/gate-manifest-template.md`: THE HOLE. Your judgment about
  which of the target repo's own checks must pass before a ship, one
  row each with its source line; exclusions carry a date and a
  reason, never silence. It lives at your clone root as
  `ship-manifest.md`, out of your diff via `.git/info/exclude`.
- `skill/scope-live.md`: the real-world scope that replaces
  pr-precheck's unit-4 sandbox scope (the swap unit 4's staff
  materials were written for; your previous scope is kept as
  `scope.md.sandbox`).

## Install

The Activity tab has the full steps and the warnings. In short: get
this repo onto your machine (`git clone
https://github.com/smoran02/ai301-unit7-starter.git`, or Code then
Download ZIP on the repo page), then, with the path to your target
repo's clone:

```
python3 skill/install.py --repo <path to your clone>
```

Then start a fresh `claude` session; settings load at startup. The
install is an overlay onto what you already own: it adds the gate,
swaps pr-precheck's scope, and touches nothing else. Every file of
your pr-precheck as you wrote it, your voice-guard and its guide, the
scout, and every Module 1 skill folder stay yours and untouched.

## No eval/ here, on purpose

Unit 7 ships no eval set and no harness. The gate is a live-mode-only
seam: nothing invokes it in eval mode, and it never reads or changes
pr-precheck's eval mode or the unit-1 and unit-4 harness interfaces.
