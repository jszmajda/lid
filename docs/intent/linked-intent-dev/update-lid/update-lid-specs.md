# update-lid specs

**LLD**: docs/intent/linked-intent-dev/update-lid/update-lid-design.md
**Implementing artifacts**:
- plugins/linked-intent-dev/skills/update-lid/SKILL.md
- plugins/linked-intent-dev/skills/update-lid/references/claude-md-template.md

Status markers: `[x]` implemented · `[ ]` active gap · `[D]` deferred

---

## Invocation

- `[x]` **LID-UPDATE-001**: When the user invokes `/update-lid`, the system SHALL dispatch to the `update-lid` skill. The skill SHALL also be reachable as a sub-step from `/linked-intent-dev` (the workflow skill) when the workflow detects an unconfigured project, and from `/map-codebase` at its terminal verification step.

## State Dispatch

- `[x]` **LID-UPDATE-002**: When invoked on a project with no `CLAUDE.md` and no `docs/` directory, the system SHALL perform a full bootstrap — creating required directories and creating `CLAUDE.md` with LID directives and a mode marker.
- `[x]` **LID-UPDATE-003**: When invoked on a project with an existing `CLAUDE.md` that contains no LID directives, the system SHALL append LID directives to `CLAUDE.md` without overwriting or removing its existing content.
- `[x]` **LID-UPDATE-004**: When invoked on a project that has LID directives in `CLAUDE.md` but no well-formed `## LID` block — none present, or a malformed one (mode merged into the heading as `## LID Mode: …`, a missing `- Mode:` or `- Version:` bullet, or stray non-template bullets) — the system SHALL write the canonical block (a bare `## LID` heading with `- Mode:` defaulting to Full and `- Version:`), normalizing a malformed block in place rather than appending a second block.
- `[x]` **LID-UPDATE-005**: When invoked on a fully-configured project with no mode change requested, the system SHALL check for convention drift — missing required directories, missing required files (including `docs/high-level-design.md`), outdated CLAUDE.md directive sections (including a malformed `## LID` block per LID-UPDATE-004), a node folder holding more than its `<node>-design.md` plus optional `<node>-specs.md` pair (an LLD not yet relocated into its own node folder), or a design doc whose `prefix:` frontmatter is an array — detecting the structural-marker categories independently of version lag — and surface each detected difference as a proposed update requiring user confirmation.
- `[x]` **LID-UPDATE-006**: When invoked with an explicit mode change request, the system SHALL execute the appropriate mode transition (promotion or demotion).

## Mode Interaction

- `[x]` **LID-UPDATE-007**: During a full bootstrap, the system SHALL prompt the user for the intended mode before writing the mode marker, **unless** the caller (e.g., `/map-codebase` invoking `update-lid` at terminal verification) has already determined the mode and passed it through — in which case the caller-provided mode is used without re-prompting.
- `[x]` **LID-UPDATE-008**: When the user does not explicitly specify a mode during bootstrap, the system SHALL select Full LID.
- `[x]` **LID-UPDATE-009**: The system SHALL persist the selected mode as a `- Mode: {Full|Scoped}` bullet in the `## LID` block of the project's `CLAUDE.md`.
- `[x]` **LID-UPDATE-010**: When the user expresses uncertainty about mode selection during bootstrap, the system SHALL describe the differences between Full and Scoped LID before requesting a choice.

## Mode Transitions

- `[x]` **LID-UPDATE-011**: When promoting a project from Scoped to Full LID, the system SHALL migrate arrow artifacts from scope-local locations into the standard Full LID positions — the `docs/intent/` design tree (each node a folder with its `{node}-design.md` and `{node}-specs.md`) and `docs/high-level-design.md`.
- `[x]` **LID-UPDATE-012**: When scoped arrows have overlapping components during promotion, the system SHALL surface overlaps one pair at a time and request user reconciliation before proceeding.
- `[x]` **LID-UPDATE-013**: The system SHALL NOT automatically merge overlapping scoped-arrow content during promotion.
- `[x]` **LID-UPDATE-014**: When demoting from Full to Scoped LID, the system SHALL update the `## LID` block's `- Mode:` bullet without performing file migration.

