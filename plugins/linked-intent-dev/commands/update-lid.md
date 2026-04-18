---
name: update-lid
description: Update LID configuration on an existing project — reconcile conventions, update directives, change modes, handle legacy artifacts. Alias of /lid-setup; the underlying skill dispatches on project state.
---

Invoke the `lid-setup` skill. `/update-lid` and `/lid-setup` are aliases — both route to the same skill, which dispatches based on whether the project is fresh or already configured. Users whose mental model prefers a separate "update" verb use this name; functionally it is identical to `/lid-setup`. See `plugins/linked-intent-dev/skills/lid-setup/SKILL.md`.
