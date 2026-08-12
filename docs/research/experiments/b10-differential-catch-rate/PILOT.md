# B10 Pilot Readout (2026-08-02)

End-to-end shakeout of the full harness on 2 seeds + 2 paired controls at T2 (fresh zero-context Sonnet), per the amended pre-registration. Everything downstream of this file ran only after Jess reviewed this readout.

## Scorecard

| Unit | Kind | Instrument classification | Key-match (Fable) | Key-match (Sol) | Finding dispositions (Fable, scoring of record) |
|---|---|---|---|---|---|
| SHEET-MAP-001 | seed U | BD-DRIFT | **DETECTED** (f0, dir BD⊇B, substance exact) | DETECTED (same) | f0 REAL (the seed); 1 CROSSREF (SHEET-MARK-008); 3 FALSE-ALARM |
| SHEET-MARK-002 | seed H | BD-DRIFT | **DETECTED** (f0, dir BD=BD, substance exact) | DETECTED (same) | f0 REAL (the seed); f4 REAL (incidental: unstated scale-to-micro-cents fold mechanism); 3 CROSSREF (SHEET-MARK-007) |
| SHEET-FORMULA-002 | control | BD-DRIFT | — | — | 1 REAL (incidental: unstated 13-column Positions schema); 3 CROSSREF; 2 FALSE-ALARM |
| SHEET-TAB-001 | control | BD-DRIFT | — | — | 0 REAL; 3 CROSSREF; 1 FALSE-ALARM |

**Pilot seed detection: 2/2, including 1/1 on class H** (the hollow-test class the experiment turns on). Both adjudicators independently matched the same finding index with exact substance.

**Control false-alarm findings: 3/10** (FALSE-ALARM verdicts only; CROSSREF — behavior stated by a sibling spec the audited EARS doesn't reference — is reported separately, consistent with B9's decomposition-gap category, and REAL control findings are incidental discoveries per the design).

**Fable↔Sol adjudication agreement: 20/22 (0.909)** — above the pre-registered 0.85 trigger. Both disagreements sit in CTRL-FORMULA-002, in opposite directions (Fable CROSSREF vs Sol REAL on f0; Fable REAL vs Sol FALSE-ALARM on f1) — no directional same-family-leniency pattern. Sol key-match adjudications were materially cheaper than realness ones (≈1.5–2k vs 29–103k input tokens).

## What the pilot taught (carried into the grid)

1. **Unit-level classification has no discriminative power on this fixture: all 4 units — seeds and controls alike — classified BD-DRIFT.** The discriminative layer is per-finding content + key-match adjudication, exactly as the design's recall definition prescribes. RESULTS must not report unit-level classification as if it were detection.
2. **The B9 decomposition-gap pattern dominates control findings** (6/10 CROSSREF): single-EARS audits flag sibling-covered behavior. The deployed instrument audits one EARS at a time, so this stays as-is (changing classifier inputs mid-experiment would change the instrument); the false-alarm metric counts only FALSE-ALARM verdicts.
3. **The classifier over-reports; the adjudication layer filters.** 10 findings on 2 untouched specs, of which 1 was a genuine incidental discovery.
4. Harness mechanics validated: seeder realism + ci.sh gate (incl. an intelligent H-seed adaptation around the formally-verified shared rounding primitive), spec-ID stripping for B-direction trees (extended to doc-comment references after a leak was caught pre-launch), schema-forced classifications, blind adjudication inputs, Sol cross-check plumbing.

## Pilot cost

| Stage | Calls | Tokens | Wall-clock |
|---|---|---|---|
| Seeding (Sonnet, incl. 2 T1 self-audits + ci.sh) | 2 | 172k | ~10 min |
| Audit units (Sonnet: 24 gen + 4 classify) | 28 | 1.42M | ~6 min |
| Fable adjudication (4 realness + 2 key-match) | 6 | ~287k | ~2.5 min |
| Sol cross-check | 6 | 195k in / 4k out (≈$1) | ~1.5 min |

Extrapolation: T2 full grid (48 units ≈ 336 calls) ≈ 17M Sonnet tokens, ~60–90 min wall-clock; subsets and EXP arm additional; Fable adjudication layer ≈ 100 units × ~50k.

## T1 self-audit note (from seeding)

Both seeders' T1 self-audits classified their own seeds as drift (B-ONLY-DRIFT / BD-DRIFT) and their assigned controls as BD-COHERENT. T1 recall on seeds is expected to be inflated (the auditor knows the seed); the honest T1 signal is in RESULTS' comparison, and in-context "3 runs" stability is not independent — both stated in the confounds.
