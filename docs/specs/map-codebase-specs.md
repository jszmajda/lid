# map-codebase specs

**LLD**: docs/llds/arrow-maintenance.md
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

- `[x]` **MAP-CODE-001**: When `/map-codebase` is invoked, the system SHALL ask the user whether to map the whole project (implies Full LID mode) or specific parts (implies Scoped LID mode, and the user identifies which parts). The answer determines both the sweep scope and the LID mode that is written at terminal verification; the user is not asked a separate "Full or Scoped?" question later.
- `[x]` **MAP-CODE-002**: When invoked, the system SHALL offer subagent-parallel mapping as an option the user may accept or decline.
- `[x]` **MAP-CODE-003**: When invoked on a project that already has partial LID docs (some LLDs or EARS specs exist), the system SHALL ask the user whether to treat the existing docs as authoritative (drafting skeletons only for segments not yet covered) or to supersede them.
- `[x]` **MAP-CODE-004**: When invoked on a project with complete LID docs but no `docs/arrows/`, the system SHALL redirect the user to `/arrow-maintenance` for overlay creation and SHALL NOT proceed with the brownfield sweep.
- `[x]` **MAP-CODE-024**: At invocation, the system SHALL warn the user that `/map-codebase` is token-intensive by design before beginning the sweep, and SHALL give the user the option to reconsider.

## Cross-Cutting: Five Critical Rules

- `[x]` **MAP-CODE-028**: Throughout `/map-codebase`, the system SHALL apply five discipline rules: (1) every claim in generated artifacts traces to file/line evidence — speculation is flagged rather than presented as fact; (2) each STOP in the workflow is mandatory; (3) LLDs describe current reality, not aspirational design; (4) thoroughness is prioritized over speed; (5) when the user's framing appears to conflict with the evidence, the system surfaces the tension with evidence rather than silently deferring.

## Phase 1 — Sweep (Reconnaissance)

- `[x]` **MAP-CODE-005**: During the sweep phase, the system SHALL read across the declared scope and extract observable behaviors, their dependencies, and their entry points, each with file/line references.
- `[x]` **MAP-CODE-006**: During the sweep phase, the system SHALL NOT attempt to segment the observed behaviors.
- `[x]` **MAP-CODE-025**: During the sweep phase, the system SHALL read every file within the declared scope, not a sample.
- `[x]` **MAP-CODE-026**: During the sweep phase, for each file read, the system SHALL record a structured summary covering: purpose, exports, dependencies, data shapes, side effects, role in the larger system, and noteworthy observations.
- `[x]` **MAP-CODE-007**: When the sweep output is expected to exceed the orchestrator's context window, subagents SHALL write their sweep outputs to per-subagent files in a working directory (e.g., `.lid/map-codebase/sweep-{N}.md`), and the orchestrator SHALL process those files in chunks during the seam-identification phase rather than holding all raw sweep data at once.
- `[x]` **MAP-CODE-032**: When the declared scope cannot be exhaustively read within the current invocation's capacity (single-agent context window, or the chosen subagent count's combined budget), the system SHALL surface the constraint to the user with concrete sizing evidence, warn that a sampled sweep produces lower-quality mapping, and recommend narrowing scope or enabling subagent parallelism. The user may override with a warning and proceed anyway.
- `[x]` **MAP-CODE-033**: When proceeding under capacity constraint per user override (MAP-CODE-032), the system SHALL preserve state across truncation points by writing interim sweep results to per-subagent files (per MAP-CODE-007) or by incrementally writing arrow-doc partial drafts during reconnaissance, rather than silently discarding information the orchestrator cannot hold at once.

## Phase 2 — Seam Identification: Lens Selection

- `[x]` **MAP-CODE-008**: During the seam-identification phase, the system SHALL propose 3–5 fundamentally different candidate clusterings, each using a distinct *lens* (e.g., data flow, user-facing capability, domain concept, behavioral boundary, or an explicitly creative/unconventional lens). The system SHALL NOT propose clusterings based on anti-pattern lenses (frontend/backend split, files-that-deploy-together, team ownership, or a generic "utils" dumping ground). For each proposed clustering, the system SHALL name the lens, the clusters it produces, pros/cons, and what kind of reasoning the lens best supports. The user selects a lens before proceeding.

## Phase 3 — Seam Identification: Slicing Granularity

- `[x]` **MAP-CODE-023**: After the user selects a lens, the system SHALL propose 2–3 slicing variations within that lens — coarse (3–4 large segments), medium (6–8 segments), and fine (10+ finer-grained segments) — and SHALL request a slicing selection before proceeding to artifact generation.

## Phase 4 — User Reconciliation

