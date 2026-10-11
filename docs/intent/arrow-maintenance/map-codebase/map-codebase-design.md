---
parent: arrow-maintenance
prefix: SCALE-MAP
---

# LLD: arrow-maintenance map-codebase Skill

## Context and Design Philosophy

The `map-codebase` skill is the brownfield-bootstrap half of the `arrow-maintenance` plugin. It maps an existing codebase into the tail of the LID arrow so a project can adopt LID without rewriting from scratch. It is a one-time (or occasional) operation: it produces the `docs/arrows/` overlay and skeleton upstream docs where none existed, after which the sibling `maintenance` skill takes over ongoing navigation and audit, and `linked-intent-dev` drives per-change work.

The shared design this skill targets — the `docs/arrows/` overlay, the `index.yaml` schema (including the `parent`/`children` tree links), the arrow-doc format, and the tree-mirrored directory layout — is specified in the parent sub-HLD at `docs/intent/arrow-maintenance/arrow-maintenance-design.md`. This LLD describes the mapping workflow that *produces* those artifacts; it does not re-specify their schema. Terms like *arrow*, *segment*, *drift*, *coherence*, and *cascade* are defined in the HLD's Glossary section.

This LLD owns the `SCALE-MAP` segment and its specs at `docs/intent/arrow-maintenance/map-codebase/map-codebase-specs.md`. The skill is behavioral — it produces verifiable project-state changes — so its assertions are covered by EARS and gated by an eval suite.

**A note on actors.** "The skill" refers to the prose guidance; the agent is the actor. All sweeping, clustering, and artifact-generation happens through the agent acting on skill guidance (or subagents the agent dispatches).

## Intent

Map an existing codebase into the tail of the LID arrow so the project can adopt LID without rewriting from scratch. The command produces three outputs: the `docs/arrows/` overlay (index + per-segment docs), skeleton upstream docs (HLD, LLDs, EARS spec files), and a prompt to the user to flesh out the skeletons through `linked-intent-dev`.

## Invocation

`/map-codebase` asks the user at invocation for the starting scope — whether to map the whole project (implies Full LID mode) or specific parts (implies Scoped LID mode, with the user identifying which parts). This single scope question determines both the sweep scope and the LID mode written at terminal verification; the user is not asked a separate "Full or Scoped?" question later. It also offers the option to enable subagent-parallel mapping (one subagent per initial scope area, outputs merged). Parallelism is recommended for large codebases where a single-agent sweep would be slow or hit context limits; single-agent mode is sufficient for smaller ones.

**Token-intensity warning.** `/map-codebase` is token-intensive by design — it reads every file in the declared scope, proposes multiple clustering lenses, drafts skeleton docs for every segment, and walks the user through multi-step reconciliation. The skill warns the user upfront at invocation: this is not a lightweight operation, and the quality of the mapping depends on the thoroughness of the work. Users who expect a one-shot quick-mapping are steered toward that expectation being wrong; they can proceed or reconsider.

**State dispatch.** If the project already has partial LID docs (an HLD or some LLDs exist), the command asks the user whether to treat the existing docs as authoritative (draft skeletons only for segments not yet covered) or to supersede them. There is no silent overwrite. If the project already has full LID docs and no `docs/arrows/`, the command redirects the user to `/arrow-maintenance`, which generates the overlay from existing docs without the brownfield sweep.

## Five Critical Rules

Five rules govern the entire workflow, applied consistently by the agent regardless of phase:

1. **Read actual code, don't guess.** Every claim in the generated artifacts traces to file/line evidence. Speculation about behavior is flagged explicitly rather than presented as fact.
2. **Each STOP is mandatory.** The workflow has multiple stop points (after sweep, after lens selection, after slicing, after user reconciliation, after each per-segment LLD draft, after HLD synthesis, after EARS and arrow-doc generation). None of them are optional. Rushing past a stop is how brownfield mapping produces bad LLDs that poison subsequent work.
3. **LLDs describe current reality, not aspirational design.** The output is what the code *is*, not what a greenfield version *would be*. Inferred design decisions carry `[inferred]` markers; known technical debt and behavioral quirks are recorded in Open Questions — the user decides later whether to endorse, fix, or change.
4. **Be thorough over fast.** Token budget is a real constraint but not a dominant one; skimming produces mappings that miss behaviors and lock in the wrong segmentation.
5. **Be humble but guide.** The agent is not the expert on the user's system; the user is. But the agent also doesn't silently defer to whatever the user says — when the user's framing seems wrong given the evidence, the agent surfaces the tension with evidence rather than just going along. Humble but not passive.

