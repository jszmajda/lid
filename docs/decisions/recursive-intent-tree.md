---
node: high-level-design
---

# Decision: Recursive design tree for the intent arrow

## Context

LID's arrow places one HLD above a flat set of LLDs — one LLD per intent component — with EARS specs below each. This holds for small and mid-sized projects and breaks for large ones in two ways. First, a single subsystem's intent can be too deep to capture in one LLD: the doc either sprawls past the point of comprehension or fragments into many sibling LLDs whose relationship is implied only by naming. Second, a team cannot own a *region* of intent — there is no artifact between "the whole project" (the HLD) and "one component" (an LLD) for a team to hold and evolve.

In practice, a large subsystem's design doc tends to grow HLD-shaped on its own — acquiring its own problem statement, approach, and key decisions while delegating the details to child docs. The structure chosen here either sanctions that growth or leaves projects to improvise it.

The choice is load-bearing and hard to reverse: it defines what design artifacts exist, how EARS IDs are shaped, how cascade flows, and what every Glossary term means. It must let depth grow without forcing small projects to carry any of that depth's machinery.

## Decision Elements

*(No binary gates apply: every option in contention preserves the arrow's phases and keeps depth-2 valid, so neither would discriminate — and an element that cannot drive selection earns no place here.)*

**Criteria** *(importance: major / moderate / minor)*

- **Captures depth of intent — major.** Can a large subsystem express intent at multiple levels of detail without sprawl or grouping-implied-only-by-naming?
- **Enables team ownership of a region — major.** Is there an artifact a team can own that is larger than one component and smaller than the whole project?
- **Minimum surface — major.** How many new concepts must a user learn? Surface growth is the load-bearing cost LID resists.
- **Navigability preserved — moderate.** Does the structure keep the arrow grep-walkable along a single axis?
- **Honest to how intent grows — moderate.** Does it match how projects actually arrive at their structure — incrementally, by differentiation — rather than demanding the full tree up front?
- **Mental-model simplicity — moderate.** *(latent)* How hard is the model to hold? "Two fixed types" is easy; recursion and roles-by-position ask more of the reader.

*Fit verdicts below — `strong / partial / weak` — classify each option against the criterion, not the option overall; the weighing happens in Selection.*

## Options in the Domain

### Option A — Fixed two-rung (status quo)

**Description.** One HLD; a flat set of LLDs, one per component; EARS below each. The simplest possible model, with nothing new for any user to learn — every existing LID project already works exactly this way. A large subsystem is handled either by one large LLD or by several sibling LLDs whose grouping is implied by shared name prefixes.

**Demonstration.** A `prompt-eval` subsystem with six components becomes either one ~1500-line LLD or six sibling files (`prompt-eval-fixtures.md`, `prompt-eval-runner.md`, …) related only by their names.

**Analysis.**
- *Captures depth (major):* **weak** — depth is faked by one sprawling doc or by naming-convention grouping with no real parent.
- *Team ownership (major):* **weak** — nothing exists between project and component for a team to own.
- *Minimum surface (major):* **strong** — nothing new to learn.
- *Navigability (moderate):* **partial** — flat prefixes grep fine, but a subsystem is not a first-class grepable unit.
- *Honest to growth (moderate):* **partial** — growth past one LLD has no sanctioned move except ad-hoc sibling splitting.
- *Mental-model simplicity (moderate):* **strong** — two types, no recursion.

**Summary.** Simplest model and zero new surface, at the cost of having no real answer for depth or team ownership.

### Option B — Recursive design tree (roles by position)

**Description.** The design layer is a tree of arbitrary depth. The HLD is the root; leaf design docs own EARS; intermediate design docs group their children and are HLD-shaped for their subtree (sub-HLDs). "HLD" and "LLD" become roles relative to a node's position rather than fixed types, and a node carries whatever sections it needs. Depth-2 is simply the shallow case; nesting is triggered only when a component outgrows one doc. A sub-HLD is earned by shared parent intent a parent design doc should capture — the test is whether such a doc *should* exist, not whether one already does; a merely categorical grouping with no shared intent is a *taxonomy label*, not a sub-HLD, and its members stay flat leaves.

**Demonstration.** The `prompt-eval` subsystem becomes a sub-HLD (its own Problem / Approach / Key Decisions) parenting six leaf LLDs that own EARS; a team owns the sub-HLD and its subtree, and `grep PEVAL` gathers the whole region.

**Analysis.**
- *Captures depth (major):* **strong** — intent nests to whatever depth the domain needs.
- *Team ownership (major):* **strong** — a sub-HLD plus its subtree is exactly the region a team owns.
- *Minimum surface (major):* **partial** — adds the concepts of nesting and roles-by-position, but reuses the existing HLD and LLD templates as the two node shapes rather than inventing new artifact types.
- *Navigability (moderate):* **strong** — with path-concatenated IDs (child decision), a subtree is grep-gatherable and the walk extends cleanly up the tree.
- *Honest to growth (moderate):* **strong** — a leaf *promotes* into a grouping node as its intent differentiates, matching incremental discovery.
- *Mental-model simplicity (moderate):* **weak** — recursion and roles-by-position are heavier to hold than two fixed types.

**Summary.** Answers both depth and team ownership directly and reuses existing templates, at the cost of a heavier mental model.

### Option C — One fixed middle tier (capped three-level)

**Description.** Add exactly one sanctioned middle tier — a "subsystem HLD" between the project HLD and component LLDs — and cap depth there: `HLD → subsystem-HLD → LLD → EARS`, no arbitrary recursion. A clean ownership unit without asking users to think recursively.

**Demonstration.** `prompt-eval` is a subsystem-HLD owned by a team, parenting six LLDs — but a component that itself needs internal depth (say the runner growing a worker/parent split worth its own sub-design) has nowhere to go.

**Analysis.**
- *Captures depth (major):* **partial** — handles one level of grouping; a subsystem that needs further internal depth is back to Option A's problem.
- *Team ownership (major):* **strong** — the subsystem tier is a clean ownership unit.
- *Minimum surface (major):* **partial** — adds one named tier, a third fixed type to learn.
- *Navigability (moderate):* **partial** — as navigable as B at the supported depth, but the cap reappears as a wall.
- *Honest to growth (moderate):* **weak** — domains do not cap their depth at three to suit the tooling; a subsystem that differentiates further has no move.
- *Mental-model simplicity (moderate):* **partial** — three fixed types is simpler than recursion but still a new type to learn.

**Summary.** A clean ownership tier without recursion's mental load, but the depth cap is an arbitrary wall that reintroduces the original problem one level down.

## Selection

**Chosen: Option B — recursive design tree.**

The two major criteria that motivated the change — capturing depth and enabling team ownership — are **strong** only in B. Option A is **weak** on both; it has no real answer. Option C is **strong** on ownership but only **partial** on depth: its cap is an arbitrary wall that reproduces A's sprawl one level down, which is why it is also **weak** on *honest to how intent grows* — domains do not agree to stop differentiating at three levels because the tooling does.

B's costs fall on the *minimum-surface* tenet (**partial**) and mental-model simplicity (**weak**), both real. This decision turns on a capability need — depth and team ownership — with minimum-surface as the tenet it is taken *against*, and accepts the partial cost to that tenet. Two design choices keep the surface from actually growing much: the two node shapes are the **existing HLD and LLD templates** — nesting adds no new artifact type, only permission for an HLD-shaped doc to sit below the root — and **depth-2 remains the default**, so recursion is a triggered exception that small and flat projects never see or pay for. The mental-model cost is the genuine price: users must hold a tree with positional roles rather than two fixed types. That cost is accepted because the alternative is having no sanctioned answer for the projects LID most wants to serve as they scale, and because the recursive model collapses to the familiar two-rung picture at shallow depth — a reader meets the complexity only when their own project has already grown into it.

**Consequences and child decisions.**
- **Namespace structure** (`docs/decisions/namespace-structure.md`) — how IDs encode tree position; resolved as path concatenation.
- **Flexible node shapes** — a node carries the sections it needs; the HLD and LLD templates are starting points, not rigid types.
- **Placement rule + substance-vs-cascade** — a decision attaches at the lowest node dominating its blast radius; substance that genuinely spans siblings rises to their shared parent.
