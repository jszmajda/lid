---
parent: onboarding
prefix: ONB-RESEARCH
---

# LLD: Research

**Created**: 2026-11-24
**Status**: Design Phase

## Context and Design Philosophy

The research section is the part of the site that publishes studies of what LID costs, what it buys, and where it falls short. People deciding whether to try LID ask what it costs and whether it works, and people who already use it want to know when it's worth the reading. A report answers with measurements and states their limits plainly. That includes results that don't favour LID, because a reader who finds only good news has reason to doubt all of it.

The section is a child of the `onboarding` sub-HLD and inherits its reader, its voice, and its rule for content the site presents. It sits on the site that the `marketing-site` segment owns: that segment owns the navigation, the visual identity, the copy register, and the build; this one owns the research index, the report pages, and the entry format a report arrives in.

**Who owns a report's words.** A report belongs to the study that produced it. Under the parent's rule for content the site presents, the site never edits or paraphrases a report, and the site's copy register does not apply to it. The study's authors change a report by changing its entry. The site's own words in this section are the index's heading and lede, which follow the copy register.

**What a report claims.** A report makes empirical claims: what the study measured when LID was used. Those claims trace to the study's own records, which each report links to, not to an HLD section. Because a measurement only holds for what was tested, every report states the LID version, the coding agent, the model, and the date of its runs, and the page shows them beside the title.

**Terms.** A **report** is one published write-up of a study's results, described by one **entry**. A report's **records** are the study's notebook, data, and code, wherever they live.

## Pages

### The index (`/research/`)

- **Heading and lede.** The h1 says the section holds research on what LID costs and what it buys. Neither the h1 nor the lede states a finding, so the site never summarises a study in its own voice, and adding a report changes no copy.
- **The reports,** newest first, each as a card: the report's title, its date, its status label, what it tested, and its summary, linking to the report's page. The summary is the report's own words, from its entry. Superseded reports stay on the index, labelled, so a link to one still finds it.
- **No reports yet** is not a state the index needs: the section is published with its first report.

### A report's page (`/research/<slug>/`)

- **The header,** above the report: a path back to the index, the title as the h1, the date (followed by "revised" and the date it was last revised, when it has been), the status label, a "What was tested" line giving the LID version, coding agent, and model in that order, and a link to "The study's records". Dates use the site's date format ("24 Nov 2026").
- **The report,** rendered from Markdown in the site's reading style. Each table sits in its own frame, which scrolls sideways when the table is wider than the screen, so its columns never squeeze.

### Status labels

A report's status says how much weight its numbers can bear:

- **Pilot results**: from pilot runs, with analyses not fixed in advance.
- **Counted results**: from runs whose analysis was fixed in advance (pre-registered).
- **Superseded**: replaced by a later report. Directly below its h1, the page says so and links to the later report. The later report's page, in the same place, says which reports it replaces and links to each.

### Link previews

A link to the index previews with the site's default card image and the index's own title and description. A link to a report previews with the default card image, the report's title, and its summary.

## The Entry Format

An entry is one folder, `site/src/research/<slug>/`, whose name is the report's URL. It holds `index.md`, whose front matter describes the report and whose body is the report itself, in Markdown, and any images the report shows. `site/src/research/_template/index.md` is a filled-in sample whose fields are each explained by a YAML comment in its front matter (an HTML comment would break the no-HTML rule below); the build does not publish it.

| Front-matter field | Required | Meaning |
|---|---|---|
| `title` | yes | The report's title as shown. |
| `date` | yes | The date the report was first published; orders the index. A published report keeps its slug, because a static site can't redirect; renaming one means a new entry and the old one superseded. |
| `revised` | no | The date of its latest revision, when it has been revised. |
| `status` | yes | `pilot`, `counted`, or `superseded`. |
| `superseded_by` | with `superseded` | The slug of the report that replaces it. |
| `summary` | yes | One or two sentences in the study's words, as plain text of at most 300 characters, shown on the card and in link previews. |
| `tested` | yes | `{lid, agent, model}`: the LID version, the coding agent and its version, and the model and effort, as plain strings shown exactly as written. |
| `records` | yes | A public URL for the study's records. |

## Rules the Build Enforces

**Any rule below that an entry breaks fails the site's build,** with a message naming the entry and the rule.

