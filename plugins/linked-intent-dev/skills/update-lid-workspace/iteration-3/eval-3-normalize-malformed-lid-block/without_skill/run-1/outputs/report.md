# LID Reconciliation Report

**Project:** My Project
**Action:** Reconcile conventions (normalize malformed `## LID` block + restore truncated directives)

## What was detected

| Signal | Result |
|---|---|
| LID directives present | Yes (`Consult the linked-intent-dev skill...`) |
| `## LID` metadata block | **Malformed** — mode merged into the heading (`## LID Mode: Full`) and the `- Mode:` bullet was missing |
| Project version | `1.2.0` |
| Installed `linked-intent-dev` version | `1.2.0` — **match**, so no version-walk needed |
| Directives section (`## Linked-Intent Development`) | **Truncated** — only the lead sentence; arrow diagram, change-type bullets, "read cold" guidance, Navigation, Terminology, and Code-annotations sections were all missing |
| `docs/high-level-design.md` | Present (correct) |
| `docs/intent/` | Present (correct) |
| `docs/arrows/` overlay | Absent — arrow-navigation row correctly omitted |
| LID Tooling (e.g. coherence-check) | None declared — `## LID Tooling` section correctly omitted |
| `docs/planning/` (legacy) | None |

The project is at the current conventions version (1.2.0), so this was a **convention-drift reconciliation**, not a version-walk.

## Changes applied

Rewrote `CLAUDE.md` (preserving the existing `# My Project` title and existing content):

1. **Normalized the `## LID` block in place.** The malformed `## LID Mode: Full` heading was rewritten to the canonical form rather than appending a second block:
   ```
   ## LID
   - Mode: Full
   - Version: 1.2.0
   ```
   Mode `Full` was recovered from the malformed heading; `- Version:` was preserved at `1.2.0`.

2. **Restored the full directives block.** The truncated `## Linked-Intent Development (MANDATORY)` section was brought back to the current 1.2.0 template — the arrow diagram (`HLD -> LLDs -> EARS -> Tests -> Code`), the new-features / bug-fixes / if-unsure bullets, the "stop after each phase" + "docs carry current intent" guidance, and the **Navigation**, **Terminology**, and **Code annotations** subsections.

## Not changed (intentionally)

- **No `## LID Scope` section** — mode is Full, so scope is the entire project (the section's absence is correct).
- **No arrow-navigation row** — `docs/arrows/` is absent.
- **No `## LID Tooling` section** — no project-local tooling to declare.
- **No version-walk** — project version equals the installed version.
- **`docs/high-level-design.md` and `docs/intent/`** were already present and left untouched (the HLD remains a stub for you to fill in via `/linked-intent-dev`).

## Recommended next step

The HLD at `docs/high-level-design.md` is still a stub (`Problem: (not yet specified)`) and `docs/intent/` is empty. When you're ready to capture intent, run `/linked-intent-dev` with a description of what you're building — its Phase 1 will flesh out the HLD and seed the design tree.
