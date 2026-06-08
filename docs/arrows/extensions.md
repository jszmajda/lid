# Arrow: extensions

The third-party extensions segment — owns LID's discovery convention for independent projects that build on it, plus the curated `EXTENSIONS.md` showcase. Discovery is by open convention (canonical GitHub topic `linked-intent-development` + link-back), not a registry LID operates.

## Status

**AUDITED** — last audited 2026-06-07 (git SHA `527cf08c9150`). New leaf segment (landed via PR #34). 6 of 7 active specs implemented; 1 deferred-gap (link-check, awaiting CI).

## References

### HLD
- `docs/high-level-design.md` § Goal 2 (minimum-system); § Architecture / Distribution / *Third-party ecosystem*; § *Minimum-system discipline — the why*; Non-Goal *Not a factory*

### LLD
- `docs/intent/extensions/extensions-design.md`

### EARS
- `docs/intent/extensions/extensions-specs.md` (7 specs, prefix `EXT-*`)

### Tests / Build checks
- Build-time link integrity on `EXTENSIONS.md` — deferred (`EXT-007`, no CI wired; tracked with `PROJ-STRUCT-039`–`041`).
- No skill-creator evals (content artifact, not a skill).

### Code (owned artifacts)
- `EXTENSIONS.md` — curated showcase + the discovery-convention / "how to get listed" section + non-endorsement disclaimer
- the `linked-intent-development` GitHub topic on the core repository (configuration; anchors the topic page)

## Architecture

**Purpose:** Make the third-party ecosystem that fills LID's deliberately-minimal core (editor plugins, language servers, CLIs, CI checkers, MCP servers) discoverable, while LID hosts, runs, and gatekeeps none of it.

**Key Components:**
1. **Discovery convention** — extension repos tag themselves `linked-intent-development` and link back to the core repo; the core repo carries the topic to anchor the topic page. Open: no submission or approval step.
2. **`EXTENSIONS.md`** — curated editorial showcase (currently `EtaCassiopeia/lid-tooling`) + the "how to get listed" convention doc + a non-endorsement disclaimer. Curation never gates discovery.

## Spec Coverage

| Category | Spec IDs | Implemented | Deferred | Gaps |
|---|---|---|---|---|
| EXTENSIONS.md | EXT-001 to EXT-003 | 3 `[x]` | 0 | 0 |
| Discovery convention | EXT-004 to EXT-006 | 3 `[x]` | 0 | 0 |
| Verification | EXT-007 | 0 | 0 | 1 `[ ]` |
| **Total** | | **6** | **0** | **1** |

**Summary:** 6 of 7 active specs implemented. The one gap (`EXT-007`, broken-link check on `EXTENSIONS.md`) is deferred alongside the `PROJ-STRUCT-039`–`041` build-check backlog — no CI is wired yet.

## Key Findings

1. **`EXTENSIONS.md` owned here despite repo-root location.** Ownership follows intent (ecosystem), not file location — the same pattern as `README.md` → `marketing-site`. `PROJ-STRUCT-055` is project-structure's pointer acknowledging this segment owns the file.
2. **The `linked-intent-development` topic is in-arrow (`EXT-005`)** while generic discoverability topics stay out-of-arrow ops — it is load-bearing convention infrastructure.
3. **`marketing-site` is a cascade consumer (`MKT-SITE-054`)** — it surfaces the ecosystem as a trust signal; the substance (convention + showcase) is owned here.

## Work Required

### Should Fix
1. **EXT-007** — wire a broken-link check for `EXTENSIONS.md` into CI (folds into the `PROJ-STRUCT-039`–`041` build-check workflow when it lands).

### Nice to Have
2. Firm up the link-back marker and the `EXTENSIONS.md` inclusion bar as the ecosystem grows (see the LLD's Open Questions).
