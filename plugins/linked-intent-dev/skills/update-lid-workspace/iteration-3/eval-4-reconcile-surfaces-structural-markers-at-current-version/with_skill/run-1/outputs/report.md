# LID reconciliation report

I reconciled this project against the current LID conventions (`linked-intent-dev` v1.2.0). Here is what I found and did.

## Detected state

- **LID directives**: present in `CLAUDE.md`.
- **`## LID` block**: present and well-formed — `Mode: Full`, `Version: 1.2.0`.
- **Version**: project is at 1.2.0, equal to the installed conventions version. **No version-walk needed.**
- **Required layout**: `docs/high-level-design.md` and `docs/intent/` both present.
- **Arrow overlay** (`docs/arrows/`): absent — no navigation rows for it are needed, none added.
- **`docs/planning/`**: absent — nothing to flag.

Because the project is already at the installed version, this was a **reconcile-conventions** pass. The two structural markers below are detected and re-surfaced independently of version lag — a project at the current version still has them surfaced (with a recommended resolution, never silently left, never auto-resolved).

## What I changed (mechanical, applied)

- **Refreshed the `## Linked-Intent Development` directives block in `CLAUDE.md`** to match the current template. The block had drifted to a single one-line consult directive, missing the arrow diagram, the change-type bullets (new features / bug fixes / if-unsure), the stop-after-phase + "docs read cold" guidance, and the Navigation / Terminology / Code-annotations sections. I rewrote it to the current template.
  - Conditional-include rules applied: Full mode, so **no `## LID Scope` section**; no `docs/arrows/`, so **no "Arrow of intent overlay" navigation row**; no project tooling to declare, so **no `## LID Tooling` section**.
  - Preserved: the `# My Project` title and the existing well-formed `## LID` block (untouched).

## What I surfaced — recommendations only, NOT applied (judgment calls)

These require a structural decision, so per the skill I am surfacing each with a concrete recommendation but leaving the files unchanged. The markers stay in place so they re-surface on the next `/update-lid` run until resolved.

### 1. Payments LLD carries two prefixes (multi-prefix marker)

`docs/intent/payments/payments-design.md` declares `prefix: [PAY, FEE]` (a `prefix:` array). A design doc's `prefix:` must be a single scalar; an array is an unresolved multi-prefix marker. Its specs (`payments-specs.md`) carry both `PAY-001` (charge a card) and `FEE-001` (record a processing fee).

**Recommendation — your call between:**
- **Collapse** into `<LEAF>-<TYPE>` facets under one Payments leaf if charging and fees are one coherent component with two facets (e.g. `PAYMENT-CHARGE-001`, `PAYMENT-FEE-001`), giving `payments-design.md` a single scalar `prefix:`; **or**
- **Split** Payments into two sibling leaf nodes — a charges node (`PAY`) and a processing-fees node (`FEE`) — each its own folder with its own single-prefix design + specs.

My lean: these read as two facets of one payments component (a charge and its associated fee), so **collapse to facets** is the lighter-weight fit — but confirm whether fees deserve independent lifecycle/ownership, which would favor split.

### 2. Orders folder holds an un-promoted refund sub-LLD (overloaded-folder marker)

`docs/intent/orders/` carries more than its `orders-design.md` + `orders-specs.md` pair: it also contains `orders-refund-design.md` and `orders-refund-specs.md` (specs under prefix `REFUND`). That is a second LLD left as extra files in the parent folder instead of relocated into its own child node folder — the un-promoted-sub-LLD marker. The refund design doc even states this explicitly ("left as an extra file in the orders folder instead of relocated into its own child node folder").

**Recommendation — promote** the refund LLD into its own child folder under Orders:
- `docs/intent/orders/refund/refund-design.md`
- `docs/intent/orders/refund/refund-specs.md`

Add `parent: orders` and a single scalar `prefix:` to the promoted design doc. Note the current refund specs use a flat `REFUND-001` ID; on promotion under Orders, path-concatenated IDs would make this `ORDER-REFUND-001` (the root-to-leaf path). Promoting Orders to a sub-HLD (it would then group a refund child) versus keeping Orders as a leaf with a nested refund leaf is itself part of this decision — confirm the intended shape.

## Summary

- Applied: 1 mechanical fix (CLAUDE.md directives block refreshed to the current template).
- Surfaced for your decision (not applied): 2 structural markers — the `[PAY, FEE]` prefix array on Payments, and the un-promoted refund sub-LLD in the Orders folder.
- Version bullet: unchanged (already 1.2.0, current).

Tell me to proceed on either structural item and I will apply the chosen resolution.
