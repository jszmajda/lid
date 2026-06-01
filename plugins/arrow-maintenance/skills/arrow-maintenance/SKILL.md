---
name: arrow-maintenance
description: Navigation and audit overlay for linked-intent development. Use when working with docs/arrows/ — orienting via index.yaml, auditing spec-to-code coherence, detecting reverse orphans and drift, splitting/merging/renaming/re-parenting segments. Dual-mode: ambient guidance when the overlay is present (catch-and-recommend), or explicit /arrow-maintenance command for a directed audit-and-update pass.
---

# Arrow Maintenance

The arrow-maintenance overlay scales linked-intent-dev for projects too large to hold in one context window. It provides a navigation index, systematic audit, and brownfield bootstrap.

This skill operates in **two modes**. Detect which mode applies before acting.

## Two modes

**Ambient mode.** Auto-triggered on arrow-adjacent prompts when `docs/arrows/` exists. Posture is *catch and recommend* — notice relevant work, surface findings, edit only as the surrounding conversation authorizes. File writes happen opportunistically (e.g., updating an arrow doc's coverage table alongside a linked-intent-dev edit on the same segment). Record arrow lifecycle events (split, merge, rename, re-parent, status transitions) rather than erasing them. Do not initiate a systematic audit-and-update pass in ambient mode.

**Command mode.** Invoked explicitly as `/arrow-maintenance`. Posture is *directed action* — the user has asked for the pass. Run an audit-and-update pass, apply unambiguous fixes in place, and surface the rest for user decision. Does not pause at synthetic phase boundaries — it is a single directed pass.

## When `/arrow-maintenance` is invoked

Inspect the project and dispatch on state:

- **Overlay present (`docs/arrows/` exists)** → run the audit-and-update pass (below).
- **LID docs present (HLD + at least one LLD) but no `docs/arrows/`** → generate the overlay from existing LID docs: populate `index.yaml` with one `arrows:` entry per design-tree node — one leaf entry per leaf LLD (the EARS-owning nodes) and one grouping entry per sub-HLD node — recording the tree's nesting via `parent`/`children` links, status `MAPPED`, `sampled: {today}`, `audited_sha: null`; create one per-segment arrow doc per leaf LLD at its tree-mirrored path (`docs/arrows/<path>/<leaf>.md`), referencing the existing LLD and any known tests/code. Sub-HLD nodes are directories, not arrow docs — their `index.yaml` entry sets `detail` to the sub-HLD's design doc (`../intent/<path>.md`) instead. Do not generate new HLD, LLD, or EARS skeletons (those exist).
- **Neither LID docs nor overlay** → the user typed `/arrow-maintenance` on a project that isn't ready for it. Don't just print a redirect — describe what you found and offer to dispatch: "I see no LID installation here. You probably want `/linked-intent-dev` if this is a greenfield project (give it a description of what you want to build; it bootstraps LID as part of Phase 1), or `/map-codebase` if you're bringing LID to an existing codebase. Shall I run one of those instead, or did you mean something else?" Then proceed based on the user's answer.

## Audit-and-update pass (command mode)

Every `/arrow-maintenance` run, in order:

1. **Repair broken overlay state.** Malformed `index.yaml`, missing per-segment docs referenced by the index, stale schema versions — these are this skill's domain, so fix them first.

2. **Run the five audit checks** (see `references/audit-checklist.md`):
   - **Reference coherence**: do arrow-doc pointers resolve? Are cited EARS specs present? Are LLD section headings as referenced?
   - **Coverage**: does every behavioral spec have at least one eval assertion citing it?
   - **Staleness**: compare `audited` and `audited_sha` against current state to find segments whose files changed since last audit.
   - **Drift signals**: modified code since `audited_sha`, specs changed without test updates, tests passing but missing `@spec` annotations, `@spec` annotations pointing to missing spec IDs (*reverse orphans*).
   - **Orphan artifacts**: LLDs, specs, or code files not listed in any arrow doc's References section.

   Exclude the reserved `docs/arrows/_experiments/` subtree from all five checks — it is owned by `lid-experimental`, not this skill, and is never audited, cleaned up, or regenerated here (see `docs/intent/arrow-maintenance/arrow-maintenance-design.md`).

   When a project-local coherence script is declared under `## LID Tooling` in `CLAUDE.md` (as `Coherence check: {path}`), invoke that script and treat its output as authoritative for the deterministic checks it performs. Languages and paths vary by project — trust the declaration. If the declaration is missing or the declared path does not exist, perform the checks in-prompt. A reference Node implementation is bundled at `references/coherence-check.mjs` that users may copy to their project and declare in CLAUDE.md.

3. **Apply unambiguous fixes in place:**
   - Regenerate `## Spec Coverage` tables in affected arrow docs from source scans.
   - Regenerate `## References` sections from source scans (grep for `@spec`, check file paths exist).
   - Update `status` / `next` / `drift` fields in `index.yaml` where the new state is clear.
   - Clean up `unmapped.docs`: assign entries to segments where the assignment is unambiguous; flag the rest for user assignment.
   - Refresh `audited: {today}` and `audited_sha: {current git HEAD}` on each audited segment.

4. **Surface everything else for user decision:**
   - Reverse orphans — ask whether to create the missing spec, delete the annotation, or treat as an alias of an existing spec. Do not auto-resolve.
   - Ambiguous segment assignments for `unmapped.docs` entries.
   - Candidate lifecycle events (splits, merges) detected from drift signals.
   - Any finding where the right fix depends on intent.

5. **Produce a structured report** at the end: list findings, distinguishing those that were automatically resolved from those requiring user decision. Include location (segment, file, line) for each.

## Incremental audit

When `audited_sha` is populated and git history is available, run the audit in incremental mode — inspect only segments whose files changed since `audited_sha`. This is a large performance win on big projects. When `audited_sha` is null (never audited) or git history is unavailable, audit every segment.

## Ambient mode behavior

When the skill is consulted ambiently (not via `/arrow-maintenance`), bias the agent's work on arrow-adjacent tasks:

- **Start from `index.yaml`.** Load it first, before any per-segment doc. Query for unblocked segments (where `blockedBy` is empty and `status` is not `OK` or `OBSOLETE`).
- **Load detail on demand.** Only load the per-segment arrow doc once a specific segment is implied. Follow its `## References` into LLDs, spec files, tests, or code as needed.
- **Surface drift rather than silently repair.** When you notice a reference mismatch, reverse orphan, or stale segment during other work, mention it. Let the user or `linked-intent-dev` drive the fix.
- **Participate in writes the conversation is already doing.** When `linked-intent-dev` is editing a segment, update that segment's arrow doc and `index.yaml` entry in the same cascade — this is opportunistic, not initiated by you.

## Authoritative sources

When information appears in multiple places, this is the authority rule:

- **Segment state fields** (`status`, `sampled`, `audited`, `audited_sha`, `next`, `drift`, `blocks`, `blockedBy`, `merged_into`) live authoritatively in `index.yaml`.
- **Per-segment arrow doc's References and Spec Coverage** are *derived views* — regenerated from source scans during audit. Do not hand-edit them to contradict source.
- **`index.yaml` schema** is defined authoritatively in `docs/intent/arrow-maintenance/arrow-maintenance-design.md` (the sub-HLD that owns the shared overlay); `references/index-schema.md` is the working copy. Cross-plugin schema changes defer to the sub-HLD.
- **Spec-file header format** (the LID-on-LID inversion) is defined in `docs/intent/linked-intent-dev/linked-intent-dev-design.md` — this skill reads from that schema.
- **`@spec` placement rule** (entry point of behavior's implementation graph) is defined in the `linked-intent-dev` skill.

## Arrow doc format

An arrow segment is the territory owned by one **leaf** LLD — the node that owns EARS specs — and its boundary is that leaf's prefix in the path-concatenated EARS IDs (e.g., `grep SCALE-MAINT` gathers the segment). Each leaf segment has one markdown file under `docs/arrows/` at the path mirroring its design doc under `docs/intent/` (e.g., `docs/arrows/arrow-maintenance/maintenance.md` mirrors `docs/intent/arrow-maintenance/maintenance/maintenance-design.md`); at depth-2 this is a flat set of `{segment-name}.md` files. Sub-HLD (grouping) nodes own no EARS and no segment — they are directories, not arrow docs. See `references/arrow-doc-template.md` for the template. The arrow doc is an *orientation page*, not a design doc — pointers + coverage table, no duplicated design content.

## Status enum

| Status | Meaning |
|---|---|
| UNMAPPED | Not yet explored |
| MAPPED | Structure known, specs not verified against code |
| AUDITED | Specs verified — implementation status understood |
| OK | Fully coherent — all specs implemented |
| PARTIAL | Some specs missing or partial |
| BROKEN | Code and docs have diverged significantly |
| STALE | Docs exist but outdated |
| OBSOLETE | Superseded, kept for historical reference |
| MERGED | Combined into another arrow (use `merged_into` field) |

Normal progression: `UNMAPPED → MAPPED → AUDITED → OK`.

## Lifecycle events

Segments evolve. Five first-class events. This skill is the owner that executes them on an existing overlay; `linked-intent-dev` recognizes one mid-change and hands off here. The mechanics and atomicity guarantees are specified authoritatively in `docs/intent/arrow-maintenance/arrow-maintenance-design.md § Lifecycle Events`.

- **Split**: one segment → two. Create the new segment's arrow doc, move relevant references, update both docs to reference each other, record in `index.yaml`. If detected mid-change, ask whether to split now or defer — deferring is preferred. Split at clean breaks, not mid-edit.
- **Merge**: two segments → one. Pick primary, move references, mark secondary as `MERGED` with `merged_into: {primary-name}`. Tombstone or delete the secondary's arrow doc.
- **Rename**: a leaf segment's name changes (e.g., `auth` → `identity`). Because that name is the leaf prefix of the segment's path-concatenated EARS IDs, the rename rewrites every spec ID under it (`AUTH-UI-001` → `IDENTITY-UI-001`) across the spec files **and** every `@spec` annotation in code and tests that cites those IDs. In the same pass, walk *all* other cross-references: the arrow-doc filename, the `index.yaml` entry key, `parent`/`children` links, `blocks`, `blockedBy`, `merged_into`, `taxonomy` membership, and every other arrow doc's References section. Rename is not rename-and-hope — spec files, docs, `index.yaml`, and code annotations land together or not at all.
- **Re-parent**: a subtree moves to a new parent in the design tree (e.g., the `runner` leaf moves from under `prompt-eval` to under `orchestration`). Because an EARS ID *is* the root-to-leaf path, re-parenting rewrites the path-concatenated IDs of every spec in the moved subtree (`PEVAL-RUN-014` → `ORCH-RUN-014`) and every `@spec` annotation citing them across code, tests, and docs, plus the `parent`/`children` links in `index.yaml` for the moved node and both the old and new parents. Like rename, this happens atomically in one session.
- **Status transition**: `UNMAPPED → MAPPED → AUDITED → OK` with detours as needed. Timestamps (`sampled`, `audited`, `audited_sha`) record when each transition happened.

Rename and re-parent are the **tooled, atomic restructuring operation** this plugin owns: path-concatenated EARS IDs are stable under ordinary growth and change *only* under a deliberate rename or re-parent. A partial application — IDs rewritten in the spec file but not in code — is exactly the cross-reference rot the atomicity requirement exists to prevent.

## Coordination with linked-intent-dev

| Concern | Owner |
|---|---|
| Per-change HLD/LLD/EARS/test/code work | linked-intent-dev |
| Cascade at change time | linked-intent-dev |
| Arrow doc + `index.yaml` updates *during* a change | linked-intent-dev (has segment in context) |
| `unmapped.docs` cleanup | arrow-maintenance during audit; linked-intent-dev when it notices an unmapped doc it can assign in passing |
| Systematic audit across segments | arrow-maintenance |
| Drift detection between sessions | arrow-maintenance |
| Brownfield mapping | arrow-maintenance (`/map-codebase`) |
| Overlay bootstrap on existing LID projects | arrow-maintenance (`/arrow-maintenance` command mode) |
| Lifecycle events (split, merge, rename, re-parent, status) | Either skill; arrow-maintenance has richer guidance for multi-segment events and owns the atomic rename/re-parent operation that rewrites path-concatenated EARS IDs and their `@spec` annotations across docs and code |

## No prescribed audit cadence

The skill does not prescribe "run audit every N commits" or "run weekly." Surface staleness signals when consulted; let the user choose the rhythm.

## Reference files

- `references/index-schema.md` — full `index.yaml` schema.
- `references/arrow-doc-template.md` — per-segment arrow doc template.
- `references/audit-checklist.md` — the five audit checks in actionable form.
- `references/coherence-check.mjs` — reference Node implementation of deterministic checks. Optional; any equivalent in any language works.
- `references/README-template.md` — template for the `docs/arrows/README.md` that projects install alongside their overlay.
