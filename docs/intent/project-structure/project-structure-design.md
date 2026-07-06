---
parent: high-level-design
prefix: PROJ-STRUCT
---

# Project Structure

## Context and Design Philosophy

Project Structure owns the repository's meta-artifacts — the documents and configuration that describe the project as a whole rather than any one piece of it. They fall into two groups.

Repo-meta artifacts:

- `CONTRIBUTING.md` — contributor onboarding
- `AGENTS.md` (canonical) and `CLAUDE.md` (symlink alias) — agent bootstrap entry point
- `docs/setup.md` — per-tool integration setup across the agentic-tool ecosystem
- `.claude-plugin/marketplace.json` and `.cursor-plugin/marketplace.json` — plugin marketplace manifests, one per first-class plugin host (Claude Code, Cursor)
- `CHANGELOG.md` — release history and per-version migration notes (canonical inside `plugins/linked-intent-dev/`, repo-root symlink alias)
- `.gitignore` — repository ignore rules, including the exclusion of regenerable eval run-output trees from version control
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

The component follows the content artifact pattern from HLD § Key Design Decisions / *The arrow for LID itself* (`HLD → LLD → EARS → content + assets`). Verification is build-time structural checks (link integrity, JSON validity, symlink resolution, presence) plus dogfooding review when upstream HLD/LLDs change.

## Owned Artifacts

### `CONTRIBUTING.md`

Contributor onboarding for humans and (primarily) their coding agents. The first paragraph is a short human preamble pointing humans at their agents; the rest is agent-facing.

Sections:

