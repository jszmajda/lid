# Arrow: linked-intent-dev

The mandatory core LID workflow plugin — the pure-prose `linked-intent-dev` skill plus two behavioral skills (`lid-setup`, `lid-coach`).

## Status

**MAPPED** — bootstrapped from existing LID docs on 2026-04-25 (git SHA `b64c439`). Spec markers reflect partial implementation: `lid-setup` complete; `lid-coach` in-flight (skill directory and command stub untracked, all 47 LID-COACH specs still `[ ]`).

## References

### HLD
- `docs/high-level-design.md` § Architecture / Plugins (linked-intent-dev plugin); § Key Design Decisions / The arrow for LID itself

### LLD
- `docs/llds/linked-intent-dev.md`

### EARS
- `docs/specs/lid-setup-specs.md` (34 specs, prefix `LID-SETUP-*`)
- `docs/specs/lid-coach-specs.md` (47 specs, prefix `LID-COACH-*`)

The pure-prose `linked-intent-dev` skill carries no EARS — it is verified by dogfooding per the HLD's pure-prose variant.

### Tests / Evals
- `plugins/linked-intent-dev/skills/lid-setup-workspace/` (skill-creator iteration outputs; latest: iteration-1, three evals)
- No coach evals yet (skill not implemented).

### Code (skill prompts and references)
- `plugins/linked-intent-dev/.claude-plugin/plugin.json`
- `plugins/linked-intent-dev/skills/linked-intent-dev/SKILL.md` + `references/`
- `plugins/linked-intent-dev/skills/lid-setup/SKILL.md` + `references/`
- `plugins/linked-intent-dev/skills/lid-coach/SKILL.md` (untracked)
- `plugins/linked-intent-dev/commands/lid-setup.md`, `update-lid.md`, `lid-coach.md` (lid-coach.md untracked)

## Architecture

**Purpose:** Translate the HLD's arrow-of-intent methodology into the three skills users interact with on every LID-driven change. Owns mode detection, phase cascade, EARS authoring, `@spec` placement, and the principle-based coach review.

**Key Components:**
1. `linked-intent-dev` skill (pure-prose) — six-phase workflow guidance: HLD → LLD → EARS → intent-narrowing edge audit → tests-first → code; mode-aware, mandatory phase stops, within-segment cascade free / across-segment paused.
2. `lid-setup` skill (behavioral) — bootstrap and idempotent reconciliation; state-dispatch table; mode marker management; `/lid-setup` and `/update-lid` aliases.
3. `lid-coach` skill (behavioral) — advisory principle-review producing prioritized, coach-toned report; auto-invocation disabled.

## Spec Coverage

| Skill / category | Spec range | Implemented | Active gap | Deferred |
|---|---|---|---|---|
| `lid-setup` | LID-SETUP-001..034 | 34 | 0 | 0 |
| `lid-coach` | LID-COACH-001..047 | 0 | 47 | 0 |
| **Total** | | **34** | **47** | **0** |

**Summary:** 34 of 81 active specs implemented (lid-setup complete). The 47 LID-COACH gaps are expected — the skill is in-flight, with the SKILL.md and command stub freshly added but not yet committed.

## Key Findings

1. **`lid-coach` in-flight.** `plugins/linked-intent-dev/skills/lid-coach/` and `plugins/linked-intent-dev/commands/lid-coach.md` are present in the working tree but untracked (`git status`). Once the skill body lands, run a `linked-intent-dev` Phase 6 cascade to flip implemented LID-COACH specs from `[ ]` to `[x]`.
2. **`@spec` annotations live in spec headers, not skill prompts (LID-on-LID inversion).** Per `docs/llds/linked-intent-dev.md` § *Linkage without prompt pollution*, embedding `@spec` IDs in `SKILL.md` prose would bend runtime behavior. Spec files carry the upstream-to-downstream pointer via `**Implementing artifacts**:` headers — confirmed in `docs/specs/lid-setup-specs.md:1-10` and `docs/specs/lid-coach-specs.md:1-10`. Audits looking for `@spec` annotations in skill prompts will (correctly) find none.
3. **No structured eval suite yet for the pure-prose `linked-intent-dev` skill.** This matches the HLD's pure-prose variant (verification by dogfooding); no action required.

## Work Required

### Must Fix
1. Land the `lid-coach` skill body and command (currently untracked); flip the 47 LID-COACH specs from `[ ]` to `[x]` as behavior is implemented (LID-COACH-001..047).

### Should Fix
2. Once `lid-coach` is committed, run `skill-creator` evals on the new behavioral skill per the HLD's `HLD → LLD → EARS → evals + SKILL.md` arrow shape for behavioral skills.
