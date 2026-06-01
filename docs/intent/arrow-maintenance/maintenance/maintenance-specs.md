# arrow-maintenance command-mode specs

**LLD**: docs/intent/arrow-maintenance/maintenance/maintenance-design.md
**Implementing artifacts**:
- plugins/arrow-maintenance/skills/arrow-maintenance/SKILL.md
- plugins/arrow-maintenance/skills/arrow-maintenance/references/index-schema.md
- plugins/arrow-maintenance/skills/arrow-maintenance/references/arrow-doc-template.md
- plugins/arrow-maintenance/skills/arrow-maintenance/references/audit-checklist.md

**Scope**: These specs cover the `/arrow-maintenance` command-mode behavior. Ambient-mode behavior (the skill's prose guidance when auto-triggered on arrow-adjacent prompts) is verified by dogfooding per the HLD's dual-mode variant, not by these EARS.

Status markers: `[x]` implemented · `[ ]` active gap · `[D]` deferred

---

## Invocation Dispatch

- `[x]` **SCALE-MAINT-001**: When the user invokes `/arrow-maintenance` on a project where `docs/arrows/` is present, the system SHALL run an audit-and-update pass.
- `[x]` **SCALE-MAINT-002**: When the user invokes `/arrow-maintenance` on a project that has LID docs (`docs/high-level-design.md` and at least one LLD) but no `docs/arrows/` directory, the system SHALL create the overlay from the existing LID docs — populating `docs/arrows/index.yaml` and one arrow doc per leaf LLD at its tree-mirrored path — without generating new HLD, LLD, or EARS skeletons.
- `[x]` **SCALE-MAINT-003**: When the user invokes `/arrow-maintenance` on a project with no LID docs, the system SHALL describe what it found (no LID installation), offer to dispatch to `/linked-intent-dev` (greenfield — invoke with a description of what to build) or `/map-codebase` (brownfield) inline, and proceed based on the user's answer rather than requiring the user to re-invoke. The system SHALL NOT silently run the audit-and-update pass on such a project.

## Audit Checks

- `[x]` **SCALE-MAINT-004**: During an audit, the system SHALL check reference coherence — every pointer in each arrow doc (to HLD section, LLD file, EARS spec file, tests, code paths) resolves to an existing file or section; every EARS spec cited in an arrow doc is present in a spec file.
- `[x]` **SCALE-MAINT-005**: During an audit, the system SHALL verify that every behavioral EARS spec has at least one eval assertion citing its ID.
- `[x]` **SCALE-MAINT-006**: During an audit, the system SHALL compare each segment's `audited` date and `audited_sha` in `index.yaml` against current repository state to flag segments whose files have changed since the last audit.
- `[x]` **SCALE-MAINT-007**: When a segment has an `audited_sha` value and git history is available, the system SHALL run the audit in incremental mode — inspecting only segments whose files changed since `audited_sha` — rather than performing a full repository re-audit.
- `[x]` **SCALE-MAINT-008**: During an audit, the system SHALL detect drift signals — specs changed without corresponding test updates, tests passing but missing `@spec` annotations, and code files modified since `audited_sha` that belong to segments not marked as in-flight.
- `[x]` **SCALE-MAINT-009**: During an audit, the system SHALL detect reverse orphans — `@spec` annotations in code or tests that reference spec IDs not present in any spec file.
- `[x]` **SCALE-MAINT-010**: During an audit, the system SHALL detect orphan artifacts — LLD files, spec files, or code files not listed in any arrow doc's References section.

## Fix and Update

- `[x]` **SCALE-MAINT-011**: When running in command mode, the system SHALL repair broken `docs/arrows/` state — malformed `index.yaml`, missing segment docs referenced by the index, stale schema versions — as part of the audit-and-update pass.
- `[x]` **SCALE-MAINT-012**: For findings with unambiguous resolutions — coverage-table regeneration, status transitions where state is clear, `audited` / `audited_sha` / `next` / `drift` field refresh, and `unmapped.docs` cleanup — the system SHALL apply the fix in place.
- `[x]` **SCALE-MAINT-013**: When a reverse orphan is detected, the system SHALL ask the user how to resolve it — create the missing spec, delete the annotation, or treat as alias of an existing spec — and SHALL NOT apply any automatic repair.
- `[x]` **SCALE-MAINT-014**: For findings that require user judgment (ambiguous segment assignment, orphan artifacts, candidate lifecycle events), the system SHALL surface each in a structured report with location and suggested resolution rather than auto-applying.

## `unmapped.docs` Cleanup

- `[x]` **SCALE-MAINT-015**: During an audit, the system SHALL examine each entry in `index.yaml`'s `unmapped.docs` list and assign entries to segments where the assignment is unambiguous (e.g., an unmapped LLD whose filename matches a segment name).
- `[x]` **SCALE-MAINT-016**: For `unmapped.docs` entries where segment assignment is ambiguous, the system SHALL retain them in the list and flag them for user assignment rather than silently picking a segment.

## Lifecycle Events

- `[x]` **SCALE-MAINT-017**: When executing a split, merge, rename, or re-parent lifecycle event, the system SHALL walk all cross-references — `parent`/`children` tree links, `blocks`, `blockedBy`, `merged_into`, `taxonomy` membership, and arrow-doc `## References` sections — and update them atomically within the same session.
- `[x]` **SCALE-MAINT-018**: When an audit detects a candidate split or merge based on drift signals (e.g., one segment's code growing to cover two clearly separate concerns), the system SHALL surface the candidate as a finding for user decision rather than executing the lifecycle event automatically.
- `[x]` **SCALE-MAINT-028**: When executing a rename of a leaf segment, the system SHALL rewrite every path-concatenated EARS ID under that segment's leaf prefix (e.g., `AUTH-UI-001` → `IDENTITY-UI-001`) across the spec files AND every `@spec` annotation in code and tests that cites those IDs, in the same session as the arrow-doc filename, `index.yaml` entry key, and cross-reference updates — landing all together or not at all.
- `[x]` **SCALE-MAINT-029**: When executing a re-parent of a subtree to a new parent node in the design tree, the system SHALL rewrite the path-concatenated EARS IDs of every spec in the moved subtree (e.g., `PEVAL-RUN-014` → `ORCH-RUN-014`) and every `@spec` annotation citing them across code, tests, and docs, AND update the `parent`/`children` links in `index.yaml` for the moved node and both the old and new parents, atomically within the same session.
- `[x]` **SCALE-MAINT-030**: The system SHALL treat path-concatenated EARS IDs as stable under ordinary growth, rewriting them ONLY as part of a deliberate rename or re-parent operation, and SHALL NOT leave a partial application in which IDs are rewritten in spec files but not in their `@spec` annotations (or vice versa).

## Derived Views

- `[x]` **SCALE-MAINT-019**: When regenerating an arrow doc's `## Spec Coverage` table, the system SHALL rescan the relevant source files (spec files, test files, code files) rather than relying on the existing table's contents.
- `[x]` **SCALE-MAINT-020**: When regenerating an arrow doc's `## References` section, the system SHALL rescan source files for `@spec` annotations and actual file paths rather than relying on the prior section's contents.

## Report Output

- `[x]` **SCALE-MAINT-021**: At the end of a command-mode run, the system SHALL produce a structured report listing each finding discovered during the audit.
- `[x]` **SCALE-MAINT-022**: The report SHALL distinguish findings that were automatically resolved from findings that require user decision, and SHALL include each finding's location (segment, file, line where applicable).

## Authority and Timestamps

- `[x]` **SCALE-MAINT-023**: When updating segment state, the system SHALL write to `index.yaml` as the primary source of truth, then regenerate arrow-doc derived views (References, Spec Coverage) from `index.yaml` plus source scans.
- `[x]` **SCALE-MAINT-024**: After completing an audit in command mode, the system SHALL refresh each audited segment's `audited` field to today's date and `audited_sha` to the current git HEAD SHA.

## Coherence-Script Delegation

- `[x]` **SCALE-MAINT-025**: When `CLAUDE.md` contains a `## LID Tooling` section with a `Coherence check: {path}` entry and the declared path resolves to an executable file, the system SHALL invoke that script for audit and treat its output as authoritative for the deterministic checks it performs (reference coherence, orphan and reverse-orphan detection, coverage counts). When the declaration is missing or the declared path does not resolve, the system SHALL perform the equivalent checks in-prompt.
- `[x]` **SCALE-MAINT-026**: The system SHALL NOT require a coherence script. The script is an opt-in performance accelerator, declared per-project via CLAUDE.md.

<!-- Starting-a-Session workflow is ambient-mode prose guidance per the arrow-maintenance LLD; it is verified by dogfooding, not EARS. See arrow-maintenance.md § Starting a Session. -->

## Index.yaml Integrity during Overlay Bootstrap

- `[x]` **SCALE-MAINT-027**: When bootstrapping the overlay on a project with existing LID docs (per SCALE-MAINT-002), the `index.yaml` the system writes SHALL conform to the schema defined in `docs/intent/arrow-maintenance/arrow-maintenance-design.md § index.yaml Schema` — one `arrows:` entry per design-tree node (a leaf entry per leaf LLD, a grouping entry per sub-HLD node), each with `status: MAPPED`, `sampled: {today}`, `audited_sha: null`, and `parent`/`children` links recording the tree's nesting — and the system SHALL create one per-segment arrow doc per leaf LLD at its tree-mirrored path (`docs/arrows/<path>/<leaf>.md`), creating no arrow doc for sub-HLD nodes.
