# Arrow: maintenance (arrow-maintenance plugin)

The dual-mode `/arrow-maintenance` skill — ambient catch-and-recommend on arrow-adjacent prompts plus the command-mode audit-and-update pass. A leaf under the `arrow-maintenance` sub-HLD.

## Status

**MAPPED** — bootstrapped from existing LID docs 2026-04-25 (git SHA `b64c439`).

## References

### Sub-HLD
- `docs/intent/arrow-maintenance/arrow-maintenance-design.md` — the overlay artifact definition, progressive-disclosure navigation model, and lifecycle events this skill operates.

### LLD
- `docs/intent/arrow-maintenance/maintenance/maintenance-design.md`

### EARS
- `docs/intent/arrow-maintenance/maintenance/maintenance-specs.md` (prefix `SCALE-MAINT-*`)

### Tests / Evals
- `plugins/arrow-maintenance/skills/arrow-maintenance/evals/evals.json` — 4 fixtures (audit-existing-overlay incl. the six-check assertion, bootstrap-overlay, redirect-on-no-lid-docs, misplaced-ears-flagged for check 6 / SCALE-MAINT-031)
- `plugins/arrow-maintenance/skills/arrow-maintenance-workspace/` (latest: iteration-2, 2026-08-08, 15/15 with-skill assertions; audit fixtures are git-initialized so `audited_sha` is verifiable)

### Code
- `plugins/arrow-maintenance/skills/arrow-maintenance/SKILL.md` + `references/` (`index-schema.md`, `arrow-doc-template.md`, `audit-checklist.md`, `README-template.md`, `coherence-check.mjs`)
- `plugins/arrow-maintenance/commands/arrow-maintenance.md`

## Spec Coverage

| Spec range | Implemented | Active gap | Deferred |
|---|---|---|---|
| SCALE-MAINT-001..031 | 31 | 0 | 0 |

Ambient-mode behavior is verified by dogfooding per the dual-mode variant (no EARS).
