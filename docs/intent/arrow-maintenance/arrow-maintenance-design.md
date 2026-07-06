---
parent: high-level-design
prefix: SCALE
---

# Sub-HLD: arrow-maintenance Plugin

## Context and Design Philosophy

The `arrow-maintenance` plugin carries LID's functions for **large and brownfield codebases** — the work that becomes necessary once a project's arrow no longer fits in one context window. It is installed alongside `linked-intent-dev` by default but is load-bearing only when the project has enough intent components that orientation takes more than a glance at the file list, when the project is brownfield and needs initial mapping, or when the user wants a navigation aid for its own sake. Its shared mechanism is the `docs/arrows/` overlay; it is never wrong to have, and the question is only whether the overhead pays for itself on a given project.

This document is a **sub-HLD**: an HLD-shaped node in LID's recursive design tree that owns no EARS of its own. It describes the shared design both of the plugin's skills depend on — the **`docs/arrows/` overlay artifact definition** (its schema, arrow-doc format, and directory layout), the progressive-disclosure navigation model, the lifecycle events that operate on the overlay, and the cascade relationship with `linked-intent-dev`. One skill *operates* this overlay; the other *produces* a conforming one as one output of a broader bootstrap. The plugin's two skills are leaf LLDs beneath it:

- **`maintenance`** (`docs/intent/arrow-maintenance/maintenance/maintenance-design.md`, segment `SCALE-MAINT`) — the dual-mode `/arrow-maintenance` skill: ambient navigation/audit guidance plus the command-mode audit-and-update pass.
- **`map-codebase`** (`docs/intent/arrow-maintenance/map-codebase/map-codebase-design.md`, segment `SCALE-MAP`) — the brownfield-bootstrap skill that maps an existing codebase into the tail of the LID arrow.

The plugin roots the `SCALE` segment prefix. Neither this sub-HLD nor the prefix itself owns EARS directly; the two leaf segments (`SCALE-MAINT`, `SCALE-MAP`) own the behavioral specs, so a `grep SCALE` gathers the whole subtree by construction. Terms like *arrow*, *segment*, *drift*, *coherence*, and *cascade* are defined in the HLD's Glossary section.

The overlay is anchored at the project root (`docs/arrows/`), same scope as the `## LID` block's `- Mode:` marker in `CLAUDE.md`. There is one overlay per project, not one per scope.

**A note on actors.** As in `linked-intent-dev`, "the skill" refers to the prose guidance and the agent is the actor. All surfacing, audit-running, and map-generating happens through the agent acting on skill guidance.

## Why arrow-maintenance Exists

Arrow-maintenance addresses three problems that emerge as projects grow past the point where the whole arrow fits in one context window:

1. **Navigation.** An agent needs to find the right arrow segment quickly without loading the whole project. A dedicated index makes this cheap.
2. **Tracking and audit.** Cascade runs at change time inside `linked-intent-dev`. Arrow-maintenance provides periodic re-audit to catch drift that slipped through cascade — partial cascades, inconsistent arrows left by aborted sessions, silent spec/code divergence accumulated over time — and tracks the coverage state of each segment so the project's coherence is legible between sessions.
3. **Lifecycle.** Segments split, merge, get renamed, and get re-parented as a project's understanding of its own shape matures. These operations rewrite cross-references across docs, `index.yaml`, and code; the overlay is where they are recorded so history is not erased.

The two leaf skills divide this work. `maintenance` owns navigation, tracking, audit, and the lifecycle operations on an existing overlay. `map-codebase` owns the one-time brownfield bootstrap that reverse-engineers the whole arrow — HLD, LLDs, EARS, and a conforming overlay — for a codebase that had none. Both depend on the same overlay definition — one operating an existing overlay, the other producing a conforming one — which is why that shared design lives here rather than being duplicated into each leaf.

## Plugin Structure

The plugin lives at `plugins/arrow-maintenance/`:

- `.claude-plugin/plugin.json` — manifest.
- `skills/arrow-maintenance/` — the navigation and audit skill (leaf `maintenance`). Invocable ambiently (auto-triggered on arrow-adjacent prompts when `docs/arrows/` is present) and as a slash command (`/arrow-maintenance`).
  - `SKILL.md`
  - `references/` — `index.yaml` schema, arrow-doc template, audit-checklist reference, a README template for projects to copy into their `docs/arrows/`.
