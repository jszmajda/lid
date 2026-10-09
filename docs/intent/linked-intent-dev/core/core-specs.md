# linked-intent-dev workflow specs

**LLD**: docs/intent/linked-intent-dev/core/core-design.md
**Implementing artifacts**:
- plugins/linked-intent-dev/skills/linked-intent-dev/SKILL.md
- plugins/linked-intent-dev/skills/linked-intent-dev/references/capability-flags.md

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
- `[x]` **LID-CORE-047**: During specification work (Phases 1–3), the system SHALL match its specification instrument to the user's current grain of interaction — elicitation when the user engages one concept at a time, drafting-then-review when the user reviews documents whole — including when the grain shifts mid-artifact.
- `[x]` **LID-CORE-048**: When eliciting, the system SHALL raise one aspect per exchange, presenting real tradeoffs with concrete examples and confirming understanding before recording the user's choice.
- `[x]` **LID-CORE-049**: When inspection of a phase is delegated to an inspector, the system SHALL present the inspector's summarized findings at that phase's stop for the human to rule on, SHALL NOT treat an inspector's pass as proof of alignment, and on a clean pass SHALL name where the inspector looked hardest and offer the human a spot-check of that raw output.
- `[x]` **LID-CORE-050**: When a spec or draft admits more than one reading, the system SHALL surface the fork to the human for resolution, regardless of which instruments are in play and at whatever phase the fork is discovered — before further tests or code are written against either reading; a fork discovered after tests exist is surfaced before proceeding, with the affected tests named.
- `[x]` **LID-CORE-051**: When inspection is delegated, the system SHALL preserve every phase-boundary stop, changing only what the human rules on at the stop — the inspector's findings rather than the raw phase output.
- `[x]` **LID-CORE-057**: When inspection is relocated to an out-of-band review, the system SHALL confirm with the user which artifacts the review will cover and SHALL NOT lighten the in-session ruling for phases whose artifacts the review will not read.
- `[ ]` **LID-CORE-058**: When a phase's work touches an area the capability-flag list flags for the executing model's configuration, the system SHALL name that area and what to check at the phase's stop, and SHALL route that judgment to the human even when the human has authorized another inspector at that stop.
- `[ ]` **LID-CORE-059**: When determining whether a capability flag applies, the system SHALL place the executing model by its own name and reasoning effort, and SHALL treat the flag as applying when the flag list has no row for that configuration or when it cannot tell its configuration.
- `[ ]` **LID-CORE-060**: When raising a capability flag, the system SHALL state the flagged area and the request for review once, plainly, without qualifying the rest of its work.
- `[x]` **LID-CORE-061**: When phase work meets a judgment the human should make or check — one of the recurring kinds in the core design's list, or any other call recognizably the human's — the system SHALL bring it to the human at that phase's stop, or immediately when the work cannot proceed without it, unless the user has let that kind of judgment go for the current work.
- `[x]` **LID-CORE-062**: While inspection is delegated, consolidated, or relocated, the system SHALL NOT settle a judgment covered by LID-CORE-061 on the human's behalf, and SHALL NOT leave it only inside a delegated inspector's findings.
- `[x]` **LID-CORE-063**: When the user lets a kind of judgment go for a stream of work, the system SHALL apply that release only to that work and SHALL NOT carry it into other work.
- `[x]` **LID-CORE-064**: The system SHALL NOT treat a general wish for fewer interruptions as letting go spec forks or hard-to-undo changes; it SHALL treat either as let go only when the user names it.
- `[x]` **LID-CORE-065**: When the conversation shows a consistent pattern in which kinds of judgment the user wants brought to them or waves through, the system SHALL name the pattern and ask whether to treat it as the user's preference, rather than applying it unasked.
- `[ ]` **LID-CORE-066**: When a capability flag applies to a kind of judgment the user has let go, the system SHALL still bring that judgment to the human and say why, unless the user, knowing the flag, has said to let it go.
- `[x]` **LID-CORE-052**: When dispatching phase work to a subagent, the system SHALL embed in the dispatch prompt the obligations that phase carries — for implementation work, the EARS IDs in scope, the tests-first gate, and the `@spec` annotation requirement — and, for every dispatch regardless of phase, the obligation to surface rather than resolve ambiguity: a spec admitting more than one reading returns to the dispatcher as a question, never as a silently chosen reading.

## Phase 1 — HLD Check

