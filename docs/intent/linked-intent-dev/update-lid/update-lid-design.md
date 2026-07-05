---
parent: linked-intent-dev
prefix: LID-UPDATE
---

# LLD: update-lid Skill

## Context

This leaf LLD covers the behavioral `update-lid` skill, which puts a project into a LID-ready state and reconciles its configuration over time. Plugin-level concerns shared across the core plugin's three skills — mode detection mechanics, spec-ID format, and eval-metadata conventions — live in the parent `LID` sub-HLD at `docs/intent/linked-intent-dev/linked-intent-dev-design.md`.

## The `update-lid` Skill (behavioral)

### Intent

Put a project into a LID-ready state. On first run, bootstrap the required directory structure and inject LID directives into the project's agent-instructions file. On subsequent runs, reconcile the project's current state with the conventions LID expects and, if requested, migrate between modes. The instruction file the skill reads and writes is defined under *Instruction-file anchor* below.

### Instruction-file anchor

LID's per-project directives, the `## LID` block, and the navigation table live in the project's **agent-instructions file**. That file is **`AGENTS.md`** — the canonical, cross-tool convention that Cursor and most agents read natively — with **`CLAUDE.md` as a symlink alias** so Claude Code (which reads `CLAUDE.md`) sees identical content. The skill never branches on which host it runs under (HLD § Key Design Decisions / *Cursor as a first-class plugin host*):

- **Reading** (detect directives, mode, version, drift): operate on whichever instruction file the project presents — `AGENTS.md` if present, otherwise `CLAUDE.md`. With the symlink, the two resolve to one file.
- **Writing on fresh bootstrap**: create `AGENTS.md` as the canonical file plus a `CLAUDE.md` symlink pointing at it. The symlink is preferred — one file, both names, zero drift, no precedence surprises. Where a project cannot use symlinks (notably Windows without Developer Mode), the documented alternative is a `CLAUDE.md` whose **sole** content is a one-line `@AGENTS.md` import (see `docs/setup.md`); keeping it to that one line sidesteps Claude Code's import-precedence rule, under which content written directly in `CLAUDE.md` outranks imported content. Claude Code does not yet read `AGENTS.md` natively, so one of these bridges is required for it.
- **Writing to an existing instruction file**: update it in place. A project that already centers `CLAUDE.md` (an existing Claude-only LID project) keeps `CLAUDE.md` as its file — the skill reconciles its content and does not force a migration to `AGENTS.md`.

Throughout this LLD, *the instruction file* means the file selected by these rules.

### Invocation

The skill is invoked as `/update-lid`. A fresh-project user instead reaches for `/linked-intent-dev` (the workflow skill) and gives a description of what they want to build; the workflow's Phase 1 detects the unconfigured state and applies this skill's bootstrap branch as a sub-step before drafting the HLD. Users who already have LID configured and need to reconcile drift, change mode, or refresh conventions invoke `/update-lid` directly. The skill is also reachable as a sub-step from `/map-codebase` at its terminal verification step.

### State dispatch

On invocation, the skill inspects the project:

| Detected state | Action |
|---|---|
| No instruction file, no `docs/` | Full bootstrap — create directories, create `AGENTS.md` (with a `CLAUDE.md` symlink alias) carrying LID directives and a `## LID` block with `- Mode:` and `- Version:` (the installed `linked-intent-dev` version), and offer the vendored workflow doc (see *Workflow-doc vendoring and sync*). |
| Instruction file exists, no LID directives | Append LID directives to the existing instruction file; create `docs/` if missing. |
| LID directives present, no well-formed `## LID` block (absent or malformed) | Add or normalize the block in place — a bare `## LID` heading with `- Mode:` (default Full) and `- Version:` the installed version; rewrite a malformed block rather than appending a second. |
| Project `- Version:` lower than the installed version (or `- Version:` absent → predating versioned conventions) | Version-walk (see below) — walk the intervening CHANGELOG migrations, propose → confirm → apply, refresh `- Version:`. |
| LID directives present, `## LID` block at the installed version, no mode change requested | Reconcile conventions — check for convention drift (e.g., missing directories, outdated instruction-file template sections) and offer targeted updates. |
| Fully configured, no drift, version current, no mode change | Inform the user what was detected and exit without changes. |
| Mode change requested | Run mode transition (see below). |

Version-walk is evaluated ahead of reconcile-conventions: a lagging project is first brought to the current conventions version, then ordinary drift reconciliation runs against those conventions.

