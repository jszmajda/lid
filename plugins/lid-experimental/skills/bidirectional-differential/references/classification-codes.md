# Classification codes

Six codes. Five are coherence classifications; `UNANNOTATABLE` is a signpost for EARS that are structurally out of scope for this technique.

Each section gives the decision rule, a worked example, and the default Action.

---

## `BD-COHERENT`

**Decision rule**: Both directions converge on the real artifact. A-runs produce code that matches the real code's behavior; B-runs reconstruct an EARS that matches the real EARS. Intent and code are mutually self-reconstructable.

**Example**:
- EARS: *"When scoring an item X against a reference Y, the system shall assign: 3 if A and B; 2 if A and not B; 1 if not A and B; 0 if not A and not B."*
- Code: the literal four-branch matrix.
- A-runs (N=3): all produce the same four-branch matrix with the same branch values.
- B-runs (N=3): all reconstruct *"…shall assign 3/2/1/0 depending on A∧B, A∧¬B, ¬A∧B, ¬A∧¬B"* (same semantics).
- Stripping spot-check: B-runs' word overlap with real EARS is ~40% — below threshold.

**Classification**: `BD-COHERENT`. Nothing to reconcile.

**Default Action**: `acknowledged-coherent`. The audit record exists as evidence for later audits.

---

## `A-ONLY-DRIFT`

**Decision rule**: A-runs diverge from the real code (multiple valid implementations satisfy the EARS); B-runs converge on the real EARS. The EARS under-pins an arbitrary implementation choice, but the drift is not semantic.

**Example**:
- EARS: *"The system shall return the k most recently created entries from a collection."*
- Code: `collection.sort((a, b) => b.createdAt - a.createdAt).slice(0, k)`.
- A-runs: one uses `sort+slice`; one uses a min-heap of size k; one uses `partialSort`; all produce behaviorally-equivalent output.
- B-runs: all reconstruct *"shall return the k most recently created entries"* (or near-equivalent).

**Classification**: `A-ONLY-DRIFT`. The code made a legitimate implementation choice the EARS did not pin down.

**Default Action**: `advisory`. Usually fine. Escalate to `reconcile-EARS` only if A-runs diverge on something a reader would expect pinned down (e.g., tie-breaking on equal `createdAt` timestamps when the choice has observable consequences).

---

## `B-ONLY-DRIFT`

**Decision rule**: A-runs converge on the real code; B-runs elevate unstated invariants that the real EARS does not mention. The code encodes intent the EARS does not state.

**Example**:
- EARS: *"The system shall deduplicate a list of IDs."*
- Code: a dedup implementation that *also* preserves first-occurrence order *and* is stable on empty input.
- A-runs: produce various dedup implementations — some order-preserving, some `Set`-based (unordered), some discarding the empty-input case.
- B-runs: uniformly reconstruct *"shall deduplicate a list of IDs while preserving first-occurrence order and returning an empty result for an empty input"*.

**Classification**: `B-ONLY-DRIFT`. Order-preservation and empty-input stability are invariants the code guarantees but the EARS does not state.

**Default Action**: `reconcile-EARS`. Update the EARS to cite the invariants B-runs elevated. The code is correct; the documentation lags.

---

## `BIDIRECTIONAL-DRIFT`

**Decision rule**: Both directions disagree with ground truth in *correlated* ways. A-runs miss what the code does; B-runs elevate what the code does; the missing/elevated content overlaps. Highest-signal finding — usually a missing sub-decision, operational halo, or decomposition gap.

**Example (missing sub-decision)**:
- EARS: *"The system shall prefer X over Y."*
- Code: `const text = X || Y || ''; if (!text) continue;`
- A-runs: produce `X ?? Y`, `X || Y`, `X || Y ?? ''` — each picks a different tiebreaker for "both missing."
- B-runs: uniformly reconstruct *"shall prefer X over Y, falling back to empty string when both are missing, and skip items with no value"* — elevating the empty-string default AND the skip-on-empty behavior.

