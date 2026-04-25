---
name: differential-audit
description: Audit EARS↔code coherence via a bidirectional differential. With no arguments, opens a scoping conversation that interprets what the user wants audited, maps it to arrows, and captures an explicit EARS selection. With one or more EARS IDs, audits those specs directly using configured defaults. Requires docs/arrows/ overlay from arrow-maintenance.
---

Invoke the `bidirectional-differential` skill in command mode.

- `/differential-audit` — opens the scoping conversation (interprets the user's description, maps to arrows, captures scope and runs-per-direction, confirms with a cost estimate).
- `/differential-audit BIDIFF-001 KWP-UE-004` — audits the listed EARS IDs directly using defaults from `CLAUDE.md`'s `## LID Experimental` section (default N=3).

See `plugins/lid-experimental/skills/bidirectional-differential/SKILL.md` for the full behavior.
