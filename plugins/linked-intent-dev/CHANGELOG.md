# Changelog

All notable changes to LID (Linked-Intent Development) are recorded here. The format follows [Keep a Changelog](https://keepachangelog.com/); LID uses [Semantic Versioning](https://semver.org/). This file is the single human-readable record of the current release — the plugin manifests carry the matching version, and `linked-intent-dev`'s version is the canonical "LID conventions" version a project records as the `- Version:` bullet in the `## LID` block.

## [No Version Update Required]

*Changes merged since the latest numbered version that did not require a version bump (per the policy in `docs/high-level-design.md` § Architecture / Distribution / What warrants a version change). These fold into the next numbered version's entry when one is cut.*

### Changed

- **HLD: linkage's payoff named as two-fold — navigation and attestation.** § Approach: Linkage-based Intent Tracking now states that the same identifiers that make the arrow walkable in tokens make its coherence checkable by grep (the traceability-matrix property), and that the two payoffs age differently as agent capability grows. Glossary gains an *Attestation* entry. Positioning only — no convention, command, or project-facing behavior changes.
- **Marketing arrow: attestation story, copy-effectiveness pass, and Teams section.** The site's How-it-works carries the verification claim, a not-a-waterfall statement, and an honest cost passage; the hero lede leads pain-first with vocabulary deferred (show-then-name); a new Home Teams section (intent PRs, onboarding-by-cold-read, mixed-tool shared truth, scoped sub-team adoption, hotfix-then-remerge) sits between the demo and Quickstart with a design-diff figure; the README body states both linkage payoffs. `MKT-SITE-055`–`064` added; stale five-panel-trace markers corrected.

## [1.3.0] — 2026-06-06

The memory-coherence release: durable project knowledge is redirected from agent memory into the arrow, and the definition of a tenet is sharpened to exclude specs in disguise.

### Added
- **Memory→intent directive in the instruction file.** Bootstrap and reconcile-conventions now write a tool-agnostic *Memory vs. intent* directive into the always-loaded instruction file (`AGENTS.md`/`CLAUDE.md`): before saving durable project knowledge to any agent/tool memory, the agent tests whether it is project *intent* (would a fresh agent, in any tool, next session, need it to build the system right?) and, if so, records it in the arrow rather than memory. It lives in the instruction file because that is the only artifact reliably in context at memory-save time — the HLD, where the rationale lives, is not. (`LID-UPDATE-047`)
- **Tenet-quality coach lens for spec-shaped tenets.** `/lid-coach` now flags a `## Tenets` entry that is a triggered `when X, do Y` rule — a spec masquerading as a tenet — and recommends routing it to EARS. (`LID-COACH-057`)
- **Cursor as a first-class plugin host.** The repository ships `.cursor-plugin/` marketplace and per-plugin manifests that reuse the same `skills/`/`commands/` source Claude Code reads, so Cursor installs the LID plugins with auto-invoking skills — not just the rule-file adapter. `docs/setup.md`'s Cursor section now leads with the plugin install; the `.cursor/rules/lid.mdc` adapter stays as the lighter no-plugin alternative. The Cursor manifests carry no `version`. (HLD § Key Design Decisions / *Cursor as a first-class plugin host*)

### Changed
- **The definition of a tenet is sharpened with a second test.** Beyond the *defensible opposite* (a tenet is not a platitude), a tenet must be a **class-level lean, not a triggered rule**: a candidate phrased as `when X, do Y` with a definite outcome is a spec — routed to EARS — even when its opposite is defensible. *A tenet says which way to lean; a spec says what to do; a Key Design Decision records what was already chosen.* Applied across the HLD, the HLD template, and the `linked-intent-dev` elicit-tenets step. (`LID-CORE-039`)
- **Bootstrap defaults to `AGENTS.md` — by preference, not mandate.** `/update-lid` (and the `/linked-intent-dev` Phase-1 bootstrap) now create `AGENTS.md` as the instruction file with a `CLAUDE.md` symlink alias (or a one-line `@AGENTS.md` import where symlinks are unavailable, e.g. Windows without Developer Mode) so Cursor and other `AGENTS.md`-native agents read the `## LID` block too. The skills read whichever instruction file a project presents — `AGENTS.md` or `CLAUDE.md` — and an existing `CLAUDE.md` project is kept in place, never migrated. No host detection, and no required change for any existing project.

### Migration (v1.2 → v1.3)
- **Add the memory→intent directive (mechanical).** Run `/update-lid`; reconcile-conventions detects that the instruction file's directives are missing the *Memory vs. intent* paragraph and adds it. No-op if already present.
- **Review existing memory for escaped intent (judgment).** As a one-time retroactive application of the new directive, review the project's existing agent/tool memory for durable project knowledge that is really *intent* — anything a fresh agent in any tool would need to build the system right — and extract it into the arrow (HLD/LLD/EARS/decision doc), leaving only user/working-relationship knowledge in memory. `/update-lid` surfaces this as a judgment step; it does not read your memory for you.
- **Review existing tenets for spec-shaped ones (judgment).** As a one-time retroactive application of the sharpened definition, sweep each `## Tenets` entry for a triggered `when X, do Y` rule masquerading as a tenet and route any you find to EARS (an entry stays a tenet only if its opposite is defensible *and* it is a class-level lean, not a triggered action). `/lid-coach`'s tenet-quality lens now surfaces these on every review; this migration prompts the one-time sweep. Genuine tenets stay valid and need no change.
- **Cursor / `AGENTS.md` bootstrap: no change required.** Additive — existing projects keep their current instruction file as-is.

### Plugin versions
`linked-intent-dev` 1.3.0 · `arrow-maintenance` 1.2.0 · `lid-experimental` 0.2.0

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
- **Multi-prefix nodes are a transient migration marker, not a stable state.** Mapping a pre-1.2 flat spec file onto one node can surface several ad-hoc ID prefixes on a single leaf — record them as a `prefix:` array to mark the node unresolved, then treat each such node as a **judgment step** (not mechanical). Resolve it to a single scalar prefix by one of three moves: **collapse** (the extras are cross-cutting concerns or requirement types of one intent → keep one leaf, fold them into `<LEAF>-<TYPE>` facets; the common case), **promote** (the extras share parent intent a parent doc should hold → a sub-HLD over child leaves), or **split** (the extras are distinct intents with no shared parent → sibling leaves). Aim to clear every `prefix:` array during the walk; `/update-lid` surfaces each with a recommended move and, if you defer one, keeps it as the unresolved marker and re-surfaces it on later runs (see *How `/update-lid` drives the walk*, below). Make the structural call on intent alone; the `@spec` ID rewrites a resolution implies can be deferred and sequenced separately — rename cost informs *when*, never *what*.
- **How `/update-lid` drives the walk.** The skill surfaces every transient marker — an un-relocated LLD (a node folder holding more than its `<node>-design.md` + optional `<node>-specs.md` pair) or a `prefix:` array — in the project's own terms with a recommended collapse/promote/split, applies it only on approval, and never silently leaves or auto-resolves one. It advances the project's `- Version:` once the defining structural move (the `docs/intent/` node-as-folder relocation) is done — not pinned to the prior version while residual cleanup is deferred — and reports what remains; reconcile-conventions then re-surfaces any persisting marker, and normalizes a malformed `## LID` block in place, on later runs independent of version lag.
- **No `@spec` ID rewrite is needed in an adopting project.** Your existing flat or `{FEATURE}-{TYPE}-{NNN}` IDs stay valid — the re-admitted within-leaf type segment keeps them so. (The internal segment renames in this release — `ARROW-MAINT→SCALE-MAINT`, `MAP-CODE→SCALE-MAP`, `BIDIFF→EXP-BIDIFF`, `UPDATE-LID→LID-UPDATE` — are LID restructuring its own docs, not a step adopters perform.)
- **Doc-layout migration (node-as-folder + `docs/intent/`):** rename `docs/llds/` → `docs/intent/`, then give each LLD and sub-HLD its own folder — the design doc as `<name>-design.md`, with a leaf LLD's specs beside it as `<name>-specs.md` (moved out of `docs/specs/`, which goes away). The grouping unit is the **leaf LLD**: the design tree is authoritative, and the arrow overlay mirrors it rather than defining it. A flat depth-2 project is a one-level move per LLD (`docs/intent/<feature>/<feature>-design.md` + `<feature>-specs.md`). `@spec` IDs and code are untouched, but the move also rewrites **doc-internal path references** — each spec file's `**LLD**:` header, arrow-doc `detail:` paths, any LLD/spec index docs — and bumps `docs/arrows/index.yaml` `schema_version` to `2`. The agent performs these moves and rewrites through `/update-lid` version-walk, propose → confirm → apply. A project whose arrow segments aren't already one-to-one with its LLDs (shared or orphaned docs, segments spanning several LLDs) hits reconciliation choices first — surfaced for confirmation in the project's own terms, not mechanical.
- **Reserved overlay subtree rename (only if present):** if the project has a `docs/arrows/experiments/` subtree — present only in projects that have run `lid-experimental`'s `bidirectional-differential` — rename it to `docs/arrows/_experiments/`. The underscore is the sigil `arrow-maintenance` keys its audit-exclusion on; without the rename, the upgraded `arrow-maintenance` no longer recognizes the reserved subtree and starts flagging the experiment's audit records as orphan artifacts / reference rot. Mechanical, and a no-op for the majority of projects (the directory does not exist).
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
