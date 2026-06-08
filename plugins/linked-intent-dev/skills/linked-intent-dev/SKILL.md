---
name: linked-intent-dev
description: Guide for linked-intent development (LID). Consult for ALL code changes. Walks changes through a mode-aware six-phase workflow (HLD → LLD → EARS → intent-narrowing edge audit → tests-first → code) with mandatory stops between each phase. Bugs walk the arrow like any other change — no short-circuit. Enforces cascade discipline within arrow segments and pauses across segment boundaries.
---

# Linked-Intent Development

This skill guides a structured linked-intent development workflow. LID's goal is to narrow the agent's output distribution to the user's latent intent — specs, tests, and linkage together make the arrow of intent walkable, and the workflow's stops are where the agent's interpretation meets the user's intent for reconciliation.

## Three rules govern every phase

**Stop and iterate at every phase boundary.** After completing each phase below, present the output to the user, incorporate numbered feedback, and proceed only on explicit approval. Each stop is mandatory. Skipping stops is the single most common way this workflow degrades into a rush — the discipline is non-optional. (Carveout: command-mode skills that execute a single directed pass, like `/arrow-maintenance`'s audit-and-update, are not phase-structured in this sense and do not pause mid-pass. This workflow is generative; phases here produce intent, so every boundary gets a stop.)

**Run a coherence pre-flight before starting or resuming implementation.** When picking up work — new session, returning to a change, cascading from an upstream change — verify that the HLD, LLDs, EARS specs, and tests are mutually coherent for the segment about to be touched:

- Do the EARS specs trace to the current LLD?
- Do the tests trace to the current EARS specs?
- Does the LLD still reflect the HLD's architecture?

If drift is detected, fix the docs first, then implement. A resumption check prevents one session's drift from being compounded into the next session's change.

**Write docs as their fresh author.** Every HLD, LLD, and EARS spec produced by these phases must read as if authored fresh today, by someone who knew only the current intent and nothing of this conversation. As you draft or revise a doc, run the test on each line — would that fresh author put it on the page? Three residues fail it: narration of how the intent changed; meaning that only resolves for someone who was in this conversation; and answers or rebuttals that exist only because we discussed the question here. The keep-side is load-bearing too — rationale, considered alternatives, and constraints a fresh author would independently write stay; they are present intent, not residue. Record rejected alternatives and why in the LLD's Decisions & Alternatives table, not as asides in body prose. This is the *docs carry current intent* tenet. Write in the project's own domain language — name components, segments, and specs with the words the user and the codebase already use, not generic or LID-imposed labels. This is the *Speak the project's language* tenet.

## Mode-aware triggering

Every LID project declares its mode in its instruction file (the project's `AGENTS.md`, or `CLAUDE.md` under Claude Code) under the `## LID` block's `- Mode:` bullet. Defaults to Full if the block or bullet is missing or malformed (surface a one-line warning).

- **Full LID**: the skill triggers broadly — any prompt that could result in a code change is in scope.
- **Scoped LID**: additionally checks whether the files or subsystems the prompt touches fall within the declared scope. Scope is declared in the instruction file under a `## LID Scope` section (see `docs/intent/linked-intent-dev/core/core-design.md § Scope declaration format`) with include/exclude glob patterns. If every file the prompt touches is outside scope (in the exclude list, or not in the include list), the skill does not trigger. If any touched path is in scope, the skill triggers. For prompts that reference no specific paths, default to triggering and ask the user to confirm when ambiguous. When the `## LID Scope` section is missing or empty in a Scoped-mode project (misconfiguration), fall back to treating all prompts as in-scope and surface a warning suggesting `/update-lid` to declare scope.

## The six phases

### Phase 1 — HLD check (with bootstrap when needed)

**First, check whether the project is LID-configured.** If the instruction file has no LID directives AND no LID-shaped artifacts exist (no `docs/intent/` content, no `docs/high-level-design.md`, no `docs/arrows/index.yaml`), this is a fresh project — the user invoked `/linked-intent-dev` with a description of what they want to build. Apply the `update-lid` skill's bootstrap branch as a sub-step: create `docs/intent/`, create or append-to the instruction file (`AGENTS.md` canonical, with a `CLAUDE.md` alias — see the `update-lid` skill) with LID directives, add the `## LID` block (`- Mode:` default Full unless the user indicates Scoped, `- Version:` set to the installed `linked-intent-dev` version). Read the `update-lid` skill's SKILL.md if you need details on the bootstrap behavior; the bootstrap is the same skill called inline, not a separate workflow.

Once configured, proceed with the HLD check: does a top-level HLD exist at `docs/high-level-design.md`? Does it cover the domain of the change? If the change alters the project's architecture, update the HLD first. If no HLD exists (fresh project), draft one from the user's description.

For consequential architectural changes (a new approach, a significant trade-off, a new mode) — and on a fresh-project HLD draft — before committing to a full HLD **sketch 2–3 competing options** (~200 words each, naming downstream consequences) and present them for user selection. Surfacing decisions as *choices among alternatives* — rather than as the agent's best guess — is the primary edge-detection mechanism at the HLD level.

When drafting or revising the HLD, **elicit tenets**: surface the few decisions that could reasonably go more than one acceptable way, ask the user which way to lean, and record each as a one-line tie-breaker under `## Tenets`. Apply the defensible-opposite test before proposing one — if the reverse of the tenet is absurd rather than a choice a different project could reasonably make, it is a platitude and resolves nothing; drop it. Apply a second test too: a tenet leans a class of decisions no spec anticipates — if the candidate reads as a triggered action (*when X, do Y* with a definite outcome), it is a spec, not a tenet; route it to EARS rather than the tenet list, even when its opposite is defensible. A tenet is edge detection for choices no spec will anticipate. Surface the load-bearing ones you can see and invite more; do not interrogate the user for an exhaustive set.

Whatever you draft, verify the HLD reads **context-free**: rationale present, alternatives named, no reliance on conversation context that won't travel to the next session.

See `references/hld-template.md` for standard HLD sections.

**STOP for user review.**

### Phase 2 — LLD check or draft

Does a leaf LLD exist for the intent component being changed?

If not, draft one using the template at `references/lld-templates.md`.

The design layer is a recursive tree, and "HLD" and "LLD" are **roles by position**: the root is the HLD, the leaves are the LLDs that own EARS, and a component with enough internal depth to outgrow one doc is promoted to a **sub-HLD** — HLD-shaped for its subtree, owning no EARS of its own — with child components beneath it. Depth-2 (one HLD over a flat set of leaf LLDs) is the default; nesting is a triggered exception. So a single large LLD is a candidate for promotion to a sub-HLD, not automatically a smell — weigh promotion when a leaf outgrows itself rather than splitting reflexively.

When a node looks like it holds more than one thing, three shapes are possible, and which fits turns on the intent, not the size of the doc: if the parts share parent intent a parent doc should hold, **promote** to a sub-HLD over child leaves; if they are distinct intents with no shared parent, they are **sibling leaves**, each owning its own prefix; if they are merely categories of one intent — cross-cutting concerns (errors, security, performance, monitoring) or requirement *types* — keep one leaf and fold them into within-leaf `<LEAF>-<TYPE>` facets. The deciding test for promotion is whether the parent doc would carry real intent or just a table of contents: a categorical grouping is a taxonomy label, not a sub-HLD.

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

**STOP for user review.**

### Phase 5 — Tests first

Write tests **before** the code that satisfies them, per the HLD's intent-preloading rationale.

- Tests carry `@spec` annotations citing the EARS IDs they verify.
- Place the `@spec` annotation on the test that directly exercises the spec's behavior, not on every inner assertion.
- Do not proceed to code until tests exist and fail in the expected way.

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
