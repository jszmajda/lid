---
node: high-level-design
---

# Decision: Spec-file placement relative to the design tree

## Context

This builds on the recursive design tree ([`recursive-intent-tree.md`](./recursive-intent-tree.md)) and path-concatenated IDs ([`namespace-structure.md`](./namespace-structure.md)) — read those first. Given that the design layer (`docs/intent/`) is now a tree, the EARS spec files have no settled home: they sit flat in `docs/specs/`, a layout from before intent nested. Where they live is a **project-wide convention** — the HLD navigation table, the `update-lid` bootstrap, and the LLD/HLD templates all name `docs/specs/` — so the choice reaches every adopter, and it is hard to reverse once a project's `@spec`-annotated code depends on it.

Two factors that look decisive but are not. First, **agent retrieval from an `@spec` ID is location-independent**: an agent reaches a spec by grepping the ID (a content match that works wherever the file sits) and resolves an ID to its owning doc via the `prefix:`/`index.yaml` lookup. No option below changes that. Second, the *verticalize intent* tenet governs **intent navigation** — the design tree and the ID structure — not the physical file layout. A second directory is a filesystem maintenance cost, not a second intent axis; the tenet does not decide this. What is genuinely at stake is how a *human* finds and reads a doc, and the upkeep cost of however many directory structures result.

## Decision Elements

**Gate** *(an option that violates it is eliminated)*

- **No cross-segment collision.** Two distinct segments must not collide on filename or path. Path-concatenated IDs are globally unique, but the *files* are not automatically so: two leaves named `core` under different parents would both want `core-specs.md`. An option that cannot keep distinct segments distinct on disk is eliminated.

**Criteria** *(importance: major / moderate / minor)*

- **Browse-tree findability — major.** A human orients by skimming the file tree in a navigator or sidebar. Does the on-disk shape mirror the intent tree they hold in their head, and is each directory's content legible rather than noisy?
- **Fuzzy-search findability — major.** A human also opens a doc by typing a fragment into a fuzzy finder (`@coach`, Cmd-P "coach"). This is a distinct action from browsing, and it turns on filenames: meaningful, segment-named basenames surface the right doc directly; generic basenames force path-based disambiguation and flood on common terms.
- **Filesystem structures to keep coherent — moderate.** How many parallel directory structures must stay in sync as the tree changes — one, or two mirrored ones — and what a tooled re-parent/rename therefore has to rewrite.
- **Segment-as-unit legibility — moderate.** LID's ontology is that a segment *owns* its design and its specs. Does the layout make that ownership visible on disk?
- **Adopter migration cost — minor.** One-time disruption to existing projects. Minor because it is a one-time file move (IDs and code are untouched) and, per the namespace decision's logic, restructuring is cheap early and rare late.

*Fit verdicts below — `strong / partial / weak` for criteria, `passes / eliminated` for the gate — classify each option against the element; the weighing happens in Selection.*

## Options in the Domain

### Option A — Node-as-folder

**Description.** Every node in the tree is a directory. It contains its design doc, its specs doc if it is a leaf that owns EARS, a `decisions/` directory if it has decision docs, and a child directory per child if it is a sub-HLD. A leaf and a sub-HLD become the same shape, distinguished only by whether the folder holds a specs doc or child folders. Crucially, the inner files are **named for the segment, not for their role** — `{node}-design.md` and `{node}-specs.md`, not `design.md`/`specs.md` — so they remain fuzzy-findable by the segment name. (Generic inner names are the rejected sub-form: they would forfeit fuzzy-search for a cosmetic gain.)

**Demonstration.** `docs/intent/linked-intent-dev/lid-coach/` holds `lid-coach-design.md`, `lid-coach-specs.md`, and `decisions/`. Browsing the file tree *is* walking the intent tree; typing `coach` in a fuzzy finder surfaces both files by name. There is no longer a `lid-coach.md` file beside a `lid-coach/` directory — the file-beside-folder pattern disappears.

**Analysis.**
- *No cross-segment collision (gate):* **passes** — every node has a unique folder path and segment-named files.
- *Browse-tree findability (major):* **strong** — folder names are the segments; the layout is the tree, and the file-beside-folder wart is gone.
- *Fuzzy-search findability (major):* **strong** — segment-named inner files (`lid-coach-design.md`, `lid-coach-specs.md`) surface directly on a name fragment.
- *Filesystem structures to keep coherent (moderate):* **strong** — one tree; a rename/re-parent moves one directory.
- *Segment-as-unit legibility (moderate):* **strong** — a folder literally *is* the segment, enclosing all its artifacts.
- *Adopter migration cost (minor):* **weak** — the largest move: every leaf becomes a directory and its files are renamed.

**Summary.** Strong across browsing, fuzzy-search, single-structure, and segment-as-unit; its cost is the largest one-time migration plus mild verbosity (`lid-coach/lid-coach-design.md` repeats the name).

### Option B — Sibling files

