# B10 Seed Plan — SEALED

**Never provide this file, the patches/ directory, or KEY.md to any auditor, classifier, or generation agent.** Only the orchestrator and adjudication layer read it. Written 2026-08-02, before any audit runs.

Baseline: `ba94c01af8eb725292340d83e7923d7ecc136c90` (see `../harness/BASELINE`). One seed per EARS; every sheets-view spec is seeded exactly once (controls are the same specs audited at baseline — paired design per the DESIGN amendment). Class targets: 8 U / 8 P / 8 H. Categories from the gap-log taxonomy named in DESIGN: wire formats, exact constants, error semantics, boundary behavior, tie-breaking.

Seed IDs are `<class>-<EARS suffix>`. The sketch guides the Sonnet seeder; the seeder may adapt within class + category if infeasible (deviations recorded in KEY.md).

## Seeds

| id | class | target EARS | category | sketch |
|---|---|---|---|---|
| U-TAB-002 | U | SHEET-TAB-002 | tie-breaking | tab reorder gains unstated placement rule for unknown/extra tabs (e.g. appended alphabetically); tests pin it |
| U-TAB-004 | U | SHEET-TAB-004 | exact constants | band separation gains unstated fixed blank-row gap constant; tests pin exact count |
| U-FORMULA-001 | U | SHEET-FORMULA-001 | wire formats | engine-written value cells gain unstated explicit number-format metadata; tests pin format strings |
| U-MAP-001 | U | SHEET-MAP-001 | boundary behavior | alias lookup gains unstated symbol normalization (trim/case) before resolution; tests pin it |
| U-MARK-001 | U | SHEET-MARK-001 | error semantics | settle-pass polling gains unstated backoff refinement between polls; tests pin schedule |
| U-MARK-004 | U | SHEET-MARK-004 | boundary behavior | quote-date stamping gains unstated fallback when quote date unparseable (keep prior stamp); tests pin |
| U-PUB-001 | U | SHEET-PUB-001 | error semantics | republish loop gains unstated coalescing/debounce of rapid successive appends; tests pin |
| U-PUB-002 | U | SHEET-PUB-002 | exact constants | batchUpdate write gains unstated row-chunking constant; tests pin chunk size |
| P-TAB-001 | P | SHEET-TAB-001 | wire formats | spec altered to additionally claim column auto-resize on publish; nothing implements it |
| P-TAB-003 | P | SHEET-TAB-003 | boundary behavior | spec altered to claim saved Filter Views are actively re-asserted on republish; code merely avoids destroying them |
| P-FORMULA-003 | P | SHEET-FORMULA-003 | wire formats | spec altered to claim red/green conditional formatting on Net Unrealized; nothing enforces |
| P-FORMULA-005 | P | SHEET-FORMULA-005 | wire formats | spec altered to claim the rate cell is protected against manual edits; nothing enforces |
| P-MAP-002 | P | SHEET-MAP-002 | error semantics | spec altered to claim duplicate-symbol violation also quarantines the row; code only errors loudly |
| P-MARK-005 | P | SHEET-MARK-005 | error semantics | spec altered to claim degraded symbols surfaced in an in-tab banner; nothing does |
| P-MARK-006 | P | SHEET-MARK-006 | error semantics | spec altered to claim one in-pass retry before propagating transport failure; code propagates immediately |
| P-PUB-003 | P | SHEET-PUB-003 | error semantics | spec altered to claim exponential-backoff retry schedule; code retries on next sync only |
| H-TAB-005 | H | SHEET-TAB-005 | exact constants | reserve summary computes one figure locally instead of consuming tax::annual_report's value; tests pin local math |
| H-FORMULA-002 | H | SHEET-FORMULA-002 | boundary behavior | formula start anchoring weakened to data-relative; tests recompute expected rows from data start |
| H-FORMULA-004 | H | SHEET-FORMULA-004 | boundary behavior | one Tax-tab column switched from kernel-exact to live-recomputed estimate; tests narrowed |
| H-MARK-002 | H | SHEET-MARK-002 | exact constants | round_half_to_even → half-away-from-zero; tests updated to pin new rounding |
| H-MARK-003 | H | SHEET-MARK-003 | error semantics | prior-good-mark retention on transient #N/A dropped or window shortened; tests pin narrowed behavior |
| H-MARK-007 | H | SHEET-MARK-007 | boundary behavior | non-finite/non-positive classification narrowed (e.g. ±∞ no longer permanent anomaly); tests narrowed |
| H-MARK-008 | H | SHEET-MARK-008 | wire formats | quote-date serial epoch changed (Sheets 1899 epoch vs spec's 1970); parser + tests adjusted in lockstep |
| H-PUB-004 | H | SHEET-PUB-004 | error semantics | advisory-lock acquisition conditionally skipped; tests adjusted to accept |

Expected detection direction by class (key default, may be refined per seed in KEY.md): U → B-elevation (B-ONLY or BD); P → A-divergence; H → hardest, BD or subtle B.

## Subsets

**Subset seeds** (used by T1, T2-cap, T3, EXP; 3U/3P/2H): U-MAP-001, U-PUB-002, U-MARK-004, P-TAB-003, P-PUB-003, P-FORMULA-005, H-MARK-002, H-MARK-008.

**Subset controls** (same 8 across all subset arms; audited at baseline, except T1 where the paired seeder audits them in its seeded clone): SHEET-TAB-001, SHEET-TAB-005, SHEET-FORMULA-002, SHEET-FORMULA-004, SHEET-MAP-002, SHEET-MARK-003, SHEET-MARK-006, SHEET-PUB-001.

**T1 seed → control assignment**: U-MAP-001→SHEET-FORMULA-002, U-PUB-002→SHEET-MARK-003, U-MARK-004→SHEET-TAB-005, P-TAB-003→SHEET-PUB-001, P-PUB-003→SHEET-MAP-002, P-FORMULA-005→SHEET-MARK-006, H-MARK-002→SHEET-TAB-001, H-MARK-008→SHEET-FORMULA-004.

**Pilot** (seeded, audited, and scored end-to-end before bulk seeding): U-MAP-001 and H-MARK-002, plus their two T1 controls as pilot controls.

## Status

- [x] Pilot seeds authored (U-MAP-001, H-MARK-002) — both ci-green, KEY.md entries + patches + T1 records archived
- [ ] Remaining 22 seeds authored
- [ ] KEY.md complete (all 24 entries, written before grid audits)
