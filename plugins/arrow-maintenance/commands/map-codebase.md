---
name: map-codebase
description: Bootstrap LID in an existing (brownfield) codebase. Reads every file in scope, proposes lens-based clusterings, walks the user through reconciliation, generates skeleton LLDs/HLD/EARS and the arrow overlay, then prompts the user to flesh out the skeletons. Token-intensive by design.
---

Invoke the `map-codebase` skill. Warns upfront about token intensity; asks the user for scope and optional subagent parallelism; runs a six-phase flow ending in `/lid-setup` + a flesh-out prompt. See `plugins/arrow-maintenance/skills/map-codebase/SKILL.md` for the full behavior and Five Critical Rules.
