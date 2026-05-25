---
parent: linked-intent-dev
prefix: LID-CORE
---

# LLD: linked-intent-dev Workflow Skill

## Context

This leaf LLD covers the pure-prose `linked-intent-dev` workflow skill — the guidance that shapes how the agent approaches every code change in a LID project. Plugin-level concerns shared across the core plugin's three skills — mode detection mechanics, spec-ID format, the LID-on-LID linkage inversion, and eval-metadata conventions — live in the parent `LID` sub-HLD at `docs/intent/linked-intent-dev/linked-intent-dev-design.md`.

**A note on actors.** Throughout this document, "the skill" refers to the prose guidance contained in a `SKILL.md`. The skill does not act on its own — it is content the agent consults. When this LLD says "the skill surfaces X" or "the skill warns," the mechanism is: the agent, after consulting the skill, performs the surfacing or warning in the assistant turn it produces. The skill is the instruction; the agent is the actor.

## The `linked-intent-dev` Skill (pure-prose)

### Intent

Shape the agent's approach to every code change in a LID project so that intent flows HLD → LLD → EARS → Tests → Code, and so that drift is caught at the earliest level where it originates. This skill does not execute a procedure; it guides the agent's workflow through a sequence of checkpoints and reminds it of cascade discipline at arrow boundaries.

### Triggering

The skill declares itself relevant for all prompts that propose changes to project code or specifications. Triggering is *mode-aware*:

- **In Full LID**, the skill triggers broadly — any prompt that could result in a code change is in scope.
- **In Scoped LID**, the skill additionally checks whether the files or subsystems the prompt touches fall within the declared scope. If the prompt is entirely outside scope, the skill does not trigger. If any touched area is in scope, the skill triggers. For prompts that do not reference any specific file paths, the skill defaults to triggering (benefit of doubt) and asks the user to confirm scope applicability when the situation is ambiguous.

### Scope declaration format (Scoped mode)

A Scoped-LID project declares its scope in `CLAUDE.md` immediately after the `## LID` block (which carries `- Mode: Scoped`), in a `## LID Scope` section:

```markdown
## LID
- Mode: Scoped
- Version: 1.2.0

## LID Scope

Paths in scope:
- `src/auth/**`
- `packages/billing/**`
- `apps/mobile/src/services/auth/**`

Paths explicitly excluded (even within in-scope roots):
- `src/auth/legacy/**`
- `**/*.test.ts`
```

Rules:

- Patterns follow gitignore-style glob semantics. A trailing `/**` matches any path under the directory; a leading `**/` matches at any depth.
- A file path is "in scope" when it matches at least one pattern in *Paths in scope* and matches no pattern in *Paths explicitly excluded*. Exclude wins when both match.
- The "Paths explicitly excluded" list is optional; when absent, only the include list governs.
- When the mode is Full, the `## LID Scope` section is **omitted entirely** from CLAUDE.md. The skill treats a missing `## LID Scope` as "entire project is in scope."
- A Scoped-mode project with a missing or empty `## LID Scope` section is a misconfiguration: the skill defaults to triggering on all prompts and surfaces a one-line warning that scope has not been declared (same fallback as before the format was finalized). The user should run `/update-lid` to declare scope.

The skill errs toward over-triggering rather than under-triggering. An over-triggered consult costs a handful of tokens; an under-triggered one lets drift accumulate silently. To keep over-triggering cheap, the SKILL.md body contains only guidance universal to every consult — the mode-aware dispatch, the phase list, the cascade rule. Per-phase and per-mode expansions (EARS syntax, LLD template, HLD template, cascade edge cases) live under `references/` and are loaded only when the relevant phase is entered. This keeps the always-loaded surface small enough that the skill can trigger liberally without burdening the user's context window. Description optimization via `skill-creator`'s `run_loop.py` remains available for calibrating trigger accuracy over time.

### Workflow checkpoints

Three rules govern every phase below.

**Stop and iterate at every phase boundary.** After completing each phase, the agent presents its output to the user, incorporates numbered feedback, and proceeds only on explicit approval. Each stop is mandatory, not optional. Skipping stops is the single most common way this workflow degrades into a rush — the discipline is non-optional. This matches the HLD tenet of the same name.

**Before starting (or resuming) implementation, run a coherence pre-flight.** Verify that the current state of HLD, LLDs, EARS specs, and tests are mutually coherent for the segment about to be touched — do EARS specs trace to the current LLD? Do tests trace to current EARS? Does the LLD still reflect the HLD's architecture? If drift is detected, fix the docs first and only then implement. A resumption check prevents one session's drift from being compounded into the next session's change.

