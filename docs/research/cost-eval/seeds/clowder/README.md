# Seed: Clowder

Clowder is the maintainer's public Rust terminal game ([github.com/jszmajda/clowder](https://github.com/jszmajda/clowder)), built entirely under LID. It serves one narrow purpose here: **a falsification test of "LID pays off once a codebase is larger than the agent can hold"** (see [design.md](../../design.md), "Later seeds and variants", and milestone M2c in [plan.md](../../plan.md)). Its non-test source is about 270k tokens: it fits in a 1M-token context window but not in a 200k one.

**Status:** prepared, not yet run.

- **The changes:** twelve, drafted by GPT-6.1 Sol in two rounds. Claude Fable and then GPT-6.2 Astra reviewed them, and both reviews' fixes were applied.
- **The probes:** 43, drafted by GPT-6.2 Sol and revised after Astra's review. Their setups were computed once on the untouched snapshot and frozen as fixtures.
- **Salience:** the four-model panel rated the 19 askable items with weighted kappa 0.78.
- **Choices for the pilot** (2026-11-18, recorded in [decisions.md](../../decisions.md)):
  - every change keeps its relevant intent within one crate; cross-crate changes are added later if the pilot shows room;
  - change 10 is Fable's reversal;
  - the items Fable wrote stand.

**How it runs:**
- **Forks:** each change is forked from Clowder's final snapshot and run independently, with the owner holding only that change's intent.
- **Three arms:** bare on a stripped repository (no docs or spec IDs, tests thinned to the ratio bare agents wrote on BenchTime), bare on the full repository, and LID Full.
- **Two windows:** 1M and 200k.
- **Grading:**
  - Keeping is graded by held-out existing tests.
  - New intent is graded by probes run against each arm's own API, on a checkout with docs and spec IDs removed.
  - A failure of the grading instrument is recorded as missing, not as not met.
  - Change 5 reports a symptom of a small bug planted in that change's snapshot.

## What's here

- **Public:** this README and the [brief](brief.md) the owner works from.
- **Private, in `hidden/`, until the runs that use them finish:**
  - the oracle, change script, probes, owner items and fixtures;
  - the planted bug's patch;
  - the drafts, reviews and edit log.

## Hashes

| Version | Date | File | SHA-256 |
|---|---|---|---|
| 1 | 2026-11-18 | `hidden/oracle.md` | `746463a568c5b6884bdcda1d013747a9f3b92263468758e78a02c72db589040f` |
| 1 | 2026-11-18 | `hidden/change-script.md` | `ee2dba17f353795b732cfcadd5c16f5a91235bf08c310990ef35e48f4e5c718b` |
| 1 | 2026-11-18 | `hidden/probes.md` | `040f1c35350b1936f5aabff16589da3cf97691efd8b8bd57c652b1423195c8ee` |
| 1 | 2026-11-18 | `hidden/owner-items.json` | `19b9695c6e0ba9b1d646851e8c33c4fda463d62de6fceb994058c9959465a979` |
| 1 | 2026-11-18 | `hidden/kept-assertions.json` | `29e0ee90a601b3259eda2764239de9942fd3cf26901a5644e68238658365b144` |
| 1 | 2026-11-18 | `hidden/patches/change-05.diff` | `9833d6a4d728e1412436044d3e2ac2ccb768493339edf3225d63269f2f6b405e` |
| 1 | 2026-11-18 | `hidden/fixtures/grader-fixtures.md` | `5c691b53b703f4b4a2f9d9756eacf29dc0f8861c8991c2df007b7ff857bd98a2` |
| 2 | 2026-11-18 | `hidden/probes.md` | `0a6031e5b3d3c02e92cbbe4cf7b2b67093b939d28d8f6cf8abfe4d0da6f46668` |
| 2 | 2026-11-18 | `hidden/kept-assertions.json` | `0ec0f46e8a365bfb1eeaee8bd371f3a6bf85b6e9061cebbd842085cae62bd348` |
| 3 | 2026-11-18 | `hidden/probes.md` | `f404d2f7988da87396439d4ce9d0d914cb6dafd154f782d3c656261e500cf555` |
| 2 | 2026-11-18 | `hidden/fixtures/grader-fixtures.md` | `bfcc6675b7642427e653bd4923761237457b96044c16df823b085d948c94dc4f` |
| 4 | 2026-11-18 | `hidden/probes.md` | `71505a10e72a10db053ef6d599efc15b0a12be7fe12616d5283258eeb4d3eaff` |