## Directory Structure

- `[x]` **LID-UPDATE-015**: When performing a full bootstrap, the system SHALL ensure `docs/`, `docs/intent/`, and `docs/high-level-design.md` exist, creating any that are missing (specs live inside node folders under `docs/intent/`).
- `[x]` **LID-UPDATE-016**: When creating `docs/high-level-design.md` on bootstrap, the system SHALL populate it from the HLD template rather than leaving it empty.
- `[x]` **LID-UPDATE-017**: The system SHALL NOT create `docs/planning/` during bootstrap or during any subsequent invocation.
- `[x]` **LID-UPDATE-035**: The system SHALL NOT create decision-doc directories (`docs/decisions/` for project-level decisions, `docs/intent/<segment>/decisions/` for segment-level decisions) at bootstrap. Each SHALL be created lazily — only when the first decision doc at that level is written.

## Legacy Artifact Handling

- `[x]` **LID-UPDATE-018**: When invoked as `/update-lid` on a project containing a `docs/planning/` directory, the system SHALL flag the directory as obsolete, describe its contents, and offer to remove it.
- `[x]` **LID-UPDATE-019**: The system SHALL NOT remove `docs/planning/` without explicit user confirmation.

## Idempotency

- `[x]` **LID-UPDATE-020**: When invoked on a well-configured project with no mode change requested and no convention drift detected, the system SHALL produce no file changes.
- `[x]` **LID-UPDATE-021**: When invoked on a well-configured project with no changes needed, the system SHALL still inform the user what was detected (mode, overlay presence, directory status) rather than silently no-op.

## Detection Signals

- `[x]` **LID-UPDATE-022**: The system SHALL detect existing LID setup by searching `CLAUDE.md` for the literal strings `"linked-intent-dev"` or `"Linked-Intent Development"`. Either match indicates LID directives are present.
- `[x]` **LID-UPDATE-023**: The system SHALL detect mode by reading the `- Mode: {Full|Scoped}` bullet in `CLAUDE.md`'s `## LID` block (case-insensitive on the mode name, whitespace tolerated), and SHALL detect the project's conventions version by reading the `- Version: {X.Y.Z}` bullet in the same block.
- `[x]` **LID-UPDATE-024**: The system SHALL detect the arrow-maintenance overlay by the presence of a `docs/arrows/` directory at the project root.

## Arrow-Maintenance Coordination

- `[x]` **LID-UPDATE-025**: When generating or updating the LID directives block in `CLAUDE.md`, the system SHALL include arrow-navigation rows pointing at `docs/arrows/index.yaml` and per-segment arrow docs if and only if the arrow-maintenance overlay is detected (LID-UPDATE-024).
- `[x]` **LID-UPDATE-026**: The system SHALL re-check arrow-maintenance presence on every invocation, so that installing the overlay after initial setup triggers a CLAUDE.md update on the next `/update-lid` run.

## Verification / Show-What-Changed

- `[x]` **LID-UPDATE-027**: After making any file changes (bootstrap, append directives, mode transition, drift reconciliation), the system SHALL read back the modified files and surface a summary to the user naming the files changed and the sections added or modified.
- `[x]` **LID-UPDATE-028**: The system SHALL NOT complete its invocation without either reporting changes made (per LID-UPDATE-027) or explicitly reporting that no changes were needed (per LID-UPDATE-021).
- `[x]` **LID-UPDATE-029**: When convention drift is detected (per LID-UPDATE-005) and the user declines every proposed update, the system SHALL still inform the user of what was detected before exiting, exercising the same inform-and-skip pathway as LID-UPDATE-021.

## Scope Declaration (Scoped mode)

