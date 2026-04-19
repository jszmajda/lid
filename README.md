# Linked-Intent Development for Claude Code

A plugin marketplace for [Claude Code](https://claude.ai/code) that brings structured, design-driven development to your projects. Stop building the wrong thing — get alignment on *what* before writing *how*.

## Quickstart

```
/plugin marketplace add jszmajda/lid
/plugin install linked-intent-dev@jszmajda-lid
/plugin install arrow-maintenance@jszmajda-lid
/linked-intent-dev:lid-setup
```

Then just tell Claude what you want to build. It handles the rest. For existing codebases, see [Getting Started: Brownfield Project](#getting-started-brownfield-project).

> **LID uses LID on itself.** This repo is the canonical mature-project example — its own HLD, LLDs, EARS specs, and evals are in `docs/` and `plugins/*/skills/*/evals/`. If you want to see what LID-at-rest looks like on a real codebase, read the docs here. For a small, intent-only demo (HLD + LLDs + specs, no code — meant to be given to an agent to regenerate), see [`examples/urlshort/`](examples/urlshort/).

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

## How LID Differs from Other SDD Systems

Several spec-driven development (SDD) systems exist for agentic coding — [BMAD](https://docs.bmad-method.org/), [spec-kit](https://github.com/github/spec-kit), and others. They all share the insight that you should specify before you code. Where they differ is in what happens *after*.

Most SDD systems are optimized for **the next change**: generate specs, plan tasks, implement, ship. The artifacts are scaffolding for delivery. Some have extensions for detecting drift or updating specs post-implementation, but the core workflow is a pipeline that ends at "done."

LID is optimized for **the project over time**. The design documents aren't scaffolding — they're the system's source of truth. Done well, you should be able to delete all tests and code and regenerate them from the HLD, LLDs, and EARS specs alone. That's the bar. If you can't, there's an intent gap somewhere, and closing it is the work.

| | Typical SDD | LID |
|---|---|---|
| **Primary goal** | Clear intent for the next change | Continuous truth for the whole project |
| **Design docs after implementation** | Reference material, may drift | The living source of truth — always current |
| **When specs and code disagree** | Sync them up (which direction?) | Specs win. Fix the code, or fix the spec and cascade. |
| **Tests and code** | The artifact you maintain | Output. Regenerable from intent. |
| **Scope** | Per-feature or per-change | Per-project, tracked across all components |

LID is also intentionally much simpler than other SDD systems. BMAD has specialized agents, adversarial reviews, and multi-phase orchestration. Spec-kit has extensions, CI guards, and reconciliation workflows. LID has two skills and a handful of markdown templates. The complexity lives in Claude, not in the tooling — we rely on the model's judgment as much as possible and focus the system on creating durable context that survives across sessions, compactions, and even model changes.

This comes from building products at AWS, where systems live for years and the biggest cost isn't building the wrong thing once — it's *maintaining* a system where nobody can explain why it does what it does. LID treats Claude Code as an English compiler: your design documents are the source, and everything downstream is compiled output.

The tradeoff is that LID requires discipline. You review HLDs and LLDs carefully. You close intent gaps through progressive application of arrow-maintenance. You don't skip the design phases because you "already know what to build." But when used consistently, it produces systems that are more coherent, more maintainable, and self-documenting — because the documentation *is* the system, and the code just happens to implement it.

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

This creates `docs/high-level-design.md`, `docs/llds/`, `docs/specs/` and appends LID directives to your project's CLAUDE.md. It asks which mode you want — **Full LID** (whole project) or **Scoped LID** (a bounded piece of a larger project, with glob patterns declaring what's in scope).

### 2. Design before you code

Start by telling Claude what you want to build. The linked-intent-dev skill guides you through six phases, **stopping for your review after each one**:

**Phase 1 — HLD check.** For new projects or architectural changes, Claude sketches 2–3 competing trade-off options and asks you to pick. Then drafts the full HLD. You review and approve before moving on.

**Phase 2 — LLD check or draft.** For each component, Claude writes (or updates) a detailed LLD covering data models, error handling, decisions, and open questions. After drafting, Claude runs an **LLD-level edge-case probe** — "what happens when..." questions targeting gaps inside this LLD. You triage which gaps to fix. You review.

**Phase 3 — EARS specifications.** Claude generates testable requirements with semantic IDs like `AUTH-UI-001`. Each spec is something you can point at and say "is this implemented?" After drafting, Claude runs **post-draft consistency verification** — coverage (behaviors without specs?), contradiction, implicit scoping. You review.

**Phase 4 — Intent-narrowing edge audit.** Distinct from Phase 2: this looks *across* the whole specification for places where the agent's interpretation could diverge from what you meant — cross-segment interactions, namespace ambiguity, composition of specs. This is the edge where LID's value lives.

**Phase 5 — Tests first.** Tests are written *before* code, per the HLD's intent-preloading rationale. Tests carry `@spec` annotations citing the EARS IDs they verify. No code until tests exist and fail in the expected way.

**Phase 6 — Code.** Implementation follows. Code carries `@spec` annotations at the *entry point of the behavior's implementation graph* — the topmost function or module that owns the behavior, not every helper. On completion, coherence verification runs (tests pass, annotations resolve to real specs, LLD matches HLD).

### 3. Build with traceability

Code gets `@spec` annotations linking back to requirements:

```typescript
// @spec AUTH-UI-001, AUTH-UI-002
export function LoginForm({ ... }) { ... }
```

Tests reference specs too. This creates a traceable chain from requirements to code to tests, walkable in one `grep` per hop.

### 4. Keep it coherent

When requirements change (they always do), the linked-intent-dev skill cascades changes downward: update the HLD → review LLDs → review specs → review tests → review code. Within one arrow segment (an LLD and its downstream), cascade runs freely. Across segment boundaries, the skill pauses and confirms — real LLDs are uneven, and aggressive cross-boundary cascade propagates incoherence.

Docs always reflect *current* intent, not history. Delete obsolete specs rather than marking them; git preserves history.

### 5. Fix bugs by walking the arrow

Bugs aren't a special case. Find where behavior diverged from intent, decide whether intent needs to change / is wrong / was never expressed, and cascade from there. Fixing code without walking the arrow is a bypass — the skill warns but doesn't block.

## Getting Started: Brownfield Project

You have an existing codebase and want to bring structure to it. This works bottom-up — understanding what exists before documenting it.

### 1. Install and set up

You'll need both plugins. Install them, then run setup:

```
/plugin install linked-intent-dev@jszmajda-lid
/plugin install arrow-maintenance@jszmajda-lid
/linked-intent-dev:lid-setup
```

### 2. Map the codebase

```
/arrow-maintenance:map-codebase
```

**Token-intensive by design.** Accurate mapping means reading actual code, not guessing from filenames. Worth warning you upfront. The command asks whether to map the whole project (Full LID) or specific parts (Scoped LID) at invocation, then walks through six phases, stopping at each for your review:

**Phase 1 — Sweep (reconnaissance).** Claude (or parallel subagents if you enable them) reads *every file* in the declared scope and produces a structured per-file summary: purpose, exports, dependencies, data shapes, side effects, role, observations. No segmentation attempted at this stage.

**Phase 2 — Lens selection.** Claude proposes 3–5 *fundamentally different* clusterings of your code, each using a distinct lens (data flow, user-facing capability, domain concept, behavioral boundary, or an unconventional one). Anti-pattern lenses (frontend/backend split, files-that-deploy-together, team ownership, generic utils) are explicitly excluded — they produce clusters that track artifacts, not intent. You pick a lens.

**Phase 3 — Slicing granularity.** Within your chosen lens, Claude proposes 2–3 slicing variations — coarse (3–4 segments), medium (6–8), or fine (10+). Fewer segments = fewer LLDs to maintain; more segments = precise scoped tracking. You pick.

**Phase 4 — User reconciliation.** Claude presents the final clustering. You approve, modify segment boundaries, or combine/split. This is where your latent intent meets the agent's interpretation — the most valuable step in the whole flow.

**Phase 5 — Artifact generation.** For each approved segment, Claude drafts a skeleton LLD, an EARS spec file, an arrow doc, and an `index.yaml` entry — with a STOP after each sub-step. Brownfield LLDs use the *standard* LLD template (no separate brownfield format); content carries `[inferred]` markers in the Decisions table and Open Questions for observed-but-unexplained behaviors. As you confirm or refute inferences, the markers come out.

**Phase 6 — Terminal verification.** Claude runs `/lid-setup` to configure CLAUDE.md, then issues a flesh-out prompt directing you to fill in skeleton LLDs and EARS specs segment-by-segment via the `linked-intent-dev` workflow. Partial arrows propagate incoherence, so this prompt isn't optional.

### 3. Work with arrows

After mapping, you have a navigable index of your codebase. At the start of any work session, Claude reads `docs/arrows/index.yaml` first to find unblocked work. Per-segment arrow docs point at their LLD, EARS specs, tests, and code — you don't load the whole project to orient.

Arrow segment statuses:

| Status | Meaning |
|--------|---------|
| UNMAPPED | Not yet explored |
| MAPPED | Structure known, specs not verified against code |
| AUDITED | Specs verified — implementation status understood |
| OK | Fully coherent |
| PARTIAL / BROKEN / STALE / OBSOLETE / MERGED | Other states; see arrow-maintenance skill |

Run `/arrow-maintenance` anytime to audit the overlay: it detects reference rot, spec-to-code drift, uncovered behavioral specs, stale segments, orphan files, and *reverse orphans* (`@spec` annotations pointing to spec IDs that don't exist). Unambiguous findings are fixed in place; ambiguous ones are surfaced for you to decide.

For large projects, declare a coherence-check script in CLAUDE.md's `## LID Tooling` section — arrow-maintenance delegates deterministic checks to it for speed. A reference Node implementation ships with the plugin; Python/bash/any-language equivalents work identically.

## Quick Reference

| You want to... | Run... |
|----------------|--------|
| Set up a new project for LID | `/linked-intent-dev:lid-setup` |
| Update LID config or change mode | `/linked-intent-dev:update-lid` |
| Map an existing codebase | `/arrow-maintenance:map-codebase` |
| Audit the arrow overlay for drift | `/arrow-maintenance:arrow-maintenance` |
| Start a new feature | Just describe it — linked-intent-dev activates automatically |
| Fix a bug | Just describe it — Claude walks the arrow to find where intent diverged |

## Reference implementations and validation

- **LID-on-LID**: this repo applies LID to itself. Read `docs/high-level-design.md`, `docs/llds/linked-intent-dev.md`, and `docs/llds/arrow-maintenance.md` to see the intent tree. EARS specs live in `docs/specs/`.
- **Eval suite**: each behavioral skill has a test harness at `plugins/*/skills/*/evals/evals.json` with spec_id-tagged assertions. Iteration 1 results in `plugins/*/skills/*-workspace/iteration-1/benchmark.md` — with-skill runs at 100%, delta of +36% to +56% over unguided baseline.
- **Example project**: [`examples/urlshort/`](examples/urlshort/) — a URL shortener specified as HLD + LLDs + EARS specs with no code. Clone the directory, install the plugins, and ask Claude to generate an implementation that satisfies the specs. Run the same prompt twice and you should get two working implementations — possibly in different languages. Demonstrates code plasticity.

## License

MIT — See [LICENSE](LICENSE)
