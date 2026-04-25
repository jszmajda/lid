# LLD: arrow-maintenance Plugin

## Context and Design Philosophy

The `arrow-maintenance` plugin is the optional navigation and audit overlay for LID. It is installed alongside `linked-intent-dev` by default but is load-bearing only when the project has enough intent components that orientation takes more than a glance at the file list, when the project is brownfield and needs initial mapping, or when the user wants a navigation aid for its own sake. It is never wrong to have the overlay; the question is only whether the overhead of maintaining it pays for itself on a given project.

The overlay is anchored at the project root (`docs/arrows/`), same scope as the `## LID Mode:` marker in `CLAUDE.md`. There is one overlay per project, not one per scope.

Arrow-maintenance addresses three problems that emerge as projects grow:

1. **Navigation.** An agent needs to find the right arrow segment quickly without loading the whole project. A dedicated index makes this cheap.
2. **Audit.** Cascade runs at change time inside `linked-intent-dev`. Arrow-maintenance provides periodic re-audit to catch drift that slipped through cascade — partial cascades, inconsistent arrows left by aborted sessions, silent spec/code divergence accumulated over time.
3. **Brownfield bootstrap.** Legacy code can be mapped into the tail of the arrow so a project can adopt LID without rewriting from scratch.

This LLD describes what the overlay produces and how the skill guides agents through these three use cases. The `SKILL.md` files and reference templates under `plugins/arrow-maintenance/` are the compiled outcome. Terms like *arrow*, *segment*, *drift*, *coherence*, and *cascade* are defined in the HLD's Glossary section.

**A note on actors.** As in `linked-intent-dev`, "the skill" refers to the prose guidance and the agent is the actor. All surfacing, audit-running, and map-generating happens through the agent acting on skill guidance.

## Plugin Structure

The plugin lives at `plugins/arrow-maintenance/`:

- `.claude-plugin/plugin.json` — manifest.
- `skills/arrow-maintenance/` — the navigation and audit skill. Invocable ambiently (auto-triggered on arrow-adjacent prompts when `docs/arrows/` is present) and as a slash command (`/arrow-maintenance`). The ambient mode is pure prose guidance; the command mode is behavioral and produces verifiable state changes (audit report, updated arrow docs, refreshed `index.yaml`).
  - `SKILL.md`
  - `references/` — `index.yaml` schema, arrow-doc template, audit-checklist reference, a README template for projects to copy into their `docs/arrows/`.
- `skills/map-codebase/` — the behavioral brownfield-mapping skill.
  - `SKILL.md`
  - `references/` — prompts for subagent-driven mapping runs, reconciliation templates, skeleton HLD/LLD/EARS starters.
- `commands/` — command stubs routing `/arrow-maintenance` and `/map-codebase` to their respective skills.

## The `arrow-maintenance` Skill

The skill operates in two modes.

### Intent (ambient mode)

When a project uses the `docs/arrows/` overlay, shape the agent's work on arrow-adjacent tasks so that:

- navigation starts from `index.yaml` rather than from file listings;
- cascade and audit findings update `index.yaml` and per-segment arrow docs in place;
- drift is surfaced explicitly, not silently corrected;
- arrow lifecycle events (split, merge, rename, status transitions) are recorded, not erased.

In ambient mode the skill is pure prose guidance — it biases how the agent uses the overlay without executing a procedure. File modifications are not forbidden in ambient mode; they happen opportunistically when the surrounding conversation authorizes them (for example, when the user has asked for a change and `linked-intent-dev` is already editing a segment, the ambient arrow-maintenance guidance tells the agent to update the arrow doc in the same cascade). What ambient mode does *not* do is initiate a systematic audit-and-update pass on its own — that is command-mode behavior. Projects without `docs/arrows/` see no ambient behavior.

### Intent (command mode)

When invoked explicitly as `/arrow-maintenance`, the skill runs an audit-and-update pass. The implied user intent is "audit my arrows and update what you find." The skill then:

- fixes any broken state in `docs/arrows/` (malformed `index.yaml`, missing per-segment docs referenced by the index, stale schema versions) — these are the skill's domain, so they are always repaired when the command runs;
- runs the audit checks described below;
- updates each affected arrow doc's `## Spec Coverage` table and `index.yaml` `status` / `next` / `drift` / `audited` / `audited_sha` fields in place;
- cleans up `unmapped.docs` by assigning entries to segments where it can, and flagging the rest for user assignment;
- produces a structured report of findings that could not be resolved automatically.

When invoked on a project that has LID docs but no `docs/arrows/`, the command creates the overlay from existing LLDs and specs — one arrow doc per LLD, a populated `index.yaml`, no upstream skeleton generation (LLDs already exist). When invoked on a project with no LID docs at all, the skill describes what it found and offers to dispatch inline to `/lid-setup` (greenfield) or `/map-codebase` (brownfield) rather than asking the user to re-invoke. The user's answer proceeds directly into the chosen command without requiring a second manual invocation.

