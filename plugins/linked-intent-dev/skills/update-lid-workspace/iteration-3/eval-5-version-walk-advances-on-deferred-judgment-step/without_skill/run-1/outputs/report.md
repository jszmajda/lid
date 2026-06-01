# LID Reconciliation: 1.1.0 -> 1.2.0

## Summary

I walked this project forward from the LID 1.1.0 conventions it recorded to the
current 1.2.0 conventions. The mechanical parts of the walk are done and applied.
One step in the walk is a structural **judgment step** -- I have surfaced it below
with a recommendation and **deferred** it per your instruction, so the walk
advanced past it rather than blocking.

## Applied (mechanical)

- **Version bumped** `CLAUDE.md` `## LID` block: `Version: 1.1.0` -> `1.2.0`.

That is the only file change. Everything else the 1.2.0 migration covers was
either already in place or a no-op for this project (see below).

## Already-conformant / no-op (verified, no action needed)

- **Node-as-folder layout** -- already adopted. The LLD lives at
  `docs/intent/billing/billing-design.md` with its specs beside it at
  `docs/intent/billing/billing-specs.md`. The design-tree root is already
  `docs/intent/` (not the pre-1.2 `docs/llds/`), and there is no leftover
  top-level `docs/specs/` to eliminate.
- **Design-node frontmatter** -- `parent:` and `prefix:` are present on the
  design doc.
- **Spec-file `**LLD**:` header** -- already points at the correct
  `docs/intent/billing/billing-design.md`; no path rewrite required.
- **`@spec` ID rewrite** -- none needed. There is no application code in the
  project, and existing flat IDs (`BILL-001`, `INVOICE-001`) stay valid under
  1.2.0 regardless.
- **`docs/arrows/` overlay** -- not present, so the `index.yaml` schema-v2 bump
  and the `experiments/` -> `_experiments/` rename are both no-ops.
- **Custom coherence-check script** -- none declared under `## LID Tooling`;
  nothing to update.

## DEFERRED -- needs your judgment (surfaced, not blocking)

**The design doc carries a multi-prefix array:** `prefix: [BILL, INVOICE]` in
`docs/intent/billing/billing-design.md`.

Under 1.2.0 this array is an explicit **transient migration marker**, not a
stable state -- the convention is that "a `prefix:` array must not survive the
walk." It exists because one leaf LLD ("Billing") currently owns two distinct
ID prefixes (`BILL-001` = charge a subscription; `INVOICE-001` = issue an
invoice). Resolving it is a judgment call about intent, so per your instruction
I have **left the array in place** and proceeded.

The three sanctioned resolutions:

| Move | What it means here | Resulting IDs |
|---|---|---|
| **Collapse** (recommended) | Charging and invoicing are facets of one cohesive *billing* intent -- keep one leaf, fold the prefixes into within-leaf facets. | `BILLING-CHARGE-001`, `BILLING-INVOICE-001` |
| **Promote** | Treat billing as a sub-HLD parenting separate `charge` and `invoice` leaf LLDs. | `BILLING-CHARGE-001`, `BILLING-INVOICE-001` (via child leaves) |
| **Split** | Treat charging and invoicing as unrelated sibling LLDs with no shared parent. | unchanged `BILL-001`, `INVOICE-001` on two docs |

**Recommendation: collapse to a single `BILLING` leaf.** The design doc already
frames charges, invoices, and dunning together as one billing concern, and there
are only two short specs -- promoting to a sub-HLD would be over-structuring two
one-line requirements, and splitting would scatter tightly-coupled billing
intent across sibling docs. The changelog also notes collapse is "the common
case." Concretely, collapse would:

1. Rename the doc's frontmatter to `prefix: BILLING` (single scalar).
2. Reword the specs to `BILLING-CHARGE-001` and `BILLING-INVOICE-001` using the
   within-leaf `<LEAF>-<TYPE>` facet form.

Note the structural call (which leaf shape) is independent of *when* to do the
`@spec`/ID rewrites it implies -- here there's no code, so the rewrite is just
the two spec lines and is cheap whenever you choose to act.

**Until you decide, the project is on 1.2.0 in every respect except this one
unresolved node**, which remains validly marked by the `prefix:` array as a
known-pending resolution.
