# Ship manifest: <owner/repo>

<!--
Your ship manifest. Before your PR opens, the ship-gate runs every
command in the first table, in order, and stops the PR if one fails.
You choose the checks, and the ship-gate runs them.

1. Title. Replace <owner/repo> above with the original repo's owner
   and name from your issue's link, like psf/requests, not your fork.

2. First table. List the two to four checks the project asks you to run
   before a PR, usually its tests and lint. Take each one from the
   project instead of making one up, and write where you found it in
   the Source column: CONTRIBUTING.md, a CI file in .github/workflows/,
   or the Build and test commands in your CLAUDE.local.md. If the
   checks fail in a fresh terminal until a setup step runs (like
   `uv sync`, `.venv/bin/pip install -e ".[dev]"`, or `npm install`),
   make that step the first row.

3. Commands. The ship-gate runs each command in a fresh terminal at the
   top folder of your clone, without your virtual environment. Write
   the form that works there: `uv run pytest` if the project uses uv,
   `.venv/bin/pytest` if you made a virtual environment, `npx eslint .`
   for an npm project. To test one, open a new terminal, cd into your
   clone without activating anything, and run it.

4. Second table. A check that fails for a reason your fix doesn't touch
   goes here, with today's date and the reason. The usual reasons: it
   already fails on main, it needs a tool or service you can't run
   here, or it changes files when it runs (like a formatter) and would
   add them to your PR. Move a check here instead of deleting it, so
   your pr-precheck can see what you skipped and why. If nothing goes
   here, leave the table empty.

If the project names no checks at all, write one row in the first table
with the command none, and say in Source where you looked.

This file stays on your computer. The install added it to
.git/info/exclude, so it never goes into your PR. When you're done,
delete this comment.
-->

## Must pass before a ship

| Check | Command | Source |
|---|---|---|
|  |  |  |

## Excluded, with a dated reason

| Check | Command | Date | Why it doesn't count against this PR |
|---|---|---|---|
|  |  |  |  |
