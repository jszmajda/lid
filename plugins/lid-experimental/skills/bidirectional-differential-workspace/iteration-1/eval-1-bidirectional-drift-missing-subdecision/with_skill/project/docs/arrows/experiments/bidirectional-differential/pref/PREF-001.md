# Differential audit — PREF-001

**Audit run**: 2026-04-25T20:12:16Z
**Git SHA at audit**: c1944e702dbc20035d1836639f91acd6ef86a720
**Runs per direction**: 3
**Model**: claude (default via `claude -p`)
**Classification**: BIDIRECTIONAL-DRIFT
**Default Action**: triage-required (this finding: reconcile-code — see drift findings)
**Stripping spot-check**: pass (max overlap 20.0% across B-runs; below ~70% threshold)

## EARS (verbatim)

> The system SHALL prefer the primary value X over the secondary value Y when rendering an item.

## Code locations

- src/pref.ts:1–10 — `renderItems(items)`: iterates a list of items, picks `primary || secondary || ''` per item, skips items whose resolved text is empty.

## A-direction — EARS → code (3 runs)

**Convergent behavior**: All 3/3 runs produced the same function — `function render(x, y) { return x ?? y; }` — a single-pair preference function returning `x` when defined, otherwise `y`.

**Divergent choices**: None across A-runs (full convergence on the simplest naive reading).

**Sub-decisions invented**: All A-runs implicitly chose:
- A pair-wise function over a single item, not a list-iteration function.
- Nullish-coalescing (`??`) — falls back only on `null`/`undefined`, not on empty string.
- No "both missing" fallback (no default value, no skip).
- Non-optional `y` parameter (assumes a fallback always exists).

**Diff against real code**: A-runs and the real code disagree on three behaviorally observable axes. (1) Surface: A-runs handle a single pair; real code iterates a list and returns a list of strings. (2) Falsy semantics: A-runs use `??` (only `null`/`undefined` triggers fallback); real code uses `||` (empty string also triggers fallback). (3) "Both missing" handling: A-runs simply return the second value; real code falls back to `''` and then *skips* the item entirely via `if (!text) continue;`. None of these three axes is mentioned in the EARS.

## B-direction — code → EARS (3 runs)

**Reconstructed EARS** (majority — 3/3 convergent in semantics, with minor wording variation):

> When rendering a list of items, the system shall emit each item's primary value if present and non-empty, otherwise its secondary value if present and non-empty, and shall omit items for which neither yields a non-empty string.

**Elevated invariants**:
- The function operates over a **list** of items, not a single pair (B-1, B-2, B-3 all open with "When rendering a list of items").
- "Empty" treatment uses **truthiness**, not just nullishness — empty strings fall through to the secondary value (B-1 calls this out explicitly: "empty-string a falls through to b due to truthiness, not just undefined").
- **Skip-on-empty**: items where both values are absent/empty are *omitted* from the output (all 3 B-runs include this clause: "omit items where both are absent/empty" / "omit items for which neither yields a non-empty string" / "omitting items where both are missing or empty").

**Cluster-splits**: None. All three B-runs reconstructed a single compound EARS covering the same three invariants.

**Diff against real EARS**: The real EARS is silent about (1) list iteration, (2) empty-vs-missing semantics, and (3) skip-on-empty. The reconstructed EARS makes all three explicit. The reconstructed EARS does NOT include "primary X / secondary Y" naming (the stripped code uses neutral identifiers `a`/`b`), so the reconstructions describe the same behavior in different vocabulary — the semantic content is what aligns and what diverges, not the words.

## Drift findings

