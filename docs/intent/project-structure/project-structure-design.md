---
parent: high-level-design
prefix: PROJ-STRUCT
---

# Project Structure

## Context and Design Philosophy

Project Structure owns the repository's meta-artifacts — the documents and configuration that describe the project as a whole rather than any one piece of it — and the rules for how the plugins' files and versions are laid out for hosts, which the `packaging-checks` segment verifies before each merge. The artifacts fall into two groups.

Repo-meta artifacts:

- `CONTRIBUTING.md` — contributor onboarding
- `AGENTS.md` (canonical) and `CLAUDE.md` (symlink alias) — agent bootstrap entry point
- `docs/setup.md` — per-tool integration setup across the agentic-tool ecosystem
- `.claude-plugin/marketplace.json` and `.cursor-plugin/marketplace.json` — plugin marketplace manifests, one per first-class plugin host (Claude Code, Cursor)
- `CHANGELOG.md` — release history and per-version migration notes (canonical inside `plugins/linked-intent-dev/`, repo-root symlink alias)
- `.gitignore` — repository ignore rules, including the exclusion of regenerable eval run-output trees from version control
- `.claude/settings.json` — Claude Code settings shared by everyone working in this repository
- `LICENSE` — MIT license

Community-health artifacts:

- `CODE_OF_CONDUCT.md` — the behavioral standard for participation, at the repository root
- `SECURITY.md` — how to report a security concern, and the scope that concern carries against a project that ships no executable application code
- `CITATION.cff` — machine-readable citation metadata so the methodology can be cited
- `.github/` contribution templates — issue forms and the pull-request template that operationalize the `CONTRIBUTING.md` arrow-walk at the point of contribution

Three principles shape the component:

- **Single ownership for repo-meta surface.** Each artifact above describes the project as a whole. Distributing them across multiple LLDs would leave individual documents over-scoped (e.g., the marketing-site LLD reasoning about contributor mechanics) or unowned. One LLD covering all of them keeps the cascade coherent and the boundaries clean. Community-health files fold in under the same rule rather than spawning a separate governance component: they describe participation in the project as a whole, change rarely, and a dedicated component would be over-scoped for them.
- **Cross-tool one-source-of-truth.** Coding agents read different per-project rule files (Claude Code reads `CLAUDE.md`; many others read `AGENTS.md`; some need adapter snippets). The component resolves this with a single canonical `AGENTS.md`, `CLAUDE.md` as a zero-drift symlink, and `docs/setup.md` documenting per-tool adapter snippets that users drop into their own projects rather than shipping them from this repository.
- **Contributor surface as the operational face of HLD principles.** `CONTRIBUTING.md` codifies HLD Goal 2 (minimum-system) as a contributor-facing test (the gate question quoted from § Key Design Decisions / *Minimum-system discipline — the why*) and surfaces the variant arrow shapes from § *The arrow for LID itself* as a decision tree contributors walk by change type.

The component follows the content artifact pattern from HLD § Key Design Decisions / *The arrow for LID itself* (`HLD → LLD → EARS → content + assets`). Verification is the packaging checks (the `packaging-checks` segment: link integrity, JSON validity, symlink resolution, the frontmatter of shipped skill and command files, version agreement, and host loading) plus dogfooding review when upstream HLD/LLDs change.

## Owned Artifacts

### `CONTRIBUTING.md`

Contributor onboarding for humans and (primarily) their coding agents. The first paragraph is a short human preamble pointing humans at their agents; the rest is agent-facing.

Sections:

