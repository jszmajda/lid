# B10 RESULTS — Differential Catch Rate on Seeded Intent Gaps

**Date**: 2026-08-03
**Status**: FINAL — the pre-registered Fable↔Sol agreement trigger fired (83.6% < 0.85) and the mandated human pass is complete: all 22 disagreements ruled by Jess on 2026-08-03 (`answer-key/human-adjudication.md`; rulings sided Fable 12 / Sol 10). Numbers below are the adjudicated finals (`scoring-final.json`; pre-human baseline in `scoring.json`).
**Design**: DESIGN.md in this directory (original + 2026-08-02 pre-registration amendment + pilot-gated adjustments). Pilot shakeout in PILOT.md.

## Summary

**The bidirectional differential passed its exam: on the annotated surface it caught nearly everything — including every hollow test — and its one blind spot turned out to be the arrow itself.**

| Question | Answer |
|---|---|
| Headline: fresh zero-context Sonnet (T2) recall on 24 seeded gaps | **23/24 (96%)** — pre-registered threshold was 0.70 |
| Hollow tests (class H) — the class the attestation question turns on | **8/8 caught** — the pre-registered expectation that H would score *lowest* was refuted |
| Phantom specs (P) / unstated intent (U) | 8/8 / 7/8 |
| The one universal miss | The seed sat in **un-annotated code**: the citation-scoped slice never showed it to any auditor at any tier. Catch rate is bounded by **annotation reach, not detection ability** |
| False alarms on untouched specs | 0–7.5% per arm; most rejected "noise" is missing cross-references between sibling specs, not fabrication |
| Prominence | In 42 of 49 fresh-arm detections, the seeded gap was the **top-ranked finding** |
| Cheap models | GPT-5.6 Luna matched Sonnet's subset recall for **$0.43 total**; Haiku (5/8) marks where the floor gives way |
| Independence gradient (self-audit → fresh → cross-provider) | Flat — ceiling-limited by seed visibility; the binding constraint was the slice, not verifier independence |
| Adjudication cross-check | Fable↔Sol agreement 83.6% tripped the pre-registered 0.85 trigger → all 22 disagreements human-adjudicated (Jess, 2026-08-03); recall moved by one exploratory cell |
| Incidental yield | Genuine gaps found on *untouched* specs, including one production bug (view-tab tail truncation exists only in test fakes) |

In one sentence: **the differential catches what it can see almost perfectly, and sees only what the arrow annotates** — "the instruments guard attestation" is now a measured claim (96%), conditional on arrow maintenance keeping the annotations honest.

## Verdict

**T2 recall 23/24 (96%) — far above the pre-registered 0.70 threshold. Class H (hollow test): 8/8 at T2.** On this fixture, a fresh zero-context Sonnet auditor caught every hollow-test seed — the failure mode the attestation question turns on — and every phantom-spec seed, missing exactly one unstated-intent seed. That miss is structural, not perceptual: the seed's code lives in a file the citation-scoped audit slice never included (see Finding 1). **The instrument's catch rate is bounded by annotation coverage, not by detection ability.**

## Recall by class × arm (key-match adjudication, blind, vs sealed key)

| Arm | Auditor | U | P | H | Total |
|---|---|---|---|---|---|
| T1 (self-audit) | Sonnet, seeding context | 2/3 | 3/3 | 2/2 | 7/8 |
| **T2 (headline, full grid)** | Sonnet, fresh | **7/8** | **8/8** | **8/8** | **23/24 (96%)** |
| T2 (subset seeds only) | — | 2/3 | 3/3 | 2/2 | 7/8 |
| T2-cap | Opus, fresh | 2/3 | 3/3 | 2/2 | 7/8 |
| T3 | GPT-5.6 Terra, fresh | 2/3 | 3/3 | 2/2 | 7/8 |
| EXP | GPT-5.6 Luna, fresh | 2/3 | 3/3 | 2/2 | 7/8 |
| EXP | Haiku, fresh | 1/3 | 3/3 | 1/2 | 5/8 |

Every arm's miss in the U column includes the same seed (U-MARK-004, Finding 1). Haiku additionally missed H-MARK-008, and — by human adjudication of the run's single detection dispute — U-PUB-002: it surfaced the exact seeded chunking mechanism but framed it as harmless surplus, missing the half-written-window violation. Ruling principle: detection that reassures isn't detection.

Sensitivity view (post-hoc, not pre-registered): excluding the slice-invisible seed, every arm scores 100% except Haiku (6/7).

## Key findings

### 1. The one universal miss is a scoping blindness, and it reframes the result

