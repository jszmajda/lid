# Research log

Newest entries first. Each entry says what was done, what was decided, and who decided it.

Older entries move to [log-archive/](log-archive/) when this file passes about 2,000 words, and 'Earlier, in brief' at the bottom summarizes them.

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
