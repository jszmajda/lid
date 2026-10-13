# B10 Human Adjudication Record (2026-08-03)

Adjudicator: Jess Szmajda. Mandated by the pre-registered trigger: Fable↔Sol adjudication agreement 112/134 (83.6%) < 0.85 (132/156 = 84.6% including the pilot sample). All 22 disagreements were walked through with both judges' reasoning and ruled individually. Final rulings sided with Fable 12 times, Sol 10 times — no family-leniency direction in either the disagreements or the resolutions.

## Rulings

| # | Item | Arm | Unit | Dispute (Fable/Sol) | Ruling |
|---|---|---|---|---|---|
| 1 | R07 S1[7] | T2CAP | FORMULA-004 ctrl | CROSSREF / FALSE-ALARM | **FALSE-ALARM** |
| 2 | R07 S4[0] | EXP-LUNA | FORMULA-004 ctrl | CROSSREF / FALSE-ALARM | **FALSE-ALARM** |
| 3 | R07 S5[1] | T2 | FORMULA-004 ctrl | CROSSREF / FALSE-ALARM | **FALSE-ALARM** |
| 4 | R07 S5[3] | T2 | FORMULA-004 ctrl | FALSE-ALARM / REAL | **FALSE-ALARM** |
| 5 | R07 S1[9] | T2CAP | FORMULA-004 ctrl | CROSSREF / REAL | **CROSSREF** |
| 6 | R07 S3[1] | T3 | FORMULA-004 ctrl | CROSSREF / REAL | **CROSSREF** |
| 7 | R07 S5[0] | T2 | FORMULA-004 ctrl | CROSSREF / REAL | **REAL** (unstated Tax band schemas; consistency with the Positions-schema ruling) |
| 8 | R03 S2[0] | T3 | FORMULA-002 ctrl | CROSSREF / REAL | **CROSSREF** (principle 1 below) |
| 9 | R03 S5[0] | T2CAP | FORMULA-002 ctrl | CROSSREF / REAL | **CROSSREF** (principle 1) |
| 10 | R03 S4[0] | EXP-HAIKU | FORMULA-002 ctrl | REAL / FALSE-ALARM | **REAL** (direct-ref mechanism test-pinned, unstated) |
| 11 | R03 S5[1] | T2CAP | FORMULA-002 ctrl | REAL / FALSE-ALARM | **REAL** (enforcement gap: "each" leak-guarded for 1 of 7 columns) |
| 12 | R03 S5[2] | T2CAP | FORMULA-002 ctrl | REAL / CROSSREF | **REAL** (production tail-truncation gap; Sol's dissent partly an evidence-access artifact) |
| 13 | R03 S5[3] | T2CAP | FORMULA-002 ctrl | REAL / FALSE-ALARM | **REAL** (header verified only in fakes; consistent with #11) |
| 14 | R03 S5[5] | T2CAP | FORMULA-002 ctrl | REAL / CROSSREF | **REAL** (unstated read contract: hardcoded columns, Date(0) fallback) |
| 15 | R03 S5[7] | T2CAP | FORMULA-002 ctrl | REAL / CROSSREF | **REAL** (silent-zero degradation of =G×H on empty rate cell) |
| 16 | R10 S1[1] | T2 | FORMULA-005 seed | REAL / FALSE-ALARM | **FALSE-ALARM** (principle 2) |
| 17 | R10 S2[2] | EXP-HAIKU | FORMULA-005 seed | REAL / FALSE-ALARM | **FALSE-ALARM** (principle 2) |
| 18 | R10 S4[4] | T2CAP | FORMULA-005 seed | REAL / FALSE-ALARM | **FALSE-ALARM** (principle 2) |
| 19 | R10 S1[5] | T2 | FORMULA-005 seed | FALSE-ALARM / REAL | **FALSE-ALARM** (spec's own parenthetical sanctions the mechanism) |
| 20 | R18 S5[2] | T2 | MARK-002 seed | CROSSREF / REAL | **REAL** (SCALE pipeline rider; consistency with prior SCALE rulings) |
| 21 | R18 S5[3] | T2 | MARK-002 seed | CROSSREF / FALSE-ALARM | **FALSE-ALARM** |
| 22 | K17 S5 | EXP-HAIKU | U-PUB-002 keymatch | detected / not detected | **NOT DETECTED** ("detection that reassures isn't detection": Haiku found the chunking mechanism but framed it as harmless surplus, missing the half-written-window violation) |

## Principles established (Jess, verbatim in substance)

1. **A sibling can drive an exception on a universal claim.** Otherwise universal claims would be too hard to write and would collect endless "unless…" amendments. A universally-quantified EARS whose exception is stated by a sibling is a CROSSREF (missing cross-reference), not drift. (Items 8, 9.)
2. **Spec silence over genuinely unclosed intent space is not drift.** REAL requires a concrete commitment on one side that the other doesn't match (a pin or a claim); a load-bearing shared silence is an open question, reported as under-specification signal, not counted as a drift finding. (Items 16–18.) **Follow-up noted for LID generally: this is exactly what the intent-narrowing edge-audit phase should help identify and close — unclosed intent space surfaced by A-run assumption divergence is a first-class edge-detection input.**

## Net effect

Recall unchanged at every arm except EXP-Haiku (5/8; U column 1/3). T2 stays 23/24 with Class H 8/8. Control false-alarm rates: T2 9/120 (7.5%), Opus 2/77 (2.6%), Terra 0/42, Luna 1/43 (2.3%), Haiku 1/18 (5.6%). One incidental discovery added (unstated Tax band column schemas). Final tallies in `../scoring-final.json`; pre-human baseline preserved in `../scoring.json`.