Command-mode behavior produces verifiable project-state changes and is therefore behavioral — EARS specs cover its assertions and eval suite runs gate changes to its prompt.

### Triggering (ambient mode)

Ambient triggering is on prompts that touch arrow-adjacent work — navigating the codebase, auditing specs, investigating drift — in projects where `docs/arrows/` exists. Presence of the directory is the sole detection signal. If the directory is absent, the ambient skill does not trigger; the core `linked-intent-dev` skill alone is sufficient for projects that do not need the overlay.

### Navigation via `index.yaml`

When the agent needs to locate an arrow segment, the skill instructs it to load `docs/arrows/index.yaml` first — always a small file relative to the full project — and query for the relevant segment by name, domain cluster, or status. The per-segment arrow doc (e.g., `docs/arrows/auth.md`) is loaded only after the segment is identified. The LLD and EARS specs are loaded after that, as needed. This progressive disclosure keeps context tight: the agent pulls detail only down the path it actually needs.

### Starting a Session

At the start of any session where the agent will touch arrow-adjacent work in a project that has `docs/arrows/`, the skill guides the agent through a consistent startup sequence:

1. Load `docs/arrows/index.yaml`.
2. Query for segments whose `blockedBy` list is empty and whose `status` is not `OK` or `OBSOLETE` — these are candidates for active work.
3. When the user names a segment or the conversation implies one, load only that segment's arrow doc (`docs/arrows/{segment-name}.md`).
4. Follow the arrow doc's `## References` section to the LLD, spec file, tests, or code as needed for the current task.
5. If no specific segment is implied and the user is orienting broadly, summarize the `next` and `drift` fields from the index for in-flight segments rather than loading every arrow doc.

This sequence exists because loading the full project is often infeasible at this scale; the index-first, detail-on-demand pattern is the ambient-mode user experience that makes arrow-maintenance worthwhile.

### Arrow Doc Format

Each arrow segment has a markdown file in `docs/arrows/` named after the segment. The file is an *orientation page*, not a design document. Standard structure:

- `# Arrow: {segment-name}` — heading and a one-line description of the segment's concern.
- `## Status` — status value + a one-sentence rationale.
- `## References` — pointers to HLD section, LLD file(s), EARS spec file(s), test file paths, code paths. Pointers only; no design content.
- `## Spec Coverage` — table of spec-ID groups with implementation status (`✓ implemented`, `? partial`, `✗ missing`) and short notes.
- Optional sections (`## Migration Notes`, `## Remaining Work`) where segment-specific context doesn't fit elsewhere.

Design detail lives in the LLD. Narrative lives in the HLD. The arrow doc is the *index view* for one segment — compact enough that an agent loading it pays a small token cost to orient. Duplicating LLD or spec content into the arrow doc creates a third source of truth that invites drift; the skill discourages it.

### Audit Guidance

Audit runs in both modes — ambiently when the skill notices drift during other work, and explicitly when invoked as `/arrow-maintenance`. The core audit checks:

