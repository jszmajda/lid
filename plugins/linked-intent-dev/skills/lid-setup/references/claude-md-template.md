# CLAUDE.md Template for LID Projects

Append this block to the project's `CLAUDE.md` during bootstrap. Conditional-include rules (applied before writing to the user's file):

- The `## LID Mode: {Full|Scoped}` heading is mandatory — substitute the user's chosen mode.
- The `## LID Scope` section is **included only** when mode is Scoped. When mode is Full, omit the section entirely — its absence means "entire project in scope." For Scoped mode, substitute the user's declared include/exclude patterns into the bulleted lists below.
- The "Arrow of intent overlay" row in the navigation table is **included only** when `docs/arrows/` exists in the project root at invocation time. When absent, omit that row entirely — do not write the parenthetical note to the user's file.
- The `## LID Tooling` section is **included only** when the project has tooling to declare (most commonly a coherence-check script). Omit entirely when there is nothing to declare; the skill falls back to in-prompt audit when the section is missing or empty.

---

## LID Mode: {Full|Scoped}

## LID Scope

*(Include this section only when mode is Scoped. Omit entirely when mode is Full.)*

Paths in scope:
- `{pattern}`
- `{pattern}`

Paths explicitly excluded:
- `{pattern}`

## Linked-Intent Development (MANDATORY)

**Consult the `linked-intent-dev` skill for ALL code changes.** All changes flow through the arrow of intent in one direction:

```
HLD → LLDs → EARS → Tests → Code
```

- **New features and refactors**: full six-phase workflow (HLD check → LLD check/draft → EARS → intent-narrowing edge audit → tests-first → code).
- **Bug fixes**: walk the arrow like any other change — find where behavior diverged from intent and cascade from there. No short-circuit.
- **If unsure**: use the full workflow.

Stop after each phase for user review. Mutation, not accumulation — docs reflect current intent, not history.

### Navigation

| What you need | Where to look |
|---|---|
| High-level design | `docs/high-level-design.md` |
| Low-level designs | `docs/llds/` |
| EARS specs | `docs/specs/` |
| Arrow of intent overlay | `docs/arrows/index.yaml` and per-segment docs in `docs/arrows/` |

### Terminology

- **HLD**: High-Level Design — single project-level doc at `docs/high-level-design.md`.
- **LLD**: Low-Level Design — detailed component design doc in `docs/llds/`. One per intent component.
- **EARS**: Easy Approach to Requirements Syntax — structured one-line requirements with globally unique IDs in `docs/specs/`. Markers: `[x]` implemented, `[ ]` active gap, `[D]` deferred.
- **Arrow**: the unidirectional chain from vision to code (HLD → LLDs → EARS → Tests → Code). Strictly a DAG of intent.
- **Arrow segment**: the territory owned by one LLD — the LLD itself plus the specs, tests, and code that cite its EARS IDs. Within-segment cascade is free; across-segment cascade pauses.
- **Cascade**: propagating a change downstream through the arrow so adjacent levels stay coherent.

### Code annotations

Annotate code and tests with `@spec` comments citing EARS IDs:

```
// @spec AUTH-UI-001, AUTH-UI-002
```

Place the annotation at the *entry point of the behavior's implementation graph* — the topmost function or module owning the specified behavior, not every helper. When a behavior spans multiple subsystems (UI + API + database, for example), annotate at the entry point in each subsystem. Tests follow the same rule: annotate the test that directly exercises the spec, not every inner assertion.

## LID Tooling

Declare project-local helper scripts LID-related skills should invoke instead of their in-prompt fallbacks. When present, the listed scripts are authoritative for the deterministic checks they perform. When absent or empty, skills fall back to performing the checks in-prompt.

- **Coherence check**: `bin/coherence-check.mjs` — performs the audit checks described in `plugins/arrow-maintenance/skills/arrow-maintenance/references/audit-checklist.md`. A Node reference implementation is bundled at `plugins/arrow-maintenance/skills/arrow-maintenance/references/coherence-check.mjs` that users may copy, adapt, or replace with an equivalent in any language. Set this to your actual path (e.g., `scripts/check-coherence.py`, `bin/lid-audit`, etc.).
