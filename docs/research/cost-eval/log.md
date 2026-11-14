# Research log

Newest entries first. Each entry says what was done, what was decided, and who decided it.

Older entries move to [log-archive/](log-archive/) when this file passes about 2,000 words, and 'Earlier, in brief' at the bottom summarizes them.

## 2026-11-14 (evening): Graders calibrated; stage 1 hits the ceiling

**Decided by the maintainer:** Claude Fable stands in for the maintainer when spot-checking grader verdicts.

**Grader calibration.**
- **Judge test-retest.** Haiku 5.5 flipped 4 of 44 verdicts when it judged the same logs again (9%, against a threshold of about 5%), all between "met" and "couldn't exercise". Sonnet 5.5 agreed with itself on all 44. It also turned four doubtful "couldn't exercise" verdicts into "met" and found a "not met" Haiku had missed. **Decided by the main session:** Sonnet judges and Haiku executes.
- **Whole-pipeline retest.** A second grading of the same checkpoint from scratch (new extraction, new execution, Sonnet judge) agreed on all 44 probes.
- **Seeded violations.** A subagent made four copies of the bare build, each breaking one item (a limit of four, a cleared label not restoring the name, touching bookings refused, cancelled time not freed). The grader flipped each target item to "not met". The other flips were real consequences of the mutation, plus an ambiguous probe and two execution sessions killed by memory pressure.
- **Memory pressure.** The Docker VM has 2 CPUs and 4 GB. Grading now retries a killed batch once, and gradings run one at a time.
- **Fable's spot-check.** Fable agreed with 35 of 36 sampled verdicts (97%, against about 90%), including all 18 "met" verdicts. It also found probes asking more than their oracle items, mostly fields an item doesn't require, such as a shown deadline or a checkout reference.
- **Probes version 2 (edits E52 to E57).** These six probes now ask only what their items say, and Fable checked the fixes.
- **Stage 0 under the Sonnet judge,** items in force at change 2 (plumbing, not evidence): bare met 22 of 28, cheap discipline 23 (3 couldn't exercise), and LID Full 23 (1).
- **Cost.** Grading a checkpoint costs about $1 notional with the Sonnet judge and takes 10 to 22 minutes with three workers.

**Stage 1: two bare trajectories on Opus 5.5, all ten changes, diligent owner.**
- **Both completed** with no caps and no errors, at $8.98 and $9.68 notional agent cost. The change-5 symptom diagnostic passed on both, so no report was sent. The change-9 diagnostic fired on both, and each agent fixed the symptom in one round.
- **Both meet 46 of 51 items in force at change 10 (90%).** Stage 1's threshold is about 85%, so stage 1 doesn't pass.
- **Most latent intent is guessable.** Of 22 askable and recognized-on-sight items, the owner disclosed 5 to 7 by correcting interpretations the agent listed in its first report. The agent met 12 to 14 of the 15 to 17 it was never told, about 82%. Even if every disclosed latent item had been missed, the arm would meet 78% to 80%.
- **The owner leak audit** over both trajectories flagged 1 reply in 15. It's borderline (a correction completing a rule the agent had only partly stated), and it's counted. Real-run leaks so far are about 1 in 40 judged replies.
- **The maintainer decides what follows,** because it changes what the study can measure.

**Also built:** probe-change forks (`run_probe.py`, tried once), the touchpoint classifier (`classify_touchpoints.py`), `rejudge.py`, `sample_verdicts.py`, and the A/A and positive-control arms.

## Earlier, in brief

**The arc so far.** The moved entries cover 2026-11-11 to 2026-11-14, in the order they happened. On 11-11, three takes on the design converged on one core design, and old transcripts were found unable to answer the question, so mining them was dropped. On 11-12, the maintainer settled that graders are models, and BenchTime was chosen as the pilot seed and ReleaseDesk as the second from fifteen candidate projects. Its materials were drafted and edited, and the maintainer decided that each arm defines its own interface. On 11-13, a grading protocol was written into design.md and the materials were accepted. About 25 throwaway sessions showed that LID's phase stops work headless. That night, Sol drafted 88 probes, and Claude Fable reviewed them. Grading proved the study's biggest cost, so replay was proposed, and the maintainer decided that the harness stays outside LID's arrow. Late that night, the harness began, and plan mode was shown to work headless. On 11-14, Claude Fable's review found the simulated owner not ready for counted runs. The main session fixed it, a sweep of 15 scenarios passed every check, and a trimming call was added to cut each answer. A trajectory runner was built, and pilot stage 0 ran the three arms through a first build and two changes. Grading was built end to end, and a first try on four probes found two setup problems, both fixed.

**Decisions.** Every decision that still stands, with its date and who made it, is in [decisions.md](decisions.md).

**Archive.**

- [2026-11.md](log-archive/2026-11.md): entries from 2026-11-11 to 2026-11-14 (thirteen entries)
