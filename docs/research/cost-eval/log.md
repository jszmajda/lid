# Research log

Newest entries first. Each entry says what was done, what was decided, and who decided it.

Older entries move to [log-archive/](log-archive/) when this file passes about 2,000 words, and 'Earlier, in brief' at the bottom summarizes them.

## 2026-11-15: ReleaseDesk's eight latent rules, drawn by lot

**Decided by the maintainer:**
- ReleaseDesk takes 8 latent-intent rules in fixed shares by guessability band (4 low, 2 medium, 2 high), with results reported by band.
- The two rules with a unanimous model default get their values by lot.
- The trivial local changes stay.

**Decided by the main session:** the rules within each band are drawn by lot too, so neither the maintainer nor the main session picks them. The seed is the hash of the commit that recorded the procedure, `3f3da229`, and the draw is a seeded Python shuffle anyone can repeat. The result and the script are in `seeds/releasedesk/hidden/`.
- **The coins:** one of the two default-value rules came up on its guessable value, and the other on its surprising one.
- **The draw:** four low-guess rules (two at the first build, one each at changes 4 and 10), two medium (first build, change 2), and two high (first build).
- **The script stays as proposed.** The rule that motivated replacing change 9 wasn't drawn, so the proposal's change 9 stays. It also tests one of the drawn rules.

**Next:** GPT-6.1 Sol drafts the oracle and change script from the fixed brief, with these eight as the only latent items. Every other item will be stated in the brief or a change request, so the bands stay as measured. Then Claude Fable reviews, and the probes follow.

## 2026-11-15 (small hours): Sonnet is BenchTime's executor; ReleaseDesk's guessability panel

**The Sonnet ceiling passes.** Two bare trajectories on Sonnet 5.5, under the rubber-stamp owner, met 80% and 76% of items in force; trajectory 2 is counted without BT-42, for the harness fault below. They met 16 and 13 of 20 latent items. **Decided by the main session**, under the maintainer's rule: Sonnet is BenchTime's main executor, and Opus results on BenchTime are reported as limited by the ceiling. **Stage 2 is running** with the diligent owner, through `harness/run_stage2.sh`.

**Two more harness faults, fixed.**
- **An unreachable admin token.** A build kept its generated admin token in its data folder, so a symptom diagnostic was inconclusive, and the trajectory skipped a symptom report it should have received. Extraction must now make secrets reachable without reading the source or data. The runner re-runs an inconclusive diagnostic once before deciding, and the faulted item is left out of that trajectory's count.
- **An unfilled placeholder.** The data-folder placeholder wasn't filled in inside the start spec's setup commands.

**ReleaseDesk's brief and panel.**
- **The brief.** GPT-6.1 Sol drafted the owner's up-front material, deliberately silent on 15 open questions. Gemini 4 Carbon wrote the owner-voice brief from it. Claude Fable checked it and found seven hints, which edits R1 to R3 in the private edit log remove. Fable also drafted 23 panel candidates.
- **The panel.** Six models, two from Anthropic plus GPT-6.1 Sol, Gemini 4 Carbon, DeepSeek V4 Pro, and Mistral Large 4, each wrote open designs from the brief, then answered a forced-choice question per candidate. OpenRouter cost $2.22.
- **The results** (`harness/guess_panel.py`; private results in `seeds/releasedesk/hidden/panel-results.md`):
  - 11 candidates are low-guess (almost no model gets them right unprompted or when asked), 3 are medium, and 7 are high.
  - The two "either way" candidates turned out to have a unanimous model default, so their non-default values are low-guess.
  - The authoring models' own guess-risk ratings were often wrong, which is why the panel measures it.

**The maintainer decides** the mix of guessability bands, whether to draw values by lot, and how the three new changes fit the script.

## 2026-11-14 (late night): Surprising intent for ReleaseDesk, from two model families

**Decided by the maintainer:** BenchTime stays as it is; stage 2 runs on it with Sonnet if a silent-owner ceiling check on Sonnet lands at or below about 85%. ReleaseDesk is designed with surprising intent that has to hold over time, drawn from several model families.

**Done.**
- **The Sonnet ceiling check is running:** two bare trajectories on Sonnet 5.5 under the rubber-stamp owner, all ten changes.
- **The brief.** Gemini 4 Carbon and Claude Fable each answered the same brief, [seeds/releasedesk/prompts/01-surprising-intent.md](seeds/releasedesk/prompts/01-surprising-intent.md), independently. It asks for owner rules that are realistic, surprising to a strong model, set either way by real organizations, re-tested by later changes, and checkable from outside, without rigging the project toward arms that ask.
- **The answers:** Carbon proposed 19 rules and Fable 17. They are kept privately in `seeds/releasedesk/hidden/`, with a merged shortlist.
  - The two converged on eight clusters, among them: an uploader can't approve their own upload; lifting a takedown doesn't republish; the last approved version stays public while a replacement waits; public-facing metadata needs reapproval; and the timing of manifests and bundles.
  - They picked opposite answers to one question (whether a new sensitive-collection rule applies to already-public records), which makes it a natural candidate for mirrored variants.
  - Carbon also listed rules that look surprising but that the brief's wording would give away, and rules that would rig the study.
