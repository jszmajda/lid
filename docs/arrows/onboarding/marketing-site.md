# Arrow: marketing-site

The conversion and orientation surface — the five-page Eleventy site at `site/` that carries LID's positioning, the cascade demo, anti-patterns, and short paths into the README and repo.

## Status

**AUDITED** — last audited 2026-06-07 (git SHA `527cf08c9150`); refreshed 2026-06-09 during the attestation and copy-effectiveness cascades, and 2026-06-11 for the portfolio-tracker exemplar cascade (`ONB-SITE-016` reframed to three lenses; `ONB-SITE-065`/`-066` added and implemented — Examples third card, Start Evaluating mention), and 2026-11-09 for the site refresh (Nodes logo, Linked list look, Home rebuilt around the free-trial example and the rings drawing; Logo Ideas page and the five-panel trace removed), and 2026-11-11 for the cascade recording (the recording now shows the change explainer's own change in the `cascade-recording` segment's trial project; `ONB-SITE-003` rewritten for the new scenario, `ONB-SITE-110` re-headed, `ONB-SITE-134` added for the committed cast, which records the asciinema.org address it was uploaded to). 101 of 113 specs implemented; 12 active gaps, concentrated in build-time checks (link strictness, mermaid, a11y contrast), README/Quickstart cascade behaviors, and process specs (`ONB-SITE-033`–`036`). Added this cycle: the attestation story beat (`ONB-SITE-055`–`059`), and the copy-effectiveness pass (`ONB-SITE-060`–`064` — pain-first hero lede, show-then-name vocabulary rule, not-a-waterfall statement, cost-honesty passage, and the Home Teams section between demo and Quickstart; `ONB-SITE-007` ordering amended accordingly). Re-parented under the `onboarding` sub-HLD on 2026-11-15: its IDs moved from `MKT-SITE-*` to `ONB-SITE-*`, with every citation rewritten in the same change. On 2026-11-16 the Examples pages moved to the new `examples-showcase` segment: `ONB-SITE-013`–`016` and `065` were removed, `ONB-SITE-021` now allows showcased projects merged by pull request and nothing else from outside, and `ONB-SITE-069`'s receipt links the Examples page. 97 of 108 specs implemented; 11 active gaps. 2026-11-17: link previews on every page (`ONB-SITE-135`–`139`: canonical address, Open Graph and Twitter card tags, and a default 1200×630 card made from `site/brand/social/`); 102 of 113 implemented. 2026-11-19: the footer's links to this design doc and its specs pointed at their paths from before the `onboarding` re-parent; fixed, and `ONB-SITE-140` now checks that every link into the repository resolves (103 of 114).

## References

### Parent
- `docs/intent/onboarding/onboarding-design.md` (sub-HLD `onboarding`: shared reader, voice, claims rule, the free-trial example, and content the site presents)

### HLD
- `docs/high-level-design.md` § Goal 5 (legible to people who learn LID by reading); § Goal 3 (meet teams where they are); § Architecture / Distribution

### LLD
- `docs/intent/onboarding/marketing-site/marketing-site-design.md`

### EARS
- `docs/intent/onboarding/marketing-site/marketing-site-specs.md` (114 specs, prefix `ONB-SITE-*`)

### Tests / Build checks
- Build-time structural checks (link-check, mermaid render, markdown lint) — declared in the LLD § *Content Maintenance and Review*; CI workflow scope per `ONB-SITE-*` build specs.
- `site/tests/site.test.js` — checks the built pages (`node --test site/tests/site.test.js`).
- `site/tests/rings.test.js` — checks the rings drawing's module (`node --test site/tests/rings.test.js`).
- No skill-creator evals (content artifact, not a skill).

### Code (site sources)
- `site/.eleventy.js` — Eleventy config
- `site/package.json`, `site/package-lock.json`
- `site/src/` — page templates, content, assets, styles
- `site/_site/` — build output (gitignored / GitHub Pages publish source)

## Architecture

**Purpose:** Close the gap between "heard of LID" and "running LID" — convert evaluators with a structured pitch, orient newcomers by audience path (evaluating / greenfield / brownfield / scoped), demonstrate plasticity via a ~2-minute asciinema cascade demo, and surface honest non-fit on an anti-patterns page. Five pages, one terminal outbound (the GitHub repo).