1. **Reference coherence** — do the pointers in the arrow doc still point to real files? Are the EARS specs cited still present? Are the LLD section headings named as referenced?
2. **Coverage** — for each behavioral spec, does an eval assertion cite its ID?
3. **Staleness** — how long since the segment was last audited? Measured by two fields in `index.yaml`: `audited` (calendar date) and `audited_sha` (git commit SHA at time of audit). The SHA enables incremental audit — on subsequent runs the skill checks only segments whose files changed since `audited_sha`, rather than re-auditing the whole project.
4. **Drift signals** — code files modified since `audited_sha`; specs changed without corresponding test updates; tests passing but missing `@spec` annotations; `@spec` annotations pointing to IDs not present in any spec file (*reverse orphans* — the spec ID is referenced but doesn't exist). For reverse orphans the skill asks the user how to resolve: create the missing spec, delete the annotation, or treat as an alias of an existing spec.
5. **Orphan artifacts** — LLDs, specs, or code files not listed in any arrow doc's References section.

In ambient mode, the skill surfaces findings as a structured report. It does not *initiate* file writes, but it may *participate* in writes the surrounding conversation is already doing (for instance, updating an arrow doc's coverage table alongside a linked-intent-dev edit on the same segment). Systematic corrective writes — touching files the user hasn't asked about — are reserved for command mode. In command mode, the skill updates arrow docs and `index.yaml` in place for findings that have unambiguous resolutions (coverage table updates, status transitions, `audited` / `audited_sha` refresh, `unmapped.docs` cleanup), and surfaces the rest for user decision.

The skill does not prescribe an audit cadence. "Run audit every N commits" or "run weekly" is surface growth — users decide when the staleness signal is worth acting on. The skill emits the signal when consulted; the user chooses the rhythm.

### Reference tooling

The audit checks above are expensive when performed by the agent via `Read`/`Grep` — enumerating every `@spec` annotation, comparing to every spec file, walking every `index.yaml` entry, checking every referenced file path. For projects large enough to need arrow-maintenance, the cost becomes real.

The skill therefore delegates deterministic checks to a project-local coherence script when one is **declared** in the project's `CLAUDE.md` under a `## LID Tooling` section. Declaration format:

```markdown
## LID Tooling

- **Coherence check**: `bin/coherence-check.mjs`
```

Language and path are the user's choice; the declaration is authoritative. The arrow-maintenance plugin ships a reference implementation in Node at `plugins/arrow-maintenance/skills/arrow-maintenance/references/coherence-check.mjs`; users may copy it, adapt it, or write their own in Python, bash, or any other language.

When the declaration is missing or the declared path does not resolve, the skill falls back to in-prompt audit. A coherence script is not required and not installed by default. It is an opt-in performance accelerator. The audit's *semantics* (what checks are run, what findings mean) live in the skill; the script is one implementation of those checks.

### Lifecycle Events

Segments evolve. The skill supports four lifecycle events without erasing history:

- **Split.** One arrow segment is discovered to contain two concerns. Create the new segment's arrow doc, move the relevant spec references and code pointers, update both docs to reference each other, record the split in `index.yaml`. If a split is detected while `linked-intent-dev` is mid-change on the affected segment, the skill asks whether to split now or defer; deferring is preferred — split at a clean break, not mid-edit.
- **Merge.** Two segments are the same thing. Pick the primary, move references from the secondary into the primary, mark the secondary as `MERGED` with a `merged_into:` field pointing at the primary. Tombstone or delete the secondary's arrow doc.
- **Rename.** A segment's name changes (e.g., `auth` → `identity`). The arrow-doc filename changes; the `index.yaml` entry key changes; every cross-reference elsewhere — `blocks`, `blockedBy`, `merged_into`, the References sections of other segments' arrow docs, `taxonomy` membership — is updated in the same pass. Rename is not a rename-and-hope operation; the skill walks all references and updates them atomically within the session.
- **Status transition.** The natural progression is `UNMAPPED → MAPPED → AUDITED → OK`, with optional detours (`PARTIAL`, `BROKEN`, `STALE`, `OBSOLETE`). Timestamps (`sampled`, `audited`) and the `audited_sha` record when each transition happened so staleness can be measured.

### Coordination with `linked-intent-dev`

Both skills may be consulted in the same session. The coordination rule:

- `linked-intent-dev` handles per-change workflow (HLD → LLD → EARS → Tests → Code). When it changes a segment, it also updates that segment's arrow doc and the relevant `index.yaml` entry, because it already has the segment's context loaded.
- `arrow-maintenance` handles systematic audit and drift detection across segments. It does not perform change workflows; it observes, reports, and nudges the user toward correction.

Linked-intent-dev is authoritative for *changes*; arrow-maintenance is authoritative for *state of coverage*. They share artifacts but own different questions.

## The `/map-codebase` Skill (behavioral)

### Intent

Map an existing codebase into the tail of the LID arrow so the project can adopt LID without rewriting from scratch. The command produces three outputs: the `docs/arrows/` overlay (index + per-segment docs), skeleton upstream docs (HLD, LLDs, EARS spec files), and a prompt to the user to flesh out the skeletons through `linked-intent-dev`.

### Invocation

`/map-codebase` asks the user at invocation for the starting scope — a directory, a file list, or the whole project. It also offers the option to enable subagent-parallel mapping (one subagent per initial scope area, outputs merged). Parallelism is recommended for large codebases where a single-agent sweep would be slow or hit context limits; single-agent mode is sufficient for smaller ones.

**Token-intensity warning.** `/map-codebase` is token-intensive by design — it reads every file in the declared scope, proposes multiple clustering lenses, drafts skeleton docs for every segment, and walks the user through multi-step reconciliation. The skill warns the user upfront at invocation: this is not a lightweight operation, and the quality of the mapping depends on the thoroughness of the work. Users who expect a one-shot quick-mapping are steered toward that expectation being wrong; they can proceed or reconsider.

**State dispatch.** If the project already has partial LID docs (an HLD or some LLDs exist), the command asks the user whether to treat the existing docs as authoritative (draft skeletons only for segments not yet covered) or to supersede them. There is no silent overwrite. If the project already has full LID docs and no `docs/arrows/`, the command redirects the user to `/arrow-maintenance`, which generates the overlay from existing docs without the brownfield sweep.

### Five Critical Rules

Five rules govern the entire workflow, applied consistently by the agent regardless of phase:

1. **Read actual code, don't guess.** Every claim in the generated artifacts traces to file/line evidence. Speculation about behavior is flagged explicitly rather than presented as fact.
2. **Each STOP is mandatory.** The workflow has multiple stop points (after sweep, after lens selection, after slicing, after user reconciliation, after each per-segment LLD draft, after HLD synthesis, after EARS and arrow-doc generation). None of them are optional. Rushing past a stop is how brownfield mapping produces bad LLDs that poison subsequent work.
3. **LLDs describe current reality, not aspirational design.** The output is what the code *is*, not what a greenfield version *would be*. Inferred design decisions carry `[inferred]` markers; known technical debt and behavioral quirks are recorded in Open Questions — the user decides later whether to endorse, fix, or change.
4. **Be thorough over fast.** Token budget is a real constraint but not a dominant one; skimming produces mappings that miss behaviors and lock in the wrong segmentation.
5. **Be humble but guide.** The agent is not the expert on the user's system; the user is. But the agent also doesn't silently defer to whatever the user says — when the user's framing seems wrong given the evidence, the agent surfaces the tension with evidence rather than just going along. Humble but not passive.

### Comprehensive Mapping Workflow

Unlike the per-change flow in `linked-intent-dev`, `/map-codebase` runs a *comprehensive* sweep before any segmentation decisions are made. This is deliberate. Segment-by-segment mapping produces over- or under-sized segments because the agent cannot see the full shape of the codebase when it starts; early segments either absorb too much (because nothing downstream exists yet) or too little (because dependencies are not yet visible). A comprehensive first pass exposes natural seams; segmentation decisions come after.

Phases:

1. **Sweep (reconnaissance).** The agent (or subagents in parallel) reads *every file in the declared scope*, not a sample. Sampling risks missing behaviors that only surface in edge-case files. For each file, the agent records:
   - **Purpose** — what this file appears to do.
   - **Exports** — what the file exposes to other parts of the system (functions, classes, types, endpoints).
   - **Dependencies** — what it imports or calls.
   - **Data shapes** — structures it produces or consumes.
   - **Side effects** — file system, network, database, logs.
   - **Role** — how this file fits into the larger system (UI component, API handler, background job, pure utility, etc.).
   - **Observations** — anything unusual, deprecated-looking, or flagged by comments.

   Output: a flat list of observed behaviors with file/line references. No segmentation attempted here. When sweep output exceeds the orchestrator's context window, each subagent writes its sweep to a per-subagent file (e.g., `.lid/map-codebase/sweep-{N}.md`); the orchestrator processes them in chunks during the next phase. The file format is left to implementation; the file-based handoff is the mechanism.

2. **Seam identification — lens selection.** The agent proposes **3–5 fundamentally different clusterings** of the swept behaviors, each using a *different lens*. Good lenses include:
   - **Data flow** — what data originates where, how it moves between modules.
   - **User-facing capability** — clusters organized around things a user can do (sign in, check out, export data).
   - **Domain concept** — clusters matching domain language (order, inventory, keeper, entry).
   - **Behavioral boundary** — where the system changes state in coordinated ways (authentication flow, payment pipeline).
   - **Creative / unconventional** — a lens not already tried, presented as a counterweight.

   Anti-pattern lenses the agent explicitly avoids proposing:
   - **Frontend vs. backend split** — deployment-location, not intent.
   - **Files that deploy together** — infrastructure grouping, not intent.
   - **Team ownership** — org chart, not intent.
   - **Utils / shared / common directory** — tooling leftover, not a real concept.

   The agent presents each lens as: name, lens description, the clusters it produces, pros/cons, and best-for (what kind of reasoning this lens supports well). **STOP for user lens selection.** Multiple lenses are the primary edge-detection mechanism — the user's choice of lens reveals latent intent in a way that a single proposed clustering cannot.

3. **Seam identification — slicing granularity.** After the user picks a lens, the agent proposes **2–3 slicing variations** within that lens: coarse (3–4 large segments), medium (6–8 segments), fine (10+ finer-grained segments). Coarse segments absorb more code per LLD; fine segments give more precise tracking at the cost of more docs. The user picks the granularity best suited to the project's maturity and their appetite for maintenance. **STOP for user slicing selection.**

4. **User reconciliation.** With a chosen lens + granularity, the agent presents the final candidate clustering. The user approves, modifies, rejects, combines, or splits proposed segments. Where subagents disagreed on a segment assignment earlier, the conflicts are flagged prominently here. **STOP for user reconciliation.** This is the edge-detection moment where the agent's interpretation meets the user's latent intent.

   **Component quality guidance.** When reviewing proposed segments, the agent applies a working definition of "intent component": a thing achieving an independent purpose in the system. Good components are self-contained in intent (auth, payment, notification, recording pipeline). False components to challenge include clusters organized around team boundaries, deployment units, file locations, or generic "utils." When a proposed segment matches an anti-pattern, the agent flags it for the user rather than accepting silently.

5. **Artifact generation.** For each approved segment, the agent drafts the following, **with a STOP after each sub-step**:

   - **Per-segment arrow doc** (`docs/arrows/{segment-name}.md`) with references to actual files and initial status `MAPPED`. **STOP after each segment's arrow doc.**
   - **Skeleton LLD** (`docs/llds/{segment-name}.md`). Uses the standard LLD template — *not* a separate brownfield template. Content reflects brownfield state: the Decisions & Alternatives table is populated with observed decisions carrying `[inferred]` markers in the Rationale column; Open Questions holds observed-but-unexplained behaviors and technical debt; major sections describe current state. **STOP after each segment's LLD.**
   - **EARS spec file** (`docs/specs/{segment-name}-specs.md`) with a reserved spec-ID prefix. Initial status semantics for brownfield mapping:
     - `[x]` — behavior is observed in current code (the spec describes what exists and works).
     - `[ ]` — behavior is specified but broken or partial in current code.
     - `[D]` — explicit non-wants (intentional non-features); rare in brownfield.
     **STOP after each segment's specs.**
   - **Entry in `index.yaml`** including the taxonomy placement chosen during reconciliation.
   - **Skeleton HLD** (`docs/high-level-design.md`) *if one does not already exist*. Uses the standard HLD template with bodies marked "not yet specified." **STOP after HLD draft.** If an HLD already exists, skip this step.

6. **Terminal verification and flesh-out prompt.** After artifact generation completes, the skill runs `/lid-setup` (or its equivalent bootstrap logic) to ensure CLAUDE.md is configured with LID directives and the chosen mode marker. Then it issues a **flesh-out prompt** directing the user to move into the `linked-intent-dev` workflow segment-by-segment to populate the skeleton LLDs and EARS specs. Without this prompt the user may leave the reconstruction incomplete, and partial arrows propagate incoherence into future sessions. The prompt is not optional from the skill's side; it is the terminal step. The exact ordering of the lid-setup call and the flesh-out prompt is an implementation choice — both must happen before the command exits.

### Output Summary

After `/map-codebase` completes (whether the user has started fleshing out skeletons or not), the project has:

- a navigable `docs/arrows/` overlay (index + segment docs);
- a complete-but-empty `docs/llds/` tree (one file per segment);
- a reserved set of EARS spec files with IDs claimed by segment;
- a skeleton HLD (or the existing one, untouched);
- `CLAUDE.md` updated with `## LID Mode: Full` (or the user-chosen mode) and the standard LID directives;
- the prompt to resume via `linked-intent-dev` on a segment-by-segment basis.

This is enough for `linked-intent-dev` to start operating immediately on subsequent changes. The agent does not need `arrow-maintenance`-specific knowledge to fill in the skeletons — they live in standard LID locations, so the core workflow picks them up naturally.

## `docs/arrows/` Directory Contents

An arrow-maintained project's `docs/arrows/` contains:

- `README.md` — instructions for working with the overlay: loading order, `yq` query patterns, workflow for mapping/auditing/fixing/splitting/merging, status enum. Cloned from the skill's `references/` on bootstrap; the project may edit it.
- `index.yaml` — the manifest.
- `{segment-name}.md` — one file per arrow segment.
- `experiments/` — *reserved namespace* for experiment-produced artifacts (see §"Experiment-produced artifacts (reserved namespace)" below). Not owned or audited by this skill.

### `index.yaml` Schema

```yaml
schema_version: 1
last_updated: YYYY-MM-DD

taxonomy:
  {cluster-name}:
    - segment-name
    - segment-name
  {another-cluster}: standalone  # single-segment cluster

arrows:
  {segment-name}:
    status: UNMAPPED | MAPPED | AUDITED | OK | PARTIAL | BROKEN | STALE | OBSOLETE | MERGED
    sampled: YYYY-MM-DD           # when first mapped
    audited: YYYY-MM-DD | null    # when last audited (calendar date)
    audited_sha: <git-sha> | null # git head SHA at time of last audit; enables incremental audit
    blocks: [other-segment, ...]  # segments blocked by this one
    blockedBy: [other-segment, ...] # segments this one depends on
    detail: {segment-name}.md
    next: "one-line next action or null"
    drift: "description of current drift or null"
    merged_into: {primary-segment}  # only if status is MERGED

unmapped:
  docs:
    llds: [file-name.md, ...]
    specs: [file-name.md, ...]
```

The schema is intentionally flat — agents query it with `yq` or simple reads. Extensions (new status values, additional metadata per arrow) are permitted but should be added to this LLD first so the schema stays coherent across projects.

### Experiment-produced artifacts (reserved namespace)

The `docs/arrows/experiments/` subtree is reserved for artifacts produced by `lid-experimental` plugin skills that want to attach per-segment or per-EARS experiment state to the arrow overlay. The subtree is **not owned by this skill** — each experiment owns its own namespace inside it and is responsible for creating, updating, and removing its own artifacts.

Convention:

```
docs/arrows/experiments/<experiment-name>/<segment-name>/<artifact>.md
```

- `<experiment-name>` — the `lid-experimental` skill's directory name (e.g., `bidirectional-differential`). Each experiment gets its own peer directory.
- `<segment-name>` — the arrow segment the artifact applies to, mirroring the segment names used at `docs/arrows/{segment-name}.md`.
- `<artifact>.md` — experiment-specific shape. Typically one file per EARS, but experiments may choose their own leaf structure.

**Audit behavior**: the `arrow-maintenance` skill (both ambient and command modes) **ignores** the `experiments/` subtree. It does not audit, clean up, or regenerate files under it. Reference-rot and spec-to-code drift checks scan arrow docs and code; they do not scan `experiments/`.

**Lifecycle**: when an experiment is retired, its entire `docs/arrows/experiments/<experiment-name>/` subtree is removed in the same commit that removes the experiment from `lid-experimental`. When an experiment is promoted into a core plugin, the subtree either migrates into core ownership (this LLD's schema gets extended to track the artifact type formally) or is removed in favor of a first-class schema entry. That decision is made at promotion time, not in advance.

**`index.yaml` coordination**: `arrows.<segment>.experiments` is a reserved key. If a future experiment needs per-segment metadata tracked in `index.yaml` (e.g., "last audit date" for an experiment's artifacts), that experiment proposes the sub-schema at promotion review and this LLD extends `index.yaml` then. Until then, experiments keep their state in the `experiments/` subtree only.

Active experiments at this LLD's current version:

- `bidirectional-differential` — see `docs/llds/lid-experimental/bidirectional-differential.md`. Uses `docs/arrows/experiments/bidirectional-differential/<segment-name>/<EARS-ID>.md`.

## Audit Mechanics

The skill's audit guidance surfaces five classes of drift that the overlay is uniquely positioned to catch:

1. **Reference rot** — arrow-doc pointers to files or sections that no longer exist.
2. **Spec-to-code drift** — specs whose cited `@spec` annotations have disappeared from code or tests.
3. **Uncovered behavioral specs** — behavioral specs with no eval assertion citing them.
4. **Stale segments** — segments whose `audited` date (and `audited_sha`) lag significantly behind current work.
5. **Orphan artifacts** — LLDs, specs, or code files not listed in any arrow doc's References section.

Surfacing is structured: the skill produces a report naming each finding and its location. In ambient mode it does not modify files; in command mode (`/arrow-maintenance`) it applies the unambiguous updates (coverage-table regeneration, `unmapped.docs` cleanup, `audited`/`audited_sha` refresh, status transitions where state is clear) and surfaces the rest for user decision.

## Authoritative Sources

When information is duplicated across artifacts, the authority rule is:

- **Segment status, `sampled`/`audited`/`audited_sha` timestamps, `next`, `drift`, `blocks`/`blockedBy` graph, `merged_into`** — `index.yaml` is authoritative.
- **Per-segment arrow doc's `## References` section, `## Spec Coverage` table** — derived views. Regenerated from source-of-truth scans (grep for `@spec`, file existence checks, eval-citation checks) during audit. Never hand-edited to contradict the source scans.
- **Spec-file header format** (the `LLD:` pointer and `Implementing artifacts:` list used in the LID-on-LID inversion) — defined authoritatively in `docs/llds/linked-intent-dev.md`. This skill's reference-coherence audit uses that schema; changes to the schema happen there and propagate here.
- **`@spec` annotation placement rule** (entry point of the behavior's implementation graph) — also defined authoritatively in `docs/llds/linked-intent-dev.md`.
- **`index.yaml` schema itself** — defined authoritatively in this LLD. Cross-plugin updates defer to this document.

## Relationship to `linked-intent-dev`

| Concern | Owner |
|---|---|
| Per-change HLD/LLD/EARS/test/code work | linked-intent-dev |
| Cascade at change time | linked-intent-dev |
| Arrow doc updates during a change (add coverage rows, refresh status) | linked-intent-dev (segment is already in context) |
| `index.yaml` status updates during a change | linked-intent-dev |
| `unmapped.docs` cleanup | arrow-maintenance during audit; linked-intent-dev when it notices an unmapped doc it can assign in passing |
| Systematic audit across segments | arrow-maintenance |
| Drift detection between sessions | arrow-maintenance |
| Brownfield mapping | arrow-maintenance (`/map-codebase`) |
| Overlay bootstrap on existing LID projects | arrow-maintenance (`/arrow-maintenance` command mode) |
| Lifecycle events (split, merge, rename, status transitions) | Either skill, depending on context; arrow-maintenance has richer guidance for multi-segment events and for renames that require walking cross-references |

The two skills share artifacts but own different questions. Coordination is implicit: both are consulted when their triggers match, and neither overrides the other.

## Decisions & Alternatives

| Decision | Chosen | Alternatives Considered | Rationale |
|---|---|---|---|
| Audit as prose guidance vs. a command | Prose guidance only | `/audit-arrow` command; scheduled audit hook | Minimum system. If guidance is insufficient in practice we upgrade; starting with a command commits to surface growth that may not be needed. |
| Mapping: comprehensive vs. segment-by-segment | Comprehensive sweep first | Segment-by-segment walk; single-pass top-down | Segment-by-segment over- or under-sizes early segments because the full shape is invisible at the start. A comprehensive sweep exposes seams; segmentation decisions follow with the user in the loop. |
| Mapping output | Arrow docs + skeleton upstream + flesh-out prompt | Arrow docs only; full fabricated upstream docs | Arrow docs alone leave reconstruction incomplete; users may never return to fill in upstream. Full fabrication risks inventing intent that was never there. Skeleton + prompt keeps the agent honest (empty sections are visible gaps) while giving `linked-intent-dev` enough scaffolding to start operating. |
| Subagent parallelism for mapping | Optional, asked at invocation | Always serial; always parallel | Small codebases do not need parallelism; large ones materially benefit. Asking respects the user's judgment about their project's size. |
| Arrow doc content | Pointers + coverage table, no design | Include design excerpts; include full spec text | Design lives in the LLD; specs live in spec files. Duplicating either into the arrow doc creates a third source of truth and invites drift. Pointers-only keeps the arrow doc compact and stable. |
| Status enum | Full Threadkeeper set | Simpler binary (mapped / not); richer taxonomy | Matches working practice on a real long-running LID project. The enum carries real semantic distinctions — "AUDITED" (we know the state) is not the same as "OK" (it is fixed). Simpler enums lose this distinction. |
| Coordination with linked-intent-dev | Ownership table, implicit runtime coordination | Explicit handoff protocol; merging into one skill | Two skills with different triggers. Merging would make the combined skill too thick for small projects that do not need the overlay. |
| Overlay activation signal (ambient) | Presence of `docs/arrows/` directory | CLAUDE.md flag; plugin config; explicit enablement command | The directory either exists or doesn't; this is the cheapest detection signal and requires no additional convention. |
| `/arrow-maintenance` command mode | Invocable; audits + updates in place | Ambient-only skill; require `/map-codebase` for all direct invocation | Users with a naive mental model reach for a command when they want to update arrow state. Exposing the skill as a command respects that expectation. Keeping command mode behavioral (verifiable outputs) makes it eval-gateable. |
| Audited state tracking | `audited` (date) + `audited_sha` (git SHA) | Date only; SHA only | Date is human-readable for staleness judgment; SHA enables incremental audit on subsequent runs, which is a large performance win on big projects. Both are cheap to store. |
| Rename as a lifecycle event | First-class; skill walks all cross-references atomically | Manual find-replace; not a supported event | Renames are common enough that un-supporting them leaves cross-reference rot. Splits and merges already warrant first-class treatment; rename is cheaper. |
| Audit cadence | No prescribed cadence; staleness signal surfaced when skill is consulted | Every N commits; scheduled; CI-enforced | Prescribing cadence is surface growth. Projects have different rhythms; LID emits the signal and lets the user choose when to act. |
| Reconnaissance: sample vs. read-every-file | Read every file in scope | Sample representative files; stop after N files | Sampling risks missing behaviors that only surface in edge-case files; mapping locks in segmentation based on incomplete view. Read-every-file is expensive but produces mappings that hold up over time. |
| Seam identification: one clustering vs. multiple lenses | 3–5 fundamentally different clusterings via distinct lenses, then slicing granularity | Single candidate clustering; free-form user input | A single clustering is the agent's best guess; the user's *choice among lenses* is what reveals latent intent. Anti-pattern lenses (frontend/backend, team ownership) are explicitly excluded because they reflect deployment or org structure, not intent. |
| Brownfield LLD template | Standard LLD template with inline `[inferred]` markers (Option B) | Separate brownfield-specific template; full greenfield rewrite | One template keeps minimum-system. Brownfield state is carried by *content* (inferred markers, Open Questions for quirks) rather than by a separate schema. Content matures into standard-form content in place via normal cascade. |
| Coherence-check script | Ship optional reference implementation; skill delegates when present, falls back to in-prompt | Require script; never ship one; bake checks into skill always | Observed pattern: real-world use (Threadkeeper) shows agents reach for such scripts constantly because in-prompt checks are expensive. Shipping an optional reference acknowledges the pattern without imposing runtime dependency. Language-neutral — any equivalent script works. |

## Open Questions

### Resolved

1. ✅ One plugin, two skills. `arrow-maintenance` has ambient (pure-prose) and command (behavioral) modes; `/map-codebase` is behavioral brownfield mapping.
2. ✅ `docs/arrows/` contains `index.yaml`, one markdown per segment, and a `README.md` template. Anchored at project root, one overlay per project.
3. ✅ Audit is guidance in ambient mode and a behavioral pass in command mode; no separate audit command.
4. ✅ `/map-codebase` runs a comprehensive sweep before segmentation; reconnaissance reads every file in scope with structured per-file reporting.
5. ✅ `/map-codebase` produces arrow docs + skeleton HLD/LLD/EARS + flesh-out prompt, with STOP points between each artifact-generation sub-step.
6. ✅ `/map-codebase` asks for scope at invocation, offers optional subagent parallelism, and warns about token intensity upfront.
7. ✅ Seam identification is two-step: 3–5 lens-based clusterings (with named lenses and anti-patterns) then slicing granularity (coarse/medium/fine).
8. ✅ Arrow doc updates flow through `linked-intent-dev` during changes; `arrow-maintenance` re-audits and cleans up `unmapped.docs` on its runs.
9. ✅ Ambient activation is detected by presence of `docs/arrows/`; command activation is explicit slash-command invocation.
10. ✅ `/arrow-maintenance` always repairs broken `docs/arrows/` state when it runs — this is the skill's domain.
11. ✅ `/arrow-maintenance` invoked on project with LID docs but no `docs/arrows/` generates the overlay from existing docs. On a project with nothing, it redirects to `/map-codebase` or `/lid-setup`.
12. ✅ `/map-codebase` on partial-LID projects asks the user whether to treat existing docs as authoritative or supersede.
13. ✅ Subagent conflicts during mapping are tentatively resolved by the orchestrator and flagged for user reconciliation.
14. ✅ Sweep overflow beyond context window uses per-subagent files as the handoff mechanism, processed in chunks.
15. ✅ Reverse orphans (`@spec` pointing to a missing spec ID) are surfaced for user resolution, not auto-repaired.
16. ✅ Rename is a first-class lifecycle event; skill walks all cross-references atomically.
17. ✅ `audited_sha` tracks git head at last audit; enables incremental audit on subsequent runs.
18. ✅ No prescribed audit cadence; the skill emits staleness signals when consulted and lets the user choose when to act.
19. ✅ Split detected mid-change asks the user and prefers deferral — split at clean breaks, not mid-edit.
20. ✅ Brownfield LLDs use the standard LLD template with `[inferred]` markers (Option B). Initial EARS status: `[x]` for observed, `[ ]` for broken, `[D]` for explicit non-wants.
21. ✅ Coherence-check script shipped as optional reference implementation; skill delegates when present.
22. ✅ Five Critical Rules govern `/map-codebase`: read actual code, each STOP mandatory, LLDs describe current reality, thorough over fast, humble but guide.
23. ✅ `/map-codebase` terminal step runs `/lid-setup` (or equivalent) plus flesh-out prompt — both required.

### Deferred to implementation

1. **Subagent output reconciliation format.** When parallel subagents report their mapping results, what exact structure does the top-level agent consume to identify seams? Likely a JSON schema with observed behaviors, dependencies, and entry points; specifics pend the first real `/map-codebase` run on a non-trivial codebase.
2. **Sweep-file format.** The file-based handoff is the mechanism; the exact schema of each `.lid/map-codebase/sweep-{N}.md` file is left to implementation. Likely YAML front matter plus markdown sections, but shape should follow from what subagents naturally produce.
3. **Orphan artifact handling at scale.** Bulk reporting is the direction, but sizing (how many orphans before the report needs pagination or grouping) matters. To be refined on a real mid-sized project.
4. **Status enum extension.** When a project wants a status value the default enum does not carry, how is that added? Likely by editing the project's own `docs/arrows/README.md`, but whether and how the skill surfaces the customization is TBD.
5. **Taxonomy evolution.** `index.yaml` taxonomy is human-authored at mapping time. How does it stay current as the project grows? Likely by `linked-intent-dev` nudging the user when a new segment doesn't fit the existing taxonomy, but the mechanics are undecided.

## References

- `docs/high-level-design.md` — the HLD; describes when arrow-maintenance becomes load-bearing and its relationship to the core plugin.
- `docs/llds/linked-intent-dev.md` — sibling plugin LLD; the ownership split is specified there as well.
- `/Users/jess/src/personal-log/docs/arrows/` — the working reference implementation this LLD is modeled on.
