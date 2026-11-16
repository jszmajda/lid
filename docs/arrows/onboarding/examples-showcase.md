# Arrow: examples-showcase

The site's showcase of projects built with LID: the index at `/examples/`, a page for each project with its picture, brief, numbers, and drawn intent tree, hosted stories, the entry format projects arrive in by pull request, and the counter that measures a design tree.

## Status

**MAPPED**, a new leaf segment sampled 2026-11-16 and not yet audited. All 93 `ONB-SHOWCASE` specs are implemented and covered by `site/tests/showcase.test.js` and `site/tests/intent-tree.test.js`; the index, a project's page, the zoom dialog, and the tree labels were checked by eye in both themes and at phone width. First entries: compost (Friday's; its story written by Claude), Clowder (spoiler-safe names only), portfolio-tracker, and Threadkeeper (private, drawn without names).

## References

### Parent
- `docs/intent/onboarding/onboarding-design.md` (sub-HLD `onboarding`: shared reader, voice, claims rule, and content the site presents)

### HLD
- `docs/high-level-design.md` § Goal 5

### LLD
- `docs/intent/onboarding/examples-showcase/examples-showcase-design.md`

### EARS
- `docs/intent/onboarding/examples-showcase/examples-showcase-specs.md` (93 specs, prefix `ONB-SHOWCASE-*`)

### Tests
- `site/tests/showcase.test.js`: entry validation (every build-failing rule), size names, the tree drawing, the built index, project pages, hosted stories, and the example pull-request template.
- `site/tests/intent-tree.test.js`: the counter on fixture trees (node-as-folder, flat, nested, skipped directories, marker and fence rules, `--no-names`, errors).

### Code
- `site/scripts/intent-tree.js`: the counter (Node, no dependencies; also imported by the build)
- `site/scripts/tree-svg.js`: the tree drawing and size names
- `site/scripts/entries.js`: reads and checks entries; any broken rule fails the build
- `site/src/_data/examples.js`: the showcase's data, the reference trees, and the hosted story's bar
- `site/src/examples.njk`, `site/src/example-page.njk`, `site/src/example-story.njk`, `site/src/example-story-html.njk`
- `site/src/assets/js/showcase.js`, `site/src/assets/css/main.css` § 17b
- `site/src/examples/`: the entries and `_template/`
- `.github/PULL_REQUEST_TEMPLATE/example.md`

## Architecture

**Purpose:** Get readers excited about working with LID by showing the range of what people build with it, each project on a page of its own that links deeper.

**Key Components:**
1. **Entries**: one folder per project (`index.md`, pictures, `tree.yaml`, an optional hosted story), checked at build time.
2. **Pages**: the index (featured newest project, the grid, "Read a whole tree", the invitation), a page per project, and hosted stories.
3. **The tree drawing**: an inline SVG built from a tree file; dots for built and open specs; names on hover, focus, or tap.
4. **The counter**: measures a design tree into a tree file, for contributors and for the build's reference trees.

## Spec Coverage

| Category | Implemented | Active gap | Deferred |
|---|---|---|---|
| Index and credit lines (`001`–`015`) | 15 `[x]` | 0 | 0 |
| Project pages, stories, pictures (`016`–`033`) | 18 `[x]` | 0 | 0 |
| Tree drawing and size names (`034`–`051`, `091`, `092`) | 20 `[x]` | 0 | 0 |
| Entries, the build, the tree file (`052`–`069`, `090`) | 19 `[x]` | 0 | 0 |
| The counter (`070`–`085`, `093`) | 17 `[x]` | 0 | 0 |
| Contributing (`086`–`089`) | 4 `[x]` | 0 | 0 |
| **Total** | **93** | **0** | **0** |

## Key Findings

1. **The build is the gate.** Any broken entry rule fails the site's build with the entry's name, so a malformed pull request cannot merge.
2. **Hosted HTML stories carry no tracking.** `story.html` may hold no script and load nothing from outside its folder, which keeps `marketing-site`'s no-tracking rule (`ONB-SITE-031`).
3. **The reference trees redraw at build time.** The site's deploy workflow runs on changes under `site/`, so LID's own tree drawing refreshes with the next site deploy, not on every design change.

## Work Required

### Nice to Have
1. Redeploy the site when `docs/intent/` changes, so LID's reference tree is never behind.
2. Filtering or grouping the index once it holds many projects (deferred in the LLD).
