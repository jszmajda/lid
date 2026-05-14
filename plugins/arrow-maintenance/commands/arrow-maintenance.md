---
name: arrow-maintenance
description: Run an audit-and-update pass on the docs/arrows/ overlay. Dispatches on project state — audits an existing overlay, bootstraps the overlay from existing LID docs, or redirects to /map-codebase or /linked-intent-dev for projects without LID.
---

Invoke the `arrow-maintenance` skill in command mode. The skill dispatches on project state: audits and updates an existing overlay, bootstraps the overlay from existing LID docs if absent, or redirects the user to `/map-codebase` (for brownfield) or `/linked-intent-dev` (for greenfield — invoke with a description of what to build; the workflow bootstraps LID as part of Phase 1) when LID is not installed. See `plugins/arrow-maintenance/skills/arrow-maintenance/SKILL.md` for the full behavior.
