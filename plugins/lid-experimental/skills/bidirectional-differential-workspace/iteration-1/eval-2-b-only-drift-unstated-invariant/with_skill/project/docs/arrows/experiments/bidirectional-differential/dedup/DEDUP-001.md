# Differential audit — DEDUP-001

**Audit run**: 2026-04-24T23:11:00Z
**Git SHA at audit**: c1944e702dbc20035d1836639f91acd6ef86a720
**Runs per direction**: 3
**Model**: claude-opus-4-7[1m] (driver); subprocess `claude -p` default model
**Classification**: B-ONLY-DRIFT
**Default Action**: reconcile-EARS
**Stripping spot-check**: pass (overlap ~23%)

## EARS (verbatim)

> The system SHALL deduplicate a list of IDs.

## Code locations

- src/dedup.ts:1–13 — `uniqueIds(ids)` returns a new array with duplicates removed; explicit early-return for empty input; loop accumulates output preserving first-occurrence order via a `Set` of seen IDs.

## A-direction — EARS → code (3 runs)

**Convergent behavior**: All 3 A-runs produced the identical one-liner `export function deduplicate(ids: string[]): string[] { return [...new Set(ids)]; }`. Behaviorally this matches the real code on every input: empty input yields `[]`, and Set spread preserves insertion order in JavaScript, so first-occurrence order is preserved.

**Divergent choices**: None observed — A-runs were essentially byte-identical.

**Sub-decisions invented**: None explicitly invented; the A-runs leaned on `Set` semantics (insertion-order iteration) rather than encoding any visible commitment to ordering or empty-input handling. They produced no explicit empty-input guard and no comment about ordering — they made the simplest call and got equivalent behavior implicitly.

**Diff against real code**: The real code spells out two things the A-runs leave implicit: an explicit `if (ids.length === 0) return [];` early return, and a hand-written loop with a `seen` set that *names* first-occurrence order as a deliberate choice. Behaviorally there is no observable difference on the input domain `readonly string[]`. Structurally, the real code is more defensive — its shape signals intent that the one-liner does not.

## B-direction — code → EARS (3 runs)

**Reconstructed EARS** (majority — all 3 runs agreed on substance):

> The system shall return the input list of IDs with duplicates removed, preserving the first-occurrence order of each unique ID.

(B1: "…preserving the order of first occurrence." B2: "…preserving the first-occurrence order of each unique ID." B3: "…preserving the order of their first occurrence." All three elevate first-occurrence order; none mentions the empty-input case explicitly, though it is implicit in "return the input IDs with duplicates removed".)

**Elevated invariants**:
- **First-occurrence order preservation**. All 3 B-runs explicitly named this. The real EARS does not.
- **Empty-input safety** — implicit but not explicitly elevated by the B-runs. (The real code's explicit empty-input branch is a defensive guard that does not change observable behavior; B-runs evidently treated it as an unremarkable special case rather than an invariant worth naming.)

**Cluster-splits**: None. All 3 B-runs produced a single-EARS reconstruction; no decomposition split was suggested.

**Diff against real EARS**: The reconstructed EARS adds "preserving the first-occurrence order" — a behavioral guarantee absent from the real EARS. The real EARS underspecifies: it would also be satisfied by an unordered `Set`-based implementation that does not commit to first-occurrence order. The reconstructed EARS would *not* be satisfied by, say, a sorted-output implementation, which the real EARS technically permits.

## Drift findings

- **Order-preservation invariant unstated** — surfaced by B; severity: latent-refactor-hazard. A future "simplification" to `[...new Set(ids)]` is behaviorally equivalent in current JS engines but is not portable to languages or hash-set abstractions where insertion order is unspecified. Callers that depend on first-occurrence order (e.g., when IDs encode a priority sequence) would silently break under such a refactor that "matches the spec".
- **Empty-input handling unstated** — surfaced by code (real code has an explicit branch); severity: pure-documentation. Behavior is the same with or without the explicit branch in TypeScript; the early return is a stylistic guard, not a behavioral commitment. No reconciliation pressure here on its own.

## Recommended reconciliations

1. **Validate intent with the user**: confirm whether first-occurrence order is a guaranteed contract of `uniqueIds`. The B-direction's reconstructed EARS — *"The system shall return the input list of IDs with duplicates removed, preserving the first-occurrence order of each unique ID."* — is the candidate intent. If callers do depend on first-occurrence order (likely, given the explicit loop+seen-set shape of the real code), accept it; if not, reject and treat the existing code as over-specified.
2. **Check LLD coherence**: `docs/llds/dedup.md` currently says only "Deduplicate a list of IDs." It does not name the order invariant. If intent is confirmed, the LLD's Context section should explicitly note that the dedup preserves first-occurrence order.
3. **Update EARS**: replace `DEDUP-001` text with: *"The system SHALL deduplicate a list of IDs, preserving first-occurrence order."* No companion unwanted-behavior EARS is needed — the positive statement covers it.
4. **Update tests**: there is no test file for `dedup.ts` currently. Add `src/dedup.test.ts` (or equivalent) carrying `@spec DEDUP-001` and asserting (a) duplicates are removed, (b) the first occurrence's position is preserved (e.g., `uniqueIds(['b','a','b','c','a']) === ['b','a','c']`), and (c) empty input returns `[]`.
5. **Adjust code**: no change needed. The current implementation already satisfies the validated intent at src/dedup.ts:1–13.

## Notes

A-direction convergence was unusually tight — all three runs produced the same one-liner. This is signal that the EARS as written admits a single dominant naive reading (use `Set`), and that the real code's *additional* defensive shape (explicit empty-input branch, named seen-set loop) is doing intent-encoding work the EARS itself does not. Classification rests on the B-direction: every B-run independently elevated first-occurrence order, which the real EARS does not state. That uniform elevation against a sparse real EARS is the textbook B-ONLY-DRIFT signature.
