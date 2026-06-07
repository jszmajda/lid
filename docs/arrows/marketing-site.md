# Arrow: marketing-site

The conversion and orientation surface — the four-page Eleventy site at `site/` that carries LID's positioning, the cascade demo, anti-patterns, and short paths into the README and repo.

## Status

**AUDITED** — last audited 2026-06-07 (git SHA `527cf08c9150`). 36 of 54 active specs implemented; 18 active gaps focused on the How-it-works five-panel trace block, theme system, build-time link checking, and README/Quickstart cascade behaviors. Added this cycle: the README badge row (`MKT-SITE-053`) and the ecosystem social-proof surface (`MKT-SITE-054` — README callout + Home Annex 03B).

## References

### HLD
- `docs/high-level-design.md` § Goal 5 (legibility for non-users); § Goal 3 (meet teams where they are); § Architecture / Distribution

### LLD
- `docs/intent/marketing-site/marketing-site-design.md`

### EARS
- `docs/intent/marketing-site/marketing-site-specs.md` (51 specs, prefix `MKT-SITE-*`)

### Tests / Build checks
- Build-time structural checks (link-check, mermaid render, markdown lint) — declared in the LLD § *Content Maintenance and Review*; CI workflow scope per `MKT-SITE-*` build specs.
- No skill-creator evals (content artifact, not a skill).

### Code (site sources)
- `site/.eleventy.js` — Eleventy config
- `site/package.json`, `site/package-lock.json`
- `site/src/` — page templates, content, assets, styles
- `site/_site/` — build output (gitignored / GitHub Pages publish source)

## Architecture

**Purpose:** Close the gap between "heard of LID" and "running LID" — convert evaluators with a structured pitch, orient newcomers by audience path (evaluating / greenfield / brownfield / scoped), demonstrate plasticity via a ~2-minute asciinema cascade demo, and surface honest non-fit on an anti-patterns page. Four pages, one terminal outbound (the GitHub repo).

**Key Components:**
1. **Home** — hero (pitch, framing, schematic) → How it works (five-panel trace + DAG) → cascade demo (asciinema embed) → Quickstart → four path links → repo CTA in hero.
2. **Start** — audience-path orientation (evaluating / greenfield / brownfield / scoped), each ~150 words.
3. **Examples** — two cards: `examples/urlshort/` (clean, minimal) and Threadkeeper (messy, real).
4. **Anti-patterns** — honest list of when LID is the wrong choice.

## Spec Coverage

| Category (per LLD groupings) | Implemented | Active gap | Deferred |
|---|---|---|---|
| Content / pages / framing | majority `[x]` | a few `[ ]` (notably the five-panel trace details) | 0 |
| README + ecosystem (badges `-053`, social proof `-054`) | 2 `[x]` | 0 | 0 |
| Theme & typography | partial — system-aware theme `[x]`; some build-time / a11y checks `[ ]` | | 0 |
| Build & deploy | partial — GitHub Pages deploy `[x]`; link-check strictness, README/Quickstart cascade `[ ]` | | 0 |
| **Total** | **36** | **18** | **0** |

**Summary:** 36 of 54 active specs implemented; 18 active gaps. The site is live and serves the core flow; this cycle added the README badge row (`MKT-SITE-053`) and the ecosystem social-proof surface (`MKT-SITE-054`). The largest remaining cluster is the How-it-works five-panel trace and its responsive layout (MKT-SITE-039, -041, -045, -047 and adjacent IDs).

## Key Findings

1. **Five-panel trace block is the dominant gap cluster.** MKT-SITE-039, -041, -045, -047 and several siblings (~7 of the 18 gaps) describe the vertical trace, its legend, the shared EARS-ID through-line, and the responsive two-column pair at ≥960px. These are content/layout work, not blocked design.
2. **README/Quickstart cascade behavior unimplemented.** MKT-SITE-009 — *"When the README's Quickstart changes, the site's Quickstart SHALL cascade to match before the next deploy"* — is `[ ]`. Currently a manual review responsibility; could be automated as a CI check or simply as a `/linked-intent-dev` cascade-discipline reminder.
3. **Site is a real LID-on-LID arrow segment.** Per `docs/intent/marketing-site/marketing-site-design.md` § *Cascade Concerns*: drift between site content and the HLD/plugin LLDs is a coherence-signal failure under HLD Goal 4. This bootstrap segment makes that auditable under `/arrow-maintenance` alongside the plugins (satisfies `MKT-SITE-036`).
4. **No `@spec` annotations in `site/` source files.** Content artifacts may carry `@spec` comments in HTML/template comments, but a quick scan turned up none. EARS coverage for content is currently spec-file-header-only — same LID-on-LID inversion as skill prompts. Acceptable; a future `arrow-maintenance` audit may want to add inline `@spec` comments to template files for grep-addressability into the content.

## Work Required

### Must Fix
1. Close the five-panel trace gap cluster (MKT-SITE-039, -041, -045, -047 and adjacent layout/responsive specs). This is the largest content debt on the site.
2. Implement README/Quickstart cascade verification (MKT-SITE-009) — at minimum a build-time check that the two Quickstart command blocks match.

### Should Fix
3. Close the remaining theme / build / a11y gaps (the other ~9 `[ ]` MKT-SITE specs).
4. Consider `@spec` annotations as HTML/template comments in `site/src/` so grep-addressability extends into the content layer.

### Nice to Have
5. Once `examples/urlshort/` exists, link from the Examples page (currently labeled in the LLD as not-yet-built).
