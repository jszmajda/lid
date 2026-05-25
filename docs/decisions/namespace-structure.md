---
node: high-level-design
---

# Decision: Namespace structure for nested intent

## Context

This decision builds on the recursive design tree decided in [`recursive-intent-tree.md`](./recursive-intent-tree.md) — read that first; it is the premise here. Given that the design layer is a tree, an EARS ID must encode *where in the tree* a spec lives, so that intent stays navigable as depth grows.

The boundary an ID encodes is the *leaf's* path: the prefix runs from the root to the leaf that owns the spec, and that leaf path is the cascade boundary. After the leaf path a project MAY append one within-leaf type/area segment (`AUTH-UI-001`, `ENGINE-LEDGER-001`) that groups specs inside a single leaf — a facet, not a tree node and not a boundary. The model therefore accommodates the `{FEATURE}-{TYPE}-{NNN}` shape: `{FEATURE}` is the leaf path, `{TYPE}` the in-leaf facet. Because the path/facet split is not always parseable from the ID string alone, the leaf's `prefix:` frontmatter is authoritative for where the path ends.

The structure chosen here is hard to reverse. Spec IDs do not stay in spec files — they appear in `@spec` annotations across code and tests, and LID promises both **stable IDs** and **grep-navigable intent**. What is at stake is navigability (a stated design goal), the cost of any future restructuring, and how much machinery an agent needs to discover intent from a starting point as small as one annotation in a source file.

## Decision Elements

**Constraints in force** *(inherited; gates — an option that violates one is eliminated)*

- **Stable IDs.** Spec IDs appear in `@spec` annotations throughout code and tests. An option that renames IDs during *ordinary growth* — adding or refining specs within a segment — is disqualified, because ordinary growth would then mean editing source files. (Deliberate restructuring is not ordinary growth; it is addressed in Selection.)

**Criteria** *(importance: major / moderate / minor)*

- **Grep-navigability of intent — major.** A stated HLD goal: a single `grep` should gather all intent under a subsystem.
- **Single-axis navigation — major.** From the *verticalize intent* tenet: locating intent should follow one axis, not require a second structure to learn and keep coherent.
- **Discovery from a bare ID — moderate.** Can an agent reading one `@spec` in a source file place the intent and reach its doc with no external lookup?
- **ID legibility & length — moderate.** IDs are read, typed, and cited by humans in commits, reviews, and conversation. Short, pronounceable IDs cost less to live with.
- **Minimal stored facts — moderate.** From the *minimum-system* tenet: how many separate facts must each node carry to place itself in the tree?
- **Reorganization cost — minor.** What does moving a subtree across the tree cost? Minor because such moves are rare and self-limiting in cost (see Selection).

*Fit verdicts below — `strong / partial / weak` for criteria, `passes / eliminated` for gates — classify each option against the element. They are not judgments of the option overall; the weighing against importance happens in Selection.*

## Options in the Domain

### Option A — Loose namespaces

**Description.** Identity is decoupled from position. A segment owns a prefix that need not encode its place in the tree; the segment's design-doc frontmatter records where it sits. Because the prefix is independent of position, a segment can be re-parented anywhere in the tree **without changing a single ID or `@spec` annotation** — the most reorganization-resilient option, and one that keeps IDs short (`RUN-014`).

**Demonstration.** `RUN-014` names the runner segment; its place under `prompt-eval` is recorded in frontmatter. Moving the runner beneath a different parent leaves `RUN-014` and every annotation citing it untouched.

**Analysis.**
- *Stable IDs (gate):* **passes** — IDs are independent of position, so neither growth nor reorganization renames them.
- *Grep-navigability (major):* **partial** — a subtree grep works where the optional nesting convention was followed; otherwise gathering a subtree resolves through frontmatter or a registry.
- *Single-axis (major):* **weak** — position is stored separately from the ID, so locating intent draws on two structures.
- *Discovery from bare ID (moderate):* **weak** — an ID does not name its owning doc; resolution uses the frontmatter or a registry.
- *ID legibility & length (moderate):* **strong** — IDs stay short regardless of tree depth.
- *Minimal stored facts (moderate):* **partial** — each node carries a prefix and a position, with a resolver mapping prefixes to docs.
- *Reorganization cost (minor):* **strong** — a move is a frontmatter edit.

**Summary.** Most reorganization-resilient and shortest IDs, at the cost of carrying position in a second structure beside the IDs.

### Option B — Rigid / concatenated namespaces

**Description.** The EARS ID *is* the root-to-leaf path to the spec's owning segment. A spec in the load-testing leaf, under performance, under prompt-eval, is `PEVAL-PERF-LOAD-003`, and the directory layout mirrors the tree *structure* — parent/child nesting — while each node's directory and file names stay human-readable and need not equal the EARS prefix. Each node records its EARS prefix in `prefix:` frontmatter, which bridges the human-readable name to the namespace. Position is carried by the ID; a node's parent is derived by dropping the last path element.