**Key Components:**
1. **Home** — hero (question, framing, the still rings drawing) → the gap (the free-trial request) → narrowing explainer → change explainer and cascade recording → check it yourself (grep + DAG) → where your time goes and the price → Teams → Quickstart → experimental → ecosystem → four path links. The rings drawing comes from `site/src/assets/js/rings.js`, rendered static at build time (`site/src/_data/rings.js`) and animated in the browser.
2. **Start** — audience-path orientation (evaluating / greenfield / brownfield / scoped), each ~150 words.
3. **Examples** — owned by the `examples-showcase` segment; this segment provides its navigation, look, build, and copy register.
4. **Anti-patterns** — honest list of when LID is the wrong choice.
5. **Tour** — the newcomer tour's steps and topics, rendered from the `tour` segment's files.

## Spec Coverage

| Category (per LLD groupings) | Implemented | Active gap | Deferred |
|---|---|---|---|
| Content / pages / framing (incl. attestation beat `-055`–`-058`) | majority `[x]` | `[ ]` ONB-SITE-012, -015, -023 | 0 |
| Home: the gap, the explainers, the rings drawing (`-099`–`-124`, `-133`) | 27 `[x]` | 0 | 0 |
| Visual identity and navigation (`-125`–`-132`) | 8 `[x]` | 0 | 0 |
| README + ecosystem (badges `-053`, social proof `-054`, two-payoff passage `-059`) | 3 `[x]` | 0 | 0 |
| Theme & typography | system-aware theme `[x]`; a11y contrast check `[ ]` (-026) | | 0 |
| Build & deploy | GitHub Pages deploy `[x]`; mermaid/link-check strictness `[ ]` (-027/-028/-029), README/Quickstart cascade `[ ]` (-009) | | 0 |
| Cascade & coherence process | `[x]` ONB-SITE-037 | `[ ]` ONB-SITE-033–036 | 0 |
| Tour page (`-072`–`-082`) | 11 `[x]` | 0 | 0 |
| **Total** | **101** | **12** | **0** |

**Summary:** 101 of 113 specs implemented; 12 active gaps. The site is live and serves the core flow, and the Tour page (`ONB-SITE-072`–`082`) renders the newcomer tour from the `tour` segment's files. The 2026-06 cycles added the attestation story (`ONB-SITE-055`–`059`), cascading from HLD § Linkage's two-payoff framing (navigation + attestation); the five-panel trace cluster was verified implemented and its stale markers corrected. Remaining gaps are build-time checks and process specs, not content debt.

## Key Findings

1. **Attestation beat carried by existing elements.** The verification story (lede claim, grep-note proof chain, outro review posture, README passage) landed inside the existing How-it-works structure per LLD Resolved 26 — no new page or section. The `ONB-SITE-058` guard (mechanism, never a trust or compliance claim) binds all attestation copy on site and README.
2. **README/Quickstart cascade behavior unimplemented.** ONB-SITE-009 — *"When the README's Quickstart changes, the site's Quickstart SHALL cascade to match before the next deploy"* — is `[ ]`. Currently a manual review responsibility; could be automated as a CI check or simply as a `/linked-intent-dev` cascade-discipline reminder.
3. **Site is a real LID-on-LID arrow segment.** Per `docs/intent/onboarding/marketing-site/marketing-site-design.md` § *Cascade Concerns*: drift between site content and the HLD/plugin LLDs is a coherence-signal failure under HLD Goal 4. This bootstrap segment makes that auditable under `/arrow-maintenance` alongside the plugins (satisfies the intent of `ONB-SITE-036`; the spec itself remains `[ ]` pending the named index entry being kept current as schema evolves).
4. **`@spec` annotations and tests.** Section-level HTML comments in the page templates, the layout, the navigation, and the rings module cite the ONB-SITE specs they implement. `site/tests/site.test.js` checks the built pages and `site/tests/rings.test.js` checks the rings module's states, pacing, and static drawing; `ONB-SITE-132` (no sideways scroll at 360px) is checked in a browser, not in the suite.
5. **SHA bookkeeping mismatch.** This doc's audited SHA (`527cf08c9150`) and `index.yaml`'s (`65a143750760`) disagree for the same 2026-06-07 audit — surfaced for the next `/arrow-maintenance` pass to reconcile; not repaired here.

## Work Required

### Must Fix
1. Implement README/Quickstart cascade verification (ONB-SITE-009) — at minimum a build-time check that the two Quickstart command blocks match.

### Should Fix
2. Close the remaining build / a11y / process gaps (ONB-SITE-012, -015, -023, -026, -027, -028, -029, -033–036).

### Nice to Have
4. Once `examples/urlshort/` exists, link from the Examples page (currently labeled in the LLD as not-yet-built).
