# HLD Template Reference

A project's High-Level Design (HLD) is the **root of the design tree** — the single top-level document that answers *what* and *why* for the whole project. One HLD per project. File location: `docs/high-level-design.md`.

The same shape also appears *below* the root. When a subsystem grows too deep for one LLD, it promotes into a **sub-HLD**: an HLD-shaped document that is the root of its own subtree, holding that subtree's problem, approach, and key decisions while parenting its children. "HLD" and "LLD" are roles by position in the tree, not fixed types — this template is a starting point for any node acting as a tree root or grouping node, which carries the sections it needs. A sub-HLD **owns no EARS**; it delegates specs to its child LLDs (see the LLD template reference). Depth-2 — one HLD over a flat set of LLDs — is the default; sub-HLDs are a triggered exception, not a requirement. A *merely categorical* grouping — a label with no shared parent intent a parent doc should hold — is **not** a sub-HLD: its members stay flat leaves (it may still group them for navigation, as `index.yaml`'s `taxonomy` field does). The test is whether a parent design doc *should* exist, not whether one already does — write a parent where shared intent warrants it; keep things flat where it does not.

**Non-root pointers.** A sub-HLD carries a `parent:` pointer naming its parent node (so the tree is walkable upward) and a `prefix:` carrying the EARS namespace it roots. The directory and file names are human-readable and need not equal that prefix; `prefix:` is the authoritative bridge from the human name to the namespace. Its child LLDs extend the prefix and own the actual specs — the sub-HLD owns none directly — but `prefix:` lets a reader grep the whole subtree (`grep EXP`). The root HLD has neither pointer.

**File placement — node-as-folder.** Every node is a directory. A sub-HLD `foo` is `docs/intent/…/foo/` holding `foo-design.md` plus a child directory per child — e.g. the `arrow-maintenance` sub-HLD is `docs/intent/arrow-maintenance/arrow-maintenance-design.md` with child directories `maintenance/` and `map-codebase/`. (A leaf is the same shape, additionally holding `foo-specs.md`.) Promoting a leaf to a sub-HLD adds child directories beside its `-design.md` and moves its EARS down into the new leaf children. (See the LLD template reference for the matching detail.)

```markdown
---
parent: high-level-design
prefix: EXP
---
```

## Standard sections

The HLD uses these sections. In **Full LID**, every section is filled. In **Scoped LID**, sections may be explicitly marked `*(not yet specified)*` rather than filled with placeholder prose — gaps are visible rather than hidden.

```markdown
# High-Level Design: {Project Name}

## Problem

The problem this project exists to solve. What is broken, who suffers, why now.

## Approach

How the project solves the problem in general terms. If there are multiple load-bearing approaches (a core mechanism plus secondary disciplines), name each as its own sub-section.

## Target Users

Who the project serves. Concrete postures or roles, not demographics. What they need and at what cost.

## Goals

What success looks like — specific, falsifiable when possible. Prefer outcomes over outputs.

## Non-Goals

What this project explicitly is not. Useful boundary — makes it easier to say "no" to surface growth.

## Tenets

One-line tie-breakers: which way the project leans when a decision has two defensible answers and no spec covers it. A tenet is forward-looking — it governs choices the arrow has not reached yet — which makes it distinct from Key Design Decisions, which record choices already made, and from specs, which fix a definite action at a known trigger. A tenet leans a class of unforeseen choices; a candidate phrased as *when X, do Y* is a spec — route it to EARS, not the tenet list, even when its opposite is a defensible choice. The discriminating test is the **defensible opposite**: a real tenet's reverse is a choice a different project could reasonably make. "We prefer X over Y" where Y is absurd is a platitude, not a tenet, and resolves nothing. State each as a single line and order them so that when two conflict, the higher one wins. A short HLD has two or three load-bearing tenets, not a manifesto.

```markdown
- **Boring over clever.** When a problem has a well-worn solution and a novel one, prefer the well-worn one unless the novel one is decisively better — a future maintainer should not have to reverse-engineer ingenuity.
- **Fail loud, not silent.** When an operation cannot complete correctly, surface the failure rather than degrading quietly.
```

## System Design

High-level architecture: major components, how they fit, what boundaries separate them. Mermaid diagrams preferred for structural views; ASCII for UI mockups when needed.

## Key Design Decisions

Load-bearing choices and the reasoning behind them. Each decision names the alternatives considered and why this direction was chosen. Prefer a few deep decisions with clear rationale over many shallow ones.

## Success Metrics

How you know the project is working. Where possible, describe falsification signals — conditions under which the project would be judged broken.

## FAQ (optional)

Questions the team has answered often enough that the answer belongs in the HLD.

## References

Prior art, linked specs, related projects, external docs.
```

## Notes

- **Keep it short enough to re-read.** An HLD that sprawls beyond ~2000 lines stops being an orientation doc. Push detail down into child LLDs; when a single subsystem's detail outgrows one LLD, promote it into a sub-HLD with its own child LLDs.
- **Docs carry current intent, written to be read cold.** When the HLD changes, update in place and delete what's wrong. Write it as if authored fresh today from current intent alone — no narration of how it changed, no meaning that needs the conversation that produced it, no rebuttals to questions only a past discussion raised. Rationale and considered alternatives that a fresh author would independently write stay; they are present intent, not history.
- **Diagrams.** Mermaid is the default for structural, flow, state, and ERD diagrams — renders natively on GitHub and is token-efficient for agent consumption. ASCII is the convention for UI mockups. Detect existing project conventions first; ask once if unclear.
- **Trade-off sketches.** When drafting a new HLD or making a consequential architectural change, first sketch 2–3 competing options (~200 words each with downstream consequences) and present them for user selection before committing to a full draft. See the `linked-intent-dev` skill's Phase 1 guidance.
- **Non-Goals earn their place.** An explicit non-goal that constrains future surface growth is worth more than a vague goal.
- **Tenets are elicited, not assumed.** When drafting or revising the HLD, surface the few decisions that could reasonably go more than one acceptable way and ask the user to state a preference. See the `linked-intent-dev` skill's Phase 1 guidance.

## Scoped-LID variant

For Scoped LID projects, mark unspecified sections explicitly:

```markdown
## System Design

*(not yet specified)*

## Success Metrics

*(not yet specified — scope is too narrow for project-level metrics; see LLD for scope-specific success criteria)*
```

Leaving a section unfilled is better than filling it with placeholder prose — agents can tell which parts of the intent are authored and which are still gaps.
