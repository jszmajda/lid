# Eval 0 — Bootstrap Empty Project (with_skill)

## State detection

- No `CLAUDE.md` present.
- No `docs/` directory present.
- No `docs/arrows/` overlay (so arrow-navigation row is omitted).
- No tooling to declare (so `## LID Tooling` section is omitted).

Dispatched to the **Full bootstrap** branch. User's prompt explicitly chose Full LID, so no mode prompt was issued.

## Actions taken

### Directories created

- `docs/` (project root)
- `docs/llds/`
- `docs/specs/`

(No `docs/planning/` created — per skill instructions, plans are agent-native.)

### Files created

- `CLAUDE.md` (project root)
- `docs/high-level-design.md`

## CLAUDE.md sections

- Project header
- `## LID Mode: Full` (the sole source of truth for mode detection; no `## LID Scope` section since mode is Full)
- `## Linked-Intent Development (MANDATORY)` directive block, copied from the canonical template:
  - Arrow direction (`HLD → LLDs → EARS → Tests → Code`)
  - Per-change-type guidance (features/refactors, bug fixes, unsure)
  - Phase-stop and mutation-not-accumulation reminders
- `### Navigation` table with rows for HLD, LLDs, EARS specs. Arrow overlay row omitted because `docs/arrows/` is not present.
- `### Terminology` (HLD, LLD, EARS, Arrow, Arrow segment, Cascade)
- `### Code annotations` (`@spec` annotation convention, entry-point placement)

The `## LID Tooling` section is intentionally omitted — there is no coherence-check script or other project tooling to declare on a fresh empty project. The skill will fall back to in-prompt audits.

## docs/high-level-design.md sections

Populated as a skeleton from the HLD template. Sections present, each marked `*(not yet specified — ...)*` so gaps are visible rather than hidden:

- `# High-Level Design: {Project Name}` (placeholder title)
- `## Problem`
- `## Approach`
- `## Target Users`
- `## Goals`
- `## Non-Goals`
- `## System Design`
- `## Key Design Decisions`
- `## Success Metrics`
- `## References`

`## FAQ` is omitted per template guidance (it is optional and there is no FAQ content yet).

## Files NOT created

- No `docs/planning/` directory (LID does not require it).
- No `docs/arrows/` overlay (the arrow-maintenance plugin is a separate install and was not requested).
- No LLD or EARS files in `docs/llds/` or `docs/specs/` — those are intent-component-driven and will be authored by the first `/linked-intent-dev` consult.