**Write docs as their fresh author.** Every HLD, LLD, and EARS spec produced by these phases must read as if authored fresh today, by someone who knew only the current intent and nothing of the conversation that produced it. As docs are drafted or revised, the agent runs the fresh-author test on each line and watches for the three residues that fail it — narration of how the intent changed; meaning that only resolves for someone who was in the conversation; and rebuttals to questions only a past discussion raised. The keep-side is load-bearing: rationale, considered alternatives, and constraints a fresh author would independently write stay, recorded in the LLD's Decisions & Alternatives table rather than as body-prose asides. This is the HLD's *docs carry current intent* tenet. Docs, component names, and segment names use the project's own domain vocabulary, not generic or LID-imposed labels (HLD tenet: *Speak the project's language*).

When the skill triggers, it guides the agent through six phases:

1. **HLD check** — first, check whether the project is LID-configured: does CLAUDE.md have LID directives? Does `docs/` exist with the standard subdirectories? If the project is unconfigured (no LID artifacts at all — typically a fresh project where the user invoked `/linked-intent-dev` with a project description), apply the `update-lid` skill's bootstrap branch as a sub-step before drafting the HLD: create `docs/intent/`, append LID directives to (or create) CLAUDE.md, prompt for mode (default Full). After bootstrap, proceed with the HLD check: does a top-level HLD exist at `docs/high-level-design.md`? If not, draft it. Does it cover the domain of the change? If the change alters the project's architecture, the HLD is updated first. For consequential architectural changes (new approach, significant trade-off, new mode), the agent first **sketches 2–3 competing options** (~200 words each, naming downstream consequences) and presents them for user selection before committing to a full HLD draft. Surfacing decisions as *choices among alternatives* — rather than as the agent's best guess — is the primary edge-detection mechanism at the HLD level. When a decision stays *live* once it lands — a cold reader of the result would still question or try to reverse it without the full tradeoffs (competing options weighed against criteria, not a choice one rationale line settles) — the agent records it as a **decision doc** (Context / Decision Elements / Options / Selection) in the node's `decisions/` directory, a sanctioned artifact that owns no EARS. The test looks forward from the landed state, not back at how hard the call was: a choice that reads as obvious or native once it lands needs neither a doc nor a row, and most decisions worth recording stay a row in the LLD's Decisions & Alternatives table. The template is at `plugins/linked-intent-dev/skills/linked-intent-dev/references/decision-doc-template.md`. When drafting or revising the HLD, the agent also **elicits tenets**: it probes for decisions that could reasonably go more than one acceptable way, asks the user which way to lean, and records each as a one-line tie-breaker in the HLD's `## Tenets` section, ordered by priority so the higher one wins a conflict. The discriminating test the agent applies is the **defensible opposite** — a candidate qualifies as a tenet only if its reverse is a choice a different project could reasonably make; if the opposite is absurd it is a platitude and is dropped. A tenet is edge detection for choices no spec will anticipate; the HLD phase is where project-wide preference belongs, so elicitation happens here rather than being deferred to the point where the agent is already mid-decision. Tenets are not exhaustive — the agent surfaces the few load-bearing ones it can see and invites more, rather than interrogating the user for a complete set.
2. **LLD check or draft** — does a leaf LLD exist for the intent component being changed? If not, draft one before downstream work. The design layer is a recursive tree, and "HLD" and "LLD" are roles by position: the root is the HLD, leaves are the LLDs that own EARS, and a component with enough internal depth to outgrow one doc is promoted to a sub-HLD (HLD-shaped for its subtree, owning no EARS) with child components beneath it. Depth-2 — one HLD over a flat set of leaf LLDs — is the default; nesting is a triggered exception taken only when a component outgrows one doc, so a single large LLD is a candidate for promotion to a sub-HLD rather than automatically a smell. In complex projects multiple LLDs may look semantically relevant; the skill helps the user select the correct one by surfacing candidates and their scopes rather than silently picking. If an LLD exists, confirm coherence with the change and update as needed. After drafting or substantially revising an LLD, the agent runs an **LLD-level edge-case probe** — a list of "what happens when..." questions pointed at *this LLD's own gaps*: missing state transitions, unstated invariants, unspecified API error shapes, ordering assumptions inside the component. Cross-component interactions and cross-spec ambiguities are the target of Phase 4, not here. When a subagent is available the probe is delegated to it for cleaner, less-biased coverage. The user triages the gap list and decides which gaps to fix in the LLD vs. defer as open questions.
3. **EARS spec draft or update** — every LLD change produces a corresponding EARS update (new specs, revised specs, or deleted specs). Spec IDs are stable; revisions mutate text, not IDs, unless scope genuinely changes. Deleted IDs are not reused — per *docs carry current intent*, and git preserves the history. After drafting or revising specs, the agent runs **post-draft consistency verification**:
   - **Coverage** — are there behaviors described in the LLD that have no corresponding EARS spec?
   - **Contradiction** — do any specs say different things about the same behavior?
   - **Implicit scoping** — are any specs phrased as universal when they actually apply only to one context? When the current change adds a new mode or variant, audit sibling specs for scope that was implicit when only one variant existed (see `ears-syntax.md § Scope Disambiguation` for the full litmus).
   The agent presents a brief consistency report alongside the specs; the user resolves issues before approval.