**Classification**: `BIDIRECTIONAL-DRIFT`. The EARS under-specifies; the code makes a specific choice; A-direction invents different choices; B-direction names the choice as an invariant.

**Triage per finding**:
- If the code's specific choice is **wrong** (e.g., silently dropping items masks a real upstream bug) → `reconcile-code`.
- If the code's choice is **correct but under-documented**, and changing it would break callers → `reconcile-EARS` (a *latent-refactor-hazard*).
- If the choice is documented elsewhere (test comment, commit message) and no user-visible behavior changes → `reconcile-EARS` (pure-doc).

The drift-findings list in the audit record distinguishes these three severities.

**Default Action**: Triage required.

---

## `INCONSISTENT-BLIND`

**Decision rule**: Within-direction variance is too high to classify. A-runs diverge wildly, B-runs diverge wildly, or both. Running N=5 does not resolve the divergence. Usually means the EARS itself is under-specified — different fresh readers reasonably interpret it differently.

**Example**:
- EARS: *"The system shall handle errors gracefully."*
- Code: some specific error handling (e.g., retry 3 times with backoff, log, return 500).
- A-runs: one silently swallows; one logs and re-throws; one returns 400; one retries with exponential backoff.
- B-runs: one reconstructs *"shall retry on transient errors"*; one reconstructs *"shall log and return 500"*; one reconstructs *"shall catch exceptions"*.

**Classification**: `INCONSISTENT-BLIND`. "Gracefully" means too many things.

**Default Action**: `reconcile-EARS` — refine the EARS first (pick a specific behavior: retry with backoff, timeout, structured error response) and re-audit. Do not force a coherence code on an under-specified EARS.

---

## `UNANNOTATABLE` (signpost, not a coherence classification)

**Decision rule**: The EARS is a *negative requirement* ("shall NOT X") with no production-code sink to annotate. There is no code region the audit can target — the requirement's satisfaction is an absence.

**Example**:
- EARS: *"The system shall NOT mutate the input collection."*
- Code: does not mutate. There is no line of code whose purpose is "don't mutate" — correctness is an absence.

**Classification**: `UNANNOTATABLE`. Do not force one of the five coherence codes.

**Signpost recommendations**:

1. **Pair with an unwanted-behavior EARS and a test**. Add a sibling spec like *"If the input collection is modified after the call returns, then the system has violated its contract"* and write a test that asserts the non-mutation. The test carries the `@spec`, and future audits target the test file (which now has a positive sink).
2. **Defer to a sibling absence-audit experiment**. If a CodeQL-backed or runtime-based absence-audit skill exists (or is later built), route these EARS to it.

**Default Action**: `advisory` (the signpost itself). Do not attempt coherence classification.

---

## Classification → Action mapping (summary)

| Classification | Default Action | Rationale |
|---|---|---|
| `BD-COHERENT` | `acknowledged-coherent` | Nothing to reconcile. |
| `A-ONLY-DRIFT` | `advisory` | Arbitrary implementation choice; usually fine. |
| `B-ONLY-DRIFT` | `reconcile-EARS` | Code encodes real intent the EARS doesn't state. |
| `BIDIRECTIONAL-DRIFT` | *triage required* | possible-bug → `reconcile-code`; latent-refactor-hazard → `reconcile-EARS`; pure-doc → `reconcile-EARS`. |
| `INCONSISTENT-BLIND` | `reconcile-EARS` (refine, re-audit) | EARS is the root cause of ambiguity. |
| `UNANNOTATABLE` | `advisory` (signpost) | Out of technique; route to sibling mechanism. |

The Action value names the layer the repair **starts with**. The actual repair walks the full arrow — HLD → LLD → EARS → Tests → Code — in that order, always beginning with validating the discovered intent with the user and checking LLD coherence before editing any EARS, tests, or code. See SKILL.md §"Repair path — cascade through the arrow" for the detailed flow.

Surface the default in the audit record; the user confirms or overrides before committing reconciliation work.
