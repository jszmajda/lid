<!-- GENERATED FILE — do not edit here.
     Assembled from the linked-intent-dev plugin (version 1.3.0) at release.
     Changes belong upstream (in the plugin) or in this project's instruction file.
     Re-sync via /update-lid where available; see docs/setup.md otherwise. -->

# LID Workflow (vendored)

The full linked-intent-development workflow, vendored for agent harnesses without a plugin system. Read this before making code changes in this project. The reference material this workflow cites (`references/...` paths) is appended as sections at the end of this document — the content is here, not in a references directory.

---

# Linked-Intent Development

This skill guides a structured linked-intent development workflow. LID's goal is to narrow the agent's output distribution to the user's latent intent — specs, tests, and linkage together make the arrow of intent walkable, and the workflow's stops are where the agent's interpretation meets the user's intent for reconciliation.

## Three rules govern every phase

**Stop and iterate at every phase boundary.** After completing each phase below, present it — the phase output in full, or an authorized inspector's summarized findings (see *Specification and inspection instruments* below) — incorporate numbered feedback, and proceed only on explicit approval. Each stop is mandatory; the stops are the mechanism realizing the HLD tenet *Every phase is inspected*. Skipping stops is the single most common way this workflow degrades into a rush. (Carveout: command-mode skills that execute a single directed pass, like `/arrow-maintenance`'s audit-and-update, are not phase-structured in this sense and do not pause mid-pass. This workflow is generative; phases here produce intent, so every boundary gets a stop.)

**Run a coherence pre-flight before starting or resuming implementation.** When picking up work — new session, returning to a change, cascading from an upstream change — verify that the HLD, LLDs, EARS specs, and tests are mutually coherent for the segment about to be touched:

- Do the EARS specs trace to the current LLD?
- Do the tests trace to the current EARS specs?
- Does the LLD still reflect the HLD's architecture?

If drift is detected, fix the docs first, then implement. A resumption check prevents one session's drift from being compounded into the next session's change.

**Write docs as their fresh author.** Every HLD, LLD, and EARS spec produced by these phases must read as if authored fresh today, by someone who knew only the current intent and nothing of this conversation. As you draft or revise a doc, run the test on each line — would that fresh author put it on the page? Three residues fail it: narration of how the intent changed; meaning that only resolves for someone who was in this conversation; and answers or rebuttals that exist only because we discussed the question here. The keep-side is load-bearing too — rationale, considered alternatives, and constraints a fresh author would independently write stay; they are present intent, not residue. Record rejected alternatives and why in the LLD's Decisions & Alternatives table, not as asides in body prose. This is the *docs carry current intent* tenet. Write in the project's own domain language — name components, segments, and specs with the words the user and the codebase already use, not generic or LID-imposed labels. This is the *Speak the project's language* tenet.

## Specification and inspection instruments

Two kinds of intent work run through the phases, verified differently: **specifying** (Phases 1–3: turning latent intent into written spec — checked against what the user actually meant) and **inspecting the cascade** (the stops and the Phase 4–6 checks — checking downstream rungs against the spec). Each admits more than one instrument; offer the choice conversationally. There is no configuration for it (see `docs/decisions/inspection-instrument-selection.md`).

**Specifying — follow the user's grain.** Drafting-then-review works one document at a time: draft the artifact whole, the user reviews it whole. Elicitation works one concept at a time: raise a single aspect, the user responds to just that, and the document accretes from the answers. Match the user's current grain — a user who answers one aspect of a draft and ignores the rest is asking for elicitation; whole-document feedback means draft-review is working. Switching mid-artifact is normal. When eliciting: one aspect per exchange, real tradeoffs with concrete examples, confirm understanding before recording a choice, and keep it short — an easy-to-click menu that hides the real decision is worse than no menu.

