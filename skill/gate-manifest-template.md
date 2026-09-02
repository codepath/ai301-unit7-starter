# Ship manifest: <owner/repo>

<!--
THE GATE MANIFEST (the unit-7 hole). This file is your judgment about
which of the target repo's OWN checks must pass before a pull request of
yours goes out. Staff never write it; the gate runs it. It lives at the
root of your clone as ship-manifest.md and never ships: keep it out of
your diff with

  echo ship-manifest.md >> .git/info/exclude

(the mechanism your CLAUDE.local.md already uses). The evidence copy goes
to your ai301-tools repo as ship-gate/gate-manifest.md.

WHERE THE COMMANDS COME FROM. Mine them, never invent them: the repo's
contributing guide (CONTRIBUTING.md, or wherever the repo keeps it: a
docs/contributing.rst, a README section; name the file you read), its
CI config under .github/workflows, and the Build and test commands
section of your own CLAUDE.local.md, which you wrote in unit 6 for
exactly this moment. Every row names its source in the third column. A
check with no source is a guess, and the gate stops on it.

WRITE THE FRESH-SHELL FORM. The gate runs each command in a fresh shell
at the clone root, on your machine, the same on both doorways: not in
your activated terminal. So the guide's `pytest` after a venv activate
is written here as the form that runs cold, `uv run pytest` or
`.venv/bin/pytest`; its `eslint` as `npx eslint .`; whichever the
repo's own setup makes true. The check is still mined and the source
still names where it came from; `command not found` is the sign a row
was written for your terminal instead. If the repo's checks need a
setup step first (`npm install`, `uv sync`, `pip install -e .[dev]`),
that step is your first must-pass row, sourced to the same guide.

UNDER A PAGE. A manifest is a judgment, not a CI mirror: the two to four
checks a reviewer would run before trusting your branch, not every
matrix cell CI runs. Commands run from the clone root, in table order,
exactly as written. The first failure stops the ship, and the gate
quotes the command and the tail of its output. Put the fastest checks
first; a suite that would outlast the session is a judgment call, the
repo's quick subset if its docs name one, or a dated exclusion with the
reason.

THE DATED-EXCLUSION RULE. A check you decide must not gate this ship
is excluded, never left out, with the date and the reason: red on main
for reasons your PR never touches; a check you cannot run here (a
toolchain or a service you lack, named); a check that rewrites tracked
files and would dirty your diff. The reason column says which. Silence
is never an option: an excluded check is a recorded judgment; a check
you simply left out is a hole. Re-check each exclusion before you ship;
a fixed main (or a toolchain you since installed) retires it.

A repo whose docs name no checks at all gets ONE row in the first table
whose command is the single word none and whose source says where you
looked.

Replace <owner/repo> in the title with the repo. Delete this whole
comment once the tables are filled: the manifest carries judgment, not
scaffolding.
-->

## Must pass before a ship

| Check | Command | Source |
|---|---|---|
|  |  |  |

## Excluded, with a dated reason

| Check | Command | Since | Why it does not gate this ship |
|---|---|---|---|
|  |  |  |  |
