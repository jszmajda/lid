# Research log

Newest entries first. Each entry says what was done, what was decided, and who decided it.

Older entries move to [log-archive/](log-archive/) when this file passes about 2,000 words, and 'Earlier, in brief' at the bottom summarizes them.

## 2026-11-15 (night): Stage 2 passes its thresholds; the owner stops leaking through corrections

**Stage 2's thresholds, all met** (pilot numbers):
- **Grader agreement:** Claude Fable, standing in for the maintainer, agreed with 38 of 40 sampled verdicts (95%). Both disagreements were the judge being too strict.
- **Test-retest:** three change-10 checkpoints judged twice more flipped 0 of 264 verdicts.
- **Positive control** is worse (80% against bare's 92%), and **the A/A check** shows no difference (92% and 92%; $2.32 and $2.35).

**From the spot-check:**
- **BenchTime probes version 5:** ten probes reworded so executors run every step and don't read a word as a feature name, and Fable checked the edits. Stage 2 stays graded under version 4.
- **Judge rules:** an inspection the executor skipped counts like one the build doesn't offer, but only when other log entries show the same thing. Every verdict now says whether a "couldn't exercise" came from the executor or the build. Grading runs an executor-caused one once more.
- **A restart race:** when a start command left a shell as the parent, the old server could answer the readiness check and then vanish, so the first request after a restore was refused. The control server now waits for the port to free.
- **A stub verdict** (reason "Placeholder") had passed the checks. Verdicts now need a real reason, and the one affected batch was judged again (it was a "met").

**The owner leaked through corrections.** The leak audit of stage 2 flagged 15 of 171 owner replies. Fable ruled five of them real leaks that plausibly changed a verdict, and two more borderline:
- **The pattern:** the agent's words were right as far as they went, and the owner "corrected" them by adding what they left out ("must also …"). A list of checks was read as a contradiction of a rule it didn't mention.
- **Who gained:** cheap discipline most, one leaked item per trajectory, because it shows a written plan before coding. LID had the lowest rate of real leaks per reply.
- **Effect on the numbers:** counting every leaked verdict as not met leaves the order unchanged at every checkpoint. At change 10: LID 95.4%, bare 90.8%, cheap discipline 87.6% (96.1%, 91.5%, 88.9% as graded). Stage 2's results carry this as a caveat.
- **The fix:** the owner's instructions now say what a correction must quote: words wrong in themselves, not words that are right but incomplete. A confirmation is "Yes." without a recital, and an open question on a rule recognised on sight still gets "Show me what you have in mind". The trim deletes added cases and can drop a correction that only adds something; the harness ignores that drop for anything this change's own request asked for.
- **How it was checked:** each candidate was replayed on the real stops (each recorded prompt with only the instruction lines swapped) and on the 15 scripted scenarios. On the problem stops, judge leaks fell from 21 of 36 runs under the old prompts. Moving the silence rule itself into rule 2 broke a scripted case, so the guidance went into the corrections instruction instead. Final acceptance of the adopted version: judge leaks on those stops 3 of 36, no earned correction lost (20 of 20 control runs, against 19 of 20 before), and the 15 scripted scenarios passed every check in 150 runs, with one judge flag.

**Two symptom reports that never reached the agent.**
- **Change 5's diagnostic** was inconclusive in six trajectories, because P-BT41-a then required a visible return record (fixed in version 4). The report wasn't delivered. Later grading meets BT-41 in all 15 trajectories, so no build had the bug, and nothing was lost.
- **Bare trajectory 2's change 9 diagnostic** couldn't load its setup, so the trajectory never received that bug report and fails BT-42 at change 10. That verdict is left out, as in stage 1.

**Built:**
- **A report generator** (`report.py`) for a stage's runs, which reproduces stage 2's numbers, records any verdict left out, and says why a change was skipped.
- **An owner replay tool** (`replay_owner.py`).
- **`gt file`,** for import fixtures, after ReleaseDesk's import probe couldn't be run.
- **Setups are prepared with every setup they're built on,** which a partial grading had missed.

**ReleaseDesk's ceiling** (bare arm, rubber-stamp owner, change 10, two trajectories per model):
- **All items:** Sonnet 90%, Opus 91%, above the 85% ceiling.
- **Stated items** (48, given to every arm by the brief and the requests): 98% and 97%.
- **Latent items:** Sonnet 7 of 16, Opus 9 of 16. Pooled by guessability band: low 6 of 16, medium 4 of 8, high 6 of 8, the order the panel predicted. Two low-band rules were never met.
- **Agent cost** for the build plus ten changes: Sonnet $2.22, Opus $9.93.
- **Proposed, for the maintainer:** read ReleaseDesk's ceiling on latent items, where both models leave room, and make latent-item fidelity by band its main measure.
- Three probes stayed "couldn't exercise" after their rerun (P-RD05-a, P-RD24-a, P-RD36-a), two of them in two trajectories each, which points at the probes or the harness rather than the executor. To look at before stage 2.

## 2026-11-15 (evening): Stage 2 graded; ReleaseDesk ready; its ceiling check starts

**Decided by the maintainer:** ReleaseDesk's brief, oracle, and change script are accepted, including the five edits that change what an item or change measures.

**ReleaseDesk's probes.** GPT-6.1 Sol drafted 71 probes. Claude Fable reviewed them (5 blockers, 11 majors, 12 minors), the main session fixed them (P2 to P24 in the private edit log), and Fable checked the fixes. They are hashed as version 1 in the seed's README.

**Harness fixes found along the way:**
- **File traffic:** the control server now sends multipart uploads, keeps a step's own Content-Type, and logs ZIP downloads as their files' names and texts.
- **Setups:** a probe whose setup couldn't load is not run, and the rest go ahead. A service that loads data inexactly is noted as a deviation, not a failure.
- **Probe text:** the probes' conventions reach the executor and the judge, and needs written as sentences still defer.
- **Workers:** every grading worker keeps its data at the same path, in its own volume.
- **Start specs** must stay inside the checkout, and a bad one gets one more extraction.
- **Executor sessions deny scheduling and other interactive tools.** Stage 2's first three cheap-discipline trajectories had scheduled wakeups in plan mode, so they are replaced.
- **BenchTime probes version 4 (E59):** a return record counts only where shown.

**Stage 2 on BenchTime** (Sonnet 5.5, diligent owner, three trajectories per arm, judged again under probes version 4 and a new rule; pilot numbers, not evidence):
- **The new rule:** an inspection a build doesn't offer, such as listing every booking, no longer makes a probe "couldn't exercise". Cheap discipline's builds offered no list operation, which had left up to 23 items unmeasured.
- **Items met at change 10:** bare 92%, bare A/A 92%, cheap discipline 89%, LID Full 96%, positive control 80%. The A/A and positive-control checks pass.
- **Agent cost for the build plus ten changes:** bare $2.32, cheap discipline $4.48, LID Full $11.54, positive control $0.97.
- **Owner replies:** 16, 21, 64. **Words the owner read:** about 4,100, 13,700, and 56,400.
- **LID's premium doesn't narrow** over the ten changes: it stays about 5× bare's per change. The same probe request run after changes 0, 3, 6, and 9 shows no slope for any arm yet.

**Running:**
- Claude Fable's spot-check of 40 stage 2 verdicts, for the grader-agreement threshold.
- ReleaseDesk's ceiling check: four bare trajectories under the rubber-stamp owner, two on Sonnet and two on Opus (`runs/rd1-*`), then grading of their final checkpoints.

## 2026-11-15 (later): ReleaseDesk's oracle and change script, drafted and reviewed

**The drafting chain.**
- **The draft.** GPT-6.1 Sol drafted the oracle (62 items) and the change script from the fixed brief, with the eight drawn rules as the only latent items. The prompt is private, because it names them. It also carried every proposal's change list through an extraction slip, but Sol used ReleaseDesk's.
- **Claude Fable's review** found 3 blockers (a redirect stating a latent rule in full, a change presupposing a command-line tool the brief never asks for, and manifests that a frozen grading clock can't fairly test), 8 majors, and 14 minors.
- **The fixes** were made under the editing rules (edits R4 to R16 in the private edit log). **Decided by the main session:** the bundle-naming rule is graded as named by public identifier, and the owner objects to any other naming, so the trigger matches the grading. Two latent items join the relies-on lists of later changes they really depend on.
- **Fable's check of the fixes** found no remaining blockers or majors. The eight latent items still match the draw. Five edits change what an item or change measures, and they go to the maintainer with Fable's notes.

