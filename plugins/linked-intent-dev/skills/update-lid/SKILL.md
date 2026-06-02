---
name: update-lid
description: Configure or reconcile a project for linked-intent development (LID). Dispatches on project state — fresh bootstrap, append directives to an existing agent-instructions file (AGENTS.md or CLAUDE.md), add missing mode marker, reconcile convention drift, or run mode transitions. Invoked as /update-lid. For fresh projects with no LID artifacts, users typically invoke /linked-intent-dev (the workflow skill) instead and the workflow's Phase 1 calls this skill's bootstrap branch.
disable-model-invocation: true
---

# update-lid

Configure or reconcile a project for linked-intent development. Dispatches on project state — do not re-run unconditionally.

Invoked as `/update-lid`. The skill handles both initial bootstrap and ongoing reconciliation; the user's mental model differs ("set me up" vs. "update what we have") but the behavior dispatches on what's detected in the project, not on the user's framing.

## Instruction-file anchor

LID's directives, the `## LID` block, and the navigation table live in the project's **agent-instructions file**. Canonically that is **`AGENTS.md`** (the cross-tool convention Cursor and most agents read), with **`CLAUDE.md` a symlink alias** so Claude Code sees the same content. Never branch on which host you are running under.

- **Read** (detect directives, mode, version, drift): use `AGENTS.md` if it exists, otherwise `CLAUDE.md`. With the symlink the two are one file.
- **Fresh bootstrap (write)**: create `AGENTS.md` and a `CLAUDE.md` symlink pointing at it (`ln -s AGENTS.md CLAUDE.md`). Where symlinks are unavailable (e.g. Windows without Developer Mode), instead write a `CLAUDE.md` whose only content is `@AGENTS.md`.
- **Existing project (write)**: update the file that already exists, in place. A project that already uses `CLAUDE.md` keeps it — do not migrate it to `AGENTS.md`.

Below, *the instruction file* means the file chosen by these rules.

## Detection signals

Use these exact detection rules — do not guess or use fuzzy matching.

- **LID directives present**: `grep` for the literal strings `"linked-intent-dev"` or `"Linked-Intent Development"` in the instruction file. Either match indicates LID directives are already installed.
- **LID metadata block present**: `grep` for a `## LID` heading in the instruction file. The block carries two bullets:
  - `- Mode: {Full|Scoped}` — the project's LID mode. Case-insensitive on the mode name; whitespace tolerated.
  - `- Version: {X.Y.Z}` — the `linked-intent-dev` plugin version the project's docs conform to. A project with a `## LID` block but no `- Version:` bullet is treated as **predating versioned conventions (no `- Version:` bullet)** (walk from the start).
- **Project version vs. installed version**: read `- Version:` from the `## LID` block and compare it to the installed `linked-intent-dev` plugin version (the `version` field in `plugins/linked-intent-dev/.claude-plugin/plugin.json`, the canonical LID conventions version). When the project version is lower, the project lags and version-walk applies.
- **Arrow-maintenance overlay present**: `docs/arrows/` directory exists at the project root.
- **Convention drift**: any of the required directories missing (`docs/intent/`, `docs/high-level-design.md`); the instruction-file directive sections diverge from the current template, including a **malformed `## LID` block** (heading other than a bare `## LID`, mode merged into the heading as `## LID Mode: Full`, a missing `- Mode:` or `- Version:` bullet, or stray non-template bullets); a design doc whose `prefix:` frontmatter is an **array** (an unresolved multi-prefix marker — see Version-walk); or a node folder holding **more than its `<node>-design.md` + optional `<node>-specs.md` pair** (an un-promoted sub-LLD left as extra files). The last two are detected independently of version lag — a project already at the installed version still has them re-surfaced by reconcile-conventions, and handled the same way (surfaced with a recommended resolution, never silently left or auto-resolved).

Re-check all detection signals on every invocation. Installing `arrow-maintenance` after initial setup, for example, should trigger an arrow-navigation-row update on the next `/update-lid` run.

## State dispatch

Inspect the project and take exactly one of these actions:

| Detected state | Action |
|---|---|
| No instruction file, no `docs/` | **Full bootstrap** — create required directories, create the instruction file (`AGENTS.md` + `CLAUDE.md` symlink, per *Instruction-file anchor*) with LID directives + `## LID` block (`- Mode:` + `- Version:` set to the installed `linked-intent-dev` version). |
| Instruction file exists, no LID directives | **Append directives** — append the LID directives block to the existing instruction file without overwriting existing content. Create `docs/` if missing. |
| LID directives present, no `## LID` block (or no `- Mode:` bullet) | **Add or normalize the LID block** — default mode Full, `- Version:` set to the installed version. If a malformed `## LID` heading already exists (mode merged into the heading, e.g. `## LID Mode: Full`, or stray non-template bullets), rewrite it in place to the canonical `## LID` + `- Mode:` + `- Version:` form rather than appending a second block. |
| Project `- Version:` lower than the installed version (or `- Version:` absent → predating versioned conventions) | **Version-walk** (see below) — propose the intervening CHANGELOG migrations, confirm, apply mechanical / surface judgment, refresh `- Version:`. |
| LID directives + `## LID` block at the installed version, no mode change requested | **Reconcile conventions** — check for convention drift (missing directories or files, outdated instruction-file sections) and surface each detected difference as a proposed update requiring user confirmation. |
| Fully configured, no drift, version current, no mode change requested | **Inform and skip** — tell the user what was detected (mode, version, overlay presence, directory status) and exit without changes. |
| Mode change requested (Scoped ⇄ Full) | **Run mode transition** (see below). |

