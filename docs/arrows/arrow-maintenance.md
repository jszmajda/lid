# Arrow: arrow-maintenance

The optional navigation and audit overlay plugin — the `arrow-maintenance` dual-mode skill (ambient + command) plus the `/map-codebase` brownfield-bootstrap skill.

## Status

**MAPPED** — bootstrapped from existing LID docs on 2026-04-25 (git SHA `b64c439`). All 60 active specs marked `[x]`; this `/arrow-maintenance` run is the first audit pass against the overlay it just generated.

## References

### HLD
- `docs/high-level-design.md` § Architecture / Plugins (arrow-maintenance); § Key Design Decisions / Arrow-maintenance stays a separate plugin; § The arrow for LID itself / Dual-mode skills

### LLD
- `docs/llds/arrow-maintenance.md`

### EARS
- `docs/specs/arrow-maintenance-specs.md` (27 specs, prefix `ARROW-MAINT-*`)
- `docs/specs/map-codebase-specs.md` (33 specs, prefix `MAP-CODEBASE-*`)

### Tests / Evals
- `plugins/arrow-maintenance/skills/arrow-maintenance-workspace/iteration-1/` — 1 eval (`bootstrap-overlay-from-lid-docs`)
- `plugins/arrow-maintenance/skills/map-codebase-workspace/iteration-1/` — `skill-creator` iteration outputs

### Code (skill prompts, references, optional script)
- `plugins/arrow-maintenance/.claude-plugin/plugin.json`
- `plugins/arrow-maintenance/skills/arrow-maintenance/SKILL.md` + `references/` (`index-schema.md`, `arrow-doc-template.md`, `audit-checklist.md`, `README-template.md`, `coherence-check.mjs`)
- `plugins/arrow-maintenance/skills/map-codebase/SKILL.md` + `references/` (subagent prompts, reconciliation templates, skeleton starters)
- `plugins/arrow-maintenance/commands/arrow-maintenance.md`, `map-codebase.md`

## Architecture

**Purpose:** Scale `linked-intent-dev` to projects too large to hold in one context window by adding a navigation index (`docs/arrows/index.yaml`), per-segment orientation pages, and systematic audit. Brownfield bootstrap maps existing code into the tail of the arrow.

**Key Components:**
1. `arrow-maintenance` skill (dual-mode) — ambient catch-and-recommend on arrow-adjacent prompts when `docs/arrows/` exists; command-mode audit-and-update pass when invoked as `/arrow-maintenance`.
2. `map-codebase` skill (behavioral, Claude-Code-specific) — five-phase comprehensive sweep (sweep → lens selection → slicing → reconciliation → artifact generation) with mandatory STOPs, ending in terminal `/lid-setup` + flesh-out prompt.
3. Optional `coherence-check.mjs` — reference Node implementation users may copy into their project and declare under `## LID Tooling` in `CLAUDE.md`.

## Spec Coverage

| Skill / category | Spec range | Implemented | Active gap | Deferred |
|---|---|---|---|---|
| `arrow-maintenance` (command-mode) | ARROW-MAINT-001..027 | 27 | 0 | 0 |
| `map-codebase` | MAP-CODEBASE-001..033 | 32 | 0 | 1 |
| **Total** | | **59** | **0** | **1** |

**Summary:** 59 of 59 active specs implemented; 1 deferred. Ambient-mode behavior is verified by dogfooding per the dual-mode variant (no EARS).

## Key Findings

1. **First audit pass.** `audited` and `audited_sha` were null before this run; bootstrap created the overlay rather than auditing existing arrow docs. Refreshing them across segments after this pass is the natural next step (ARROW-MAINT-006, ARROW-MAINT-007).
2. **Reserved experiments subtree exists in the schema.** `docs/arrows/experiments/` is reserved per `docs/llds/arrow-maintenance.md` § *Experiment-produced artifacts*; this skill ignores it during audit. Currently empty — `bidirectional-differential` will populate it on its first run.
3. **Coherence script bundled but not declared.** `references/coherence-check.mjs` ships with the plugin but no `## LID Tooling` declaration exists in this repo's `CLAUDE.md`. Audit fell back to in-prompt checks (acceptable; the script is opt-in performance acceleration, not a dependency).

## Work Required

### Must Fix
None — all active specs implemented.

### Should Fix
1. After this bootstrap pass, the next `/arrow-maintenance` invocation is the project's *first true audit*. It should refresh `audited` and `audited_sha` across all five segments (ARROW-MAINT-006).

### Nice to Have
2. Consider declaring `references/coherence-check.mjs` (or a copy) under `## LID Tooling` in `CLAUDE.md` to accelerate future audits.
