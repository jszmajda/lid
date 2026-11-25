# Research notebook: what LID costs, compared with other ways of working

**Status: pilot work; no counted runs yet.** Last updated 2026-11-24. Every run so far tested LID 1.4.6, run in Claude Code 2.1.323 on Claude Sonnet 5.5 at medium effort (Opus 5.5 only in ceiling checks).

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
- **BenchTime's probes** (92, for all 53 graded items) are at version 2, after Claude Fable's spot-check of grader verdicts found six asking more than their oracle items. The oracle is at version 3 and the change script at version 2.
- **The simulated owner passed its leak threshold** (2026-11-14): 15 live scenarios × 10 runs with no confirmed leaks, judged by Opus. In real runs so far, the leak audit has flagged about 1 judged reply in 40. "The user simulator" in [design.md](design.md) describes how it works.
- **The harness** ([harness/](harness/README.md)) runs trajectories, probe forks, grading, re-judging, owner audits, touchpoint classification, and spot-check sampling, with 372 tests. Runs are recorded in the git-ignored `runs/` folder, which stays private because the owner's prompts hold the hidden oracle.
- **The graders are calibrated** (2026-11-14). Sonnet 5.5 judges and Haiku 5.5 executes. The judge agreed with itself on all 44 probes, and a whole-pipeline regrade agreed on all 44. Four seeded violations were each caught, and Claude Fable, standing in for the maintainer, agreed with 35 of 36 sampled verdicts. Grading costs about $1 per checkpoint notional. The three prior-data probes aren't implemented and are reported as not run. Calibration notes are in `seeds/benchtime/hidden/calibration/`.
- **Pilot stage 0 passed:** all three arms on Sonnet 5.5, a build plus two changes. Plumbing only.
- **Pilot stage 1 settled the executor.** A bare arm on Opus 5.5 met 88% of BenchTime's items with a silent owner and 90% to 92% with a diligent one, above the ceiling threshold. On Sonnet 5.5 it met 76% to 80%. Under the maintainer's rule, Sonnet is BenchTime's main executor, and Opus results there are reported as limited by the ceiling.
- **Pilot stage 2 on BenchTime passes all four thresholds** (Sonnet 5.5, diligent owner, three trajectories per arm). Pilot numbers only:
  - items met at change 10: bare 92%, bare A/A 92%, cheap discipline 89%, LID Full 96%, positive control 80%;
  - agent cost for the build plus ten changes: $2.32, $2.35, $4.48, $11.54, and $0.97;
  - grader agreement 38 of 40 (Claude Fable's spot-check), test-retest 0 flips in 264, positive control worse, A/A no difference.

  The verdicts to use are each checkpoint's `rejudge-v4.json`. Cheap-discipline trajectories 1 to 3 are left out. The results carry a leak caveat: the owner leaked through corrections in a few replies, mostly to cheap discipline, and counting those verdicts as not met changes no ordering. `harness/report.py` regenerates the tables (`runs/stage2/report.md`).
- **The simulated owner was fixed after stage 2** so that a correction quotes words wrong in themselves and never adds what a list left out. It was checked by replaying the real stops and the scripted scenarios (`harness/replay_owner.py`). Every later run uses the fixed owner.
- **BenchTime's probes are at version 5**, and the judge now says whether each "couldn't exercise" came from the executor or the build; grading reruns executor-caused ones once.
- **The simulated owner is now an imperfect person** (maintainer's decision, 2026-11-16): it hides nothing on purpose but doesn't realise what it left unsaid, can be reminded by what the agent shows, and misses more as it reads more. Attention and memory are separate seeded draws, with constants from published research ([owner-model-research.md](owner-model-research.md); design in [design.md](design.md), "Attention and recall"). It is built and reviewed (212 tests); both seeds' salience tiers and recall lines are frozen in `owner-items.json`. Trajectories now need `--replicate`, shared by the arms being compared. Fidelity is reported as surfacing and keeping. It passed its leak gate on the final prompt (0 confirmed leaks in 260 replies; a recognised-on-sight objection in 18 of 20 runs) and a live smoke check. **BenchTime under the rebuilt owner is done** (bounded policy, three trajectories per arm; [log.md](log.md), 2026-11-17; `runs/stage3b/report.md`): items met at change 10 were bare 95%, cheap discipline 93%, LID Full 97%, at agent costs of $2.53, $4.54, and $11.17.
- **ReleaseDesk, the second seed, is ready, and its ceiling check is done** ([seeds/releasedesk/README.md](seeds/releasedesk/README.md)). The bare arm under a silent owner met 90 to 91% of all items but only 44 to 56% of latent items. The maintainer chose to read its ceiling on latent items, and to grow ReleaseDesk into the large greenfield test later, sized by what Clowder shows.
- **The Clowder pilot ran** (2026-11-18; [seeds/clowder/README.md](seeds/clowder/README.md); plan.md milestone M2c): bare on a stripped copy, bare on the full repository as an inheritance check, and LID Full, one run per cell at a 1M and a 200k window. The bare agent on the full repository copied LID's artifacts, so the study turned to a greenfield growth test and then to cross-crate and brownfield changes.
- **The Docker VM** has 6 CPUs and 10 GB (resized 2026-11-22 with the maintainer's approval), and runs four forks at a time. Its disk is 100 GiB; M2h's runner releases each fork's volumes after grading unless a repair needs them, and waits while free disk is under 20 GB.
- **Start long jobs as tracked background tasks, or with a watch.** A job started detached sends no notice when it finishes.
- **The maintainer has handed the pilot to the main session** (2026-11-14): run it on your own judgment, and bring the maintainer only decisions that are really theirs. Pushing to the draft pull request is allowed; marking it ready, merging, and releasing are not. Claude Fable stands in for the maintainer's detailed reviews (probes, oracles, verdict spot-checks).
- **M2f, Clowder's cross-crate test, has run** (log.md, 2026-11-23; analysis in `runs/clowder-m2f/analysis/`). The arms finish close in total (new rows 69 and 70 of 72; dependencies kept 18 and 19 of 24) but miss different dependencies. LID's arm ran under Clowder's own standing override of phase reviews.
- **M2h, the openGym brownfield test, has run** (log.md, 2026-11-24; `runs/opengym-m2h/m2h.md` and `analysis/`). LID built every requested change and bare 33 of 36; breakage of the dependent component is level (7 of 33 against 6 of 35), at about 3× the agent cost before LID's one-time mapping.

**Next actions:**

1. **Publish the first report** ([report-1-draft.md](report-1-draft.md)) in a research section of the LID site, built through LID's own workflow in the main repository (maintainer's decision, 2026-11-24).
2. **The maintainer is taking on LID issues the study raised first:** #135 (cross-segment links), document length, and test-quality guidance. After #135, rerun M2f's changes 16 to 18 as a before-and-after.
3. **Long-horizon evidence:** an anonymised before-and-after from the private project's history, cost data from a friend's large LID project if they share it, and a public project of realistic size for a long-horizon growth test, which the maintainer is choosing.
4. **Review the specification-explicitness paper's deferred ideas** with the maintainer (plan.md, "After the growth test"), and the competitor arms (M5).
5. **Finish the owner checks:** labelled judgments on about 100 replayed stops, the constants sweep, and the three replayed stops where the owner still errs.
6. **Still to build:** prior-data probes, grading for the probe request, and a scripted check for operating requirements.

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
| [report-1-draft.md](report-1-draft.md) | The first report's draft: what LID cost and bought in the pilot runs, what that shows and doesn't, and open questions |
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
