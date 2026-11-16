---
parent: onboarding
prefix: ONB-SHOWCASE
---

# LLD: Examples Showcase

**Created**: 2026-11-15
**Status**: Design Phase

## Context and Design Philosophy

The examples showcase is the part of the site that shows what people have built with LID. Its job is to get a reader excited about working with LID by showing how different the results can be: a desktop written in days, a game its owner never read the code of, a tax tracker with proven arithmetic, a product that has lived with LID for well over a year. Each project gets a page of its own on the site, and each page links deeper, to the story of how the project was built and to whatever of the project is public.

The showcase is a child of the `onboarding` sub-HLD and inherits its reader, its voice, its claims rule, and its rule for content the site presents. It sits on the site that the `marketing-site` segment owns: that segment owns the navigation, the visual identity, the copy register, and the build; this one owns the showcase's pages, the entry format a project is described in, the drawing of a project's intent tree, the counter that measures a tree, and the route by which projects arrive.

Projects arrive from their owners, by pull request. The showcase is curated, not a feed: the maintainer reviews and merges each entry, and nothing on the site accepts comments or discussion. Projects need not be open source. A private project shows only what its owner chooses: its numbers, its pictures, its story, and, if they wish, the shape of its intent tree without a single name in it.

**Terms.** A **project** is one showcased piece of work, described by one **entry**. A project's **story** is the post about how it was built, written by anyone the owner credits and hosted on the site or elsewhere. A **tree file** records a project's intent tree as names and spec counts, with nothing of the docs' text. A **reference tree** is a tree shown for reading rather than as a story: the repository's own `examples/urlshort/` and LID's own design tree.

## Pages

### The index (`/examples/`)

The index is a showcase, newest first.

- **Heading and lede.** The h1 states a claim about the range of what people build with LID and never states how many projects there are, so adding one changes no copy. The lede names a few of the projects' outcomes in a phrase each.
- **The featured project.** The project whose entry carries the latest date is shown first, in a wide card: its picture on one side and, on the other, its project name, date and size name, its story's title, its credit line, its tagline, up to three of its stats, and where it can be read.
- **The rest.** Every other project follows in a grid of cards with the same contents, its picture on top. A card's picture is the entry's first picture, or the drawing of its tree when it has no pictures. The whole card leads to the project's page.
- **Read a whole tree.** A short section shows the reference trees, each as its drawing, a sentence, a few numbers, and a link to the tree in the repository. Their drawings are measured from the repository at build time, so they are never stale.
- **The invitation.** The page closes by inviting readers to add their own project by pull request, and says that private projects are welcome and that a tree can be shown without its names. Its button leads to the instructions in `CONTRIBUTING.md`.

A card's **credit line** names the owner ("Friday's project"). When the story's author is someone other than the owner, the line adds them ("post written by Claude").

### A project's page (`/examples/<slug>/`)

The page puts the reading first. Nothing on it is so large that it hides the text below the first screen.

- **The top, in two columns.** On one side: the owner and whether the code is open, the size name, the project name as the h1, the tagline, the brief, and a card for the story. On the other: the first picture at a moderate size, any further pictures as small thumbnails, and a card titled "How big it is", holding its size name, its stats, where the numbers come from, and its public links (repository, HLD, intent tree, live site).
- **The story card** shows the story's title, its byline, and where it lives ("Hosted here", or the site that hosts it), with a button to read it. A project whose story has not been written yet shows the card without a button, saying the story is to come.
- **The intent tree**, below the top, at full width when the entry has a tree, with its legend (see *The Tree Drawing*).
- **Narrow screens** stack the two columns, with the reading first.

### A hosted story (`/examples/<slug>/story/`)

An entry may host its story on the site, in one of two forms:

- **`story.md`**: rendered in the site's own style, under a path back to the index and to the project's page, with the story's title, byline, and date.
- **`story.html`**: a self-contained page served exactly as its author made it, with one addition the build inserts at its top: a thin bar that leads back to the project's page and names whose project it is and who wrote the story.

A story is its author's words. Under the parent's rule for content the site presents, the site never edits it, and the site's copy register does not apply to it. The tagline and the brief are the site's framing of the project, so the copy register applies to them, and the maintainer edits them at review when needed.

### Pictures

Every picture on a project's page leads to its full-size file, so it can be enlarged without JavaScript; on the index, a card's picture leads to the project's page instead. With JavaScript, clicking a picture opens it over the page in a dialog that closes on a click, on Escape, or on its close button. Each picture carries the alt text its entry gives.

## The Tree Drawing