4. **Intent-narrowing edge audit** — distinct from the LLD-level probe in Phase 2 in what it targets. Phase 2 looked inside one LLD for its own gaps; Phase 4 looks across LLD + specs together for cross-spec and cross-segment divergence:
   - Interactions between this LLD's specs and a sibling segment's specs (who owns what state?).
   - Specs that read cleanly in isolation but admit two different behaviors when composed with another spec in the same segment.
   - Namespace or feature-prefix ambiguity (does spec X apply to mode A, mode B, or both?).
   - Sequencing ambiguity across specs (if A and B are both required, does order matter?).
   - Places where the user's latent intent is probably narrower than what the specs literally allow.

   The skill surfaces these and asks the user to resolve them before tests are written. LID's fundamental purpose — narrowing the agent's output distribution to the user's latent intent — is carried by this step more than any other.
5. **Tests-first** — tests are written *before* the code that satisfies them, per the HLD's intent-preloading rationale. Tests carry `@spec` annotations citing the EARS IDs they verify. The skill does not proceed to code until tests exist and fail in the expected way.
6. **Code** — implementation follows. Code carries `@spec` annotations placed at the *entry point of the behavior's implementation graph* — the topmost function or module that owns the specified behavior, not every helper in its subtree. When a behavior spans multiple subsystems (e.g., UI + API + database), annotate at the entry point in each subsystem. Tests follow the same rule: annotate the test that directly exercises the spec, not every assertion. On completion, the skill runs **coherence verification** (see below).

### Coherence verification

Phase 6 ends with a two-layer coherence pass.

**Structural checks (deterministic; soft-block completion):**

1. All tests pass.
2. Every `@spec` annotation in the changed files points to a spec ID that exists in a spec file.
3. Every behavioral EARS spec cited by the LLD has at least one test citing it.
4. No spec file references a deleted spec ID (either in headers or in cross-references).

*Soft-block* means the skill will not consider the change "complete" until these pass, and surfaces the failure clearly. The user can override per the user-is-always-right tenet — this is not a CI gate or a linter, consistent with the HLD's "not a linter or validator" non-goal. The skill makes the cost visible; the user decides. When the project declares a coherence script under `## LID Tooling` in `CLAUDE.md`, these structural checks may be delegated to that script (see `docs/intent/arrow-maintenance/arrow-maintenance-design.md § Reference tooling`); without a declaration, they are performed in-prompt.

**Semantic checks (agent judgment; surfaced, do not block):**

1. Do the updated specs describe behavior consistent with the LLD?
2. Does the updated LLD match the HLD's architecture?

The agent re-reads each adjacent level of the arrow for the changed segment and produces a short narrative report: for each spec/LLD/HLD pair, either "consistent" with a one-line justification or "needs review" with a specific point of tension. Semantic findings are surfaced for user review but do not block the change, because "match" at the prose level is judgment, not a theorem.

If the user overrides a phase ("skip EARS here", "skip tests for this change"), the skill warns about the drift risk and honors the override. The user is always right; the skill's job is to make the cost visible, not to block.

### Cascade discipline

**Cascade** is this: when a change is made at one level of the arrow (HLD, LLD, EARS, tests, or code), the levels *downstream* of that change are reviewed and updated in the same session so the arrow stays coherent. A spec change implies potential test and code changes; an LLD change implies potential spec/test/code changes; an HLD change implies potential LLD/spec/test/code changes. Cascade is the mechanism by which intent changes propagate to implementation without manual follow-up, and its absence is what lets drift accumulate silently.

