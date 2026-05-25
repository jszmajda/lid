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

## [1.1.0] — 2026-05-18

The tool-agnostic release: LID stops being a Claude Code plugin and becomes a methodology any agentic coding tool can run, gets tenets as a first-class design element, and splits its core plugin into purpose-built skills.

### Added
- **Tenets as a first-class HLD element.** The HLD now carries explicit, named tenets — durable design principles that cascade downward and that the new `lid-coach` skill reviews a project against. (`b228892`, `7b51ff6`)
- **`lid-coach` skill** (in `linked-intent-dev`) — a principle-review coach that checks a project's LID usage against its tenets, separate from the build workflow.
- **Tool-agnostic positioning.** LID is reframed from "Claude Code plugin" to a methodology that runs on any agent reading per-project instructions. `docs/setup.md` ships per-tool adapter instructions for Cursor, Windsurf, GitHub Copilot, Aider, Continue, JetBrains Junie, Zed, Codex, Amp, Jules, Cline, and Pi, anchored on the cross-tool `AGENTS.md` convention. (`e268813`, `0caaaa0`, `b16049b`)
- **`lid-experimental` plugin** (0.1.0) with the **`bidirectional-differential`** skill — round-trip EARS↔code coherence auditing via parallel fresh sessions; the home for more formal coherence-check research. (`b64c439`, `c1944e7`)
- **`CONTRIBUTING.md`** and a `project-structure` arrow segment documenting the repo's own layout. (`ee7bd51`)
- **Marketing site "How It Works"** — a five-panel trace of the arrow (HLD → LLD → EARS → Tests → Code) plus a tool chip row on the home quickstart. (`3958dcd`, `4696491`, `9e714f8`)

### Changed
- **`linked-intent-dev` plugin restructured into three skills** — the monolithic workflow split into `/linked-intent-dev` (build), `/update-lid` (reconcile drift / change modes, absorbing the former `lid-setup`), and `/lid-coach` (principle review). (`1eedf56`, `34ce002`)
- **Truth tenet refined** — the fresh-author test, three residues, and a locality convention for where rationale lives. (`a2a1558`)
- `arrow-maintenance` overlay bootstrapped on LID's own docs, reconciling `BIDIFF` markers. (`e2abcfc`)

### Fixed
- **Firefox Android DAG/hero paint bugs** on the marketing site — soft-reload rects failing to fill, traced to an SVG size threshold and nested-opacity compositing; resolved with uniform 70×30 rects and an attribute-only fill pattern. (`3c129a2`, and the `2382044`→`2aa4f33` diagnostic series)
- Mobile overflow and hero SVG dark-mode rendering. (`66c25db`, `bf92642`)

### Migration (v1.0 → v1.1)
- **No doc or spec format changes.** Existing HLD, LLD, EARS, `@spec` annotations, and status markers stay valid — this release is additive at the methodology level.
- **Re-install the plugins** to pick up the three-skill split. The former `lid-setup` command is gone; **bootstrapping and reconciliation now both run through `/update-lid`**. `/linked-intent-dev` (build) and the new `/lid-coach` (principle review) round out the set.
- **Tenets are opt-in.** Existing projects gain nothing automatically; add a tenets section to your HLD when you want `/lid-coach` to review against it.
- **Other agentic tools (new):** non-Claude-Code users follow `docs/setup.md` to ship an `AGENTS.md` (and any tool-specific adapter). Existing Claude Code users need no change.

### Plugin versions
`linked-intent-dev` 1.1.0 · `arrow-maintenance` 1.1.0 · `lid-experimental` 0.1.0

## [1.0.0] — 2026-04-18

First public release — LID as two installable Claude Code plugins, dogfooded on its own docs.

### Added
- **`linked-intent-dev` plugin** — the core design-before-code workflow (HLD → LLD → EARS → tests → code) as an auto-invoking skill, plus a `lid-setup` skill/command for bootstrapping LID into a project and an `update-lid` command for reconciling it.
- **`arrow-maintenance` plugin** — the scaling overlay that tracks spec-to-code coherence across large projects via a `docs/arrows/` index, plus **`/map-codebase`** for brownfield bootstrap (mapping an existing codebase into LID).
- **EARS specifications** with `@spec` code annotations and status markers (`[x]` implemented, `[ ]` gap, `[D]` deferred) for HLD→code traceability.
- **LID-on-LID dogfooding** — the repo's own `docs/` tree authored as LID applied to LID, serving as the canonical reference.
- **Marketing site** and the source-language positioning of the methodology.

### Migration
- First public release — nothing to migrate. Install with `/plugin marketplace add jszmajda/lid`, then `/plugin install linked-intent-dev@jszmajda-lid` and `/plugin install arrow-maintenance@jszmajda-lid`.