- `skills/map-codebase/` — the behavioral brownfield-mapping skill (leaf `map-codebase`).
  - `SKILL.md`
  - `references/` — prompts for subagent-driven mapping runs, reconciliation templates, skeleton HLD/LLD/EARS starters.
- `commands/` — command stubs routing `/arrow-maintenance` and `/map-codebase` to their respective skills.

## Component Map

| Leaf | Segment | Skill | Concern |
|---|---|---|---|
| `maintenance` | `SCALE-MAINT` | `/arrow-maintenance` (dual-mode) | Navigation via `index.yaml`, audit-and-update of an existing overlay, lifecycle execution. Owns `docs/intent/arrow-maintenance/maintenance/maintenance-specs.md`. |
| `map-codebase` | `SCALE-MAP` | `/map-codebase` (behavioral) | One-time brownfield bootstrap — sweep, lens-based clustering, reconciliation, skeleton HLD/LLD/EARS, overlay bootstrap. Owns `docs/intent/arrow-maintenance/map-codebase/map-codebase-specs.md`. |

The leaf LLDs describe each skill's behavior in full. This sub-HLD describes the overlay and lifecycle they share, and the leaves reference back here for those concerns rather than re-specifying them.

## The `docs/arrows/` Overlay

The overlay is the shared artifact both skills produce and maintain. `map-codebase` creates it during brownfield bootstrap; `maintenance` audits, updates, and navigates it thereafter; `linked-intent-dev` writes to it during changes (see *Coordination with `linked-intent-dev`* below).

### Directory Contents

An arrow-maintained project's `docs/arrows/` contains:

- `README.md` — instructions for working with the overlay: loading order, `yq` query patterns, workflow for mapping/auditing/fixing/splitting/merging, status enum. Cloned from the skill's `references/` on bootstrap; the project may edit it.
- `index.yaml` — the manifest of the design tree.
- Per-segment arrow docs, nested in a folder structure that **mirrors the design tree under `docs/intent/`** — a leaf segment's arrow doc lives at the path mirroring its design doc (e.g., `docs/arrows/prompt-eval/runner.md` mirrors `docs/intent/prompt-eval/runner.md`), and sub-HLD (grouping) nodes are directories rather than arrow docs. At depth-2 this is a flat set of `{segment-name}.md` files.
- `_experiments/` — *reserved namespace* for experiment-produced artifacts (see *Experiment-produced artifacts* below). Not owned or audited by either skill.
- `_map-codebase/` — *reserved working area* for the brownfield bootstrap's sweep-handoff files (see the map-codebase LLD). Transient: removed at the end of a mapping run; never audited.

### `index.yaml` Schema

```yaml
schema_version: 2
last_updated: YYYY-MM-DD

taxonomy:
  {cluster-name}:
    - segment-name
    - segment-name
  {another-cluster}: standalone  # single-segment cluster

arrows:
  {node-name}:
    status: UNMAPPED | MAPPED | AUDITED | OK | PARTIAL | BROKEN | STALE | OBSOLETE | MERGED
    parent: {node-name} | null    # parent node in the design tree; null/omitted at the root level
    children: [node-name, ...]    # child nodes; present on intermediate (sub-HLD) nodes, omitted/empty on leaf segments
    sampled: YYYY-MM-DD           # when first mapped
    audited: YYYY-MM-DD | null    # when last audited (calendar date)
    audited_sha: <git-sha> | null # git head SHA at time of last audit; enables incremental audit
    blocks: [other-segment, ...]  # segments blocked by this one
    blockedBy: [other-segment, ...] # segments this one depends on
    detail: {path}.md             # the doc to open on this node — a leaf's arrow doc at its tree-mirrored path under docs/arrows/; a sub-HLD's design doc (../intent/<path>.md), since a sub-HLD has no arrow doc of its own
    next: "one-line next action or null"
    drift: "description of current drift or null"
    merged_into: {primary-segment}  # only if status is MERGED

unmapped:
  docs:
    intent: [file-name.md, ...]
```

The schema is intentionally minimal — agents query it with `yq` or simple reads. The `parent`/`children` links express the design tree's nesting (root → sub-HLDs → leaf segments); a depth-2 project simply has every node at the root level with no children, so a flat project reads as a flat list. The links are the only navigation structure for the tree — position is not duplicated elsewhere. Extensions (new status values, additional metadata per arrow) are permitted but should be added to this sub-HLD first so the schema stays coherent across projects.

