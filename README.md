# Linked-Intent Development for Claude Code

A plugin marketplace for [Claude Code](https://claude.ai/code) that brings structured, design-driven development to your projects. Stop building the wrong thing — get alignment on *what* before writing *how*.

## The Problem

Modern AI coding agents don't really write bugs anymore. What they write are *intent gaps* — places where the agent assumed you meant something different than you did. The biggest challenge in agentic development isn't getting code to work; it's making sure the agent builds the right thing.

This gets worse as systems grow. Every new session starts a capable but amnesiac programmer from scratch. Context windows help, but there's always a gap between what's in your head and what's in the agent's context. That gap is where intent drifts, and intent drift is where projects go sideways.

## The Arrow of Intent

The solution is to make intent explicit and traceable. There's a chain of documents that translates what you want into working software:

```
HLD → LLDs → EARS → Tests → Code
```

Each level translates the previous into more specific terms. They aren't independent documents — they're a single expression of intent at different levels of specificity. When you change your mind about something, the change flows *downstream* through the chain: update the design, then the specs, then the tests, then the code. Never the reverse.

This is the "arrow of intent." It means you don't ask the agent to "fix the bug" — you ask it to "update the arrow so this behavior is clearly specified, tested, and implemented." The documentation becomes the source of truth, not the code. Code is output. Intent is the artifact you maintain.

For more background, see [The Arrow of Intent](https://loki.ws/code/2026/01/25/the-arrow-of-intent.html).

## What's in here

**Two core plugins** for linked-intent development:

| Plugin | What it does | When to use it |
|--------|-------------|----------------|
| **linked-intent-dev** | Structured design-before-code workflow: HLD → LLD → EARS specs → Implementation plan | Every project. Consult for all code changes. |
| **arrow-maintenance** | Tracks spec-to-code coherence across large projects via `docs/arrows/` index | Projects too large to hold in one context window |

## Installation

Inside Claude Code:

```
/plugin marketplace add jszmajda/lid
```

Then install the plugins you need. Choose "project" scope to share with your team:

```
/plugin install linked-intent-dev@jszmajda-lid
/plugin install arrow-maintenance@jszmajda-lid
```

After installing, run the setup skill to configure your project:

```
/linked-intent-dev:lid-setup
```

This creates your `docs/` directory structure and adds the required directives to your project's CLAUDE.md.

## Getting Started: Greenfield Project

You're starting something new. Here's the workflow:

### 1. Run setup

```
/linked-intent-dev:lid-setup
```

This creates `docs/llds/`, `docs/specs/`, `docs/planning/` and configures your CLAUDE.md.

### 2. Design before you code

Start by telling Claude what you want to build. The linked-intent-dev skill guides you through four phases, stopping for your review after each one:

**Phase 1 — High-Level Design.** Claude presents 2-3 architectural trade-offs, you pick a direction, then Claude drafts the full HLD. You review and approve before moving on.

**Phase 2 — Low-Level Designs.** For each major component, Claude writes a detailed LLD covering data models, error handling, edge cases, and design decisions. Claude probes for gaps you might have missed. You review each one.

**Phase 3 — EARS Specifications.** Claude generates testable requirements with semantic IDs like `AUTH-UI-001`. Each spec is something you can point at and say "is this implemented?" Claude cross-checks for coverage gaps and contradictions. You review.

**Phase 4 — Implementation Plan.** Phased execution plan with checkboxes, spec references, and a definition of done. You review, then Claude starts building.

### 3. Build with traceability

During implementation, code gets `@spec` annotations linking back to requirements:

```typescript
// @spec AUTH-UI-001, AUTH-UI-002
export function LoginForm({ ... }) { ... }
```

Tests reference specs too. This creates a traceable chain from requirements to code to tests.

### 4. Keep it coherent

When requirements change (they always do), the linked-intent-dev skill cascades changes downward: update the HLD → review LLDs → review specs → review tests → review code. Docs always reflect *current* intent, not history.

## Getting Started: Brownfield Project

You have an existing codebase and want to bring structure to it. This works bottom-up — understanding what exists before documenting it.

### 1. Install both plugins

You'll need linked-intent-dev (for the LLD/EARS workflow) and arrow-maintenance (for the mapping and tracking):

```
/plugin install linked-intent-dev@jszmajda-lid
/plugin install arrow-maintenance@jszmajda-lid
```

### 2. Map the codebase

```
/arrow-maintenance:map-codebase
```

This kicks off a thorough, multi-phase process. Be warned: **it's deliberately token-intensive.** Accurate mapping requires reading actual code, not guessing from filenames.

**Phase 1 — Deep Reconnaissance.** Claude launches parallel subagents to read *every file* in your codebase. No assumptions, no shortcuts. This produces a structured inventory of the entire project.

**Phase 2 — Creative Clustering.** Claude presents 3-5 fundamentally different ways to think about your codebase — by data flow, by user journey, by deployment boundary, by team ownership, by change frequency, or other models that fit your specific project. These aren't variations on one theme; they're entirely different mental models. You pick a grouping, then choose a slicing granularity within it.

**Phase 3 — Bottom-Up LLDs.** For each cluster, Claude writes an LLD describing what the code *actually does today* — including the messy parts, technical debt, and behavioral quirks. You review each one before moving on.

**Phase 4 — Synthesize HLD.** Once all LLDs are approved, Claude writes a High-Level Design that emerges from the bottom up. The HLD describes the system as it is, not as it should be.

**Phase 5 — EARS Linkages.** Claude writes specs for current behavior, adds `@spec` annotations to existing code, and creates arrow docs with `docs/arrows/index.yaml` to tie it all together.

### 3. Work with arrows

After mapping, you have a navigable index of your codebase. At the start of any work session, Claude reads `docs/arrows/index.yaml` to understand what's available, what's blocked, and what needs work. Arrows track the status of each domain:

| Status | Meaning |
|--------|---------|
| UNMAPPED | Not yet explored |
| MAPPED | Structure known, specs not yet verified |
| AUDITED | Specs verified against code |
| OK | Fully coherent |

New features get arrows. Bug fixes check arrow coherence first. Over time, the whole codebase becomes traceable.

## Quick Reference

| You want to... | Run... |
|----------------|--------|
| Set up a new project for LID | `/linked-intent-dev:lid-setup` |
| Map an existing codebase | `/arrow-maintenance:map-codebase` |
| Start a new feature | Just describe it — linked-intent-dev activates automatically |
| Fix a bug | Just describe it — Claude checks intent coherence before changing code |

## License

MIT — See [LICENSE](LICENSE)