U-MARK-004's seed (a last-known-good quote-date carry-forward) was planted in `crates/runtime/src/adapters.rs` with **no spec-ID mention in that file**; the audit slice — built from spec-ID citations — contained only the sheets-view files. No auditor at any tier ever saw the seeded code; even the T1 seeder's self-audit honestly reported it "would not have surfaced the seeded gap" under the audit's scoping. The natural control: U-PUB-002 sits in the **same file**, but SHEET-PUB-002's baseline citations already reached the runtime crate, so its slice included adapters.rs — and it was detected by every arm. Same drift locus; annotated vs unannotated; detected vs invisible. **Detection power is conditional on the arrow's annotation reach — drift that escapes `@spec` placement escapes the audit entirely.** This is the strongest empirical argument yet recorded for arrow-maintenance as a load-bearing (not cosmetic) practice: the differential guards only the annotated surface.

### 2. Hollow tests were the easiest class here, not the hardest

The pre-registered expectation (Class H lowest) was refuted: H scored 8/8 at T2 and 100% at every arm except Haiku. Mechanism, from the run transcripts: an H seed leaves the spec text intact, so the A-direction reconstructs the *original* intent while the B-direction reconstructs the *narrowed* code+tests — the two collide head-on, and the collision names an exact constant (e.g. `1.005 → 101` where `round_half_to_even` gives 100). By contrast, U seeds only produce a B-side surplus that must compete with the fixture's abundant natural B-side surplus. The bidirectional structure — not auditor brilliance — is what makes hollow tests detectable: the spec text is the tripwire the narrowed tests cannot rewrite.

### 3. The independence gradient is flat; the capability floor is real but low

T1 = T2 = Opus = Terra = Luna = 7/8 on subset seeds. Cross-provider independence bought no recall on this seed set (ceiling effect: seeds were either visible-and-caught or invisible-to-all), so readout #3 is answered "no gradient observed — but the test was ceiling-limited; the correlated-verifier objection is neither confirmed nor rebutted here." The only capability signal: Haiku finished at 5/8 (dropped one H seed, one U seed whose gap it found but declared benign, plus the slice-invisible seed), produced the run's only INCONSISTENT-BLIND, the only BD-COHERENT-on-drift codes, and 8/16 a-low stability — the cheap-model floor is real. Luna (at $0.43/arm) matched Sonnet's subset recall with 7/7 top-finding prominence.

### 4. Prominence is excellent — the matched finding is almost always finding #0

Top-finding rates: T3, Luna 7/7; Haiku 6/6; Opus 6/7; T2 17/23 (mean rank 0.48). When the instrument catches a seeded gap, it leads with it. Combined with the false-alarm rates below, the "recall could be noise-buried" worry from the pilot did not materialize.

### 5. False-alarm rates are low; the dominant "noise" is cross-reference structure, and the REAL surplus is genuine discovery