The `index.yaml` schema is defined authoritatively here. Cross-plugin updates defer to this document.

### Progressive-Disclosure Navigation

The overlay exists so that an agent can orient without loading the whole project. The loading order is index-first, detail-on-demand:

1. Load `docs/arrows/index.yaml` — always a small file relative to the full project.
2. Query for the relevant segment by name, domain cluster, or status. Where the design tree nests, the index records `parent`/`children` links, so the agent walks from a grouping node down to the leaf segments it contains rather than scanning a flat list.
3. Load the per-segment arrow doc (e.g., `docs/arrows/auth.md`) only after the leaf segment is identified.
4. Load the LLD and EARS specs after that, as needed.

This keeps context tight: the agent pulls detail only down the path it actually needs. When the user is orienting broadly rather than naming a segment, summarize the `next` and `drift` fields from the index for in-flight segments rather than loading every arrow doc; where the tree nests, walk `parent`→`children` to summarize a subtree under a grouping node rather than the whole project.

### Arrow Doc Format

An arrow segment is the territory owned by one **leaf** LLD — the node in the design tree that owns EARS specs. Intermediate (sub-HLD) nodes own no EARS and no segment; they group the segments their leaf descendants own, and the arrow boundary of a segment is its leaf prefix. Each arrow segment has a markdown file in `docs/arrows/` named after the segment, at the tree-mirrored path. The file is an *orientation page*, not a design document. Standard structure:

- `# Arrow: {segment-name}` — heading and a one-line description of the segment's concern.
- `## Status` — status value + a one-sentence rationale.
- `## References` — pointers to HLD section, LLD file(s), EARS spec file(s), test file paths, code paths. Pointers only; no design content.
- `## Spec Coverage` — table of spec-ID groups with implementation status (`✓ implemented`, `? partial`, `✗ missing`) and short notes.
- Optional sections (`## Migration Notes`, `## Remaining Work`) where segment-specific context doesn't fit elsewhere.

Design detail lives in the LLD. Narrative lives in the HLD. The arrow doc is the *index view* for one segment — compact enough that an agent loading it pays a small token cost to orient. Duplicating LLD or spec content into the arrow doc creates a third source of truth that invites drift; both skills discourage it.

## Lifecycle Events

Segments evolve. The overlay supports five lifecycle events without erasing history. These operate on the shared overlay and are executed by the `maintenance` leaf (which has the richest guidance for multi-segment events); `linked-intent-dev` recognizes them mid-change and hands off here.

- **Split.** One arrow segment is discovered to contain two concerns. Create the new segment's arrow doc, move the relevant spec references and code pointers, update both docs to reference each other, record the split in `index.yaml`. If a split is detected while `linked-intent-dev` is mid-change on the affected segment, the skill asks whether to split now or defer; deferring is preferred — split at a clean break, not mid-edit.
- **Merge.** Two segments are the same thing. Pick the primary, move references from the secondary into the primary, mark the secondary as `MERGED` with a `merged_into:` field pointing at the primary. Tombstone or delete the secondary's arrow doc.
- **Rename.** A segment's name changes (e.g., `auth` → `identity`). When the segment is a leaf, its name is the leaf prefix of path-concatenated EARS IDs, so the rename rewrites every spec ID under it (`AUTH-UI-001` → `IDENTITY-UI-001`) across the spec files **and** every `@spec` annotation in code and tests that cites those IDs. Alongside the IDs, the arrow-doc filename changes, the `index.yaml` entry key changes, and every cross-reference elsewhere — `blocks`, `blockedBy`, `merged_into`, the `parent`/`children` tree links, the References sections of other segments' arrow docs, `taxonomy` membership — is updated in the same pass. Rename is not a rename-and-hope operation; the skill walks spec files, docs, `index.yaml`, and code annotations and updates them atomically within the session.
- **Re-parent.** A subtree moves to a new parent in the design tree (e.g., the `runner` leaf moves from under `prompt-eval` to under `orchestration`). Because EARS IDs are the path from root to leaf, re-parenting rewrites the path-concatenated IDs of every spec in the moved subtree (`PEVAL-RUN-014` → `ORCH-RUN-014`) and every `@spec` annotation citing them across code, tests, and docs, plus the `parent`/`children` links in `index.yaml` for the moved node and both old and new parents. Like rename, this happens atomically in one session — spec files, docs, `index.yaml`, and code annotations move together or not at all.
- **Status transition.** The natural progression is `UNMAPPED → MAPPED → AUDITED → OK`, with optional detours (`PARTIAL`, `BROKEN`, `STALE`, `OBSOLETE`). Timestamps (`sampled`, `audited`) and the `audited_sha` record when each transition happened so staleness can be measured.

