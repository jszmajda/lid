# arrow-maintenance command-mode specs

**LLD**: docs/llds/arrow-maintenance.md
**Implementing artifacts**:
- plugins/arrow-maintenance/skills/arrow-maintenance/SKILL.md
- plugins/arrow-maintenance/skills/arrow-maintenance/references/index-schema.md
- plugins/arrow-maintenance/skills/arrow-maintenance/references/arrow-doc-template.md
- plugins/arrow-maintenance/skills/arrow-maintenance/references/audit-checklist.md

**Scope**: These specs cover the `/arrow-maintenance` command-mode behavior. Ambient-mode behavior (the skill's prose guidance when auto-triggered on arrow-adjacent prompts) is verified by dogfooding per the HLD's dual-mode variant, not by these EARS.

Status markers: `[x]` implemented · `[ ]` active gap · `[D]` deferred

---

## Invocation Dispatch

- `[x]` **ARROW-MAINT-001**: When the user invokes `/arrow-maintenance` on a project where `docs/arrows/` is present, the system SHALL run an audit-and-update pass.
- `[x]` **ARROW-MAINT-002**: When the user invokes `/arrow-maintenance` on a project that has LID docs (`docs/high-level-design.md` and at least one LLD) but no `docs/arrows/` directory, the system SHALL create the overlay from the existing LID docs — populating `docs/arrows/index.yaml` and one arrow doc per LLD — without generating new HLD, LLD, or EARS skeletons.
- `[x]` **ARROW-MAINT-003**: When the user invokes `/arrow-maintenance` on a project with no LID docs, the system SHALL describe what it found (no LID installation), offer to dispatch to `/lid-setup` (greenfield) or `/map-codebase` (brownfield) inline, and proceed based on the user's answer rather than requiring the user to re-invoke. The system SHALL NOT silently run the audit-and-update pass on such a project.

## Audit Checks

- `[x]` **ARROW-MAINT-004**: During an audit, the system SHALL check reference coherence — every pointer in each arrow doc (to HLD section, LLD file, EARS spec file, tests, code paths) resolves to an existing file or section; every EARS spec cited in an arrow doc is present in a spec file.
- `[x]` **ARROW-MAINT-005**: During an audit, the system SHALL verify that every behavioral EARS spec has at least one eval assertion citing its ID.
- `[x]` **ARROW-MAINT-006**: During an audit, the system SHALL compare each segment's `audited` date and `audited_sha` in `index.yaml` against current repository state to flag segments whose files have changed since the last audit.
- `[x]` **ARROW-MAINT-007**: When a segment has an `audited_sha` value and git history is available, the system SHALL run the audit in incremental mode — inspecting only segments whose files changed since `audited_sha` — rather than performing a full repository re-audit.
- `[x]` **ARROW-MAINT-008**: During an audit, the system SHALL detect drift signals — specs changed without corresponding test updates, tests passing but missing `@spec` annotations, and code files modified since `audited_sha` that belong to segments not marked as in-flight.
- `[x]` **ARROW-MAINT-009**: During an audit, the system SHALL detect reverse orphans — `@spec` annotations in code or tests that reference spec IDs not present in any spec file.
- `[x]` **ARROW-MAINT-010**: During an audit, the system SHALL detect orphan artifacts — LLD files, spec files, or code files not listed in any arrow doc's References section.

## Fix and Update

- `[x]` **ARROW-MAINT-011**: When running in command mode, the system SHALL repair broken `docs/arrows/` state — malformed `index.yaml`, missing segment docs referenced by the index, stale schema versions — as part of the audit-and-update pass.
- `[x]` **ARROW-MAINT-012**: For findings with unambiguous resolutions — coverage-table regeneration, status transitions where state is clear, `audited` / `audited_sha` / `next` / `drift` field refresh, and `unmapped.docs` cleanup — the system SHALL apply the fix in place.
- `[x]` **ARROW-MAINT-013**: When a reverse orphan is detected, the system SHALL ask the user how to resolve it — create the missing spec, delete the annotation, or treat as alias of an existing spec — and SHALL NOT apply any automatic repair.
- `[x]` **ARROW-MAINT-014**: For findings that require user judgment (ambiguous segment assignment, orphan artifacts, candidate lifecycle events), the system SHALL surface each in a structured report with location and suggested resolution rather than auto-applying.

## `unmapped.docs` Cleanup

- `[x]` **ARROW-MAINT-015**: During an audit, the system SHALL examine each entry in `index.yaml`'s `unmapped.docs` list and assign entries to segments where the assignment is unambiguous (e.g., an unmapped LLD whose filename matches a segment name).
- `[x]` **ARROW-MAINT-016**: For `unmapped.docs` entries where segment assignment is ambiguous, the system SHALL retain them in the list and flag them for user assignment rather than silently picking a segment.

## Lifecycle Events

- `[x]` **ARROW-MAINT-017**: When executing a split, merge, or rename lifecycle event, the system SHALL walk all cross-references — `blocks`, `blockedBy`, `merged_into`, `taxonomy` membership, and arrow-doc `## References` sections — and update them atomically within the same session.
- `[x]` **ARROW-MAINT-018**: When an audit detects a candidate split or merge based on drift signals (e.g., one segment's code growing to cover two clearly separate concerns), the system SHALL surface the candidate as a finding for user decision rather than executing the lifecycle event automatically.

## Derived Views

- `[x]` **ARROW-MAINT-019**: When regenerating an arrow doc's `## Spec Coverage` table, the system SHALL rescan the relevant source files (spec files, test files, code files) rather than relying on the existing table's contents.
- `[x]` **ARROW-MAINT-020**: When regenerating an arrow doc's `## References` section, the system SHALL rescan source files for `@spec` annotations and actual file paths rather than relying on the prior section's contents.

## Report Output

- `[x]` **ARROW-MAINT-021**: At the end of a command-mode run, the system SHALL produce a structured report listing each finding discovered during the audit.
- `[x]` **ARROW-MAINT-022**: The report SHALL distinguish findings that were automatically resolved from findings that require user decision, and SHALL include each finding's location (segment, file, line where applicable).

## Authority and Timestamps

- `[x]` **ARROW-MAINT-023**: When updating segment state, the system SHALL write to `index.yaml` as the primary source of truth, then regenerate arrow-doc derived views (References, Spec Coverage) from `index.yaml` plus source scans.
- `[x]` **ARROW-MAINT-024**: After completing an audit in command mode, the system SHALL refresh each audited segment's `audited` field to today's date and `audited_sha` to the current git HEAD SHA.

## Coherence-Script Delegation

- `[x]` **ARROW-MAINT-025**: When `CLAUDE.md` contains a `## LID Tooling` section with a `Coherence check: {path}` entry and the declared path resolves to an executable file, the system SHALL invoke that script for audit and treat its output as authoritative for the deterministic checks it performs (reference coherence, orphan and reverse-orphan detection, coverage counts). When the declaration is missing or the declared path does not resolve, the system SHALL perform the equivalent checks in-prompt.
- `[x]` **ARROW-MAINT-026**: The system SHALL NOT require a coherence script. The script is an opt-in performance accelerator, declared per-project via CLAUDE.md.

<!-- Starting-a-Session workflow is ambient-mode prose guidance per the arrow-maintenance LLD; it is verified by dogfooding, not EARS. See arrow-maintenance.md § Starting a Session. -->

## Index.yaml Integrity during Overlay Bootstrap

- `[x]` **ARROW-MAINT-027**: When bootstrapping the overlay on a project with existing LID docs (per ARROW-MAINT-002), the `index.yaml` the system writes SHALL conform to the schema defined in `docs/llds/arrow-maintenance.md § index.yaml Schema` and include one `arrows:` entry per existing LLD with `status: MAPPED`, `sampled: {today}`, `audited_sha: null`.
