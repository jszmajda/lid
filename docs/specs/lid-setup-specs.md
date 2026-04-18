# lid-setup specs

**LLD**: docs/llds/linked-intent-dev.md
**Implementing artifacts**:
- plugins/linked-intent-dev/skills/lid-setup/SKILL.md
- plugins/linked-intent-dev/skills/lid-setup/references/claude-md-template.md

Status markers: `[x]` implemented · `[ ]` active gap · `[D]` deferred

---

## Invocation

- `[x]` **LID-SETUP-001**: When the user invokes `/lid-setup` or `/update-lid`, the system SHALL dispatch to the same underlying skill behavior.

## State Dispatch

- `[x]` **LID-SETUP-002**: When invoked on a project with no `CLAUDE.md` and no `docs/` directory, the system SHALL perform a full bootstrap — creating required directories and creating `CLAUDE.md` with LID directives and a mode marker.
- `[x]` **LID-SETUP-003**: When invoked on a project with an existing `CLAUDE.md` that contains no LID directives, the system SHALL append LID directives to `CLAUDE.md` without overwriting or removing its existing content.
- `[x]` **LID-SETUP-004**: When invoked on a project that has LID directives in `CLAUDE.md` but no `## LID Mode:` heading, the system SHALL add the heading with the default mode (Full).
- `[x]` **LID-SETUP-005**: When invoked on a fully-configured project with no mode change requested, the system SHALL check for convention drift — missing required directories, missing required files (including `docs/high-level-design.md`), outdated CLAUDE.md directive sections — and surface each detected difference as a proposed update requiring user confirmation.
- `[x]` **LID-SETUP-006**: When invoked with an explicit mode change request, the system SHALL execute the appropriate mode transition (promotion or demotion).

## Mode Interaction

- `[x]` **LID-SETUP-007**: During a full bootstrap, the system SHALL prompt the user for the intended mode before writing the mode marker, **unless** the caller (e.g., `/map-codebase` invoking `lid-setup` at terminal verification) has already determined the mode and passed it through — in which case the caller-provided mode is used without re-prompting.
- `[x]` **LID-SETUP-008**: When the user does not explicitly specify a mode during bootstrap, the system SHALL select Full LID.
- `[x]` **LID-SETUP-009**: The system SHALL persist the selected mode under a heading of the form `## LID Mode: {Full|Scoped}` in the project's `CLAUDE.md`.
- `[x]` **LID-SETUP-010**: When the user expresses uncertainty about mode selection during bootstrap, the system SHALL describe the differences between Full and Scoped LID before requesting a choice.

## Mode Transitions

- `[x]` **LID-SETUP-011**: When promoting a project from Scoped to Full LID, the system SHALL migrate arrow artifacts from scope-local locations into the standard Full LID positions (`docs/llds/`, `docs/specs/`, `docs/high-level-design.md`).
- `[x]` **LID-SETUP-012**: When scoped arrows have overlapping components during promotion, the system SHALL surface overlaps one pair at a time and request user reconciliation before proceeding.
- `[x]` **LID-SETUP-013**: The system SHALL NOT automatically merge overlapping scoped-arrow content during promotion.
- `[x]` **LID-SETUP-014**: When demoting from Full to Scoped LID, the system SHALL update the `## LID Mode:` marker without performing file migration.

## Directory Structure

- `[x]` **LID-SETUP-015**: When performing a full bootstrap, the system SHALL ensure `docs/`, `docs/llds/`, `docs/specs/`, and `docs/high-level-design.md` exist, creating any that are missing.
- `[x]` **LID-SETUP-016**: When creating `docs/high-level-design.md` on bootstrap, the system SHALL populate it from the HLD template rather than leaving it empty.
- `[x]` **LID-SETUP-017**: The system SHALL NOT create `docs/planning/` during bootstrap or during any subsequent invocation.

## Legacy Artifact Handling

- `[x]` **LID-SETUP-018**: When invoked as `/update-lid` on a project containing a `docs/planning/` directory, the system SHALL flag the directory as obsolete, describe its contents, and offer to remove it.
- `[x]` **LID-SETUP-019**: The system SHALL NOT remove `docs/planning/` without explicit user confirmation.

## Idempotency

- `[x]` **LID-SETUP-020**: When invoked on a well-configured project with no mode change requested and no convention drift detected, the system SHALL produce no file changes.
- `[x]` **LID-SETUP-021**: When invoked on a well-configured project with no changes needed, the system SHALL still inform the user what was detected (mode, overlay presence, directory status) rather than silently no-op.

## Detection Signals

- `[x]` **LID-SETUP-022**: The system SHALL detect existing LID setup by searching `CLAUDE.md` for the literal strings `"linked-intent-dev"` or `"Linked-Intent Development"`. Either match indicates LID directives are present.
- `[x]` **LID-SETUP-023**: The system SHALL detect the mode marker by searching `CLAUDE.md` for a line matching `## LID Mode:` followed by `Full` or `Scoped` (case-insensitive on the mode name, whitespace tolerated around the heading).
- `[x]` **LID-SETUP-024**: The system SHALL detect the arrow-maintenance overlay by the presence of a `docs/arrows/` directory at the project root.

## Arrow-Maintenance Coordination

- `[x]` **LID-SETUP-025**: When generating or updating the LID directives block in `CLAUDE.md`, the system SHALL include arrow-navigation rows pointing at `docs/arrows/index.yaml` and per-segment arrow docs if and only if the arrow-maintenance overlay is detected (LID-SETUP-024).
- `[x]` **LID-SETUP-026**: The system SHALL re-check arrow-maintenance presence on every invocation, so that installing the overlay after initial setup triggers a CLAUDE.md update on the next `/update-lid` run.

## Verification / Show-What-Changed

- `[x]` **LID-SETUP-027**: After making any file changes (bootstrap, append directives, mode transition, drift reconciliation), the system SHALL read back the modified files and surface a summary to the user naming the files changed and the sections added or modified.
- `[x]` **LID-SETUP-028**: The system SHALL NOT complete its invocation without either reporting changes made (per LID-SETUP-027) or explicitly reporting that no changes were needed (per LID-SETUP-021).
- `[x]` **LID-SETUP-029**: When convention drift is detected (per LID-SETUP-005) and the user declines every proposed update, the system SHALL still inform the user of what was detected before exiting, exercising the same inform-and-skip pathway as LID-SETUP-021.
