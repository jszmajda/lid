---
name: linked-intent-dev
description: Guide for linked-intent development (LID). Consult for ALL code changes. New features use full workflow (HLD → LLD → EARS → Plan). Bug fixes skip doc creation but still verify intent coherence—check that existing specs, tests, and code align before changing anything.
---

# Linked-Intent Development

This skill guides a structured linked-intent development workflow. The goal is to get alignment on what you're building *before* writing code, which dramatically reduces rework and misunderstandings.

## Critical Rule: Stop and Iterate

**STOP after completing each phase.** Present the document to the user for review. Incorporate their numbered feedback. Only proceed to the next phase when explicitly approved.

This is the most important part of the workflow. Don't rush through design to get to code.

## Workflow Overview

1. **High-Level Design (HLD)** - Project vision and architecture
2. **Low-Level Design (LLD)** - Component-specific technical design
3. **EARS Specifications** - Requirements with semantic IDs
4. **Implementation Plan** - Phases, checkboxes, Definition of Done

## When to Use This Workflow

**Consult this skill for ALL code changes.**

**Full workflow (create new docs) for:**
- New features
- Major refactors
- Significant behavior changes

**Coherence check only (skip doc creation) for:**
- Bug fixes
- Quick changes (<30 minutes)
- Debugging sessions

Even when skipping doc creation, verify intent coherence: do existing specs, tests, and code align? If not, fix the docs before changing the code.

**If unsure, use the full workflow.** Over-designing is safer than under-designing.

## Phase 1: High-Level Design

Check if a project HLD exists first: `/docs/high-level-design.md`

### Step 1a: Trade-off Sketches

Before drafting the full HLD, identify the 2–3 most consequential architectural trade-offs for this feature. For each one:
- Name the decision point
- Sketch the competing approaches (~200 words max each)
- Note downstream consequences of each approach (what becomes easier, what becomes harder)

**Present the trade-off sketches to the user.** The user selects, combines, or redirects. This ensures the checkpoint is a *choice among alternatives*, not a reaction to a single draft.

### Step 1b: Full HLD Draft

