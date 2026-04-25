# Marketing Site Specs

**LLD**: docs/llds/marketing-site.md
**Implementing artifacts**:
- site/src/**
- site/_site/** (build output)
- .github/workflows/site-build.yml

Status markers: `[x]` implemented · `[ ]` active gap · `[D]` deferred

---

## Home: Pitch and Framing

- `[x]` **MKT-SITE-001**: When a user loads the home page, the site SHALL present a single-sentence pitch synchronized with the opening of the repository README.
- `[x]` **MKT-SITE-002**: When a user loads the home page, the site SHALL present the three-line framing: "LID is the language. Claude is the compiler. Code is the output."
- `[x]` **MKT-SITE-003**: When a user loads the home page, the site SHALL embed an asciinema recording whose scenario is a cascade demonstration — an HLD or LLD edit in a live LID project, propagating through specs, tests, and code.
- `[x]` **MKT-SITE-004**: When a user loads the home page, the site SHALL link to the GitHub repository as its single primary call-to-action.
- `[x]` **MKT-SITE-005**: When a user loads the home page, the site SHALL present four audience-path links (evaluating, greenfield, brownfield, scoped), each linking to the corresponding section on the Start page.

## Home: Quickstart

- `[x]` **MKT-SITE-006**: When a user loads the home page, the site SHALL present a Quickstart section containing copy-pastable install commands with a one-line explanation per command.
- `[x]` **MKT-SITE-007**: The home page SHALL present its primary sections in this order: hero, How it works, cascade demo, Quickstart, audience-path links.
- `[x]` **MKT-SITE-008**: The Quickstart commands SHALL match the repository README's Quickstart section exactly.
- `[ ]` **MKT-SITE-009**: When the README's Quickstart changes, the site's Quickstart SHALL cascade to match before the next deploy.
- `[x]` **MKT-SITE-040**: The hero SHALL include a primary call-to-action that anchor-links to the Quickstart section on the same page, so an evaluator who has already decided can reach the install commands without scrolling past the structural orientation content.
- `[x]` **MKT-SITE-050**: The Home page SHALL include a peer "Annex" section (placed between the Quickstart and the audience-path links) that surfaces the existence of the `lid-experimental` plugin as an optional, opt-in install — naming the plugin, showing its install command, framing it as not part of the core install path, and linking to the plugin's user-facing README — so an evaluator learns the experimental capabilities exist without those capabilities being promoted into the core four-command Quickstart flow. The Annex section SHALL use the same major-section structure (section-head plate + h2 + lede, then a content block) as Plates 01 through 04 so it inherits the page's standard vertical rhythm rather than crowding any neighbouring section.
- `[x]` **MKT-SITE-051**: The Start page's Evaluating section SHALL include a one-sentence mention of the experimental plugin as an opt-in onboarding consideration, with a link to the experimental skill's source in the repository for evaluators who want to inspect what the experimental layer contains.

## Home: How It Works

- `[x]` **MKT-SITE-038**: When a user loads the home page, the site SHALL present a "How it works" section containing a primary diagram that depicts a directed acyclic graph from a single high-level design node, through multiple low-level design nodes, EARS-spec nodes, and failing-first test nodes, terminating at code nodes.
- `[ ]` **MKT-SITE-039**: The How it works section SHALL also present a compact five-node schematic (HLD → LLD → EARS → Tests → code) positioned as a legend paired with the five-panel trace (see MKT-SITE-047). The schematic SHALL serve as a key labeling the rungs that the trace's panels instantiate with concrete example content, rather than standing alone as a second diagram. The schematic SHALL remain horizontally oriented at all widths (native 540×140 aspect).
- `[x]` **MKT-SITE-042**: Every edge in the primary DAG diagram SHALL render with a directional arrowhead at its terminus so cascade directionality is unambiguous.
- `[x]` **MKT-SITE-043**: The primary DAG diagram SHALL include at least one edge rendered in the accent color whose endpoints demonstrate the DAG-not-tree property (one node with more than one outgoing edge to the tier below, or one node with more than one incoming edge from the tier above).
- `[ ]` **MKT-SITE-041**: The How it works section SHALL present its content in this narrative order: section header, lede, trace block (see MKT-SITE-047), bridge paragraph, full DAG diagram, outro paragraph. The trace's five panels SHALL stack vertically with downward connectors between them at all breakpoints. Below 960px the trace block SHALL render as a single column with legend, strip, and grep-addressability note in that reading order. At ≥960px the trace block SHALL render as a two-column pair: the legend schematic and the grep-note SHALL occupy the left column (stacked top-to-bottom); the vertical five-panel strip SHALL occupy the right column, spanning both rows of the left side. The DAG+outro block SHALL render as a single stacked column below 1100px and SHALL break into a two-column pair (DAG right, outro left) at ≥1100px. The header, the lede, and the bridge paragraph SHALL remain full-width at all breakpoints.
- `[x]` **MKT-SITE-044**: The site SHALL NOT name specific peer spec-driven-development systems anywhere in its content. LID's positioning is expressed through its own claim (a graph rooted in intent, traceable across the whole repository), not through comparison to named alternatives.
- `[ ]` **MKT-SITE-045**: The trace's Code panel (the last panel in the vertical stack) SHALL display a code snippet containing an `@spec` annotation comment that references at least one EARS spec ID, paired with a short note describing how spec IDs are grep-addressable. The note SHALL appear in the same visual block as the trace (below the strip at narrow widths; in the left column under the legend at ≥960px).
- `[x]` **MKT-SITE-046**: The How it works section SHALL explicitly state where users spend their time in LID (the HLD and the LLDs) and that downstream artifacts (EARS specs, failing-first tests, code) are primarily agent-generated and reviewed rather than hand-written. The section SHALL also state that application changes and bug fixes both route back to an LLD edit.
- `[ ]` **MKT-SITE-047**: The How it works section SHALL present a five-panel trace carrying one worked example from HLD through Code. The five panels SHALL, in order, depict: (1) an HLD-level sentence of intent; (2) an LLD-level paragraph of design; (3) an EARS-level atomic claim with its grep-addressable ID; (4) failing-first test names tagged with the EARS ID they assert; (5) an `@spec`-annotated code snippet carrying the same ID. The example content of all five panels SHALL describe the same subject (account-scoped authentication) so the trace reads as one thought threaded through five levels of resolution.
- `[ ]` **MKT-SITE-048**: The EARS spec ID that is born on the trace's EARS panel SHALL appear visibly on the Tests panel and on the Code panel, so the grep-addressable through-line from claim to code annotation is readable without inference. The ID SHALL NOT appear on the HLD or LLD panels, since IDs are not minted at those rungs.
- `[ ]` **MKT-SITE-049**: The through-line of shared EARS IDs on the trace (MKT-SITE-048) SHALL be rendered as a visible dimension rail — a thin accent-coloured vertical line connecting the three ID-carrying panels — with a short horizontal tick mark extending from each ID chip to meet the rail. HLD and LLD panels SHALL NOT be connected to the rail.

## Start Page

- `[x]` **MKT-SITE-010**: When a user loads the Start page, the site SHALL present four audience sections matching the home-page path links — evaluating, greenfield, brownfield, scoped.
- `[x]` **MKT-SITE-011**: Each Start-page section SHALL contain a short description, the relevant plugin command(s) a user would run, and a link to the README for depth.
- `[ ]` **MKT-SITE-012**: Start-page section descriptions SHALL be approximately 150 words each; depth beyond that SHALL link to the README rather than expand inline.

## Examples Page

- `[x]` **MKT-SITE-013**: When a user loads the Examples page, the site SHALL link to the `examples/urlshort/` intent-only example in the repository.
- `[x]` **MKT-SITE-014**: Where the threadkeeper project is publicly linkable with maintainer permission, the Examples page SHALL link to it as a long-running real-world case study.
- `[ ]` **MKT-SITE-015**: If threadkeeper is not publicly linkable, the Examples page SHALL describe its nature (long-running, striated, real) without linking, rather than omit the case-study signal entirely.
- `[x]` **MKT-SITE-016**: The Examples page SHALL frame the two examples as complementary — urlshort as "clean, minimal, 5-minute read"; threadkeeper as "messy, real, instructive."

## Anti-patterns Page

- `[x]` **MKT-SITE-017**: When a user loads the Anti-patterns page, the site SHALL present at least three scenarios in which LID is the wrong choice.
- `[x]` **MKT-SITE-018**: Anti-patterns page items SHALL be framed as fit problems ("LID is not for you when...") rather than product deficiencies.

## Structure and Navigation

- `[x]` **MKT-SITE-019**: The site SHALL contain exactly four top-level pages: Home, Start, Examples, Anti-patterns.
- `[x]` **MKT-SITE-020**: When a user visits any page, the site SHALL provide navigation to the other three pages and to the GitHub repository.
- `[x]` **MKT-SITE-021**: The site SHALL NOT contain community features — forums, comments, user-submitted content, newsletter signups.
- `[x]` **MKT-SITE-022**: The site SHALL NOT contain calls-to-action beyond "install and use."
- `[ ]` **MKT-SITE-023**: The site SHALL NOT duplicate content from the README beyond the orientation material needed for an evaluator to decide whether to click through to it.

## Theme

- `[x]` **MKT-SITE-024**: When the user's system exposes a color-scheme preference, the site SHALL render using that preference via the `prefers-color-scheme` media query.
- `[x]` **MKT-SITE-025**: If the user has no system color-scheme preference, the site SHALL default to the dark theme.
- `[ ]` **MKT-SITE-026**: Both the dark and light themes SHALL meet WCAG AA contrast ratios for body text and interactive elements.

## Build and Deploy

- `[ ]` **MKT-SITE-027**: The site build SHALL render all Mermaid code blocks to static SVG at build time rather than loading a Mermaid runtime in the browser.
- `[ ]` **MKT-SITE-028**: The site build SHALL fail if any internal link resolves to a missing page, asset, or anchor.
- `[ ]` **MKT-SITE-029**: If the site build detects a broken external link, the build SHALL emit a warning but SHALL NOT fail.
- `[x]` **MKT-SITE-030**: The site MAY load typefaces from a no-tracking font service (such as Bunny Fonts) or self-hosted font files. Typefaces from services that log user requests for tracking or analytics purposes SHALL NOT be used.
- `[x]` **MKT-SITE-031**: The site SHALL NOT include analytics, tracking scripts, or cookie-setting code beyond what GitHub Pages emits by default.
- `[x]` **MKT-SITE-032**: When a change to `site/` is merged to the main branch, a GitHub Actions workflow SHALL build the site and deploy it to GitHub Pages.

## Cascade and Coherence

- `[ ]` **MKT-SITE-033**: When the HLD is modified, the site owner SHALL review site content for claim drift before the HLD change is considered complete.
- `[ ]` **MKT-SITE-034**: When a plugin LLD describing user-facing behavior is modified, the site owner SHALL review the affected Start-page path descriptions and the Quickstart commands.
- `[ ]` **MKT-SITE-035**: When skill behavior changes materially, the site owner SHALL re-record the asciinema demo before the next deploy.
- `[ ]` **MKT-SITE-036**: Where the `docs/arrows/` overlay is present in this repository, the site SHALL appear as a named segment in `docs/arrows/index.yaml` with the same schema as plugin segments.
- `[x]` **MKT-SITE-037**: The site SHALL NOT claim capabilities or behaviors that are not present in the current plugin LLDs.
