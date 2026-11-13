# Research notebook: what LID costs, compared with other ways of working

**Status: designing the pilot. No counted runs yet.** Last updated 2026-11-13.

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
- **The seed's materials** are accepted by the maintainer, and their hashes are recorded as version 1. The public [brief](seeds/benchtime/brief.md) is in the repository. The oracle, change script, and edit log are in `seeds/benchtime/hidden/`, which git ignores, so they exist only in this workspace on the maintainer's machine. See [seeds/benchtime/README.md](seeds/benchtime/README.md).
- **Claude roles** (executors, the simulator, and graders) run on the maintainer's subscription to keep costs down.
- **The plumbing test is done** (see [log.md](log.md), 2026-11-13 afternoon and evening). LID's phase stops work headless, and cost accounting is understood. A bare build of BenchTime ran in a container, its interface was extracted, and a Haiku grader ran four probes through the reference and judged them, catching both violations seeded into a mutant.
- **Executor sessions run in a Linux container,** the standard recipe the maintainer accepted, using the maintainer's subscription token.
- **No counted runs yet.**

**Next actions** (milestone M1 in [plan.md](plan.md)):

1. Have Sol draft the probes for every item, then edit them and get them reviewed.
2. Walk LID's arrow for the harness: an intent node under `docs/intent/`, then specs, then tests, then code (see "Harness code" below). The plumbing test's lessons for the harness are in the log's 2026-11-13 evening entry: probes in batches, snapshots of the data location, a `gt` that can't open the source, a commit at the end of each change, and extraction under the fake clock.
3. In parallel: the user simulator's prompt, the touchpoint rubric, and the seeded-violation calibration set. The simulator has to recognise a finished change, and the design has to say whether an agent's list of its own interpretations counts as asking.

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

The notebook is research and sits outside LID's arrow. The harness that runs the eval is code, so it walks the arrow like the repository's other maintainer tooling: an intent node under `docs/intent/`, then specs, then tests, then code. The alternate-model runner (`docs/intent/alt-model-evals/`) and the cascade recorder (`docs/intent/cascade-recording/`) are the closest examples, and the runner's sandbox and opencode setup can probably be reused.
