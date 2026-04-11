---
name: lid-setup
description: Set up a project for linked-intent development (LID). Creates docs/ directory structure, appends CLAUDE.md directives. Run once when adopting LID in a new project.
disable-model-invocation: true
---

# LID Project Setup

Bootstrap a project for linked-intent development. Run this once per project.

## What to Do

### 1. Check Current State

Before making changes, check what already exists:
- Does `CLAUDE.md` exist? Does it already reference linked-intent-dev?
- Do `docs/llds/`, `docs/specs/`, `docs/planning/` exist?

If LID directives are already in CLAUDE.md (grep for "linked-intent-dev" or "Linked-Intent Development"), inform the user and skip. Don't duplicate.

### 2. Create Directory Structure

Create these directories if they don't exist:
- `docs/llds/`
- `docs/specs/`
- `docs/planning/`
- `docs/planning/old/`

### 3. Append CLAUDE.md Directives

Append the template from [claude-md-template.md](references/claude-md-template.md) to the project's CLAUDE.md. Create CLAUDE.md if it doesn't exist.

**Do NOT overwrite existing CLAUDE.md content.** Append to it.

If the arrow-maintenance plugin is also installed in this project (check for `docs/arrows/` or grep settings for arrow-maintenance), include the arrow navigation rows in the navigation table.

### 4. Verify

Read back CLAUDE.md and confirm the directives are present and well-formatted. Show the user what was added.
