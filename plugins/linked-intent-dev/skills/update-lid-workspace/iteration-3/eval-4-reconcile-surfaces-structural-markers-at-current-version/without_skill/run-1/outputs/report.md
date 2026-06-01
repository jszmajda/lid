# LID Reconciliation Report

**Project:** My Project
**LID mode:** Full · **Version:** 1.2.0 (matches installed `linked-intent-dev` 1.2.0)

## Summary

The project's `## LID` block already records the current conventions version (1.2.0), so this was a **reconcile-conventions** pass, not a version-walk. No release migrations applied. The pass surfaced and resolved two *structural markers* — exactly the un-finished-walk residue that 1.2 reconcile re-surfaces even at the current version — plus CLAUDE.md directive drift.

## What was found and done

### 1. Overloaded node folder: `docs/intent/orders/` (resolved -> promote)

`docs/intent/orders/` held more than its `orders-design.md` + `orders-specs.md` pair — it also carried `orders-refund-design.md` and `orders-refund-specs.md`, an un-promoted refund sub-LLD left as extra files (the refund design doc even narrated this). A node folder may hold either a `-specs.md` (leaf) or child folders (sub-HLD), never loose sibling LLD files.

**Resolution — promote.** Orders carries two distinct intents under one parent (order lifecycle + a refund sub-flow), so `orders` became a **sub-HLD** over two leaf children:

- `orders/orders-design.md` — rewritten as a sub-HLD (owns no EARS; its `orders-specs.md` was removed since EARS move down to the leaves).
- `orders/lifecycle/` — new leaf, `prefix: ORDER-LIFECYCLE`. The former `ORDER-001` ("create an order") became `ORDER-LIFECYCLE-001`.
- `orders/refund/` — new leaf, `prefix: ORDER-REFUND`. The former `REFUND-001` became `ORDER-REFUND-001` (now path-concatenated under its parent, so `grep ORDER` gathers the whole subtree).

The refund LLD body lost its "left as an extra file…" narration — that was history-of-change residue under *docs carry current intent*; the doc now reads as authored fresh.

### 2. `prefix:` array on `payments-design.md` (resolved -> collapse)

`payments-design.md` carried `prefix: [PAY, FEE]` — a multi-prefix array, a transient migration marker that must not survive reconciliation. Payments is a single intent ("charges and the processing fees recorded against them"); the fee is a facet of a charge, not a sibling intent.

**Resolution — collapse.** Single scalar `prefix: PAY`. `FEE-001` ("record a processing fee") became `PAY-FEE-001` — folded into the `PAY` leaf as a within-leaf `-FEE-` type facet. `PAY-001` is unchanged. The design doc's body was updated to state the facet relationship rather than imply a second namespace.

### 3. CLAUDE.md directive drift (resolved -> refresh)

`CLAUDE.md` carried only the `## LID` block and a one-line "Consult the skill" directive — the directive section diverged from the current 1.2 template. Refreshed the `## Linked-Intent Development (MANDATORY)` section to the current template: the arrow, the docs-carry-current-intent rule, and the Navigation, Terminology, and Code-annotations subsections. Project title ("My Project") and the existing `## LID` block (Mode: Full, Version: 1.2.0) preserved. No `## LID Scope` (mode is Full), no arrow-overlay nav row (`docs/arrows/` absent), and no `## LID Tooling` (nothing to declare) — each correctly omitted.

## Final structure

```
CLAUDE.md
docs/high-level-design.md
docs/intent/
  orders/                         (sub-HLD, prefix ORDER)
    orders-design.md
    lifecycle/                    (leaf, prefix ORDER-LIFECYCLE)
      lifecycle-design.md
      lifecycle-specs.md          ORDER-LIFECYCLE-001
    refund/                       (leaf, prefix ORDER-REFUND)
      refund-design.md
      refund-specs.md             ORDER-REFUND-001
  payments/                       (leaf, prefix PAY)
    payments-design.md
    payments-specs.md             PAY-001, PAY-FEE-001
```

## Notes / things to confirm

- **No code in this project**, so no `@spec` annotation rewrites were needed. In a real codebase, the ID renames (`ORDER-001`->`ORDER-LIFECYCLE-001`, `REFUND-001`->`ORDER-REFUND-001`, `FEE-001`->`PAY-FEE-001`) would each require updating the matching `@spec` comments and test references; that rewrite can be sequenced separately from this structural reconciliation.
- No `docs/arrows/` overlay is present, so there was no `index.yaml` schema bump or `detail:` path rewrite to perform.
- The two structural calls (promote orders, collapse payments) are judgment moves. They were made on intent as read from the docs; if the intended shape differs — e.g. refund is genuinely a facet of one order intent (collapse) rather than a sibling sub-flow, or fees are a distinct billing concern (split) — say so and the structure can be re-cut.
- No markers were left deferred; the walk is complete with no residual `prefix:` arrays or overloaded folders.
