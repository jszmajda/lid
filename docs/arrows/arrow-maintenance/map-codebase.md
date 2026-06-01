# Arrow: map-codebase (arrow-maintenance plugin)

The `/map-codebase` brownfield-bootstrap skill — five-phase sweep (sweep → lens selection → slicing → reconciliation → artifact generation) with mandatory STOPs, ending in the terminal `/update-lid` + flesh-out prompt. A leaf under the `arrow-maintenance` sub-HLD.

## Status

**MAPPED** — bootstrapped from existing LID docs 2026-04-25 (git SHA `b64c439`).

## References

### Sub-HLD
- `docs/intent/arrow-maintenance/arrow-maintenance-design.md` — the overlay schema and arrow-doc format the bootstrap output conforms to.

### LLD
- `docs/intent/arrow-maintenance/map-codebase/map-codebase-design.md`

### EARS
- `docs/intent/arrow-maintenance/map-codebase/map-codebase-specs.md` (prefix `SCALE-MAP-*`)

### Tests / Evals
- `plugins/arrow-maintenance/skills/map-codebase-workspace/iteration-1/` — `skill-creator` iteration outputs

### Code
- `plugins/arrow-maintenance/skills/map-codebase/SKILL.md` + `references/` (subagent-sweep prompts, reconciliation templates, skeleton starters)
- `plugins/arrow-maintenance/commands/map-codebase.md`

## Spec Coverage

| Spec range | Implemented | Active gap | Deferred |
|---|---|---|---|
| SCALE-MAP-001..033 | 32 | 0 | 1 |
