---
name: lid-setup
description: Set up or update a project for linked-intent development (LID). Dispatches on project state — fresh bootstrap, append directives to existing CLAUDE.md, add missing mode marker, reconcile convention drift, or run mode transitions. Invoked as /lid-setup or /update-lid; both names route here.
disable-model-invocation: true
---

# LID Project Setup

Bootstrap or update a project for linked-intent development. Dispatches on project state — do not re-run setup unconditionally.

Invocable as `/lid-setup` (the primary name) or `/update-lid` (alias for users whose mental model prefers a separate update verb). Both route to this skill; the behavior dispatches on what's detected in the project, not on which name was used.

## Detection signals

Use these exact detection rules — do not guess or use fuzzy matching.

- **LID directives present**: `grep` for the literal strings `"linked-intent-dev"` or `"Linked-Intent Development"` in `CLAUDE.md`. Either match indicates LID directives are already installed.
- **Mode marker present**: `grep` for a line matching `## LID Mode:` followed by `Full` or `Scoped`. Case-insensitive on the mode name; whitespace around the heading tolerated.
- **Arrow-maintenance overlay present**: `docs/arrows/` directory exists at the project root.
- **Convention drift**: any of the required directories missing (`docs/llds/`, `docs/specs/`, `docs/high-level-design.md`), or the CLAUDE.md directive sections diverge from the current template.

Re-check all detection signals on every invocation. Installing `arrow-maintenance` after initial setup, for example, should trigger an arrow-navigation-row update on the next `/update-lid` run.

## State dispatch

Inspect the project and take exactly one of these actions:

| Detected state | Action |
|---|---|
| No `CLAUDE.md`, no `docs/` | **Full bootstrap** — create required directories, create `CLAUDE.md` with LID directives + mode marker. |
| `CLAUDE.md` exists, no LID directives | **Append directives** — append the LID directives block to existing `CLAUDE.md` without overwriting existing content. Create `docs/` if missing. |
| LID directives present, no `## LID Mode:` heading | **Add mode marker** with default Full. |
| LID directives + mode marker, no mode change requested | **Reconcile conventions** — check for convention drift (missing directories or files, outdated CLAUDE.md sections) and surface each detected difference as a proposed update requiring user confirmation. |
| Fully configured, no drift, no mode change requested | **Inform and skip** — tell the user what was detected (mode, overlay presence, directory status) and exit without changes. |
| Mode change requested (Scoped ⇄ Full) | **Run mode transition** (see below). |

## Mode prompting

During a full bootstrap, prompt the user for the intended mode with **Full LID** as the default. For users uncertain which to pick, describe the difference before requesting a choice:

- **Full LID** — whole project, team adopted. HLD and LLDs are anchors of truth; drift is a bug.
- **Scoped LID** — a bounded scope inside a larger non-LID project. Anchors of truth within scope; slippage outside.

If the user does not specify a mode, select Full.

**When mode is Scoped, prompt for scope patterns** before writing CLAUDE.md. Ask the user:
- Which paths (directories, files, glob patterns) are in scope? At minimum one pattern required.
- Which paths, if any, should be explicitly excluded even within the in-scope roots? (Optional.)

Write the answers into a `## LID Scope` section immediately after the `## LID Mode: Scoped` heading:

```markdown
## LID Mode: Scoped

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

Persist the mode in `CLAUDE.md` under a `## LID Mode: {Full|Scoped}` heading. This is the sole source of truth for mode detection by the `linked-intent-dev` skill.

## Mode transitions and scope

- **Full → Scoped.** Prompt for scope patterns and write a new `## LID Scope` section following the format above.
- **Scoped → Full.** Remove any existing `## LID Scope` section from `CLAUDE.md`.
- **Scoped → Scoped (scope update).** Use `/update-lid` and pass the new scope patterns; the skill rewrites the `## LID Scope` section in place.

## Mode transitions

- **Full → Scoped (demotion)** — update mode marker; no file migration. Cascade rigor relaxes on the next `linked-intent-dev` consult.
- **Scoped → Full (promotion)** — migrate arrow artifacts from scope-local paths into the standard Full LID positions (`docs/llds/`, `docs/specs/`, `docs/high-level-design.md`). Where multiple scoped arrows have overlapping components, surface the overlaps to the user one pair at a time and ask for reconciliation. Do not merge automatically.

## Directory structure

Ensure this layout in the project root, creating any missing:

- `docs/high-level-design.md` (populated from the HLD template in `plugins/linked-intent-dev/skills/linked-intent-dev/references/hld-template.md`)
- `docs/llds/`
- `docs/specs/`

**Do not create `docs/planning/`.** Plans are agent-native; LID does not require the directory.

## Arrow-maintenance coordination

When `docs/arrows/` is detected, include extra navigation rows in the CLAUDE.md directives template — pointing at `docs/arrows/index.yaml` and per-segment arrow docs — as part of the project's navigation table. When `docs/arrows/` is absent, omit these rows. Re-check this signal on every invocation.

## Legacy `docs/planning/` handling

When invoked as `/update-lid` on a project containing a `docs/planning/` directory (leftover from earlier LID eras):

- Flag the directory as obsolete.
- Describe what it contains (brief summary of files).
- Offer to remove it.
- **Do not remove without explicit user confirmation.**

The `linked-intent-dev` skill itself ignores this directory — it is not part of the required arrow.

## Idempotency and inform-and-skip

The skill is idempotent. Running it twice on a well-configured project produces no changes. When the project is already fully configured and no changes are needed, **do not silently no-op**. Tell the user what was detected — mode, overlay presence, directory status — so they know the skill ran and found nothing to do.

Similarly, when convention drift is detected but the user declines every proposed update, still summarize what was found before exiting.

## Verification / show-what-changed

After making any file changes (bootstrap, append directives, mode transition, drift reconciliation):

- Read back the modified files — primarily `CLAUDE.md`.
- Surface a summary naming the files changed and the sections added or modified.
- Do not elide — short summaries are fine; silent changes are not.

The user should never have to `git diff` the repo to understand what the skill just did.

## Do-not-overwrite rule

When appending the LID directives block to an existing `CLAUDE.md`, preserve all existing content. Append, don't overwrite.

## Reference

- `references/claude-md-template.md` — the LID directives block to append to `CLAUDE.md`.
