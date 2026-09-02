# Scope: where your pull request lives, and the rules of the wild

<!--
STAFF-COMPLETE. This is unit 4's real-world scope for pr-precheck,
shipped in the ship-gate package as the swap the install performs:
install.py copies this file over ~/.claude/skills/pr-precheck/scope.md
and keeps the sandbox copy beside it as scope.md.sandbox. The copy you
submitted in Module 1 stays untouched in your ai301-tools repo. Unit 4's
staff materials said this file would be everyone's swap in unit 7; this
is that swap.

Like every scope file, this one is the tool's field of view, live mode
only: the rubric (your rubric.md) decides whether a pull request is
READY; the scope decides which repositories the tool may grade at all,
and what the rules are where your pull request lands. In eval mode the
bundle is the whole world and this file is ignored. There is nothing to
edit.
-->

## Where your pull request lives

Any public repository. The sandbox is behind you: your pull request
now lands in front of real maintainers, and asking a stranger to
spend review time on your work is exactly what this tool exists to
make safe.

## Rules of the wild

The Path Review house rules do not travel. Out here:

- **The repo's conventions outrank the course's.** Branch names,
  commit style, PR size, target branch: read the repo's contributing
  docs and follow those. The `fix/<issue>-<slug>` habit is a good
  default only where the repo states nothing.
- **From your fork, always.** You have no push access to a stranger's
  repository: the branch you ship lives on your fork of it, and the
  pull request points from there at the branch the repo's contributing
  docs name as the target (its default branch unless they say
  otherwise; some repos take pull requests on `dev`).
- **One PR per issue is now a courtesy to reviewers, not a course
  rule.** If a maintainer asks you to split or combine work, the
  maintainer is right.
- **A parallel PR is a real cost.** In the sandbox, classmates on one
  issue was coordination; out here, check the issue's linked PRs
  before opening yours. If someone's fix is already up, review or
  test theirs instead of racing it.
- **Deviations get reported upstream, not just recorded.** If your
  diff materially departs from the plan you posted on the issue, say
  so in the PR description AND the issue thread. A maintainer who
  read plan A should never be surprised by diff B.
- **Disclosure follows the repo's stated policy, always.** Your
  coursework is AI-assisted by design; where a repo asks for AI-use
  disclosure, the disclosure appears, in your own words, every time.
  Where a repo bans AI-assisted contributions outright, that repo is
  out of scope for course work: pick another issue.
