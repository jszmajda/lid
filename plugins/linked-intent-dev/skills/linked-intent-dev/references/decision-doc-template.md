# Decision Doc Template Reference

A **decision doc** records a single design decision at high enough resolution that a future reader can *re-run the judgment* if circumstances change — not just learn what was chosen. It is the expanded form of a Decisions & Alternatives table row, reserved for the few decisions that earn it. Decision docs are **rare**.

## When to write one (the earns-its-place heuristic)

> **Apply the test from the landed state, looking forward — not from the deliberation, looking back.** The question is *not* "was this hard to decide?" Plenty of decisions are contested while the work is in flight and then read as **obvious, even native, once they land** — the structure ends up self-evidently the way it had to be. The question is: **once this lands, would a cold reader of the result find the choice non-obvious — would they question it, or be tempted to reverse it, not knowing why it went this way?**

That yields three outcomes, not two:

- **Record nothing.** The choice is obvious or native once it lands; the structure documents itself. Writing down a settled-and-obvious decision is the same residue the *docs carry current intent* tenet strips — a fresh author of the landed system would not explain why the natural shape is natural.
- **A Decisions & Alternatives row.** A cold reader would plausibly wonder "why this?", and one line of rationale settles it (one option clearly dominates, or an inherited constraint eliminated the rest).
- **A full decision doc.** The choice stays genuinely *live*: a cold reader would re-litigate it without the full tradeoffs laid out — competing options weighed against criteria.

Competitive options scored against weighted criteria are a *symptom* that a doc may be warranted, not the test itself — the test is the reader's forward-looking need. A directory full of decision docs is a smell.

## Where it lives

A decision doc lives in the `decisions/` directory of the node that owns it:

- **Segment-level decision** → `docs/intent/<segment>/decisions/<name>.md`.
- **Project-level (HLD) decision** → `docs/decisions/<name>.md`, parallel to `docs/intent/`.

Name it for the decision (`namespace-structure.md`, not `001.md`). The decision doc is **owned by the design node whose decision it is** — it shares that node's position in the tree, owns no EARS specs, and carries no spec IDs. The owning design doc links to it from its Decisions & Alternatives table.

A decision belongs where its **substance** lives, even when implementing it cascades an obligation into a sibling segment — record it there and note the sibling obligation as a cascade, not co-ownership. Only a decision whose substance genuinely spans siblings rises to their shared parent (`docs/decisions/`).

## Lifecycle

While the decision is open it is a **plan-space working artifact** — options live, discussion present. When the decision is made, its durable reasoning lands here and the transient deliberation is shed. Like every LID doc, it is **written to be read cold**: present tense, no narration of how the discussion unfolded, no "we decided X after Y raised Z." "Options in the domain" means *the options that exist in this problem space*, not a chronology of what was proposed when.

## Frontmatter

```yaml
---
node: {owning-segment}        # the node whose decision this is — a segment, or high-level-design for a project-level decision
---
```

A decision doc carries no `status` field. Its presence in `docs/` *is* its acceptance — deliberation happens in plan-space, so a doc only lands here once the decision is made. A superseded decision is deleted and replaced, not flagged (mutation, not accumulation; git preserves the history).

When a decision builds on or relates to another — when it would be unintelligible without that premise — say so in **Context**: open with a one-line pointer to the decision it depends on. Keep this as freeform prose, not a fixed field; what a decision relates to varies too much to bind to a schema.

## Structure

```markdown
# Decision: {title}

## Context

Why the decision is needed, the background, and what's at stake if it's wrong.
A cold reader should understand why this decision exists from the domain itself —
not from when or by whom it was raised. No temporal framing ("forced now").

## Decision Elements

The machinery a future reader needs to re-run the judgment if circumstances change. Every
element must be able to **drive selection** — an element that all options pass, or score
equally on, is noise; cut it. A foundational invariant every option respects is background,
not a decision element.

Elements come in two forms:

- **Gates** — *binary* criteria (pass/fail). An option that fails a gate is eliminated, not
  merely scored down. A gate may be **doc-local** (a boundary this decision sets) or
  **inherited** (a standing constraint that applies at this node). Include a gate only if it
  eliminates an option actually in contention.
- **Weighted criteria** — graded considerations. Mark each with its importance:
  **major / moderate / minor** (a project may substitute its own ordered vocabulary as long
  as the ordering is unambiguous). Where a criterion's importance derives from a **tenet**,
  name the tenet — this is how decisions are made to *turn on* tenets. Tenets are engaged
  through the criteria (and named again in Selection); they get no section of their own. A
  decision that cites no tenet anywhere is a signal: either it is purely local, or the
  project is missing a tenet.

  Before finalizing the criteria, **probe for latent criteria the discussion has not
  surfaced** — the same latent-intent discovery the core LID workflow applies to
  specs. Ask what a thoughtful critic would weigh that no one has named yet,
  especially criteria that cut *against* the emerging recommendation. Criteria you
  surface and then eliminate need not be written down; criteria that survive and
  could move the decision must be.

## Options in the Domain

One `###` subhead per option — not a comparison table. Tables read cleanly with two
or three shallow criteria and collapse as criteria deepen; per-option prose keeps each
option's context attached to it. Each option carries:

- **Description** — what the option *is*, in enough detail that a reader with no access
  to the originating discussion can reconstruct it. Give each option its **strongest
  honest representation** — describe it as its advocate would. An option a future
  maintainer cannot understand from the text alone is under-described; this is the
  most common failure of this section.
- **Demonstration** *(optional)* — a concrete example (an ID, a snippet, a path)
  showing the option in action.
- **Analysis** — a bullet per element. Lead each bullet with a **verdict**, then the
  factual basis:
  - Constraints (gates): **passes** or **eliminated**.
  - Criteria: **strong / partial / weak** fit against the criterion.

  The verdict classifies the option's fit to *that element* — it is not a judgment of
  the option overall (every option is strong on some elements and weak on others).
  Keep the basis clause clinical: state what is true, don't editorialize ("fails the
  intent," "exactly what we want"). The three things stay separate — **importance**
  (major/moderate/minor) lives on the criterion, **fit** (strong/partial/weak) lives on
  the option↔criterion pair, and the **weighing** of fit against importance happens
  only in Selection.
- **Summary** *(optional)* — one neutral line naming the option's essential trade.

Hold a **high bar for "obvious."** Omit only what a cold reader would independently
know — not what the authoring conversation happened to surface.

## Selection

The option chosen, why it wins against the elements (especially the high-importance
criteria and any gate that shaped the option set), and the implications of committing: what
it forecloses, and what it obligates downstream. Name the tenet(s) the decision turns on —
or the tenet it is taken *against*, when a capability need overrides one — closing the
tenet-coverage loop opened in Decision Elements.

Judgment lives **here and only here**. It may be capricious if it must, but it is
strongly preferred to arise from the analysis above rather than override it. If the
recommendation contradicts the criteria, say so plainly — don't quietly reshape the
analysis to fit.
```