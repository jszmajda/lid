# Research log

Newest entries first. Each entry says what was done, what was decided, and who decided it.

Older entries move to [log-archive/](log-archive/) when this file passes about 2,000 words, and 'Earlier, in brief' at the bottom summarizes them.

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
