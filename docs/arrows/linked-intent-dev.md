# Arrow: linked-intent-dev

The mandatory core LID workflow plugin — the pure-prose `linked-intent-dev` workflow skill (invokable as `/linked-intent-dev`) plus the behavioral `update-lid` skill (invokable as `/update-lid`). The plugin's third skill, `lid-coach`, has its own arrow segment at `docs/arrows/lid-coach.md`.

## Status

**MAPPED** — sampled 2026-05-14. `update-lid` complete (34/34 specs `[x]`); the pure-prose workflow skill is verified by dogfooding (no EARS, per the HLD's pure-prose variant).

## References

### HLD
- `docs/high-level-design.md` § Architecture / Plugins (linked-intent-dev plugin); § Key Design Decisions / The arrow for LID itself

### LLD
- `docs/llds/linked-intent-dev.md` — covers the workflow skill, `update-lid`, and plugin-level concerns shared by all three skills (mode detection, spec ID format, LID-on-LID linkage inversion, eval metadata schema).

### EARS
- `docs/specs/update-lid-specs.md` (34 specs, prefix `UPDATE-LID-*`)

The pure-prose `linked-intent-dev` skill carries no EARS — it is verified by dogfooding per the HLD's pure-prose variant.

### Tests / Evals
- `plugins/linked-intent-dev/skills/update-lid-workspace/` (skill-creator iteration outputs; latest: iteration-1, three evals)

### Code (skill prompts and references)
- `plugins/linked-intent-dev/.claude-plugin/plugin.json`
- `plugins/linked-intent-dev/skills/linked-intent-dev/SKILL.md` + `references/`
- `plugins/linked-intent-dev/skills/update-lid/SKILL.md` + `references/`

No command stubs — skills are directly invokable by name (`/linked-intent-dev`, `/update-lid`) per Claude Code's skills model.

## Architecture

**Purpose:** Translate the HLD's arrow-of-intent methodology into the workflow guidance and configuration-reconciliation skills users interact with on every LID-driven change. Owns mode detection, phase cascade, EARS authoring, `@spec` placement conventions, and the LID-on-LID linkage inversion.

**Key Components:**
1. `linked-intent-dev` skill (pure-prose) — six-phase workflow guidance: HLD → LLD → EARS → intent-narrowing edge audit → tests-first → code; mode-aware, mandatory phase stops, within-segment cascade free / across-segment paused.
2. `update-lid` skill (behavioral) — bootstrap and idempotent reconciliation; state-dispatch table; mode marker management; invoked as `/update-lid`, also reachable as a sub-step from `/linked-intent-dev`'s Phase 1 and from `/map-codebase`'s terminal step.

## Spec Coverage

| Skill / category | Spec range | Implemented | Active gap | Deferred |
|---|---|---|---|---|
| `update-lid` | UPDATE-LID-001..034 | 34 | 0 | 0 |
| **Total** | | **34** | **0** | **0** |

**Summary:** All 34 active specs implemented; `update-lid` is feature-complete.

## Key Findings

1. **`@spec` annotations live in spec headers, not skill prompts (LID-on-LID inversion).** Per `docs/llds/linked-intent-dev.md` § *Spec-File Header Format (LID-on-LID Linkage Inversion)*, embedding `@spec` IDs in `SKILL.md` prose would bend runtime behavior. Spec files carry the upstream-to-downstream pointer via `**Implementing artifacts**:` headers — confirmed in `docs/specs/update-lid-specs.md:1-10`. Audits looking for `@spec` annotations in skill prompts will (correctly) find none.
2. **No structured eval suite for the pure-prose `linked-intent-dev` skill.** This matches the HLD's pure-prose variant (verification by dogfooding); no action required.

## Work Required

No must-fix items. The segment is feature-complete relative to its current LLD scope; future work cascades from HLD-level changes when they land.
