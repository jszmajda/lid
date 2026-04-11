---
name: map-codebase
description: Bootstrap the arrow-of-intent system for an existing (brownfield) codebase. Deep-reads every file, offers creative clustering options, generates LLDs and HLD bottom-up, then creates EARS specs and arrow docs. Token-intensive by design. Use when asked to map a codebase, bootstrap arrows, reverse-engineer the design, or set up arrows for an existing project.
disable-model-invocation: true
---

# Map Codebase (Brownfield Arrow Bootstrap)

This skill maps an existing codebase into the linked-intent / arrow-maintenance documentation system. It works bottom-up: read all the code first, then build design documents that describe what actually exists.

**This process is deliberately token-intensive.** Accurate mapping requires reading actual code, not guessing from filenames. Warn the user upfront that this will consume significant tokens. That is correct and expected.

See [brownfield-bootstrap.md](references/brownfield-bootstrap.md) for the full workflow reference with detailed guidance for each phase.

## Workflow Overview

### Phase 1: Deep Reconnaissance

Launch massively parallel subagents to read EVERY file in the codebase. Do not skip files. Do not assume what a file does from its name or path. Read actual content and report.

For each file, record: purpose, exports/interfaces, dependencies, data shapes, side effects, and role in the larger system.

Output: a structured inventory of the entire codebase.

### Phase 2: Creative Clustering

Present **3-5 fundamentally different ways** to group the codebase into components. These are not variations on one theme — they are entirely different mental models:

- By data flow (what data moves where)
- By user journey (what users touch in sequence)
- By deployment boundary (what ships together)
- By team ownership (what one team could own end-to-end)
- By change frequency (what changes together)
- By domain concept (business-domain-driven boundaries)
- Other creative groupings that fit this specific codebase

Each grouping should be named and presented with its components, pros, and cons.

**STOP. Present groupings to the user. User picks one.**

Then within the chosen grouping, offer 2-3 slicing variations — different levels of granularity or boundary placement.

**STOP. User picks a slicing.**

### Phase 3: Per-Cluster LLDs (Bottom-Up)

For each cluster in the chosen slicing, write a Low-Level Design document following the LLD template from the linked-intent-dev skill. Key adaptation for brownfield:

- Describe what the code **actually does today**, not what it should do
- "Context and Design Philosophy" becomes "Context and Current State"
- "Decisions & Alternatives" becomes "Observed Design Decisions" (what was chosen and why, inferred from code evidence)
- Include a "Technical Debt & Inconsistencies" section
- Include a "Behavioral Quirks" section for undocumented but intentional-looking behaviors

Place LLDs in `docs/llds/`.

**STOP after each LLD. User reviews before proceeding to the next.**

### Phase 4: Synthesize HLD

After all LLDs are approved, write the High-Level Design. The HLD **emerges from** the LLDs — it is not designed top-down. Identify cross-cutting concerns, shared patterns, and architectural boundaries that the LLDs revealed.

Place at `docs/high-level-design.md`.

**STOP. User reviews.**

### Phase 5: EARS Linkages & Arrow Docs

- Write EARS specs for current behavior (what IS, not what SHOULD BE)
- Brownfield specs start as `[x]` (code exists and works) — most things are already implemented
- Mark broken/incomplete behavior as `[ ]`, intentionally absent as `[D]`
- Add `@spec` annotations to existing code and test files
- Create `docs/arrows/index.yaml` and per-cluster arrow docs using the arrow-doc-template
- Initial arrow status: MAPPED or AUDITED depending on verification depth

### Phase 6: Verify Setup

Run `/linked-intent-dev:lid-setup` if not already done to ensure CLAUDE.md directives are in place.

## Critical Rules

1. **Read actual code.** Do not infer from filenames. This is the single most important rule.
2. **Each STOP is mandatory.** Do not proceed without explicit user approval.
3. **LLDs describe current reality.** Mark aspirational items separately from what exists.
4. **Be thorough over being fast.** It's better to spend 10x the tokens and get an accurate map than to make assumptions that lead to incorrect arrows.
5. **Be humble but be a guide.** The user may not know this codebase well. Offer your best judgment on clustering, but present options — don't dictate.
