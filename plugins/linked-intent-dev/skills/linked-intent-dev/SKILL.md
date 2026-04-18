---
name: linked-intent-dev
description: Guide for linked-intent development (LID). Consult for ALL code changes. Walks changes through a mode-aware six-phase workflow (HLD → LLD → EARS → intent-narrowing edge audit → tests-first → code) with mandatory stops between each phase. Bugs walk the arrow like any other change — no short-circuit. Enforces cascade discipline within arrow segments and pauses across segment boundaries.
---

# Linked-Intent Development

This skill guides a structured linked-intent development workflow. LID's goal is to narrow the agent's output distribution to the user's latent intent — specs, tests, and linkage together make the arrow of intent walkable, and the workflow's stops are where the agent's interpretation meets the user's intent for reconciliation.

## Two rules govern every phase

**Stop and iterate at every phase boundary.** After completing each phase below, present the output to the user, incorporate numbered feedback, and proceed only on explicit approval. Each stop is mandatory. Skipping stops is the single most common way this workflow degrades into a rush — the discipline is non-optional. (Carveout: command-mode skills that execute a single directed pass, like `/arrow-maintenance`'s audit-and-update, are not phase-structured in this sense and do not pause mid-pass. This workflow is generative; phases here produce intent, so every boundary gets a stop.)

**Run a coherence pre-flight before starting or resuming implementation.** When picking up work — new session, returning to a change, cascading from an upstream change — verify that the HLD, LLDs, EARS specs, and tests are mutually coherent for the segment about to be touched:

- Do the EARS specs trace to the current LLD?
- Do the tests trace to the current EARS specs?
- Does the LLD still reflect the HLD's architecture?

If drift is detected, fix the docs first, then implement. A resumption check prevents one session's drift from being compounded into the next session's change.

## Mode-aware triggering

Every LID project declares its mode in `CLAUDE.md` under a `## LID Mode:` heading. Defaults to Full if missing or malformed (surface a one-line warning).

- **Full LID**: the skill triggers broadly — any prompt that could result in a code change is in scope.
- **Scoped LID**: additionally checks whether the files or subsystems the prompt touches fall within the declared scope. If the prompt is entirely outside scope, the skill does not trigger. Until the scope-declaration format is formalized, Scoped-mode triggering treats all prompts as in-scope and surfaces a one-line warning that scope has not yet been declared.

## The six phases

### Phase 1 — HLD check

Does a top-level HLD exist at `docs/high-level-design.md`? Does it cover the domain of the change? If the change alters the project's architecture, update the HLD first.

For consequential architectural changes (a new approach, a significant trade-off, a new mode), before drafting the full HLD **sketch 2–3 competing options** (~200 words each, naming downstream consequences) and present them for user selection. Surfacing decisions as *choices among alternatives* — rather than as the agent's best guess — is the primary edge-detection mechanism at the HLD level.

See `references/hld-template.md` for standard HLD sections.

**STOP for user review.**

### Phase 2 — LLD check or draft

Does an LLD exist for the intent component being changed?

If not, draft one using the template at `references/lld-templates.md`.

In complex projects multiple LLDs may look semantically relevant. Do not silently pick — surface the candidate LLDs with their scopes and ask the user which applies.

If an LLD exists, confirm coherence with the change and update as needed.

After drafting or substantially revising an LLD, run an **LLD-level edge-case probe**: a list of "what happens when..." questions pointed at *this LLD's own gaps* — missing state transitions, unstated invariants, unspecified API error shapes, ordering assumptions inside the component. (Cross-component and cross-spec interactions come later in Phase 4, not here.) When a subagent is available, delegate the probe to the subagent for cleaner, less-biased coverage. Present the gap list; the user triages which gaps to fix in the LLD vs. defer as open questions.

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

When the project declares a coherence-check script under `## LID Tooling` in `CLAUDE.md`, structural checks may be delegated to that script. Without a declaration, perform checks in-prompt. See `docs/llds/arrow-maintenance.md § Reference tooling` for the delegation rule.

**Semantic checks (agent judgment; surfaced, do not block):**

1. Do the updated specs describe behavior consistent with the LLD?
2. Does the updated LLD match the HLD's architecture?

Re-read each adjacent level of the arrow for the changed segment and produce a short report: for each spec/LLD/HLD pair, either "consistent" with a one-line justification or "needs review" with a specific point of tension. Semantic findings are surfaced for user review but do not block — "match" at the prose level is judgment, not a theorem.

## Cascade discipline

**Cascade** means: when a change is made at one level of the arrow, the levels *downstream* are reviewed and updated in the same session so adjacent levels stay coherent. An LLD change implies potential spec/test/code changes; an HLD change implies potential LLD/spec/test/code changes.

**Within one arrow segment — one LLD and the specs, tests, and code that cite its EARS IDs — cascade is free.** Update downstream levels in the same session without further confirmation.

**Across segment boundaries, pause.** A change whose effect crosses into another LLD's territory is flagged; ask before propagating into the adjacent segment. Real LLDs are uneven; aggressive cross-boundary cascade propagates incoherence from under-specified regions into well-specified ones.

Arrow segment boundaries are defined by the EARS spec ID prefix: specs sharing a `{FEATURE}` prefix are in the same segment. When two unrelated features would collide on a prefix, ask the user for a disambiguating namespace rather than silently coalescing.

**HLD-originating cascade** fans out across every segment. Walk the affected LLDs in turn, pausing at each segment to confirm the change lands cleanly before cascading to that segment's specs, tests, and code.

**Cascade and uncommitted work.** When cascade would touch files the user has uncommitted changes in, warn with a description and proceed only after confirmation.

**Cascade and inconsistent arrows.** Arrows are often inconsistent — mid-transition aborts, overlapping scoped arrows, partial cascades from prior sessions. When you notice, surface it; do not auto-repair.

**Lifecycle events.** When cascade implies a split, merge, or rename of a segment, defer to the mechanics in `docs/llds/arrow-maintenance.md § Lifecycle Events`.

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

Inside LID's own repository (when editing LID itself), `@spec` annotation direction inverts — `SKILL.md` bodies cannot host `@spec` without bending runtime behavior. Spec files carry the artifact pointer in their header; SKILL.md stays clean. This applies only inside the LID repo. See `docs/llds/linked-intent-dev.md § Spec-File Header Format` for the schema.

## Reference files

- `references/ears-syntax.md` — EARS syntax, spec ID format, scope disambiguation.
- `references/lld-templates.md` — LLD structure template.
- `references/hld-template.md` — HLD standard sections template.