- `[x]` **MAP-CODE-009**: When parallel subagents disagree on a segment assignment for the same observation, the orchestrator SHALL tentatively pick an assignment and SHALL flag the conflict prominently in the candidate clustering so it can be resolved during user reconciliation.
- `[x]` **MAP-CODE-010**: During the user-reconciliation phase, the system SHALL present the candidate clustering to the user in a reviewable form.
- `[x]` **MAP-CODE-011**: During reconciliation, the user SHALL be able to approve, modify, reject, combine, or split proposed segments before artifact generation begins.
- `[x]` **MAP-CODE-012**: The system SHALL NOT proceed to artifact generation until the user has approved the final clustering.

## Phase 5 — Artifact Generation

- `[x]` **MAP-CODE-013**: For each approved segment, the system SHALL generate a per-segment arrow doc with References pointing to actual files and an initial `status` of `MAPPED`.
- `[x]` **MAP-CODE-014**: For each approved segment, the system SHALL generate a skeleton LLD at `docs/llds/{segment-name}.md` using the standard LLD template defined in `plugins/linked-intent-dev/skills/linked-intent-dev/references/lld-templates.md` — standard section structure (Context and Design Philosophy, major sections per component, Decisions & Alternatives, Open Questions & Future Decisions, References), with empty or `[inferred]`-marked bodies per the brownfield content rules in MAP-CODE-030. No separate brownfield template.
- `[x]` **MAP-CODE-015**: For each approved segment, the system SHALL generate an EARS spec file at `docs/specs/{segment-name}-specs.md` with a reserved spec-ID prefix and empty spec bodies ready for the user to fill in.
- `[x]` **MAP-CODE-016**: For each approved segment, the system SHALL add an entry to `docs/arrows/index.yaml` including the taxonomy placement chosen during reconciliation, following the schema defined in `docs/llds/arrow-maintenance.md`.
- `[x]` **MAP-CODE-017**: When the project does not have `docs/high-level-design.md`, the system SHALL draft a skeleton HLD with the standard HLD sections and bodies explicitly marked "not yet specified" rather than filled with placeholder content.
- `[x]` **MAP-CODE-018**: When the project has an existing `docs/high-level-design.md`, the system SHALL NOT modify it.
- `[x]` **MAP-CODE-019**: When generating an EARS spec file for a new segment, the system SHALL reserve a spec-ID prefix derived from the segment name; when that prefix collides with an existing segment's prefix, the system SHALL ask the user for a namespacing segment to disambiguate rather than picking silently.
- `[x]` **MAP-CODE-027**: During artifact generation, the system SHALL pause for user review (a STOP) after drafting each per-segment arrow doc, after each segment's skeleton LLD, after each segment's EARS spec file, and after the skeleton HLD (if drafted). The system SHALL NOT batch-produce all segments without these intermediate stops.
- `[x]` **MAP-CODE-029**: When generating EARS specs for a brownfield segment, the system SHALL assign initial status markers as follows: `[x]` for behaviors observed as working in current code; `[ ]` for behaviors specified but broken or partial in current code; `[D]` for explicit non-wants (intentional non-features).
- `[x]` **MAP-CODE-030**: When generating a skeleton LLD for a brownfield segment, the system SHALL use the standard LLD template (same section structure as greenfield LLDs) and encode brownfield state in content: inline `[inferred]` markers on Decisions & Alternatives rows whose rationale was inferred from code rather than authored, and Open Questions entries for observed-but-unexplained behavior or technical debt. The system SHALL NOT use a separate brownfield template.

## Phase 6 — Terminal Verification & Flesh-out Prompt

- `[x]` **MAP-CODE-031**: Before completing the command, the system SHALL ensure `CLAUDE.md` carries the LID directives and the mode marker determined from MAP-CODE-001's scope question. The system invokes `lid-setup` behavior (per `LID-SETUP-002`, `LID-SETUP-003`, `LID-SETUP-009`, and `LID-SETUP-025` for arrow-nav rows) **with the mode pre-determined** — the caller-provided mode is honored and `lid-setup` does not re-prompt for it (per LID-SETUP-007's caller-provided-mode behavior). The system SHALL NOT exit with `CLAUDE.md` unconfigured. `lid-setup` is invoked exactly once per `/map-codebase` run.
- `[x]` **MAP-CODE-021**: After artifact generation completes, the system SHALL issue a flesh-out prompt directing the user to move into the `linked-intent-dev` workflow segment-by-segment to populate the skeleton LLDs and EARS spec bodies.
- `[x]` **MAP-CODE-022**: The flesh-out prompt SHALL be the terminal step of the command; the system SHALL NOT complete the command without issuing it.

## Superseded

- `[D]` **MAP-CODE-020**: *Superseded by MAP-CODE-031 — lid-setup is invoked at terminal verification only, not during artifact generation.*
