# Arrow: linked-intent-dev / core (workflow skill)

The pure-prose `linked-intent-dev` workflow skill (invokable as `/linked-intent-dev`) — the mandatory core that walks every change through the six-phase arrow with mandatory stops, and enforces cascade discipline. A leaf under the `LID` sub-HLD.

## Status

**AUDITED** — last audited 2026-06-07 (git SHA `65a143750760`). The workflow skill's behaviors are captured as `LID-CORE-*` specs against the `SKILL.md` artifact. No automated eval suite — the skill is guidance the agent consults, not a deterministic harness run; per the eval-metadata convention the coverage audit does not apply to this leaf.

## References

### HLD
- `docs/high-level-design.md` § Architecture / Plugins (linked-intent-dev plugin); § Methodology; § Key Design Decisions / The arrow for LID itself

### LLD
- `docs/intent/linked-intent-dev/core/core-design.md` — this segment's leaf LLD.
- `docs/intent/linked-intent-dev/linked-intent-dev-design.md` — parent `LID` sub-HLD for plugin-level concerns (mode detection, spec ID format, LID-on-LID linkage inversion, eval-metadata schema).

### EARS
- `docs/intent/linked-intent-dev/core/core-specs.md` (57 specs, prefix `LID-CORE-*`)

### Tests / Evals
- None. The pure-prose workflow skill has no eval suite; its behaviors are verified by dogfooding (the LID repo runs on this skill).

### Code (skill prompt and references)
- `plugins/linked-intent-dev/skills/linked-intent-dev/SKILL.md` + `references/` (`ears-syntax.md`, `lld-templates.md`, `hld-template.md`, `decision-doc-template.md`)

No command stub — the skill is directly invokable as `/linked-intent-dev` per Claude Code's skills model.

## Architecture

**Purpose:** Translate the HLD's arrow-of-intent methodology into the workflow guidance users interact with on every change. Owns mode-aware triggering, the six-phase workflow (HLD → LLD → EARS → intent-narrowing edge audit → tests-first → code) with mandatory stops, coherence pre-flight and verification, within-segment-free / across-segment-paused cascade discipline, the placement rule, bug-fix-walks-the-arrow, and user-override handling.

## Spec Coverage

| Category | Spec range | Implemented | Active gap | Deferred |
|---|---|---|---|---|
| Triggering | LID-CORE-001..004 | 4 | 0 | 0 |
| Phase Governance | LID-CORE-005..007 | 3 | 0 | 0 |
| Phase 1–6 | LID-CORE-008..025 | 18 | 0 | 0 |
| Cascade Discipline | LID-CORE-026..035 | 10 | 0 | 0 |
| Bug Fixes / Overrides | LID-CORE-036..037 | 2 | 0 | 0 |
| Brownfield | LID-CORE-038 | 1 | 0 | 0 |
| **Total** | | **38** | **0** | **0** |

**Summary:** All 38 specs `[x]` — the `SKILL.md` embodies every described behavior. The `[x]` marker is artifact coverage; there is no eval suite (and the coverage audit does not apply to a pure-prose skill).

## Key Findings

1. **`@spec` annotations live in the spec header, not the skill prompt (LID-on-LID inversion).** Embedding `@spec` IDs in `SKILL.md` prose would bend runtime behavior; `docs/intent/linked-intent-dev/core/core-specs.md` carries the artifact pointer in its header instead. An audit looking for `@spec` annotations in this skill's prompt will correctly find none.
2. **No eval suite for a pure-prose skill is expected, not drift.** The coverage audit applies only to behavioral leaves (`LID-UPDATE`, `LID-COACH`).

## Work Required

No must-fix items. The segment is feature-complete relative to its current LLD scope; future work cascades from HLD-level changes when they land.
