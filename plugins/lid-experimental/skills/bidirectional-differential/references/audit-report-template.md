# Audit report template

One file per audit, at:

```
docs/arrows/experiments/bidirectional-differential/{segment-name}/{EARS_ID}.md
```

Re-running an audit for the same EARS replaces this file. Commit the prior audit before re-running if before/after comparison matters.

---

## Template

```markdown
# Differential audit — {EARS_ID}

**Audit run**: {ISO-8601 timestamp}
**Git SHA at audit**: {full commit SHA from `git rev-parse HEAD`}
**Runs per direction**: {N} (or "{N} → {M} after 2-vs-1 re-run" if the split-result rule fired)
**Model**: {model ID if recorded}
**Classification**: {BD-COHERENT | A-ONLY-DRIFT | B-ONLY-DRIFT | BIDIRECTIONAL-DRIFT | INCONSISTENT-BLIND | UNANNOTATABLE}
**Default Action**: {acknowledged-coherent | advisory | reconcile-EARS | reconcile-code | triage-required}
**Stripping spot-check**: {pass | suspected-leak (overlap X%)}

## EARS (verbatim)

{one-line quote of the EARS as it appears in `docs/specs/`}

## Code locations

- {path/to/file.ts}:{start}–{end} — {one-line description}
- {path/to/other.ts}:{start}–{end} — {one-line description}
- ...

(Each `@spec {EARS_ID}`-annotated region. If multiple regions span subsystems, note which subsystem each is in.)

## A-direction — EARS → code ({N} runs)

**Convergent behavior**: {what all N A-runs agreed on}

**Divergent choices**: {where A-runs disagreed; list each variant briefly}

**Sub-decisions invented**: {tiebreakers, defaults, edge-case handling each A-run made up on its own}

**Diff against real code**: {one-paragraph summary — where did A-runs agree with the real code, where did they diverge?}

## B-direction — code → EARS ({N} runs)

**Reconstructed EARS** (majority):

> {the EARS text the majority of B-runs produced}

**Elevated invariants**: {specific behaviors B-runs flagged as requirements the EARS doesn't state — e.g., order-preservation, empty-input behavior, pagination, retries}

**Cluster-splits**: {if any B-run reconstructed multiple EARS where the real spec has one, note the decomposition B-runs proposed}

**Diff against real EARS**: {one-paragraph summary — what did the reconstructed EARS say that the real EARS doesn't, and vice versa?}

## Drift findings

- **{finding 1}** — surfaced by {A | B | both}; severity: {possible-bug | latent-refactor-hazard | pure-documentation}
- **{finding 2}** — surfaced by {A | B | both}; severity: {...}
- ...

## Recommended reconciliations

Every non-`BD-COHERENT` finding gets a cascade-shaped recommendation. Fill in the steps that apply; skip steps that don't:

1. **Validate intent with the user**: {the candidate intent surfaced by this audit — either the B-direction's reconstructed EARS or the pattern across the A-runs' divergent implementations — for the user to accept, reject, or refine.}
2. **Check LLD coherence**: {whether `{segment-name}`'s LLD already reflects the validated intent, or needs updating to match. Name the LLD section if an update is needed.}
3. **Update EARS**: {proposed new or additional EARS text; or "add companion unwanted-behavior EARS" with proposed text.}
4. **Update tests**: {which tests need to be added or modified to assert the validated invariant. Tests carry `@spec` citing the updated EARS; if no such test exists today, naming its future location is part of this step.}
5. **Adjust code**: {required code change — or "no change needed" if the intent matches current behavior — including file:line anchors.}

For `advisory` or `acknowledged-coherent` classifications, use:

- **Leave as-is**: {one-line justification.}

## Notes

{Optional free-form notes — context the audit reveals that doesn't fit the fields above. Examples: a surprising convergent pattern, a B-run that disagreed in an interesting way, a stripping-rule concern worth escalating.}
```

---

## Field-by-field guidance

### `Classification`

One of six codes per `classification-codes.md`. Do not invent codes.

### `Default Action`

Auto-populated from the Classification → Action table in `classification-codes.md`. The user may override in the final summary; override decisions do NOT get written back into this file (the audit is a point-in-time record, not a ticket).

### `Stripping spot-check`

Always populated. `pass` when the B-direction's word overlap with the real EARS is ≤ ~70%. `suspected-leak (overlap X%)` when above the threshold — in that case, the reviewer should manually inspect the stripped code input before trusting `BD-COHERENT`.

### `A-direction — Divergent choices`

Don't enumerate every character-level difference. Group by *kind* of divergence: data-structure choice, control-flow shape, error-handling policy, default-value pick. One or two sentences per kind.

### `B-direction — Reconstructed EARS`

When B-runs produce near-identical reconstructions, quote the majority version. When B-runs split, quote each variant with a count (e.g., "2/3 runs:", "1/3 run:"). A 2-vs-1 split at N=3 should have triggered the re-run rule; if a split persists at N=5, the result is `INCONSISTENT-BLIND`, not a classification.

### `Drift findings — severity tags`

- **possible-bug** — the code's behavior diverges from what a reasonable reader of the EARS would expect; if a caller relied on the EARS, they'd be surprised.
- **latent-refactor-hazard** — the code embeds an invariant callers depend on, but the EARS doesn't state it; a later refactor to "match the spec" would break callers.
- **pure-documentation** — the EARS and code behave compatibly for all real callers; only the documentation is drifted.

When in doubt between `possible-bug` and `latent-refactor-hazard`, pick `possible-bug` — it escalates the human review, which is the safer default.

### `Recommended reconciliations`

Concrete, actionable, and arrow-cascade-shaped. The list walks HLD → LLD → EARS → Tests → Code for every non-coherent finding: validate intent with the user first, check LLD coherence, update EARS, update tests, then adjust code. "Update EARS to say X" beats "consider clarifying the EARS." The user will read the list and act on specific items; ambiguous suggestions waste their attention.

Skip steps that don't apply — most audits don't need an LLD edit, and `reconcile-EARS` results usually leave the code untouched. But always name the validation step (1) explicitly: no downstream edit is correct without user-confirmed intent.