Version-walk is evaluated before reconcile-conventions: a lagging project is brought to the current conventions version first, then ordinary drift reconciliation runs against those conventions.

## Version-walk

A project records the `linked-intent-dev` version its docs conform to in the `## LID` block's `- Version:` bullet. The canonical LID version is the `version` field in `plugins/linked-intent-dev/.claude-plugin/plugin.json`. When the project's `- Version:` is lower than the installed version — or absent, in which case the project is treated as **predating versioned conventions (no `- Version:` bullet)** and walked from the start — the skill walks the project forward to the installed version.

Walk the releases between the project's version and the installed version, in ascending order. The migration source is the CHANGELOG at `plugins/linked-intent-dev/CHANGELOG.md` (the root `CHANGELOG.md` symlinks to it). Each release entry has a **`### Migration (vX → vY)`** section describing the doc-level steps to move a project forward by one release; read each intervening release's Migration section and reconcile the project against it.

Apply the existing propose → confirm → apply discipline — the skill never silently rewrites:

- **Mechanical steps** — deterministic edits with one correct outcome (for example, backfill `parent:`/`prefix:` frontmatter on design docs, bump `docs/arrows/index.yaml` `schema_version`). Batch these and apply them together on a single confirmation.
- **Judgment steps** — steps that require a human decision (for example, formalizing an ad-hoc sub-HLD, reconciling overlapping segments). Surface each individually as its own proposed decision; do not auto-apply. Present the migration text, name the affected files, and let the user decide per step.

A migration entry that mixes both kinds is split: apply its mechanical part in the batch, surface its judgment part individually.

**Never silently leave a transient migration marker.** Some migrations deliberately leave a marker that flags a node as unresolved. The load-bearing one is a node folder carrying **more than its `<node>-design.md` + `<node>-specs.md` pair** — a former separate-spec LLD left as extra files instead of relocated into its own child folder. Relocating the LLDs into the node-as-folder tree is the defining, error-prone part of the move, so an overloaded folder is the marker most worth surfacing; a `prefix:` **array** on a design doc is a second, lower-risk marker (agents reconcile these reliably on a later pass). These are the steps most often dropped, because the marker is easy to write and easy to forget — leaving the walk *looking* done while the structural call it stands in for was never made. Treat each as a judgment step that must be surfaced before the walk reports complete: name the node in the project's own terms, recommend a resolution — **promote** the extra LLD into its own child folder, **collapse** a multi-prefix node into `<LEAF>-<TYPE>` facets, or **split** into sibling leaves — and apply it on approval. The user may defer any of them — honor that (user-is-always-right) — but the deferral is explicit, the marker stays in place as the record of it, and the completion report names every node left unresolved. The same surfacing-with-recommendation applies when reconcile-conventions detects these markers in a project already at the installed version. Surface, never silently leave; recommend, never silently auto-resolve.