- **The bar** — contributions follow LID; this repository is the canonical LID-on-LID reference, and all changes walk the arrow.
- **Trivial changes** — explicit carve-out for typo and grammar fixes, broken-link repairs, formatting, and stale external references. Anything that changes the meaning of intent is not trivial and walks the arrow.
- **Out of scope** — the principle (LID's territory is the structure of intent the agent compiles from) plus four declined categories (multi-agent orchestration, personas, development styles or ceremonies, task management or work tracking). The list is descriptive, not exhaustive — new proposals are judged against the principle.
- **Arrow variant by change type** — decision tree mapping change types to the variant arrow shapes from HLD § Key Design Decisions / *The arrow for LID itself*. Covers: changes to existing core plugins (with sub-cases for behavioral, pure-prose, and dual-mode skills); novel capabilities not in core (route to `lid-experimental`); HLD or methodology changes; site or content changes; and new tool adapters. Closes with the *tests when possible, dogfooding-or-justify when not* principle keyed to artifact variant.
- **Minimum-surface gate** — quotes the HLD's gate question (*"Can the existing surface absorb this, or is the agent about to absorb it anyway?"*) verbatim and routes novel capabilities at `lid-experimental` first.
- **Mechanics** — atomic-improvement framing (one PR equals one coherent intent change, walked end-to-end through whichever arrow phases it touches), propose-first guidance for new surface, and PR-description conventions.

### `AGENTS.md` (with `CLAUDE.md` as symlink alias)

Per-repo invocation of the LID workflow. Names the repository's purpose, the plugin layer, the methodology workflow (`HLD → LLDs → EARS → Tests → Code`), the LID Mode declaration, and a navigation table to canonical doc locations. Read by every coding agent on entry to the repository.

`AGENTS.md` is canonical because it is the cross-tool convention. `CLAUDE.md` is a symlink resolving to `AGENTS.md`, so Claude Code (which reads `CLAUDE.md`) and tools that honor `AGENTS.md` natively (Codex CLI, Amp, Jules, JetBrains Junie's fallback path, Copilot, etc.) read identical content. A reverse-direction implementation (content in `CLAUDE.md`, `AGENTS.md` as a `@CLAUDE.md` import) is documented in `docs/setup.md` for users whose Claude-Code-first projects prefer it; this repository uses the symlink direction.

### `docs/setup.md`

Per-tool setup guide spanning the agentic-tool ecosystem. Three layers:

1. **First-class plugin hosts** — Claude Code and Cursor, each installing the LID plugins from its own marketplace (the richest path: auto-invoking skills, slash commands). Cursor's section frames the plugin install as the primary path and the rule-file adapter below as the lighter alternative for users who want the methodology without installing a plugin.
2. **The simple path** — a table of tools that honor a repo-root `AGENTS.md` natively without an adapter (Codex CLI, Amp, Jules, Pi, Zed, Cline, JetBrains Junie, Copilot in supported surfaces, Windsurf, and the broader `agents.md`-spec-compliant set).
3. **Per-tool adapter sections** — explicit rule-file snippets for tools that need or benefit from a separate file (Cursor's `.cursor/rules/lid.mdc` as the no-plugin alternative, Copilot's `.github/copilot-instructions.md`, etc.).

The repository does not ship *adapter* files — users drop the appropriate adapter into their own LID project. (It does ship plugin *manifests*; the two are different, per the marketplace-manifest section below.) This keeps LID one source of truth (`AGENTS.md`) with N thin adapter pointers across the ecosystem.

### Plugin marketplace manifests (`.claude-plugin/`, `.cursor-plugin/`)

The two first-class plugin hosts each read their own marketplace manifest at the repository root, both declaring the same three first-party plugins (`linked-intent-dev`, `arrow-maintenance`, `lid-experimental`) against the same `plugins/` source tree:

- **`.claude-plugin/marketplace.json`** — Claude Code manifest. Each plugin entry carries `name`, `description`, `source`, `version`, `category`, and `license`; `source` resolves to a directory under `plugins/`. Install commands in `README.md` and `docs/setup.md` resolve through it. Each plugin additionally carries a `.claude-plugin/plugin.json` inside its directory.
- **`.cursor-plugin/marketplace.json`** — Cursor manifest. Required marketplace-level fields `name`, `owner`, and `plugins`; each plugin entry carries the required `name` and `source` plus `description`, `category`, and `license`. Each plugin additionally carries a thin `.cursor-plugin/plugin.json` (Cursor requires only `name`; LID's also carry `description` and `license`). Cursor discovers each plugin's `skills/<name>/SKILL.md` and `commands/` natively from the same source tree Claude Code reads.

**The Cursor manifests deliberately omit `version`.** Cursor's schema makes it optional, and `update-lid`'s version-walk reads the project's `## LID` block and the CHANGELOG — never a marketplace manifest — so the canonical LID version stays single-sourced in `plugins/linked-intent-dev/.claude-plugin/plugin.json` and the CHANGELOG, and the Cursor manifests stay out of the release-step version-sync set. (If Cursor's marketplace submission later requires a version, it is added then and folded into the release step.)

These are **plugin manifests, not rule-file adapters** — the repository ships them because they register first-party plugins for a host's marketplace, distinct from the per-tool *adapter* files (`.cursor/rules/lid.mdc` and the like) it does **not** ship (see `docs/setup.md` above).

### `CHANGELOG.md`

Release history and per-version migration notes for LID. The canonical file lives inside the core plugin at `plugins/linked-intent-dev/CHANGELOG.md`; the repository root `CHANGELOG.md` is a symlink alias resolving to it — the same canonical-plus-symlink pattern as `AGENTS.md`/`CLAUDE.md`. Shipping the changelog inside the plugin means it travels with the plugin into any project that installs `linked-intent-dev`, so the `update-lid` skill can read it wherever it runs.

The file follows [Keep a Changelog](https://keepachangelog.com) format and semantic versioning. LID is versioned with semver per plugin — each plugin's `version` lives in its `.claude-plugin/plugin.json` — and `linked-intent-dev`'s `plugin.json` version is the canonical "LID conventions" version that the changelog's top *versioned* entry tracks. Each release entry carries a `### Migration (vX → vY)` section describing what a downstream LID project must reconcile when conventions change; `update-lid`'s version-walk reads these sections to drive a guided upgrade. When a release is cut, that entry is also the source for the published GitHub Release notes (see the *Release publication* decision below). Changes that warrant no version bump — additive host/platform support, internal refactors, docs (the bump policy lives in HLD § Architecture / Distribution / *What warrants a version change*) — are held under a `## [No Version Update Required]` section above the most recent versioned entry, folding into the next numbered version's entry when one is cut; that section is not itself a version, so it does not advance the canonical version or trigger a `/update-lid` walk.

`index.yaml`'s `schema_version` is a separate integer describing the arrow-overlay format, unrelated to the LID semver tracked here.

### `.gitignore`

Repository ignore rules. Beyond conventional ignores, it excludes the per-skill eval run-output trees (`plugins/*/skills/*-workspace/`) from version control: these are regenerable skill-creator outputs, not plugin content or intent, so committing them would only bloat the repository and both hosts' plugin bundles. The intent-bearing eval *definitions* (`plugins/*/skills/*/evals/evals.json`) are not ignored and travel with their skills.

### `LICENSE`

MIT license at repository root.

### `CODE_OF_CONDUCT.md`

The behavioral standard for participating in the project, at the repository root. Adopts the Contributor Covenant — a widely recognized standard contributors already know — rather than a bespoke code, so the expectations are legible on sight and carry no per-project interpretation burden. Names a private contact for enforcement reports.

### `SECURITY.md`

The security-reporting policy, at the repository root. Its first job is to set scope honestly: LID ships no executable application code — it is a methodology, Markdown skills, prompts, and documentation, plus the static marketing-site build under `site/`. The realistic surface is therefore prompt content that could steer an agent and the build/tooling dependencies of `site/`, not a running service. The file routes reports to a private channel (GitHub's vulnerability-advisory flow or maintainer email) rather than public issues, and states the out-of-scope boundary that ties to the HLD Non-Goal *Not adversarial security review*: a vulnerability in a downstream project that used LID to design itself belongs to that project's own security process, because LID does adversarial *coherence* review, not security review.

### `CITATION.cff`

Machine-readable citation metadata in the Citation File Format, at the repository root, so GitHub renders a "Cite this repository" affordance and a methodology that gets referenced can be cited cleanly. The file carries the title, authorship, repository and site URLs, an abstract, the license, and topic keywords. It deliberately omits a `version`/`date-released` pair: those would add a place the release step must keep in sync on top of the existing version contract (the three `plugin.json` versions, their `marketplace.json` entries, and the CHANGELOG top), and a citation does not require them.

### `.github/` contribution templates

GitHub-native templates that meet a contributor at the moment of filing, complementing the prose in `CONTRIBUTING.md`. Their shape is taken from what this repository's own issues and PRs already do well, not from an idealized checklist.

- **Issue forms** (`.github/ISSUE_TEMPLATE/`) — two forms plus a `config.yml`. An **intent-proposal** form mirrors the structure the repository's substantive issues already converge on — *Context / Problem → Proposed change → Acceptance criteria → Scope & non-goals → Intent touchpoints (LID) → Related* — where *Intent touchpoints* maps the change to the design docs, specs, and prefix it lands in and flags novel intent. A lighter **bug / drift** form lowers the barrier for a quick report (what's wrong, where in the tree if known, which tool, how to reproduce). Neither form auto-applies labels; triage owns labeling. The `config.yml` routes open-ended questions to GitHub Discussions rather than issues.
- **Pull-request template** (`.github/PULL_REQUEST_TEMPLATE.md`) — oriented to what reviewers of this repository actually find useful: *Why* (motivation and impact), *What changed*, *How it's been tested* (builds, evals, cold-reads, real-project checks), a **lightweight** *Arrow touched* line (segments and EARS IDs, or "trivial"), and optional reviewer notes. It deliberately is not a fixed HLD/LLD/EARS/tests/code compliance grid: in practice the heavier gate items (minimum-surface answers, dogfooding scenarios, cross-segment pause points) belong in a PR only when the change involves them, and leading with motivation and testing matches how the project's strongest PRs are already written.

## Cascade

- **HLD Goal 2** (minimum-system, surface-growth resistance) → review `CONTRIBUTING.md`'s *Out of scope* and *Minimum-surface gate* sections for claim drift.
- **HLD Goal 4** (dogfooding signals) → review `CONTRIBUTING.md`'s *Tests, or justify* framing.
- **HLD § Key Design Decisions / *The arrow for LID itself*** — when the variant set changes (new variant added, existing one revised) → `CONTRIBUTING.md`'s arrow-variant decision tree absorbs the change.
- **HLD § Architecture / Methodology** — when the workflow itself changes (rare; itself an HLD-level edit) → `AGENTS.md` updates.
- **Plugin added under `plugins/`, removed, or renamed** → both marketplace manifests (`.claude-plugin/marketplace.json`, `.cursor-plugin/marketplace.json`) and both per-plugin manifests (`.claude-plugin/plugin.json`, `.cursor-plugin/plugin.json`) add or update the entry; `README.md` and `docs/setup.md` install commands cascade.
- **New supported coding tool** → if it is a first-class plugin host, add its marketplace manifest, its per-plugin manifests, and a `docs/setup.md` plugin-host section; if it is rule-file-only, add either a simple-path table row (native `AGENTS.md`) or a per-tool adapter section in `docs/setup.md`.
- **Plugin version bumped / release cut** → `CHANGELOG.md` entry added; the three `.claude-plugin/plugin.json` versions and their `.claude-plugin/marketplace.json` entries bumped together; the shipped workflow-doc asset (`plugins/linked-intent-dev/skills/update-lid/references/workflow-doc.md`) regenerated from the core skill source — SKILL.md plus its reference files, the LID-on-LID exception section stripped, a repository-reference note added — and stamped with the released version; a matching git tag and GitHub Release are published from the new `CHANGELOG.md` entry, and the Release posts an announcement to the Discussions *Announcements* category (release-step in `CONTRIBUTING.md`). The Cursor manifests carry no `version` and are not part of this sync.
- **HLD Non-Goal *Not adversarial security review* changes** → `SECURITY.md`'s scope and out-of-scope boundary are reviewed for drift.
- **`CONTRIBUTING.md`'s arrow-variant decision tree changes** → `.github/PULL_REQUEST_TEMPLATE.md`'s arrow-walk checklist is reviewed so the two stay aligned.
- **Project authorship, title, or canonical URLs change** → `CITATION.cff` is updated to match.

The component is a leaf in the arrow graph — nothing downstream depends on it — so its `blocks` list in `docs/arrows/index.yaml` is empty.

## Decisions & Alternatives

| Decision | Chosen | Alternatives Considered | Rationale |
|---|---|---|---|
| Component scope | Repo-meta artifacts: CONTRIBUTING, AGENTS (+ CLAUDE symlink), docs/setup.md, marketplace.json, LICENSE | Standalone CONTRIBUTING-only component; fold into marketing-site | One LLD for repo-meta keeps the artifacts coherent with each other (they all describe the project as a whole). A CONTRIBUTING-only LLD is too narrow; folding into marketing-site mixes prospect-facing positioning with contributor-facing operations. |
| README ownership | Stays with `marketing-site` | Dual-owned; moved to `project-structure` | README's primary job is positioning to new arrivals — that is marketing-site's territory. Project-structure references README's existence but does not duplicate its content; cross-segment cascade pauses at the boundary per HLD tenet. |
| AGENTS.md ownership | This component owns AGENTS.md | Each plugin owns its own slice; HLD owns it directly | AGENTS.md is the per-repo invocation of the methodology — not the methodology itself (HLD) and not any single plugin's behavior (plugin LLDs). Single owner avoids cross-LLD write contention. |
| `CLAUDE.md` treatment | Symlink to `AGENTS.md` | Adapter file using Claude Code's `@AGENTS.md` import; duplicate maintained content | Symlink resolves identically for both filename conventions with zero drift surface. The `@AGENTS.md`-import alternative is documented in `docs/setup.md` for users whose Claude-Code-first projects prefer it. |
| Component variant | Content artifact (`HLD → LLD → EARS → content + assets`) | Behavioral skill; standalone variant without EARS | Owned artifacts are content and configuration, not behavior. Matches `marketing-site`'s shape; preserves linkage uniformity per HLD § Key Design Decisions / *Content artifacts*. |
| EARS prefix | `PROJ-STRUCT-*` | `PROJECT-*`; `META-*`; `REPO-*` | Most descriptive of what the component owns; matches the component name. |
| Verification mode | Build-time structural checks plus dogfooding review | Eval suite; manual-only review | Owned artifacts have no runtime to assert against beyond structural validity. Build-time checks cover what is automatable (links, JSON validity, presence, symlinks); dogfooding covers framing currency and gate-question phrasing. |
| LICENSE inclusion | Listed as owned by this component | Leave unowned; create a separate licensing LLD | LICENSE is repo-meta and changes rarely; including it costs near-zero LLD prose and closes the unowned gap. A standalone licensing component is overkill for a one-file MIT setup. |
| Version sync mechanism | Release-step discipline plus conventional review (the `CONTRIBUTING.md` release step keeps the six version strings — three `plugin.json` plus three `marketplace.json` — and the CHANGELOG top version equal) | CI gate that fails on version mismatch; generated `marketplace.json` derived from the `plugin.json` files | A CI gate is new scope and runs against the HLD Non-Goal that LID is not a linter/validator — enforcement is conversational. Generation removes hand-edited `marketplace.json` but adds a build step and tooling LID does not otherwise carry. The release step plus reviewer attention is the minimum-system fit. |
| Release publication & announcement | Cut a git tag + GitHub Release from the new CHANGELOG entry, with the Release auto-creating a Discussions *Announcements* post (`gh release create … --discussion-category Announcements`) | Manifest-only versioning (no tag/Release); a CI/Action that auto-publishes or gates on a version bump; a separate manual announcement step | A tagged, published Release is what users and tooling actually discover, and the absence of this publish step is what let releases fall behind the manifests. Having the Release create the announcement folds two steps into one. Automation/gating is rejected for the same reason as the version-sync gate — enforcement is conversational, not a CI obligation (HLD: not a linter/validator). |
| CHANGELOG location | Canonical inside the core plugin (`plugins/linked-intent-dev/CHANGELOG.md`) with a repo-root symlink alias | Repo-root canonical with no plugin copy | A repo-root canonical does not travel with the plugin, so `update-lid` cannot read the migration notes when `linked-intent-dev` is installed in a user project. Canonical-in-plugin ships the changelog with the conventions it documents; the root symlink keeps it discoverable at the conventional location. |
| Community-health inclusion | Fold `CODE_OF_CONDUCT.md`, `SECURITY.md`, `CITATION.cff`, and `.github/` templates into this component | Spawn a separate governance/community component; leave to GitHub's defaults | These files describe participation in the project as a whole — the same single-ownership logic that groups the repo-meta artifacts. They change rarely, so a dedicated component would be over-scoped, and GitHub's defaults (no code of conduct, a generic security stub) miss the project-specific scope `SECURITY.md` needs. |
| Code of conduct standard | Contributor Covenant | A bespoke code; no code of conduct | A recognized standard contributors already know, legible on sight, with no per-project interpretation burden. |
| `SECURITY.md` scope framing | State that LID ships no executable application code and bound the real surface (prompt content, `site/` build deps); route reports privately; tie the out-of-scope line to the HLD Non-Goal *Not adversarial security review* | Generic GitHub security stub; omit the file | An honest scope is more useful than a boilerplate stub for a project with no runtime, and tying the out-of-scope line to the HLD Non-Goal keeps the coherence/security boundary consistent across documents. |
| `CITATION.cff` version fields | Omit `version`/`date-released` | Carry the current version and release date | Including them adds another place the release step must keep synchronized; the version contract already lives across the `plugin.json` files, `marketplace.json`, and the CHANGELOG top, and a citation does not require a version. |
| Contribution-template format | Two YAML issue forms (rich intent-proposal + light bug/drift) plus a Markdown PR template | Markdown issue templates; a single form; no templates | Issue forms collect the LID-specific fields (intent-tree touchpoints) as structured input; two forms match the repository's real traffic (substantive proposals plus the occasional quick report); the PR template stays prose for flexibility. |
| PR-description shape | Motivation/impact-first with a lightweight arrow-touched line; heavier gate items included only when the change involves them | A fixed every-PR checklist of arrow segments + variant + minimum-surface answers + dogfooding + pause points | Grounded in the repository's own merged PRs: the consistently useful sections are why / what / how-tested plus a light segments-and-IDs line; the full compliance grid is rarely all-applicable and reads as ceremony. `PROJ-STRUCT-018` is revised to match. |
| Cursor as a first-class plugin host | Ship `.cursor-plugin/` marketplace + per-plugin manifests from this repo, reusing the same `plugins/` skill/command source | Rule-file adapter only (status quo); a separate Cursor-only fork/repo | Cursor's native marketplace reads the same `SKILL.md`/`skills/`/`commands/` layout, so one shared source serves both hosts with only a thin extra manifest. Adapter-only leaves Cursor users without auto-invoking skills; a fork doubles the maintenance surface and drifts. See HLD § Key Design Decisions / *Cursor as a first-class plugin host*. |
| Cursor manifest `version` field | Omitted | Include and sync with the Claude manifests / CHANGELOG | `version` is optional in Cursor's schema, and `update-lid`'s version-walk reads the `## LID` block + CHANGELOG, not a marketplace manifest. Including it would add strings to the release-step sync for no functional gain. Added at submission only if Cursor requires it. |
| Eval run-output fixtures (`skills/*-workspace/`) | Gitignored — excluded from the repo and therefore from both hosts' bundles | Keep committed; move to a top-level `eval-runs/` outside `plugins/` | The `*-workspace` trees are regenerable skill-creator run outputs (`iteration-N/eval-K/`), referenced by no `evals.json`, `SKILL.md`, or spec — pure accumulation, ~92% of plugin files. Gitignoring excludes them from both bundles with zero eval-runner breakage; the intent-bearing `evals/evals.json` definitions stay with each skill. Moving rather than removing preserves run history but keeps ~1.4 MB of scratch in the repo for no consumer. |

## Open Questions & Future Decisions

### Resolved

1. ✅ Component scope: CONTRIBUTING.md, AGENTS.md (+ CLAUDE.md symlink), docs/setup.md, .claude-plugin/marketplace.json, LICENSE.
2. ✅ EARS prefix: `PROJ-STRUCT-*`.
3. ✅ Component variant: content artifact (`HLD → LLD → EARS → content + assets`).
4. ✅ README ownership stays with `marketing-site`; this component references but does not own.
5. ✅ AGENTS.md is canonical; CLAUDE.md is a symlink to it.
6. ✅ Community-health files (`CODE_OF_CONDUCT.md`, `SECURITY.md`, `CITATION.cff`, `.github/` contribution templates) are owned by this component, folded in under single-ownership rather than spawned as separate components.

### Deferred

1. **CI integration of structural checks.** Wiring the link-check, JSON validity, plugin-source-path resolution, and symlink-integrity checks into a CI workflow — most cheaply by extending the marketing-site CI workflow once it exists — is achievable but not yet wired. Tracked as `PROJ-STRUCT-039` through `PROJ-STRUCT-041`.
2. **Contributor-licensing (CLA / DCO).** Still out of scope. If the project later adds a contributor-licensing mechanism, it folds into this component rather than spawning a new one unless it grows substantially.
3. **Cursor marketplace submission.** The `.cursor-plugin/` manifests make the plugins installable locally (`~/.cursor/plugins/local/`) and ready for submission; the actual publish to Cursor's reviewed marketplace (`cursor.com/marketplace/publish`) is a maintainer action taken once the manifests and the anchor-agnostic skill text have landed.
4. **Anchor-agnostic skill text is a cross-segment cascade.** For the plugins to behave correctly under Cursor, the skill bodies that read or write the instruction file (`update-lid` writing the `## LID` block; the workflow skill detecting mode) must treat `AGENTS.md` as the anchor under Cursor, not only `CLAUDE.md`. That intent lives in the `linked-intent-dev` core and `update-lid` LLD segments, not here; this segment pauses at the boundary and the skill-text cascade is walked separately. The same cascade covers per-skill host portability — all three plugins ship to Cursor, but Claude-orchestration-heavy skills (`map-codebase`, `bidirectional-differential`) carry their host-support limits in their own segments, not in the marketplace manifest.

## References

- `docs/high-level-design.md` — Goal 2 (minimum-system); Goal 4 (dogfooding); § Architecture / Methodology; § Architecture / Distribution; § Key Design Decisions / *The arrow for LID itself*; § Key Design Decisions / *Minimum-system discipline — the why*; § Key Design Decisions / *Cursor as a first-class plugin host*.
- `docs/intent/marketing-site/marketing-site-design.md` — sibling component in the onboarding taxonomy bucket; owns `README.md`; defines the content-artifact verification pattern this LLD reuses.
- `docs/intent/linked-intent-dev/linked-intent-dev-design.md` — defines the workflow `AGENTS.md` instantiates per-repo.
- `docs/intent/project-structure/project-structure-specs.md` — EARS specs for this component.
- `CONTRIBUTING.md`, `AGENTS.md`, `docs/setup.md`, `.claude-plugin/marketplace.json`, `CHANGELOG.md`, `LICENSE` — owned artifacts.
- `plugins/linked-intent-dev/CHANGELOG.md` — canonical changelog (repo-root `CHANGELOG.md` is its symlink alias); `linked-intent-dev`'s `.claude-plugin/plugin.json` carries the canonical LID version its top entry tracks.
- `plugins/linked-intent-dev/skills/linked-intent-dev/references/lld-templates.md` — LLD structure this document follows.
