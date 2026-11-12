# Research notebook: what LID costs, compared with other ways of working

**Status: designing the pilot. No counted runs yet.** Last updated 2026-11-12.

## The question

People who try LID ask what it costs, and they most often ask how it compares with other spec-driven development (SDD) systems such as OpenSpec, GitHub Spec Kit, and BMAD. LID can't answer either question today. Issue [#75](https://github.com/jszmajda/lid/issues/75) records the gap. LID has never stated what walking the arrow costs. HLD Goal 3's claim that the adoption modes let teams use LID "at proportional cost" has no evidence behind it. Nobody knows the project size or change count at which walking the arrow starts to pay for itself.

The working hypothesis is that LID costs more to build a system and less to change it later. A change made months later should find the intent it needs in the design docs and specs, so it should cost less and break less than it would where that intent lives only in code. The hypothesis is about long-term maintenance, especially of complex systems, so the research measures sequences of changes, not single tasks.

The goal is to be able to tell a user, with the size of the effect and the strength of the evidence stated, "LID is cheaper (or more expensive) than X under Y conditions." Cost here means two things. It means tokens and dollars, and it also means the human attention each way of working asks for. The human cost is the more interesting of the two, because a person saying "ok" to a plan is a very different cost from a person having to think hard about what they want.

## What kind of work this is

This is a research spike to collect data, not a merge gate for LID's own development. We build the instrument so that it can later become a measuring eval, or a gate, without a rewrite: arms, seeds, and change scripts are data, runs are repeatable, and every result records the versions it ran on.

The work happens in public. The draft pull request [#120](https://github.com/jszmajda/lid/pull/120) stays open and gets regular pushes, so other people can give feedback as it goes.

## Resume here

Read this section first when you pick the work up in a new session. Update it at the end of every working session.

**Where things stand.** The design has a first full draft in [design.md](design.md), built from three independent takes: a brainstorm in the main session, a brainstorm by a second model, and a literature and landscape survey. A fresh review of the plan by Claude Fable came back on 2026-11-12 with a list of risks and gaps ([inputs/2026-11-12-fable-plan-review.md](inputs/2026-11-12-fable-plan-review.md)). Its proposed changes aren't in [design.md](design.md) yet, because the maintainer hasn't decided on them. Fifteen candidate projects for the pilot seed are in [seed-proposals/](seed-proposals/README.md), waiting for the maintainer to pick one. The maintainer's decisions so far are in [log.md](log.md). Nothing has been built or run.

**Next actions** (the matching milestone in [plan.md](plan.md) is M1):

1. The maintainer picks the pilot seed from [seed-proposals/](seed-proposals/README.md), and decides which of the plan review's changes to adopt. Then update [design.md](design.md), [hypotheses.md](hypotheses.md), and [plan.md](plan.md) to match.
2. Write the chosen seed's product brief, then have a model from another family write the hidden oracle as narrative product prose.
3. Write the pilot's change script, the user simulator's prompt, the attention rubric, and the grading rubric.
4. Write the configurations for the three pilot arms: bare agent, cheap discipline, and LID Full.
5. Decide where the harness code lives, then walk LID's arrow for it before writing any code (see "Harness code" below).

## Files

| File | What it holds |
|---|---|
| [README.md](README.md) | This page: the question, where things stand, and how to keep the notebook |
| [hypotheses.md](hypotheses.md) | The working hypotheses, each with its predicted direction and what would show it wrong |
| [design.md](design.md) | The current eval design: arms, executors, seeds, changes, the user simulator, measures, statistics, fairness |
| [plan.md](plan.md) | Milestones, with status |
| [landscape.md](landscape.md) | A dated snapshot of the other SDD systems and how each one handles later changes |
| [sources.md](sources.md) | Papers, benchmarks, and articles, each labelled by how closely we read it |
| [log.md](log.md) | A dated journal: what was done, what was decided, and who decided it |
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
- **Freeze the hypotheses before the first counted run.** Pilot runs exist to test the instrument and don't count as evidence. Once the hypotheses, the primary comparison, and the analysis plan are frozen, any later change is a dated amendment that says why it was made.
- **Label every source by how closely it was read.** Several numbers in [sources.md](sources.md) came from a fetch tool's summary of a page rather than from the page itself. Check a number against the original before quoting it anywhere public.
- **Keep the public notebook free of private material.** Don't record personal details, private project names, or local paths.
- **Hand work to subagents with this README and [design.md](design.md) as the brief.** A subagent given those two pages and one milestone from [plan.md](plan.md) has what it needs to start. Record what it found in the log and in the file it changed.

## Harness code

The notebook is research and sits outside LID's arrow. The harness that runs the eval is code, so it walks the arrow like the repository's other maintainer tooling: an intent node under `docs/intent/`, then specs, then tests, then code. The alternate-model runner (`docs/intent/alt-model-evals/`) and the cascade recorder (`docs/intent/cascade-recording/`) are the closest examples, and the runner's sandbox and opencode setup can probably be reused.
