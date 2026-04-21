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
  - **`linked-intent-dev/`**: Core LID workflow + `/lid-setup` command
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

1. **linked-intent-dev** is the core workflow — consult for ALL code changes. New features get full 4-phase design (HLD → LLD → EARS specs → Plan). Bug fixes skip doc creation but still verify intent coherence. Includes `/lid-setup` for project bootstrapping.

2. **arrow-maintenance** overlays on top — adds navigation (`index.yaml`) and tracking (arrow docs) for projects too large to hold in one context window. Includes `/map-codebase` for brownfield codebase mapping.

Both LID plugins use EARS (Easy Approach to Requirements Syntax) for specifications with semantic IDs (`{FEATURE}-{TYPE}-{NNN}`), `@spec` code annotations, and status markers (`[x]` implemented, `[ ]` gap, `[D]` deferred).

## Other Agentic Coding Tools

LID works with any agent that can read per-project instructions. Tools without auto-invoking skills rely on the agent reading this file (or an adapter that points here) on every task. See `docs/setup.md` for the exact adapter file and location per tool.

The methodology is identical across tools — only the invocation differs. Claude Code's plugins automate phase gates; elsewhere the agent follows the same workflow by reading this file.

## Editing Guidelines

- Each plugin lives in `plugins/<name>/` with `.claude-plugin/plugin.json` manifest
- Skills follow the SKILL.md frontmatter format (`name`, `description` in YAML front matter)
- The skill `description` field is critical — it determines when Claude Code auto-invokes the skill. Use specific trigger words, not vague descriptions
- Reference templates live in `references/` subdirectories within each skill

## LID Mode: Full

## Linked-Intent Development (MANDATORY)

**Consult the `linked-intent-dev` skill (Claude Code) or follow the workflow below (other tools) for ALL code changes.** All changes start with intent:

```
HLD → LLDs → EARS → Tests → Code
```

- **New features**: Full workflow (HLD → LLD → EARS → Tests → Code)
- **Bug fixes**: Walk the arrow like any other change — find where intent diverged, cascade from there. No short-circuit.
- **If unsure**: Use the full workflow.

Mutation, not accumulation — docs reflect current intent, not history.

### Navigation

| What you need | Where to look |
|---|---|
| High-level design | `docs/high-level-design.md` |
| Low-level designs | `docs/llds/` |
| EARS specs | `docs/specs/` |
| Setup for other tools | `docs/setup.md` |

### Terminology

- **LLD**: Low-level design — detailed component design docs in `docs/llds/`
- **EARS**: Easy Approach to Requirements Syntax — structured requirements in `docs/specs/`. Markers: `[x]` implemented, `[ ]` active gap, `[D]` deferred
- **Arrow**: A traced dependency from HLD through code, tracked in `docs/arrows/`

### Code Annotations

Annotate code with `@spec` comments linking to EARS IDs:

```
// @spec AUTH-UI-001, AUTH-UI-002
```

Test files also reference specs for traceability.
