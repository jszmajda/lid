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

- `[x]` Write the user simulator's prompt for the three policies, with its answer record, its rules for broad questions and for silence, and a leak audit. Drafted on 2026-11-14 and reworked from Claude Fable's review (kept privately in `seeds/benchtime/hidden/fable-simulator-review.md`). It passed the leak threshold: 15 scenarios × 10 runs, no confirmed leaks.
- `[ ]` Write the touchpoint rubric for the six kinds of request, and the classifier prompt.
- `[x]` Calibrate execution and judgment on Haiku 5.5 through `claude -p`, using seeded violations and labelled pairs in both directions, and fall back to Sonnet 5.5 if Haiku misses the threshold. Measure test-retest flips at both steps. Done on 2026-11-14: Haiku judged inconsistently (9% flips), so Sonnet judges; four seeded violations caught; a whole-pipeline retest agreed on 44 of 44; Claude Fable agreed with 35 of 36 sampled verdicts. Labelled pairs are still to do.
- `[~]` Write the interface-extraction prompt and its fixed template, and check it on a few builds: does the reference let a grader exercise every operation, without describing intended behaviour? In [harness/prompts/extraction.md](harness/prompts/extraction.md); it writes a start spec too, and is told not to wait for time to pass instead of running under the fake clock. It worked on the three stage 0 builds; references haven't been spot-checked against the code yet.
- `[x]` Work out how the level 1 grader reaches the running software without seeing its source: through `gt`, a harness tool that works from inside the software's container and writes the execution log. Its command operation still has to be kept away from the source.

**Arms and harness:**

- `[x]` Write the configurations for the bare agent, cheap discipline, and LID Full ([harness/arms/](harness/arms/)).
- `[x]` Write the isolation recipe: each executor session runs in a Linux container from [plumbing/executor.Dockerfile](plumbing/executor.Dockerfile), with the arm's configuration in its own volume, the maintainer's subscription token, and a check of each session's start-up record. Accepted by the maintainer on 2026-11-13.
- `[x]` Check the headless plumbing under `claude -p` (see [log.md](log.md), 2026-11-13): LID's phase stops; questions answered by stopping and resuming; controlling time from outside with `libfaketime`; resetting by starting from an empty data location; and whether an extraction reference lets a Haiku grader run probes against an interface it hasn't seen.
- `[x]` Check plan-mode approval headless, for the cheap-discipline arm. It works: a turn in plan mode ends by presenting the plan, and resuming in the normal mode builds it.
- `[~]` Write the rule that tells "done" from "waiting", and check it against labelled transcripts. The simulator classifies every stop (completion report, approval request, questions, or a stop partway), and a completion report it has nothing to say about ends the change. Not yet checked against labelled transcripts.
- `[x]` Check that the recorded token usage includes subagent sessions.
- `[x]` Decide where the harness lives: beside the notebook in `harness/`, outside LID's arrow during the spike. Decided by the maintainer on 2026-11-13. It moves into the arrow if its results come to back a claim LID ships; M8 is the natural point to decide.
- `[~]` Build the trajectory runner, then grading with replay, then reports, with tests where a quiet bug would bias the results. The runner and grading work (103 tests); grading costs about $0.70 per checkpoint, so replay waits. Still to build: prior-data probes, probe-change forks, and reports.

## M2: Run the pilot, in stages `[ ]`

The pilot tests the instrument, so its runs don't count as evidence. Each stage has a threshold. The thresholds below are proposals and get settled before the stage runs.

