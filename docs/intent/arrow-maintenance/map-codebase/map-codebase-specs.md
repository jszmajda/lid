# map-codebase specs

**LLD**: docs/intent/arrow-maintenance/map-codebase/map-codebase-design.md
**Implementing artifacts**:
- plugins/arrow-maintenance/skills/map-codebase/SKILL.md
- plugins/arrow-maintenance/skills/map-codebase/references/brownfield-bootstrap.md
- plugins/arrow-maintenance/skills/map-codebase/references/subagent-sweep-prompt.md
- plugins/arrow-maintenance/skills/map-codebase/references/reconciliation-template.md
- plugins/arrow-maintenance/skills/map-codebase/references/skeleton-hld-template.md

Status markers: `[x]` implemented · `[ ]` active gap · `[D]` deferred

Phase structure in this file mirrors the `/map-codebase` workflow in the arrow-maintenance LLD: Invocation → Phase 1 Sweep → Phase 2 Seam Identification: Lens Selection → Phase 3 Seam Identification: Slicing Granularity → Phase 4 User Reconciliation → Phase 5 Artifact Generation → Phase 6 Terminal Verification & Flesh-out Prompt. Cross-cutting rules govern all phases.

---

## Invocation

- `[x]` **SCALE-MAP-001**: When `/map-codebase` is invoked, the system SHALL ask the user whether to map the whole project (implies Full LID mode) or specific parts (implies Scoped LID mode, and the user identifies which parts). The answer determines both the sweep scope and the LID mode that is written at terminal verification; the user is not asked a separate "Full or Scoped?" question later.
- `[x]` **SCALE-MAP-002**: When invoked, the system SHALL offer subagent-parallel mapping as an option the user may accept or decline.
- `[x]` **SCALE-MAP-003**: When invoked on a project that already has partial LID docs (some LLDs or EARS specs exist), the system SHALL ask the user whether to treat the existing docs as authoritative (drafting skeletons only for segments not yet covered) or to supersede them.
- `[x]` **SCALE-MAP-004**: When invoked on a project with complete LID docs but no `docs/arrows/`, the system SHALL redirect the user to `/arrow-maintenance` for overlay creation and SHALL NOT proceed with the brownfield sweep.
- `[x]` **SCALE-MAP-024**: At invocation, the system SHALL warn the user that `/map-codebase` is token-intensive by design before beginning the sweep, and SHALL give the user the option to reconsider.

## Cross-Cutting: Five Critical Rules

- `[x]` **SCALE-MAP-028**: Throughout `/map-codebase`, the system SHALL apply five discipline rules: (1) every claim in generated artifacts traces to file/line evidence — speculation is flagged rather than presented as fact; (2) each STOP in the workflow is mandatory; (3) LLDs describe current reality, not aspirational design; (4) thoroughness is prioritized over speed; (5) when the user's framing appears to conflict with the evidence, the system surfaces the tension with evidence rather than silently deferring.

## Phase 1 — Sweep (Reconnaissance)

- `[x]` **SCALE-MAP-005**: During the sweep phase, the system SHALL read across the declared scope and extract observable behaviors, their dependencies, and their entry points, each with file/line references.
- `[x]` **SCALE-MAP-006**: During the sweep phase, the system SHALL NOT attempt to segment the observed behaviors.
- `[x]` **SCALE-MAP-025**: During the sweep phase, the system SHALL read every file within the declared scope, not a sample.
- `[x]` **SCALE-MAP-026**: During the sweep phase, for each file read, the system SHALL record a structured summary covering: purpose, exports, dependencies, data shapes, side effects, role in the larger system, and noteworthy observations.
- `[x]` **SCALE-MAP-007**: When the sweep output is expected to exceed the orchestrator's context window, subagents SHALL write their sweep outputs to per-subagent files in a working directory (e.g., `.lid/map-codebase/sweep-{N}.md`), and the orchestrator SHALL process those files in chunks during the seam-identification phase rather than holding all raw sweep data at once.
- `[x]` **SCALE-MAP-032**: When the declared scope cannot be exhaustively read within the current invocation's capacity (single-agent context window, or the chosen subagent count's combined budget), the system SHALL surface the constraint to the user with concrete sizing evidence, warn that a sampled sweep produces lower-quality mapping, and recommend narrowing scope or enabling subagent parallelism. The user may override with a warning and proceed anyway.
- `[x]` **SCALE-MAP-033**: When proceeding under capacity constraint per user override (SCALE-MAP-032), the system SHALL preserve state across truncation points by writing interim sweep results to per-subagent files (per SCALE-MAP-007) or by incrementally writing arrow-doc partial drafts during reconnaissance, rather than silently discarding information the orchestrator cannot hold at once.

## Phase 2 — Seam Identification: Lens Selection

- `[x]` **SCALE-MAP-008**: During the seam-identification phase, the system SHALL propose 3–5 fundamentally different candidate clusterings, each using a distinct *lens* (e.g., data flow, user-facing capability, domain concept, behavioral boundary, or an explicitly creative/unconventional lens). The system SHALL NOT propose clusterings based on anti-pattern lenses (frontend/backend split, files-that-deploy-together, team ownership, or a generic "utils" dumping ground). For each proposed clustering, the system SHALL name the lens, the clusters it produces, pros/cons, and what kind of reasoning the lens best supports. The user selects a lens before proceeding.

## Phase 3 — Seam Identification: Slicing Granularity

- `[x]` **SCALE-MAP-023**: After the user selects a lens, the system SHALL propose 2–3 slicing variations within that lens — coarse (3–4 large segments), medium (6–8 segments), and fine (10+ finer-grained segments) — and SHALL request a slicing selection before proceeding to artifact generation.