**Stage 2:** the replacement cheap-discipline trajectories are running under the fixed harness, and grading follows.

## Earlier, in brief

**The arc so far.** On 11-11, three takes on the design converged on one core design, and mining old transcripts was dropped. On 11-12, the maintainer settled that graders are models, and BenchTime and ReleaseDesk were chosen as the pilot and second seeds. On 11-13, a grading protocol was written into design.md, about 25 throwaway sessions showed that LID's phase stops work headless, and the maintainer decided the harness stays outside LID's arrow. On 11-14, Claude Fable's review found the simulated owner not ready for counted runs, and pilot stage 0 ran the three arms through two changes. In the evening, grader calibration showed Haiku 5.5 flipping 9% of its verdicts on repeat, so Sonnet 5.5 judges and Haiku executes, and two Opus 5.5 trajectories met 90% in stage 1 under the diligent owner. Under a rubber-stamp owner, which shares only what direct questions ask for, Opus met 88%. Late that night, a Sonnet ceiling check started. On 11-15, it met 80% and 76%, so Sonnet became BenchTime's main executor. ReleaseDesk's owner brief was drafted by several models and checked by Claude Fable, and a six-model panel measured how guessable its candidate rules are. The maintainer then set the mix of eight latent rules by guessability band, and the rules within each band were drawn by lot.

**Decisions.** Every decision that still stands, with its date and who made it, is in [decisions.md](decisions.md).

**Archive.**

- [2026-11.md](log-archive/2026-11.md): entries from 2026-11-11 to 2026-11-15 (eighteen entries)
