# Research Specs

**LLD**: docs/intent/onboarding/research/research-design.md
**Implementing artifacts**:
- site/src/research/** (the entries, and `_template/`)
- site/scripts/research-entries.js (reads and checks the entries)
- site/src/_data/research.js (the section's data)
- site/src/research.njk, site/src/research-page.njk
- site/.eleventy.js (the entries are data; their images are copied beside their pages)
- site/src/assets/css/main.css (the research section)
- site/tests/research.test.js

Status markers: `[x]` implemented · `[ ]` active gap · `[D]` deferred

## The Index

- `[x]` **ONB-RESEARCH-001**: The site SHALL serve the research section's index at `/research/`.
- `[x]` **ONB-RESEARCH-002**: The index's h1 SHALL say that the section holds research on what LID costs and what it buys.
- `[x]` **ONB-RESEARCH-003**: The index's h1 and lede SHALL state no finding of any study.
- `[x]` **ONB-RESEARCH-004**: The index SHALL list every research entry exactly once, superseded entries included, ordered by `date` with the newest first and with ties broken by slug in code-point order; `revised` SHALL NOT affect the order.
- `[x]` **ONB-RESEARCH-005**: Each index card SHALL show the entry's title, its `date`, its status label, its `tested` values, and its `summary`.
- `[x]` **ONB-RESEARCH-006**: Each index card SHALL link to its report's page.

## A Report's Page

- `[x]` **ONB-RESEARCH-010**: The site SHALL serve each research entry's report at `/research/<slug>/`, where `<slug>` is the entry's folder name.
- `[x]` **ONB-RESEARCH-011**: A report's page SHALL show, above the report, a link back to the index, the entry's title as the page's only h1, its `date`, its status label, a line labelled "What was tested" giving its `tested` values in the order LID, coding agent, model, and a link labelled "The study's records" to its `records`.
- `[x]` **ONB-RESEARCH-012**: When an entry has `revised`, its report's page SHALL show "revised" and the revision date immediately after `date`.
- `[x]` **ONB-RESEARCH-013**: An entry's index card SHALL show its `date` and SHALL NOT show its `revised`.
- `[x]` **ONB-RESEARCH-014**: A report's page SHALL render the entry's body as the report, in the site's reading style.
- `[x]` **ONB-RESEARCH-015**: Each table in a report SHALL sit inside its own frame that scrolls sideways when the table is wider than the frame, so the table keeps its columns.
- `[x]` **ONB-RESEARCH-017**: On both the index card and the report's page, the site SHALL show an entry's `tested` values and `summary` as written, escaped as plain text and not rendered as Markdown.
- `[x]` **ONB-RESEARCH-018**: The index and each report's page SHALL show dates in the site's date format (for example, "24 Nov 2026").

## Status Labels

- `[x]` **ONB-RESEARCH-020**: The site SHALL show the status label "Pilot results" for an entry whose `status` is `pilot`, "Counted results" for `counted`, and "Superseded" for `superseded`.
- `[x]` **ONB-RESEARCH-021**: A superseded report's page SHALL say, directly below its h1, that a later report replaces it, and SHALL link to the entry its `superseded_by` gives.
- `[x]` **ONB-RESEARCH-022**: When one or more entries name an entry in their `superseded_by`, the named entry's page SHALL say, directly below its h1, which reports it replaces, and SHALL link to each of them.

## Link Previews

- `[x]` **ONB-RESEARCH-030**: A link to the research index SHALL preview with the site's default card image, the index's title, and the index's description.
- `[x]` **ONB-RESEARCH-031**: A link to a report's page SHALL preview with the site's default card image, the entry's title as the preview title, and its `summary` as the preview description.

## The Entry Format

- `[x]` **ONB-RESEARCH-040**: The build SHALL read each folder in `site/src/research/` as one research entry, whose folder name is its slug, and SHALL skip folders whose names start with `_` or `.`.
- `[x]` **ONB-RESEARCH-041**: An entry SHALL hold an `index.md` whose front matter describes the report and whose body is the report in Markdown.
- `[x]` **ONB-RESEARCH-042**: The repository SHALL carry `site/src/research/_template/index.md`, a filled-in sample entry whose front-matter fields are each explained by a YAML comment, and the site SHALL NOT publish a page for it.

## Rules the Build Enforces

- `[x]` **ONB-RESEARCH-050**: When any research entry breaks a rule in this section, the build SHALL fail with a message giving the entry's slug and the rule it breaks.
- `[x]` **ONB-RESEARCH-051**: An entry's slug SHALL consist only of lowercase letters, digits, and hyphens.
- `[x]` **ONB-RESEARCH-052**: An entry's front matter SHALL have `title`, `date`, `status`, `summary`, `tested`, and `records`, and SHALL have no field other than those and `revised` and `superseded_by`.
- `[x]` **ONB-RESEARCH-053**: An entry's `title` and `summary` SHALL each be a string that is not empty or only whitespace.
- `[x]` **ONB-RESEARCH-054**: An entry's `date`, and its `revised` when present, SHALL each be a real calendar date written as `YYYY-MM-DD`, quoted or not, and no later than the day of the build in UTC.
- `[x]` **ONB-RESEARCH-055**: When an entry has `revised`, its `revised` SHALL be later than its `date`.
- `[x]` **ONB-RESEARCH-056**: An entry's `status` SHALL be `pilot`, `counted`, or `superseded`.
- `[x]` **ONB-RESEARCH-057**: An entry whose `status` is `superseded` SHALL have `superseded_by`, giving the slug of an existing entry other than itself whose `status` is not `superseded`.
- `[x]` **ONB-RESEARCH-058**: An entry whose `status` is not `superseded` SHALL NOT have `superseded_by`.
- `[x]` **ONB-RESEARCH-059**: An entry's `tested` SHALL be a mapping with exactly the keys `lid`, `agent`, and `model`, each a string that is not empty or only whitespace.
- `[x]` **ONB-RESEARCH-060**: An entry's `summary` SHALL be plain text that Markdown would render as nothing but that same text, of at most 300 characters counted as Unicode code points.
- `[x]` **ONB-RESEARCH-061**: An entry's `records` SHALL be a URL beginning `https://` followed by a host name.
- `[x]` **ONB-RESEARCH-062**: An entry's report body SHALL contain something other than whitespace.
- `[x]` **ONB-RESEARCH-063**: An entry's report body SHALL contain no level-1 heading as Markdown parses it, in either the `#` or the underlined form; headings inside code blocks do not count.
- `[x]` **ONB-RESEARCH-064**: An entry's report body SHALL contain no raw HTML as Markdown parses it: no HTML block, inline tag, or HTML comment. A URL in angle brackets is a link, and text inside code blocks and code spans does not count.
- `[x]` **ONB-RESEARCH-065**: Every link and every image reference in an entry's report body SHALL be a URL beginning `https://` followed by a host name, an anchor within the page beginning `#`, a `mailto:` address, or the bare file name, with no path, of an image file in the entry's own folder.
- `[x]` **ONB-RESEARCH-066**: An entry's folder SHALL hold only `index.md` and image files that the report body references, by image or by link.
- `[x]` **ONB-RESEARCH-067**: Each image file in an entry's folder SHALL have the extension `.png`, `.jpg`, `.jpeg`, or `.svg`, in lowercase, and SHALL be no larger than 2,000,000 bytes.
- `[x]` **ONB-RESEARCH-068**: An SVG image in an entry's folder SHALL contain no `script` or `foreignObject` element and no attribute whose name begins `on`, and every `href`, `xlink:href`, or `src` value and every `url(…)` reference in it SHALL be an anchor beginning `#` or the bare file name of another file in the entry's folder.
- `[x]` **ONB-RESEARCH-069**: A file directly in `site/src/research/`, outside any entry folder, SHALL fail the build.

## Review

- `[ ]` **ONB-RESEARCH-080**: Before a research entry merges, the maintainer SHALL review that the report quotes no material its study keeps private, and that each number in it traces to the study's records.