### Detection signals

The skill detects state via specific signals rather than heuristics:

- **LID directives present** — `grep` for the literal strings `"linked-intent-dev"` or `"Linked-Intent Development"` in the instruction file. Either string matches; both indicate directives already present.
- **LID metadata block present** — `grep` for a `## LID` heading in the instruction file. The block carries the project's LID metadata as bullets: `- Mode: {Full|Scoped}` (case-insensitive on the mode name, whitespace tolerated) and `- Version: {X.Y.Z}`. The `- Version:` bullet is the `linked-intent-dev` plugin version the project's docs conform to. A `## LID` block with no `- Version:` bullet marks a project **predating versioned conventions** (walk from the start). Mode and version detection both read this block; it is the sole source of truth for each.
- **Project version vs. installed version** — read `- Version:` and compare it to the installed `linked-intent-dev` plugin version (the `version` field in `plugins/linked-intent-dev/.claude-plugin/plugin.json`, the canonical LID conventions version). A lower project version means the project lags and version-walk applies.
- **Arrow-maintenance overlay present** — `docs/arrows/` directory exists in the project root.
- **Convention drift** — required directories missing (`docs/intent/`, `docs/high-level-design.md`); instruction-file template sections do not match the current template version, including a malformed `## LID` block (heading other than a bare `## LID`, mode merged into the heading, or a missing `- Mode:`/`- Version:` bullet); a node folder holding more than its `<node>-design.md` plus optional `<node>-specs.md` pair (an LLD not yet relocated into its own node folder); or a design doc whose `prefix:` frontmatter is an array. The structural-marker categories (overloaded node folder, `prefix:` array) are detected independently of version lag, so a project already at the installed version still has deferred markers re-surfaced.

These signals are the authoritative detection rules. The skill does not guess or use fuzzy matching.

### Version-walk

A project records the `linked-intent-dev` version its docs conform to in its `## LID` block's `- Version:` bullet. The canonical LID version is the `version` in `plugins/linked-intent-dev/.claude-plugin/plugin.json`. When the project version is lower than the installed version — or absent, in which case the project predates versioned conventions and is walked from the start — the skill walks the project forward.

The migration source is the CHANGELOG at `plugins/linked-intent-dev/CHANGELOG.md` (the root `CHANGELOG.md` symlinks to it). The CHANGELOG is part of the core plugin and is owned by `docs/intent/project-structure/project-structure-design.md`; this skill consumes it. Each release entry carries a **`### Migration (vX → vY)`** section describing the doc-level steps to move a project forward by one release. The skill reads each intervening release's Migration section, in ascending order, and reconciles the project against it.

Reconciliation follows the skill's existing propose → confirm → apply discipline — it never silently rewrites:

- **Mechanical steps** — deterministic edits with one correct outcome (backfill `parent:`/`prefix:` design-doc frontmatter, bump `docs/arrows/index.yaml` `schema_version`). Batched and applied together on a single confirmation.
- **Judgment steps** — steps requiring a human decision (formalize an ad-hoc sub-HLD, reconcile overlapping segments). Surfaced individually as proposed decisions; never auto-applied.

Some migrations deliberately leave a **transient marker** flagging an unresolved node. The load-bearing one is a node folder carrying more than its `<node>-design.md` plus optional `<node>-specs.md` pair — a former separate-spec LLD left as extra files instead of relocated into its own child folder. Relocating the LLDs into the node-as-folder tree is the defining, error-prone part of the move, so an overloaded folder is the marker most worth surfacing; a `prefix:` array on a design doc is a second, lower-risk marker (agents reconcile these reliably on a later pass). Each is a judgment step that must be surfaced before the walk reports complete: name the node in the project's own terms, recommend a resolution (promote the extra LLD into its own child folder, collapse a multi-prefix node into `<LEAF>-<TYPE>` facets, or split into sibling leaves), and apply it on approval — never silently leave it, never silently auto-resolve it. The same surfacing-with-recommendation applies when reconcile-conventions detects these markers in a project already at the installed version.