**Inspecting — the user chooses the inspector.** Default: the user reads each phase's output at its stop. On the user's authorization: a **zero-context reader** (given only the arrow artifacts, never the conversation, so it cannot inherit the builder's blind spots — the coach's cold-read pass and the experimental blind differential are this family) or a **delegated inspector** (a subagent reviewing the phase output in the user's place). Inspection may also be **relocated out-of-band**: the user lands the change on a branch and leans on the project's existing review process (a pull-request review); the stops still run in-session, and a review finding that reveals an *intent* gap walks the arrow like any bug.

Three rules hold whatever the instruments:

- A delegated inspector's findings are never applied silently — present them summarized and focused at the stop; a pass means "no counterexample found," not proof.
- A spec or draft that admits more than one reading always goes back to the user — only they hold the latent intent — before tests are written against either reading.
- Delegation changes *who inspects at a stop*, never *how many stops there are*. The user can still override anything, per *the user is always right — with warning*.

## Delegation discipline

Discipline does not travel by ambient context. A subagent dispatched to perform phase work receives only its prompt — not this skill, not the instruction file, not the conversation. Embed the phase's obligations in the dispatch prompt itself.

For implementation work (Phases 5–6): the EARS spec ID(s) in scope, the tests-first gate ("write failing tests first; do not proceed to code until they fail as expected"), and the `@spec` annotation requirement. For a Phase 2 probe: what the probe targets. For a delegated inspector: the spec(s) it inspects against and the requirement to return summarized, focused findings. When a phase gains a new obligation, dispatches of that phase's work carry it.

## Mode-aware triggering

Every LID project declares its mode in its instruction file (the project's `AGENTS.md`, or `CLAUDE.md` under Claude Code) under the `## LID` block's `- Mode:` bullet. Defaults to Full if the block or bullet is missing or malformed (surface a one-line warning).

- **Full LID**: the skill triggers broadly — any prompt that could result in a code change is in scope.
- **Scoped LID**: additionally checks whether the files or subsystems the prompt touches fall within the declared scope. Scope is declared in the instruction file under a `## LID Scope` section (see `docs/intent/linked-intent-dev/core/core-design.md § Scope declaration format`) with include/exclude glob patterns. If every file the prompt touches is outside scope (in the exclude list, or not in the include list), the skill does not trigger. If any touched path is in scope, the skill triggers. For prompts that reference no specific paths, default to triggering and ask the user to confirm when ambiguous. When the `## LID Scope` section is missing or empty in a Scoped-mode project (misconfiguration), fall back to treating all prompts as in-scope and surface a warning suggesting `/update-lid` to declare scope.

## The six phases

### Phase 1 — HLD check (with bootstrap when needed)

**First, check whether the project is LID-configured.** If the instruction file has no LID directives AND no LID-shaped artifacts exist (no `docs/intent/` content, no `docs/high-level-design.md`, no `docs/arrows/index.yaml`), this is a fresh project — the user invoked `/linked-intent-dev` with a description of what they want to build. Apply the `update-lid` skill's bootstrap branch as a sub-step: create `docs/intent/`, create or append-to the instruction file (`AGENTS.md` canonical, with a `CLAUDE.md` alias — see the `update-lid` skill) with LID directives, add the `## LID` block (`- Mode:` default Full unless the user indicates Scoped, `- Version:` set to the installed `linked-intent-dev` version). Read the `update-lid` skill's SKILL.md if you need details on the bootstrap behavior; the bootstrap is the same skill called inline, not a separate workflow.

Once configured, proceed with the HLD check: does a top-level HLD exist at `docs/high-level-design.md`? Does it cover the domain of the change? If the change alters the project's architecture, update the HLD first. If no HLD exists (fresh project), draft one from the user's description.

For consequential architectural changes (a new approach, a significant trade-off, a new mode) — and on a fresh-project HLD draft — before committing to a full HLD **sketch 2–3 competing options** (~200 words each, naming downstream consequences) and present them for user selection. Surfacing decisions as *choices among alternatives* — rather than as the agent's best guess — is the primary edge-detection mechanism at the HLD level.

When drafting or revising the HLD, **elicit tenets**: surface the few decisions that could reasonably go more than one acceptable way, ask the user which way to lean, and record each as a one-line tie-breaker under `## Tenets`. Apply the defensible-opposite test before proposing one — if the reverse of the tenet is absurd rather than a choice a different project could reasonably make, it is a platitude and resolves nothing; drop it. Apply a second test too: a tenet leans a class of decisions no spec anticipates — if the candidate reads as a triggered action (*when X, do Y* with a definite outcome), it is a spec, not a tenet; route it to EARS rather than the tenet list, even when its opposite is defensible. Apply a third rule to the survivors — form: a tenet stays a one-line lean. When a genuine tenet carries operational elaboration (how to apply it, steps to run), record only the lean under `## Tenets` and route the elaboration into workflow guidance — a user project's instruction file, or the governing skill when editing LID itself. Apply the three in order: platitude test, spec test, form rule. A tenet is edge detection for choices no spec will anticipate. Surface the load-bearing ones you can see and invite more; do not interrogate the user for an exhaustive set.

Whatever you draft, verify the HLD reads **context-free**: rationale present, alternatives named, no reliance on conversation context that won't travel to the next session.

See `references/hld-template.md` for standard HLD sections.

**STOP for user review.**

### Phase 2 — LLD check or draft

Does a leaf LLD exist for the intent component being changed?

If not, draft one using the template at `references/lld-templates.md`.

The design layer is a recursive tree, and "HLD" and "LLD" are **roles by position**: the root is the HLD, the leaves are the LLDs that own EARS, and a component with enough internal depth to outgrow one doc is promoted to a **sub-HLD** — HLD-shaped for its subtree, owning no EARS of its own — with child components beneath it. Depth-2 (one HLD over a flat set of leaf LLDs) is the default; nesting is a triggered exception. So a single large LLD is a candidate for promotion to a sub-HLD, not automatically a smell — weigh promotion when a leaf outgrows itself rather than splitting reflexively.

When a node looks like it holds more than one thing, choose its shape by the *kind* of multiplicity, not the size of the doc. Two forces shape the tree, pulling opposite directions on purpose: **split out what is independent; consolidate what is bounded.** A concern that spans components and carries design decisions of its own (monitoring, security, a cost strategy) is an independent arrow: model it as its own node, referenced by dependent nodes from their own design docs — never as labels spread across many nodes or a side catalogue. (Where the arrow-maintenance overlay is present, the dependency edge is also encoded in its index; the overlay's guidance covers the fields.) Within one bounded component, the pull reverses — consolidate: if the parts share parent intent a parent doc should hold, **promote** to a sub-HLD over child leaves; if they are distinct intents with no shared parent, they are **sibling leaves**, each owning its own prefix; if they are merely categories of one component's intent — requirement types like errors, security, or performance *within that component* — keep one leaf and fold them into within-leaf `<LEAF>-<TYPE>` facets. The test between the two forces: does the concern carry its own design decisions spanning components (own node), or is it a sorting of one component's requirements (facet)? The deciding test for promotion is whether the parent doc would carry real intent or just a table of contents: a categorical grouping is a taxonomy label, not a sub-HLD.

In complex projects multiple LLDs may look semantically relevant. Do not silently pick — surface the candidate leaf LLDs with their scopes and ask the user which applies.

If a leaf LLD exists, confirm coherence with the change and update as needed.

After drafting or substantially revising an LLD, run an **LLD-level edge-case probe**: a list of "what happens when..." questions pointed at *this LLD's own gaps* — missing state transitions, unstated invariants, unspecified API error shapes, ordering assumptions inside the component. (Cross-component and cross-spec interactions come later in Phase 4, not here.) When a subagent is available, delegate the probe to the subagent for cleaner, less-biased coverage. Present the gap list; the user triages which gaps to fix in the LLD vs. defer as open questions.

Verify the LLD reads **context-free**: the Decisions & Alternatives table has filled-out Rationale columns, alternatives considered are named, and the prose doesn't rely on assumptions only present in the conversation. A reader without your chat history should be able to follow the design.

**STOP for user review.**

### Phase 3 — EARS spec draft or update

Every LLD change produces a corresponding EARS update. See `references/ears-syntax.md` for format.

- Spec IDs are stable. Revisions mutate text, not IDs, unless scope genuinely changes.
- Deleted IDs are not reused — git preserves the history.
- Delete specs that are no longer wanted rather than marking them obsolete.
- EARS requirement content lives only in the node's `{node}-specs.md` — never defined in a design doc. Design docs may cite spec IDs; they never carry requirement lines, status markers, or in-place definitions of what an ID requires.

After drafting or revising specs, run **post-draft consistency verification**:

- **Coverage** — are there behaviors described in the LLD that have no corresponding EARS spec?
- **Contradiction** — do any specs say different things about the same behavior?
- **Implicit scoping** — are any specs phrased as universal when they actually apply only to one context? When the current change adds a new mode or variant, audit sibling specs for scope that was implicit when only one variant existed. See `references/ears-syntax.md § Scope Disambiguation` for the litmus.
- **Context-free reading** — read each spec as if you have no conversation context. Are scopes explicit (no reliance on the surrounding section name to disambiguate)? Are conditions concrete (no "as we discussed" assumptions)? Specs travel by `grep`, so each line has to stand alone.

Present a brief consistency report alongside the specs.

**STOP for user review.**

### Phase 4 — Intent-narrowing edge audit

Distinct from the Phase 2 LLD-level probe in what it targets. Phase 2 asked "what's under-specified in *this LLD*?" — structural gaps inside one component. Phase 4 asks "given the LLD + specs *together*, where could the agent's interpretation diverge from what the user meant?" The targets here are **cross-spec and cross-segment**:

- Interactions between this LLD's specs and a sibling segment's specs (who owns what state?).
- Specs that read cleanly in isolation but admit two different behaviors when composed with another spec in the same segment.
- Namespace or feature-prefix ambiguity (does spec X apply to mode A, mode B, or both?).
- Sequencing ambiguity across specs (if A and B are both required, does order matter?).
- Places where the user's latent intent is probably narrower than what the specs literally allow.

Ask the user to resolve these *before* tests are written. LID's fundamental purpose — narrowing the agent's output distribution to the user's latent intent — is carried by this step more than any other.

**Divergence probe (per-spec).** The target list above is compositional; each new or changed spec line also gets probed individually. Generate 2–3 deliberately divergent plausible readings — what a blind implementer could take this line to require — and surface only the genuine forks for user resolution. Do not rely on introspection ("does this look ambiguous?"): the distribution that would miss the ambiguity is the one being asked. Use the most context-independent reader available — in-context generation is the floor; when subagents are available, delegate to blind readers given *only* the spec text, never the conversation; where the platform allows, use an equivalently capable model from a different provider. Land each fork's resolution as a narrowing edit or a new atomic spec line — never a compound "shall X and Y".

**STOP for user review.**

### Phase 5 — Tests first

Write tests **before** the code that satisfies them, per the HLD's intent-preloading rationale.

- Tests carry `@spec` annotations citing the EARS IDs they verify.
- Place the `@spec` annotation on the test that directly exercises the spec's behavior, not on every inner assertion.
- Do not proceed to code until tests exist and fail in the expected way.
- When this work is delegated to a subagent, the dispatch prompt embeds these obligations — see *Delegation discipline*.

**STOP for user review.**

### Phase 6 — Code

Implement. Code carries `@spec` annotations placed at the **entry point of the behavior's implementation graph** — the topmost function or module that owns the specified behavior, not every helper in its subtree. When a behavior spans multiple subsystems (e.g., UI + API + database), annotate at the entry point in each subsystem.

On completion, run **coherence verification** (below).

## Coherence verification

Two layers at the end of Phase 6.

**Structural checks (deterministic; soft-block completion):**

1. All tests pass.
2. Every `@spec` annotation in the changed files points to a spec ID that exists in a spec file.
3. Every behavioral EARS spec cited by the LLD has at least one test citing it.
4. No spec file references a deleted spec ID.

*Soft-block* means the skill will not consider the change complete until these pass, and surfaces failures clearly. The user can override per the user-is-always-right tenet — LID is not a linter or CI gate. The skill makes the cost visible; the user decides.

When the project declares a coherence-check script under `## LID Tooling` in the instruction file, structural checks may be delegated to that script. Without a declaration, perform checks in-prompt. See `docs/intent/arrow-maintenance/arrow-maintenance-design.md § Reference tooling` for the delegation rule.

**Semantic checks (agent judgment; surfaced, do not block):**

1. Do the updated specs describe behavior consistent with the LLD?
2. Does the updated LLD match the HLD's architecture?

Re-read each adjacent level of the arrow for the changed segment and produce a short report: for each spec/LLD/HLD pair, either "consistent" with a one-line justification or "needs review" with a specific point of tension. Semantic findings are surfaced for user review but do not block — "match" at the prose level is judgment, not a theorem.

## Decision docs

Most design decisions are recorded as a row in the relevant LLD's Decisions & Alternatives table. A few earn a full **decision doc** — a standalone artifact laying out a decision's context, criteria, options, and selection at enough resolution that a future cold reader can re-run the judgment.

Apply the test from the **landed** state, not the deliberation: *would a cold reader of the result find the choice non-obvious — question it, or be tempted to reverse it?* — not *was it hard to decide?* A decision that was contested while you worked but reads as obvious or native once it lands needs **neither a doc nor a row**; the structure documents itself, and recording a settled-obvious choice is the residue the *docs carry current intent* tenet strips. Add a **table row** when a cold reader would wonder "why this?" and a line settles it. Write a **full decision doc** only when the choice stays genuinely live — a reader would re-litigate it without the competing options and criteria. Decision docs are rare; a directory full of them is a smell.

A decision doc lives in the owning node's `decisions/` directory (`docs/intent/<segment>/decisions/` for a segment-level decision, `docs/decisions/` for a project-level one), is owned by that node, and carries no EARS IDs. See `references/decision-doc-template.md` for structure, the earns-its-place heuristic, and the fit-verdict format.

## Cascade discipline

**Cascade** means: when a change is made at one level of the arrow, the levels *downstream* are reviewed and updated in the same session so adjacent levels stay coherent. An LLD change implies potential spec/test/code changes; an HLD change implies potential LLD/spec/test/code changes.

**Within one arrow segment — one LLD and the specs, tests, and code that cite its EARS IDs — cascade is free.** Update downstream levels in the same session without further confirmation.

**Across segment boundaries, pause.** A change whose effect crosses into another LLD's territory is flagged; ask before propagating into the adjacent segment. Real LLDs are uneven; aggressive cross-boundary cascade propagates incoherence from under-specified regions into well-specified ones.

**A decision belongs where its substance lives.** When a decision's substance sits in one segment but implementing it cascades an obligation into a sibling segment, record the decision in the segment that owns its substance and note the sibling obligation as a cascade — not co-ownership. Only a decision whose *substance* genuinely spans siblings rises to their shared parent. (Example: a component's internal subprocess-split decision lives in that component's LLD even though it creates a contract a sibling component consumes — the sibling gets a cascade note, not co-ownership. Contrast: a decision that rewrites the EARS ID format the HLD itself defines has HLD-spanning substance and belongs at the root.)

An arrow segment is the territory owned by one **leaf** LLD, and its boundary is the **leaf prefix** — the full root-to-leaf path that identifies the segment. Because EARS IDs are path-concatenated, the boundary check is a prefix comparison: specs sharing the leaf prefix are in the same segment; specs whose path diverges at any earlier point belong to a different segment. When two unrelated leaves would collide on a path prefix, ask the user to disambiguate the position rather than silently coalescing them.

**HLD-originating cascade** fans out across every segment. Walk the affected LLDs in turn, pausing at each segment to confirm the change lands cleanly before cascading to that segment's specs, tests, and code.

**Cascade and uncommitted work.** When cascade would touch files the user has uncommitted changes in, warn with a description and proceed only after confirmation.

**Cascade and inconsistent arrows.** Arrows are often inconsistent — mid-transition aborts, overlapping scoped arrows, partial cascades from prior sessions. When you notice, surface it; do not auto-repair.

**Lifecycle events.** When cascade implies a split, merge, or rename of a segment, defer to the mechanics in `docs/intent/arrow-maintenance/arrow-maintenance-design.md § Lifecycle Events`.

## Bug fixes

Bug fixes are not a special case. They walk the arrow like any other change: find where behavior diverged from intent, determine whether intent needs to change / is already expressed but wrong / was never expressed at all, and cascade from there.

Fixing code without walking the arrow is a bypass — warn but do not block, per the user-is-always-right tenet.

## User overrides

If the user says "skip EARS here," "skip tests for this change," or otherwise overrides a phase requirement, warn about the drift risk and honor the override. The user is always right; make the cost visible.

## Brownfield LLD content

LLDs for reverse-engineered components use the **same template and section structure** as greenfield LLDs. What varies is the content's starting state:

- **Decisions & Alternatives** table entries carry `[inferred]` in the Rationale column when the decision was observed in code rather than authored. As the user confirms or refutes the inference, the `[inferred]` marker is removed and the rationale is written out.
- **Open Questions & Future Decisions** holds observed-but-unexplained behaviors and technical debt found during reconnaissance.
- **Major sections** may describe current state alongside intended behavior when they differ; flag divergence explicitly.

The LLD matures in place under the standard cascade discipline — no migration command or graduation step.

## `@spec` annotation pattern

```typescript
// @spec AUTH-UI-001, AUTH-UI-002
export function LoginForm({ ... }) { ... }
```

Place at the entry point of the behavior's implementation graph, not on every helper. Test files:

```typescript
// @spec AUTH-UI-010
it('validates email format before submission', () => { ... });
```

## LID-on-LID exception

Inside LID's own repository (when editing LID itself), `@spec` annotation direction inverts — `SKILL.md` bodies cannot host `@spec` without bending runtime behavior. Spec files carry the artifact pointer in their header; SKILL.md stays clean. This applies only inside the LID repo. See `docs/intent/linked-intent-dev/linked-intent-dev-design.md § Spec-File Header Format` for the schema.

## Reference files

- `references/ears-syntax.md` — EARS syntax, spec ID format, scope disambiguation.
- `references/lld-templates.md` — LLD structure template.
- `references/hld-template.md` — HLD standard sections template.
- `references/decision-doc-template.md` — decision-doc structure, the earns-its-place heuristic, and the fit-verdict format.


---

<!-- Appended reference: ears-syntax.md -->

# EARS Syntax Reference

EARS (Easy Approach to Requirements Syntax) provides structured patterns for writing unambiguous, testable requirements.

**Source**: https://alistairmavin.com/ears/

---

## Spec File Format

Specs live beside their design doc as `{node}-specs.md` within the node's folder under `docs/intent/`, with status markers. Each requirement is one line:

```markdown
- [x] **{ID}**: {Requirement statement}
- [ ] **{ID}**: {Requirement statement}
- [D] **{ID}**: {Requirement statement}
```

### Status Markers

- `[x]` — **Implemented**: Code and tests exist that realize this spec
- `[ ]` — **Active gap**: Should be implemented, work to do
- `[D]` — **Deferred**: Correct intent, not needed yet (e.g., scaling optimization not needed at current user count)

### Removing Specs

**Delete specs that are no longer wanted.** Do not mark them — just remove the line. Git preserves history if the rationale needs to be recovered later. A spec's presence means the intent is current; absence means the intent was withdrawn.

### Example

```markdown
## User Authentication

- [x] **AUTH-UI-001**: The system shall display a login button on the home screen.
- [x] **AUTH-UI-002**: When the user taps the login button, the system shall navigate to the authentication flow.
- [ ] **AUTH-API-001**: The system shall validate JWT tokens on every authenticated API request.
- [D] **AUTH-API-002**: Where multi-factor authentication is enabled, the system shall require a second factor.
```

---

## Semantic ID Format

**An ID is the root-to-leaf path, an optional within-leaf type/area segment, and a zero-padded number.** The path segments are tree positions; the prefix *is* the position up to the leaf that owns the spec. At depth-2 — one HLD over a flat set of LLDs, the default — the path is a single segment, so an ID is `{LEAF}-{NNN}` (`AUTH-001`, `CART-003`) or, with a within-leaf facet, `{LEAF}-{TYPE}-{NNN}` (`AUTH-UI-001`, `CART-API-012`). As the tree deepens, the path extends one segment at a time: `PEVAL-RUN-014` for the runner under prompt-eval, `PEVAL-PERF-LOAD-003` for load-testing under performance under prompt-eval.

- **The path encodes ancestry up to the leaf.** Read left to right, the path names the owning leaf and every ancestor up to the root. The cascade boundary is the *leaf's* path: two specs whose leaf paths differ belong to different segments.
- **A leaf may append one within-leaf type/area segment.** After the leaf path, a project MAY add a single facet segment that groups specs *inside* that leaf — `AUTH-UI-001` (leaf `AUTH`, UI facet), `ENGINE-LEDGER-001` (leaf `ENGINE`, ledger area). The facet is not a tree node and not a cascade boundary; it is an in-leaf grouping convention. This is the long-standing `{FEATURE}-{TYPE}-{NNN}` shape.
- **A subtree greps by construction.** Because the path *is* the position, `grep PEVAL-PERF` gathers the whole performance subtree and `grep PEVAL-RUN` gathers the runner leaf, facet and all. Prefix-grep gathers specs and code regardless of where the path/facet split falls.
- **The leaf's `prefix:` frontmatter is authoritative for where the path ends.** The path/facet boundary is not always parseable from the ID string alone (`AUTH-UI-001` could be leaf `AUTH` + facet `UI`, or a leaf at path `AUTH-UI`). The owning leaf declares its EARS prefix in `prefix:` frontmatter; that frontmatter, with `index.yaml` when the overlay is present, is the bridge from an ID to its design doc. Prefix-grep still gathers specs and code without it.

Constraints:

- **Global uniqueness across the project.** Two specs cannot share an ID. Path concatenation enforces this by construction — two leaves in different parts of the tree have different paths.
- **Grep-friendliness.** IDs use uppercase letters, digits, and hyphens only. No other characters. `grep "PEVAL-RUN-014"` should find every annotation, test, and spec-file citation of a given ID, and a prefix grep should gather a subtree or a leaf.
- **ID stability.** Ordinary growth — adding or refining specs within a segment — never renames an ID. IDs are stable **except under a deliberate, tooled re-parent or rename**, which rewrites the affected paths across spec files, docs, and `@spec` annotations together as one atomic operation (owned by the arrow-maintenance plugin). Revisions mutate text, not IDs. Deletion is permanent; the number is not recycled.
- **Numbering on conflict.** When drafting a new spec whose path already exists, surface the collision rather than silently picking — most often the new spec belongs at a deeper segment, which extends the path and resolves the conflict.

Keep IDs stable — don't renumber when inserting requirements.

---

## EARS Requirement Patterns

### 1. Ubiquitous (always true)

**Pattern**: "The system shall..."

```
- **CART-UI-001**: The system shall display the item count in the cart icon.
```

### 2. Event-Driven (triggered by action)

**Pattern**: "When [trigger], the system shall..."

```
- **CART-UI-002**: When the user taps "Add to Cart", the system shall add the item and show a confirmation.
```

### 3. State-Driven (while condition is true)

**Pattern**: "While [state], the system shall..."

```
- **CART-UI-003**: While the cart is empty, the system shall display an empty state message.
```

### 4. Optional (feature-dependent)

**Pattern**: "Where [feature enabled], the system shall..."

```
- **AUTH-OPT-001**: Where biometric auth is enabled, the system shall prompt for Face ID before checkout.
```

### 5. Unwanted (error handling)

**Pattern**: "If [unwanted condition], then the system shall..."

```
- **CART-UI-004**: If the network request fails, then the system shall display cached data with an error banner.
```

---

## Scope Disambiguation

A spec should be interpretable correctly even if found via grep without its surrounding section or file context. The dangerous anti-pattern is a spec that **reads as a universal rule but is actually scoped to a specific mode, variant, or context** — it becomes an implementation trap when a second variant is added.

### Checklist

1. **Name the scope in the WHEN clause.** If a spec applies to a specific mode, pass, or context, state it explicitly — don't rely on the section header.
2. **Litmus test:** "If a second variant of this behavior existed, would this spec still be unambiguous?" If no, the scope is implicit and needs to be stated.
3. **Cross-file domain concepts:** When a spec references a concept defined in another spec file, include a brief parenthetical — not a full definition, but enough to prevent a plausible-but-wrong implementation.

### Watch ubiquitous specs

Ubiquitous specs ("The system shall...") are most vulnerable — they have no WHEN clause to carry scope. Ask: is this truly ubiquitous, or does it just feel that way because there's currently only one context?

### Examples

**Bad** — sounds universal, actually scoped to one notification channel:
```
- **NOTIF-BE-003**: Notifications shall use a 30-second delivery timeout.
```

**Good** — scope is explicit:
```
- **NOTIF-BE-003**: Both email and push notifications shall use a 30-second delivery timeout.
```

**Bad** — cross-file concept with no inline context:
```
- **CART-API-012**: When processing retry queue items, the system shall implement a 500ms delay between requests.
```

**Good** — parenthetical prevents wrong interpretation:
```
- **CART-API-012**: When processing retry queue items (failed payment attempts re-queued after gateway timeout), the system shall implement a 500ms delay between payment gateway requests.
```

---

## Code Annotations

Reference specs in implementation:

```typescript
// @spec CART-UI-001, CART-UI-002
export function CartIcon({ ... }) {
  // Implementation
}
```

In tests:

```typescript
// @spec CART-UI-002
it('adds item to cart on tap', () => {
  // Test implementation
});
```

---

## Traceability

In implementation plans, map specs to phases:

```markdown
## Phase 1: Core Cart UI
Specs: CART-UI-001 through CART-UI-010
```


---

<!-- Appended reference: lld-templates.md -->

# LLD Templates Reference

Low-Level Designs (LLDs) document component-specific technical decisions. LLDs are **pure design documents** — they describe *how* things work, the constraints, trade-offs, and decisions. They do not track implementation status.

An LLD is a **leaf of the design tree**: it owns its segment's EARS specs and sits under an HLD (the root) or a sub-HLD. "LLD" is a role by position, not a fixed type — the template below is a **starting point**, not a rigid shape. A node carries the sections it needs; flat depth-2 (one HLD over a flat set of LLDs) is the default. When a leaf LLD outgrows itself — its intent differentiating into sub-parts that each warrant their own design — it **promotes into a sub-HLD** with child LLDs beneath it (see the HLD template reference); the promoted node sheds its EARS to those children, since only leaves own specs.

**Frontmatter.** Every LLD carries two pointers: `parent:` names the node above it (the root HLD at depth-2, or a sub-HLD when nested), so the tree is walkable upward; `prefix:` carries the EARS namespace the leaf owns — its full root-to-leaf path — so a reader knows its spec namespace (`AUTH-*`, or `EXP-BIDIFF-*` when nested) without grepping. The directory and file names are human-readable and need not equal this prefix (`arrow-maintenance/maintenance.md` may own prefix `SCALE-MAINT`); `prefix:` is the authoritative bridge from the human name to the namespace, and it marks where the leaf path ends — a spec ID may append an optional within-leaf type/area segment and a number after the leaf prefix (`AUTH-UI-001`). A pure-prose leaf that owns no EARS omits `prefix:`. (Grouping sub-HLDs also carry `prefix:` — the namespace they root — per the HLD template reference.)

```markdown
---
parent: high-level-design
prefix: AUTH
---
```

Implementation status is tracked in:
- **Spec files** (`{node}-specs.md`, beside each design doc under `docs/intent/`) via `[x]`/`[ ]`/`[D]` markers on EARS specs
- **Arrow docs** (`docs/arrows/`) via coverage tables (if using arrow-maintenance plugin)

## Greenfield vs. Brownfield

The template below is used for both greenfield LLDs (authored before implementation) and brownfield LLDs (reverse-engineered from existing code). There is no separate brownfield template. What varies is the *content's starting state*:

- **Brownfield Decisions & Alternatives** rows carry `[inferred]` in the Rationale column when the decision was observed in code rather than authored by the user. As the user confirms or refutes the inference in subsequent sessions, the `[inferred]` marker is removed and the rationale is written out.
- **Brownfield Open Questions & Future Decisions** holds observed-but-unexplained behaviors and technical debt discovered during reconnaissance. These migrate into Decisions, into specs, or into a planned remediation as the user engages with the code.
- **Brownfield Major sections** may describe current state alongside intended behavior when the two differ — flag divergence explicitly rather than pretending the code matches intent.

As a brownfield LLD matures through normal LID cascades, inferred content becomes authored content. No migration or "graduation" step is needed — the LLD evolves in place.

## File Location

Every node is a **directory** under `/docs/intent/`, named for the node. A leaf LLD `foo` is `docs/intent/foo/foo-design.md`, with its EARS beside it as `foo-specs.md` and a `decisions/` dir if it has decision docs. At the default depth-2, each LLD is one such folder directly under `docs/intent/`:
- `docs/intent/user-authentication-flow/user-authentication-flow-design.md` (+ `user-authentication-flow-specs.md`)
- `docs/intent/payment-processing-pipeline/payment-processing-pipeline-design.md`
- `docs/intent/offline-sync-strategy/offline-sync-strategy-design.md`

**The directory layout mirrors the design tree's structure (node-as-folder).** A sub-HLD `foo` is the directory `docs/intent/…/foo/` holding `foo-design.md` plus a child directory per child — e.g. the `arrow-maintenance` sub-HLD is `docs/intent/arrow-maintenance/arrow-maintenance-design.md` with child directories `maintenance/` (holding `maintenance-design.md` + `maintenance-specs.md`) and `map-codebase/`. A leaf and a sub-HLD have the same shape, distinguished only by whether the folder holds a `-specs.md` (leaf) or child directories (sub-HLD). When a leaf promotes into a sub-HLD, its `-specs.md` goes away — the EARS move down into the new leaf children — and child directories appear beside its `-design.md`. Directory and file names are human-readable and need not equal the EARS prefix; each node's `prefix:` frontmatter carries it (see the EARS syntax reference). Decision docs follow `references/decision-doc-template.md`.

## Standard Structure

```markdown
# [Component Name]

## Context and Design Philosophy

Why this component exists and guiding principles.

## [Major Section 1]

Technical details...

## [Major Section 2]

Technical details...

## Decisions & Alternatives

For each significant design choice, record what was chosen, what was considered, and why. This section preserves context for future sessions — if requirements change, the team can revisit a specific decision rather than re-exploring the entire design space.

This table is the sanctioned home for rejected alternatives and why they were trimmed. A "we considered X and rejected it because Y" note belongs here, where a fresh author choosing the current design would independently record it. The same note as a defensive aside in body prose ("there is no separate X…") is residue under *docs carry current intent* — the rationale is legitimate; only its placement makes it keep-worthy here and a fossil elsewhere.

| Decision | Chosen | Alternatives Considered | Rationale |
|----------|--------|------------------------|-----------|
| (decision point) | (selected approach) | (brief list) | (why this direction) |

## Open Questions & Future Decisions

### Resolved
1. ✅ Decision made with rationale

### Deferred
1. Decision to make during implementation

## References

- Related docs, external resources
```

## When to Use Narrative vs Structured Format

### Use Narrative Format For:

**Complex constraint interactions** - When multiple requirements interact:

```markdown
## Offline Buffering Strategy

The offline buffer must balance three competing constraints: reliable
persistence across app crashes, efficient upload resumption, and minimal
battery impact during background sync. IndexedDB provides the persistence
foundation, storing metadata including uploadId and progress markers. When
network drops mid-upload, the multipart session preserves server-side state
while the client maintains enough context to resume without re-uploading
completed parts. The 5MB part size represents a deliberate trade-off between
retry cost (smaller parts mean less re-upload on failure) and request overhead
(larger parts mean fewer HTTP round-trips).
```

**Multi-service orchestration** - When showing flow between components:

```markdown
## Processing Pipeline

Order processing flows through three phases, each with distinct error handling
requirements. Phase 1 (validation) tolerates retry since it's idempotent - the
same input always produces the same result. Phase 2 (payment) requires careful
state tracking because payment gateway calls are expensive and partially-
completed transactions should be preserved. Phase 3 (fulfillment) uses database
transactions to ensure atomic updates across Orders, Inventory, and Shipping.
```

### Use Structured Format For:

**API contracts and interfaces**:

```markdown
## API Endpoints

| Endpoint              | Method | Request          | Response        |
| --------------------- | ------ | ---------------- | --------------- |
| `/orders`             | POST   | OrderCreateReq   | OrderConfirm    |
| `/orders/{id}`        | GET    | -                | Order           |
| `/orders/{id}/status` | GET    | -                | OrderStatus     |
```

**Configuration and thresholds**:

```markdown
## Rate Limiting Thresholds

**Per-user limits**:
- Standard tier: 100 requests/minute
- Premium tier: 1000 requests/minute
- Enterprise tier: Custom

**Global limits**:
- Burst: 10,000 requests/second
- Sustained: 5,000 requests/second
```

**State enumerations**:

```markdown
## Order States

- `pending` - Created, awaiting payment
- `paid` - Payment confirmed
- `processing` - Being prepared
- `shipped` - In transit
- `delivered` - Complete
- `cancelled` - Order cancelled
```

## Visual Diagrams

Include ASCII diagrams for UI layouts:

```markdown
## Visual Hierarchy

┌─────────────────────────────────────┐
│ My Orders                     [⚙]   │ ← Top nav
├─────────────────────────────────────┤
│ Active│History│ Returns             │ ← Tab bar
│ ██████│       │                     │
├─────────────────────────────────────┤
│ Order #12345              In Transit│ ← Order card
│ ┌─────────────────────────────────┐ │
│ │ 2 items · $47.99                │ │
│ │ Arrives: Jan 22                 │ │
│ └─────────────────────────────────┘ │
│              [Track Order]          │ ← CTA button
└─────────────────────────────────────┘
```

## Design Decision Documentation

Capture the "why" alongside the "what":

```markdown
## Decision: Payment Provider

**Chosen**: Stripe

**Rationale**: Stripe provides comprehensive fraud detection, handles
PCI compliance, and offers a well-documented API. The 2.9% + $0.30 fee
is competitive and predictable. Their webhook system enables reliable
async processing.

**Alternatives considered**:
- PayPal: Higher fees for our volume, more complex integration
- Square: Better for in-person, weaker for online-only
- Adyen: Enterprise pricing not cost-effective at our scale
```

## Section Depth Guidelines

- Keep sections focused on single concerns
- Use H2 for major sections, H3 for subsections
- If a section exceeds ~100 lines, consider splitting
- Link to separate reference docs for detailed specs


---

<!-- Appended reference: hld-template.md -->

# HLD Template Reference

A project's High-Level Design (HLD) is the **root of the design tree** — the single top-level document that answers *what* and *why* for the whole project. One HLD per project. File location: `docs/high-level-design.md`.

The same shape also appears *below* the root. When a subsystem grows too deep for one LLD, it promotes into a **sub-HLD**: an HLD-shaped document that is the root of its own subtree, holding that subtree's problem, approach, and key decisions while parenting its children. "HLD" and "LLD" are roles by position in the tree, not fixed types — this template is a starting point for any node acting as a tree root or grouping node, which carries the sections it needs. A sub-HLD **owns no EARS**; it delegates specs to its child LLDs (see the LLD template reference). Depth-2 — one HLD over a flat set of LLDs — is the default; sub-HLDs are a triggered exception, not a requirement. A *merely categorical* grouping — a label with no shared parent intent a parent doc should hold — is **not** a sub-HLD: its members stay flat leaves (it may still group them for navigation, as `index.yaml`'s `taxonomy` field does). The test is whether a parent design doc *should* exist, not whether one already does — write a parent where shared intent warrants it; keep things flat where it does not.

**Non-root pointers.** A sub-HLD carries a `parent:` pointer naming its parent node (so the tree is walkable upward) and a `prefix:` carrying the EARS namespace it roots. The directory and file names are human-readable and need not equal that prefix; `prefix:` is the authoritative bridge from the human name to the namespace. Its child LLDs extend the prefix and own the actual specs — the sub-HLD owns none directly — but `prefix:` lets a reader grep the whole subtree (`grep EXP`). The root HLD has neither pointer.

**File placement — node-as-folder.** Every node is a directory. A sub-HLD `foo` is `docs/intent/…/foo/` holding `foo-design.md` plus a child directory per child — e.g. the `arrow-maintenance` sub-HLD is `docs/intent/arrow-maintenance/arrow-maintenance-design.md` with child directories `maintenance/` and `map-codebase/`. (A leaf is the same shape, additionally holding `foo-specs.md`.) Promoting a leaf to a sub-HLD adds child directories beside its `-design.md` and moves its EARS down into the new leaf children. (See the LLD template reference for the matching detail.)

```markdown
---
parent: high-level-design
prefix: EXP
---
```

## Standard sections

The HLD uses these sections. In **Full LID**, every section is filled. In **Scoped LID**, sections may be explicitly marked `*(not yet specified)*` rather than filled with placeholder prose — gaps are visible rather than hidden.

```markdown
# High-Level Design: {Project Name}

## Problem

The problem this project exists to solve. What is broken, who suffers, why now.

## Approach

How the project solves the problem in general terms. If there are multiple load-bearing approaches (a core mechanism plus secondary disciplines), name each as its own sub-section.

## Target Users

Who the project serves. Concrete postures or roles, not demographics. What they need and at what cost.

## Goals

What success looks like — specific, falsifiable when possible. Prefer outcomes over outputs.

## Non-Goals

What this project explicitly is not. Useful boundary — makes it easier to say "no" to surface growth.

## Tenets

One-line tie-breakers: which way the project leans when a decision has two defensible answers and no spec covers it. A tenet is forward-looking — it governs choices the arrow has not reached yet — which makes it distinct from Key Design Decisions, which record choices already made, and from specs, which fix a definite action at a known trigger. A tenet leans a class of unforeseen choices; a candidate phrased as *when X, do Y* is a spec — route it to EARS, not the tenet list, even when its opposite is a defensible choice. The discriminating test is the **defensible opposite**: a real tenet's reverse is a choice a different project could reasonably make. "We prefer X over Y" where Y is absurd is a platitude, not a tenet, and resolves nothing. A tenet stays a one-line lean: operational elaboration (how to apply it, steps to run) routes into workflow guidance — the project's instruction file or governing skill — not into the tenet text. State each as a single line and order them so that when two conflict, the higher one wins. A short HLD has two or three load-bearing tenets, not a manifesto.

```markdown
- **Boring over clever.** When a problem has a well-worn solution and a novel one, prefer the well-worn one unless the novel one is decisively better — a future maintainer should not have to reverse-engineer ingenuity.
- **Fail loud, not silent.** When an operation cannot complete correctly, surface the failure rather than degrading quietly.
```

## System Design

High-level architecture: major components, how they fit, what boundaries separate them. Mermaid diagrams preferred for structural views; ASCII for UI mockups when needed.

## Key Design Decisions

Load-bearing choices and the reasoning behind them. Each decision names the alternatives considered and why this direction was chosen. Prefer a few deep decisions with clear rationale over many shallow ones.

## Success Metrics

How you know the project is working. Where possible, describe falsification signals — conditions under which the project would be judged broken.

## FAQ (optional)

Questions the team has answered often enough that the answer belongs in the HLD.

## References

Prior art, linked specs, related projects, external docs.
```

## Notes

- **Keep it short enough to re-read.** An HLD that sprawls beyond ~2000 lines stops being an orientation doc. Push detail down into child LLDs; when a single subsystem's detail outgrows one LLD, promote it into a sub-HLD with its own child LLDs.
- **Docs carry current intent, written to be read cold.** When the HLD changes, update in place and delete what's wrong. Write it as if authored fresh today from current intent alone — no narration of how it changed, no meaning that needs the conversation that produced it, no rebuttals to questions only a past discussion raised. Rationale and considered alternatives that a fresh author would independently write stay; they are present intent, not history.
- **Diagrams.** Mermaid is the default for structural, flow, state, and ERD diagrams — renders natively on GitHub and is token-efficient for agent consumption. ASCII is the convention for UI mockups. Detect existing project conventions first; ask once if unclear.
- **Trade-off sketches.** When drafting a new HLD or making a consequential architectural change, first sketch 2–3 competing options (~200 words each with downstream consequences) and present them for user selection before committing to a full draft. See the `linked-intent-dev` skill's Phase 1 guidance.
- **Non-Goals earn their place.** An explicit non-goal that constrains future surface growth is worth more than a vague goal.
- **Tenets are elicited, not assumed.** When drafting or revising the HLD, surface the few decisions that could reasonably go more than one acceptable way and ask the user to state a preference. See the `linked-intent-dev` skill's Phase 1 guidance.

## Scoped-LID variant

For Scoped LID projects, mark unspecified sections explicitly:

```markdown
## System Design

*(not yet specified)*

## Success Metrics

*(not yet specified — scope is too narrow for project-level metrics; see LLD for scope-specific success criteria)*
```

Leaving a section unfilled is better than filling it with placeholder prose — agents can tell which parts of the intent are authored and which are still gaps.


---

<!-- Appended reference: decision-doc-template.md -->

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