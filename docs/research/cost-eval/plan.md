# Plan and milestones

Status marks: `[x]` done, `[~]` in progress, `[ ]` not started. Spend on repetitions before breadth: three model families with one run each teach less than one family with five runs.

## M0: Start the notebook `[x]`

- `[x]` Find the issue (#75) and set up a working branch and draft pull request.
- `[x]` Collect three independent takes on the design and merge them into [design.md](design.md).
- `[x]` Survey the other SDD systems and the published research ([landscape.md](landscape.md), [sources.md](sources.md)).
- `[x]` Check whether existing Claude Code transcripts from real LID projects can give a cheap first answer. Result: they can't (see the 2026-11-11 entry in [log.md](log.md)).

## M1: Design the pilot `[ ]`

- `[ ]` Choose the pilot seed's domain, and write the product brief with its fixed external interface.
- `[ ]` Have a model from another family write the hidden oracle as narrative product prose, and review it.
- `[ ]` Write the change script: about 8 to 10 changes, including probe changes at different ages and two redirects (one change of mind, one clarification; one early, one late).
- `[ ]` Write the hidden tests: acceptance and regression tests for each change, audited against the oracle-gap rule.
- `[ ]` Write the user simulator's prompt for both policies, and the four-kind attention rubric.
- `[ ]` Write the arm configurations for the bare agent, cheap discipline, and LID Full.
- `[ ]` Decide where the harness lives and walk LID's arrow for it (an intent node under `docs/intent/`, then specs, then tests, then code).

## M2: Run the pilot `[ ]`

One seed, three arms, Claude Opus 5.5 and Sonnet 5.5 through `claude -p` at medium effort, three trajectories per arm, forked checkpoints, both user policies.

The pilot tests the instrument, so its runs don't count as evidence. It should answer these questions:

- Do the hidden tests tell the arms apart at all, or does the bare agent pass nearly everything (the ceiling check)? If it does, make the seed harder before spending more.
- How noisy are cost and fidelity between repeated runs?
- Does the user simulator behave believably? (The maintainer plays the user on a few trajectories to compare.)
- Can a judge sort touchpoints into the four attention kinds reliably?
- What does one trajectory cost, so that later stages can be budgeted?

## M2b: Check against SlopCodeBench `[ ]`

- `[ ]` Find out whether SlopCodeBench can run Claude Code with a plugin or a project instruction file.
- `[ ]` Run a few of its problems with a bare arm and a LID arm on Claude.

## M3: Pre-register `[ ]`

- `[ ]` Freeze [hypotheses.md](hypotheses.md), the primary comparison, the analysis plan, and the exclusion rules, and commit them before the first counted run.
- `[ ]` Choose the number of repetitions from the pilot's measured variance.

## M4: Add competitors `[ ]`

- `[ ]` Add arms for OpenSpec, Spec Kit (living-spec model), and cc-sdd, plus LID Scoped.
- `[ ]` Add a second, medium-sized seed.
- `[ ]` Publish the guide to running the eval on one's own system, and invite the maintainers of the compared systems to review their arms.

## M5: Add model families `[ ]`

- `[ ]` Run the OpenAI family (GPT-6.1 Sol and Terra) through opencode over OpenRouter, with a hard dollar cap set from the pilot's measured cost per trajectory.
- `[ ]` Decide whether to add a third family.

## M6: Larger and older projects `[ ]`

- `[ ]` A brownfield seed, onboarded by each arm.
- `[ ]` History replay from an open-source project.
- `[ ]` Measure design-level fidelity (HLD to LLD to EARS) for LID, and file a separate issue for any change to LID's skills that comes out of it.

## M7: Answer #75 `[ ]`

- `[ ]` Rewrite or support HLD Goal 3's "proportional cost" claim with graded evidence.
- `[ ]` Write what LID can tell users about cost: where it pays, where it doesn't, and how strong the evidence is. This may go in a users' guide or on the site, with every claim tracing to graded results.
