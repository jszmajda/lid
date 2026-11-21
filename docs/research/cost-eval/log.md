# Research log

Newest entries first. Each entry says what was done, what was decided, and who decided it.

Older entries move to [log-archive/](log-archive/) when this file passes about 2,000 words, and 'Earlier, in brief' at the bottom summarizes them.

## 2026-11-21: The trial's scale, and a strategic review

**Size at change 20:**

| | bare | LID Full |
|---|---|---|
| Source | 5 files, 1,440 lines | 16 files, 2,727 lines |
| Tests | 1 file, 637 lines | 18 files, 8,977 lines |
| Docs | the README | 22 files, with 406 specs |
| Code and tests | about 25k tokens | about 123k tokens |

Bare never split the service into components. The maintainer judged ReleaseDesk too small to exercise the scale and rot mechanisms: a bare agent can read its whole system at every change.

**The cost of working around rot** is now measured in every fork. The trial shows no contrast in outcome yet: every reliance fork followed the current rule.

**Claude Fable's strategic review:**
- **Don't run the full growth run.** The trial's latent lead is all intent only LID heard. On rules both arms had heard, both met every one. So a bigger run would mostly confirm that LID asks more.
- **Rot sat at the floor in both arms.** Fable suggested that agents read code, which is current, so tests may not be an agent's main record of intent.
- **History replay is a fair test of adopting LID on an existing project, but a weak test of scale or rot:**
  - real tests encode the implementer's choices, not the owner's intent;
  - issues carry no latent intent;
  - the model has likely seen the project.
- **A better scale test:** Clowder with cross-crate changes, stripped against LID, three repeats each.
- **The study is missing:**
  - the cost of repairing missed intent, which is the break-even #75 asks about;
  - LID's Scoped mode;
  - cost by how deeply the owner reviews;
  - per-phase token spend;
  - the competitors.
- **What can be claimed so far is grade C or D:**
  - LID costs about 4–5.5× the agent tokens per change;
  - it asks for about ten times the owner reading;
  - on small projects its fidelity gain is a few points.

The maintainer is choosing the next direction.

## 2026-11-21: The growth trial

**What ran:** bare and LID Full, one trajectory each (replicate g-r1), through change 20 under the bounded owner. Each had course forks (3 per course change), reliance forks (3 per course change), checkpoints at 10 and 20, intent from tests and docs, and the stale-intent audit. One trajectory per arm: pilot observations, not evidence.

**Harness faults found and fixed before reading anything:**
- LID's build takes its data folder only as a command-line option, and setups ran the reference's `{DATA}` placeholder literally. So 44 of LID's 55 gradings failed at setup, and an errored grading still counted as done. Both are fixed and the trial is regraded.
- The same fault could have hidden two of LID's symptom diagnostics. Rechecked: change 15's passes, and change 7's can't occur, because LID's build at that point offers no saved-link download. LID's trajectory stands as run.

| Measure at change 20 | bare | LID Full |
|---|---|---|
| Stated items met | 98% | 93% |
| Latent items met (change 10 → 20) | 75% → 67% | 88% → 89% |
| Keeping (items met at 10 still met) | 49/49 | 45/47 |
| Reliance forks following the displaced rule | 0 of 18 | 0 of 18 |
| Flip checks behaving | 8/8 | 8/8 |
| Stale files found by the audit in course forks | 1 of 12 | 4 of 64 |
| Intent from tests, recall of met items (above a brief-only reader) | 61% (+10) | 83% (+35) |
| Intent from docs | – | 83% (+36) |
| Cost per change (notional) | $0.29 | $1.59 |
| Owner reading by change 20 | 0.6 hours | 6.6 hours |

- **LID's latent lead grew** from 13 points at change 10 to 22 at change 20, in this one replicate.
- **No reliance fork followed a displaced rule** in either arm through change 20, so the rot consequence sits at the floor so far.
- **Bare's tests carry little intent beyond the brief:** a reader of bare's tests recovers 10 points more than a reader of the brief alone, against LID's 35.

**Cost:** the trial used about 19 points of the weekly subscription limit, regrades included.

## 2026-11-21: The growth test's instrument gate passes

The gate asks whether the probes tell a correct build from a stale one, before any arm runs. It never looks at arm results.
- **The correct build (R+):** a bare agent told every rule in force at each change, through change 40.
- **The stale builds:** one fork per course change, declining that change and carrying the displaced rule through its reliance request.

