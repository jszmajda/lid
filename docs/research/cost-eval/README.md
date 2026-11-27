# Research notebook: what LID costs, compared with other ways of working

**Status: pilot phase finished and published; no counted runs yet.** Last updated 2026-11-25. Every run so far tested LID 1.4.6, run in Claude Code 2.1.323 on Claude Sonnet 5.5 at medium effort (Opus 5.5 only in ceiling checks).

## The question

People who try LID ask what it costs, and they most often ask how it compares with other spec-driven development (SDD) systems such as OpenSpec, GitHub Spec Kit, and BMAD. LID can't answer either question today. Issue [#75](https://github.com/jszmajda/lid/issues/75) records the gap. LID has never stated what walking the arrow costs. HLD Goal 3's claim that the adoption modes let teams use LID "at proportional cost" has no evidence behind it. Nobody knows the project size or change count at which walking the arrow starts to pay for itself.

The working hypothesis is that LID costs more to build a system and less to change it later. A change made months later should find the intent it needs in the design docs and specs, so it should cost less and break less than it would where that intent lives only in code. The hypothesis is about long-term maintenance, especially of complex systems, so the research measures sequences of changes, not single tasks.

The goal is to be able to tell a user, with the size of the effect and the strength of the evidence stated, "LID is cheaper (or more expensive) than X under Y conditions." Cost here means two things. It means tokens and dollars, and it also means the human attention each way of working asks for. The human cost is the more interesting of the two, because a person saying "ok" to a plan is a very different cost from a person having to think hard about what they want.

## What kind of work this is

This is a research spike to collect data, not a merge gate for LID's own development. We build the instrument so that it can later become a measuring eval, or a gate, without a rewrite: arms, seeds, and change scripts are data, runs are repeatable, and every result records the versions it ran on.

The work happens in public. The draft pull request [#120](https://github.com/jszmajda/lid/pull/120) stays open and gets regular pushes, so other people can give feedback as it goes.

## Resume here

Read this section first when you pick the work up in a new session. Update it at the end of every working session.

**Where things stand (2026-11-25).** The pilot phase is finished and published.

- **The first report** is on the LID site, in its research section (`site/src/research/first-results/` in the repository, published at `/research/first-results/`). It covers every pilot run: BenchTime, ReleaseDesk (the growth trial and the checklist arm), the Clowder pilot, Clowder's cross-crate changes (M2f), and openGym (M2h). [observations.md](observations.md) holds the leads behind its list of LID changes.
- **What was tested:** LID 1.4.6, in Claude Code 2.1.323, with Claude Sonnet 5.5 at medium effort as the executor; Opus 5.5 only in ceiling checks. A later LID release is a new condition, reported apart.
- **The evidence is pilot grade.** Nothing is pre-registered, and every comparison rests on three runs or fewer per cell. [log.md](log.md) has each phase's results, and [decisions.md](decisions.md) every decision that still stands.
- **Issues the study raised for LID:** #133 and #134 (`/map-codebase`), and #135 (links between segments, so a change can find what relies on it).
- **Seed material.** Each seed's oracle, change script, probes, and edit log are in its git-ignored `hidden/` folder, on the maintainer's machine only. Some rule wording also appears in the harness's seed converters and tests, and in the authoring prompts, which the seed READMEs list as public. A later comparison that needs material no agent could have seen should use new seeds.
- **Run records** are in the git-ignored `runs/` folder, including each phase's analysis (`runs/clowder-m2f/analysis/`, `runs/opengym-m2h/analysis/`, `runs/growth/`).

**How the work runs.**

- **The harness** ([harness/](harness/README.md)) runs every phase in Docker (Colima, 6 CPUs and 10 GB) with the maintainer's subscription token, through `plumbing/with-token.sh`. Its unit tests run with `python3.12 -m unittest discover -s tests` from `harness/`.
- **Check the grading both ways before any counted run:** the untouched start must meet no new rule, and a correct build of every change must meet every rule. Both checks caught faults in every phase.
- **Watch long jobs yourself.** Start them as tracked background tasks, or start a watcher on any job a subagent leaves running; once a finished job sat unnoticed for five hours.
- **Disk:** freed container volumes return space to macOS only after the VM's disk is trimmed (`harness/trim.sh`); the runners trim after every release and wait while free disk is low.
- **Other model families** draft and review test material through OpenRouter, from the main session only; spend so far is about $18.
- **The maintainer has handed the work to the main session** (2026-11-14): run it on your own judgment, and bring the maintainer only decisions that are really theirs. Opening and merging pull requests, and releases, need the maintainer's approval. Claude Fable stands in for the maintainer's detailed reviews.

**Next actions:**

1. **The maintainer is taking on LID issues the study raised:** #135 (cross-segment links), document length, and test-quality guidance. After #135, rerun M2f's changes 16 to 18 as a before-and-after.
2. **Long-horizon evidence:** cost data from a friend's large LID project if they share it; the private project's history, though its adoption was gradual, so its before and after won't split cleanly; and a public project of realistic size for a long-horizon growth test, which the maintainer is choosing.
3. **Review the specification-explicitness paper's deferred ideas** with the maintainer (plan.md, "After the growth test"), and the competitor arms (M5).
4. **Finish the owner checks:** labelled judgments on about 100 replayed stops, the constants sweep, and the three replayed stops where the owner still errs.
5. **Still to build:** prior-data probes, grading for the probe request, and a scripted check for operating requirements.

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
| [report-1-draft.md](report-1-draft.md) | Where the first report lives now: on the LID site, from `site/src/research/first-results/` |
| [lid-research-records](https://github.com/jszmajda/lid-research-records/tree/main/cost-eval) (separate repository) | Aggregates behind the reports on [intent recovery](https://linked-intent.dev/research/intent-recovery/) and [mapping an existing codebase](https://linked-intent.dev/research/mapping-an-existing-codebase/), kept outside this repository so it stays small to clone |
| [observations.md](observations.md) | Leads noticed along the way about LID, about measuring it, and about running a study like this with agents |
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