**Demonstration.** From the bare annotation `// @spec PEVAL-PERF-LOAD-003` in a source file, a reader places the intent (load-testing → performance → prompt-eval) by the path and gathers the segment's specs and code by prefix-grep; one `prefix:`/`index.yaml` lookup resolves the ID to its owning design doc, whose human-readable filename the ID does not itself encode.

**Analysis.**
- *Stable IDs (gate):* **passes** — for growth; adding or refining specs within a segment renames nothing. A deliberate re-parent or rename rewrites the affected IDs and their annotations (see Selection).
- *Grep-navigability (major):* **strong** — `grep PEVAL-PERF` returns the whole performance subtree by construction, independent of any convention.
- *Single-axis (major):* **strong** — the path is the only navigation structure; no separate index exists.
- *Discovery from bare ID (moderate):* **strong** — prefix-grep gathers a segment's specs and code by construction; resolving an ID to its design doc is one `prefix:`/`index.yaml` lookup, since the ID does not encode the human-readable doc path.
- *ID legibility & length (moderate):* **weak** — IDs grow with depth (`PEVAL-PERF-LOAD-003`), making them longer to read and cite; they do sort into tree order.
- *Minimal stored facts (moderate):* **strong** — the path is the single source of truth; parent and role are derived.
- *Reorganization cost (minor):* **weak** — a cross-tree move rewrites the moved subtree's IDs and every `@spec` annotation citing them.

**Summary.** Satisfies both major criteria by construction, at the cost of longer IDs and expensive cross-tree moves.

### Option C — Flat namespaces with a registry

**Description.** IDs carry no hierarchy (`RUN-014`); a single registry file maps each prefix to its position in the tree. The tree has one authoritative, machine-readable definition rather than being implied across many docs — IDs stay short, and reorganizing is a one-file edit.

**Demonstration.** `RUN-014` is short to cite; the registry records that `RUN` sits under `PEVAL`, and re-parenting it is a single line in that file.

**Analysis.**
- *Stable IDs (gate):* **passes** — reorganization edits only the registry.
- *Grep-navigability (major):* **weak** — no prefix gathers a subtree; broader gathering resolves through the registry.
- *Single-axis (major):* **weak** — the registry is a navigation structure separate from the IDs.
- *Discovery from bare ID (moderate):* **weak** — an ID needs the registry to be placed.
- *ID legibility & length (moderate):* **strong** — IDs stay short regardless of depth.
- *Minimal stored facts (moderate):* **weak** — the registry is one additional artifact, centralizing all position information.
- *Reorganization cost (minor):* **strong** — a move is a one-file edit.

**Summary.** Authoritative single definition of the tree and short IDs, at the cost of an explicit second navigation structure that every lookup depends on.

## Selection

**Chosen: Option B — rigid / concatenated namespaces.**

The two major criteria decide it. Grep-navigability and single-axis navigation are both **strong** in Option B *by construction*; in Options A and C they are **partial** or **weak**, holding only through a separate structure — a nesting convention plus a registry or frontmatter. That separate structure is the second navigation axis the *verticalize intent* tenet exists to forbid, so A and C pay their reorganization savings in the currency the project values most.

Option B's **weak** verdicts fall on lower-importance criteria. ID legibility — `PEVAL-PERF-LOAD-003` is longer to read and cite than `RUN-014` — is bounded: intent trees are usually shallow (two or three levels), and concatenated IDs sort into tree order, which aids any listing or report. Reorganization cost lands on the lowest-importance criterion, and runs the right way against frequency: restructuring is frequent early, when specs are few and churn is cheap, and expensive late, when the domain has settled and restructuring is rare. The pathological case — large and still-restructuring — describes a project that never understood its own domain, which loose namespaces would not rescue.

Two mitigations retire most of the remaining cost:
1. Re-parent and rename are a single **atomic, tooled lifecycle operation** (owned by arrow-maintenance) that updates spec files, docs, and `@spec` annotations together.
2. Cross-cutting concerns attach at the node that dominates all their dependents (the placement rule), rather than being mis-placed in one branch — removing the most common reason to re-parent at all.

**Implications.** This is an HLD-level decision: it changes the EARS ID format the HLD defines (Approach: Linkage-based Intent Tracking) and the shape of the arrow itself, then cascades into the affected segments.
- Forecloses casual reorganization: moving a subtree becomes a deliberate, tooled event rather than a frontmatter edit.
- **Cascade to `linked-intent-dev`:** EARS authoring and `@spec` placement adopt the path-structured ID.
- **Cascade to `arrow-maintenance`:** it owns the atomic rename/re-parent operation across docs *and* code.
- Obligates directory layout to mirror the tree *structure* (parent/child nesting); node directory and file names stay human-readable, and each node's `prefix:` frontmatter carries the EARS prefix that bridges the name to the namespace.
- Restates LID's stability rule precisely: **spec IDs are stable except under a deliberate, tooled re-parent or rename.**