## Phase 4 — User Reconciliation

- `[x]` **SCALE-MAP-009**: When parallel subagents disagree on a segment assignment for the same observation, the orchestrator SHALL tentatively pick an assignment and SHALL flag the conflict prominently in the candidate clustering so it can be resolved during user reconciliation.
- `[x]` **SCALE-MAP-010**: During the user-reconciliation phase, the system SHALL present the candidate clustering to the user in a reviewable form.
- `[x]` **SCALE-MAP-011**: During reconciliation, the user SHALL be able to approve, modify, reject, combine, or split proposed segments before artifact generation begins.
- `[x]` **SCALE-MAP-012**: The system SHALL NOT proceed to artifact generation until the user has approved the final clustering.

## Phase 5 — Artifact Generation

- `[x]` **SCALE-MAP-013**: For each approved leaf segment, the system SHALL generate a per-segment arrow doc at the tree-mirrored path under `docs/arrows/` (the path mirroring the segment's position in the design tree under `docs/intent/`; at depth-2 a flat `docs/arrows/{segment-name}.md`), with References pointing to actual files and an initial `status` of `MAPPED`. Grouping (sub-HLD) nodes are directories, not arrow docs.
- `[x]` **SCALE-MAP-014**: For each approved leaf segment, the system SHALL generate a skeleton LLD at the tree-mirrored path under `docs/intent/` (at depth-2 `docs/intent/{segment-name}.md`) using the standard LLD template defined in `plugins/linked-intent-dev/skills/linked-intent-dev/references/lld-templates.md` — standard section structure (Context and Design Philosophy, major sections per component, Decisions & Alternatives, Open Questions & Future Decisions, References), with empty or `[inferred]`-marked bodies per the brownfield content rules in SCALE-MAP-030. No separate brownfield template.
- `[x]` **SCALE-MAP-015**: For each approved leaf segment, the system SHALL generate an EARS spec file beside the segment's design doc at `docs/intent/<segment-path>/{segment-name}-specs.md` with a reserved spec-ID prefix and empty spec bodies ready for the user to fill in.
- `[x]` **SCALE-MAP-016**: For each approved segment, the system SHALL add an entry to `docs/arrows/index.yaml` including the taxonomy placement and the `parent`/`children` design-tree links chosen during reconciliation — a leaf segment carries `parent` (null at the root level) and a `detail` pointing at its tree-mirrored arrow-doc path; each grouping (sub-HLD) node carries its `children` list and no `detail` — following the schema defined in `docs/intent/arrow-maintenance/arrow-maintenance-design.md`.
- `[x]` **SCALE-MAP-017**: When the project does not have `docs/high-level-design.md`, the system SHALL draft a skeleton HLD with the standard HLD sections and bodies explicitly marked "not yet specified" rather than filled with placeholder content.
- `[x]` **SCALE-MAP-018**: When the project has an existing `docs/high-level-design.md`, the system SHALL NOT modify it.
- `[x]` **SCALE-MAP-019**: When generating an EARS spec file for a new leaf segment, the system SHALL reserve a spec-ID prefix that is the segment's root-to-leaf path (path-concatenated — the leaf prefix is the full path from the root of the design tree; at depth-2 this is just the segment name); when that prefix collides with an existing segment's prefix, the system SHALL ask the user for a namespacing parent to disambiguate rather than picking silently.
- `[x]` **SCALE-MAP-027**: During artifact generation, the system SHALL pause for user review (a STOP) after drafting each per-segment arrow doc, after each segment's skeleton LLD, after each segment's EARS spec file, and after the skeleton HLD (if drafted). The system SHALL NOT batch-produce all segments without these intermediate stops.
- `[x]` **SCALE-MAP-029**: When generating EARS specs for a brownfield segment, the system SHALL assign initial status markers as follows: `[x]` for behaviors observed as working in current code; `[ ]` for behaviors specified but broken or partial in current code; `[D]` for explicit non-wants (intentional non-features).
- `[x]` **SCALE-MAP-030**: When generating a skeleton LLD for a brownfield segment, the system SHALL use the standard LLD template (same section structure as greenfield LLDs) and encode brownfield state in content: inline `[inferred]` markers on Decisions & Alternatives rows whose rationale was inferred from code rather than authored, and Open Questions entries for observed-but-unexplained behavior or technical debt. The system SHALL NOT use a separate brownfield template.

## Phase 6 — Terminal Verification & Flesh-out Prompt

- `[x]` **SCALE-MAP-031**: Before completing the command, the system SHALL ensure `CLAUDE.md` carries the LID directives and the mode marker determined from SCALE-MAP-001's scope question. The system invokes `update-lid` behavior (per `LID-UPDATE-002`, `LID-UPDATE-003`, `LID-UPDATE-009`, and `LID-UPDATE-025` for arrow-nav rows) **with the mode pre-determined** — the caller-provided mode is honored and `update-lid` does not re-prompt for it (per LID-UPDATE-007's caller-provided-mode behavior). The system SHALL NOT exit with `CLAUDE.md` unconfigured. `update-lid` is invoked exactly once per `/map-codebase` run.
- `[x]` **SCALE-MAP-021**: After artifact generation completes, the system SHALL issue a flesh-out prompt directing the user to move into the `linked-intent-dev` workflow segment-by-segment to populate the skeleton LLDs and EARS spec bodies.
- `[x]` **SCALE-MAP-022**: The flesh-out prompt SHALL be the terminal step of the command; the system SHALL NOT complete the command without issuing it.

## Superseded

- `[D]` **SCALE-MAP-020**: *Superseded by SCALE-MAP-031 — `update-lid` is invoked at terminal verification only, not during artifact generation.*