A project's intent tree is drawn at build time as an SVG, in the site's line style. The drawing tells the size and shape of a project better than its numbers do, so the showcase draws it whenever a tree file or a reference tree is available.

- **Nodes.** The HLD is a dark tile at the top labeled "HLD". A sub-HLD is an outlined node with its children below it. A leaf design doc is a small outlined node. Leaves sit at their own depth, so nesting shows as height.
- **Specs as dots.** Under each leaf hang its specs as a column of dots: filled for a spec that is built, hollow for one that is not. One dot stands for one spec, or for several when a project is large; the number per dot is chosen so the tallest column stays a readable height, and the legend states it.
- **Shape without counts.** A tree whose leaves carry no counts is drawn as nodes alone, and the legend leaves out the dot keys.
- **Names on demand.** The drawing shows no text but "HLD". A node that has a name in the tree file shows it, with a short note (a leaf's spec count and how many are built; a sub-HLD's count of design docs below it), when the reader hovers over it, focuses it, or taps it. Without JavaScript the same text is the node's native tooltip. A node without a name shows nothing.
- **The legend** sits under the drawing: the HLD, a sub-HLD, a design doc, and, when there are counts, a built spec and an open one, each with its count per dot. It ends with one line saying names can be revealed by hovering or tapping, when any node has one.

### Size names

A project's size name comes from its total spec count: **Small** under 100, **Medium** from 100 to 499, **Large** from 500 to 999, and **Very large** from 1,000. The count is the tree file's total when the tree has counts, and otherwise the `spec_count` the entry gives. An entry with neither shows no size name. The thresholds live in one place in the build so they can be moved as the roster grows.

## The Entry Format

An entry is one folder, `site/src/examples/<slug>/`, whose name is the project's URL. It holds:

- **`index.md`**, whose front matter describes the project and whose body is the brief, a paragraph or two on what the project is and how it was built.
- **Pictures** the front matter names, in PNG or JPEG.
- **`tree.yaml`**, the tree file, when the owner provides one.
- **`story.md` or `story.html`**, when the story is hosted here.

`site/src/examples/_template/index.md` is a filled-in sample with every field commented, for contributors to copy; the build does not publish it.

