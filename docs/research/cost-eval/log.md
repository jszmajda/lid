# Research log

Newest entries first. Each entry says what was done, what was decided, and who decided it.

Older entries move to [log-archive/](log-archive/) when this file passes about 2,000 words, and 'Earlier, in brief' at the bottom summarizes them.

## 2026-11-17: BenchTime under the rebuilt owner

**What ran:** bare, cheap discipline, and LID Full on Sonnet 5.5, three trajectories each, under the bounded owner at the central constants. The three arms of each replicate share one draw seed. Then probe forks and grading at changes 2, 6, and 10 with probes version 5 (`harness/run_stage3b.sh`; `runs/stage3b/report.md`). Every trajectory completed. Pilot numbers, not evidence.

| Arm | Items met at change 10 | Latent (askable) items met | Agent cost | Owner replies | Words shown to the owner |
|---|---|---|---|---|---|
| bare | 95% | 92% | $2.53 | 19.0 | 5,156 |
| cheap discipline | 93% | 90% | $4.54 | 23.7 | 14,348 |
| LID Full | 97% | 96% | $11.17 | 64.7 | 53,431 |

**What the owner did:**
- **Recall on review was about the same in every arm:** 8 to 10 unsaid items per trajectory. No broad question recalled anything.
- **The bounded owner caught few contradictions in LID's long documents:** 0.3 kept of 4.0 drawn per trajectory, against 2.7 of 4.3 for bare and 2.7 of 7.0 for cheap discipline. A contradiction deep in a long plan is read near the attention floor.
- **LID still met the most items,** so its lead here comes from its own asking and specification, not from the owner correcting it.

**Keeping** (items met at change 2 that are still met at change 10) was 100%, 100%, and 98.8%: BenchTime has almost no regressions to measure.

**Comparability:** stage 2's diligent-owner numbers were graded under probes version 4 and the earlier judge rules. These use version 5, and the rerun of executor-caused verdicts, which lifts every arm. The two stages can be compared arm against arm within a stage, not across.

**Reading:** on BenchTime, with Sonnet, a realistic owner leaves the arms 2 to 4 points apart at change 10. LID costs about 4.4 times bare's agent spend and shows the owner about 10 times the words. The seed is near its ceiling for this executor. The latent-heavy seed, ReleaseDesk, is where the arms have room to differ.

## 2026-11-16: The owner becomes an imperfect person, built on published research

**Decided by the maintainer:**
- **What fidelity measures.** It is the true intent, not the brief. Arms are compared on two things against cost and attention: surfacing (latent intent that reaches the build) and keeping (intent held through change).
- **The owner model.** The simulated owner hides nothing on purpose, doesn't realise what it left unsaid, can be reminded by what the agent shows, and misses more as it reads more.
- **Calibration.** Its constants come from published research, not from the maintainer playing the owner.

**What led there.** ReleaseDesk's ceiling run met 90% of items with a silent owner, but only about half its latent ones; 48 of its 56 items are stated. Gemini 4 Carbon and Claude Fable were asked separately how to handle that. Both put the latent intent in "the rules at the joints". The maintainer's correction: real owners don't hide intent at the joints; they fail to realise what they left unsaid, and their understanding changes with experience.

**The research** ([owner-model-research.md](owner-model-research.md)), five strands:
- cued recall: ACT-R and prospective memory;
- omission neglect;
- how review size and reading affect what's caught;
- requirements elicitation;
- simulated users.

They support a composite model:
- **Attention** belongs to the policy, and falls with a passage's position in the stop.
- **Recall** belongs to the item. A direct touch brings back an unsaid item at 0.50 to 0.90 by salience tier, and an adjacent touch at 0.10 to 0.50.
- **Both are seeded draws in the harness.** The constants are swept, not trusted.

**Built and reviewed:**
- **The design.** Fable's review found four blockers, three of which tilted toward arms that restate intent across many documents and stops. Fixed: one draw per item per change, keyed on a replicate seed shared across arms; numbered passages; broad questions drawn by the harness; recall lines frozen with the oracle.
- **Salience tiers and recall lines.** Four model families rated every askable item blind. Agreement stayed below the 0.7 bar (pooled weighted kappa 0.60), so the median tiers are used and the shortfall is recorded. GPT-6.1 Sol drafted the recall lines. Fable reviewed them and set a standard: one decision per line, plus a boundary only where leaving it out would invert the item.
- **The harness change,** test-first: 212 tests. Fable's code review found no blockers; its five majors and the first leak-gate run's findings are fixed. The early gate run, before those fixes, had 1 confirmed leak in 250 replies. It showed the stage 2 leaks gone, and recall rates close to the table.
- **A process slip.** A commit taken while a subagent was editing the workspace published half of the harness change under the wrong message. The next commit completes it and says so; no force-push.

**Open for the maintainer:**
- the scope of a draw (per change is the default);
- whether w counts within a stop or across the change (within a stop is the default);
- how far the sweep runs end to end;
- ReleaseDesk's latent set, which now also trips the salience check (2 of 6 high).

**Next:** the full leak gate on the final prompt, a short live trajectory, then ReleaseDesk's stage 2.

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
- Three probes stayed "couldn't exercise" after their rerun (P-RD05-a, P-RD24-a, P-RD36-a). Each had a cause outside the build:
  - a step the probe never asked for (P-RD05-a);
  - an import file the executor couldn't write (P-RD24-a);
  - a long response the judge saw only part of (P-RD36-a).

  All three are fixed (ReleaseDesk probes version 2, `gt file`, and a longer response view), and graded again on the same checkpoints all three are met.

## Earlier, in brief

**The arc so far.** On 11-11, three takes on the design converged on one core design, and mining old transcripts was dropped. On 11-12, the maintainer settled that graders are models, and BenchTime and ReleaseDesk were chosen as the pilot and second seeds. On 11-13, a grading protocol was written into design.md, about 25 throwaway sessions showed that LID's phase stops work headless, and the maintainer decided the harness stays outside LID's arrow. On 11-14, Claude Fable's review found the simulated owner not ready for counted runs, and pilot stage 0 ran the three arms through two changes. In the evening, grader calibration showed Haiku 5.5 flipping 9% of its verdicts on repeat, so Sonnet 5.5 judges and Haiku executes, and two Opus 5.5 trajectories met 90% in stage 1 under the diligent owner. Under a rubber-stamp owner, which shares only what direct questions ask for, Opus met 88%. Late that night, a Sonnet ceiling check started. On 11-15, it met 80% and 76%, so Sonnet became BenchTime's main executor. ReleaseDesk's owner brief was drafted by several models and checked by Claude Fable, and a six-model panel measured how guessable its candidate rules are. The maintainer then set the mix of eight latent rules by guessability band, and the rules within each band were drawn by lot. Later on 11-15, ReleaseDesk's oracle, change script, and probes were drafted, reviewed, and accepted. Stage 2 on BenchTime was graded. Its first numbers put LID Full at 96% of items met at about 5× bare's cost, and ReleaseDesk's ceiling check started.

**Decisions.** Every decision that still stands, with its date and who made it, is in [decisions.md](decisions.md).

**Archive.**

- [2026-11.md](log-archive/2026-11.md): entries from 2026-11-11 to 2026-11-15 (twenty entries)
