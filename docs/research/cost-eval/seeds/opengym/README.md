# Seed: openGym

openGym is an open-source, self-hosted gym and body-weight tracker (AGPL-3.0-or-later): a Node API, a React web app that is also the phone app, native shells, watch apps and an MCP server. It was created after the executor model's training cutoff, so the model can't have seen its code (decisions.md, 2026-11-22). It serves milestone M2h (plan.md): **a brownfield test of changes whose relevant intent lives in another component of an existing codebase that wasn't built with LID.**

**The pin:** github.com/DuarteSantos8/openGym at `e4a68a9`. The subject is used locally for research only: nothing is pushed to the project, and no issues or pull requests are opened there. Its exercise media are licensed separately and never leave the local workspace.

**Status:** the change text is drafted and reviewed. GPT-6.2 Sol drafted the twelve changes and the owner's brief; Claude Fable and then GPT-6.2 Astra reviewed them, and both reviews' fixes are applied. The probes and their validation come next.

**How it runs:**
- **Two arms:** a bare agent on the pinned tree as it is, and LID Full on the same tree after one `/map-codebase` mapping per replicate. The mapping is reported as a one-time cost of adopting LID.
- **Forks:** each change is forked from its arm's start and run on its own, with the owner holding only that change's intent.
- **The owner** runs their own copy of openGym for a training group, and steers it lightly as a user and coach. They aren't openGym's author or maintainer, and know nothing about its internals. [brief.md](brief.md) is what they tell every developer.
- **Grading:**
  - new intent by probes against each arm's own build, in a container;
  - keeping by the project's existing test suites and by graded probes;
  - a failure of the grading instrument is recorded as missing, not as not met.

## What's here

- **Public:** this README and the owner's [brief](brief.md).
- **Private, in `hidden/`, until the runs that use them finish:**
  - the change script, oracle, probes, owner items and fixtures;
  - the drafts, prompts, reviews and edit log;
  - the right builds, one-sided builds and mutants used to validate the probes.

No openGym code and no detail of the changes appears outside `hidden/`.

## Hashes

Recorded here before any counted run.
