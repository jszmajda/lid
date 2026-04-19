---
name: map-codebase
description: Bootstrap LID in an existing (brownfield) codebase. Deep-reads every file in the declared scope, offers lens-based clustering options, generates skeleton LLDs/HLD/EARS bottom-up, then creates arrow docs and prompts the user to flesh out the skeletons. Token-intensive by design. Use when asked to map a codebase, bootstrap arrows, reverse-engineer the design, or start LID on an existing project.
disable-model-invocation: true
---

# Map Codebase (Brownfield Arrow Bootstrap)

This skill maps an existing codebase into the arrow of intent. It works bottom-up: read all the code in scope first, then propose lens-based clusterings for the user to choose among, then generate skeleton docs that describe what actually exists.

See [brownfield-bootstrap.md](references/brownfield-bootstrap.md) for detailed guidance per phase.

## Five Critical Rules

These govern every phase. Apply consistently.

1. **Read actual code, don't guess.** Every claim in generated artifacts traces to file/line evidence. Speculation is flagged explicitly rather than presented as fact.
2. **Each STOP is mandatory.** The workflow has multiple stop points. None are optional. Rushing past a stop is how brownfield mapping produces bad LLDs that poison subsequent work.
3. **LLDs describe current reality, not aspirational design.** Output is what the code *is*, not what a greenfield version *would be*. Inferred design decisions carry `[inferred]` markers; known technical debt and behavioral quirks go in Open Questions.
4. **Thoroughness over speed.** Token budget is real but not dominant; skimming produces mappings that miss behaviors and lock in the wrong segmentation.
5. **Humble but guide.** The agent is not the expert on the user's system; the user is. But don't silently defer — when the user's framing conflicts with the evidence, surface the tension with evidence rather than just going along.

## At invocation

Ask one question first:

- **Whole project, or specific parts?**
  - **Whole project** → implies Full LID mode. Scope is the entire project.
  - **Specific parts** → implies Scoped LID mode. Ask the user to name the parts (directories, file lists, or component names). The declared parts are both the sweep scope and the LID scope going forward.

This question determines scope *and* mode simultaneously — the user is not asked a separate "Full or Scoped?" later at terminal verification. Default to Full (whole project) if the user is undecided.

Then ask:

- **Subagent parallelism** — offer as an option. Recommended for large codebases; single-agent works for smaller ones.

**Token-intensity warning.** Tell the user upfront this is token-intensive by design — reading every file, proposing multiple lenses, drafting skeletons for every segment, multi-step reconciliation. Not a lightweight operation. Users expecting a quick one-shot map should reconsider.

**Undo.** The workflow's STOPs between phases are the undo mechanism — aborting at any STOP leaves nothing written to disk. Agent harnesses also provide their own session-level rewind. LID does not ship a dedicated `/unmap-codebase` command; users roll back via the agent framework's rewind or by reverting a git commit.

## State dispatch

Inspect the project before starting:

- **Partial LID docs exist** (HLD or some LLDs, but not complete). Ask the user: treat existing docs as authoritative (draft skeletons only for uncovered segments) or supersede them? Do not silently overwrite.
- **Full LID docs exist but no `docs/arrows/`.** Redirect the user to `/arrow-maintenance` — that command bootstraps the overlay from existing docs without the brownfield sweep. Do not proceed here.
- **No LID docs, no overlay.** Standard brownfield flow (below).

## Phase 1 — Sweep (Reconnaissance)

Read **every file** in the declared scope. Not a sample. Sampling risks missing behaviors that only surface in edge-case files and locks in segmentation based on incomplete view.

For each file, record a structured summary:

- **Purpose** — what this file appears to do.
- **Exports** — functions, classes, types, endpoints exposed to other parts of the system.
- **Dependencies** — what the file imports or calls.
- **Data shapes** — structures it produces or consumes.
- **Side effects** — filesystem, network, database, logs.
- **Role** — how this file fits into the larger system (UI component, API handler, background job, pure utility, etc.).
- **Observations** — anything unusual, deprecated-looking, or flagged by comments.

Output: a flat list of observed behaviors with file/line references. **No segmentation attempted here.**

**Capacity constraint handling.** If the declared scope exceeds the invocation's capacity (single-agent context window, or the chosen subagent budget), surface the constraint with concrete sizing evidence, warn the user that a sampled sweep produces lower-quality mapping, and recommend narrowing scope or enabling subagent parallelism. The user may override and proceed with sampling anyway. Under override, preserve state across truncation points via per-subagent files (`.lid/map-codebase/sweep-{N}.md`) or by incrementally writing arrow-doc partial drafts during reconnaissance — never silently discard information the orchestrator cannot hold.

When subagents ran in parallel, each subagent writes its sweep to its own file; the orchestrator processes them in chunks during Phase 2.

See [subagent-sweep-prompt.md](references/subagent-sweep-prompt.md) for the prompt template given to sweep workers.

## Phase 2 — Seam Identification: Lens Selection

Propose **3–5 fundamentally different clusterings**, each using a distinct *lens*. Not variations on one theme — entirely different mental models.

**Good lenses to propose:**