- `[x]` **LID-CORE-008**: When invoked on a project with no LID directives and no LID-shaped artifacts, the system SHALL apply the `update-lid` bootstrap branch as a sub-step before drafting the HLD.
- `[x]` **LID-CORE-009**: When a change alters the project's architecture, the system SHALL update the HLD before downstream work.
- `[x]` **LID-CORE-010**: For a consequential architectural change (a new approach, a significant trade-off, a new mode) or a fresh-project HLD draft, the system SHALL sketch 2–3 competing options naming downstream consequences and present them for user selection before committing to a full HLD draft.
- `[x]` **LID-CORE-011**: When the user settles a choice among options the agent sketched, and the landed choice would stay live for a cold reader — credible options traded against more than one criterion, with other design nodes sized around the result — the system SHALL offer once to record it as a decision doc, with a Decisions & Alternatives row as the alternative.
- `[x]` **LID-CORE-045**: When a cold reader of a landed decision would merely wonder "why this?" and a single line settles it, the system SHALL record the decision as a row in the owning LLD's Decisions & Alternatives table.
- `[x]` **LID-CORE-046**: When a landed choice reads as obvious or native, the system SHALL record neither a decision doc nor a table row — judging from the landed state, not from how contested the decision was while being made.
- `[x]` **LID-CORE-071**: The system SHALL write a decision doc only when the user has accepted the offer to record the choice as one.
- `[x]` **LID-CORE-072**: The system SHALL NOT offer a decision doc for a choice that one option dominates, that an inherited constraint settles, or that affects only its own design node, however long the debate about it ran.
- `[x]` **LID-CORE-073**: When Phase 2 meets an LLD-level choice with real tradeoffs that no document settles, the system SHALL sketch 2–3 options naming their downstream consequences and present them for user selection before drafting the LLD around the choice.
- `[x]` **LID-CORE-074**: When the user accepts a decision doc, the system SHALL draft it in the owning node's `decisions/` directory following the decision-doc template and link it from the owning design doc's Decisions & Alternatives table.
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
- `[x]` **LID-CORE-067**: When drafting or revising a design node, the system SHALL place each decision at the lowest design node whose subtree contains everything the decision affects.
- `[x]` **LID-CORE-068**: When drafting or revising a design node, the system SHALL define each term at the lowest design node that dominates every node that uses the term.
- `[x]` **LID-CORE-069**: When a new concept could be named by a plain descriptive phrase, the system SHALL use the phrase rather than coin a term, unless several design nodes need the same exact concept.
- `[x]` **LID-CORE-070**: When placing a decision or term correctly would move it across a segment boundary, the system SHALL raise the move with the user rather than make it silently.

## Phase 3 — EARS Spec Draft or Update

- `[x]` **LID-CORE-017**: When an LLD changes, the system SHALL produce the corresponding EARS update — new, revised, or deleted specs.
- `[x]` **LID-CORE-018**: On revision the system SHALL mutate spec text rather than spec IDs unless scope genuinely changes, SHALL NOT reuse a deleted spec ID, and SHALL delete unwanted specs rather than marking them obsolete.
- `[x]` **LID-CORE-019**: After drafting or revising specs, the system SHALL run post-draft consistency verification (coverage, contradiction, implicit scoping, context-free reading) and present a brief consistency report.
- `[x]` **LID-CORE-056**: When drafting or updating EARS specs, the system SHALL express EARS-labeled requirement content only in the owning node's `{node}-specs.md`; a design doc cites spec IDs without defining or extending their content.

## Phase 4 — Intent-Narrowing Edge Audit

- `[x]` **LID-CORE-020**: After specs are drafted, the system SHALL run an intent-narrowing edge audit across the LLD and specs together — cross-spec and cross-segment ownership, composition ambiguity, namespace ambiguity, sequencing ambiguity, and places the user's latent intent is narrower than the specs literally allow — and SHALL resolve these with the user before tests are written.
- `[x]` **LID-CORE-053**: When Phase 4 runs, for each new or changed EARS spec the system SHALL probe for divergent plausible readings — what a blind implementer could take the line to require — and surface only the genuine forks to the user for resolution before tests are written.
- `[x]` **LID-CORE-054**: When probing for divergent readings, the system SHALL use the most context-independent reader available — in-context generation as the floor, blind subagents given only the spec text when available, and an equivalently capable model from a different provider where the platform allows.
- `[x]` **LID-CORE-055**: When a fork is resolved, the system SHALL land the resolution as a narrowing edit to the forked spec or as a new atomic spec line, and SHALL NOT bundle multiple resolved behaviors into one compound spec.

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
