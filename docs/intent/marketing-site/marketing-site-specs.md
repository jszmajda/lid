# Marketing Site Specs

**LLD**: docs/intent/marketing-site/marketing-site-design.md
**Implementing artifacts**:
- site/src/**
- site/_site/** (build output)
- .github/workflows/site-build.yml
- README.md (the segment owns README content; see "Repository README")

Status markers: `[x]` implemented · `[ ]` active gap · `[D]` deferred

---

## Home: Pitch and Framing

- `[x]` **MKT-SITE-001**: When a user loads the home page, the site SHALL present as its h1 the intent-gap question addressed personally to the reader: "How do you know your agent built what you meant?" The site h1 and the repository README's opening pitch are independently owned surfaces; only the Quickstart commands are synchronized between them (MKT-SITE-008).
- `[x]` **MKT-SITE-002**: When a user loads the home page, the site SHALL present a four-line framing under the h1 that answers the h1's question at intent altitude, each line beginning "Because," with the arc intent → derivation → check → name: (1) because the user wrote it down — a design, in plain English; (2) because everything the agent builds comes from that design; (3) because the user can check — one ID grep returns the requirement, its tests, and its code; (4) because LID helped you get there. The artifact list (requirement, tests, code) SHALL appear exactly once in the hero, in the check line. The framing SHALL NOT open with requirement-level mechanics and SHALL NOT display a literal spec ID (real IDs first appear in How it works, where the trace explains them); the closing line SHALL name LID only after the mechanism has been shown; and the agent SHALL be named generically rather than as a specific tool.
- `[x]` **MKT-SITE-003**: When a user loads the home page, the site SHALL embed an asciinema recording whose scenario is a cascade demonstration — an HLD or LLD edit in a live LID project, propagating through specs, tests, and code.
- `[x]` **MKT-SITE-004**: When a user loads the home page, the hero SHALL present exactly two calls-to-action: a primary Install action that anchor-links to the Quickstart (MKT-SITE-040) and a secondary "Read the source" link to the GitHub repository. The page SHALL present no additional calls-to-action beyond install-and-use (MKT-SITE-022).
- `[x]` **MKT-SITE-005**: When a user loads the home page, the site SHALL present four audience-path links (evaluating, greenfield, brownfield, scoped), each linking to the corresponding section on the Start page.
- `[x]` **MKT-SITE-060**: The hero lede SHALL lead with the intent-gap problem (working code that misses what was meant — a judgment call the user never saw; the next session starts with no memory of why), SHALL expand the product name at its first mention — "LID (Linked-Intent Development)" — so the framing's closing name connects to its expansion, SHALL state the fix-once loop with the agent's cascade paired to the user's per-step review and SHALL NOT use hands-off verbs (closes, eliminates, rewrites itself) for agent work done under review, SHALL close with the ceremony-disarm line (the design sentences are what the user would type into the chat anyway; LID keeps them where the next session can find them), and SHALL NOT contain methodology acronyms (EARS, HLD, LLD, DAG) or the term "arrow." (The product name "LID" is not a methodology acronym for this purpose.)
- `[x]` **MKT-SITE-061**: On each site page, the first mention of a methodology term SHALL be plain English with the formal name or acronym introduced afterward (e.g., structured one-line requirements with greppable IDs, then EARS), and the term "arrow" SHALL be defined in one clause at its first use on the page. Internal workflow vocabulary (phase names, audit names) SHALL NOT appear on the site. A real spec ID MAY appear before EARS is named — showing the artifact is the show-then-name rule applied to identifiers; the format name still arrives with the trace. Diagram labels inside schematic figures MAY use methodology notation ahead of the prose definition; the one-clause prose definition still governs the term's first use in page prose.

## Home: Quickstart

- `[x]` **MKT-SITE-006**: When a user loads the home page, the site SHALL present a Quickstart section containing copy-pastable install commands with a one-line explanation per command.
- `[x]` **MKT-SITE-007**: The home page SHALL present its primary sections in this order: hero, How it works, cascade demo, Teams, Quickstart, audience-path links.
- `[x]` **MKT-SITE-008**: The Quickstart commands SHALL match the repository README's Quickstart section exactly.
- `[ ]` **MKT-SITE-009**: When the README's Quickstart changes, the site's Quickstart SHALL cascade to match before the next deploy.
- `[x]` **MKT-SITE-040**: The hero SHALL include a primary call-to-action that anchor-links to the Quickstart section on the same page, so an evaluator who has already decided can reach the install commands without scrolling past the structural orientation content.
- `[x]` **MKT-SITE-050**: The Home page SHALL include a peer "Annex" section (placed between the Quickstart and the audience-path links) that surfaces the existence of the `lid-experimental` plugin as an optional, opt-in install — naming the plugin, showing its install command, framing it as not part of the core install path, and linking to the plugin's user-facing README — so an evaluator learns the experimental capabilities exist without those capabilities being promoted into the core four-command Quickstart flow. The Annex section SHALL use the same major-section structure (section-head plate + h2 + lede, then a content block) as the page's numbered plate sections so it inherits the page's standard vertical rhythm rather than crowding any neighbouring section.
- `[x]` **MKT-SITE-051**: The Start page's Evaluating section SHALL include a one-sentence mention of the experimental plugin as an opt-in onboarding consideration, with a link to the experimental skill's source in the repository for evaluators who want to inspect what the experimental layer contains.

## Home: How It Works

- `[x]` **MKT-SITE-038**: When a user loads the home page, the site SHALL present a "How it works" section containing a primary diagram that depicts a directed acyclic graph from a single high-level design node, through multiple low-level design nodes, EARS-spec nodes, and failing-first test nodes, terminating at code nodes.
- `[x]` **MKT-SITE-039**: The How it works section SHALL also present a compact five-node schematic (HLD → LLD → EARS → Tests → code) positioned as a legend paired with the five-panel trace (see MKT-SITE-047). The schematic SHALL serve as a key labeling the rungs that the trace's panels instantiate with concrete example content, rather than standing alone as a second diagram. The schematic SHALL remain horizontally oriented at all widths (native 540×140 aspect).
- `[x]` **MKT-SITE-042**: Every edge in the primary DAG diagram SHALL render with a directional arrowhead at its terminus so cascade directionality is unambiguous.
- `[x]` **MKT-SITE-043**: The primary DAG diagram SHALL include at least one edge rendered in the accent color whose endpoints demonstrate the DAG-not-tree property (one node with more than one outgoing edge to the tier below, or one node with more than one incoming edge from the tier above).
- `[x]` **MKT-SITE-041**: The How it works section SHALL present its content in this narrative order: section header, lede, trace block (see MKT-SITE-047), bridge paragraph, full DAG diagram, outro paragraph. The trace's five panels SHALL stack vertically with downward connectors between them at all breakpoints. Below 960px the trace block SHALL render as a single column with legend, strip, and grep-addressability note in that reading order. At ≥960px the trace block SHALL render as a two-column pair: the legend schematic and the grep-note SHALL occupy the left column (stacked top-to-bottom); the vertical five-panel strip SHALL occupy the right column, spanning both rows of the left side. The DAG+outro block SHALL render as a single stacked column below 1100px and SHALL break into a two-column pair (DAG right, outro left) at ≥1100px. The header, the lede, and the bridge paragraph SHALL remain full-width at all breakpoints.
- `[x]` **MKT-SITE-044**: The site SHALL NOT name specific peer spec-driven-development systems anywhere in its content. LID's positioning is expressed through its own claim (a graph rooted in intent, traceable across the whole repository), not through comparison to named alternatives.
- `[x]` **MKT-SITE-045**: The trace's Code panel (the last panel in the vertical stack) SHALL display a code snippet containing an `@spec` annotation comment that references at least one EARS spec ID, paired with a short note describing how spec IDs are grep-addressable. The note SHALL appear in the same visual block as the trace (below the strip at narrow widths; in the left column under the legend at ≥960px).
- `[x]` **MKT-SITE-046**: The How it works section SHALL explicitly state where users spend their time in LID (the HLD and the LLDs) and that downstream artifacts (EARS specs, failing-first tests, code) are primarily agent-generated and reviewed rather than hand-written. The section SHALL also state that application changes and bug fixes both route back to an LLD edit.
- `[x]` **MKT-SITE-047**: The How it works section SHALL present a five-panel trace carrying one worked example from HLD through Code. The five panels SHALL, in order, depict: (1) an HLD-level sentence of intent; (2) an LLD-level paragraph of design; (3) an EARS-level atomic claim with its grep-addressable ID; (4) failing-first test names tagged with the EARS ID they assert; (5) an `@spec`-annotated code snippet carrying the same ID. The example content of all five panels SHALL describe the same subject (account-scoped authentication) so the trace reads as one thought threaded through five levels of resolution.
- `[x]` **MKT-SITE-048**: The EARS spec ID that is born on the trace's EARS panel SHALL appear visibly on the Tests panel and on the Code panel, so the grep-addressable through-line from claim to code annotation is readable without inference. The ID SHALL NOT appear on the HLD or LLD panels, since IDs are not minted at those rungs.
- `[x]` **MKT-SITE-049**: The through-line of shared EARS IDs on the trace (MKT-SITE-048) SHALL be rendered as a visible dimension rail — a thin accent-coloured vertical line connecting the three ID-carrying panels — with a short horizontal tick mark extending from each ID chip to meet the rail. HLD and LLD panels SHALL NOT be connected to the rail.
- `[x]` **MKT-SITE-055**: The How it works lede SHALL present coherence-checking as a bounded verification claim: it SHALL lead with the concrete cite-chain (code cites spec, test cites spec, spec traces to design) before naming the graph; it SHALL state that checking that the code still traces to the design is mechanical (a walk through the graph, suitable for CI) while whether the design says what the user means remains a human judgment; and it SHALL NOT hedge the mechanical claim with minimizers ("just a walk") that imply the walk certifies semantic correctness.
- `[x]` **MKT-SITE-056**: The grep-addressability note (MKT-SITE-045) SHALL state the attestation claim: one search on a spec ID returns everything that cites it — the spec line, the tests asserting it, and the code implementing it — framed as how a reviewer verifies coherence, not only as how an agent navigates.
- `[x]` **MKT-SITE-057**: The How it works outro SHALL state the review posture that follows from locus-of-work: the user reviews intent and agent-proposed deltas, and the downstream linkage is what lets the user, an audit pass, or a fresh agent with no project context verify mechanically that what landed traces to what was written down.
- `[x]` **MKT-SITE-062**: The How it works section SHALL state explicitly that the five-rung shape is not a one-way phase sequence: every level remains editable for the life of the project, and an edit at any level recompiles the levels below it.
- `[x]` **MKT-SITE-063**: The How it works section SHALL name the discipline's costs concretely — per-change review of design, specs, and tests before code; reading that shifts toward design diffs; additional agent tokens spent maintaining linkage — framed as a trade the reader can evaluate, and SHALL NOT present LID as cost-free.
- `[x]` **MKT-SITE-067**: The How it works lede SHALL state why the reader's existing checks miss intent drift: green tests cannot catch a misreading on their own, because the tests may come from the same misreading as the code.
- `[x]` **MKT-SITE-068**: Persuasive headings — the h2s of How it works, the cascade demo, and Teams, plus the Examples and Anti-patterns page h1s — SHALL each state a claim that traces to a mechanism or artifact shown on the page; the Home h1 is the sanctioned exception, an interrogative naming the intent-gap doubt (MKT-SITE-001). Navigational headings (Quickstart, entry paths, ecosystem, the Start page) MAY merely orient. Metaphor SHALL NOT lead a persuasive heading.
- `[x]` **MKT-SITE-069**: Site copy SHALL contain exactly one authorial first-person sentence, placed with the price passage in How it works, carrying verifiable receipts — a link to the portfolio-tracker exemplar (~63k lines of Rust, ~350 specs, a CI gate that fails the build on uncited specs) and the breadth clause that LID runs on projects beyond the author's own — and the author's name SHALL appear in the site footer. First-person authorial voice SHALL NOT appear anywhere else on the site.
- `[x]` **MKT-SITE-070**: Site copy SHALL name the discipline's cost "the price" wherever the cost is referenced, on every page.
- `[x]` **MKT-SITE-071**: Site copy SHALL contain at most two "X, not Y" antithesis constructions across all pages.

## Home: Teams

- `[x]` **MKT-SITE-064**: The home page SHALL present a Teams section, placed between the cascade demo and the Quickstart, carrying these beats: (1) intent review runs through pull requests — design conversations happen on HLD/LLD diffs before implementation, and once aligned intent lands, any team member cascades it; (2) the intent tree doubles as the onboarding surface because its docs are written to be read cold; (3) teammates on different coding agents share the same plain-markdown source of truth; (4) a sub-team adopts inside a larger organization via Scoped mode with an explicit declared boundary; (5) urgent hotfixes ship outside the workflow and are walked back through the design afterward so intent catches up. Each beat SHALL describe properties of the artifacts (files, git, markdown), not governance or tooling capabilities LID does not have.

## Start Page

- `[x]` **MKT-SITE-010**: When a user loads the Start page, the site SHALL present four audience sections matching the home-page path links — evaluating, greenfield, brownfield, scoped.
- `[x]` **MKT-SITE-011**: Each Start-page section SHALL contain a short description, the relevant plugin command(s) a user would run, and a link to the README for depth.
- `[ ]` **MKT-SITE-012**: Start-page section descriptions SHALL be approximately 150 words each; depth beyond that SHALL link to the README rather than expand inline.
- `[x]` **MKT-SITE-066**: The Start page's Evaluating section SHALL mention portfolio-tracker as a clonable example of the full arrow (design through `@spec`-cited tests and the CI coverage gate), with a link to the repository.
- `[x]` **MKT-SITE-052**: The Start page SHALL surface `/lid-coach` — the core `linked-intent-dev` plugin's principle-review skill — within the audience-path narratives (at minimum the Evaluating path), framed as a tool for reviewing an already-running LID project against the methodology's principles, with a link to the skill's source in the repository. The site SHALL NOT add `/lid-coach` to the Home Quickstart command list or give it its own audience-path section, since it is neither an install step nor an audience path.

## Examples Page

- `[x]` **MKT-SITE-013**: When a user loads the Examples page, the site SHALL link to the `examples/urlshort/` intent-only example in the repository.
- `[x]` **MKT-SITE-014**: Where the threadkeeper project is publicly linkable with maintainer permission, the Examples page SHALL link to it as a long-running real-world case study.
- `[ ]` **MKT-SITE-015**: If threadkeeper is not publicly linkable, the Examples page SHALL describe its nature (long-running, striated, real) without linking, rather than omit the case-study signal entirely.
- `[x]` **MKT-SITE-016**: The Examples page SHALL frame the three examples as complementary lenses — urlshort as "clean, minimal, 5-minute read"; portfolio-tracker as "complete, real, end-to-end"; threadkeeper as "messy, real, instructive."
- `[x]` **MKT-SITE-065**: When a user loads the Examples page, the site SHALL link to the portfolio-tracker repository (`github.com/jszmajda/portfolio-tracker`) as a complete public project built with LID end-to-end — design tree, EARS specs, `@spec`-cited tests, and code — naming its CI coverage gate (the build fails unless every spec is cited by at least one test and every citation resolves to a defined spec) as the public enforcement of the linkage the site describes.

## Anti-patterns Page

- `[x]` **MKT-SITE-017**: When a user loads the Anti-patterns page, the site SHALL present at least three scenarios in which LID is the wrong choice.
- `[x]` **MKT-SITE-018**: Anti-patterns page items SHALL be framed as fit problems ("LID is not for you when...") rather than product deficiencies.

## Structure and Navigation

- `[x]` **MKT-SITE-019**: The site SHALL contain exactly four top-level pages: Home, Start, Examples, Anti-patterns.
- `[x]` **MKT-SITE-020**: When a user visits any page, the site SHALL provide navigation to the other three pages and to the GitHub repository.
- `[x]` **MKT-SITE-021**: The site SHALL NOT contain community features — forums, comments, user-submitted content, newsletter signups.
- `[x]` **MKT-SITE-022**: The site SHALL NOT contain calls-to-action beyond "install and use."
- `[ ]` **MKT-SITE-023**: The site SHALL NOT duplicate content from the README beyond the orientation material needed for an evaluator to decide whether to click through to it.
- `[x]` **MKT-SITE-058**: Anywhere on the onboarding surface (site pages and the repository README), attestation copy SHALL present linkage as the mechanism that makes verification cheap; it SHALL NOT claim that agent-written code is trustworthy by virtue of LID, and SHALL NOT present traceability as a compliance guarantee.

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

## Repository README

- `[x]` **MKT-SITE-059**: The repository README body SHALL state both linkage payoffs — navigation (the arrow walkable in tokens) and attestation (coherence checkable by search) — consistent with HLD § Approach: Linkage-based Intent Tracking, without modifying the README's opening pitch (independently owned; see `MKT-SITE-001`).
- `[x]` **MKT-SITE-053**: The repository `README.md` SHALL open with a badge row that includes, at minimum, badges for the license, the GitHub star count, Claude Code compatibility, the project website, an open-contributions signal, and a built-with-LID signal; each badge SHALL link to the resource it represents and SHALL trace to a fact already owned in the arrow. The README SHALL NOT carry build-status, test-coverage, package-download, or hand-maintained version badges, since the project has no such surface to report on. Badges SHALL be served as proxied static images so that no third-party tracking request is made on the reader's behalf, consistent with `MKT-SITE-031`.

## Ecosystem (social proof)

- `[x]` **MKT-SITE-054**: The onboarding surface SHALL surface the third-party extension ecosystem as a trust signal — at minimum a curated link from the repository `README.md` to `EXTENSIONS.md` and/or the canonical `linked-intent-development` topic, framed as projects building on LID, optionally enriched with a site element. It SHALL be a single curated maintainer link-out, not user-submitted content or an embedded feed, consistent with `MKT-SITE-021` (not a community hub). The ecosystem's substance is owned by the `extensions` segment; this segment owns only the trust-signal framing.