- `[x]` **LID-UPDATE-030**: When the chosen mode is Scoped, the system SHALL prompt the user for the initial scope patterns (paths to include and, optionally, paths to exclude) before writing the `## LID` block with `- Mode: Scoped`.
- `[x]` **LID-UPDATE-031**: When writing a Scoped-mode configuration, the system SHALL append a `## LID Scope` section to `CLAUDE.md` immediately after the `## LID` block (which carries `- Mode: Scoped`), with bulleted "Paths in scope" and (if any were declared) "Paths explicitly excluded" subsections using gitignore-style glob patterns.
- `[x]` **LID-UPDATE-032**: When the chosen mode is Full, the system SHALL NOT write a `## LID Scope` section to `CLAUDE.md`. A missing section means "entire project in scope."
- `[x]` **LID-UPDATE-033**: During a mode transition from Full to Scoped, the system SHALL prompt the user for scope patterns and write a new `## LID Scope` section following LID-UPDATE-031.
- `[x]` **LID-UPDATE-034**: During a mode transition from Scoped to Full, the system SHALL remove any existing `## LID Scope` section from `CLAUDE.md`.

## Version Walk

- `[x]` **LID-UPDATE-036**: When performing a full bootstrap, the system SHALL write a `- Version:` bullet in the `## LID` block set to the installed `linked-intent-dev` plugin version (the `version` field in `plugins/linked-intent-dev/.claude-plugin/plugin.json`).
- `[x]` **LID-UPDATE-037**: On invocation, the system SHALL compare the project's recorded `- Version:` against the installed `linked-intent-dev` plugin version, and WHEN the project version is lower than the installed version it SHALL perform a version-walk before reconcile-conventions.
- `[x]` **LID-UPDATE-038**: When a project has a `## LID` block with no `- Version:` bullet, the system SHALL treat the project as predating versioned conventions (no `- Version:` bullet) and version-walk it from the start.
- `[x]` **LID-UPDATE-039**: During a version-walk, the system SHALL read the `### Migration (vX → vY)` section of each release between the project version and the installed version, in ascending order, from the CHANGELOG at `plugins/linked-intent-dev/CHANGELOG.md`, and reconcile the project against those sections.
- `[x]` **LID-UPDATE-040**: During a version-walk, the system SHALL batch the mechanical migration steps (e.g., backfilling `parent:`/`prefix:` design-doc frontmatter, bumping `docs/arrows/index.yaml` `schema_version`) and apply them only after a single user confirmation.
- `[x]` **LID-UPDATE-041**: During a version-walk, the system SHALL surface each judgment migration step (e.g., formalizing an ad-hoc sub-HLD) individually as a proposed decision and SHALL NOT auto-apply it.
- `[x]` **LID-UPDATE-042**: When a version-walk fully reconciles the project to the installed conventions, the system SHALL refresh the project's `- Version:` bullet to the installed version (once at the end of a multi-release walk).
- `[x]` **LID-UPDATE-043**: When a version-walk does not fully reconcile the project (e.g., the user defers a judgment step), the system SHALL still apply the confirmed mechanical steps, advance `- Version:` to the installed version — a project that has taken the release's defining structural moves is on the new conventions, and residual cleanup markers do not hold the version back — and report every deferred resolution and persisting marker, leaving those markers in place so that reconcile-conventions (LID-UPDATE-005) and later invocations re-surface them until resolved.
- `[x]` **LID-UPDATE-044**: When the system surfaces a transient migration marker — a node folder holding more than its `<node>-design.md` plus optional `<node>-specs.md` pair (an LLD not yet relocated into its own node folder), or a `prefix:` array on a design doc — whether during a version-walk (LID-UPDATE-039) or during reconcile-conventions (LID-UPDATE-005), it SHALL name the node in the project's own terms and recommend a resolution (promote the extra LLD into its own child folder, collapse a multi-prefix node into `<LEAF>-<TYPE>` facets, or split into sibling leaves), applying the resolution only on user approval. The system SHALL neither silently leave the marker nor silently auto-resolve it.
