# Arrow: marketing-site

The conversion and orientation surface — the four-page Eleventy site at `site/` that carries LID's positioning, the cascade demo, anti-patterns, and short paths into the README and repo.

## Status

**AUDITED** — last audited 2026-06-07 (git SHA `527cf08c9150`); refreshed 2026-06-09 during the attestation and copy-effectiveness cascades, and 2026-06-11 for the portfolio-tracker exemplar cascade (`MKT-SITE-016` reframed to three lenses; `MKT-SITE-065`/`-066` added and implemented — Examples third card, Start Evaluating mention). 54 of 66 active specs implemented; 12 active gaps, concentrated in build-time checks (link strictness, mermaid, a11y contrast), README/Quickstart cascade behaviors, and process specs (`MKT-SITE-033`–`036`). Added this cycle: the attestation story beat (`MKT-SITE-055`–`059`), and the copy-effectiveness pass (`MKT-SITE-060`–`064` — pain-first hero lede, show-then-name vocabulary rule, not-a-waterfall statement, cost-honesty passage, and the Home Teams section between demo and Quickstart; `MKT-SITE-007` ordering amended accordingly). The five-panel trace cluster (`MKT-SITE-039/-041/-045/-047/-048/-049`) verified implemented (panels + dimension rail in `site/src/index.njk` and `main.css`) and its stale gap markers flipped.

## References

### HLD
- `docs/high-level-design.md` § Goal 5 (legibility for non-users); § Goal 3 (meet teams where they are); § Architecture / Distribution

### LLD
- `docs/intent/marketing-site/marketing-site-design.md`

### EARS
- `docs/intent/marketing-site/marketing-site-specs.md` (66 specs, prefix `MKT-SITE-*`)

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
3. **Examples** — three cards: `examples/urlshort/` (clean, minimal), portfolio-tracker (complete, end-to-end), and Threadkeeper (messy, real).
4. **Anti-patterns** — honest list of when LID is the wrong choice.

## Spec Coverage

| Category (per LLD groupings) | Implemented | Active gap | Deferred |
|---|---|---|---|
| Content / pages / framing (incl. five-panel trace, attestation beat `-055`–`-058`) | majority `[x]` | `[ ]` MKT-SITE-012, -015, -023 | 0 |
| README + ecosystem (badges `-053`, social proof `-054`, two-payoff passage `-059`) | 3 `[x]` | 0 | 0 |
| Theme & typography | system-aware theme `[x]`; a11y contrast check `[ ]` (-026) | | 0 |
| Build & deploy | GitHub Pages deploy `[x]`; mermaid/link-check strictness `[ ]` (-027/-028/-029), README/Quickstart cascade `[ ]` (-009) | | 0 |
| Cascade & coherence process | `[x]` MKT-SITE-037 | `[ ]` MKT-SITE-033–036 | 0 |
| **Total** | **47** | **12** | **0** |

**Summary:** 47 of 59 active specs implemented; 12 active gaps. The site is live and serves the core flow. This cycle added the attestation story (`MKT-SITE-055`–`059`), cascading from HLD § Linkage's two-payoff framing (navigation + attestation); the five-panel trace cluster was verified implemented and its stale markers corrected. Remaining gaps are build-time checks and process specs, not content debt.

## Key Findings

1. **Attestation beat carried by existing elements.** The verification story (lede claim, grep-note proof chain, outro review posture, README passage) landed inside the existing How-it-works structure per LLD Resolved 26 — no new page or section. The `MKT-SITE-058` guard (mechanism, never a trust or compliance claim) binds all attestation copy on site and README.
2. **README/Quickstart cascade behavior unimplemented.** MKT-SITE-009 — *"When the README's Quickstart changes, the site's Quickstart SHALL cascade to match before the next deploy"* — is `[ ]`. Currently a manual review responsibility; could be automated as a CI check or simply as a `/linked-intent-dev` cascade-discipline reminder.
3. **Site is a real LID-on-LID arrow segment.** Per `docs/intent/marketing-site/marketing-site-design.md` § *Cascade Concerns*: drift between site content and the HLD/plugin LLDs is a coherence-signal failure under HLD Goal 4. This bootstrap segment makes that auditable under `/arrow-maintenance` alongside the plugins (satisfies the intent of `MKT-SITE-036`; the spec itself remains `[ ]` pending the named index entry being kept current as schema evolves).
4. **`@spec` annotations now present in `site/src/index.njk`.** Section-level HTML comments cite the MKT-SITE specs each block implements. Coverage of the other page templates (`start.njk`, `examples.njk`, `anti-patterns.njk`) is still spec-file-header-only.
5. **SHA bookkeeping mismatch.** This doc's audited SHA (`527cf08c9150`) and `index.yaml`'s (`65a143750760`) disagree for the same 2026-06-07 audit — surfaced for the next `/arrow-maintenance` pass to reconcile; not repaired here.

## Work Required

### Must Fix
1. Implement README/Quickstart cascade verification (MKT-SITE-009) — at minimum a build-time check that the two Quickstart command blocks match.

### Should Fix
2. Close the remaining build / a11y / process gaps (MKT-SITE-012, -015, -023, -026, -027, -028, -029, -033–036).
3. Extend `@spec` HTML-comment annotations to the remaining page templates.

### Nice to Have
4. Once `examples/urlshort/` exists, link from the Examples page (currently labeled in the LLD as not-yet-built).
