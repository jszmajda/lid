# Instruction-File Template for LID Projects

Append this block to the project's instruction file — `AGENTS.md` (canonical; the cross-tool convention) or `CLAUDE.md` under Claude Code — during bootstrap. Conditional-include rules (applied before writing to the user's file):

- The `## LID` block is mandatory. Substitute the user's chosen mode into `- Mode:` and the `linked-intent-dev` plugin version the project's docs conform to into `- Version:`.
- The `## LID Scope` section is **included only** when mode is Scoped, and follows the `## LID` block. When mode is Full, omit the section entirely — its absence means "entire project in scope." For Scoped mode, substitute the user's declared include/exclude patterns into the bulleted lists below.
- The "Arrow of intent overlay" row in the navigation table is **included only** when `docs/arrows/` exists in the project root at invocation time. When absent, omit that row entirely — do not write the parenthetical note to the user's file.
- The `## LID Tooling` section is **included only** when the project has tooling to declare (most commonly a coherence-check script). Omit entirely when there is nothing to declare; the skill falls back to in-prompt audit when the section is missing or empty.

---

## LID
- Mode: {Full|Scoped}
- Version: {linked-intent-dev plugin version}

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

Stop after each phase for user review. **Docs carry current intent, written to be read cold** — write each doc as if authored fresh today, from current intent alone: no narration of how it changed, no meaning that needs the conversation that produced it, no rebuttals to questions only a past discussion raised. Rationale, considered alternatives, and constraints a fresh author would independently write stay; record rejected alternatives and why in the LLD's Decisions & Alternatives table, not as asides in body prose.

**Memory vs. intent.** Before saving durable project knowledge to agent or tool memory, test whether it is project *intent* — would a fresh agent, in any tool, next session, need it to build this system correctly? If yes, record it in the arrow (HLD / LLD / EARS / decision doc), which travels and cascades — not in private, per-tool memory, where intent escapes the arrow. Knowledge about the user or how they like to work stays in memory.

### Navigation

| What you need | Where to look |
|---|---|
| High-level design | `docs/high-level-design.md` |
| Design tree (sub-HLDs, LLDs, their specs) | `docs/intent/` — one folder per node |
| EARS specs | beside each design doc as `{node}-specs.md` in the node's folder under `docs/intent/` |
| Decision docs | `docs/decisions/` (project-level) and `docs/intent/<segment>/decisions/` |
| Arrow of intent overlay | `docs/arrows/index.yaml` and per-segment docs in `docs/arrows/` |

### Terminology

- **HLD**: High-Level Design — single project-level doc at `docs/high-level-design.md`.
- **LLD**: Low-Level Design — detailed component design doc in `docs/intent/`. The design layer is a recursive tree: the root is the HLD, leaf LLDs own EARS, and a component deep enough to outgrow one doc becomes a sub-HLD (HLD-shaped, owns no EARS) with children beneath it. "HLD" and "LLD" are roles by position; depth-2 (one HLD over flat leaf LLDs) is the default.
- **EARS**: Easy Approach to Requirements Syntax — structured one-line requirements beside each design doc as `{node}-specs.md` in the node's folder under `docs/intent/`. IDs are path-concatenated — the root-to-leaf path of the owning segment plus a number — so a prefix grep gathers a subtree. Markers: `[x]` implemented, `[ ]` active gap, `[D]` deferred.
- **Arrow**: the unidirectional chain from vision to code (HLD → LLDs → EARS → Tests → Code). Strictly a DAG of intent.
- **Arrow segment**: the territory owned by one leaf LLD — the LLD itself plus the specs, tests, and code that cite its EARS IDs. The boundary is the leaf prefix. Within-segment cascade is free; across-segment cascade pauses.
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
