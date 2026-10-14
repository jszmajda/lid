# Arrow: project-structure

The repo-meta segment — owns the artifacts that describe the project itself rather than any one piece of it: contributor onboarding (`CONTRIBUTING.md`), agent bootstrap (`AGENTS.md` + `CLAUDE.md` symlink), per-tool integration setup (`docs/setup.md`), the Claude Code and Cursor marketplace manifests, `CHANGELOG.md`, `.gitignore`, `LICENSE`, the community-health files (`CODE_OF_CONDUCT.md`, `SECURITY.md`, `CITATION.cff`, `.github/` contribution templates), and the `README`/`EXTENSIONS` ownership pointers.

## Status

**AUDITED** — last audited 2026-06-07 (git SHA `527cf08c9150`); revised 2026-10-24 by the packaging-checks change (#86, #87). 80 of 80 active specs implemented. The former build-time checks (`PROJ-STRUCT-039`–`041`) are superseded by the `packaging-checks` segment, which now verifies this segment's rules.

## References

### HLD
- `docs/high-level-design.md` § Goal 2 (minimum-system); § Goal 4 (dogfooding); § Architecture / Methodology; § Architecture / Distribution; § Key Design Decisions / *The arrow for LID itself*; § Key Design Decisions / *Minimum-system discipline — the why*

### LLD
- `docs/intent/project-structure/project-structure-design.md`

### EARS
- `docs/intent/project-structure/project-structure-specs.md` (80 active specs, prefix `PROJ-STRUCT-*`; `-014` retired; `-039`–`-041` and `-061` superseded)

### Tests / Build checks
- The `packaging-checks` segment's tool (`tools/packaging-checks/`) verifies this segment's rules before every merge: skill and command files, frontmatter, the shared version and CHANGELOG, the workflow doc, links in `CONTRIBUTING.md` and `docs/setup.md`, marketplace manifests, and the `CLAUDE.md` symlink.
- No skill-creator evals (content artifact, not a skill).

### Code (owned artifacts)
- `CONTRIBUTING.md` — contributor onboarding
- `AGENTS.md` — agent bootstrap (canonical)
- `CLAUDE.md` — symlink to `AGENTS.md`
- `docs/setup.md` — per-tool adapter + first-class plugin-host setup (Claude Code, Cursor) + skills host (opencode)
- `.claude-plugin/marketplace.json` + per-plugin `.claude-plugin/plugin.json` — Claude Code manifests (the shared version lives only in each `plugin.json`)
- `.cursor-plugin/marketplace.json` + per-plugin `.cursor-plugin/plugin.json` — Cursor manifests (no `version`)
- `CHANGELOG.md` — release history (canonical in `plugins/linked-intent-dev/`, root symlink)
- `.gitignore` — excludes regenerable eval run-output trees
- `CODE_OF_CONDUCT.md`, `SECURITY.md`, `CITATION.cff` — community-health artifacts
- `.github/ISSUE_TEMPLATE/` + `.github/PULL_REQUEST_TEMPLATE.md` — contribution templates
- `LICENSE` — MIT license
- (pointers only, owned elsewhere: `README.md` → marketing-site; `EXTENSIONS.md` → extensions)

## Architecture

**Purpose:** Give the repository's meta-artifacts a single arrow-of-intent owner so the contributor surface, the agent bootstrap, the per-tool integration story, and the distribution manifest stay coherent with the HLD they cascade from. Until this segment was created, none of these had an upstream LLD — `CONTRIBUTING.md` in particular was load-bearing for codifying the minimum-surface gate and the out-of-scope categories, with no place for those statements to trace to.

**Key Components:**
1. **`CONTRIBUTING.md`** — human preamble + agent-facing body. Covers the bar, trivial-change carve-out, out-of-scope principle and concrete declined categories, arrow-variant decision tree by change type, the minimum-surface gate (quoted from HLD), and PR mechanics including the atomic-improvement framing.
2. **`AGENTS.md` (canonical) + `CLAUDE.md` (symlink)** — per-repo invocation of the LID workflow. Describes the methodology, the LID Mode declaration, and provides a navigation table to canonical doc locations. Symlink resolves identically for tools that read either filename.
3. **`docs/setup.md`** — two-layer per-tool guide: a table of tools that honor a repo-root `AGENTS.md` natively, and per-tool sections with adapter snippets for tools that need them. Repo does not ship adapter files itself.
4. **`.claude-plugin/marketplace.json`** — declares the three first-party plugins (`linked-intent-dev`, `arrow-maintenance`, `lid-experimental`) with `source` paths matching directories under `plugins/`.
5. **`LICENSE`** — MIT license at repo root.

## Spec Coverage

| Category (per LLD groupings) | Implemented | Active gap | Deferred |
|---|---|---|---|
| CONTRIBUTING.md (audience, trivial, out-of-scope, variants, gate, mechanics incl. packaging checks `-070`) | 18 `[x]` | 0 | 0 |
| AGENTS.md / CLAUDE.md (incl. `tools/` `-068`, editing guidelines `-071`) | 7 `[x]` | 0 | 0 |
| docs/setup.md (incl. plugin hosts `-062`, opencode skills host `-072`) | 6 `[x]` | 0 | 0 |
| .claude-plugin/marketplace.json (no `version`, `-030`) | 3 `[x]` | 0 | 0 |
| .cursor-plugin manifests (`-056`–`-058`, `-060`) | 4 `[x]` | 0 | 0 |
| Repo-root file pointers | 3 `[x]` | 0 | 0 |
| .gitignore / .claude/settings.json | 5 `[x]` | 0 | 0 |
| LICENSE, CODE_OF_CONDUCT, SECURITY, CITATION | 5 `[x]` | 0 | 0 |
| .github/ contribution templates (PR template's *Packaging checks* line, `-053`) | 3 `[x]` | 0 | 0 |
| Skill and command files (`-073`–`-076`, `-084`) | 5 `[x]` | 0 | 0 |
| CHANGELOG, versions, releases (`-043`–`-046`, `-054`, `-063`, `-077`–`-081`) | 11 `[x]` | 0 | 0 |
| Cascade obligations (incl. `-082`, `-083`, `-085`) | 9 `[x]` | 0 | 0 |
| Arrow registration | 1 `[x]` | 0 | 0 |
| **Total** (recounted from the spec file) | **80** | **0** | **0** |

**Summary:** 80 of 80 active specs implemented. The packaging-checks change (#86, #87) added the rules for skill and command files (`073`–`076`, `084`), the shared version and the release step that travels with each change (`046`, `077`–`081`), the opencode skills host (`072`, `085`), and the pull-request record (`053`, `070`); it superseded the build-time-check specs `039`–`041` (now `PKG-CHECK-018`–`020`) and the No-Version-Update section `061`.

## Key Findings

1. **Blocks `packaging-checks`.** The packaging checks enforce this segment's rules, so `blocks: [packaging-checks]`; `blockedBy: [linked-intent-dev]` because `AGENTS.md` instantiates the workflow defined upstream there.
2. **README ownership stays with `marketing-site`.** Cross-segment cascade pauses at the boundary per the HLD tenet *within-segment cascade is free; across-segment cascade pauses*. `project-structure` references `README.md`'s existence (PROJ-STRUCT-031) but does not claim or duplicate its content; the marketing-site LLD remains the single owner.
3. **`CLAUDE.md` symlink is the zero-drift implementation of the cross-tool filename convention.** `AGENTS.md` is canonical (the cross-tool spec); `CLAUDE.md` resolves to it via symlink. The reverse-direction alternative (content in `CLAUDE.md`, `AGENTS.md` as `@CLAUDE.md` import) is documented in `docs/setup.md` for users whose Claude-Code-first projects prefer it, but is not used in this repo.
4. **All cascade specs (PROJ-STRUCT-034 through 038) are review-discipline obligations.** They name the maintainer's responsibility to review owned artifacts when specific upstream sources change. They are marked `[x]` because the obligation is in effect once stated; their effectiveness is verified by the next dogfooding pass after each upstream change.
5. **The rules live here; the checks live in `packaging-checks`.** Skill and command layout, frontmatter form, the shared version, the CHANGELOG, and the manifests are this segment's intent; the tool that verifies them before each merge is its own segment.

## Work Required

### Must Fix
*(none)* — all non-deferred specs implemented at bootstrap.

### Should Fix
*(none)*

### Nice to Have
*(none yet)* — open questions in the LLD list CODE_OF_CONDUCT, governance, and contributor-licensing as future work that would fold into this segment, but only if a concrete need arises.
