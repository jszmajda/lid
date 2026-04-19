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
- **Mutation, not accumulation.** When the HLD changes, update in place. Delete what's wrong. The HLD should always reflect current intent, not history.
- **Diagrams.** Mermaid is the default for structural, flow, state, and ERD diagrams — renders natively on GitHub and is token-efficient for agent consumption. ASCII is the convention for UI mockups. Detect existing project conventions first; ask once if unclear.
- **Trade-off sketches.** When drafting a new HLD or making a consequential architectural change, first sketch 2–3 competing options (~200 words each with downstream consequences) and present them for user selection before committing to a full draft. See the `linked-intent-dev` skill's Phase 1 guidance.
- **Non-Goals earn their place.** An explicit non-goal that constrains future surface growth is worth more than a vague goal.

## Scoped-LID variant

For Scoped LID projects, mark unspecified sections explicitly:

```markdown
## System Design

*(not yet specified)*

## Success Metrics

*(not yet specified — scope is too narrow for project-level metrics; see LLD for scope-specific success criteria)*
```

Leaving a section unfilled is better than filling it with placeholder prose — agents can tell which parts of the intent are authored and which are still gaps.