Rename and re-parent are the **tooled, atomic restructuring operation** the namespace decision assigns to this plugin: path-concatenated EARS IDs are stable under ordinary growth and change *only* under a deliberate re-parent or rename, and when they change this plugin is the owner that rewrites spec files, docs, `index.yaml`, and `@spec` annotations together. A partial application — IDs renamed in the spec file but not in code — is exactly the cross-reference rot the atomicity requirement exists to prevent.

## Coordination with `linked-intent-dev`

Both `linked-intent-dev` and the `maintenance` skill may be consulted in the same session, and both write to the overlay. The ownership split governs who writes `index.yaml` and the arrow docs when:

- `linked-intent-dev` handles per-change workflow (HLD → LLD → EARS → Tests → Code). When it changes a segment, it also updates that segment's arrow doc and the relevant `index.yaml` entry — status transitions, `next`, `drift`, `audited_sha` on completion — because it already has the segment's context loaded.
- `arrow-maintenance` (the `maintenance` leaf) handles systematic audit and drift detection across segments, and owns the atomic lifecycle operations. It does not perform change workflows; it observes, reports, and nudges the user toward correction.

Linked-intent-dev is authoritative for *changes*; arrow-maintenance is authoritative for *state of coverage*. They share artifacts but own different questions. Coordination is implicit: both are consulted when their triggers match, and neither overrides the other.

| Concern | Owner |
|---|---|
| Per-change HLD/LLD/EARS/test/code work | linked-intent-dev |
| Cascade at change time | linked-intent-dev |
| Arrow doc updates during a change (add coverage rows, refresh status) | linked-intent-dev (segment is already in context) |
| `index.yaml` status updates during a change | linked-intent-dev |
| `unmapped.docs` cleanup | arrow-maintenance during audit; linked-intent-dev when it notices an unmapped doc it can assign in passing |
| Systematic audit across segments | arrow-maintenance |
| Drift detection between sessions | arrow-maintenance |
| Brownfield mapping | arrow-maintenance (`map-codebase`) |
| Overlay bootstrap on existing LID projects | arrow-maintenance (`maintenance`, command mode) |
| Lifecycle events (split, merge, rename, re-parent, status transitions) | Either skill, depending on context; arrow-maintenance has richer guidance for multi-segment events and owns the atomic rename/re-parent operation that rewrites path-concatenated EARS IDs and their `@spec` annotations across docs and code |

### Authoritative Sources

When information is duplicated across artifacts, the authority rule is:

