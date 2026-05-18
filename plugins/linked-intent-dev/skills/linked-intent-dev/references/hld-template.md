# HLD Template Reference

A project's High-Level Design (HLD) is the single top-level document that answers *what* and *why* for the whole project. One HLD per project. File location: `docs/high-level-design.md`.

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

One-line tie-breakers: which way the project leans when a decision has two defensible answers and no spec covers it. A tenet is forward-looking — it governs choices the arrow has not reached yet — which makes it distinct from Key Design Decisions, which record choices already made. The discriminating test is the **defensible opposite**: a real tenet's reverse is a choice a different project could reasonably make. "We prefer X over Y" where Y is absurd is a platitude, not a tenet, and resolves nothing. State each as a single line and order them so that when two conflict, the higher one wins. A short HLD has two or three load-bearing tenets, not a manifesto.

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

- **Keep it short enough to re-read.** An HLD that sprawls beyond ~2000 lines stops being an orientation doc. Split into LLDs if detail accumulates.
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