- **Cost:** OpenRouter $0.37, of which the first Carbon call ($0.24) spent all its tokens reasoning and returned no answer.

**Proposed next:** measure each candidate's guessability with a cold panel of several model families, before choosing six to eight rules.

## 2026-11-14 (night): The silent-owner ceiling is still above the threshold

**Decided by the maintainer:** re-run stage 1 under the rubber-stamp owner, go on to stage 2 on this seed if that lands at or below about 85%, and have Claude Fable draft ideas for hardening later runs.

**Fable's hardening ideas** are kept privately in `seeds/benchtime/hidden/hardening-ideas.md`, because they name hidden items.
- **Diagnosis:** about half the latent items are met by the simplest or most careful build, the brief's wording settles two, and the real misses are conventions that could go either way, in corners the agent never surfaced.
- **Options:**
  - report latent fidelity under the rubber-stamp owner, split by told and untold;
  - measure each item's guessability with a cold panel of several model families, as a stratum fixed before runs;
  - add either-way items from a blind drafter, with values drawn by lot or run as mirrored variants;
  - make Sonnet the main executor;
  - add later changes that must agree with the arm's own earlier unstated choices;
  - clean the measure;
  - use relayed briefs;
  - build several of these into ReleaseDesk.
- **Recommendation:** keep BenchTime's oracle frozen, since any item added after seeing results is post hoc, and put the hardening into ReleaseDesk.
- **Two corrections to the evening entry:** there are 20 latent items, not 22, because the count included the two symptom items. And P-BT20-a was grading a point the oracle leaves open (whether planned maintenance releases an existing hold). Probes version 3 (edit E58, checked by Fable) fixes it. Re-judged under version 3, the diligent-owner runs meet 47 and 46 of 51.

**The rubber-stamp ceiling.** Two bare trajectories on Opus 5.5 ran all ten changes, with the rubber-stamp owner, at $8.04 and $10.27 notional.
- **Both meet 45 of 51 items in force (88%),** still above the threshold.
- **Latent items:** 16 of 20 met in each (80%). The owner shared only what direct questions asked for: 1 rule in one run and 4 in the other.
- **The misses:** the same four askable items in both runs. Two stated items in each were "couldn't exercise", still to check as possible probe or execution slips.

**Two grading bugs found and fixed on the way.**
- **Lost credentials.** A build that issues per-person access keys, shown once, made the setup session lose them, so the change-5 diagnostic was inconclusive. Setups now record credentials and create their own administrator. Re-run with the fix, the diagnostic passed, so the trajectory stands.
- **An over-long command line.** A long execution log exceeded the command-line argument limit, so harness roles now take their prompts on standard input.

**The maintainer decides what follows,** because the threshold rule doesn't say what happens above it.

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
- **Most latent intent is guessable.** Of 20 askable and recognized-on-sight items, the owner disclosed 5 to 7 by correcting interpretations the agent listed in its first report. The agent met 10 to 12 of the 13 to 15 it was never told, 77% to 80%. Even if every disclosed latent item had been missed, the arm would meet 78% to 80%. (Corrected from 22 items and 82%: the first count included the two symptom items.)
- **The owner leak audit** over both trajectories flagged 1 reply in 15. It's borderline (a correction completing a rule the agent had only partly stated), and it's counted. Real-run leaks so far are about 1 in 40 judged replies.
- **The maintainer decides what follows,** because it changes what the study can measure.

**Also built:** probe-change forks (`run_probe.py`, tried once), the touchpoint classifier (`classify_touchpoints.py`), `rejudge.py`, `sample_verdicts.py`, and the A/A and positive-control arms.

## Earlier, in brief

**The arc so far.** The moved entries cover 2026-11-11 to 2026-11-14, in the order they happened. On 11-11, three takes on the design converged on one core design, and old transcripts were found unable to answer the question, so mining them was dropped. On 11-12, the maintainer settled that graders are models, and BenchTime was chosen as the pilot seed and ReleaseDesk as the second from fifteen candidate projects. Its materials were drafted and edited, and the maintainer decided that each arm defines its own interface. On 11-13, a grading protocol was written into design.md and the materials were accepted. About 25 throwaway sessions showed that LID's phase stops work headless. That night, Sol drafted 88 probes, and Claude Fable reviewed them. Grading proved the study's biggest cost, so replay was proposed, and the maintainer decided that the harness stays outside LID's arrow. Late that night, the harness began, and plan mode was shown to work headless. On 11-14, Claude Fable's review found the simulated owner not ready for counted runs. The main session fixed it, a sweep of 15 scenarios passed every check, and a trimming call was added to cut each answer. A trajectory runner was built, and pilot stage 0 ran the three arms through a first build and two changes. Grading was built end to end, and a first try on four probes found two setup problems, both fixed.

**Decisions.** Every decision that still stands, with its date and who made it, is in [decisions.md](decisions.md).

**Archive.**

- [2026-11.md](log-archive/2026-11.md): entries from 2026-11-11 to 2026-11-14 (thirteen entries)
