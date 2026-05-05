# Project Structure

## Context and Design Philosophy

Project Structure owns the repository's meta-artifacts — the documents and configuration that describe the project as a whole rather than any one piece of it. Five artifacts are in scope:

- `CONTRIBUTING.md` — contributor onboarding
- `AGENTS.md` (canonical) and `CLAUDE.md` (symlink alias) — agent bootstrap entry point
- `docs/setup.md` — per-tool integration setup for non-Claude-Code agents
- `.claude-plugin/marketplace.json` — Claude Code plugin marketplace manifest
- `LICENSE` — MIT license

Three principles shape the component:

- **Single ownership for repo-meta surface.** Each artifact above describes the project as a whole. Distributing them across multiple LLDs would leave individual documents over-scoped (e.g., the marketing-site LLD reasoning about contributor mechanics) or unowned. One LLD covering all of them keeps the cascade coherent and the boundaries clean.
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

Per-tool setup guide for non-Claude-Code agents. Two layers:

1. **The simple path** — a table of tools that honor a repo-root `AGENTS.md` natively without an adapter (Codex CLI, Amp, Jules, Pi, Zed, Cline, JetBrains Junie, Copilot in supported surfaces, Windsurf, and the broader `agents.md`-spec-compliant set).
2. **Per-tool sections** — explicit adapter snippets for tools that need or benefit from a separate rule file (Cursor's `.cursor/rules/lid.mdc`, Copilot's `.github/copilot-instructions.md`, etc.).

The repository does not ship adapter files. Users drop the appropriate adapter into their own LID project per `docs/setup.md`. This keeps LID one source of truth (`AGENTS.md`) with N thin adapter pointers across the ecosystem.

### `.claude-plugin/marketplace.json`

Claude Code marketplace manifest. Declares the three first-party plugins shipped from this repository — `linked-intent-dev`, `arrow-maintenance`, `lid-experimental` — with their source paths, versions, categories, and licenses. Each plugin entry's `source` field resolves to a directory under `plugins/`. Install commands shown in `README.md` and `docs/setup.md` resolve through this manifest.

### `LICENSE`

MIT license at repository root.

## Cascade

- **HLD Goal 2** (minimum-system, surface-growth resistance) → review `CONTRIBUTING.md`'s *Out of scope* and *Minimum-surface gate* sections for claim drift.
- **HLD Goal 4** (dogfooding signals) → review `CONTRIBUTING.md`'s *Tests, or justify* framing.
- **HLD § Key Design Decisions / *The arrow for LID itself*** — when the variant set changes (new variant added, existing one revised) → `CONTRIBUTING.md`'s arrow-variant decision tree absorbs the change.
- **HLD § Architecture / Methodology** — when the workflow itself changes (rare; itself an HLD-level edit) → `AGENTS.md` updates.
- **Plugin added under `plugins/`, removed, or renamed** → `.claude-plugin/marketplace.json` adds or updates the entry; `README.md` and `docs/setup.md` install commands cascade.
- **New supported coding tool** → `docs/setup.md` gains either a row in the simple-path table or a per-tool section with an adapter snippet.

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

## Open Questions & Future Decisions

### Resolved

1. ✅ Component scope: CONTRIBUTING.md, AGENTS.md (+ CLAUDE.md symlink), docs/setup.md, .claude-plugin/marketplace.json, LICENSE.
2. ✅ EARS prefix: `PROJ-STRUCT-*`.
3. ✅ Component variant: content artifact (`HLD → LLD → EARS → content + assets`).
4. ✅ README ownership stays with `marketing-site`; this component references but does not own.
5. ✅ AGENTS.md is canonical; CLAUDE.md is a symlink to it.

### Deferred

1. **CI integration of structural checks.** Wiring the link-check, JSON validity, plugin-source-path resolution, and symlink-integrity checks into a CI workflow — most cheaply by extending the marketing-site CI workflow once it exists — is achievable but not yet wired. Tracked as `PROJ-STRUCT-039` through `PROJ-STRUCT-041`.
2. **CODE_OF_CONDUCT, governance, contributor-licensing.** Out of scope today. If the project later adds any of these, they fold into this component rather than spawning new ones unless they grow substantially.

## References

- `docs/high-level-design.md` — Goal 2 (minimum-system); Goal 4 (dogfooding); § Architecture / Methodology; § Architecture / Distribution; § Key Design Decisions / *The arrow for LID itself*; § Key Design Decisions / *Minimum-system discipline — the why*.
- `docs/llds/marketing-site.md` — sibling component in the onboarding taxonomy bucket; owns `README.md`; defines the content-artifact verification pattern this LLD reuses.
- `docs/llds/linked-intent-dev.md` — defines the workflow `AGENTS.md` instantiates per-repo.
- `docs/specs/project-structure-specs.md` — EARS specs for this component.
- `CONTRIBUTING.md`, `AGENTS.md`, `docs/setup.md`, `.claude-plugin/marketplace.json`, `LICENSE` — owned artifacts.
- `plugins/linked-intent-dev/skills/linked-intent-dev/references/lld-templates.md` — LLD structure this document follows.