**Entries**
- Each folder in `site/src/research/` is an entry, and its name is the slug: lowercase letters, digits, and hyphens. Folders whose names start with `_` or `.` are not entries. A file directly in `site/src/research/` is an error.
- Every required field is present, and unknown fields are an error. `title` and `summary` are strings with something other than whitespace in them.
- `date` and `revised` are real calendar dates written `YYYY-MM-DD`, quoted or not; neither is later than the day of the build, taken in UTC so the rule doesn't depend on where the site is built; `revised`, when present, is later than `date`.
- `status` is `pilot`, `counted`, or `superseded`.
- A `superseded` entry has `superseded_by`, naming an existing entry other than itself, which is not itself superseded, so a reader is never sent along a chain or round a loop. No other status carries `superseded_by`. Several entries may name the same replacement.
- `tested` is a mapping with exactly the keys `lid`, `agent`, and `model`, each a string with something other than whitespace in it.
- `summary` is plain text: Markdown would render it as nothing but the same text. It is at most 300 characters, counted as Unicode code points.
- `records` is a URL beginning `https://` and a host name.

**The report**
- The body has something other than whitespace in it, and no level-1 heading as Markdown parses it (`#` or underlined), because the page's header holds the title. Its headings start at h2.
- It contains no raw HTML as Markdown parses it: no HTML block, inline tag, or comment, so no script, style, or frame can enter a report. A URL in angle brackets is a link, and code blocks and code spans don't count.
- Every link and image reference is a URL beginning `https://` and a host name, an anchor within the page (`#…`), a `mailto:` address, or the bare file name of an image in the entry's own folder. `http://`, protocol-relative (`//…`), and paths with a slash fail.
- The entry's folder holds only `index.md` and the images the report references, by image or by link: files ending `.png`, `.jpg`, `.jpeg`, or `.svg`, in lowercase, of at most 2,000,000 bytes each. Any other file, or an image the report doesn't reference, fails the build.
- An SVG image contains no `script` or `foreignObject` element and no event-handler attribute (a name beginning `on`), and its `href`, `xlink:href`, `src`, and `url(…)` references are anchors or bare file names of other files in the folder, since an SVG file can carry code.

**Ordering.** The index orders entries by `date`, newest first, and breaks ties by slug in code-point order; `revised` doesn't move an entry.

## Verification

This segment is a content artifact, verified as the parent's other children are: by build-time checks and by review.

- **Build-time checks** in `site/tests/`: the index lists every entry once, newest first; each entry has its page; each page shows its title, dates, status label, what was tested, and its records link; a superseded report links to its replacement; and each rule above fails the build on a fixture entry that breaks it.
- **Review:** the maintainer reviews each report before it merges, for privacy (a report quotes no material its study keeps private) and for the claims rule (every number traces to the study's records).
- **By eye**, in both themes and at phone width: the index, a report's page, and a wide table.

## Cascade

- **The parent sub-HLD's reader, voice, claims rule, or presentation rule changes:** this segment's pages are reviewed.
- **`marketing-site` changes its navigation, visual identity, or copy register:** the research pages follow. Adding this section adds Research to the site's top-level navigation, which `marketing-site` owns.
- **A report is added, revised, or superseded:** no cascade; reports are content within this design. A revision updates `revised`.
- **A study's records move:** the report's `records` link is updated in the same change.

## Decisions & Alternatives

| Decision | Chosen | Alternatives Considered | Rationale |
|---|---|---|---|
| Where a report's text lives | In its entry folder on the site, as the one published copy | Read at build time from the study's notebook under `docs/research/` | A study's notebook may live on a branch until the study is done, and the site builds from `main`. One copy in the entry means the published report is always what the site serves; the notebook links to it. |
| What the index says about findings | Nothing; each card shows the report's own summary | A site-written headline per report | The site's voice is the maintainer's; a site-written summary of a study about LID is the place overselling would creep in. The study's own summary keeps its own caveats. |
| Stating what was tested | Required on every report and shown beside its title | Left to each report's text | A measurement holds only for the version, agent, and model that produced it, and readers skim. Requiring it makes every number scoped where it is read. |
| Status labels | Pilot, counted, superseded | No status; free text | A reader needs to know at a glance whether a result was fixed in advance, and whether a newer report replaces it. Free text would drift between reports. |
| Report format | Markdown only | Markdown or a self-contained HTML page, as stories allow | Reports are prose and tables. Charts can arrive as images in the entry folder. HTML would invite scripts and outside assets into a section whose job is to be checkable. |
| Links inside a report | Absolute, or to files in the entry folder | Relative paths into the repository | A path into the repository resolves only on GitHub, and a study's records may be on a branch. |

## Open Questions & Future Decisions

### Deferred

- Charts drawn by the build from a report's data, rather than as images.
- Grouping several reports from one study as a series.

## References

- `docs/intent/onboarding/onboarding-design.md`: the parent sub-HLD (the reader, the voice, the claims rule, content the site presents).
- `docs/intent/onboarding/marketing-site/marketing-site-design.md`: navigation, visual identity, copy register, the build.
- `docs/intent/onboarding/examples-showcase/examples-showcase-design.md`: the sibling whose entry format this one follows.
- `docs/high-level-design.md`: Goal 5.
