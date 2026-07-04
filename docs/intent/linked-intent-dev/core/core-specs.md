# linked-intent-dev workflow specs

**LLD**: docs/intent/linked-intent-dev/core/core-design.md
**Implementing artifacts**:
- plugins/linked-intent-dev/skills/linked-intent-dev/SKILL.md

Status markers: `[x]` implemented · `[ ]` active gap · `[D]` deferred

The `linked-intent-dev` workflow skill is pure prose — its `SKILL.md` is the artifact, and per the LID-on-LID linkage inversion this file carries the artifact pointer. These specs have no automated eval suite (the skill is guidance the agent consults, not a deterministic harness run); `[x]` marks behavior the `SKILL.md` embodies.

---

## Triggering

- `[x]` **LID-CORE-001**: When a prompt proposes a change to project code or specifications, the system SHALL consult the linked-intent-dev workflow. The skill errs toward over-triggering, since an over-triggered consult is cheap and an under-triggered one lets drift accumulate.
- `[x]` **LID-CORE-002**: While in Scoped mode, when every path a prompt touches is outside the declared `## LID Scope`, the system SHALL NOT trigger the workflow; when any touched path is in scope, it SHALL trigger.
- `[x]` **LID-CORE-003**: While in Scoped mode, when a prompt references no specific paths, the system SHALL default to triggering and SHALL confirm scope applicability with the user when the situation is ambiguous.
- `[x]` **LID-CORE-004**: While in Scoped mode, when the `## LID Scope` section is missing or empty, the system SHALL treat all prompts as in-scope and surface a one-line warning suggesting `/update-lid` to declare scope.

## Phase Governance

- `[x]` **LID-CORE-005**: When a workflow phase completes, the system SHALL present its output to the user and SHALL proceed to the next phase only on explicit approval. Each stop is mandatory, not optional.
- `[x]` **LID-CORE-006**: Before starting or resuming implementation, the system SHALL run a coherence pre-flight verifying that the HLD, LLD, EARS specs, and tests are mutually coherent for the segment about to be touched, and when drift is detected it SHALL fix the docs before implementing.
- `[x]` **LID-CORE-007**: When drafting or revising any HLD, LLD, or EARS spec, the system SHALL write it to read as if authored fresh from current intent alone — excluding narration of how the intent changed, meaning that resolves only with conversation context, and rebuttals to questions only a past discussion raised.

## Phase 1 — HLD Check

- `[x]` **LID-CORE-008**: When invoked on a project with no LID directives and no LID-shaped artifacts, the system SHALL apply the `update-lid` bootstrap branch as a sub-step before drafting the HLD.
- `[x]` **LID-CORE-009**: When a change alters the project's architecture, the system SHALL update the HLD before downstream work.
- `[x]` **LID-CORE-010**: For a consequential architectural change (a new approach, a significant trade-off, a new mode) or a fresh-project HLD draft, the system SHALL sketch 2–3 competing options naming downstream consequences and present them for user selection before committing to a full HLD draft.
- `[x]` **LID-CORE-011**: When a decision would stay non-obvious to a cold reader of the landed result — one they would question or try to reverse without the full tradeoffs — the system SHALL record it as a decision doc in the owning node's `decisions/` directory.
- `[x]` **LID-CORE-045**: When a cold reader of a landed decision would merely wonder "why this?" and a single line settles it, the system SHALL record the decision as a row in the owning LLD's Decisions & Alternatives table.
- `[x]` **LID-CORE-046**: When a landed choice reads as obvious or native, the system SHALL record neither a decision doc nor a table row — judging from the landed state, not from how contested the decision was while being made.
- `[x]` **LID-CORE-012**: When drafting or revising the HLD, the system SHALL elicit tenets — surfacing the few decisions that could reasonably go more than one acceptable way and recording each as a one-line tie-breaker under `## Tenets` — and SHALL drop a candidate whose opposite would be absurd rather than a choice a different project could reasonably make.
- `[x]` **LID-CORE-039**: When eliciting tenets, the system SHALL route a candidate phrased as a triggered action (*when X, do Y* with a definite outcome) to EARS rather than recording it as a tenet, even when its opposite is defensible.
- `[x]` **LID-CORE-041**: When a tenet candidate carries operational elaboration (how to apply it, steps to run), the system SHALL record the tenet as a one-line lean and route the elaboration into workflow guidance.

## Phase 2 — LLD Check or Draft

- `[x]` **LID-CORE-013**: When no leaf LLD exists for the intent component being changed, the system SHALL draft one before downstream work.
- `[x]` **LID-CORE-014**: When more than one existing LLD is semantically relevant to a change, the system SHALL surface the candidate leaf LLDs with their scopes and ask the user which applies rather than silently selecting one.
- `[x]` **LID-CORE-015**: When a node appears to hold more than one intent, the system SHALL choose its shape by the kind of multiplicity rather than by document size.
- `[x]` **LID-CORE-042**: When the parts of a node share parent intent that a parent doc should hold, the system SHALL promote the node to a sub-HLD — HLD-shaped, owning no EARS — over child leaves.
- `[x]` **LID-CORE-043**: When the parts of a node are distinct intents with no shared parent, the system SHALL keep them as sibling leaves, each owning its own prefix.
- `[x]` **LID-CORE-044**: When the parts of a node are categories or requirement types of a single intent, the system SHALL fold them into within-leaf type/area facets of one leaf rather than child nodes.
- `[x]` **LID-CORE-040**: When a concern spans multiple components and carries design decisions of its own, the system SHALL model it as its own design node, referenced by dependent nodes from their own design docs, rather than spread as labels across nodes or catalogued in a side structure.
- `[x]` **LID-CORE-016**: After drafting or substantially revising an LLD, the system SHALL run an LLD-level edge-case probe targeting that LLD's own internal gaps and present the gap list for the user to triage.