**First run: 13 of 18 course changes separated.** The failures traced to:
- **Harness faults, fixed:**
  - code exported afresh lacked its installed environment, so every probe on earlier-prepared data, and two preparations, failed;
  - the judge never saw which identifier was which fixture;
  - names-only planted tests leaked their rule through file names and assertion messages;
  - a grading that ran nothing reported success.
- **Probe faults, fixed:**
  - one probe graded JSON field names, which the change explicitly keeps;
  - one never asked for the record's text;
  - one depended on how same-day renames are grouped;
  - change 27's reliance request read as a request for a written answer. It was reworded to ask for a page in the service, an instrument fix made before any arm ran.

**After the fixes: 17 of 17 course changes separate, with no mismatches.** Every probe that applies to R+ is met at changes 10, 20, 30 and 40. Change 38 is outside the gate and is reported descriptively (decisions.md, 2026-11-20).

**The positive control:**

| Change | Planted kind | Reader sees tests as written | Reader sees names and comments replaced |
|---|---|---|---|
| 20 | names only | 83% | 33% |
| 20 | assertions | 83% | 83% |
| 40 | names only | 72% | 17% |
| 40 | assertions | 72% | 47% |

The readers catch most planted stale tests. With names and comments replaced, they lose most of the names-only plants, as they should. The 17–33% they still name is probably inferred from the build itself; that's unconfirmed. R+ wrote a single test file, so the plants outnumber its own tests.

The probe set is frozen at version 3, the change script at version 6, and the reference spec at version 2, with their hashes in the seed's README. **Next:** the trial, one bare and one LID trajectory through change 20.

## Earlier, in brief

**The arc so far.** On 11-19, the growth test was designed and its seed drafted blind; a first look at intent from tests found bare's, cheap discipline's and LID's tests carrying 83%, 89% and 93% of BenchTime's current intent, and a symptom-row leak in the owner was fixed without changing any standing. On 11-18, the Clowder pilot ran (bare on the stripped repository 79% at 1M and 85% at 200k, LID 97% and 84%; one run per cell); a bare agent on the full repository copied LID's artifacts, which ruled out further Clowder runs as a test of LID against bare. Also on 11-18, a null arm checked Clowder's grading (no new-intent item met on an untouched snapshot once stand-in readings were ruled out), and the ceiling check showed room (bare on the stripped repository met 80%). On 11-17, BenchTime ran under the rebuilt owner (pilot: bare 95%, cheap discipline 93%, LID Full 97% at change 10; LID's lead came from its own asking, not the owner's corrections). On 11-16, the simulated owner was rebuilt as an imperfect person on published attention and recall research, with separate seeded draws for attention and recall. On 11-11, three takes on the design converged on one core design, and mining old transcripts was dropped. On 11-12, the maintainer settled that graders are models, and BenchTime and ReleaseDesk were chosen as the pilot and second seeds. On 11-13, a grading protocol was written into design.md, about 25 throwaway sessions showed that LID's phase stops work headless, and the maintainer decided the harness stays outside LID's arrow. On 11-14, Claude Fable's review found the simulated owner not ready for counted runs, and pilot stage 0 ran the three arms through two changes. In the evening, grader calibration showed Haiku 5.5 flipping 9% of its verdicts on repeat, so Sonnet 5.5 judges and Haiku executes, and two Opus 5.5 trajectories met 90% in stage 1 under the diligent owner. Under a rubber-stamp owner, which shares only what direct questions ask for, Opus met 88%. Late that night, a Sonnet ceiling check started. On 11-15, it met 80% and 76%, so Sonnet became BenchTime's main executor. ReleaseDesk's owner brief was drafted by several models and checked by Claude Fable, and a six-model panel measured how guessable its candidate rules are. The maintainer then set the mix of eight latent rules by guessability band, and the rules within each band were drawn by lot. Later on 11-15, ReleaseDesk's oracle, change script, and probes were drafted, reviewed, and accepted. Stage 2 on BenchTime was graded. Its first numbers put LID Full at 96% of items met at about 5× bare's cost, and ReleaseDesk's ceiling check started. That night stage 2 passed all four of its thresholds, and a leak review found the owner adding what a plan left out; the owner's corrections were tightened.

**Decisions.** Every decision that still stands, with its date and who made it, is in [decisions.md](decisions.md).

**Archive.**

- [2026-11.md](log-archive/2026-11.md): entries from 2026-11-11 to 2026-11-19 (twenty-six entries)