**Description.** A spec file sits beside its leaf LLD as a paired file in the parent directory, keyed by the segment's name: `core.md` and `core-specs.md`. Only sub-HLDs get directories (the existing sibling-file pattern — `foo.md` beside `foo/`); the specs join as more siblings. `docs/specs/` is eliminated.

**Demonstration.** `docs/intent/linked-intent-dev/` holds `core.md` + `core-specs.md`, `update-lid.md` + `update-lid-specs.md`, `lid-coach.md` + `lid-coach-specs.md`.

**Analysis.**
- *No cross-segment collision (gate):* **passes** — the parent directory makes the path unique even when two leaves share a basename.
- *Browse-tree findability (major):* **partial** — one tree, but each leaf contributes two loose files to its parent (a broad sub-HLD's directory roughly doubles in file count), and the file-beside-folder wart for sub-HLDs remains.
- *Fuzzy-search findability (major):* **strong** — every file carries the segment name; `coach` finds the LLD and its specs directly.
- *Filesystem structures to keep coherent (moderate):* **strong** — one tree; specs live beside their LLD in the same node.
- *Segment-as-unit legibility (moderate):* **partial** — design and specs are a named pair in a shared directory rather than enclosed in the segment's own container.
- *Adopter migration cost (minor):* **partial** — spec files move from `docs/specs/` into the LLD tree; IDs and code are untouched.

**Summary.** Shallower than node-as-folder and strong on fuzzy-search, but the parent directories grow noisy and the segment is a loose pair rather than an enclosed unit.

### Option C — Stay split (mirror `docs/specs/` to the tree)

**Description.** Keep `docs/specs/` as a separate top-level directory, but nest it to mirror the shape of `docs/intent/` so specs stay structured. (The *flat* form — one undivided `docs/specs/` — is eliminated by the collision gate the moment two leaves share a name, so the only viable split form is the mirror.)

**Demonstration.** `docs/intent/linked-intent-dev/lid-coach.md` is the design; `docs/specs/linked-intent-dev/lid-coach-specs.md` is its specs. The two trees carry the same shape in parallel.

**Analysis.**
- *No cross-segment collision (gate):* **passes** in the mirror form (the flat form is eliminated).
- *Browse-tree findability (major):* **partial** — each tree reads cleanly on its own, but seeing one segment's full picture means navigating to the same path in two trees.
- *Fuzzy-search findability (major):* **strong** — filenames stay meaningful (`lid-coach-specs.md`).
- *Filesystem structures to keep coherent (moderate):* **weak** — two trees mirror each other; a re-parent or rename must rewrite both in lockstep.
- *Segment-as-unit legibility (moderate):* **weak** — design and specs sit in different trees; ownership is implied by parallel structure, not shown.
- *Adopter migration cost (minor):* **strong** — additive: keep `docs/specs/`, just nest it; the least disruptive option.

**Summary.** Most familiar and lowest migration, paid for with a second directory structure to keep in sync and a segment whose two halves never sit together.

## Selection

**Chosen: Option A — node-as-folder, with segment-named inner files.**

Option A is **strong on both major criteria and both moderate ones**, weak only on the minor (migration). The segment-named inner files (`{node}-design.md`, `{node}-specs.md`) are what let it hold both kinds of findability at once: the folder tree gives browse-findability and the named files give fuzzy-findability, where the two competitors each give up one of those or a moderate. Option B is **partial** on browse-findability — loose paired files thicken every directory and the file-beside-folder pattern persists — and only partial on segment-as-unit. Option C is **weak** on both moderates: two parallel trees to keep coherent, and a segment split across them.

The cost A carries is real but lands low: the largest one-time migration (every leaf becomes a directory), and mild verbosity where the folder name repeats in the filename (`lid-coach/lid-coach-design.md`). Migration is the minor criterion by the namespace decision's reasoning — restructuring is cheap while a project is young and rare once it settles — and the verbosity is the price of keeping fuzzy-search, which a major criterion demands.

**Implications.**
- `docs/specs/` is eliminated; every node is a directory holding `{node}-design.md`, a `{node}-specs.md` when it is a leaf, a `decisions/` directory when it has decision docs, and child directories when it is a sub-HLD.
- **Inner design filename** is `{node}-design.md` — `design` is role-accurate for every node (the root is an HLD, middles are sub-HLDs, leaves are LLDs, all are "design"), where `-lld` would misname the non-leaf nodes.
- The root HLD stays at `docs/high-level-design.md` (it is not folded into the tree as a `-design.md`), and the tree-root directory is `docs/intent/` (renamed from `docs/llds/`, since the tree holds sub-HLDs, leaf LLDs, their specs, and decision docs — more than LLDs).
- **Cascade** to the HLD navigation table, to `update-lid` (bootstrap directory set; `LID-UPDATE-015` drops `docs/specs/`), to the LLD/HLD templates and `ears-syntax.md`, to `project-structure`, and to `arrow-maintenance` (the tooled re-parent/rename now moves a node's directory whole, design and specs together).
- One-time adopter migration is mechanical (`docs/specs/<seg>-specs.md` → the node's directory); `@spec` IDs and code are untouched, and `/update-lid` version-walk can assist.