The skill enforces cascade at arrow boundaries. *Within* one segment — one LLD and the specs, tests, and code that cite its EARS IDs — cascade is free: the agent updates downstream levels in the same session without further confirmation. *Across* segment boundaries, the skill pauses. A change whose effect crosses from one LLD's territory into another's is flagged to the user; the agent asks before propagating into the adjacent segment, because real LLDs are uneven and aggressive cross-boundary cascade propagates incoherence from under-specified regions into well-specified ones.

An arrow segment is the territory owned by one *leaf* LLD. Boundaries are defined by the leaf prefix — the full root-to-leaf path identifying that segment: specs sharing the leaf prefix are in the same segment; specs whose path diverges at any earlier point belong to a different segment. This makes the boundary check a prefix comparison rather than a structural analysis. When two leaves would naturally collide on a path prefix (two unrelated segments both named, say, `USER`), the skill asks the user to disambiguate the position rather than silently coalescing them.

**Cascade and uncommitted work.** When cascade would touch files the user has uncommitted changes in, the skill warns with a description of the intended changes and proceeds only after confirmation. It does not silently edit over pending work.

**Cascade and inconsistent arrows.** Arrows are often inconsistent — mid-transition aborts, overlapping scoped arrows, partial cascades from prior sessions. When the skill notices an inconsistency it surfaces it with a description of what it found. Resolving inconsistency is a userland decision, assisted by the agent; the skill does not auto-repair. The `arrow-maintenance` overlay is where systematic inconsistency-hunting lives — this skill only flags what it notices along the way.

**HLD-originating cascade.** Changes that start at the HLD level fan out across *every* segment of the arrow by construction — an HLD change is a new architectural stance that each LLD has to be reviewed against. In that case "within-segment free, across-segment pauses" cannot apply uniformly; the skill walks the affected LLDs in turn, pausing at each segment to confirm the change lands cleanly before cascading to that segment's specs, tests, and code. The user sees one pause per affected segment, not one grand pause at the start.