## Comprehensive Mapping Workflow

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

   Output: a flat list of observed behaviors with file/line references. No segmentation attempted here. When sweep output exceeds the orchestrator's context window, each subagent writes its sweep to a per-subagent file (e.g., `docs/arrows/_map-codebase/sweep-{N}.md`); the orchestrator processes them in chunks during the next phase. The file format is left to implementation; the file-based handoff is the mechanism.

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

   **Component quality guidance.** When reviewing proposed segments, the agent applies a working definition of "intent component": a thing achieving an independent purpose in the system. Good components are self-contained in intent (auth, payment, notification, recording pipeline). False components to challenge include clusters organized around team boundaries, deployment units, file locations, or generic "utils." When a proposed segment matches an anti-pattern, the agent flags it for the user rather than accepting silently. Segment and component names are derived from the codebase's existing vocabulary (module/directory names, domain terms), not imposed by LID (HLD tenet: *Speak the project's language*).

5. **Artifact generation.** For each approved segment, the agent drafts the following, **with a STOP after each sub-step**:

   - **Per-segment arrow doc** (at the tree-mirrored path under `docs/arrows/`, per the parent sub-HLD's directory layout) with references to actual files and initial status `MAPPED`. **STOP after each segment's arrow doc.**
   - **Skeleton LLD** (at the mirroring path under `docs/intent/`). Uses the standard LLD template — *not* a separate brownfield template. Content reflects brownfield state: the Decisions & Alternatives table is populated with observed decisions carrying `[inferred]` markers in the Rationale column; Open Questions holds observed-but-unexplained behaviors and technical debt; major sections describe current state. **STOP after each segment's LLD.**
   - **EARS spec file** beside the segment's design doc (`docs/intent/<segment-path>/{segment-name}-specs.md`) with a reserved spec-ID prefix (the segment's root-to-leaf path). Initial status semantics for brownfield mapping:
     - `[x]` — behavior is observed in current code (the spec describes what exists and works).
     - `[ ]` — behavior is specified but broken or partial in current code.
     - `[D]` — explicit non-wants (intentional non-features); rare in brownfield.
     **STOP after each segment's specs.**
   - **Entry in `index.yaml`** including the taxonomy placement and `parent`/`children` tree links chosen during reconciliation.
   - **Skeleton HLD** (`docs/high-level-design.md`) *if one does not already exist*. Uses the standard HLD template with bodies marked "not yet specified." **STOP after HLD draft.** If an HLD already exists, skip this step.

6. **Terminal verification and flesh-out prompt.** After artifact generation completes, the skill runs `/update-lid` (or its equivalent bootstrap logic) to ensure CLAUDE.md is configured with LID directives and the chosen mode marker — passing through the mode determined by the invocation scope question so the user is not re-prompted. Then it issues a **flesh-out prompt** directing the user to move into the `linked-intent-dev` workflow segment-by-segment to populate the skeleton LLDs and EARS specs. Without this prompt the user may leave the reconstruction incomplete, and partial arrows propagate incoherence into future sessions. The prompt is not optional from the skill's side; it is the terminal step. The exact ordering of the `update-lid` call and the flesh-out prompt is an implementation choice — both must happen before the command exits.

## Output Summary

After `/map-codebase` completes (whether the user has started fleshing out skeletons or not), the project has:

- a navigable `docs/arrows/` overlay (index + segment docs at tree-mirrored paths);
- a complete-but-empty `docs/intent/` tree (one file per segment);
- a reserved set of EARS spec files with IDs claimed by segment;
- a skeleton HLD (or the existing one, untouched);
- `CLAUDE.md` updated with a `## LID` block carrying `- Mode: Full` (or the user-chosen mode) and the standard LID directives;
- the prompt to resume via `linked-intent-dev` on a segment-by-segment basis.

This is enough for `linked-intent-dev` to start operating immediately on subsequent changes. The agent does not need `arrow-maintenance`-specific knowledge to fill in the skeletons — they live in standard LID locations, so the core workflow picks them up naturally.

## Decisions & Alternatives

