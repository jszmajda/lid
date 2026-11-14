# Research notebook: what LID costs, compared with other ways of working

**Status: running the pilot. No counted runs yet.** Last updated 2026-11-14.

## The question

People who try LID ask what it costs, and they most often ask how it compares with other spec-driven development (SDD) systems such as OpenSpec, GitHub Spec Kit, and BMAD. LID can't answer either question today. Issue [#75](https://github.com/jszmajda/lid/issues/75) records the gap. LID has never stated what walking the arrow costs. HLD Goal 3's claim that the adoption modes let teams use LID "at proportional cost" has no evidence behind it. Nobody knows the project size or change count at which walking the arrow starts to pay for itself.

The working hypothesis is that LID costs more to build a system and less to change it later. A change made months later should find the intent it needs in the design docs and specs, so it should cost less and break less than it would where that intent lives only in code. The hypothesis is about long-term maintenance, especially of complex systems, so the research measures sequences of changes, not single tasks.

The goal is to be able to tell a user, with the size of the effect and the strength of the evidence stated, "LID is cheaper (or more expensive) than X under Y conditions." Cost here means two things. It means tokens and dollars, and it also means the human attention each way of working asks for. The human cost is the more interesting of the two, because a person saying "ok" to a plan is a very different cost from a person having to think hard about what they want.

## What kind of work this is

This is a research spike to collect data, not a merge gate for LID's own development. We build the instrument so that it can later become a measuring eval, or a gate, without a rewrite: arms, seeds, and change scripts are data, runs are repeatable, and every result records the versions it ran on.