- **Data flow** — what data originates where, how it moves between modules.
- **User-facing capability** — clusters organized around things a user can do (sign in, check out, export data).
- **Domain concept** — clusters matching domain language (order, inventory, keeper, entry).
- **Behavioral boundary** — where the system changes state in coordinated ways (authentication flow, payment pipeline).
- **Creative / unconventional** — a lens not already tried, presented as a counterweight.

**Anti-pattern lenses to explicitly avoid:**

- Frontend vs. backend split (deployment-location, not intent).
- Files that deploy together (infrastructure grouping, not intent).
- Team ownership (org chart, not intent).
- Utils / shared / common directory (tooling leftover, not a real concept).

For each proposed clustering, present: name, lens, the clusters it produces, pros, cons, and best-for (what kind of reasoning it supports well).

**STOP. User picks a lens.** Multiple lenses are the primary edge-detection mechanism — the user's *choice* of lens reveals latent intent in a way no single clustering can.

See [reconciliation-template.md](references/reconciliation-template.md) for the presentation format.

## Phase 3 — Seam Identification: Slicing Granularity

Within the chosen lens, propose **2–3 slicing variations**:

- **Coarse** — 3–4 large segments. Fewer LLDs to maintain, less precise tracking.
- **Medium** — 6–8 segments. Balanced.
- **Fine** — 10+ finer-grained segments. More precise tracking at the cost of more docs.

Coarse absorbs more code per LLD; fine gives precise segment-scoped tracking. Pick based on project maturity and the user's appetite for maintenance.

**STOP. User picks a slicing.**

## Phase 4 — User Reconciliation

Present the final candidate clustering (chosen lens + chosen granularity). User:

- Approves, or
- Modifies individual segment boundaries, or
- Rejects and goes back to lens/slicing selection, or
- Combines or splits proposed segments.

Where parallel subagents disagreed on segment assignments earlier, flag those conflicts prominently here.

**Component quality check.** When reviewing, apply the working definition: a segment should be *an independent system achieving an independent purpose*. Flag proposed segments that match anti-patterns (team boundaries, deployment units, file locations, generic "utils") rather than accepting them silently.

**STOP. User approves the final clustering before artifact generation begins.**

## Phase 5 — Artifact Generation

For each approved segment, generate these artifacts in order with a **STOP after each**:

1. **Per-segment arrow doc** at `docs/arrows/{segment-name}.md` — References pointing to actual files, initial `status: MAPPED`. See [arrow-doc template](../../arrow-maintenance/references/arrow-doc-template.md). **STOP.**
2. **Skeleton LLD** at `docs/llds/{segment-name}.md` — standard LLD template ([lld-templates](../../../linked-intent-dev/skills/linked-intent-dev/references/lld-templates.md)), no separate brownfield template. Content carries brownfield state: `[inferred]` markers in Decisions & Alternatives table, Open Questions for observed-but-unexplained behaviors. **STOP.**
3. **EARS spec file** at `docs/specs/{segment-name}-specs.md` — reserved spec-ID prefix (derived from segment name; ask the user for a namespacing segment if the prefix collides with an existing one). Initial status semantics:
   - `[x]` — behavior is observed as working in current code.
   - `[ ]` — behavior is specified but broken or partial in current code.
   - `[D]` — explicit non-wants (intentional non-features); rare in brownfield.
   **STOP.**
4. **`index.yaml` entry** under `arrows:` with the taxonomy placement chosen during reconciliation. Follow the schema in [index-schema.md](../../arrow-maintenance/references/index-schema.md).

After all segments are generated, if no HLD exists:

5. **Skeleton HLD** at `docs/high-level-design.md` — standard template ([hld-template](../../../linked-intent-dev/skills/linked-intent-dev/references/hld-template.md)), bodies marked `*(not yet specified)*` rather than filled with placeholder content. If an HLD already exists, skip this step — never modify an existing HLD. **STOP.**

## Phase 6 — Terminal Verification & Flesh-out Prompt

Before completing:

- **Ensure CLAUDE.md is configured.** Invoke the `/lid-setup` behavior (equivalent to running the `lid-setup` skill), passing the mode that was determined from the invocation-time scope question. `lid-setup` honors caller-provided mode and does not re-prompt. Result: LID directives block present, `## LID Mode:` marker set to the determined mode, arrow-navigation rows included (since the overlay is now installed), and a `## LID Tooling` section scaffolded if a coherence script is to be declared. `lid-setup` runs exactly once per `/map-codebase` invocation — at terminal verification, not during artifact generation.

- **Issue the flesh-out prompt.** Direct the user to move into the `linked-intent-dev` workflow segment-by-segment to populate the skeleton LLDs and EARS specs. Without this prompt the user may leave reconstruction incomplete — and partial arrows propagate incoherence into future sessions. **The flesh-out prompt is the terminal step; do not exit without issuing it.**

## Reference files

- [brownfield-bootstrap.md](references/brownfield-bootstrap.md) — full detailed workflow guidance.
- [subagent-sweep-prompt.md](references/subagent-sweep-prompt.md) — prompt template for parallel sweep workers.
- [reconciliation-template.md](references/reconciliation-template.md) — presentation format for Phase 2/3 user reconciliation.
- [skeleton-hld-template.md](references/skeleton-hld-template.md) — pointer to the standard HLD template.
