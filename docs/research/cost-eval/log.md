# Research log

Newest entries first. Each entry says what was done, what was decided, and who decided it.

Older entries move to [log-archive/](log-archive/) when this file passes about 2,000 words, and 'Earlier, in brief' at the bottom summarizes them.

## 2026-11-18: The Clowder pilot

**What ran:** three arms, each at a 1M and a 200k context window, twelve independent changes each, one run per cell, on Sonnet 5.5 under the bounded owner. The arms were bare on the stripped repository, bare on the full repository, and LID Full. These are pilot numbers, not evidence.

**Items met** (33 items: 12 stated, 20 latent, and the planted bug's repair), with the spot-check rulings applied:

| Arm | 1M | 200k | Latent items, 1M / 200k | Agent cost, 1M / 200k | Words shown to the owner, 1M / 200k |
|---|---|---|---|---|---|
| bare, stripped repository | 26 (79%) | 28 (85%) | 15 / 16 of 20 | $4.30 / $4.03 | 7,699 / 13,791 |
| bare, full repository | 29 (88%) | 30 (91%) | 17 / 18 of 20 | $12.48 / $13.61 | 5,316 / 39,494 |
| LID Full | 32 (97%) | 27 of 32 (84%), 1 missing | 19 / 16 of 20 | $18.55 / $15.74 | 195,044 / 105,323 |
| null (untouched snapshot) | | 0 | | | |

- **Room exists.** Bare on the stripped repository missed one item in five, against one in twenty on BenchTime.
- **The repository's docs and fuller tests helped bare** by 2 to 3 items, at three times the agent cost.
- **LID at 1M met the most items, and at 200k fell to the stripped arm's level.** LID's 200k losses (changes 6, 7, 11 and 12) don't line up with compaction, which happened only at change 7. With one run per cell, a single item moves a share 3 points, so none of these differences separate the arms or the windows.
- **Owner attention is LID's largest cost:** about 195,000 words shown across twelve changes at 1M, which is roughly 14 hours of reading at 238 words a minute, against 5,000 to 14,000 for bare.
- **Keeping didn't discriminate:** held-out tests lost per cell ranged from 5 to 15 out of about 3,900 runs. Two LID runs changed the API so that some held-out tests couldn't build (86 tests, reported by cause).

**Context:** bare on the stripped repository never used more than 98k tokens in a session. Bare on the full repository reached 193k, and LID reached 255k. At 200k, four sessions compacted: bare on the full repository at changes 7 and 11, and LID at changes 2 and 7. The window binds only for arms that read the repository's intent, and rarely.

**What the pilot fixed in the instruments.** Each fix was applied blind to arm, and the affected changes were regraded:
- **The owner's completion reading:** the owner took "Phase 6 is next. I'll add…" as a completion report, so a separate check now reads every completion first. The two runs it had cut short were rerun.
- **The stand-in rule:** it now turns on who produced the outcome. A changed existing command counts as the build's own operation.
- **The evidence the judge sees:** executor output is no longer cut off.
- **Probe output:** probes print one summary line per case.
- **Two probe flaws:** a stock drop is now the probe's own measurement, and a setup no longer pre-fills a record.
- **Held-out adaptation:** it now fills missing array fields.

The pilot ends on probes version 5 for changes 5 and 10 and version 4 elsewhere; the two differ by one clarifying sentence in the shared conventions.

**Spot-checks** (Claude Fable, blind to arm):
- **The one conflict** (change 11) was ruled not met.
- **A stratified sample of 20 met verdicts:** 19 were upheld. One, change 7 in bare stripped at 1M, was overturned because the build shows "Cuddles “Professor Fluff”" where the item asks for the nickname as the display name. Every other build shows the nickname alone.
- **A pattern the readers noted:** executors often build setup S1 with housing 6 rather than 2. That rarely touches a deciding reading, but the judge ruled it a fixture fault once (LID at 200k, change 7, the one missing item). The next probe version fixes S1, and the judge counts a broken witness only when it could change the deciding reading.

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

## Earlier, in brief

**The arc so far.** On 11-16, the simulated owner was rebuilt as an imperfect person on published attention and recall research, with separate seeded draws for attention and recall. On 11-11, three takes on the design converged on one core design, and mining old transcripts was dropped. On 11-12, the maintainer settled that graders are models, and BenchTime and ReleaseDesk were chosen as the pilot and second seeds. On 11-13, a grading protocol was written into design.md, about 25 throwaway sessions showed that LID's phase stops work headless, and the maintainer decided the harness stays outside LID's arrow. On 11-14, Claude Fable's review found the simulated owner not ready for counted runs, and pilot stage 0 ran the three arms through two changes. In the evening, grader calibration showed Haiku 5.5 flipping 9% of its verdicts on repeat, so Sonnet 5.5 judges and Haiku executes, and two Opus 5.5 trajectories met 90% in stage 1 under the diligent owner. Under a rubber-stamp owner, which shares only what direct questions ask for, Opus met 88%. Late that night, a Sonnet ceiling check started. On 11-15, it met 80% and 76%, so Sonnet became BenchTime's main executor. ReleaseDesk's owner brief was drafted by several models and checked by Claude Fable, and a six-model panel measured how guessable its candidate rules are. The maintainer then set the mix of eight latent rules by guessability band, and the rules within each band were drawn by lot. Later on 11-15, ReleaseDesk's oracle, change script, and probes were drafted, reviewed, and accepted. Stage 2 on BenchTime was graded. Its first numbers put LID Full at 96% of items met at about 5× bare's cost, and ReleaseDesk's ceiling check started. That night stage 2 passed all four of its thresholds, and a leak review found the owner adding what a plan left out; the owner's corrections were tightened.

**Decisions.** Every decision that still stands, with its date and who made it, is in [decisions.md](decisions.md).

**Archive.**

- [2026-11.md](log-archive/2026-11.md): entries from 2026-11-11 to 2026-11-16 (twenty-two entries)
