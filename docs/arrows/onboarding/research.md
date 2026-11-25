# Arrow: research

The site's research section: the index at `/research/`, a page for each published report with what it tested and a link to its study's records, and the entry format a report arrives in.

## Status

**MAPPED**, a new leaf segment sampled 2026-11-25 and not yet audited. 42 of the 43 `ONB-RESEARCH` specs are implemented and covered by `site/tests/research.test.js`; ONB-RESEARCH-080, the maintainer's review before an entry merges, is a process step. The index and a report's page were checked by eye in both themes and at phone width. First report: `first-results`, the cost study's pilot results for LID 1.4.6.

## References

### Parent
- `docs/intent/onboarding/onboarding-design.md` (sub-HLD `onboarding`: shared reader, voice, claims rule, and content the site presents)

### HLD
- `docs/high-level-design.md` § Goal 5

### LLD
- `docs/intent/onboarding/research/research-design.md`

### EARS
- `docs/intent/onboarding/research/research-specs.md` (43 specs, prefix `ONB-RESEARCH-*`)

### Tests
- `site/tests/research.test.js`: entry validation (every build-failing rule, on fixture entries), the built index and report pages from a fixture set (ordering, cards, header, supersession both ways, table frames, link previews), and the real section (the template unpublished, every entry published).

### Code
- `site/scripts/research-entries.js`: reads and checks entries; any broken rule fails the build
- `site/src/_data/research.js`: the section's data
- `site/src/research.njk`, `site/src/research-page.njk`
- `site/.eleventy.js`: entries are data; images are copied beside their pages; reports render with table frames
- `site/src/assets/css/main.css` § 17c
- `site/src/research/`: the entries and `_template/`

## Architecture

**Purpose:** Publish studies of what LID costs and what it buys, with their limits stated, so a reader can weigh LID on evidence and check every number against its study's records.

**Ownership:** a report is its study's words; the site presents it and never edits it. The index's heading and lede are the site's words, under the copy register, and state no finding.

## Spec Coverage

| Category | Specs | Built | Notes |
|---|---|---|---|
| Index | 001–006 | 6 | |
| A report's page | 010–018 | 8 | 016 was folded into 011 |
| Status labels | 020–022 | 3 | |
| Link previews | 030–031 | 2 | |
| Entry format | 040–042 | 3 | |
| Rules the build enforces | 050–069 | 20 | |
| Review | 080 | 0 | a process step at merge |
