# Examples Showcase Specs

**LLD**: docs/intent/onboarding/examples-showcase/examples-showcase-design.md
**Implementing artifacts**:
- site/src/examples/** (the entries, and `_template/`)
- site/src/_data/examples.js (reads the entries and measures the trees)
- site/src/examples.njk, site/src/example-page.njk, site/src/example-story.njk, site/src/example-story-html.njk
- site/src/assets/js/showcase.js (picture zoom and tree labels)
- site/src/assets/css/main.css (the showcase's section)
- site/scripts/intent-tree.js (the tree counter)
- site/scripts/tree-svg.js (the tree drawing)
- .github/PULL_REQUEST_TEMPLATE/example.md
- site/tests/showcase.test.js, site/tests/intent-tree.test.js

Status markers: `[x]` implemented · `[ ]` active gap · `[D]` deferred

## The Index

- `[x]` **ONB-SHOWCASE-001**: The site SHALL serve the showcase's index at `/examples/`.
- `[x]` **ONB-SHOWCASE-002**: The index's h1 SHALL state a claim about the range of what people build with LID and SHALL NOT state how many projects the showcase holds.
- `[x]` **ONB-SHOWCASE-003**: The index SHALL list every entry exactly once, ordered by `date` with the newest first, and with ties broken by slug in alphabetical order.
- `[x]` **ONB-SHOWCASE-004**: The index SHALL show the first entry in that order as the featured project, in a wide card that places its picture beside its text.
- `[x]` **ONB-SHOWCASE-005**: The index SHALL show every entry after the first as a card in a grid, with its picture above its text.
- `[x]` **ONB-SHOWCASE-006**: Each index card SHALL show the entry's project name, its date, its size name when it has one, its story's title (or the project name when the entry has no story), its credit line, its tagline, the first three of its stats, and whether its code is open.
- `[x]` **ONB-SHOWCASE-007**: Each index card's picture SHALL be the entry's first picture, or the drawing of its tree when the entry has no pictures.
- `[x]` **ONB-SHOWCASE-008**: Each index card SHALL link to its project's page.
- `[x]` **ONB-SHOWCASE-009**: The index SHALL carry a section titled "Read a whole tree" that shows each reference tree, `examples/urlshort/` and LID's own design tree, as its drawing, a sentence, its spec count, design-doc count, and size name, and a link to the tree on the repository's `main` branch.
- `[x]` **ONB-SHOWCASE-010**: The reference trees' drawings, counts, and size names SHALL be measured from the repository at build time.
- `[x]` **ONB-SHOWCASE-011**: The reference trees' sentences SHALL state no numbers.
- `[x]` **ONB-SHOWCASE-012**: The index SHALL close with an invitation to add a project by pull request that says private projects are welcome and that a tree can be shown without its names, with a button linking to the "Share a project you built" section of `CONTRIBUTING.md`.

## Credit Lines

- `[x]` **ONB-SHOWCASE-013**: An entry's credit line SHALL be its `owner` followed by `'s project`.
- `[x]` **ONB-SHOWCASE-014**: When an entry's `story.author` differs from its `owner`, compared exactly, the credit line SHALL add "post written by" followed by the author.
- `[x]` **ONB-SHOWCASE-015**: A story's byline SHALL be its `story.byline` when given, and otherwise "by" followed by `story.author`, which defaults to the entry's `owner`.

## A Project's Page

- `[x]` **ONB-SHOWCASE-016**: The site SHALL serve a page for each entry at `/examples/<slug>/`.
- `[x]` **ONB-SHOWCASE-017**: A project's page SHALL show, in its reading column, the owner, whether the code is open, the size name when there is one, the project name as the h1, the tagline, the brief, and the story card.
- `[x]` **ONB-SHOWCASE-018**: A project's page SHALL show, in its side column, the entry's first picture, any further pictures as thumbnails, and a card titled "How big it is" holding the size name, every stat, the `stats_source` sentence when given, and each public link the entry gives.
- `[x]` **ONB-SHOWCASE-019**: When the viewport is too narrow for two columns, a project's page SHALL stack them with the reading column first.
- `[x]` **ONB-SHOWCASE-020**: A project's page SHALL show no picture taller than about two thirds of the viewport's height.
- `[x]` **ONB-SHOWCASE-021**: The story card SHALL show the story's title, its byline, where it lives ("Hosted here", or the host name of its `url`), and a button linking to it.
- `[x]` **ONB-SHOWCASE-022**: When an entry's story has neither a `file` nor a `url`, the story card SHALL show its title and byline with no button and say the story is to come.
- `[x]` **ONB-SHOWCASE-023**: When an entry has a tree file, its project's page SHALL show the tree's drawing at full width below the two columns, with the drawing's legend.

## Hosted Stories

- `[x]` **ONB-SHOWCASE-024**: When an entry's `story.file` is `story.md`, the site SHALL render it at `/examples/<slug>/story/` in the site's own style, under links back to the index and to the project's page, with the story's title, byline, and the entry's date.
- `[x]` **ONB-SHOWCASE-025**: When an entry's `story.file` is `story.html`, the site SHALL serve it at `/examples/<slug>/story/` exactly as written except for one inserted element, a bar placed as the first child of its `<body>`.
- `[x]` **ONB-SHOWCASE-026**: The bar inserted into a hosted `story.html` SHALL link back to the project's page and name whose project it is and who wrote the story, using inline styles only.
- `[x]` **ONB-SHOWCASE-027**: When an entry's `story.file` is `story.html`, the site SHALL serve the entry folder's files other than `index.md`, `tree.yaml`, and the story file beside the hosted story at `/examples/<slug>/story/`, so the story's relative links resolve.
- `[x]` **ONB-SHOWCASE-028**: The site SHALL NOT edit the words of a hosted story.

## Pictures

- `[x]` **ONB-SHOWCASE-029**: Every picture on a project's page SHALL be a link to its full-size file, so it enlarges without JavaScript.
- `[x]` **ONB-SHOWCASE-030**: When JavaScript runs and a reader activates a picture on a project's page, the site SHALL open the full-size picture in a dialog over the page instead of following the link.
- `[x]` **ONB-SHOWCASE-031**: The picture dialog SHALL close when the reader clicks anywhere in it, presses Escape, or activates its close button.
- `[x]` **ONB-SHOWCASE-032**: Opening the picture dialog SHALL move focus to its close button, and closing it SHALL return focus to the picture that opened it.
- `[x]` **ONB-SHOWCASE-033**: Every showcase picture SHALL carry the alt text its entry gives.

## The Tree Drawing

- `[x]` **ONB-SHOWCASE-034**: The build SHALL draw each tree as an inline SVG, with the HLD as a dark tile labeled "HLD" at the top, each sub-HLD as an outlined node with its children below it, and each leaf as a small outlined node at its own depth.
- `[x]` **ONB-SHOWCASE-035**: Under each leaf that has counts, the drawing SHALL hang its specs as a column of dots, filled for built specs and hollow for open ones.
- `[x]` **ONB-SHOWCASE-036**: The number of specs per dot SHALL be the smallest value in the sequence 1, 2, 5, 10, 20, 50, 100, and so on, for which the tallest leaf's column has at most 16 rows.
- `[x]` **ONB-SHOWCASE-037**: A leaf SHALL show its spec count divided by the specs per dot, rounded up, as dots.
- `[x]` **ONB-SHOWCASE-038**: Of a leaf's dots, its open specs divided by the specs per dot, rounded to the nearest whole number with halves rounded up, and at least one when any spec is open, SHALL be hollow, and the rest filled.
- `[x]` **ONB-SHOWCASE-039**: When any leaf in a tree lacks counts, the drawing SHALL show no dots for any leaf.
- `[x]` **ONB-SHOWCASE-040**: The drawing's SVG SHALL render no visible text other than "HLD"; its legend sits outside the SVG.
- `[x]` **ONB-SHOWCASE-041**: Each node that has a name in its tree file SHALL be focusable from the keyboard and carry a `<title>` giving its name and a note: for a leaf with counts, its spec count and how many are built; for a leaf without counts, "design doc"; for a sub-HLD, how many design docs lie below it.
- `[x]` **ONB-SHOWCASE-042**: A node without a name SHALL carry no `<title>` and SHALL NOT be focusable.
- `[x]` **ONB-SHOWCASE-043**: When JavaScript runs and a reader hovers over, focuses, or taps a named node, the page SHALL show that node's name and note in a label beside it and highlight the node.
- `[x]` **ONB-SHOWCASE-044**: The page SHALL show at most one node label at a time, and SHALL close it when the pointer leaves the node, focus moves away, or the reader taps elsewhere.
- `[x]` **ONB-SHOWCASE-045**: The drawing's SVG SHALL carry an accessible label stating how many design docs the tree has, how many levels deep it goes, and, when every leaf has counts, how many specs.
- `[x]` **ONB-SHOWCASE-046**: The drawing SHALL carry a legend naming the HLD, a sub-HLD, and a design doc, and, when every leaf has counts, a built spec and an open spec with the specs per dot.
- `[x]` **ONB-SHOWCASE-047**: When any node in a tree has a name, the legend SHALL end with a line saying names show on hover or tap.
- `[x]` **ONB-SHOWCASE-048**: When a drawing is too wide to keep each leaf at least 12 pixels wide, it SHALL keep that width and scroll sideways within its frame.

- `[x]` **ONB-SHOWCASE-091**: A tree's design-doc count SHALL be its number of leaves; neither the HLD nor a sub-HLD counts as a design doc.
- `[x]` **ONB-SHOWCASE-092**: The site SHALL serve each picture an entry names at `/examples/<slug>/<file>`.

## Size Names

- `[x]` **ONB-SHOWCASE-049**: An entry's size name SHALL be "Small" for a total under 100 specs, "Medium" from 100 to 499, "Large" from 500 to 999, and "Very large" from 1,000.
- `[x]` **ONB-SHOWCASE-050**: The total for an entry's size name SHALL be its tree file's spec total when every leaf has counts, and otherwise its `spec_count`.
- `[x]` **ONB-SHOWCASE-051**: When an entry has neither a fully counted tree nor a `spec_count`, it SHALL show no size name.

## Entries and the Build

- `[x]` **ONB-SHOWCASE-052**: The build SHALL treat each folder in `site/src/examples/` whose name does not start with `_` or `.` as one entry, and SHALL publish nothing from the others.
- `[x]` **ONB-SHOWCASE-053**: If an entry breaks any rule in this section or in *The Tree File*, the build SHALL fail with a message naming the entry and the rule.
- `[x]` **ONB-SHOWCASE-054**: An entry's folder name SHALL consist of lowercase letters, digits, and hyphens.
- `[x]` **ONB-SHOWCASE-055**: An entry's `index.md` front matter SHALL hold `project`, `owner`, `tagline`, `date` as an ISO date, and `open_source` as `true` or `false`.
- `[x]` **ONB-SHOWCASE-056**: An entry's front matter SHALL hold no fields other than `project`, `owner`, `tagline`, `date`, `open_source`, `pictures`, `stats`, `stats_source`, `spec_count`, `story`, and `links`.
- `[x]` **ONB-SHOWCASE-057**: An entry SHALL have at least one picture or a tree file.
- `[x]` **ONB-SHOWCASE-058**: Each picture an entry names SHALL be a file in the entry's folder whose name ends in `.png`, `.jpg`, or `.jpeg` (in any case), no larger than 2,000,000 bytes, with non-empty `alt` text.
- `[x]` **ONB-SHOWCASE-059**: Each `stats` item SHALL be a pair of strings, and the site SHALL show them exactly as written.
- `[x]` **ONB-SHOWCASE-060**: An entry's `links` SHALL hold only `repo`, `hld`, `intent_tree`, and `live`, each an `https` URL.
- `[x]` **ONB-SHOWCASE-061**: An entry whose `open_source` is `false` SHALL have no `repo`, `hld`, or `intent_tree` link.
- `[x]` **ONB-SHOWCASE-062**: An entry's `story` SHALL hold a `title`, MAY hold `author` and `byline`, SHALL hold at most one of `file` and `url`, and SHALL hold no other fields; a `file` SHALL be `story.md` or `story.html` and SHALL exist, and a `url` SHALL be an `https` URL.
- `[x]` **ONB-SHOWCASE-063**: An entry's folder SHALL hold no `story.md` or `story.html` that its `story.file` does not name.
- `[x]` **ONB-SHOWCASE-064**: A hosted `story.md` SHALL have no front matter.
- `[x]` **ONB-SHOWCASE-065**: A hosted `story.html` SHALL contain a `<body>` element.
- `[x]` **ONB-SHOWCASE-090**: A hosted `story.html` SHALL contain no `<script>` element and SHALL load no resource (image, style sheet, font, or frame) from outside its entry folder; ordinary links to other sites are allowed.
- `[x]` **ONB-SHOWCASE-066**: The build SHALL NOT publish `site/src/examples/_template/`, which holds a filled-in sample entry with every field commented.

## The Tree File

- `[x]` **ONB-SHOWCASE-067**: A tree file SHALL hold a non-empty `children` list. Each node in it SHALL have an optional `name`, and SHALL be either a sub-HLD, holding a non-empty `children` list and no counts, or a leaf, holding no `children`.
- `[x]` **ONB-SHOWCASE-068**: A leaf in a tree file SHALL carry both `specs` and `built`, or neither.
- `[x]` **ONB-SHOWCASE-069**: A leaf's `specs` and `built` SHALL be whole numbers with `built` no greater than `specs`.

## The Tree Counter

- `[x]` **ONB-SHOWCASE-070**: `site/scripts/intent-tree.js` SHALL run with Node and no installed dependencies as `node site/scripts/intent-tree.js <design-dir> [--no-names]`, writing a tree file to standard output.
- `[x]` **ONB-SHOWCASE-071**: The counter SHALL export the function it uses to measure a tree, so the site's build measures the reference trees with the same code.
- `[x]` **ONB-SHOWCASE-072**: The counter SHALL treat a file whose name ends in `-specs.md` as a spec file, and no other file.
- `[x]` **ONB-SHOWCASE-073**: The counter SHALL treat a directory as a sub-HLD when it holds child nodes, and as a leaf when it holds exactly one spec file and no child nodes.
- `[x]` **ONB-SHOWCASE-074**: When a directory holds more than one spec file and no child nodes, the counter SHALL make one leaf per spec file, named for the file without its `-specs.md` ending.
- `[x]` **ONB-SHOWCASE-075**: When a directory holds its own spec files and child nodes, the counter SHALL make it a sub-HLD and add one leaf beneath it per own spec file, named like the directory when it has one spec file and for each file's stem when it has several.
- `[x]` **ONB-SHOWCASE-076**: The counter SHALL skip hidden directories, directories named `decisions`, symbolic links, and directories that hold no spec file at any depth.
- `[x]` **ONB-SHOWCASE-077**: The counter SHALL list each node's children in alphabetical order of name.
- `[x]` **ONB-SHOWCASE-078**: The counter SHALL count as a spec each list item, at any indentation and under `-`, `*`, or `+`, whose text starts with a status marker `[x]`, `[X]`, or `[ ]`, optionally in backticks, followed by a bold ID of capital letters, digits, and hyphens ending in a number.
- `[x]` **ONB-SHOWCASE-079**: The counter SHALL count a spec marked `[x]` or `[X]` as built.
- `[x]` **ONB-SHOWCASE-080**: The counter SHALL NOT count a spec marked `[D]`.
- `[x]` **ONB-SHOWCASE-081**: The counter SHALL NOT count lines inside fenced code blocks.
- `[x]` **ONB-SHOWCASE-082**: The counter SHALL count every matching line, including lines that repeat an ID.
- `[x]` **ONB-SHOWCASE-083**: The counter SHALL name each node for its directory, or for its spec file's stem in a flat layout, and SHALL write no names when given `--no-names`.
- `[x]` **ONB-SHOWCASE-084**: The counter's output SHALL hold only node names, the tree's structure, and counts: no document text, no spec IDs, and no paths.
- `[x]` **ONB-SHOWCASE-093**: The counter SHALL make each spec file directly inside the design directory a leaf directly beneath the HLD, named for the file's stem.
- `[x]` **ONB-SHOWCASE-085**: When the design directory does not exist or holds no spec file, the counter SHALL write an error to standard error and exit with a non-zero status.

## Contributing a Project

- `[x]` **ONB-SHOWCASE-086**: `.github/PULL_REQUEST_TEMPLATE/example.md` SHALL ask for the project's name, owner, tagline, and whether it is open source.
- `[x]` **ONB-SHOWCASE-087**: The example template SHALL list the entry folder's files as a checklist, with the command that makes a tree file and its `--no-names` option.
- `[x]` **ONB-SHOWCASE-088**: The example template SHALL ask where the entry's numbers come from.
- `[x]` **ONB-SHOWCASE-089**: The example template SHALL ask the contributor to confirm that they own the project or have its owner's agreement, that every picture and word in the entry may be published on the site, and that a story written by an AI credits it.