- **Silent skip when both fields are missing/empty** — surfaced by both directions (A-runs miss it, B-runs elevate it); severity: **possible-bug**. The code drops items whose `primary` and `secondary` are both absent or empty without logging or signaling. If callers assume the output array length matches the input, or if "both missing" reflects an upstream data-pipeline failure, this masks a real issue. The EARS gives no guidance; the code makes a specific, opinionated choice.
- **`||` vs `??` (empty-string treated as falsy)** — surfaced by both directions; severity: **latent-refactor-hazard**. A maintainer reading only the EARS would reach for `??` (matching the A-direction's choice), changing observable behavior for items where `primary === ''` and `secondary` is non-empty. Today's code treats those items as "use secondary"; an EARS-faithful refactor would treat them as "use primary (empty)". Callers may depend on the current behavior.
- **List-iteration shape** — surfaced by both directions; severity: **latent-refactor-hazard**. The EARS describes single-item rendering; the implementing artifact is a list mapper-with-filter. A reasonable EARS reader could implement this as `renderItem(item)` and place the iteration elsewhere, fragmenting the skip-on-empty invariant across modules.

## Recommended reconciliations

This is a `BIDIRECTIONAL-DRIFT` finding — triage-required. The dominant severity is **possible-bug** (silent skip), so the cascade starts at `reconcile-code`, but the EARS update is also required to capture the validated invariants.

1. **Validate intent with the user**: Confirm with the user which behavior is intended:
   (a) silently skip items where both `primary` and `secondary` are missing/empty (current code), or
   (b) emit a sentinel/empty string and let downstream handle it, or
   (c) raise/log on "both missing" because it indicates upstream data corruption.
   Also confirm whether empty-string `primary` should fall through to `secondary` (`||` semantics, current code) or be treated as an explicit value (`??` semantics). Also confirm the function's surface: list-mapper (current) or single-item function with iteration elsewhere.
2. **Check LLD coherence**: `docs/llds/pref.md` currently says only "Prefer a primary value over a fallback when rendering items." It needs to spell out (i) list semantics, (ii) empty-string treatment, and (iii) what happens when both values are missing. Add a "Sub-decisions" section under Context with explicit choices for each.
3. **Update EARS**: Replace PREF-001 with two (or more) EARS that pin down the validated sub-decisions. Suggested structure:
   - `PREF-001`: "When rendering a list of items, the system shall emit one string per item using the primary value if present and non-empty, otherwise the secondary value if present and non-empty."
   - `PREF-002`: "If neither the primary nor the secondary value is present and non-empty for an item, then the system shall {omit the item from the output | emit an empty string | raise an error}." (User picks the verb in step 1.)
   - Optionally `PREF-003` (companion unwanted-behavior EARS): "The system SHALL NOT silently produce an output array shorter than the input array without surfacing the discrepancy." — only if the user picks "omit" in PREF-002 and wants to preserve the current behavior with explicit acknowledgement.
4. **Update tests**: No tests exist today for `src/pref.ts`. Add (at minimum):
   - A test asserting primary-wins-when-present (`@spec PREF-001`).
   - A test asserting secondary-fallback-when-primary-empty-string (`@spec PREF-001`) — pins the `||`-vs-`??` decision.
   - A test asserting the both-missing behavior chosen in step 1 (`@spec PREF-002`). Future audits can target the test file once the production sink is small.
5. **Adjust code**: Depends on user's choice in step 1.
   - If "omit silently" remains the intended behavior: no code change needed; the EARS and tests now match.
   - If "emit empty string" is preferred: drop the `if (!text) continue;` line at `src/pref.ts:6`.
   - If "raise/log on both missing" is preferred: replace the `continue` with a thrown error or warning at `src/pref.ts:6`, and update the function signature/return contract accordingly.

## Notes

- A-direction convergence was unusually tight (3/3 byte-identical TypeScript). This is a strong signal that the EARS as written admits a single naive reading, and the real code's deviation from that naive reading is the entire content of this finding.
- The stripping spot-check came in well under threshold (~17–20% overlap) — confirming the B-direction reconstructions are about behavior the code exhibits, not vocabulary the code carries. The renamings `primary→a`, `secondary→b` and the removal of the `@spec` annotation were the load-bearing strips; nothing else in the code echoed EARS vocabulary.
- B-1 explicitly named the `||`-vs-`??` distinction ("falls through to b due to truthiness, not just undefined") even though the prompt only asked for an EARS reconstruction. That observation is the seed of the *latent-refactor-hazard* finding above and worth preserving.