| Front-matter field | Required | Meaning |
|---|---|---|
| `project` | yes | The project's name as shown. |
| `owner` | yes | Who owns the project, as they want to be credited. |
| `tagline` | yes | One sentence on what the project is. |
| `date` | yes | The date the entry is about (usually its story's date); orders the index. |
| `open_source` | yes | `true` or `false`; shown as "Open source" or "Code private". |
| `pictures` | no | A list of `{file, alt}`; the first is the project's picture. |
| `stats` | no | A list of `[label, value]` pairs, in the owner's words. Up to three appear on the card, in order. |
| `stats_source` | no | One sentence on where the numbers come from. |
| `spec_count` | no | The project's total spec count, for the size name when the tree file has no counts. |
| `story` | no | `{title, author, byline?, file?, url?}`: a hosted `file` or an external `url`, or neither while the story is to come. `author` defaults to the owner; `byline` overrides the default "by <author>". |
| `links` | no | Any of `repo`, `hld`, `intent_tree`, `live`, each a public URL. |

### The tree file

`tree.yaml` holds a list of `children` under the HLD. Each node has an optional `name`, and either `children` of its own (a sub-HLD) or `specs` and `built` counts (a leaf). A leaf may omit both counts when they are unknown. A name may be left out of any node, and the drawing then shows nothing for it.

## The Tree Counter

`site/scripts/intent-tree.js` measures a design tree and writes its tree file. It is plain Node with no dependencies, so a contributor can run it on a checkout of their own project, and the site's build imports the same module to measure the reference trees.

- **Usage:** `node site/scripts/intent-tree.js <design-dir> [--no-names] > tree.yaml`, where `<design-dir>` is the project's design tree, usually `docs/intent`.
- **What counts as a node.** Each directory below the design directory that holds a spec file, or holds such directories, is a node; one that holds child nodes is a sub-HLD, and one that holds a spec file and no child nodes is a leaf. A directory holding several spec files and no child nodes contributes one leaf per spec file, named for the file without its `-specs.md` ending; this reads a flat layout such as `examples/urlshort/docs/specs/`. Hidden directories and `decisions/` directories are skipped.
- **What counts as a spec.** A list item at any indentation (`-`, `*`, or `+`) whose text starts with a status marker, `[x]`, `[X]`, `[ ]`, or `[D]`, with or without backticks, followed by a bold ID of the form `**PREFIX-NNN**` (capital letters, digits, and hyphens, ending in a number). Lines inside fenced code blocks are skipped. Every such line is counted, duplicates included, except deferred ones: a `[D]` spec is designed but not planned, so the counter leaves it out of `specs` and the drawing never shows it. Of the counted specs, those marked `[x]` or `[X]` are built.
- **Which files are spec files:** files whose names end in `-specs.md`. Symbolic links are not followed. A directory holding its own spec files and child nodes as well is drawn as a sub-HLD with one more leaf beneath it per own spec file, named like the directory when there is one file and for each file's stem when there are several; spec files directly in the design directory are leaves beneath the HLD. A tree's design-doc count is its number of leaves. Children are listed in alphabetical order. A design directory that does not exist, or holds no spec files, is an error.
- **Names.** A node's name is its directory name, or its spec file's stem in a flat layout. `--no-names` writes the tree with no names at all. An owner who wants to keep some names and not others deletes the ones they don't want from the file by hand.
- **Output** is the tree file described above, and nothing else: no doc text, no IDs, no paths.

## Rules the Build Enforces

The build is the gate for an entry: **any rule below that an entry breaks fails the site's build**, with a message naming the entry and the rule, so a broken entry cannot merge.

**Entries**
- A slug is lowercase letters, digits, and hyphens. Folders whose names start with `_` or `.` are not entries.
- Every required field is present; `date` is an ISO date (`YYYY-MM-DD`); `open_source` is `true` or `false`; unknown fields are an error, so a typo is caught.
- An entry has at least one picture or a tree file, so every card has a picture.
- Each picture is a PNG or JPEG file in the entry folder, carries non-empty `alt` text, and is no larger than 2 MB. The build serves the originals; it does not resize them.
- A private entry (`open_source: false`) has no `repo`, `hld`, or `intent_tree` link; `live` is allowed. Whether a public link points at anything private is the maintainer's review.
- `stats` values are strings, shown exactly as written. The card shows the first three; the project's page shows all of them.

**Stories**
- `story` names at most one of `file` and `url`. A `file` is `story.md` or `story.html`, and it exists. A story file in the folder that the entry does not name is an error.
- `story.md` has no front matter of its own: its title is `story.title`, its date the entry's `date`.
- `story.html` has a `<body>` element, contains no script, and loads no image, style sheet, font, or frame from outside its folder (links to other sites are fine), so a hosted story can never bring tracking onto the site, as `marketing-site` promises. The build inserts the bar as the body's first child, styled inline so the author's styles and the bar's stay apart, and serves the page at `/examples/<slug>/story/` with the entry folder's other files beside it, so the page's relative links resolve.

**The credit line** is the owner's name with `'s project` ("Friday's project"). When `story.author` differs from `owner`, compared exactly, it adds "post written by" and the author. The story card and a hosted story's byline use `story.byline` when given, otherwise "by" and the author. A card whose entry has no story is headed by the project's name.

**Ordering.** The index orders entries by `date`, newest first, and breaks ties by slug. The first is the featured project. Future dates are allowed.

**The tree file**
- Every leaf has both `specs` and `built`, or neither; `built` is a whole number no greater than `specs`. A node has `children` or counts, never both, and a `children` list is never empty.
- When every leaf has counts, the tree's total gives the size name. When any leaf lacks them, the drawing shows no dots and the size name comes from `spec_count`. When both a total and `spec_count` exist, the total wins; a disagreement is the maintainer's to catch at review.

**The drawing**
- Dots per spec is the smallest of 1, 2, 5, 10, 20, 50, 100 (and so on) that keeps the tallest leaf's column within 16 rows. A leaf shows its spec count divided by that number, rounded up; of those, its open specs take their share rounded to the nearest dot, and at least one dot when any spec is open. The rest are filled.
- Named nodes are focusable from the keyboard; unnamed ones are not. Each named node carries a `<title>` with its name and note, which is the native tooltip without JavaScript and the accessible name with it. The SVG as a whole has an accessible label summarizing the tree (its design docs, depth, and spec counts). One label shows at a time; it closes when the pointer leaves, focus moves, or the reader taps elsewhere.
- A tree too wide to read at the page's width keeps a minimum node width and scrolls sideways inside its frame rather than shrinking further.

**Pictures on a project's page** are at most about two thirds of the screen's height. The zoom dialog shows one picture; opening it moves focus to its close button and closing it returns focus to the picture.

**Reference trees.** Each has a hand-written sentence in the index template, under the copy register, that states no numbers. The numbers beside it (spec count and design docs) and its size name are computed at build time. Names are shown, since both trees are public. Each links to its tree on the repository's `main` branch.

## Contributing a Project

A project arrives as a pull request that adds one entry folder and nothing else. The repository carries a pull-request template for it, `.github/PULL_REQUEST_TEMPLATE/example.md`, alongside the default template, chosen by adding `?template=example.md` to the pull request's URL. The template asks for:

- the project's name, owner, tagline, and whether it is open source;
- a checklist of the folder's files, with how to make the tree file and the `--no-names` option;
- where the numbers come from;
- confirmation that the contributor owns the project or has its owner's agreement, that every picture and word may be published on the site, and that a story written by an AI credits it.

`CONTRIBUTING.md` carries a short section, "Share a project you built", that points to the template and says that an entry is content within this segment's existing design, so adding one walks no arrow. The index's invitation links to that section.

The maintainer's review checks the permissions, that a private project's entry links to nothing private, that the tagline and brief follow the copy register, and that the site builds.

## Verification

This segment is a content artifact, verified as the parent's other children are: by build-time checks and by review.

- **Build-time checks** in `site/tests/`: every entry has the required fields; every picture, story file, and tree file an entry names exists; every tree file parses and every leaf's `built` is no more than its `specs`; the index lists every entry, newest first; each entry has a page; each hosted story has its page; and the reference trees are measured from the repository.
- **The counter's tests** run it on small fixture trees: node-as-folder, flat, nested sub-HLDs, unknown counts, skipped directories, and `--no-names`.
- **By eye**, in both themes and at phone width: the index, a project's page, the zoom dialog, and the tree labels.

## Cascade

- **The parent sub-HLD's reader, voice, or presentation rule changes:** this segment's pages are reviewed.
- **`marketing-site` changes its navigation, visual identity, or copy register:** the showcase's pages follow; its copy register binds the tagline and brief.
- **An entry is added or edited:** no cascade; entries are content within this design.
- **The tree-file format or the counter's output changes:** every committed tree file is regenerated or migrated in the same change, and the PR template's instructions follow.
- **LID's own design tree changes:** the reference tree redraws at the next build of the site.

## Decisions & Alternatives

| Decision | Chosen | Alternatives Considered | Rationale |
|---|---|---|---|
| Unit of the showcase | A page per project on the site, linking deeper to its story | Cards that link straight out to each story | A page of its own lets every project show its picture large enough to see, its tree, and a short brief, whatever its story looks like or wherever it lives. |
| Stories | Free-form, by any author, hosted here (Markdown or a self-contained HTML page) or linked elsewhere | One fixed template for every story | Projects differ, and so do the best ways to tell how they were built; a fixed template would flatten the range the showcase exists to show. |
| How projects arrive | Pull requests, reviewed and merged by the maintainer | Issues that the maintainer turns into entries; a form | A pull request carries the files themselves, keeps the contributor's words as they wrote them, and puts every addition through the same review as any other change. |
| Showing size | The tree drawing first, with a few stats and a size name | Stats alone | The drawing shows size and shape at a glance, and the share of built specs, in a way a list of numbers does not. |
| Names in a private or spoiler-sensitive tree | Left out by the owner, all at once with `--no-names` or one by one by hand | Never show names; always show names | Names make a tree readable, but they can reveal a private design or spoil a game; only the owner knows which. |
| Where the counter lives | `site/scripts/`, in Node, used by contributors and by the build | A Python script under `tools/` | One implementation serves both uses, and the site's build has no other language to install. |
| Deferred specs | Left out of the counts and the drawing | Drawn as open specs | A deferred spec is designed but not planned work; drawing it as open would make a project look less finished than its plan says it is. |
| Size thresholds | Spec counts of 100, 500, and 1,000 | Lines of code; no size names | Every LID project has specs, counted the same way in any language; lines of code vary by language and by whether tests count. |
| Large pictures | A moderate picture that enlarges on click | A full-width picture at the top of each page | A full-width picture pushed the brief below the first screen and hid that the page had anything to read. |

## Open Questions & Future Decisions

### Deferred

- Retiring a project whose story or site has gone away: removal by pull request is enough until it happens.
- Filtering or grouping the index once it holds many projects.

## References

- `docs/intent/onboarding/onboarding-design.md`: the parent sub-HLD (the reader, the voice, the claims rule, content the site presents).
- `docs/intent/onboarding/marketing-site/marketing-site-design.md`: navigation, visual identity, copy register, the build.
- `docs/high-level-design.md`: Goal 5.
