# Differential audit — SCORE-001

**Audit run**: 2026-04-25T20:12:21Z
**Git SHA at audit**: c1944e702dbc20035d1836639f91acd6ef86a720
**Runs per direction**: 3
**Model**: claude-opus-4-7[1m]
**Classification**: BD-COHERENT
**Default Action**: acknowledged-coherent
**Stripping spot-check**: pass (max IoU across B-runs = 26%, threshold ~70%)

## EARS (verbatim)

> When scoring an item X against a reference Y, the system SHALL assign 3 if A(X,Y) and B(X,Y); 2 if A(X,Y) and not B(X,Y); 1 if not A(X,Y) and B(X,Y); 0 if not A(X,Y) and not B(X,Y).

## Code locations

- src/scoring.ts:1-9 — `scorePair(x, y)` four-branch scoring matrix annotated with `@spec SCORE-001`.

## A-direction — EARS → code (3 runs)

**Convergent behavior**: All 3 A-runs produced the literal four-branch matrix
```
if (a && b) return 3;
if (a && !b) return 2;
if (!a && b) return 1;
return 0;
```
which is behaviorally identical to the real `scorePair` body.

**Divergent choices**: Surface-level only — how A and B are supplied to the score function:
- a1: A and B are passed as function parameters.
- a2: A and B are inlined as stub predicates returning `x === y`.
- a3: A and B are passed as function parameters (different identifier casing).

All three keep the same control flow and return values; none invents extra branches, error paths, or normalization steps.

**Sub-decisions invented**: None of operational consequence. A2 chose an arbitrary stub for A/B because the EARS leaves them opaque; A1/A3 chose to inject them. None of these choices changes the matrix's behavior.

**Diff against real code**: A-runs match the real code's matrix exactly. The real code commits to specific A and B predicates (`predicateA = id-length-greater`, `predicateB = id-lexicographic-less`) which the EARS does not pin down — A-runs treated this correctly as out-of-scope for SCORE-001 and either parameterized A/B or stubbed them.

## B-direction — code → EARS (3 runs)

**Reconstructed EARS** (majority — all 3 runs agree on shape):

> When scoring a pair of items, the system shall return 3 if [predicate A holds] and [predicate B holds], 2 if only A, 1 if only B, and 0 otherwise.

(Each B-run substituted the concrete `length >` / lexicographic-less predicates for A and B, since the stripped code retained their bodies; the EARS shape — four-branch matrix on two predicates — is unanimous.)

**Elevated invariants**:
- B-runs surfaced the concrete predicate semantics (id-length comparison, lexicographic comparison). This is a description of the visible predicate bodies in the stripped input, not an unstated invariant in the real EARS — the real EARS deliberately abstracts A and B as opaque predicates, and the predicate definitions would be the subject of separate EARS if they ever needed pinning.
- All B-runs noted ties / non-symmetry edge cases. These are properties of the chosen predicates, not of SCORE-001 itself.

**Cluster-splits**: None. All 3 B-runs reconstructed a single EARS with the same four-branch shape.

**Diff against real EARS**: The reconstructed EARS and the real EARS describe the same four-branch matrix on two predicates. The reconstructions add concrete predicate detail because the B-direction saw concrete predicate bodies; abstracted to the predicate-agnostic level, the reconstructed EARS is structurally identical to SCORE-001. No invariant the real EARS omits is being elevated.

## Drift findings

None of operational severity. The audit confirms intent and code agree on the four-branch scoring matrix.

## Recommended reconciliations

- **Leave as-is**: A-runs and B-runs converge on the real artifact in both directions. SCORE-001 and `src/scoring.ts:1-9` are mutually self-reconstructable. Audit record kept as a coherence baseline.

## Notes

- The B-runs concretizing A and B is a feature of the stripped input, not drift. SCORE-001's job is to specify the *matrix shape*, not to specify which predicates A and B are; the predicates would belong to their own EARS (if any). The stripping rules already permit predicate bodies to remain because removing them would change behavior, not just vocabulary.
- All 6 subprocesses returned cleanly (no timeouts, no errors). Model recorded as `claude-opus-4-7[1m]` from the `modelUsage` field of each session's JSON output.
- Stripping spot-check IoU values per B-run vs real EARS: b1=23.08%, b2=25.64%, b3=21.43% — comfortably below the ~70% leak threshold.
