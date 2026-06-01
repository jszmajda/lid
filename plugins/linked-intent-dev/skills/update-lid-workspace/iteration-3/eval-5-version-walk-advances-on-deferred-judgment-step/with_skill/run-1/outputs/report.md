# LID Reconciliation Report

## Summary

Reconciled the project from LID conventions **1.1.0** to the current **1.2.0**. I ran a version-walk across the single intervening release (v1.1 → v1.2), applied the mechanical work, surfaced the one structural decision, and — per your instruction — deferred it while still advancing the version.

**Version set: `- Version: 1.2.0`** in `CLAUDE.md`'s `## LID` block.

## What I detected

- **Project version:** 1.1.0 (lagging the installed 1.2.0) → version-walk applies.
- **Layout:** The billing LLD already lives in the node-as-folder layout — `docs/intent/billing/billing-design.md` plus `docs/intent/billing/billing-specs.md`. The defining structural move of the 1.2 conventions (relocation onto the `docs/intent/` node-as-folder tree) is **already done**.
- **Required artifacts present:** `docs/high-level-design.md` and `docs/intent/` both exist; the `## LID` block is well-formed (both `- Mode:` and `- Version:` bullets); no `docs/arrows/` overlay; no `docs/planning/` directory.
- **One residual marker:** the billing design doc carries a `prefix:` **array** (`prefix: [BILL, INVOICE]`) — an unresolved multi-prefix marker that the v1.2 migration says must not survive the walk.

## v1.1 → v1.2 migration walk

1. **Node-as-folder (mechanical / already satisfied)** — each LLD must live in `docs/intent/<node>/` as `<node>-design.md` (+ `<node>-specs.md`). The billing node already conforms; no relocation needed.
2. **Resolve the `prefix:` array (judgment — DEFERRED)** — see below.

## Applied

- Refreshed `CLAUDE.md` `## LID` → `- Version:` from `1.1.0` to `1.2.0`.

Because the project has already taken the defining structural move of the 1.2 conventions (the node-as-folder layout), it *is* on the 1.2 conventions, so the version bullet advances even though the residual `prefix:`-array cleanup below is deferred. The marker stays in place as the record of the open decision and will be re-surfaced on every later `/update-lid` run until resolved.

## Deferred (needs your judgment) — with recommendation

**The billing LLD declares two prefixes in one node.** `docs/intent/billing/billing-design.md` has `prefix: [BILL, INVOICE]`, and its specs file mixes `BILL-001` ("charge a subscription") and `INVOICE-001` ("issue an invoice") under the single `billing` node. Under 1.2 conventions a node owns exactly one prefix, so this array must eventually be resolved one of three ways:

- **Collapse** into `<LEAF>-<TYPE>` facets under one billing prefix — keep a single `billing` node and re-express the two concerns as facets of one prefix.
- **Promote** `billing` to a sub-HLD over two child leaves (e.g. `docs/intent/billing/charges/` and `docs/intent/billing/invoices/`), each with its own prefix.
- **Split** into two sibling leaf LLDs (e.g. `charges` with `BILL-*` and `invoices` with `INVOICE-*`).

**Recommendation: split into sibling leaves.** Charges and invoices are distinct concerns with already-distinct prefixes (`BILL` vs `INVOICE`) and distinct specs — that maps most cleanly onto two sibling leaf LLDs (`charges`/`BILL-*` and `invoices`/`INVOICE-*`) without inventing the extra grouping layer a sub-HLD promotion would add. Promote instead only if you expect billing to grow more internal structure (dunning, refunds, proration) that would benefit from a shared parent.

**As requested, I did not act on this** — `billing-design.md` is unchanged, the `prefix: [BILL, INVOICE]` array remains in place as the marker of record, and the specs split across `BILL-001`/`INVOICE-001` stays as-is. Resolve it whenever you're ready; the next `/update-lid` will re-surface it.

## Files changed

- `CLAUDE.md` — `## LID` block `- Version:` bullet bumped `1.1.0` → `1.2.0`.

## Files left intentionally unchanged

- `docs/intent/billing/billing-design.md` — carries the deferred `prefix:` array marker.
- `docs/intent/billing/billing-specs.md`, `docs/high-level-design.md` — no drift.