The work happens in public. The draft pull request [#120](https://github.com/jszmajda/lid/pull/120) stays open and gets regular pushes, so other people can give feedback as it goes.

## Resume here

Read this section first when you pick the work up in a new session. Update it at the end of every working session.

**Where things stand.**

- **The design** in [design.md](design.md) is a second full draft. It merges the kickoff takes, a fresh review of the plan, and the maintainer's decisions recorded in [log.md](log.md).
- **The pilot seed** is BenchTime, a reservation service for shared lab instruments. Each arm designs its own interface from a brief in the owner's words. A step before grading extracts the interface, and graders follow the grading protocol in [design.md](design.md): probes, separate execution and judgment, and checks on the graders.
- **The seed's materials** are accepted, and their hashes are recorded in the seed's README (the brief and change script at version 1, the oracle at version 2, the probes at version 1). The public [brief](seeds/benchtime/brief.md) is in the repository. The oracle, change script, and edit log are in `seeds/benchtime/hidden/`, which git ignores, so they exist only in this workspace on the maintainer's machine. See [seeds/benchtime/README.md](seeds/benchtime/README.md).
- **Claude roles** (executors, the simulator, and graders) run on the maintainer's subscription to keep costs down.
- **The plumbing test is done** (see [log.md](log.md) and [log-archive/](log-archive/)). LID's phase stops work headless, cost accounting is understood, and executor sessions run in a Linux container with the maintainer's subscription token.
- **BenchTime's probes** (92, for all 53 graded items) are drafted by Sol, edited, and reviewed by Claude Fable in the maintainer's place, at version 1. The oracle is at version 3 and the change script at version 2, after edits that changed only what the simulated owner holds.
- **The simulated owner passed its leak threshold** (2026-11-14): 15 live scenarios × 10 runs, with no confirmed leaks by an Opus judge, after the rework that Claude Fable's review called for. One model call per stop serves all three policies, the harness times and inserts redirects, and a trimming call cuts replies to what was asked. "The user simulator" in [design.md](design.md) describes it.
- **The harness** ([harness/](harness/README.md)) runs whole trajectories (`run_trajectory.py`), grades checkpoints (`grade_checkpoint.py`), and audits real owner replies for leaks (`audit_owner.py`), with 103 tests. Runs are recorded in the git-ignored `runs/` folder, which stays private because the owner's prompts hold the hidden oracle.
- **Grading runs end to end and costs about $0.70 per checkpoint** at Haiku's list price, on the subscription: Sonnet extraction, a setup session, Haiku probe execution across four workers, and a Haiku judge. Replay isn't needed at pilot scale. The three probes that need prior-data aren't implemented yet and are reported as not run. Grader calibration hasn't started; doubtful verdicts go in `seeds/benchtime/hidden/calibration/cases.md`.
- **Pilot stage 0 passed** (all three arms on Sonnet 5.5, a build plus two changes): every arm completed, isolation held, stops and questions worked, and every turn's usage was recorded. Plumbing only, not evidence.
- **Pilot stage 1 is running:** two bare trajectories on Opus 5.5 through all ten changes, `runs/s1-bare-opus-1` and `-2`.
- **The maintainer has handed the pilot to the main session** (2026-11-14): run it on your own judgment, and bring the maintainer only decisions that are really theirs. Pushing to the draft pull request is allowed; marking it ready, merging, and releasing are not.
- **No counted runs yet.**

**Next actions** (milestones M1 and M2 in [plan.md](plan.md)):

1. **Finish stage 1.** When the two trajectories end, grade their final checkpoints. The threshold is that the bare arm meets no more than about 85% of the requirements in force; if it meets more, harden the seed. Check by hand any symptom diagnostic recorded as inconclusive.
2. **Calibrate the graders** before stage 2: seeded violations on a few builds, labelled pairs, test-retest at both steps, and a sample of verdicts checked in the maintainer's place (by Claude Fable, as for the probes). Try Sonnet as the judge if Haiku stays as cautious as it was in stage 0, where several "couldn't exercise" verdicts look unwarranted.
3. **Build what stage 2 needs:** probe-change forks from the snapshots after changes 0, 3, 6, and 9 (the runner now saves the owner's state after every change), prior-data probes, the A/A check, the positive control, and the touchpoint classifier.
4. **Run stages 2 and 3** as [plan.md](plan.md) describes, logging and pushing as you go.

## Files

| File | What it holds |
|---|---|
| [README.md](README.md) | This page: the question, where things stand, and how to keep the notebook |
| [hypotheses.md](hypotheses.md) | The working hypotheses, each with its predicted direction and what would show it wrong |
| [design.md](design.md) | The current eval design: arms, executors, seeds, changes, the user simulator, measures, statistics, fairness |
| [plan.md](plan.md) | Milestones, with status |
| [landscape.md](landscape.md) | A dated snapshot of the other SDD systems and how each one handles later changes |
| [sources.md](sources.md) | Papers, benchmarks, and articles, each labelled by how closely we read it |
| [log.md](log.md) | A dated journal: what was done, what was decided, and who decided it. Older entries are in [log-archive/](log-archive/) |
| [decisions.md](decisions.md) | Every decision that still stands, with its date and who made it |
| [harness/](harness/README.md) | The harness code, with its tests |
| [plumbing/](plumbing/README.md) | Throwaway scripts from the plumbing test: the executor image, the clock check, the grading tool, and a draft extraction template |
| [upkeep/](upkeep/) | Procedures for keeping the notebook, such as compacting the log |
| [seed-proposals/](seed-proposals/README.md) | Candidate projects for the pilot seed from three model families, with a comparison table |
| [inputs/](inputs/) | Design inputs kept as they were written: the second model's kickoff brainstorm and its later review of the plan |

## Glossary

- **Arm:** one way of working with the agent, such as a bare agent, cheap discipline, or LID Full.
- **Executor:** a harness, a model, and a reasoning effort, treated as one unit.
- **Seed:** the project an arm builds, defined by a product brief and a hidden oracle.
- **Oracle:** the fuller, hidden description of what the product owner wants. The user simulator answers from it, and graders check against it.
- **Trajectory:** one arm's build of one seed, followed by its whole sequence of changes.
- **Checkpoint:** a snapshot of a trajectory's repository after a given change, which later runs can fork from.
- **Probe change:** a change used to measure how cost per change grows with the project's age.
- **Redirect:** a change of mind or a clarification that the user simulator delivers partway through a change.
- **Touchpoint:** a point where an arm turns to the person, such as an approval, a question, or a review.
- **Yield:** whether a touchpoint's answer brought out intent that a later graded requirement checks.

## How to keep this notebook

- **Write a log entry for every working session.** Say what was done, what was decided, and who decided it. When something in [design.md](design.md) or [hypotheses.md](hypotheses.md) changes, edit that file in place so it always shows the current state, and put the reason in the log.
- **Compact the log when it passes about 2,000 words.** Check `wc -w log.md` whenever you update the log at the end of a working session. If it's over, hand [upkeep/compact-log.md](upkeep/compact-log.md) to a subagent (Haiku is enough), then check its work as that file describes. Recent entries stay, older ones move word for word to [log-archive/](log-archive/), an "Earlier, in brief" section at the bottom keeps the arc, and [decisions.md](decisions.md) keeps the decisions that still stand.
- **Freeze the hypotheses before the first counted run.** Pilot runs exist to test the instrument and don't count as evidence. Once the hypotheses, the primary comparison, and the analysis plan are frozen, any later change is a dated amendment that says why it was made.
- **Label every source by how closely it was read.** Several numbers in [sources.md](sources.md) came from a fetch tool's summary of a page rather than from the page itself. Check a number against the original before quoting it anywhere public.
- **Keep the public notebook free of private material.** Don't record personal details, private project names, or local paths.
- **Hand work to subagents with this README and [design.md](design.md) as the brief.** A subagent given those two pages and one milestone from [plan.md](plan.md) has what it needs to start. Record what it found in the log and in the file it changed.

## Harness code

The harness serves this study, so it sits outside LID's arrow like the rest of the notebook. Its code lives in [harness/](harness/), beside the [plumbing/](plumbing/README.md) scripts it grew from, and its design is in [design.md](design.md) under "The harness". The parts where a quiet bug would bias results have tests. If the harness's results come to back a claim LID ships, or the eval becomes a repeated measurement, it moves into the arrow as its own segment, as the alternate-model runner (`docs/intent/alt-model-evals/`) is. That runner's opencode setup and credential handling are the patterns to reuse for the opencode executors.