**Lifecycle events.** When a cascade implies a split, merge, or rename of a segment (for example, an HLD change that dissolves a segment's boundary with another), the skill defers to the mechanics described in the `arrow-maintenance` LLD's Lifecycle Events section rather than re-specifying them here. Lifecycle events are first-class there; this skill recognizes them and hands off.

### Bug fixes

Bug fixes are not a special case. They walk the arrow like any other change: find where the behavior diverged from intent, determine whether intent needs to change, is already expressed but wrong, or was never expressed at all, and cascade from there. Fixing code without walking the arrow is a bypass — the skill warns but does not block, per the user-is-always-right tenet.

### Brownfield LLD content

LLDs for reverse-engineered components start with incomplete or inferred content. They use the **same template and same section structure** as greenfield LLDs — there is no separate brownfield LLD format. What varies is the content's starting state:

- **Decisions & Alternatives** table entries carry `[inferred]` in the Rationale column when a decision was observed in code rather than authored by the user. As the user confirms or refutes the inference in subsequent sessions, the `[inferred]` marker is removed and the rationale is written out, or the decision is revised.
- **Open Questions & Future Decisions** holds observed-but-unexplained behaviors and technical debt discovered during reconnaissance. These migrate out (into Decisions, into specs, or into a planned remediation) as the user engages with the code.
- **Major sections** may describe current state alongside intended behavior when the two differ; flag the divergence explicitly rather than pretending the code matches intent.

As a brownfield LLD matures through normal LID cascades — each change triggers the skill's phased workflow — inferred content becomes authored content. No migration command is needed and no "graduation" step is triggered; the LLD simply evolves in place under the standard cascade discipline. This matches the HLD-level convention for Scoped LID (HLD sections may be marked "not yet specified" and filled in over time).

## Phase-Requirement Policy

The skill enforces this phase set per mode. This table is the reference the `linked-intent-dev` skill uses when prompting for missing phases:

| Phase | Full LID | Scoped LID |
|---|---|---|
| HLD | Required, all standard HLD sections filled | Required, sections may be marked "not yet specified" |
| LLD per leaf intent component (a component with internal depth becomes a sub-HLD with child components rather than one LLD) | Required for all components | Required for components in scope only |
| EARS spec file per behavioral component | Required | Required (linkage is not optional) |
| Tests before code | Required | Required (TDD is not optional) |
| `@spec` annotations on code and tests | Required | Required (linkage is not optional) |

## `index.yaml` Updates during Changes

When a change is made inside an arrow segment (phases 2–6 above), this skill updates the segment's entry in `docs/arrows/index.yaml` (if the overlay is present) — status transitions, `next`, `drift`, `audited_sha` on completion. The schema is defined authoritatively in `docs/intent/arrow-maintenance/arrow-maintenance-design.md`; this skill writes to fields already specified there. When the two disagree, the arrow-maintenance LLD is the authority.

Authority between artifacts: `index.yaml` holds the source of truth for per-segment status and timestamps. The per-segment arrow doc's References and Spec Coverage sections are *derived views* — they are regenerated from source scans (grep for `@spec`, file existence checks, eval-citation checks) during audit, not hand-maintained in ways that can diverge from source.

## Decisions & Alternatives

| Decision | Chosen | Alternatives Considered | Rationale |
|---|---|---|---|
| Arrow boundary definition | Leaf prefix — the full root-to-leaf path of the owning leaf LLD's segment | LLD file identity; directory membership; manual tagging | Prefix comparison is cheap and already present in the path-concatenated ID. The leaf prefix delimits exactly one leaf LLD's territory even in a nested tree. LLD file identity couples boundaries to file organization; manual tagging is surface growth. |
| Project-tenet capture | Dedicated `## Tenets` HLD section, elicited in Phase 1 | Fold tenets into Key Design Decisions as an entry type; guidance-only note with no fixed heading | A tenet governs a *future, unanticipated* choice; a Key Design Decision records a *past* one — conflating them forfeits the forward-looking edge-detection value that is the whole point of a tenet. A fixed, greppable heading makes tenets an arrow anchor; a guidance-only note is weaker for navigation. Elicitation rides on the existing HLD phase, so no new surface is added. |
| Bug-fix workflow | Walk the arrow like any other change | Short-circuit to coherence check; dedicated bug-fix path | Bugs are intent gaps — either the spec was wrong or never existed. Treating them as a special case lets the agent "fix" code while the upstream intent stays unexpressed, which is exactly the rot LID is designed to prevent. |
| Phase override by user | Allowed, with warning | Blocked; allowed silently | The user is always right; the skill's job is to make the cost visible. Blocking would compete with the agent's authority to judge local context. Silent allow forfeits the drift signal. |

## Open Questions & Future Decisions

### Deferred to implementation

1. ~~**Scope declaration format**~~ — *Resolved*. Declared in `## LID Scope` section of `CLAUDE.md` with bulleted include/exclude globs; section omitted when mode is Full. See the Scope declaration format section above. Original candidates (dedicated `docs/scope.yaml`, inferred from `docs/intent/`) were rejected because CLAUDE.md is already read unconditionally and the section-in-a-file form matches the `## LID` block precedent.
2. **HLD template file format** — referenced by the `update-lid` skill for bootstraps in either mode. The standard section list (problem / approach / users / goals-and-non-goals / tenets / system design / key decisions / success metrics / FAQ / references) is the intended baseline; exact headings and commentary prose to be drafted during implementation.
3. **Description-optimization cadence** — when is `run_loop.py` run against the `linked-intent-dev` skill's description to keep trigger accuracy calibrated. Candidates: every skill-body change; periodic; on-demand only.
4. **Cross-scope change surfacing UX** — when a change touches multiple arrow boundaries, does the skill list all affected arrows up front, walk one at a time, or produce a structured confirmation? To be refined after running the skill on real changes.

## References

- `docs/intent/linked-intent-dev/linked-intent-dev-design.md` — parent `LID` sub-HLD; plugin-level concerns (mode detection, spec ID format, the LID-on-LID linkage inversion, eval metadata schema) live there.
- `docs/high-level-design.md` — the HLD this LLD traces from.
- `docs/intent/linked-intent-dev/update-lid/update-lid-design.md` — sibling leaf LLD covering the `update-lid` skill.
- `docs/intent/linked-intent-dev/lid-coach/lid-coach-design.md` — sibling leaf LLD covering the `lid-coach` skill.
- `plugins/linked-intent-dev/skills/linked-intent-dev/references/ears-syntax.md` — EARS syntax reference.
- `plugins/linked-intent-dev/skills/linked-intent-dev/references/lld-templates.md` — LLD structure template.