- **The bar** — contributions follow LID; this repository is the canonical LID-on-LID reference, and all changes walk the arrow.
- **Trivial changes** — explicit carve-out for typo and grammar fixes, broken-link repairs, formatting, and stale external references. Anything that changes the meaning of intent is not trivial and walks the arrow.
- **Out of scope** — the principle (LID's territory is the structure of intent the agent compiles from) plus four declined categories (multi-agent orchestration, personas, development styles or ceremonies, task management or work tracking). The list is descriptive, not exhaustive — new proposals are judged against the principle.
- **Arrow variant by change type** — decision tree mapping change types to the variant arrow shapes from HLD § Key Design Decisions / *The arrow for LID itself*. Covers: changes to existing core plugins (with sub-cases for behavioral, pure-prose, and dual-mode skills); novel capabilities not in core (route to `lid-experimental`); HLD or methodology changes; site or content changes; and new tool adapters. Closes with the *tests when possible, dogfooding-or-justify when not* principle keyed to artifact variant.
- **Minimum-surface gate** — quotes the HLD's gate question (*"Can the existing surface absorb this, or is the agent about to absorb it anyway?"*) verbatim and routes novel capabilities at `lid-experimental` first.
- **Mechanics** — atomic-improvement framing (one PR equals one coherent intent change, walked end-to-end through whichever arrow phases it touches), propose-first guidance for new surface, PR-description conventions, and the packaging-checks command whose result line every pull request records (see the `packaging-checks` segment).
- **Release / versioning** — when a merge raises the shared version and by how much, and the release step that goes with it (see *Versions and releases* below).

### `AGENTS.md` (with `CLAUDE.md` as symlink alias)

Per-repo invocation of the LID workflow. Names the repository's purpose, the plugin layer, the repository tooling under `tools/` (maintainer helpers such as the alternate-model eval runner and the packaging checks, which ship in no plugin), the editing guidelines for plugin files — one file per invocable name and the preferred frontmatter form (see *Skill and command files* below), and running the packaging checks before a pull request — the methodology workflow (`HLD → LLDs → EARS → Tests → Code`), the LID Mode declaration, and a navigation table to canonical doc locations. Read by every coding agent on entry to the repository.

`AGENTS.md` is canonical because it is the cross-tool convention. `CLAUDE.md` is a symlink resolving to `AGENTS.md`, so Claude Code (which reads `CLAUDE.md`) and tools that honor `AGENTS.md` natively (Codex CLI, Amp, Jules, JetBrains Junie's fallback path, Copilot, etc.) read identical content. A reverse-direction implementation (content in `CLAUDE.md`, `AGENTS.md` as a `@CLAUDE.md` import) is documented in `docs/setup.md` for users whose Claude-Code-first projects prefer it; this repository uses the symlink direction.

### `.claude/settings.json`

The Claude Code settings every contributor's session gets in this repository, and nothing personal. It carries two things:

- **Every first-party plugin enabled** — `linked-intent-dev`, `arrow-maintenance`, and `lid-experimental` from this repository's marketplace. `AGENTS.md` makes the LID workflow mandatory here, so enabling its plugins for every contributor is dogfooding, not preference. `lid-experimental` is opt-in for LID's users, but this repository is where experiments are built and where the evidence for promoting or retiring them should first come from, so it runs them. Each experiment stays dormant or asks before acting: `review-depth` activates only when the instruction file declares a review depth, and the differential audit opens with a scoping conversation before it spends anything.
- **One permission: the alternate-model eval runner** — `Bash(tools/alt-model-evals/run_eval.py:*)`. The runner launches a coding agent with its tool permissions pre-granted, which a cautious agent-permission policy blocks by default; the committed rule lets any contributor's session run it without setup and records that the launch is intended (see the `alt-model-evals` segment).

Anything else — other plugins, broader permissions, personal tools — belongs in the untracked `.claude/settings.local.json`.

### `docs/setup.md`

Per-tool setup guide spanning the agentic-tool ecosystem. Four layers:

1. **First-class plugin hosts** — Claude Code and Cursor, each installing the LID plugins from its own marketplace (the richest path: auto-invoking skills, slash commands). Cursor's section frames the plugin install as the primary path and the rule-file adapter below as the lighter alternative for users who want the methodology without installing a plugin.
2. **Skills hosts** — opencode, which loads the same skills with no manifest: the user lists the core plugins' directories from a clone of this repository (`plugins/linked-intent-dev` and `plugins/arrow-maintenance`) under `skills.paths` in their opencode config, adds `plugins/lid-experimental` only to opt in to the experiments, and updates by pulling the clone. The section states what opencode does not load from the plugin layer: the command aliases, and on opencode 1.x the `disable-model-invocation` guard, so `lid-coach` and `map-codebase` are also model-invocable there. The `packaging-checks` segment's opencode run uses this same setup.
3. **The simple path** — a table of tools that honor a repo-root `AGENTS.md` natively without an adapter (Codex CLI, Amp, Jules, Pi, Zed, Cline, JetBrains Junie, Copilot in supported surfaces, Windsurf, and the broader `agents.md`-spec-compliant set).
4. **Per-tool adapter sections** — explicit rule-file snippets for tools that need or benefit from a separate file (Cursor's `.cursor/rules/lid.mdc` as the no-plugin alternative, Copilot's `.github/copilot-instructions.md`, etc.).

The repository does not ship *adapter* files — users drop the appropriate adapter into their own LID project. (It does ship plugin *manifests*; the two are different, per the marketplace-manifest section below.) This keeps LID one source of truth (`AGENTS.md`) with N thin adapter pointers across the ecosystem.

### Plugin marketplace manifests (`.claude-plugin/`, `.cursor-plugin/`)

The two first-class plugin hosts each read their own marketplace manifest at the repository root, both declaring the same three first-party plugins (`linked-intent-dev`, `arrow-maintenance`, `lid-experimental`) against the same `plugins/` source tree:

- **`.claude-plugin/marketplace.json`** — Claude Code manifest. Each plugin entry carries `name`, `description`, `source`, `category`, and `license`; `source` resolves to a directory under `plugins/`. Install commands in `README.md` and `docs/setup.md` resolve through it. Each plugin additionally carries a `.claude-plugin/plugin.json` inside its directory, which holds the plugin's `version` (see *Versions and releases*). The marketplace entries carry no `version`: Claude Code reads a plugin's version from its `plugin.json` first, so a second copy in the entry is ignored and can only drift.
- **`.cursor-plugin/marketplace.json`** — Cursor manifest. Required marketplace-level fields `name`, `owner`, and `plugins`; each plugin entry carries the required `name` and `source` plus `description`, `category`, and `license`. Each plugin additionally carries a thin `.cursor-plugin/plugin.json` (Cursor requires only `name`; LID's also carry `description` and `license`). Cursor discovers each plugin's `skills/<name>/SKILL.md` and `commands/` natively from the same source tree Claude Code reads.

**The Cursor manifests deliberately omit `version`.** Cursor's schema makes it optional, and `update-lid`'s version-walk reads the project's `## LID` block and the CHANGELOG — never a marketplace manifest — so the shared LID version lives only in the three `.claude-plugin/plugin.json` files and the CHANGELOG, and the version checks confirm the Cursor manifests carry none. (If Cursor's marketplace submission later requires a version, it is added then and the version checks hold it equal to the others.)

These are **plugin manifests, not rule-file adapters** — the repository ships them because they register first-party plugins for a host's marketplace, distinct from the per-tool *adapter* files (`.cursor/rules/lid.mdc` and the like) it does **not** ship (see `docs/setup.md` above).

### Skill and command files

Each skill sits at `plugins/<plugin>/skills/<name>/SKILL.md` and is directly invocable by its own name, so a plugin needs a command file (`plugins/<plugin>/commands/<name>.md`) only to offer a skill under a second name — an alias, such as `lid-experimental`'s `/differential-audit` for its `bidirectional-differential` skill.

**One file per invocable name.** No command file shares a name with a skill in the same plugin. A host keeps one entry per name, and which of a same-named command and skill supplies it differs by host and by where the files live. A same-named command file can therefore hide the skill's description (the text that decides when the skill triggers), its body, and its invocation guard.

**Names and description length.** A skill's frontmatter `name` equals its directory name, and no skill name repeats across the three plugins. Hosts key a skill by its frontmatter `name`, and some load all three plugins into one namespace, so a mismatch or a repeat gives one skill different names, or two skills one name, on different hosts. A command file's `name`, when present, equals its filename. Every `description` is at most 1,024 characters, the Agent Skills limit.

**Frontmatter rules.** Every skill and command file opens with its frontmatter block — `---` on the first line, with no byte-order mark or blank line before it — and uses line feeds alone. The block carries no YAML comments, so every `#` in it belongs to a value; each file has a non-empty `description`; and `disable-model-invocation`, where a file sets it, is written as the literal `true` or `false`, which every host reads the same way.

**Preferred frontmatter form.** Contributors write each `description` as a single-line double-quoted string (`description: "…"`), as `AGENTS.md`'s editing guidelines state. Inside double quotes `: ` and ` #` are literal, so neither of the frontmatter failures the packaging checks look for (the `packaging-checks` segment) can arise; a mistake in the form itself — an unescaped `"`, a missing closing quote — fails the parse instead of truncating silently; and a single line stays readable by tools that read frontmatter line by line. A literal `"` inside a description is reworded rather than escaped, because a line-by-line reader does not unescape it. The checks enforce the outcomes, not this form.

### `CHANGELOG.md`

Release history and per-version migration notes for LID. The canonical file lives inside the core plugin at `plugins/linked-intent-dev/CHANGELOG.md`; the repository root `CHANGELOG.md` is a symlink alias resolving to it — the same canonical-plus-symlink pattern as `AGENTS.md`/`CLAUDE.md`. Shipping the changelog inside the plugin means it travels with the plugin into any project that installs `linked-intent-dev`, so the `update-lid` skill can read it wherever it runs.

The file follows [Keep a Changelog](https://keepachangelog.com) format and semantic versioning. It holds only version entries, one per version of LID (see *Versions and releases*), newest first, so its first `## ` heading is the current version. It has no `[Unreleased]` section, because every change that ships is released as it merges. A minor or major entry carries exactly one migration section, headed with the two major.minor versions it moves between (`### Migration (v1.3 → v1.4)`), describing what a downstream LID project must reconcile; `update-lid`'s version-walk reads these sections to drive a guided upgrade. A patch demands no migration, so its entry carries none; the optional refreshes it may ship reach projects through reconcile-conventions. Each entry is also the source for that version's GitHub Release notes.

The changelog records changes to what the plugins ship; work that ships in no plugin — the site, research, this repository's own design docs and tooling — takes no entry, and its record is the repository history and pull requests.

`index.yaml`'s `schema_version` is a separate integer describing the arrow-overlay format, unrelated to the LID semver tracked here.

### Versions and releases

The three plugins share one semver version, set in each plugin's `.claude-plugin/plugin.json`; it is also the LID conventions version (HLD § Architecture / Distribution / *Versioning*). No marketplace manifest carries a version.

**Every merge that changes shipped plugin files raises the version.** Claude Code delivers an update to an existing install only when the plugin's version changes, and users install from `main`, so a merge that leaves the version alone reaches new installs and never existing ones. A plugin's shipped files are its tracked files under `plugins/<plugin>/`, except any `evals/` directory (maintainer evidence no installed skill reads). The CHANGELOG counts: `update-lid` reads its migration sections from the installed plugin, so a correction to it ships as a patch like any other change.

The raise is to the next version after `main`'s, with none skipped, and its size follows the HLD's rule: **patch** for a change that asks nothing of a project, **minor** or **major** for one a project adopts through migration steps. All three plugins move together, whichever of them changed. A patch demands no migration. It may carry optional refreshes — template rewording, a changed workflow doc — which reconcile-conventions offers to projects; a change a project must make to stay correct is minor and carries the migration steps. So for the instruction-file template that `/update-lid` writes into projects, a wording fix is a patch, and a change to what the template tells an agent to do is minor.

**The release travels with the change.** A pull request that changes shipped plugin files also:

- sets the raised version in the three `plugin.json` files and adds its `CHANGELOG.md` entry;
- regenerates the shipped workflow-doc asset (`plugins/linked-intent-dev/skills/update-lid/references/workflow-doc.md`) with the packaging checks' assembly, which builds it from the core skill source (the `packaging-checks` segment). The doc takes the new version as its stamp only when its assembled content changed, so the stamp names the version in which the content last changed, and a vendored copy reads as stale only when there is something new in it.

On a contributor's pull request, the maintainer raises the version, writes the CHANGELOG entry, and regenerates the workflow doc before merging: the right version depends on what else has merged by then, which a contributor cannot see when they open the pull request.

After the merge, the maintainer tags the merge commit `v<version>` and publishes a GitHub Release with notes from the version's `CHANGELOG.md` entry. A minor or major Release also creates a Discussions *Announcements* post (`gh release create … --discussion-category Announcements`). Every version is tagged, because a project's instruction file links to the workflow doc at the tag of the project's recorded version, and bootstrap records whatever version is installed.

**Releases that span several changes gather on a release branch** and merge to `main` once, as one version. `main` holds only released content.

### `.gitignore`

Repository ignore rules. Beyond conventional ignores, it excludes the per-skill eval run-output trees (`plugins/*/skills/*-workspace/`) from version control: these are regenerable skill-creator outputs, not plugin content or intent, so committing them would only bloat the repository and both hosts' plugin bundles. The intent-bearing eval *definitions* (`plugins/*/skills/*/evals/evals.json`) are not ignored and travel with their skills. It also ignores the `.claude/` directory — local session data, worktrees, and each contributor's `settings.local.json` — with one exception: `.claude/settings.json`, the shared settings above, is tracked.

### `LICENSE`

MIT license at repository root.

### `CODE_OF_CONDUCT.md`

The behavioral standard for participating in the project, at the repository root. Adopts the Contributor Covenant — a widely recognized standard contributors already know — rather than a bespoke code, so the expectations are legible on sight and carry no per-project interpretation burden. Names a private contact for enforcement reports.

### `SECURITY.md`

The security-reporting policy, at the repository root. Its first job is to set scope honestly: LID ships no executable application code — it is a methodology, Markdown skills, prompts, and documentation, plus the static marketing-site build under `site/`. The realistic surface is therefore prompt content that could steer an agent and the build/tooling dependencies of `site/`, not a running service. The file routes reports to a private channel (GitHub's vulnerability-advisory flow or maintainer email) rather than public issues, and states the out-of-scope boundary that ties to the HLD Non-Goal *Not adversarial security review*: a vulnerability in a downstream project that used LID to design itself belongs to that project's own security process, because LID does adversarial *coherence* review, not security review.

### `CITATION.cff`

Machine-readable citation metadata in the Citation File Format, at the repository root, so GitHub renders a "Cite this repository" affordance and a methodology that gets referenced can be cited cleanly. The file carries the title, authorship, repository and site URLs, an abstract, the license, and topic keywords. It deliberately omits a `version`/`date-released` pair: those would add a place the release step must keep in sync on top of the existing version contract (the three `plugin.json` versions and the CHANGELOG top), and a citation does not require them.

### `.github/` contribution templates

GitHub-native templates that meet a contributor at the moment of filing, complementing the prose in `CONTRIBUTING.md`. Their shape is taken from what this repository's own issues and PRs already do well, not from an idealized checklist.

- **Issue forms** (`.github/ISSUE_TEMPLATE/`) — two forms plus a `config.yml`. An **intent-proposal** form mirrors the structure the repository's substantive issues already converge on — *Context / Problem → Proposed change → Acceptance criteria → Scope & non-goals → Intent touchpoints (LID) → Related* — where *Intent touchpoints* maps the change to the design docs, specs, and prefix it lands in and flags novel intent. A lighter **bug / drift** form lowers the barrier for a quick report (what's wrong, where in the tree if known, which tool, how to reproduce). Neither form auto-applies labels; triage owns labeling. The `config.yml` routes open-ended questions to GitHub Discussions rather than issues.
- **Pull-request template** (`.github/PULL_REQUEST_TEMPLATE.md`) — oriented to what reviewers of this repository actually find useful: *Why* (motivation and impact), *What changed*, *How it's been tested* (builds, evals, cold-reads, real-project checks), a *Packaging checks* line holding the result line of the run the merge rests on (see the `packaging-checks` segment), a **lightweight** *Arrow touched* line (segments and EARS IDs, or "trivial"), and optional reviewer notes. It deliberately is not a fixed HLD/LLD/EARS/tests/code compliance grid: in practice the heavier gate items (minimum-surface answers, dogfooding scenarios, cross-segment pause points) belong in a PR only when the change involves them, and leading with motivation and testing matches how the project's strongest PRs are already written.

## Cascade

- **HLD Goal 2** (minimum-system, surface-growth resistance) → review `CONTRIBUTING.md`'s *Out of scope* and *Minimum-surface gate* sections for claim drift.
- **HLD Goal 4** (dogfooding signals) → review `CONTRIBUTING.md`'s *Tests, or justify* framing.
- **HLD § Key Design Decisions / *The arrow for LID itself*** — when the variant set changes (new variant added, existing one revised) → `CONTRIBUTING.md`'s arrow-variant decision tree absorbs the change.
- **HLD § Architecture / Methodology** — when the workflow itself changes (rare; itself an HLD-level edit) → `AGENTS.md` updates.
- **Plugin added under `plugins/`, removed, or renamed** → both marketplace manifests (`.claude-plugin/marketplace.json`, `.cursor-plugin/marketplace.json`) and both per-plugin manifests (`.claude-plugin/plugin.json`, `.cursor-plugin/plugin.json`) add or update the entry; `README.md` and `docs/setup.md` install commands cascade.
- **New supported coding tool** → if it is a first-class plugin host, add its marketplace manifest, its per-plugin manifests, and a `docs/setup.md` plugin-host section; if it is a skills host, add a `docs/setup.md` skills-host section stating what it does not load from the plugin layer; if it is rule-file-only, add either a simple-path table row (native `AGENTS.md`) or a per-tool adapter section in `docs/setup.md`.
- **A merge changes a plugin's shipped files** → the shared version rises in the three `.claude-plugin/plugin.json` files and a `CHANGELOG.md` entry is added for it; the workflow-doc asset is regenerated with the packaging checks' assembly; after the merge, a `v<version>` tag and GitHub Release are published from the entry, and a minor or major Release posts to Discussions *Announcements* (release step in `CONTRIBUTING.md`; see *Versions and releases*).
- **HLD Non-Goal *Not adversarial security review* changes** → `SECURITY.md`'s scope and out-of-scope boundary are reviewed for drift.
- **`CONTRIBUTING.md`'s arrow-variant decision tree changes** → `.github/PULL_REQUEST_TEMPLATE.md`'s arrow-walk checklist is reviewed so the two stay aligned.
- **Project authorship, title, or canonical URLs change** → `CITATION.cff` is updated to match.
- **The alternate-model eval runner's entry point moves or is renamed** → the allow rule in `.claude/settings.json` updates in the same change.
- **Where a host reads skills or commands changes** (HLD § Architecture / Distribution: `skills/<name>/SKILL.md`, `commands/<name>.md`) → *Skill and command files* updates in the same change.
- **The rules in *Skill and command files*, *Versions and releases*, *`CHANGELOG.md`*, or the marketplace manifests change** → the `packaging-checks` segment's checks update in the same change.
- **opencode changes how it finds or guards skills** (a different `skills.paths` behavior, or a pinned version that honors `disable-model-invocation`) → `docs/setup.md`'s skills-host section updates.
- **A skill gains or loses `disable-model-invocation`** → `docs/setup.md`'s list of skills a skills host leaves model-invocable updates.

The `packaging-checks` segment enforces this component's rules, so this segment's `blocks` list in `docs/arrows/index.yaml` names it.

## Decisions & Alternatives

| Decision | Chosen | Alternatives Considered | Rationale |
|---|---|---|---|
| Component scope | Repo-meta artifacts: CONTRIBUTING, AGENTS (+ CLAUDE symlink), docs/setup.md, marketplace.json, LICENSE | Standalone CONTRIBUTING-only component; fold into marketing-site | One LLD for repo-meta keeps the artifacts coherent with each other (they all describe the project as a whole). A CONTRIBUTING-only LLD is too narrow; folding into marketing-site mixes prospect-facing positioning with contributor-facing operations. |
| README ownership | Stays with `marketing-site` | Dual-owned; moved to `project-structure` | README's primary job is positioning to new arrivals — that is marketing-site's territory. Project-structure references README's existence but does not duplicate its content; cross-segment cascade pauses at the boundary per HLD tenet. |
| AGENTS.md ownership | This component owns AGENTS.md | Each plugin owns its own slice; HLD owns it directly | AGENTS.md is the per-repo invocation of the methodology — not the methodology itself (HLD) and not any single plugin's behavior (plugin LLDs). Single owner avoids cross-LLD write contention. |
| Shared Claude Code settings | Track `.claude/settings.json` with only the first-party plugins and the runner's allow rule | Leave all of `.claude/` untracked and document the rule for contributors to add; track the settings file with every plugin the maintainer uses | A tracked file gives every contributor the dogfooding plugins and the runner permission without setup. Keeping it to what LID itself needs stops one person's tools from becoming everyone's. |
| `lid-experimental` in this repository | Enabled alongside the core plugins | Left off, keeping contributors on the stable surface | This repository is where experiments are built and first evaluated; their own designs keep them dormant or asking first, so enabling them costs a contributor an occasional offer, not an unrequested action. |
| `CLAUDE.md` treatment | Symlink to `AGENTS.md` | Adapter file using Claude Code's `@AGENTS.md` import; duplicate maintained content | Symlink resolves identically for both filename conventions with zero drift surface. The `@AGENTS.md`-import alternative is documented in `docs/setup.md` for users whose Claude-Code-first projects prefer it. |
| Component variant | Content artifact (`HLD → LLD → EARS → content + assets`) | Behavioral skill; standalone variant without EARS | Owned artifacts are content and configuration, not behavior. Matches `marketing-site`'s shape; preserves linkage uniformity per HLD § Key Design Decisions / *Content artifacts*. The packaging checks that verify them are code and walk the standard arrow in their own segment (`packaging-checks`). |
| EARS prefix | `PROJ-STRUCT-*` | `PROJECT-*`; `META-*`; `REPO-*` | Most descriptive of what the component owns; matches the component name. |
| Verification mode | Packaging checks plus dogfooding review | Eval suite; manual-only review | Owned artifacts have no runtime to assert against beyond structural validity and whether a host loads them. The packaging checks cover what is automatable (links, JSON validity, symlinks, shipped frontmatter, version agreement, host loading); dogfooding covers framing currency and gate-question phrasing. |
| LICENSE inclusion | Listed as owned by this component | Leave unowned; create a separate licensing LLD | LICENSE is repo-meta and changes rarely; including it costs near-zero LLD prose and closes the unowned gap. A standalone licensing component is overkill for a one-file MIT setup. |
| Plugin versions | One version shared by the three plugins, set only in each `plugin.json`, raised by every merge that changes shipped plugin files; the packaging checks confirm the copies agree and that a changed plugin raised it | A version per plugin, raised only at numbered releases, with changes in between shipping under the old version; the version in both `plugin.json` and the marketplace entry; no version, so installs track commits | Claude Code delivers an update to an existing install only when the plugin's version changes, so a merge that keeps the version reaches new installs and never existing ones, and two installs reporting the same version hold different files. Raising it on every shipped change keeps a version naming one set of files. One shared version gives the CHANGELOG one sequence and each release one tag; per-plugin versions would need a sequence and tag scheme per plugin for no reader who uses them. A copy in the marketplace entry is ignored when `plugin.json` sets one (Claude Code's guidance is to set it in one place) and can only drift. With no version, Claude Code versions a relative-path plugin by the marketplace repository's latest commit, so every site, research, or design-doc commit here would read as an update to all three plugins, and the conventions version would need a new home outside the manifests. |
| Shipped files for the version rule | A plugin's tracked files under `plugins/<plugin>/`, except any `evals/` directory; the CHANGELOG counts | Every file under `plugins/`; only `SKILL.md` files and `references/`; the CHANGELOG exempt as a record | A host copies the whole plugin directory and a skill may read any file in it, so anything a skill can reach counts. The CHANGELOG is one of those files: `update-lid` reads its migration sections from the installed plugin, so a correction that raised no version would leave every existing install walking projects with the uncorrected step. Eval definitions and their `tested_with` results are maintainer evidence no installed skill reads, and recording an eval run is frequent enough that raising the version for it would turn releases into a feed of eval runs. |
| Branches | `main` holds only released content; a release that spans several changes gathers on a release branch and merges once | A long-lived `develop` branch that pull requests target, with releases merged to `main` | Every merge to `main` is a release, so `main` is always what users should have, and release branches already gather multi-change releases (as the 1.4.0 release did). A `develop` branch would make every contributor's pull request — which opens against the default branch — need retargeting, or, made the default branch, would hand unreleased work to anyone running `/plugin marketplace add jszmajda/lid`. |
| Release publication & announcement | Every version gets a `v<version>` tag on its merge commit and a GitHub Release with notes from its CHANGELOG entry; a minor or major Release also creates a Discussions *Announcements* post (`gh release create … --discussion-category Announcements`) | Manifest-only versioning (no tag/Release); tagging only minor and major versions; announcing every version; a hosted action that publishes on merge | A tagged, published Release is what users and tooling actually discover. Every version is tagged because a project's instruction file links to the workflow doc at the tag of its recorded version, and bootstrap records whatever version is installed, patch included. A patch asks nothing of a project, so its Release notes are enough; announcing every patch would turn Announcements into a change feed. Publishing stays a maintainer step after the merge, as the repository runs no hosted CI (the `packaging-checks` segment, *Where the checks run*). |
| Patch or minor for the instruction-file template | A wording fix is a patch, which reconcile-conventions may offer as an optional refresh; a change to what the template tells an agent to do is minor, with a migration step | Every template change is minor | Reconcile-conventions compares a project's instruction file with the current template at every version, so a reworded template reaches projects that run `/update-lid` without a walk. Requiring a minor version and a migration step for every typo fix would make migrations routine and blunt the signal that a minor version asks something of a project. A change to what agents are told to do is the kind of change a project adopts, so it carries the step. |
| Who raises the version on a contributor's pull request | The maintainer, together with the CHANGELOG entry and the workflow-doc regeneration, before merging | The contributor, when opening the pull request | The right version depends on what has merged by the time the pull request does. A contributor sees only `main` as it was when they branched, so their number collides with parallel pull requests, and judging patch against minor needs the release history the maintainer holds. |
| CHANGELOG scope | Only changes to what the plugins ship, in version entries only; no `[Unreleased]` section | Every repository change, including the site, research, and design docs; an `[Unreleased]` section gathering changes before a release | The changelog ships to users and drives `update-lid`, and work outside the plugins never reaches either; its record is the repository history and pull requests. Every shipped change is released as it merges, so there is nothing unreleased to gather, and a section above the current version would make "the first entry is the current version" ambiguous. |
| Skill names | A skill's `name` equals its directory name and is unique across the three plugins; a command's `name`, when present, equals its filename | Names free, with the directory as a fallback | Hosts key a skill by its frontmatter `name`, while tools and people read the directory, and opencode loads all three plugins into one namespace where a repeated name keeps whichever skill loads last. Tying the name to the directory and keeping it unique gives each skill one name on every host. |
| opencode as a supported skills host | Documented in `docs/setup.md`: a clone's `plugins/` listed under `skills.paths`, with the host's limits stated | An `AGENTS.md`-only tool, as before; waiting for an opencode version that honors `disable-model-invocation` | opencode reads Agent Skills natively and is the harness LID's alternate-model evals already run on, so its loading path is exercised here on every packaging-checks run. Its limits (no command aliases; opencode 1.x ignores the invocation guard, so the user-invoked skills are also model-invocable) are stated for users rather than worked around in skill text, since opencode's v2 line honors the guard. |
| CHANGELOG location | Canonical inside the core plugin (`plugins/linked-intent-dev/CHANGELOG.md`) with a repo-root symlink alias | Repo-root canonical with no plugin copy | A repo-root canonical does not travel with the plugin, so `update-lid` cannot read the migration notes when `linked-intent-dev` is installed in a user project. Canonical-in-plugin ships the changelog with the conventions it documents; the root symlink keeps it discoverable at the conventional location. |
| Community-health inclusion | Fold `CODE_OF_CONDUCT.md`, `SECURITY.md`, `CITATION.cff`, and `.github/` templates into this component | Spawn a separate governance/community component; leave to GitHub's defaults | These files describe participation in the project as a whole — the same single-ownership logic that groups the repo-meta artifacts. They change rarely, so a dedicated component would be over-scoped, and GitHub's defaults (no code of conduct, a generic security stub) miss the project-specific scope `SECURITY.md` needs. |
| Code of conduct standard | Contributor Covenant | A bespoke code; no code of conduct | A recognized standard contributors already know, legible on sight, with no per-project interpretation burden. |
| `SECURITY.md` scope framing | State that LID ships no executable application code and bound the real surface (prompt content, `site/` build deps); route reports privately; tie the out-of-scope line to the HLD Non-Goal *Not adversarial security review* | Generic GitHub security stub; omit the file | An honest scope is more useful than a boilerplate stub for a project with no runtime, and tying the out-of-scope line to the HLD Non-Goal keeps the coherence/security boundary consistent across documents. |
| `CITATION.cff` version fields | Omit `version`/`date-released` | Carry the current version and release date | Including them adds another place every release must keep synchronized; the version contract already lives across the `plugin.json` files and the CHANGELOG top, and a citation does not require a version. |
| Contribution-template format | Two YAML issue forms (rich intent-proposal + light bug/drift) plus a Markdown PR template | Markdown issue templates; a single form; no templates | Issue forms collect the LID-specific fields (intent-tree touchpoints) as structured input; two forms match the repository's real traffic (substantive proposals plus the occasional quick report); the PR template stays prose for flexibility. |
| PR-description shape | Motivation/impact-first with a lightweight arrow-touched line; heavier gate items included only when the change involves them | A fixed every-PR checklist of arrow segments + variant + minimum-surface answers + dogfooding + pause points | Grounded in the repository's own merged PRs: the consistently useful sections are why / what / how-tested plus a light segments-and-IDs line; the full compliance grid is rarely all-applicable and reads as ceremony. `PROJ-STRUCT-018` is revised to match. |
| Cursor as a first-class plugin host | Ship `.cursor-plugin/` marketplace + per-plugin manifests from this repo, reusing the same `plugins/` skill/command source | Rule-file adapter only (status quo); a separate Cursor-only fork/repo | Cursor's native marketplace reads the same `SKILL.md`/`skills/`/`commands/` layout, so one shared source serves both hosts with only a thin extra manifest. Adapter-only leaves Cursor users without auto-invoking skills; a fork doubles the maintenance surface and drifts. See HLD § Key Design Decisions / *Cursor as a first-class plugin host*. |
| Cursor manifest `version` field | Omitted | Include and sync with the Claude manifests / CHANGELOG | `version` is optional in Cursor's schema, and `update-lid`'s version-walk reads the `## LID` block + CHANGELOG, not a marketplace manifest. Including it would add copies the version checks must keep equal, for no functional gain. Added at submission only if Cursor requires it. |
| Eval run-output fixtures (`skills/*-workspace/`) | Gitignored — excluded from the repo and therefore from both hosts' bundles | Keep committed; move to a top-level `eval-runs/` outside `plugins/` | The `*-workspace` trees are regenerable skill-creator run outputs (`iteration-N/eval-K/`), referenced by no `evals.json`, `SKILL.md`, or spec — pure accumulation, ~92% of plugin files. Gitignoring excludes them from both bundles with zero eval-runner breakage; the intent-bearing `evals/evals.json` definitions stay with each skill. Moving rather than removing preserves run history but keeps ~1.4 MB of scratch in the repo for no consumer. |
| One file per invocable name | A command file only as an alias under a name no skill in its plugin uses | Command stubs beside same-named skills, routing each slash name to its skill; no command files at all | Measured on Claude Code 2.1.296: within a plugin, a same-named `commands/<name>.md` replaces `skills/<name>/SKILL.md` outright — the model is shown the stub's description, the Skill tool delivers the stub's body without the skill's base directory, and the skill's `disable-model-invocation` guard is lost — while in a project's `.claude/` directory the skill wins. The plugin-level precedence is undocumented, so a same-named pair is harmful where the command wins and redundant where the skill does. Every skill is already invocable by its own name, so a stub adds nothing; an alias under a different name (`/differential-audit`) collides with nothing and stays available. |
| Preferred `description` form | Single-line double-quoted string | Plain (unquoted) scalar; single-quoted string; folded block (`>-`); literal block (`\|-`) | Double quotes make `: ` and ` #` literal, and a mistake in the form fails the parse rather than truncating. A plain scalar carries both hazards. Single quotes are as safe but escape an apostrophe by doubling it, and descriptions are prose full of apostrophes. Block scalars need no escaping, but a tool that reads frontmatter line by line (as the alternate-model eval runner reads a skill's `name`) sees only the `>-` or `\|-` indicator. |

## Open Questions & Future Decisions

### Resolved

1. ✅ Component scope: CONTRIBUTING.md, AGENTS.md (+ CLAUDE.md symlink), docs/setup.md, .claude-plugin/marketplace.json, LICENSE.
2. ✅ EARS prefix: `PROJ-STRUCT-*`.
3. ✅ Component variant: content artifact (`HLD → LLD → EARS → content + assets`).
4. ✅ README ownership stays with `marketing-site`; this component references but does not own.
5. ✅ AGENTS.md is canonical; CLAUDE.md is a symlink to it.
6. ✅ Community-health files (`CODE_OF_CONDUCT.md`, `SECURITY.md`, `CITATION.cff`, `.github/` contribution templates) are owned by this component, folded in under single-ownership rather than spawned as separate components.

### Deferred

1. **Contributor-licensing (CLA / DCO).** Still out of scope. If the project later adds a contributor-licensing mechanism, it folds into this component rather than spawning a new one unless it grows substantially.
2. **Cursor marketplace submission.** The `.cursor-plugin/` manifests make the plugins installable locally (`~/.cursor/plugins/local/`) and ready for submission; the actual publish to Cursor's reviewed marketplace (`cursor.com/marketplace/publish`) is a maintainer action taken once the manifests and the anchor-agnostic skill text have landed.
3. **Anchor-agnostic skill text is a cross-segment cascade.** For the plugins to behave correctly under Cursor, the skill bodies that read or write the instruction file (`update-lid` writing the `## LID` block; the workflow skill detecting mode) must treat `AGENTS.md` as the anchor under Cursor, not only `CLAUDE.md`. That intent lives in the `linked-intent-dev` core and `update-lid` LLD segments, not here; this segment pauses at the boundary and the skill-text cascade is walked separately. The same cascade covers per-skill host portability — all three plugins ship to Cursor, but Claude-orchestration-heavy skills (`map-codebase`, `bidirectional-differential`) carry their host-support limits in their own segments, not in the marketplace manifest.
4. **How Cursor delivers updates.** The Cursor manifests carry no `version`. Whether Cursor then updates an install on every commit, or never, is unverified (Cursor's documentation describes team marketplaces refreshing on push; forum reports differ for other installs), so the HLD's statement that hosts deliver an update when the version changes is confirmed for Claude Code only. Settled by testing a Cursor install when one is available.

## References

- `docs/high-level-design.md` — Goal 2 (minimum-system); Goal 4 (dogfooding); Non-Goal *Not a linter or validator*; § Architecture / Methodology; § Architecture / Distribution; § Key Design Decisions / *The arrow for LID itself*; § Key Design Decisions / *Minimum-system discipline — the why*; § Key Design Decisions / *Cursor as a first-class plugin host*.
- `docs/intent/marketing-site/marketing-site-design.md` — sibling component in the onboarding taxonomy bucket; owns `README.md`; defines the content-artifact verification pattern this LLD reuses.
- `docs/intent/linked-intent-dev/linked-intent-dev-design.md` — defines the workflow `AGENTS.md` instantiates per-repo.
- `docs/intent/project-structure/project-structure-specs.md` — EARS specs for this component.
- `docs/intent/packaging-checks/packaging-checks-design.md` — the segment whose checks enforce this component's skill, command, version, CHANGELOG, and manifest rules, and whose workflow-doc assembly the release step runs.
- `CONTRIBUTING.md`, `AGENTS.md`, `docs/setup.md`, `.claude-plugin/marketplace.json`, `CHANGELOG.md`, `LICENSE` — owned artifacts.
- `plugins/linked-intent-dev/CHANGELOG.md` — canonical changelog (repo-root `CHANGELOG.md` is its symlink alias); each plugin's `.claude-plugin/plugin.json` carries the shared LID version its top entry tracks.
- `plugins/linked-intent-dev/skills/linked-intent-dev/references/lld-templates.md` — LLD structure this document follows.