Surface migration and reconciliation choices in the project's own terms — its LLDs, components, segments, and specs — not LID's internal structural vocabulary (HLD tenet: *Speak the project's language*).

On a successful walk, refresh the project's `- Version:` bullet to the installed version. When a walk crosses several releases, refresh once at the end rather than stepping the bullet per release. The defining marker of a conventions version is its structural layout — for the 1.2 conventions, relocation onto the `docs/intent/` node-as-folder tree — so a project that has taken those structural moves *is* on the new conventions and the bullet advances even when the user defers residual cleanup (a prefix array, a not-yet-promoted folder); do not pin it to the prior version. What an honest walk owes the user is not a withheld version bump but a clear account: the completion report names every deferred resolution and every persisting marker (unresolved `prefix:` arrays, overloaded node folders), and those markers stay in place so the fall-through to reconcile-conventions — and every later `/update-lid` run — re-surfaces them until resolved.

After version-walk completes, fall through to ordinary reconcile-conventions against the now-current conventions.

## Mode prompting

During a full bootstrap, prompt the user for the intended mode with **Full LID** as the default. For users uncertain which to pick, describe the difference before requesting a choice:

- **Full LID** — whole project, team adopted. HLD and LLDs are anchors of truth; drift is a bug.
- **Scoped LID** — a bounded scope inside a larger non-LID project. Anchors of truth within scope; slippage outside.

If the user does not specify a mode, select Full.

**When mode is Scoped, prompt for scope patterns** before writing the instruction file. Ask the user:
- Which paths (directories, files, glob patterns) are in scope? At minimum one pattern required.
- Which paths, if any, should be explicitly excluded even within the in-scope roots? (Optional.)

Write the answers into a `## LID Scope` section immediately after the `## LID` block (which carries `- Mode: Scoped`):

```markdown
## LID
- Mode: Scoped
- Version: 1.2.0

## LID Scope

Paths in scope:
- `src/auth/**`
- `packages/billing/**`

Paths explicitly excluded:
- `src/auth/legacy/**`
- `**/*.test.ts`
```

When mode is Full, **do not write a `## LID Scope` section**. Its absence means "entire project in scope."

**Caller-provided mode.** When this skill is invoked by another skill (for example, `/map-codebase` at its terminal verification step) that has already determined the mode from its own scope question, the caller passes the mode — and, if Scoped, the scope patterns — through, and this skill honors them without re-prompting. Re-prompting the user for a mode at the end of a long mapping session is a bad UX; the scope question the caller already asked is the mode decision.

Persist the mode and version in the instruction file's `## LID` block — `- Mode: {Full|Scoped}` and `- Version: {X.Y.Z}`. At bootstrap, write `- Version:` set to the installed `linked-intent-dev` plugin version (from `plugins/linked-intent-dev/.claude-plugin/plugin.json`), so a freshly-bootstrapped project starts current and never triggers a spurious version-walk. The `## LID` block is the sole source of truth for mode and version detection by the `linked-intent-dev` skill.

## Mode transitions and scope

- **Full → Scoped.** Prompt for scope patterns and write a new `## LID Scope` section following the format above.
- **Scoped → Full.** Remove any existing `## LID Scope` section from the instruction file.
- **Scoped → Scoped (scope update).** Use `/update-lid` and pass the new scope patterns; the skill rewrites the `## LID Scope` section in place.

## Mode transitions

- **Full → Scoped (demotion)** — update the `## LID` block's `- Mode:` bullet; no file migration. Cascade rigor relaxes on the next `linked-intent-dev` consult.
- **Scoped → Full (promotion)** — migrate arrow artifacts from scope-local paths into the standard Full LID positions — the `docs/intent/` design tree (each node a folder with its `{node}-design.md` and `{node}-specs.md`) and `docs/high-level-design.md`. Where multiple scoped arrows have overlapping components, surface the overlaps to the user one pair at a time and ask for reconciliation. Do not merge automatically.

## Directory structure

Ensure this layout in the project root, creating any missing:

- `docs/high-level-design.md` (populated from the HLD template in `plugins/linked-intent-dev/skills/linked-intent-dev/references/hld-template.md`)
- `docs/intent/`

`docs/decisions/` holds project-level (HLD) decision docs; segment-level decision docs live alongside their segment at `docs/intent/<segment>/decisions/`. Create either lazily — only when the first decision doc at that level is written, not at bootstrap.

**Do not create `docs/planning/`.** Plans are agent-native; LID does not require the directory.

## Arrow-maintenance coordination

When `docs/arrows/` is detected, include extra navigation rows in the instruction file's directives template — pointing at `docs/arrows/index.yaml` and per-segment arrow docs — as part of the project's navigation table. When `docs/arrows/` is absent, omit these rows. Re-check this signal on every invocation.

## Legacy `docs/planning/` handling

When invoked as `/update-lid` on a project containing a `docs/planning/` directory (leftover from earlier LID eras):

- Flag the directory as obsolete.
- Describe what it contains (brief summary of files).
- Offer to remove it.
- **Do not remove without explicit user confirmation.**

The `linked-intent-dev` skill itself ignores this directory — it is not part of the required arrow.

## Idempotency and inform-and-skip

The skill is idempotent. Running it twice on a well-configured project produces no changes. When the project is already fully configured and no changes are needed, **do not silently no-op**. Tell the user what was detected — mode, version (and whether it matches the installed version), overlay presence, directory status — so they know the skill ran and found nothing to do.

Similarly, when convention drift is detected but the user declines every proposed update, still summarize what was found before exiting.

## Verification / show-what-changed

After making any file changes (bootstrap, append directives, mode transition, drift reconciliation):

- Read back the modified files — primarily the instruction file.
- Surface a summary naming the files changed and the sections added or modified.
- Do not elide — short summaries are fine; silent changes are not.

The user should never have to `git diff` the repo to understand what the skill just did.

## Do-not-overwrite rule

When appending the LID directives block to an existing instruction file, preserve all existing content. Append, don't overwrite.

## Reference

- `references/agents-md-template.md` — the LID directives block to append to the instruction file.