Control-finding verdicts (blind realness adjudication, human-final): T2 9/120 FALSE-ALARM (7.5%), Opus 2/77 (2.6%), Terra 0/42, Luna 1/43 (2.3%), Haiku 1/18 (5.6%). CROSSREF (behavior stated by an uncited sibling spec — B9's decomposition-gap pattern) is 30–55% everywhere. The REAL verdicts on *untouched* specs (53 at T2 alone, pre-dedup across arms/sets) are incidental discoveries; distinct headline items include: **the production Sheets adapter never truncates the residual tail that SHEET-PUB-002 requires (only the test fakes do — a genuine enforcement gap in portfolio-tracker)**; the 13-column Positions schema and its formula algebra are pinned by tests but stated by no spec; `DATA_START_ROW=2`/header-row-1 are unstated constants; the Unrealized % zero-basis guard is unstated; the own-row no-leak property is test-checked for only 1 of 7 formula columns; the Tax bands' exact column schemas are likewise unstated (added by human ruling #7); and an empty effective-rate cell silently zeroes the post-tax `=G×H` columns.

### 6. The adjudication cross-check tripped its own wire — and the human pass settled it

Fable↔Sol agreement on the sampled groups: 112/134 (83.6%); including the pilot sample, 132/156 (84.6%) — below the pre-registered 0.85 trigger, so the mandated human re-adjudication ran (all 22 items; `answer-key/human-adjudication.md`). Texture: 21 of 22 were verdict-granularity disputes on realness (REAL↔CROSSREF↔FALSE-ALARM boundary calls, concentrated in the two schema-heavy FORMULA specs) with **no directional same-family-leniency pattern** — Fable was stricter about as often as Sol, and the human rulings split 12/10. Recall was robust to the entire dispute (one exploratory cell moved). Two adjudication principles came out of the pass and are now part of the protocol record:

1. **A sibling can license an exception to a universal claim** — otherwise universals become unwritable, collecting endless "unless…" amendments. Such cases are CROSSREF (missing cross-reference), not drift.
2. **Spec silence over genuinely unclosed intent space is not drift** — REAL requires a concrete commitment on one side that the other fails to match. The silence signal is still reported (as under-specification, visible in A-run assumption divergence), and it points at a LID improvement: **the intent-narrowing edge-audit phase should treat A-run assumption divergence as first-class edge-detection input for identifying and closing unclosed intent space.**

### 7. Classification codes remain descriptive, not discriminative

100% of Opus units and 100% of T2 units classified as drift (no BD-COHERENT on 24 untouched controls at T2) — replicating B9's "real specs carry natural drift" at scale and confirming the pilot lesson now baked into the amendment: detection lives in per-finding key-matching, never in the unit-level code. The accidental T2 duplicate run (below) adds a stability datum: the same unit flipped BD-DRIFT ↔ B-ONLY-DRIFT between executions while its key-matched finding stayed identical.

## Stability

A-direction: high 30/48, medium 16/48, low 2/48 at T2; Opus 16/16 high on both directions; Haiku the outlier (a-low on 8/16). B-direction agreement is high nearly everywhere — replicating B9's "B is the stronger, stabler signal."

## Cost (honest accounting)

| Item | Amount |
|---|---|
| Claude tokens, in-instrument (seeding, pilot, smoke, T2 grid, Opus + Haiku arms) | ≈ 46.1M subagent tokens, of which **16.6M was a duplicated T2 run** (workflow-resume prefix-cache miss; first run superseded, kept as `runs/T2-run1-superseded/`) |
| Claude tokens, measurement layer (adjudication ×2 waves, pilot adjudicators, T1 key-matches) | ≈ 5.5M |
| OpenAI, exact per-call | Terra arm $3.94 · Luna arm $0.43 · Sol cross-check ≈ $2.33 (pilot + sample) |
| Wall-clock | pilot→final adjudication ≈ 1 day elapsed; compute time ≈ 2.5 h of workflow runtime; one 2.5 h session-limit stall overnight |
| Per audit unit (T2) | ≈ 343k tokens (7 calls: 3A + 3B + classifier) |

The economics headline, human-adjudicated: **Luna audited 16 units for $0.43 with subset recall equal to Sonnet's, perfect top-finding prominence, and a 2.3% control false-alarm rate** — the "cheap-model boon" result is real. Haiku (5/8) marks the floor where it stops being true.

## Confounds and limits

Single codebase, single segment, n=8 per class. Seeds authored by Sonnet knowing the instrument exists (mitigated: gap-log-derived categories; realism notes per seed; one seed's realism produced the scoping-invisibility finding). T1 recall inflated by construction (auditor knows the seed); its one miss was self-declared. Adjudicator blinding was partial: realness adjudicators had filesystem access wide enough to diff seed trees against baseline, and at least two verdicts cite "the planted change" — realness verdicts are unaffected in principle (planted gaps are real gaps) but the seed/control distinction was not perfectly blind. Sol cross-check sample completed 10/15 groups (OpenAI credits exhausted mid-run); the ≥20%-of-adjudications bar was met in verdict count (134 paired verdicts) but not in planned group coverage. API arms received slice file *contents* embedded rather than file access (protocol asymmetry). Unit-level classification codes are execution-unstable (BD-DRIFT ↔ B-ONLY-DRIFT flip observed between duplicate T2 executions of one unit); per-finding scoring is unaffected. The independence gradient was ceiling-limited by the seed set. `[1m]`-class safety-classifier unavailability affected one adjudication (R11); a full redo matched 5/5.

## Pre-registered readouts, answered (final)

1. **T2 recall ≥ 0.70?** Yes — 96% (23/24). "The instruments guard attestation" is defensible *on the annotated surface* of this fixture.
2. **Class H recall**: 8/8 at T2 — the trace-vs-reader question gets its first data point, and it says audited traces caught every deliberate hollow-test on annotated code.
3. **Independence gradient**: flat (ceiling-limited); no evidence independence buys recall here; correlated-verifier objection unresolved by this run.
4. **Stability and cost**: stated above, including the duplicated-run overhead and the resource stalls.

**The sharpest sentence this experiment earned: the differential catches what it can see almost perfectly, and sees only what the arrow annotates.** Catch rate is a property of the instrument *and* the annotation discipline jointly — which converts "maintain the arrow" from hygiene advice into the load-bearing precondition of the attestation stance.

## Human adjudication (completed 2026-08-03)

All 22 Fable↔Sol disagreements ruled by Jess; record with per-item rulings and the two protocol principles in `answer-key/human-adjudication.md`. Final tallies: `scoring-final.json` (pre-human baseline preserved in `scoring.json`). Sol's 5 unfinished sample groups (R21, R30, R34, R36, R47 — OpenAI credits exhausted mid-run) remain open as an optional top-up; their absence is disclosed in Confounds and does not affect the adjudicated numbers.