Incorporating the user's trade-off selections, draft the HLD covering:
- Problem statement and goals
- Target users and personas
- System architecture overview
- Key design decisions and trade-offs (with selections from Step 1a)
- Non-goals (what's explicitly out of scope)

**Stop and get user approval before proceeding.**

## Phase 2: Low-Level Design

Create component-specific LLDs in `/docs/llds/` for each major component.

See [lld-templates.md](references/lld-templates.md) for structure guidance.

Key principles:
- **Narrative format** for complex constraint interactions
- **Structured format** for API contracts and interfaces
- Include data models, error handling, edge cases
- Reference the HLD for context
- **LLDs are pure design documents** — they describe *how* things work but do not track implementation status
- Include a **Decisions & Alternatives** section — see [lld-templates.md](references/lld-templates.md)

### Edge Case Probe

After drafting each LLD, review it and generate a list of "what happens when..." questions — missing edge cases, unspecified failure modes, implicit assumptions about ordering, concurrency, empty states, or error propagation that the LLD doesn't address. Use a subagent for this review if available.

**Present the gap list alongside the LLD draft.** The user decides which gaps to address in the LLD and which are out of scope. Update the LLD before proceeding. This is a *coverage probe*, not an alternative design — the HLD trade-offs were already resolved in Phase 1.

**Stop and get user approval before proceeding.**

## Phase 3: EARS Specifications

Generate requirements using EARS (Easy Approach to Requirements Syntax).

See [ears-syntax.md](references/ears-syntax.md) for full syntax reference.

Key principles:
- **Semantic spec IDs**: `{FEATURE}-{TYPE}-{NNN}` (e.g., `AUTH-UI-001`, `CART-API-003`)
- Create in `/docs/specs/` (e.g., `user-authentication-specs.md`)
- Each requirement is testable and traceable
- Spec files carry status markers: `[x]` implemented, `[ ]` active gap, `[D]` deferred
- **Delete specs that are no longer wanted** — git preserves history

### Consistency Verification

After generating specs, cross-check before presenting to the user:

- **Coverage**: Are there behaviors described in the LLD that have no corresponding EARS spec?
- **Contradiction**: Do any specs say different things about the same behavior?
- **Implicit scoping**: Review each spec for scope that is implicit rather than stated — see [ears-syntax.md § Scope Disambiguation](references/ears-syntax.md). When adding a new mode or variant, audit sibling specs for scope that was implicit when only one variant existed.

**Present a brief consistency report alongside the specs.** Flag gaps, contradictions, and scoping issues explicitly. The user resolves any issues before approval.

**Stop and get user approval before proceeding.**

## Phase 4: Implementation Plan

Create execution plan in `/docs/planning/` with date suffix.

See [plan-templates.md](references/plan-templates.md) for structure guidance.

Key elements:
- **Phases** with clear deliverables
- **Checkboxes** for tracking progress
- **Spec ID references** tying to EARS requirements
- **Definition of Done** with verification criteria
- **Testing requirements** with spec annotations

**Stop and get user approval before proceeding.**

## Maintaining Intent Coherence

### The Arrow of Intent

There's a chain of documents that translates intent from vision to working code:

```
HLD → LLDs → EARS → Tests → Code
```

Each level translates the previous into more specific terms:
- **HLD** says *what* and *why*
- **LLDs** say *how* at a component level
- **EARS** says *exactly what must be true* in testable terms
- **Tests** verify those truths
- **Code** makes them real

These aren't independent documents—they're a single expression of intent at different levels of specificity.

### The Problem: Intent Drift

Intent drifts over time. User clarifies something and the LLD gets updated but not the EARS. A test gets fixed but the spec still says the old thing. The HLD evolves but nobody touches downstream docs.

Eventually the levels disagree. The code works, but doesn't match the specs. The specs pass review, but don't match the design. The chain breaks.

### The Principle: Coherence Over History

The arrow of intent must stay coherent. When one level changes, downstream levels must be reviewed and updated to match.

**Mutation, not accumulation.** Update docs in place. Delete what's wrong. The documentation should always reflect *current* intent—not the history of how intent evolved.

### The Practice: Cascade Changes Downward

When requirements or understanding change:

1. **Identify the entry point** - Where in the chain does this change originate?
2. **Update at that level** - Mutate the doc directly
3. **Cascade downward** - Review and update each subsequent level:
   - HLD change → review LLDs → review EARS → review tests → review code
   - LLD change → review EARS → review tests → review code
   - EARS change → review tests → review code
4. **Delete what's obsolete** - Delete specs that no longer apply (don't mark them, just remove); remove tests for removed specs

### Before Implementation

Before implementing (or resuming implementation), verify coherence:

- Do the EARS specs trace to the current LLD?
- Do the tests trace to current EARS?
- If drift is detected, fix the docs first—then implement.

## Code Annotation Pattern

Annotate code with `@spec` comments linking to EARS IDs:

```typescript
// @spec AUTH-UI-001, AUTH-UI-002, AUTH-UI-003
export function LoginForm({ ... }) {
  // Implementation
}
```

Test files also reference specs:

```typescript
// @spec AUTH-UI-010
it('validates email format before submission', () => {
  expect(validateEmail('invalid')).toBe(false);
});
```

This creates traceability from requirements → code → tests.

## Progress Tracking

During implementation:
- Check off items in the implementation plan as completed
- Update the plan doc with any discovered changes
- Move completed phases to an `/old/` subdirectory when fully done

## Why This Works

| Benefit | Why It Matters |
|---------|----------------|
| **Forced checkpoints** | Catches misunderstandings before you've built the wrong thing |
| **Scannable docs** | One-line requirements easy to search and reference |
| **Traceability** | @spec annotations link code to requirements |
| **Survives session breaks** | Docs persist, context doesn't get lost |
| **Reusable** | Same docs work across multiple sessions |
| **Testable requirements** | EARS format ensures requirements are verifiable |

Work back and forth with the user, starting with your open questions and outline before writing any plan.