| Stage | What runs | Rough size | Go on only if |
|---|---|---|---|
| 0. Plumbing (passed 2026-11-14) | All three arms on Sonnet 5.5: a build plus two changes | About 9 sessions | Every arm completes, isolation holds, stops and questions work, and usage records are complete |
| 1. Ceiling (ran 2026-11-14: 90% met, didn't pass) | Bare arm only, on Opus 5.5: the full script, 2 trajectories | About 20 sessions | The bare arm meets no more than about 85% of requirements in force. If it meets more, harden the seed before going on |
| 2. Variance | All three arms on Sonnet 5.5, 3 trajectories each, one policy, with identical-probe forks; plus the A/A check and the positive control | About 120 sessions | Graders agree with the maintainer's spot checks on at least about 90% of verdicts; test-retest flips stay under about 5%; the positive control shows worse fidelity; the A/A check shows no difference |
| 3. Second tier and policy | LID Full and cheap discipline on Opus 5.5, and under a second user policy | About 50 sessions | Variance is low enough to size the counted runs |

In total that is about 200 sessions, against about 700 for the pilot as first drafted.

Alongside the stages:

- `[x]` Build attention and recall into the owner (design.md, "Attention and recall"), reviewed by Claude Fable first, with tests for the draws. Done 2026-11-16: 212 tests; Fable reviewed the design and the code.
- `[x]` Rate salience for every askable item in both seeds, blind, with four model families; report weighted kappa; freeze with a hash. Done 2026-11-16: pooled weighted kappa 0.60, below the 0.7 bar, so median tiers with the shortfall recorded.
- `[ ]` Check the owner: labelled judgments on about 100 replayed stops, replays of logged stops, stimuli modelled on published experiments, and the constants sweep. A maintainer's play-through is a smoke test only.
- `[ ]` Run the guessability panel on BenchTime's latent items, so both seeds report latent fidelity by band.
- `[ ]` Two people label about 100 requests to check the touchpoint rubric (target kappa 0.7 or better).
- `[ ]` A small cross-family grader sample (GPT-6.1 Terra) measures self-preference.

## M2c: Clowder, the falsification test at scale `[ ]`

See design.md, "Later seeds and variants". Feasibility is checked:
- Rust 1.89 plus `procps` builds and passes all 1,753 tests on the 2-CPU VM, in about 45 seconds for an edit-rebuild-test cycle;
- a hosts block stops GitHub while the model API stays reachable;
- `CLAUDE_CODE_DISABLE_1M_CONTEXT=1` gives a 200k window.

- `[ ]` An executor image with Rust 1.89 and `procps`; GitHub blocked and web tools denied for Clowder runs; a window setting per run.
- `[ ]` The three repository variants from the final snapshot: stripped (tests thinned to a 0.6 test-to-source ratio, at random across modules), full, and LID. A held-out slice of tests is removed from all three.
- `[ ]` Twelve changes in the owner's voice, drafted by GPT-6.1 Sol and reviewed by Claude Fable, each with new intent written outside the existing specs, its predicted direction, and its dispersion class.
- `[ ]` A fork runner that starts each change from a variant snapshot, and grading for a Rust library:
  - held-out tests for keeping;
  - probes for new intent, written against each arm's own API after interface extraction;
  - the existing tests each arm edited or deleted;
  - intent reach and context telemetry.
- `[ ]` The pilot: bare stripped first as a ceiling check, then all three arms at both windows.

## M2d: The growth test `[x]` (banked as a pilot)

Banked as a pilot on 2026-11-21: the instrument gate passed and the trial ran (bare and LID through change 20), but at change 20 bare's whole system was about 25k tokens, too small to exercise the scale and rot mechanisms. Neither hypothesis was tested; the full run was not started.

ReleaseDesk grown by each arm through 40 changes (design.md, "The growth test").

- `[ ]` Draft the thirty new changes with Sol, blind to the hypotheses: six course changes per block, a reliance change for each, three re-reversals, and new oracle rows with disclosure points and lifetimes.
- `[ ]` Review by Claude Fable and GPT-6.2 Astra, and apply their fixes; record each change's predicted direction and intent distance.
- `[ ]` Rate the new askable items with the salience panel; draft and review the probes, including flip checks for every retirement and reversal.
- `[ ]` Build the harness pieces: the one-line arm, course-change forks, the drift floor, intent from tests and docs at checkpoints (with its baseline, stripped variant and positive control), the stale-intent audit, and fidelity per owner-hour.
- `[ ]` Trial: one bare and one LID trajectory through change 20. Gate: bare shows stale claims after course changes, the positive control fires, and flip checks behave.
- `[ ]` Fix X and Y for the predictions from the trial's spread, and record them.
- `[ ]` Full run: bare ×5 (plus the drift floor), LID Full ×5, one-line bare ×3.

## M2e: The checklist arm and the cost of rework, a first look `[ ]`

On ReleaseDesk's growth seed through change 20, paired with the trial's bare and LID runs (replicate g-r1).

- `[x]` The checklist arm: a bare agent whose AGENTS.md asks it to keep a spec of the system's obligations and ask the owner about anything unsettled (landscape.md, "The checklist arm"). One trajectory through change 20 on replicate g-r1, with the same forks, checkpoints, intent readers and stale-intent audit as the trial's replicate 1.
- `[x]` Repair forks: for every latent rule a run missed at changes 10 and 20, fork from that snapshot, deliver the owner's report of the wrong behaviour, and measure what the fix costs and whether it holds without breaking other rules. For all three runs, from their existing snapshots.
- `[x]` From data already collected: module count and coupling at every snapshot; LID's spend by phase; owner reading by review depth.
- `[ ]` Then decide: if the checklist arm lands near LID on latent rules at a fraction of the cost, add replicates 2 and 3 for all three arms (the trial's runs are replicate 1).

## M2f: Clowder with cross-crate changes `[ ]`

The scale question, recast: agents search a codebase rather than load it, so "too big to hold" means "the intent you need isn't near the code you're editing". Clowder has two crates of similar size (core simulation and terminal UI), much like an app and its backend.

- `[ ]` Draft about twelve new changes with Sol, blind to the hypotheses. Most are requested on one crate's surface while the rule they must respect lives in the other; a few same-crate changes serve as controls. Each records its intent distance before any run.
- `[ ]` Review by Claude Fable and GPT-6.2 Astra; record predicted directions; draft and review probes, including probes and held-out tests for intent held in the other crate; repair reports for every item.
- `[ ]` Null-arm check of the grading on the untouched snapshot.
- `[ ]` Runs: bare on the stripped repository and LID Full, three forks per change each, at the 1M window; repair forks for every miss, measuring rounds and cost to fix.

## After the growth test: ideas to review with the maintainer `[ ]`

Suggested by Onagh and Nayebi's specification-explicitness paper (sources.md, "Specification explicitness"). The maintainer asked that they change nothing in the growth test, and be reviewed with her once it finishes.

- `[~]` **A checklist arm** (pulled forward into M2e on 2026-11-21). A few lines of AGENTS.md: before each change, write or update a spec listing functional requirements, constraints, invariants, negative requirements, edge cases and tie-breaking rules; ask the owner about anything unsettled; update the spec before the code. No design-doc hierarchy, no `@spec` links, no phase stops.
  - If it gets most of LID's latent-item lead at a fraction of the cost and owner reading, that answers where LID isn't worth the spend. If LID beats it on reliance forks and rot, that isolates the value of linking and the cascade.
  - It leans on the simulated owner's broad-question rules.
- `[ ]` **Tag each oracle item by kind of obligation** (invariant, negative requirement, edge case, tie-break, constraint, assumption), done blind, and report fidelity by kind. This gives H2 a second axis beyond change type, and shows which kinds LID's questions bring out.
- `[ ]` **A calibration measure,** for the unmeasured "how easy changes are to review":
  - agent overclaiming: what each completion report says was handled, against the graded verdicts;
  - a cold reviewer model that sees the diff and the arm's artifacts, predicts which items are met, and is scored against the grader.

  Not the simulated owner, whose calibration would only measure the simulator.
- `[ ]` **Report keeping as two numbers:** how often a change breaks anything, and how much it breaks. One keeping rate hides a more-but-shallower tradeoff.

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
