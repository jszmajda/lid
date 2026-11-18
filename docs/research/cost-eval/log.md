# Research log

Newest entries first. Each entry says what was done, what was decided, and who decided it.

Older entries move to [log-archive/](log-archive/) when this file passes about 2,000 words, and 'Earlier, in brief' at the bottom summarizes them.

## 2026-11-18: Clowder's grading checked on a null arm, and the ceiling check

**The null arm** grades Clowder's untouched snapshot as if an arm had changed nothing, so every new-intent item should come back not met.
- **The first pass found a false met.** The probe executor wrote the missing feature into its own test, and the judge credited it. Since then:
  - executors must perform every step under test through the build's own API;
  - a stand-in reading counts as a grader fault;
  - a met on an item the extraction recorded as absent is a conflict, counted as missing and flagged.
- **Over all twelve changes, no new-intent item was met.** The conflict check caught three probes that could pass without the feature (one by coincidence, two from the journal). Those probes were fixed, and a recheck scored them not met.
- **Held-out retention was 323 of 323** at every change, and the planted bug's repair was not met.
- **Grading cost about $5 of subscription quota** for twelve changes.

**The ceiling check** (pilot): bare on the stripped repository, 1M window, bounded owner, one fork per change.

| Measure | Result |
|---|---|
| New-intent items met | 24 of 30 graded (80%); 2 more missing (grader observation faults) |
| Planted bug (change 5) | repaired |
| Held-out tests kept | 99.4% to 100% per change; 5 tests lost across the twelve changes |
| Agent cost | $4.31 for the twelve changes |
| Peak context per session | 14k to 98k tokens, under 10% of the window |

- **The room is there:** bare met 80% here, against 95% on BenchTime.
- **The window may not be a dose.** No bare session came near 200k tokens. Bare agents search and read slices of the code rather than loading it, so a 200k window would not have changed what they saw. If that holds, the window cannot test the hypothesis as stated. The open question becomes whether agents read where the intent lives, which `context_telemetry.py` measures as intent reach. The pilot proper runs both windows as planned and measures whether any arm comes near the window: LID reads about four times as much as bare on BenchTime.

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

## Earlier, in brief

**The arc so far.** On 11-11, three takes on the design converged on one core design, and mining old transcripts was dropped. On 11-12, the maintainer settled that graders are models, and BenchTime and ReleaseDesk were chosen as the pilot and second seeds. On 11-13, a grading protocol was written into design.md, about 25 throwaway sessions showed that LID's phase stops work headless, and the maintainer decided the harness stays outside LID's arrow. On 11-14, Claude Fable's review found the simulated owner not ready for counted runs, and pilot stage 0 ran the three arms through two changes. In the evening, grader calibration showed Haiku 5.5 flipping 9% of its verdicts on repeat, so Sonnet 5.5 judges and Haiku executes, and two Opus 5.5 trajectories met 90% in stage 1 under the diligent owner. Under a rubber-stamp owner, which shares only what direct questions ask for, Opus met 88%. Late that night, a Sonnet ceiling check started. On 11-15, it met 80% and 76%, so Sonnet became BenchTime's main executor. ReleaseDesk's owner brief was drafted by several models and checked by Claude Fable, and a six-model panel measured how guessable its candidate rules are. The maintainer then set the mix of eight latent rules by guessability band, and the rules within each band were drawn by lot. Later on 11-15, ReleaseDesk's oracle, change script, and probes were drafted, reviewed, and accepted. Stage 2 on BenchTime was graded. Its first numbers put LID Full at 96% of items met at about 5× bare's cost, and ReleaseDesk's ceiling check started. That night stage 2 passed all four of its thresholds, and a leak review found the owner adding what a plan left out; the owner's corrections were tightened.

**Decisions.** Every decision that still stands, with its date and who made it, is in [decisions.md](decisions.md).

**Archive.**

- [2026-11.md](log-archive/2026-11.md): entries from 2026-11-11 to 2026-11-15 (twenty-one entries)
