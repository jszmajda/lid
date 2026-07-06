# AGENTS.md

Project instructions for coding agents working in this repository. The file is named `AGENTS.md` per the emerging cross-tool convention; tools that look for other filenames (e.g. Claude Code's `CLAUDE.md`) find the same content via symlink or adapter file.

## Repository Purpose

This is the **Linked-Intent Development (LID)** project — a methodology for keeping intent and code coherent in agentic codebases. The repo ships:

- The methodology itself (this document plus `docs/`).
- **Two Claude Code plugins** under `plugins/` — richest integration, with auto-invoking skills and slash commands.
- Rule-file adapters for other agentic coding tools (Cursor, Windsurf, GitHub Copilot, Aider, Continue, JetBrains Junie, Zed, Codex, and any tool that reads `AGENTS.md`). See `docs/setup.md` for per-tool setup.

There is no build system, test suite, or application code. The repo is simultaneously the distribution source for the plugins and the canonical LID-on-LID reference — its own `docs/` tree is LID applied to LID.

## Structure

- **`plugins/`**: Two installable Claude Code plugins
  - **`linked-intent-dev/`**: Core LID workflow skill (`/linked-intent-dev`), configuration skill (`/update-lid`), and principle-review coach (`/lid-coach`)
  - **`arrow-maintenance/`**: Arrow tracking overlay + `/map-codebase` command for brownfield bootstrap
- **`.claude-plugin/marketplace.json`**: Claude Code plugin manifest (technical file — users install via `/plugin marketplace add jszmajda/lid`)
- **`docs/setup.md`**: Per-tool setup instructions for non-Claude-Code agents
- **`docs/`**: The HLD, LLDs, and EARS specs that define the project

## Plugin Architecture (Claude Code)

Users install via:

```
/plugin marketplace add jszmajda/lid
/plugin install linked-intent-dev@jszmajda-lid
/plugin install arrow-maintenance@jszmajda-lid
```

The plugins form a layered system:

1. **linked-intent-dev** is the core workflow — consult for ALL code changes. Every change walks the full arrow (HLD → LLD → EARS → Tests → Code); each phase's output is inspected — by the user or an inspector they name — before the next begins, and ambiguous spec readings go back to the user. Bug fixes walk the same arrow — find where intent diverged and cascade from there; no short-circuit. Fresh projects start with `/linked-intent-dev` + a description of what to build (the workflow bootstraps LID inline). Established projects use `/update-lid` to reconcile drift, change modes, or refresh conventions.

2. **arrow-maintenance** overlays on top — adds navigation (`index.yaml`) and tracking (arrow docs) for projects too large to hold in one context window. Includes `/map-codebase` for brownfield codebase mapping.

Both LID plugins use EARS (Easy Approach to Requirements Syntax) for specifications with path-concatenated IDs (an ID is the root-to-leaf path through the design tree — `FEATURE-NNN` flat, extending one segment per level as intent nests, e.g. `PEVAL-RUN-014`), `@spec` code annotations, and status markers (`[x]` implemented, `[ ]` gap, `[D]` deferred).

## Other Agentic Coding Tools

LID works with any agent that can read per-project instructions. Tools without auto-invoking skills rely on the agent reading this file (or an adapter that points here) on every task. See `docs/setup.md` for the exact adapter file and location per tool.

The methodology is identical across tools — only the invocation differs. Claude Code's plugins automate phase gates; elsewhere the agent follows the same workflow by reading this file.

## Editing Guidelines

- Each plugin lives in `plugins/<name>/` with `.claude-plugin/plugin.json` manifest
- Skills follow the SKILL.md frontmatter format (`name`, `description` in YAML front matter)
- The skill `description` field is critical — it determines when Claude Code auto-invokes the skill. Use specific trigger words, not vague descriptions
- Reference templates live in `references/` subdirectories within each skill

## LID
- Mode: Full
- Version: 1.4.0

## Linked-Intent Development (MANDATORY)

**Consult the `linked-intent-dev` skill (Claude Code) or follow the workflow below (other tools) for ALL code changes.** All changes start with intent:

```
HLD → LLDs → EARS → Tests → Code
```

- **New features**: Full workflow (HLD → LLD → EARS → Tests → Code)
- **Bug fixes**: Walk the arrow like any other change — find where intent diverged, cascade from there. No short-circuit.
- **If unsure**: Use the full workflow.

**Docs carry current intent, written to be read cold.** Write each doc as if authored fresh today, from current intent alone — no narration of how it changed, no meaning that needs the conversation that produced it, no rebuttals to questions only a past discussion raised. Rationale, considered alternatives, and constraints a fresh author would independently write stay; record rejected alternatives and why in the LLD's Decisions & Alternatives table, not as asides in body prose.

**Memory vs. intent.** Before saving durable project knowledge to agent or tool memory, test whether it is project *intent* — would a fresh agent, in any tool, next session, need it to build this system correctly? If yes, record it in the arrow (HLD / LLD / EARS / decision doc), which travels and cascades — not in private, per-tool memory, where intent escapes the arrow. Knowledge about the user or how they like to work stays in memory.

### Navigation

| What you need | Where to look |
|---|---|
| High-level design | `docs/high-level-design.md` |
| Design tree (HLD's children: sub-HLDs, LLDs, their specs) | `docs/intent/` — one folder per node |
| EARS specs | `{node}-specs.md` beside each design doc in `docs/intent/` |
| Decision docs | `docs/decisions/` (project-level) and `docs/intent/<segment>/decisions/` |
| Arrow of intent overlay | `docs/arrows/index.yaml` and per-segment docs in `docs/arrows/` |
| Setup for other tools | `docs/setup.md` |

### Terminology

- **HLD / LLD / sub-HLD**: the design layer is a recursive tree — the HLD is the root, leaf LLDs own EARS, and a component with internal depth becomes a sub-HLD (HLD-shaped, grouping child LLDs). "HLD" and "LLD" are roles by position; depth-2 (one HLD over flat LLDs) is the default. Design docs live in `docs/intent/`
- **EARS**: Easy Approach to Requirements Syntax — structured requirements living beside each design doc as `{node}-specs.md` in the node's folder under `docs/intent/`, with path-concatenated IDs. Markers: `[x]` implemented, `[ ]` active gap, `[D]` deferred
- **Decision doc**: a standalone record of a decision that stays *live* for a cold reader of the landed result (rare), in a node's `decisions/` directory; owns no EARS and carries no status (presence is acceptance)
- **Arrow**: A traced dependency from HLD through code, tracked in `docs/arrows/`

### Code Annotations

Annotate code with `@spec` comments linking to EARS IDs:

```
// @spec AUTH-UI-001, AUTH-UI-002
```

Test files also reference specs for traceability.
