# LID Coach Review — Delivery Tracking

## Executive summary

**Posture:** *LID-shaped and walkable, but heavily accumulation-loaded — the docs are carrying their own history instead of their current intent.*

The good news first: this project has the full arrow in place. There is one HLD, one LLD scoped to a single intent component (delivery tracking), and one spec file that correctly links back to its LLD and uses the `{FEATURE}-{NNN}` ID form with status markers. The HLD's `## Problem` and `## Approach` sections do exactly what they should — they carry the architecture-level *what* and *why* tersely. The spec `DELIVERY-001` is clean, well-formed EARS with a `[x]` marker. The skeleton is correct; nothing structural is broken. That is the foundation the rest of this review builds on.

**Scorecard**
- ✓ Arrow completeness — HLD, LLD, and spec all present and linked
- ✓ LLD granularity — one LLD, one intent component, no overlap
- ✗ Mutation hygiene — change-narration residue in all three docs
- ⚠ Spec hygiene — an `[obsolete]` spec kept next to its replacement
- ⚠ Configuration — CLAUDE.md directive block is a stub
- ✓ Mode fit — Full mode matches a small single-component project

**Headline:** The arrow is real and correctly linked end to end; the single most valuable thing you can do is sweep the accumulated history out of all three docs so each one states only what is true today.

## Findings (5 total · 3 high · 2 medium)

- **F1 (high):** HLD carries `## History` and `## Changelog` sections plus a "we are planning to move to streaming in Q4" forward-narration · *docs carry current intent, written to be read cold* (a doc states today's intent, not the story of how it got there)
- **F2 (high):** LLD carries `## Previous Architecture (Redis)` and `## Planned Architecture (Streaming)` alongside the current Postgres design · *docs carry current intent, written to be read cold*
- **F3 (high):** Spec `DELIVERY-002` is kept with an `[obsolete]` marker beside its replacement `DELIVERY-001` · *delete obsolete specs* (a spec's presence means the intent is current; absence means withdrawal)
- **F4 (medium):** The "Planned Architecture (Streaming) / Kafka in Q4" content is unsourced future intent with no upstream design or spec · *intent leads; code is compiled output* (the arrow walks from stated current intent, not roadmap)
- **F5 (medium):** CLAUDE.md's Linked-Intent Development block is a one-line stub — no Navigation, Terminology, or Code Annotations directives · *modes are declared, not inferred* (the directive block is the project's standing instruction set)

## What was audited

- Read fully: `CLAUDE.md`, `docs/high-level-design.md`, `docs/llds/delivery-tracking.md`, `docs/specs/delivery-specs.md`
- Enumerated: 1 HLD, 1 LLD, 1 spec file (2 spec IDs)
- Code/tests: none present in the project — no `@spec` annotations to sample, no tests-first evidence to assess (not flagged as a gap; there is no observed behavior demanding code yet)
- Arrow overlay: not installed (`docs/arrows/` absent) — cascade-health and structural findings out of scope for this review; not a deficiency at this project size
- Cold-read pass: completed across all three LID docs

## Offer to help

Want me to walk through the findings in detail, focus on a theme or priority (the accumulation sweep is the obvious one), or work through specific items together? You can also pick a single finding — F1, F2, or F3 — to dig into.

If you have broader questions about using LID for this project — where roadmap/planning content belongs relative to the HLD, when an arrow overlay starts paying off, or how to handle a planned architecture migration without polluting current-intent docs — I can help with those too.