- **Segment status, `sampled`/`audited`/`audited_sha` timestamps, `next`, `drift`, `blocks`/`blockedBy` graph, `merged_into`** — `index.yaml` is authoritative.
- **Per-segment arrow doc's `## References` section, `## Spec Coverage` table** — derived views. Regenerated from source-of-truth scans (grep for `@spec`, file existence checks, eval-citation checks) during audit. Never hand-edited to contradict the source scans.
- **Spec-file header format** (the `LLD:` pointer and `Implementing artifacts:` list used in the LID-on-LID inversion) — defined authoritatively in `docs/intent/linked-intent-dev/linked-intent-dev-design.md`. The reference-coherence audit uses that schema; changes to the schema happen there and propagate here.
- **`@spec` annotation placement rule** (entry point of the behavior's implementation graph) — also defined authoritatively in `docs/intent/linked-intent-dev/linked-intent-dev-design.md`.
- **`index.yaml` schema itself** — defined authoritatively in this sub-HLD. Cross-plugin updates defer to this document.

## Experiment-produced Artifacts (reserved namespace)

The `docs/arrows/_experiments/` subtree is reserved for artifacts produced by `lid-experimental` plugin skills that want to attach per-segment or per-EARS experiment state to the arrow overlay. The subtree is **not owned by either arrow-maintenance skill** — each experiment owns its own namespace inside it and is responsible for creating, updating, and removing its own artifacts.

The leading underscore keeps reserved overlay subtrees out of the segment namespace — segment names are never underscore-prefixed — so they cannot collide with a project's own segments now that intent nests. The same rule and audit exemption cover `docs/arrows/_map-codebase/`, the brownfield bootstrap's transient sweep-handoff area (owned by the map-codebase LLD, removed at the end of a mapping run).

Convention:

```
docs/arrows/_experiments/<experiment-name>/<segment-path>/<artifact>.md
```

- `<experiment-name>` — the `lid-experimental` skill's directory name (e.g., `bidirectional-differential`). Each experiment gets its own peer directory.
- `<segment-path>` — the arrow segment the artifact applies to, mirroring the tree-structured path used for the segment's arrow doc under `docs/arrows/`.
- `<artifact>.md` — experiment-specific shape. Typically one file per EARS, but experiments may choose their own leaf structure.

**Audit behavior**: the `maintenance` skill (both ambient and command modes) **ignores** the `_experiments/` subtree. It does not audit, clean up, or regenerate files under it. Reference-rot and spec-to-code drift checks scan arrow docs and code; they do not scan `_experiments/`.

**Lifecycle**: when an experiment is retired, its entire `docs/arrows/_experiments/<experiment-name>/` subtree is removed in the same commit that removes the experiment from `lid-experimental`. When an experiment is promoted into a core plugin, the subtree either migrates into core ownership (this sub-HLD's schema gets extended to track the artifact type formally) or is removed in favor of a first-class schema entry. That decision is made at promotion time, not in advance.

**`index.yaml` coordination**: `arrows.<segment>.experiments` is a reserved key. If a future experiment needs per-segment metadata tracked in `index.yaml` (e.g., "last audit date" for an experiment's artifacts), that experiment proposes the sub-schema at promotion review and this sub-HLD extends `index.yaml` then. Until then, experiments keep their state in the `_experiments/` subtree only.

Active experiments at this document's current version:

- `bidirectional-differential` — see `docs/intent/lid-experimental/bidirectional-differential/bidirectional-differential-design.md`. Uses `docs/arrows/_experiments/bidirectional-differential/<segment-name>/<EARS-ID>.md`.
- `review-depth` — see `docs/intent/lid-experimental/review-depth/review-depth-design.md`. Uses `docs/arrows/_experiments/review-depth/<segment-name>/fork-log.md`.

## Decisions & Alternatives

| Decision | Chosen | Alternatives Considered | Rationale |
|---|---|---|---|
| arrow-maintenance as a sub-HLD over two leaf LLDs | Sub-HLD owning no EARS, with `maintenance` and `map-codebase` as leaf LLDs beneath it | Collapse both skills into one LLD (as before); leave the two skills as unrelated sibling LLDs under the root HLD | Both skills ride on one shared design — the `docs/arrows/` overlay, its schema, the navigation model, and the lifecycle operations. That shared design is HLD-shaped intent for the subtree, so it belongs in a parent node both leaves inherit rather than being duplicated into two siblings or buried in one oversized LLD. Collapsing the two loses the clean per-skill EARS ownership (`SCALE-MAINT` vs `SCALE-MAP`) and makes the combined doc too thick. Leaving them as unrelated siblings forces the overlay schema to live in one of them with the other referencing across — an asymmetry that invites drift. A sub-HLD makes the shared layer first-class and the two skills genuine peers. |
| Audit as prose guidance vs. a command | Prose guidance (ambient) + behavioral command mode | `/audit-arrow` command; scheduled audit hook | Minimum system. Ambient guidance biases navigation; command mode gives a directed, eval-gateable audit-and-update pass. A separate audit command would be redundant surface. (Detailed in the `maintenance` leaf.) |
| Arrow doc content | Pointers + coverage table, no design | Include design excerpts; include full spec text | Design lives in the LLD; specs live in spec files. Duplicating either into the arrow doc creates a third source of truth and invites drift. Pointers-only keeps the arrow doc compact and stable. |
| Status enum | Full Threadkeeper set | Simpler binary (mapped / not); richer taxonomy | Matches working practice on a real long-running LID project. The enum carries real semantic distinctions — "AUDITED" (we know the state) is not the same as "OK" (it is fixed). Simpler enums lose this distinction. |
| Coordination with linked-intent-dev | Ownership table, implicit runtime coordination | Explicit handoff protocol; merging into one skill | Two skills with different triggers. Merging would make the combined skill too thick for small projects that do not need the overlay. |
| Overlay activation signal (ambient) | Presence of `docs/arrows/` directory | CLAUDE.md flag; plugin config; explicit enablement command | The directory either exists or doesn't; this is the cheapest detection signal and requires no additional convention. |
| Audited state tracking | `audited` (date) + `audited_sha` (git SHA) | Date only; SHA only | Date is human-readable for staleness judgment; SHA enables incremental audit on subsequent runs, which is a large performance win on big projects. Both are cheap to store. |
| Rename and re-parent as lifecycle events | First-class; the plugin rewrites path-concatenated EARS IDs, `@spec` annotations, docs, and `index.yaml` atomically in one session | Manual find-replace; not supported events; ID rewrite left to the user | The namespace decision makes path-concatenated IDs stable except under a deliberate re-parent or rename, and assigns that tooled operation to this plugin. Because the ID *is* the tree path, a rename or re-parent changes IDs in spec files and every `@spec` annotation citing them in code and tests — a partial application is exactly the cross-reference rot atomicity prevents. Splits and merges already warrant first-class treatment; these are the operations the path-ID model makes mandatory to do atomically. |
| `index.yaml` schema home | This sub-HLD (owns the shared overlay design) | A leaf LLD; the root HLD | The schema is the shared contract both leaves and `linked-intent-dev` write against. The sub-HLD is the lowest node that sees the whole overlay, so it is the natural authority; placing it in a leaf would force the sibling and the core plugin to reference across leaves. |

## Open Questions

### Resolved

1. ✅ arrow-maintenance is a sub-HLD over two leaf LLDs: `maintenance` (dual-mode `/arrow-maintenance`) and `map-codebase` (brownfield bootstrap). The sub-HLD owns the shared overlay design and no EARS.
2. ✅ `docs/arrows/` contains `index.yaml`, per-segment arrow docs at tree-mirrored paths, a `README.md` template, and a reserved `_experiments/` subtree. Anchored at project root, one overlay per project.
3. ✅ `index.yaml` schema (including `parent`/`children` tree links and the `audited`/`audited_sha` staleness fields) is defined authoritatively here.
4. ✅ Lifecycle events (split, merge, rename, re-parent, status transition) operate on the shared overlay and are described here; rename and re-parent rewrite path-concatenated EARS IDs and their `@spec` annotations atomically.
5. ✅ Arrow doc updates flow through `linked-intent-dev` during changes; arrow-maintenance re-audits and cleans up `unmapped.docs` on its runs.
6. ✅ The `_experiments/` subtree is a reserved namespace owned by `lid-experimental`, ignored by both arrow-maintenance skills.

### Deferred to implementation

1. **Status enum extension.** When a project wants a status value the default enum does not carry, how is that added? Likely by editing the project's own `docs/arrows/README.md`, but whether and how the skill surfaces the customization is TBD.
2. **Taxonomy evolution.** `index.yaml` taxonomy is human-authored at mapping time. How does it stay current as the project grows? Likely by `linked-intent-dev` nudging the user when a new segment doesn't fit the existing taxonomy, but the mechanics are undecided.
3. **Orphan artifact handling at scale.** Bulk reporting is the direction, but sizing (how many orphans before the report needs pagination or grouping) matters. To be refined on a real mid-sized project.

## References

- `docs/high-level-design.md` — the root HLD; describes when arrow-maintenance becomes load-bearing and its relationship to the core plugin.
- `docs/intent/arrow-maintenance/maintenance/maintenance-design.md` — leaf LLD for the dual-mode `/arrow-maintenance` skill (segment `SCALE-MAINT`).
- `docs/intent/arrow-maintenance/map-codebase/map-codebase-design.md` — leaf LLD for the `/map-codebase` brownfield-bootstrap skill (segment `SCALE-MAP`).
- `docs/intent/linked-intent-dev/linked-intent-dev-design.md` — core plugin LLD; the ownership split is specified there as well, and the spec-file header / `@spec` placement schemas this overlay's audit relies on are authoritative there.
- `/Users/jess/src/personal-log/docs/arrows/` — the working reference implementation this design is modeled on.
