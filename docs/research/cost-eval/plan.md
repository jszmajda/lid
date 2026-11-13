# Plan and milestones

Status marks: `[x]` done, `[~]` in progress, `[ ]` not started.

**Principles:**

- **Spend on repetitions before breadth.** Three model families with one run each teach less than one family with five runs.
- **Claude roles run on the maintainer's subscription.** Real dollars go only to OpenRouter, for authorship, a small cross-family grader sample, and the later stage with other executor families ([design.md](design.md), "Budget").
- **Every pilot stage has a stopping criterion.** If a stage fails its threshold, fix the instrument before spending more.

## M0: Start the notebook `[x]`

- `[x]` Find the issue (#75) and set up a working branch and draft pull request.
- `[x]` Collect three independent takes on the design and merge them into [design.md](design.md).
- `[x]` Survey the other SDD systems and the published research ([landscape.md](landscape.md), [sources.md](sources.md)).
- `[x]` Check whether existing Claude Code transcripts from real LID projects can give a cheap first answer. Result: they can't (see the 2026-11-11 entry in [log.md](log.md)).
- `[x]` Collect candidate projects from three model families, and choose the pilot seed (BenchTime) and the second seed (ReleaseDesk).
- `[x]` Get a fresh review of the plan, and fold the adopted changes into the design.

## M1: Build the pilot's instrument `[ ]`

**Seed materials.** These are written by models from families other than Claude, reviewed by the maintainer, and hashed before any counted run.

- `[x]` Write BenchTime's product brief in the owner's words, with no fixed interface. It fixes only the stack, one start command, one data location, and reading time from the system clock. A first version with a full interface contract was drafted and then set aside on 2026-11-12. The owner-voice version was reviewed and accepted on 2026-11-13.
- `[x]` Write the hidden oracle as narrative product prose, with a disclosure point for every item: stated, askable, recognised on sight, emerging at change k, or realised on a symptom. Drafted by Sol, edited, and accepted on 2026-11-13.
- `[x]` Write the change script: about 10 changes covering the change types, two redirects for testing the plumbing, at least one emerging item, and one probe request that makes sense at any age. Drafted by Sol, edited, and accepted on 2026-11-13.
- `[x]` Write the grading rubric. Each requirement is a checkable statement with its disclosure, the change that introduced it, and the change that retires it, if any. This is the oracle's item table, accepted on 2026-11-13.
- `[x]` Write the probes: one or more per item, each a scenario and an expected observation in terms of operations ([design.md](design.md), "Grading protocol"). Sol drafts them, the main session edits them, and the maintainer reviews them. They are kept hidden with the oracle. Drafted, edited, and reviewed by Claude Fable in the maintainer's place on 2026-11-13: 92 probes, recorded as version 1.

**Simulator and graders:**

- `[ ]` Write the user simulator's prompt for the three policies, with its answer record, its rules for broad questions and for silence, and a leak audit.
- `[ ]` Write the touchpoint rubric for the six kinds of request, and the classifier prompt.
- `[ ]` Calibrate execution and judgment on Haiku 5.5 through `claude -p`, using seeded violations and labelled pairs in both directions, and fall back to Sonnet 5.5 if Haiku misses the threshold. Measure test-retest flips at both steps.
- `[ ]` Write the interface-extraction prompt and its fixed template, and check it on a few builds: does the reference let a grader exercise every operation, without describing intended behaviour? A draft is in [plumbing/](plumbing/README.md) and worked on one build. It needs to run under the fake clock, so it doesn't wait out real time.
- `[x]` Work out how the level 1 grader reaches the running software without seeing its source: through `gt`, a harness tool that works from inside the software's container and writes the execution log. Its command operation still has to be kept away from the source.

**Arms and harness:**

- `[ ]` Write the configurations for the bare agent, cheap discipline, and LID Full.
- `[x]` Write the isolation recipe: each executor session runs in a Linux container from [plumbing/executor.Dockerfile](plumbing/executor.Dockerfile), with the arm's configuration in its own volume, the maintainer's subscription token, and a check of each session's start-up record. Accepted by the maintainer on 2026-11-13.
- `[x]` Check the headless plumbing under `claude -p` (see [log.md](log.md), 2026-11-13): LID's phase stops; questions answered by stopping and resuming; controlling time from outside with `libfaketime`; resetting by starting from an empty data location; and whether an extraction reference lets a Haiku grader run probes against an interface it hasn't seen.
- `[ ]` Check plan-mode approval headless, for the cheap-discipline arm.
- `[ ]` Write the rule that tells "done" from "waiting", and check it against labelled transcripts.
- `[x]` Check that the recorded token usage includes subagent sessions.
- `[ ]` Decide where the harness lives, and walk LID's arrow for it (an intent node under `docs/intent/`, then specs, then tests, then code).

## M2: Run the pilot, in stages `[ ]`

The pilot tests the instrument, so its runs don't count as evidence. Each stage has a threshold. The thresholds below are proposals and get settled before the stage runs.

| Stage | What runs | Rough size | Go on only if |
|---|---|---|---|
| 0. Plumbing | All three arms on Sonnet 5.5: a build plus two changes | About 9 sessions | Every arm completes, isolation holds, stops and questions work, and usage records are complete |
| 1. Ceiling | Bare arm only, on Opus 5.5: the full script, 2 trajectories | About 20 sessions | The bare arm meets no more than about 85% of requirements in force. If it meets more, harden the seed before going on |
| 2. Variance | All three arms on Sonnet 5.5, 3 trajectories each, one policy, with identical-probe forks; plus the A/A check and the positive control | About 120 sessions | Graders agree with the maintainer's spot checks on at least about 90% of verdicts; test-retest flips stay under about 5%; the positive control shows worse fidelity; the A/A check shows no difference |
| 3. Second tier and policy | LID Full and cheap discipline on Opus 5.5, and under a second user policy | About 50 sessions | Variance is low enough to size the counted runs |

In total that is about 200 sessions, against about 700 for the pilot as first drafted.

Alongside the stages:

- `[ ]` The maintainer plays the owner on a few trajectories, to calibrate the bounded-attention policy and check the simulator.
- `[ ]` Two people label about 100 requests to check the touchpoint rubric (target kappa 0.7 or better).
- `[ ]` A small cross-family grader sample (GPT-6.1 Terra) measures self-preference.

## M2b: Check against SlopCodeBench `[ ]`

- `[ ]` Find out whether SlopCodeBench can run Claude Code with a plugin or a project instruction file.
- `[ ]` Run a few of its problems with a bare arm and a LID arm on Claude.

## M3: Pre-register `[ ]`

- `[ ]` Draft the competitor arm configurations (OpenSpec, Spec Kit with its living-spec model, cc-sdd), and invite their maintainers to review them, and the design, before the freeze.
- `[ ]` Freeze [hypotheses.md](hypotheses.md), the primary comparison, the analysis plan, the equivalence margin, and the exclusion rules, and commit them before the first counted run.
- `[ ]` Choose the number of repetitions from the pilot's measured variance.

## M4: LID against itself, and a larger project `[ ]`

- `[ ]` Run LID Scoped, and LID with and without the arrow-maintenance overlay (H8).
- `[ ]` Add a medium size tier, near the executor's context window.
- `[ ]` Add ReleaseDesk as the second seed.
- `[ ]` Run the single-session and memory-on ablations.
- `[ ]` Add repairs, with delayed, symptom-only reports confirmed by a replayed reproduction.

## M5: Add competitors `[ ]`

- `[ ]` Run OpenSpec, Spec Kit, and cc-sdd with the configurations their maintainers reviewed.
- `[ ]` Publish the guide to running the eval on one's own system.

## M6: Add model families `[ ]`

- `[ ]` Run the OpenAI family (GPT-6.1 Sol and Terra) through opencode over OpenRouter, with a hard dollar cap set from the pilot's measured tokens per trajectory.
- `[ ]` Decide whether to add a third family, and a Haiku 5.5 tier.

## M7: Larger and older projects `[ ]`

- `[ ]` A brownfield seed, onboarded by each arm.
- `[ ]` History replay from an open-source project.
- `[ ]` Relayed briefs, where an intermediary product manager loses and reinterprets some intent.
- `[ ]` Measure design-level fidelity (HLD to LLD to EARS) for LID, and file a separate issue for any change to LID's skills that comes out of it.

## M8: Answer #75 `[ ]`

- `[ ]` Rewrite or support HLD Goal 3's "proportional cost" claim with graded evidence.
- `[ ]` Write what LID can tell users about cost: where it pays, where it doesn't, and how strong the evidence is. This may go in a users' guide or on the site, with every claim tracing to graded results.