| Decision | Chosen | Alternatives Considered | Rationale |
|---|---|---|---|
| Mapping: comprehensive vs. segment-by-segment | Comprehensive sweep first | Segment-by-segment walk; single-pass top-down | Segment-by-segment over- or under-sizes early segments because the full shape is invisible at the start. A comprehensive sweep exposes seams; segmentation decisions follow with the user in the loop. |
| Mapping output | Arrow docs + skeleton upstream + flesh-out prompt | Arrow docs only; full fabricated upstream docs | Arrow docs alone leave reconstruction incomplete; users may never return to fill in upstream. Full fabrication risks inventing intent that was never there. Skeleton + prompt keeps the agent honest (empty sections are visible gaps) while giving `linked-intent-dev` enough scaffolding to start operating. |
| Subagent parallelism for mapping | Optional, asked at invocation | Always serial; always parallel | Small codebases do not need parallelism; large ones materially benefit. Asking respects the user's judgment about their project's size. |
| Reconnaissance: sample vs. read-every-file | Read every file in scope | Sample representative files; stop after N files | Sampling risks missing behaviors that only surface in edge-case files; mapping locks in segmentation based on an incomplete view. Read-every-file is expensive but produces mappings that hold up over time. |
| Seam identification: one clustering vs. multiple lenses | 3–5 fundamentally different clusterings via distinct lenses, then slicing granularity | Single candidate clustering; free-form user input | A single clustering is the agent's best guess; the user's *choice among lenses* is what reveals latent intent. Anti-pattern lenses (frontend/backend, team ownership) are explicitly excluded because they reflect deployment or org structure, not intent. |
| Brownfield LLD template | Standard LLD template with inline `[inferred]` markers | Separate brownfield-specific template; full greenfield rewrite | One template keeps minimum-system. Brownfield state is carried by *content* (inferred markers, Open Questions for quirks) rather than by a separate schema. Content matures into standard-form content in place via normal cascade. |
| Scope question carries the mode | One scope question (whole project → Full, parts → Scoped); passed through to `/update-lid` | Separate "Full or Scoped?" prompt at terminal verification | The scope answer already determines the mode; a second prompt at the end of a long flow is a bad user experience. The caller passes the mode through and `update-lid` honors it. |

## Open Questions

### Resolved

1. ✅ `/map-codebase` runs a comprehensive sweep before segmentation; reconnaissance reads every file in scope with structured per-file reporting.
2. ✅ `/map-codebase` produces arrow docs + skeleton HLD/LLD/EARS + flesh-out prompt, with STOP points between each artifact-generation sub-step.
3. ✅ `/map-codebase` asks for scope at invocation (which sets the LID mode), offers optional subagent parallelism, and warns about token intensity upfront.
4. ✅ Seam identification is two-step: 3–5 lens-based clusterings (with named lenses and anti-patterns) then slicing granularity (coarse/medium/fine).
5. ✅ `/map-codebase` on partial-LID projects asks the user whether to treat existing docs as authoritative or supersede; on full-LID projects with no overlay it redirects to `/arrow-maintenance`.
6. ✅ Subagent conflicts during mapping are tentatively resolved by the orchestrator and flagged for user reconciliation.
7. ✅ Sweep overflow beyond context window uses per-subagent files as the handoff mechanism, processed in chunks.
8. ✅ Brownfield LLDs use the standard LLD template with `[inferred]` markers. Initial EARS status: `[x]` for observed, `[ ]` for broken, `[D]` for explicit non-wants.
9. ✅ Five Critical Rules govern `/map-codebase`: read actual code, each STOP mandatory, LLDs describe current reality, thorough over fast, humble but guide.
10. ✅ `/map-codebase` terminal step runs `/update-lid` (or equivalent) plus a flesh-out prompt — both required, mode passed through from the scope question.

### Deferred to implementation

1. **Subagent output reconciliation format.** When parallel subagents report their mapping results, what exact structure does the top-level agent consume to identify seams? Likely a JSON schema with observed behaviors, dependencies, and entry points; specifics pend the first real `/map-codebase` run on a non-trivial codebase.
2. **Sweep-file format.** The file-based handoff is the mechanism; the exact schema of each `docs/arrows/_map-codebase/sweep-{N}.md` file is left to implementation. Likely YAML front matter plus markdown sections, but shape should follow from what subagents naturally produce.

## References

- `docs/intent/arrow-maintenance/arrow-maintenance-design.md` — parent sub-HLD; authoritative for the `docs/arrows/` overlay it produces, the `index.yaml` schema (including `parent`/`children` tree links), the arrow-doc format, and the tree-mirrored directory layout.
- `docs/intent/arrow-maintenance/map-codebase/map-codebase-specs.md` — the `SCALE-MAP` specs this LLD owns.
- `docs/intent/arrow-maintenance/maintenance/maintenance-design.md` — sibling leaf; the navigation/audit skill that takes over once the overlay exists, and the redirect target for full-LID projects that only need overlay bootstrap.
- `docs/intent/linked-intent-dev/linked-intent-dev-design.md` — core plugin LLD; authoritative for the LLD/HLD/EARS templates the skeletons use, the brownfield-LLD content conventions, the spec-ID format, and the `/update-lid` bootstrap this skill's terminal step invokes.
- `plugins/arrow-maintenance/skills/map-codebase/` — the compiled skill (`SKILL.md` + `references/`).
