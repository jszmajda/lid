# Changelog

All notable changes to LID (Linked-Intent Development) are recorded here. The format follows [Keep a Changelog](https://keepachangelog.com/); LID uses [Semantic Versioning](https://semver.org/). This file is the single human-readable record of the current release — the plugin manifests carry the matching version, and `linked-intent-dev`'s version is the canonical "LID conventions" version a project records as the `- Version:` bullet in the `## LID` block.

## [1.2.0] — 2026-05-25

The recursive-intent-tree release: the design layer becomes a tree, EARS IDs become path-concatenated, and decisions get a first-class artifact.

### Added
- **Recursive design tree.** The design layer is a tree of arbitrary depth, not a fixed HLD→LLD two-rung. "HLD" and "LLD" are roles by position; a leaf that outgrows itself promotes into a **sub-HLD** (HLD-shaped, owns no EARS) parenting child LLDs. Depth-2 remains the default. A sub-HLD is earned by shared parent intent a parent doc should hold; a merely categorical grouping is a *taxonomy label*, not a sub-HLD, and its members stay flat. (`docs/decisions/recursive-intent-tree.md`)
- **Path-concatenated EARS IDs.** A spec ID is the root-to-leaf path, plus an optional within-leaf type/area facet, plus a number (`PEVAL-RUN-014`, `AUTH-UI-001`). `grep PREFIX` gathers a subtree by construction. (`docs/decisions/namespace-structure.md`)
- **Decision docs** — a sanctioned artifact for contested decisions, in a node's `decisions/` directory; carries no `status` field.
- **Design-node frontmatter** — `parent:` and `prefix:` on design docs. `prefix:` is the bridge from a human-readable doc name to its EARS namespace (they need not match).
- The **`verticalize intent`**, **`LID runs on the agent, not a runtime`**, and **`Speak the project's language`** tenets, the **placement rule** (intent attaches at the lowest dominating node; substance-vs-cascade), and **re-parent** as a tooled, atomic arrow-maintenance lifecycle event.

### Changed
- `docs/arrows/index.yaml` schema → **v2**: adds `parent`/`children` design-tree links; `detail` is now "the doc to open on this node" (a leaf's arrow doc, or a sub-HLD's design doc).
- Reserved overlay subtree renamed `docs/arrows/experiments/` → `docs/arrows/_experiments/`.
- `arrow-maintenance` opened into a sub-HLD (`SCALE`) over `maintenance` (`SCALE-MAINT`) and `map-codebase` (`SCALE-MAP`); `lid-experimental` roots the `EXP` namespace (`EXP-BIDIFF`). The core plugin `linked-intent-dev` opened into the `LID` sub-HLD over three leaves — `core` (`LID-CORE`, the workflow skill, now spec'd), `update-lid` (`LID-UPDATE`), and `lid-coach` (`LID-COACH`).
- **Doc tree restructured to node-as-folder.** Every design node is now a directory holding `{node}-design.md` (plus `{node}-specs.md` if it owns EARS, a `decisions/` dir if any, and child folders if it is a sub-HLD). The separate top-level `docs/specs/` directory is **eliminated** — a node's specs live beside its design doc — and the design-tree root directory is renamed `docs/llds/` → **`docs/intent/`** (it holds sub-HLDs, leaf LLDs, their specs, and decision docs, so "llds" no longer described it). The HLD stays at `docs/high-level-design.md` as the tree's root.

### Migration (v1.1 → v1.2)
- **Flat depth-2 projects: no change required.** Existing IDs stay valid; nesting and node frontmatter are opt-in.
- **Nested / large projects:** backfill `parent:`/`prefix:` frontmatter, formalize any ad-hoc sub-HLD, and bump `index.yaml` `schema_version` to `2`. Adopt incrementally; `/update-lid` reconciles each project forward.
- **No `@spec` ID rewrite is needed in an adopting project.** Your existing flat or `{FEATURE}-{TYPE}-{NNN}` IDs stay valid — the re-admitted within-leaf type segment keeps them so. (The internal segment renames in this release — `ARROW-MAINT→SCALE-MAINT`, `MAP-CODE→SCALE-MAP`, `BIDIFF→EXP-BIDIFF`, `UPDATE-LID→LID-UPDATE` — are LID restructuring its own docs, not a step adopters perform.)
- **Doc-layout migration (node-as-folder + `docs/intent/`):** rename `docs/llds/` → `docs/intent/`, then give each LLD and sub-HLD its own folder — the design doc as `<name>-design.md`, with a leaf LLD's specs beside it as `<name>-specs.md` (moved out of `docs/specs/`, which goes away). The grouping unit is the **leaf LLD**: the design tree is authoritative, and the arrow overlay mirrors it rather than defining it. A flat depth-2 project is a one-level move per LLD (`docs/intent/<feature>/<feature>-design.md` + `<feature>-specs.md`). `@spec` IDs and code are untouched, but the move also rewrites **doc-internal path references** — each spec file's `**LLD**:` header, arrow-doc `detail:` paths, any LLD/spec index docs — and bumps `docs/arrows/index.yaml` `schema_version` to `2`. The agent performs these moves and rewrites through `/update-lid` version-walk, propose → confirm → apply. A project whose arrow segments aren't already one-to-one with its LLDs (shared or orphaned docs, segments spanning several LLDs) hits reconciliation choices first — surfaced for confirmation in the project's own terms, not mechanical.
- **Custom coherence-check script:** a project that runs its own coherence-check script (declared under `## LID Tooling`) may need to update it to handle path-concatenated IDs and the `## LID` block.

### Plugin versions
`linked-intent-dev` 1.2.0 · `arrow-maintenance` 1.2.0 · `lid-experimental` 0.2.0
