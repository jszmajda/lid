# Arrow: project-structure

The repo-meta segment — owns the artifacts that describe the project itself rather than any one piece of it: contributor onboarding (`CONTRIBUTING.md`), agent bootstrap (`AGENTS.md` + `CLAUDE.md` symlink), per-tool integration setup (`docs/setup.md`), the Claude Code marketplace manifest (`.claude-plugin/marketplace.json`), and `LICENSE`.

## Status

**MAPPED** — bootstrapped on 2026-05-05. 39 of 42 active specs implemented; 3 active gaps cluster around build-time structural checks deferred until CI workflow scope is decided. (Git SHA recorded by `/arrow-maintenance` on first audit.)

## References

### HLD
- `docs/high-level-design.md` § Goal 2 (minimum-system); § Goal 4 (dogfooding); § Architecture / Methodology; § Architecture / Distribution; § Key Design Decisions / *The arrow for LID itself*; § Key Design Decisions / *Minimum-system discipline — the why*

### LLD
- `docs/llds/project-structure.md`

### EARS
- `docs/specs/project-structure-specs.md` (42 specs, prefix `PROJ-STRUCT-*`)

### Tests / Build checks
- Build-time structural checks (link-check on `CONTRIBUTING.md` and `docs/setup.md`, JSON validity on `marketplace.json`, symlink integrity on `CLAUDE.md`, plugin-source-path validity in `marketplace.json`) — declared in the LLD § *Component Variant*; CI workflow scope deferred (see `PROJ-STRUCT-039` through `PROJ-STRUCT-041`).
- No skill-creator evals (content artifact, not a skill).

### Code (owned artifacts)
- `CONTRIBUTING.md` — contributor onboarding
- `AGENTS.md` — agent bootstrap (canonical)
- `CLAUDE.md` — symlink to `AGENTS.md`
- `docs/setup.md` — per-tool adapter setup
- `.claude-plugin/marketplace.json` — Claude Code plugin marketplace manifest
- `LICENSE` — MIT license

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
| CONTRIBUTING.md (audience, trivial, out-of-scope, variants, gate, mechanics) | 18 `[x]` | 0 | 0 |
| AGENTS.md / CLAUDE.md | 5 `[x]` | 0 | 0 |
| docs/setup.md | 4 `[x]` | 0 | 0 |
| .claude-plugin/marketplace.json | 3 `[x]` | 0 | 0 |
| README pointer | 2 `[x]` | 0 | 0 |
| LICENSE | 1 `[x]` | 0 | 0 |
| Cascade obligations | 5 `[x]` | 0 | 0 |
| Build-time checks | 0 | 3 `[ ]` | 0 |
| Arrow registration | 1 `[x]` | 0 | 0 |
| **Total** | **39** | **3** | **0** |

**Summary:** 39 of 42 active specs implemented at bootstrap; 3 active gaps. The owned content artifacts are all in place and current. The gap cluster is build-time structural checks (PROJ-STRUCT-039, 040, 041) deferred until a CI workflow extends from `marketing-site`'s scope or stands up alongside it.

## Key Findings

1. **Leaf in the arrow graph.** `blocks: []` because no other segment depends on the meta-artifacts; `blockedBy: [linked-intent-dev]` because `AGENTS.md` instantiates the workflow defined upstream there. Cross-segment cascade reaches this segment but does not propagate further from it.
2. **README ownership stays with `marketing-site`.** Cross-segment cascade pauses at the boundary per the HLD tenet *within-segment cascade is free; across-segment cascade pauses*. `project-structure` references `README.md`'s existence (PROJ-STRUCT-031) but does not claim or duplicate its content; the marketing-site LLD remains the single owner.
3. **`CLAUDE.md` symlink is the zero-drift implementation of the cross-tool filename convention.** `AGENTS.md` is canonical (the cross-tool spec); `CLAUDE.md` resolves to it via symlink. The reverse-direction alternative (content in `CLAUDE.md`, `AGENTS.md` as `@CLAUDE.md` import) is documented in `docs/setup.md` for users whose Claude-Code-first projects prefer it, but is not used in this repo.
4. **All cascade specs (PROJ-STRUCT-034 through 038) are review-discipline obligations.** They name the maintainer's responsibility to review owned artifacts when specific upstream sources change. They are marked `[x]` because the obligation is in effect once stated; their effectiveness is verified by the next dogfooding pass after each upstream change.
5. **Build-time checks are the only deferred work.** Three specs (PROJ-STRUCT-039 link-check, 040 marketplace.json validity + plugin-source matching, 041 symlink integrity) are achievable as either an extension to the marketing-site CI workflow or a small standalone job. None block the segment from being MAPPED.

## Work Required

### Must Fix
*(none)* — all non-deferred specs implemented at bootstrap.

### Should Fix
1. **PROJ-STRUCT-039** — wire link-check for `CONTRIBUTING.md` and `docs/setup.md` into a CI workflow (extending the marketing-site link-check job if/when that workflow exists is the cheapest path).
2. **PROJ-STRUCT-040** — wire JSON validity + plugin-source-path resolution check for `.claude-plugin/marketplace.json`.
3. **PROJ-STRUCT-041** — wire symlink-integrity check for `CLAUDE.md → AGENTS.md`.

### Nice to Have
*(none yet)* — open questions in the LLD list CODE_OF_CONDUCT, governance, and contributor-licensing as future work that would fold into this segment, but only if a concrete need arises.
