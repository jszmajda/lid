# SCORE-001 Audit

## Assessment

The spec and code agree. SCORE-001 specifies a four-branch truth table over predicates A(X,Y) and B(X,Y) yielding {3, 2, 1, 0}. The implementation in `src/scoring.ts` realizes that table exactly:

| A    | B    | Spec | Code               |
|------|------|------|--------------------|
| T    | T    | 3    | `aOk && bOk` → 3   |
| T    | F    | 2    | `aOk && !bOk` → 2  |
| F    | T    | 1    | `!aOk && bOk` → 1  |
| F    | F    | 0    | fallthrough → 0    |

The final `return 0` covers the `!aOk && !bOk` case because the three preceding branches exhaustively cover the others.

## Drift

None of substance. Two minor notes:

1. The spec is abstract about what A and B mean. The code provides concrete toy predicates (A: `x.id.length > y.id.length`; B: `x.id < y.id`). Because the spec doesn't constrain them, this is consistent rather than contradictory — but it leaves room for silent semantic drift if the predicates change later.
2. HLD and LLD are near-empty stubs. They do not contradict the spec; they just don't add much.

## Recommendation

No action required for spec/code coherence. Optionally, add a sentence to `docs/llds/scoring.md` describing the intended meaning of predicates A and B so future predicate changes cascade through documented intent. The arrow overlay's `status: OK` is accurate as of this audit.
