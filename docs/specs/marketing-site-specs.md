# Marketing Site Specs

**LLD**: docs/llds/marketing-site.md
**Implementing artifacts**:
- site/src/**
- site/_site/** (build output)
- .github/workflows/site-build.yml

Status markers: `[x]` implemented · `[ ]` active gap · `[D]` deferred

---

## Home: Pitch and Framing

- `[ ]` **MKT-SITE-001**: When a user loads the home page, the site SHALL present a single-sentence pitch synchronized with the opening of the repository README.
- `[ ]` **MKT-SITE-002**: When a user loads the home page, the site SHALL present the three-line framing: "LID is the blueprint. Claude is the compiler. Code is the output."
- `[x]` **MKT-SITE-003**: When a user loads the home page, the site SHALL embed an asciinema recording whose scenario is a cascade demonstration — an HLD or LLD edit in a live LID project, propagating through specs, tests, and code.
- `[ ]` **MKT-SITE-004**: When a user loads the home page, the site SHALL link to the GitHub repository as its single primary call-to-action.
- `[ ]` **MKT-SITE-005**: When a user loads the home page, the site SHALL present four audience-path links (evaluating, greenfield, brownfield, scoped), each linking to the corresponding section on the Start page.

## Home: Quickstart

- `[ ]` **MKT-SITE-006**: When a user loads the home page, the site SHALL present a Quickstart section containing copy-pastable install commands with a one-line explanation per command.
- `[ ]` **MKT-SITE-007**: The Quickstart section SHALL be placed sufficiently high on the home page that an evaluator scrolling for "what do I run" finds it without navigating away.
- `[ ]` **MKT-SITE-008**: The Quickstart commands SHALL match the repository README's Quickstart section exactly.
- `[ ]` **MKT-SITE-009**: When the README's Quickstart changes, the site's Quickstart SHALL cascade to match before the next deploy.

## Start Page

- `[ ]` **MKT-SITE-010**: When a user loads the Start page, the site SHALL present four audience sections matching the home-page path links — evaluating, greenfield, brownfield, scoped.
- `[ ]` **MKT-SITE-011**: Each Start-page section SHALL contain a short description, the relevant plugin command(s) a user would run, and a link to the README for depth.
- `[ ]` **MKT-SITE-012**: Start-page section descriptions SHALL be approximately 150 words each; depth beyond that SHALL link to the README rather than expand inline.

## Examples Page

- `[ ]` **MKT-SITE-013**: When a user loads the Examples page, the site SHALL link to the `examples/urlshort/` intent-only example in the repository.
- `[ ]` **MKT-SITE-014**: Where the threadkeeper project is publicly linkable with maintainer permission, the Examples page SHALL link to it as a long-running real-world case study.
- `[ ]` **MKT-SITE-015**: If threadkeeper is not publicly linkable, the Examples page SHALL describe its nature (long-running, striated, real) without linking, rather than omit the case-study signal entirely.
- `[ ]` **MKT-SITE-016**: The Examples page SHALL frame the two examples as complementary — urlshort as "clean, minimal, 5-minute read"; threadkeeper as "messy, real, instructive."

## Anti-patterns Page

- `[ ]` **MKT-SITE-017**: When a user loads the Anti-patterns page, the site SHALL present at least three scenarios in which LID is the wrong choice.
- `[ ]` **MKT-SITE-018**: Anti-patterns page items SHALL be framed as fit problems ("LID is not for you when...") rather than product deficiencies.

## Structure and Navigation

- `[ ]` **MKT-SITE-019**: The site SHALL contain exactly four top-level pages: Home, Start, Examples, Anti-patterns.
- `[ ]` **MKT-SITE-020**: When a user visits any page, the site SHALL provide navigation to the other three pages and to the GitHub repository.
- `[ ]` **MKT-SITE-021**: The site SHALL NOT contain community features — forums, comments, user-submitted content, newsletter signups.
- `[ ]` **MKT-SITE-022**: The site SHALL NOT contain calls-to-action beyond "install and use."
- `[ ]` **MKT-SITE-023**: The site SHALL NOT duplicate content from the README beyond the orientation material needed for an evaluator to decide whether to click through to it.

## Theme

- `[ ]` **MKT-SITE-024**: When the user's system exposes a color-scheme preference, the site SHALL render using that preference via the `prefers-color-scheme` media query.
- `[ ]` **MKT-SITE-025**: If the user has no system color-scheme preference, the site SHALL default to the dark theme.
- `[ ]` **MKT-SITE-026**: Both the dark and light themes SHALL meet WCAG AA contrast ratios for body text and interactive elements.

## Build and Deploy

- `[ ]` **MKT-SITE-027**: The site build SHALL render all Mermaid code blocks to static SVG at build time rather than loading a Mermaid runtime in the browser.
- `[ ]` **MKT-SITE-028**: The site build SHALL fail if any internal link resolves to a missing page, asset, or anchor.
- `[ ]` **MKT-SITE-029**: If the site build detects a broken external link, the build SHALL emit a warning but SHALL NOT fail.
- `[ ]` **MKT-SITE-030**: The site MAY load typefaces from a no-tracking font service (such as Bunny Fonts) or self-hosted font files. Typefaces from services that log user requests for tracking or analytics purposes SHALL NOT be used.
- `[ ]` **MKT-SITE-031**: The site SHALL NOT include analytics, tracking scripts, or cookie-setting code beyond what GitHub Pages emits by default.
- `[ ]` **MKT-SITE-032**: When a change to `site/` is merged to the main branch, a GitHub Actions workflow SHALL build the site and deploy it to GitHub Pages.

## Cascade and Coherence

- `[ ]` **MKT-SITE-033**: When the HLD is modified, the site owner SHALL review site content for claim drift before the HLD change is considered complete.
- `[ ]` **MKT-SITE-034**: When a plugin LLD describing user-facing behavior is modified, the site owner SHALL review the affected Start-page path descriptions and the Quickstart commands.
- `[ ]` **MKT-SITE-035**: When skill behavior changes materially, the site owner SHALL re-record the asciinema demo before the next deploy.
- `[ ]` **MKT-SITE-036**: Where the `docs/arrows/` overlay is present in this repository, the site SHALL appear as a named segment in `docs/arrows/index.yaml` with the same schema as plugin segments.
- `[ ]` **MKT-SITE-037**: The site SHALL NOT claim capabilities or behaviors that are not present in the current plugin LLDs.
