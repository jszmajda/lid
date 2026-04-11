# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Purpose

A Claude Code plugin marketplace for linked-intent development (LID). Contains installable plugins for structured design-before-code workflows. There is no build system, test suite, or application code.

## Structure

- **`plugins/`**: Claude Code plugin marketplace — three installable plugins
  - **`linked-intent-dev/`**: Core LID workflow + `/lid-setup` command
  - **`arrow-maintenance/`**: Arrow tracking overlay + `/map-codebase` command for brownfield bootstrap
- **`.claude-plugin/marketplace.json`**: Marketplace manifest listing all plugins

## Plugin Architecture

This repo is a **Claude Code plugin marketplace**. Users install via:

```
/plugin marketplace add jszmajda/lid
/plugin install linked-intent-dev@jszmajda-lid
/plugin install arrow-maintenance@jszmajda-lid
```

The plugins form a layered system:

1. **linked-intent-dev** is the core workflow — consult for ALL code changes. New features get full 4-phase design (HLD → LLD → EARS specs → Plan). Bug fixes skip doc creation but still verify intent coherence. Includes `/lid-setup` for project bootstrapping.

2. **arrow-maintenance** overlays on top — adds navigation (`index.yaml`) and tracking (arrow docs) for projects too large to hold in one context window. Includes `/map-codebase` for brownfield codebase mapping.

Both LID plugins use EARS (Easy Approach to Requirements Syntax) for specifications with semantic IDs (`{FEATURE}-{TYPE}-{NNN}`), `@spec` code annotations, and status markers (`[x]` implemented, `[ ]` gap, `[D]` deferred).

## Editing Guidelines

- Each plugin lives in `plugins/<name>/` with `.claude-plugin/plugin.json` manifest
- Skills follow the SKILL.md frontmatter format (`name`, `description` in YAML front matter)
- The skill `description` field is critical — it determines when Claude auto-invokes the skill. Use specific trigger words, not vague descriptions
- Reference templates live in `references/` subdirectories within each skill