## Phase 3 — EARS Spec Draft or Update

- `[x]` **LID-CORE-017**: When an LLD changes, the system SHALL produce the corresponding EARS update — new, revised, or deleted specs.
- `[x]` **LID-CORE-018**: On revision the system SHALL mutate spec text rather than spec IDs unless scope genuinely changes, SHALL NOT reuse a deleted spec ID, and SHALL delete unwanted specs rather than marking them obsolete.
- `[x]` **LID-CORE-019**: After drafting or revising specs, the system SHALL run post-draft consistency verification (coverage, contradiction, implicit scoping, context-free reading) and present a brief consistency report.

## Phase 4 — Intent-Narrowing Edge Audit

- `[x]` **LID-CORE-020**: After specs are drafted, the system SHALL run an intent-narrowing edge audit across the LLD and specs together — cross-spec and cross-segment ownership, composition ambiguity, namespace ambiguity, sequencing ambiguity, and places the user's latent intent is narrower than the specs literally allow — and SHALL resolve these with the user before tests are written.

## Phase 5 — Tests First

- `[x]` **LID-CORE-021**: The system SHALL write tests carrying `@spec` annotations before the code that satisfies them, and SHALL NOT proceed to code until the tests exist and fail in the expected way.

## Phase 6 — Code and Coherence Verification

- `[x]` **LID-CORE-022**: When implementing, the system SHALL place `@spec` annotations at the entry point of the behavior's implementation graph in each subsystem the behavior spans, not on every helper.
- `[x]` **LID-CORE-023**: On completing implementation, the system SHALL run the structural coherence checks (all tests pass; every `@spec` resolves to an existing spec ID; every behavioral spec the LLD cites has a citing test; no spec file references a deleted ID) and SHALL soft-block completion — surfacing failures clearly without hard-blocking — until they pass.
- `[x]` **LID-CORE-024**: When the project declares a coherence-check script under `## LID Tooling`, the system SHALL delegate the structural checks to that script; otherwise it SHALL perform them in-prompt.
- `[x]` **LID-CORE-025**: On completing implementation, the system SHALL run the semantic coherence checks (specs consistent with the LLD; LLD consistent with the HLD) and surface the findings for user review without blocking.

## Cascade Discipline

- `[x]` **LID-CORE-026**: When a change is made at one arrow level, the system SHALL review and update the levels downstream of it in the same session.
- `[x]` **LID-CORE-027**: While cascading within a single arrow segment — one leaf LLD and the specs, tests, and code citing its EARS IDs — the system SHALL update downstream levels without further confirmation.
- `[x]` **LID-CORE-028**: When a cascade's effect crosses a segment boundary into another leaf's territory, the system SHALL pause and ask the user before propagating into the adjacent segment.
- `[x]` **LID-CORE-029**: The system SHALL determine a spec's segment by its leaf-prefix path — specs sharing the leaf prefix are in one segment, and a divergence at any earlier path element marks a boundary — and SHALL ask the user to disambiguate when two unrelated leaves would collide on a path prefix.
- `[x]` **LID-CORE-030**: When a decision's substance sits in one segment but implementing it obligates a sibling segment, the system SHALL record the decision in the segment that owns its substance and note the sibling obligation as a cascade; only a decision whose substance genuinely spans siblings rises to their shared parent.
- `[x]` **LID-CORE-031**: When a change originates at the HLD, the system SHALL walk the affected leaf LLDs in turn, pausing at each segment to confirm the change lands before cascading into that segment's specs, tests, and code.
- `[x]` **LID-CORE-032**: When a cascade would touch files with uncommitted user changes, the system SHALL warn with a description of the intended changes and proceed only after confirmation.
- `[x]` **LID-CORE-033**: When the system notices an inconsistent arrow (mid-transition abort, overlapping scoped arrows, a partial prior cascade), it SHALL surface the inconsistency and SHALL NOT auto-repair it.
- `[x]` **LID-CORE-034**: When a cascade implies a split, merge, or rename of a segment, the system SHALL defer to the lifecycle-event mechanics in the `arrow-maintenance` LLD rather than re-specifying them.
- `[x]` **LID-CORE-035**: When a change is made inside an arrow segment and the arrow-maintenance overlay is present, the system SHALL update that segment's `index.yaml` entry (status transitions, `next`, `drift`, `audited_sha`) using the schema the arrow-maintenance LLD defines.

## Bug Fixes and Overrides

- `[x]` **LID-CORE-036**: When fixing a bug, the system SHALL walk the full arrow — locating where behavior diverged from intent and cascading from there — rather than short-circuiting to a code change.
- `[x]` **LID-CORE-037**: When the user overrides a phase requirement (skipping EARS, skipping tests, fixing code without walking the arrow), the system SHALL warn about the drift risk and honor the override.

## Brownfield LLD Content

- `[x]` **LID-CORE-038**: When authoring an LLD for a reverse-engineered component, the system SHALL use the standard LLD template and section structure and mark inferred decisions with `[inferred]` in the Rationale column, removing the marker as the user confirms or refutes the inference.