`docs/arrows/index.yaml`'s `schema_version` is a separate overlay-format integer; bumping it can be one of a migration's mechanical steps. On a successful walk the skill refreshes `- Version:` to the installed version (once at the end of a multi-release walk). The defining marker of a conventions version is its structural layout — for the 1.2 conventions, relocation onto the `docs/intent/` node-as-folder tree — so a project that has taken those structural moves *is* on the new conventions and `- Version:` advances even when the user defers residual cleanup (a prefix array, a not-yet-promoted folder); it is not pinned to the prior version. What an honest walk owes the user is not a withheld bump but a clear account: the completion report names every deferred resolution and persisting marker, and those markers stay in place so reconcile-conventions and later invocations re-surface them until resolved. After version-walk the skill falls through to ordinary reconcile-conventions against the now-current conventions. Migration and reconciliation choices are surfaced in the project's own terms (its LLDs, components, specs), not LID's internal structural vocabulary (HLD tenet: *Speak the project's language*).

### Workflow-doc vendoring and sync

Hosts without a plugin system get the full workflow through a vendored doc rather than the instruction file (HLD § Distribution; rationale in `docs/decisions/workflow-distribution.md`). The mechanics this skill owns:

- **The doc is a shipped asset, never authored per-project.** The plugin ships `references/workflow-doc.md`, assembled from the core skill source (SKILL.md plus its reference files) as part of the release ritual — the project-structure segment owns that assembly step; this skill only copies the shipped asset. The copy lands at `docs/lid/workflow.md`, opening with a generated-file header naming the source plugin and version and stating that changes belong upstream (in the plugin) or in the project's instruction file — not in the doc.
- **Bootstrap offers it, default yes.** The offer states the tradeoff plainly: with the doc, the instruction file carries a compact core (arrow mandate, inspection invariant, navigation, `## LID` block) plus a capability-conditional pointer — "consult the `linked-intent-dev` skill if your harness provides it; otherwise read `docs/lid/workflow.md` before making changes." Declining keeps the fuller compressed workflow summary in the instruction file instead. Either shape is valid; the choice is the user's.
- **Aider bridge, offered alongside.** When the user wants deterministic loading for Aider, the skill offers a committed `.aider.conf.yml` carrying `read: AGENTS.md` (Aider's own idiom — nothing auto-loads there otherwise). Per-tool loading notes live in `docs/setup.md`.
- **Version-walk re-syncs.** When a walk finds `docs/lid/workflow.md` present, re-copying the current shipped asset is a mechanical step.
- **Hand-edits are surfaced, never overwritten.** Reconcile-conventions compares the vendored doc's version stamp (and content) against the shipped asset; a stale or locally-modified doc is surfaced with a recommendation (re-sync; move local additions to the instruction file or upstream) — the skill never silently replaces a file the user has edited, even a generated one.

### Arrow-maintenance coordination

When the arrow-maintenance overlay is present (detected by `docs/arrows/` directory), the skill includes additional arrow-navigation rows in the instruction file's directives template — pointing at `docs/arrows/index.yaml` and the per-segment arrow docs as part of the project's navigation table. When arrow-maintenance is absent, these rows are omitted. The skill re-checks this signal on every invocation, so installing arrow-maintenance later triggers the corresponding instruction-file update on the next `/update-lid` run.

### Memory→intent directive

The LID directives the skill writes into the instruction file include a brief, tool-agnostic **memory→intent** note — written unconditionally on bootstrap and refreshed when reconcile-conventions detects an outdated directives section. Agentic tools offer per-agent or per-tool *memory*; that memory does not travel with the project or cascade through the arrow, so durable project knowledge parked there escapes LID (HLD tenet *Docs carry current intent* — the doc tree is what travels, nothing else). The note instructs the agent to test, before persisting durable knowledge to any memory mechanism, whether the knowledge is project intent — *would a fresh agent, in any tool, next session, need it to build the system right?* — and if so to record it in the arrow (HLD/LLD/EARS/decision doc) rather than memory; knowledge about the user or the working relationship stays in memory.

The directive lives in the always-loaded instruction file, not the HLD, because that file is the only artifact reliably in context at the moment an agent is about to write a memory — the HLD, where the rationale belongs, is not loaded then. This mirrors how the MANDATORY workflow directive and the `## LID` block are operative digests of HLD intent placed where they fire.

### Mode interaction

The skill prompts the user for the intended mode when bootstrapping, with Full LID as the default. For projects where the mode is ambiguous, the skill explains the difference and lets the user choose.

**Caller-provided mode.** When this skill is invoked by another skill (for example, `/map-codebase` at terminal verification) that has already determined the mode — typically from its own upstream scope question — the caller passes the mode through and this skill honors it without re-prompting. Re-prompting at the end of a long caller-driven flow would be a bad user experience; the caller's scope question is the mode decision.

Mode and version are persisted in the instruction file's `## LID` block — `- Mode: {Full|Scoped}` and `- Version: {X.Y.Z}`. At bootstrap the skill writes `- Version:` set to the installed `linked-intent-dev` version, so a freshly-bootstrapped project starts current and triggers no spurious version-walk. The `## LID` block is the sole source of truth for both mode and version detection.

### Mode transitions

- **Full → Scoped (demotion).** Mode marker updates; no file migration required. Cascade rigor relaxes on the next `linked-intent-dev` skill run.
- **Scoped → Full (promotion).** Arrow artifacts migrate from scope-local paths into the standard Full LID positions — the `docs/intent/` design tree (each node a folder with its `{node}-design.md` and `{node}-specs.md`) and `docs/high-level-design.md`. Where multiple scoped arrows have overlapping components, the skill surfaces the overlaps to the user one pair at a time and asks for reconciliation. There is no automatic merge.

### Idempotency and inform-and-skip

The skill is idempotent. Running it twice on a well-configured project produces no changes. This is important because the alias invites repeat invocation, and because users may run it to confirm their project is still correctly configured.

When the skill detects that the project is already fully configured (LID directives present, mode marker valid, all required directories exist, no convention drift), it **informs the user what it detected and exits without making changes**. The user sees a brief summary — detected mode, presence of arrow-maintenance overlay, directory structure status — rather than a silent no-op. Silent no-ops are confusing; an explicit "nothing to do; here is what I saw" avoids the user wondering whether the skill ran at all.

### Verification and show-what-changed

After making any file changes (bootstrap, append directives, mode transition, drift reconciliation), the skill reads back the modified files — primarily the instruction file — and produces a short summary of what was added or modified. The user should never have to diff the repo manually to understand what the skill just did. Summaries name the files changed and the sections added/modified, with the actual content elided unless it is a single line.

### Directory structure

The skill creates (or verifies) this layout in the project root:

- `docs/high-level-design.md`
- `docs/intent/`

Notably, `docs/planning/` is **not** created. Plans are agent-native; LID does not require the directory. When invoked as `/update-lid` against a project that contains a legacy `docs/planning/` from an earlier LID era, the skill flags the directory as obsolete, describes what it contains, and offers to remove it after explicit user confirmation. It never removes without confirmation. The `linked-intent-dev` skill itself ignores the directory — it is not part of the required arrow.

## Decisions & Alternatives

| Decision | Chosen | Alternatives Considered | Rationale |
|---|---|---|---|
| Configure-or-reconcile: one skill (`update-lid`) vs. separate setup/update skills | One skill, one command (`/update-lid`); fresh-project entry is via `/linked-intent-dev` (the workflow skill calls `update-lid`'s bootstrap branch in Phase 1) | Separate `/lid-setup` and `/update-lid` commands aliased to one skill; standalone `/lid-setup` for fresh projects | Two command names for one skill is surface noise — users learn one name, the skill state-dispatches. Fresh-project users reach for `/linked-intent-dev` with a project description anyway (they want the workflow, not a setup ritual), so the workflow handling bootstrap inline is the natural fit. |
| Mode and version detection source | The instruction file's `## LID` block (`- Mode:` / `- Version:` bullets) | Per-doc frontmatter; dedicated config file; directory convention; separate `## LID Mode:` heading per marker | The instruction file is already the bootstrap entry point and is read on every session. Mode and conventions-version are both project-global, not per-doc. One `## LID` block holding both as bullets is less heading noise than a heading per marker and groups the project's LID metadata in one greppable place. |
| Bootstrap instruction-file target | `AGENTS.md` canonical + `CLAUDE.md` symlink alias; update an existing instruction file in place; no host detection | Write `CLAUDE.md` only (prior behavior); detect host and write that host's file; mirror content between both files | `AGENTS.md` is the cross-tool convention Cursor and most agents read natively, so one canonical `AGENTS.md` with a `CLAUDE.md` alias makes a single bootstrap serve every host. Writing `CLAUDE.md` only leaves a Cursor project with no file the host reads, so mode detection silently never fires. Host detection and content-mirroring are machinery the symlink makes unnecessary (HLD § *Cursor as a first-class plugin host*); keeping an existing `CLAUDE.md`-centered project in place avoids a forced migration. |
| Version-walk migration source | The plugin CHANGELOG's per-release `### Migration (vX → vY)` sections, walked in order between project and installed version | Migration scripts shipped per release; a dedicated migrations directory; reconcile-conventions alone (no version awareness) | The CHANGELOG already records each release and is the human-readable conventions record; co-locating the doc-level migration steps there keeps one source. Scripts/directories add surface and code where prose steps suffice. Reconcile-conventions alone cannot know which conventions a lagging project predates, so it would mis-propose or miss steps a version delta makes explicit. |
| Version-walk application discipline | Reuse propose → confirm → apply; batch mechanical steps, surface judgment steps individually | Auto-apply all migration steps; require per-step confirmation for everything | Mechanical steps have one correct outcome, so batching them is safe and low-friction; judgment steps (formalizing a sub-HLD) genuinely need the user, so they are surfaced one at a time. Auto-applying everything would silently rewrite, violating the skill's never-silently-rewrite contract; confirming every mechanical step would bury the user in trivial approvals. |
| Version bump on partial migration | Advance `- Version:` to the installed version once the release's defining structural move is done (for 1.2, the `docs/intent/` node-as-folder relocation), even when residual cleanup is deferred; report deferrals and leave the markers for reconcile-conventions to re-surface | Withhold the bump / pin to the highest fully-reconciled version until everything resolves (gate-like) | The `docs/intent/` layout is what marks a project as on the 1.2 conventions, and relocating the LLDs is the load-bearing, error-prone part of the move; once it is done the project *is* 1.2-shaped. Residual cleanup — prefix arrays especially — is low-risk and agents reconcile it reliably on a later pass, so it does not warrant misrepresenting the project's version, and pinning would re-trigger a full version-walk on the next run that re-proposes the done steps. Advancing is sound because deferred markers are re-surfaced by reconcile-conventions independently of version lag (LID-UPDATE-005), so the debt is tracked, not buried; withholding the version as a precondition would make `/update-lid` a gate, against the HLD Non-Goal that LID is not a linter/validator and the *user-is-always-right* tenet. |
| Missing/malformed mode fallback | Default to Full, surface warning | Default to Scoped; fail loudly; prompt for mode | Full is the more rigorous mode; defaulting there errs toward more specification. Full and Scoped are close enough that the cost of the wrong default is small. Failing loudly would block harmless sessions; prompting interrupts the user unnecessarily. |
| `docs/planning/` creation | Do not create; flag obsolete if present | Create empty; create with README; create conditionally | Plans are agent-native now. Creating an unused directory is clutter; creating a README is surface growth. Flagging legacy directories respects existing user content. |
| Memory→intent directive placement | An unconditional directive in the instruction-file template, delivered by bootstrap + reconcile-conventions | An HLD tenet; a nudge in the `linked-intent-dev` core skill | The behavior is triggered (*when about to save a memory → test it*), so it is EARS-shaped, not a class-level tenet; and it must fire at memory-save time, when only the always-loaded instruction file is reliably in context — not the HLD (where the rationale lives) nor the workflow skill (which loads only on a code change). |

## Open Questions & Future Decisions

### Resolved

1. ✅ One plugin, two skills (prose + behavioral). Commands are entry points to the behavioral skill.
2. ✅ Mode lives in the instruction file's `## LID` block, single source; defaults to Full when missing or malformed.
3. ✅ Plans are not a required artifact; legacy `docs/planning/` is flagged but not auto-removed.
5. ✅ Multiple instruction files resolved by harness first, nearest-to-file-under-review second.
6. ✅ Mid-transition or otherwise inconsistent arrows are surfaced to the user; resolving inconsistency is a userland decision, not an auto-repair.
7. ✅ Cascade touching uncommitted work warns and requires confirmation before proceeding.

## References

- `docs/intent/linked-intent-dev/linked-intent-dev-design.md` — parent `LID` sub-HLD; holds plugin-level concerns shared across the plugin's three skills (mode detection mechanics, spec-ID format, eval-metadata conventions).
- `docs/high-level-design.md` — the HLD this design traces from.
- `docs/intent/linked-intent-dev/core/core-design.md` — sibling leaf LLD covering the `linked-intent-dev` workflow skill.
- `docs/intent/arrow-maintenance/arrow-maintenance-design.md` — sibling plugin LLD; arrow-overlay coordination behavior lives there.
