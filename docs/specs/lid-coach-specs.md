# lid-coach specs

**LLD**: docs/llds/lid-coach.md
**Implementing artifacts**:
- plugins/linked-intent-dev/skills/lid-coach/SKILL.md

Status markers: `[x]` implemented · `[ ]` active gap · `[D]` deferred

---

## Invocation

- `[ ]` **LID-COACH-001**: When the user invokes `/lid-coach`, the system SHALL dispatch to the `lid-coach` skill.
- `[ ]` **LID-COACH-002**: The `lid-coach` skill SHALL declare `disable-model-invocation: true` so the skill is reachable only via explicit `/lid-coach` invocation and is not auto-triggered by model interpretation of ambient prompts.

## State Dispatch

- `[ ]` **LID-COACH-003**: When invoked on a project that has no `CLAUDE.md` AND has no LID-shaped artifacts — that is, no `docs/high-level-design.md`, no `.md` files in `docs/llds/` (other than `README.md` or `index.md`), no `.md` files in `docs/specs/` (other than `README.md` or `index.md`), and no `docs/arrows/index.yaml` — the system SHALL inform the user that the project is not LID-configured, recommend running `/update-lid`, and SHALL NOT proceed with coaching.
- `[ ]` **LID-COACH-004**: When invoked on a project that has LID directives but is missing one or more of the required directories (`docs/llds/`, `docs/specs/`) or `docs/high-level-design.md`, the system SHALL proceed with a reduced review of what does exist, surface each missing piece as a high-priority finding, and recommend `/update-lid` to reconcile.
- `[ ]` **LID-COACH-005**: When invoked on a Scoped-mode project that has a missing or empty `## LID Scope` section in `CLAUDE.md`, the system SHALL surface the misconfiguration as a high-priority finding and SHALL perform a conservative project-wide review that treats all paths as in-scope.
- `[ ]` **LID-COACH-006**: When invoked on a project where `docs/arrows/index.yaml` exists but cannot be parsed, the system SHALL flag the corruption to the user before beginning principle review and SHALL offer either to proceed with a reduced review that treats the overlay as absent or to pause for the user to repair the overlay.
- `[ ]` **LID-COACH-007**: When invoked on a project that has LID directives, a valid `## LID Mode:` marker, all standard directories (`docs/llds/`, `docs/specs/`, `docs/high-level-design.md`) present, and — where mode is Scoped — a well-formed `## LID Scope` section, the system SHALL proceed with a full review regardless of whether those files have been populated with content.

## Inputs

- `[ ]` **LID-COACH-008**: During a review, the system SHALL read `CLAUDE.md` and extract mode, scope declaration (if Scoped), and directive-block coherence with the current template as review inputs.
- `[ ]` **LID-COACH-009**: During a review, the system SHALL read `docs/high-level-design.md` and assess section coverage against the HLD template and evidence of active intent versus boilerplate.
- `[ ]` **LID-COACH-010**: During a review, the system SHALL read every file in `docs/llds/` and assess granularity and alignment with the HLD's architecture.
- `[ ]` **LID-COACH-011**: During a review, the system SHALL read every file in `docs/specs/` and assess EARS format compliance, scope-disambiguation hygiene, ID uniqueness and namespacing, and status-marker usage.
- `[ ]` **LID-COACH-012**: During a review, the system SHALL sample code and test files to inspect `@spec` annotation patterns — placement relative to implementation-graph entry points and coverage of behavioral specs — without requiring exhaustive reading of the codebase.
- `[ ]` **LID-COACH-013**: Where the arrow-maintenance overlay is present, the system SHALL additionally read `docs/arrows/index.yaml` and per-segment arrow docs as review inputs.

## Principle Body

- `[ ]` **LID-COACH-014**: The coach's principle content (each LID principle paired with drift/audit signals and a *why-it-matters* layer) SHALL be embedded directly in the coach's `SKILL.md` body rather than split into a separate `references/` file, for as long as total SKILL.md length stays within the skill-creator progressive-disclosure budget. A separate `references/` directory MAY exist for content that is genuinely load-on-demand (e.g., the `lid-faq.md` conversational-guidance resource); the principle body specifically belongs in `SKILL.md` because it is needed for every review.
- `[ ]` **LID-COACH-015**: The embedded principle content SHALL be a downstream artifact of LID's own `docs/high-level-design.md` — sourced from its Approach sections, Tenets, Goals, and key Design Decisions — and SHALL participate in LID-on-LID cascade when the HLD changes.

## Review Dimensions

- `[ ]` **LID-COACH-016**: During a review, the system SHALL assess arrow completeness — whether each phase of the canonical arrow (HLD, LLD, EARS, tests, code) exists for components in scope — and report gaps.
- `[ ]` **LID-COACH-017**: During a review, the system SHALL assess linkage hygiene — whether `@spec` annotations point to specs that exist and, in LID-on-LID projects, whether spec files cite their implementing artifacts — and report drift.
- `[ ]` **LID-COACH-018**: During a review, the system SHALL assess LLD granularity — whether LLDs are authored one per intent component, or are lumped (one LLD covering many components) or over-fragmented (many LLDs covering one component) — and report misalignment.
- `[ ]` **LID-COACH-019**: During a review, the system SHALL assess HLD discipline — whether the HLD contains implementation-level detail (schemas, function signatures, API shapes) that belongs in LLDs — and report bloat.
- `[ ]` **LID-COACH-020**: During a review, the system SHALL assess LLD sufficiency — whether each LLD closes enough of the solution space that two reasonable agents reading it would arrive at compatible implementations — and report under-specified or over-specified LLDs.
- `[ ]` **LID-COACH-021**: During a review, the system SHALL assess effective intent-tree alignment — whether specs trace to identifiable intent components, whether `{FEATURE}` prefixes correspond to concepts in the HLD or an LLD, and whether there are behaviors described in LLDs that lack corresponding specs — and report misalignment.
- `[ ]` **LID-COACH-022**: During a review, the system SHALL assess semantic legibility — whether names, types, and module structure echo the specs and LLDs — and report drift where code surface disagrees with intent.
- `[ ]` **LID-COACH-023**: During a review, the system SHALL assess the *docs carry current intent* discipline across *all* LID doc types (HLD, LLDs, specs) using the fresh-author test, watching for three residues — (1) change-narration ("this was X before, now it's Y", "we will eventually…" planning-ahead text, `[obsolete]`-marked specs kept alongside replacements, changelog-style append-only sections); (2) in-conversation-only meaning; and (3) conversational fossils (answers or rebuttals that exist only because a past discussion raised the question, even when cleanly present-tense) — and report them. The system SHALL apply the locality discriminator for residue (3): a rejected alternative and its rationale in an LLD's Decisions & Alternatives table is present intent and SHALL NOT be reported, whereas the same content as a body-prose aside SHALL be reported.
- `[ ]` **LID-COACH-024**: During a review, the system SHALL assess scope disambiguation — whether ubiquitous specs are truly ubiquitous or are scoped-but-phrased-universally — and report implicit-scoping risks.
- `[ ]` **LID-COACH-025**: During a review, the system SHALL assess tests-first evidence — whether behavioral specs have tests citing them, and whether tests read as intent documents (outside-in) or as post-hoc verification (inside-out) — and report gaps.
- `[ ]` **LID-COACH-026**: During a review, the system SHALL assess cascade health — evidence of recent within-segment cascades versus obvious stale segments — and report stale segments.
- `[ ]` **LID-COACH-027**: During a review, the system SHALL assess brownfield inferred content — presence and age of `[inferred]` markers in LLD Decisions & Alternatives tables — and recommend the user triage stale markers (confirm and remove, or refute and revise).
- `[ ]` **LID-COACH-028**: During a review, the system SHALL assess arrow shape — whether the project's arrow matches the canonical `HLD → LLD → EARS → Tests → Code` ordering or deviates (extra phases inserted, phases collapsed) — and where deviation is detected, report it and reason with the user about implications rather than assuming canonical shape.
- `[ ]` **LID-COACH-029**: During a review, the system SHALL assess mode fit — whether the declared mode (Full or Scoped) matches project reality — and recommend a mode transition where warranted.

## Mode Interaction

- `[ ]` **LID-COACH-030**: When mode is Full, the review SHALL cover the whole project.
- `[ ]` **LID-COACH-031**: When mode is Scoped, the review SHALL cover only paths matching the declared `## LID Scope` include patterns (less any declared excludes), and out-of-scope paths SHALL be listed explicitly in the report rather than silently skipped.
- `[ ]` **LID-COACH-032**: The system SHALL trust the project's declared mode and scope — paths deliberately excluded by scope SHALL NOT be reported as gaps, and HLD sections marked "not yet specified" in Scoped mode SHALL NOT be reported as findings.

## Report Structure

- `[ ]` **LID-COACH-033**: At the end of a review, the system SHALL produce a single inline report, structured in this order: (1) executive summary (posture line, scorecard, one-sentence headline), (2) findings inventory (one line per finding — priority, title, principle cited — with no detailed paragraphs), (3) what was audited, (4) out-of-scope note when mode is Scoped (omitted in Full), and (5) an offer-to-help line. The offer-to-help SHALL invite the user to direct review follow-up (walk through findings, focus on a theme or priority, dig into a specific finding) AND, as a separate sentence, hint that the coach can also help with broader LID-usage questions (multi-repo setups, where PRDs fit, mode transitions, splitting a segment that grew too large). The two pathways — review detail and LID-usage help — SHALL both be discoverable from the report. The report SHALL NOT render detailed finding paragraphs. **Subsequent user-driven turns** render detailed finding paragraphs (for the requested subset), a working session on a specific finding, a concrete next-step list, or conversational LID-usage help (per LID-COACH-052) — without re-rendering the inventory, audit, or executive summary.
- `[ ]` **LID-COACH-034**: The executive summary SHALL open with a **categorical posture line** (e.g., "Healthy, with accumulation drift" / "Drifting linkage" / "Bootstrapping"), followed by a **scorecard** rendered as a short bulleted list (one line per dimension) using ✓/⚠/✗ markers and short word labels across principle clusters (e.g., *Linkage*, *Cascade*, *Mutation hygiene*, *Mode fit*, *HLD discipline*, *LLD quality*), followed by a **one-sentence headline** naming what is working in the project and the single most valuable next step. The posture line and scorecard SHALL NOT take the form of a numeric score, a letter grade, or a point total. The scorecard is user-facing and is referred to as a "scorecard" in the report — "dimensional strip" is internal vocabulary and SHALL NOT appear in user-facing output.
- `[ ]` **LID-COACH-035**: When detailed findings are rendered in user-driven turns following the report, each finding SHALL be rendered as one paragraph per finding (not a sub-bullet form with labeled Observation/Principle/Action fields), ordered high → medium → low priority by default. Each finding paragraph SHALL weave: (a) a concrete observation, naming files or lines where useful; (b) a citation of the LID principle the finding relates to, cited by name with a plain-English gloss appended inline (e.g., "*Mutation, not accumulation* — docs reflect current intent; git preserves history"); (c) a sentence or two explaining **why the drift matters** — what gets harder if it is not addressed, or what gets more reliable if it is — drawing from the principle's motivation grounded in the user's project; (d) a closing concrete recommended action. Bullet lists within a finding are permitted only for genuinely parallel items (e.g., "the following four files could be removed"), not as the finding's structural backbone.
- `[ ]` **LID-COACH-036**: When a finding's recommended follow-up is structural in character (orphans, reverse orphans, adjacent-level drift enumeration), the recommended action SHALL point the user at `/arrow-maintenance` rather than attempt to enumerate the structural instances from the coach's sampled read.
- `[ ]` **LID-COACH-037**: The "what was audited" section SHALL name the files read, the areas sampled, and the depth of sampling, to allow the user to judge breadth. This section MAY include quantitative signals about scope of inspection (e.g., counts of `@spec` references, LLDs reviewed, arrow segments sampled, files read).
- `[ ]` **LID-COACH-038**: The system SHALL NOT persist the report to disk by default; persistence happens only when the user explicitly requests a saved report.

## Advisory Posture

- `[ ]` **LID-COACH-039**: The system SHALL NOT edit any project files as part of a coach invocation. Recommendations SHALL be surfaced in the report for the user to act on.
- `[ ]` **LID-COACH-040**: When a recommendation implies a configuration change, the recommended action SHALL point at `/update-lid` — the single command that bootstraps unconfigured projects, reconciles drift on configured ones, and runs mode transitions, dispatching on state. The coach SHALL NOT attempt to reconcile configuration itself. When the user appears to be starting a code change on a fresh project, the coach MAY additionally point at `/linked-intent-dev` (with a description of what to build), since the workflow's Phase 1 will call `/update-lid`'s bootstrap branch as a sub-step.

## Arrow-Maintenance Relationship

- `[ ]` **LID-COACH-041**: The coach's review SHALL NOT duplicate `arrow-maintenance`'s deterministic structural audit (orphans, reverse orphans, adjacent-level coherence between arrow levels, `index.yaml` drift); structural enumeration is delegated to `/arrow-maintenance` via recommended actions.
- `[ ]` **LID-COACH-042**: The coach SHALL NOT require the arrow-maintenance overlay to be installed in order to run.

## Voice and Tone

- `[ ]` **LID-COACH-043**: The report SHALL be written in a coach voice — forward-looking, framing drift as opportunity to tighten rather than as violation. The executive summary SHALL acknowledge what is working in the project before naming the headline next step, and findings SHALL use constructive phrasing ("consider", "try", "you could") in preference to evaluative phrasing ("violation", "failure", "wrong", "broken").
- `[ ]` **LID-COACH-044**: Every citation of a LID principle in the report SHALL pair the principle name with a short plain-English gloss inline, so that a reader who is new to LID can follow the finding without needing to consult a glossary. Citing a principle by name alone is insufficient.

## Lenient Dispatch on LID-Shaped Projects

- `[ ]` **LID-COACH-045**: When invoked on a project whose `CLAUDE.md` is absent or missing LID directives, and which contains at least one LID-shaped artifact — a `docs/high-level-design.md`, a `.md` file in `docs/llds/` other than `README.md`/`index.md`, a `.md` file in `docs/specs/` other than `README.md`/`index.md`, or a `docs/arrows/index.yaml` — the system SHALL proceed with a review anchored on the existing artifacts, default to Full mode, and surface the missing (or precursor-named) CLAUDE.md directives as a high-priority finding recommending `/update-lid` to reconcile. The system SHALL NOT refuse coaching in this case.
- `[ ]` **LID-COACH-046**: When dispatching under LID-COACH-045, the system SHALL recognize that the project may be running a precursor or dialect name for LID (e.g., "design-driven-dev") in its CLAUDE.md and SHALL treat the structural arrow (HLD, LLDs, specs, overlay) as the authoritative signal that the project is LID-shaped, not the directive string.

## Teach While Correcting

- `[ ]` **LID-COACH-047**: The embedded principle body in the skill SHALL carry, for each principle, both (a) a description of the principle and what drift from it looks like in practice and (b) an explanation of what the principle protects against — the cost of leaving the drift in place over time. Findings in the report draw on the second layer to answer "why this matters" inline.

## Sampling Strategy

- `[ ]` **LID-COACH-048**: When the project under review has more than 15 LLDs OR more than 200 files carrying `@spec` annotations, the coach SHALL sample at least one complete arrow path per arrow segment — HLD section → LLD → at least one EARS spec → at least one test citing that spec → at least one code file citing that spec — to verify each arrow is end-to-end coherent. Below those thresholds, sampling depth is left to agent judgment.
- `[ ]` **LID-COACH-049**: When `docs/arrows/index.yaml` is present, the coach SHALL read it as a primary guide for arrow-segment selection and SHALL incorporate its `status`, `audited`, `audited_sha`, `next`, and `drift` fields into relevant findings (cascade health, arrow completeness, segment-level drift). A segment whose `drift` field has been non-null for many sessions is itself a finding signal.

## Quantitative Signals

- `[ ]` **LID-COACH-050**: Quantitative measurements about the project's scope of inspection (counts of `@spec` references, LLDs reviewed, arrow segments sampled, files read) SHALL be welcome in the "what was audited" section. Findings SHALL NOT use numbers as grades or scores (e.g., "Linkage hygiene: 87/100" is forbidden), though findings MAY cite specific counts when the count is the observation itself (e.g., "the spec file has 3 IDs in the legacy 1000-block alongside semantic-naming IDs").

## Cold-Read Pass

- `[ ]` **LID-COACH-051**: Beyond the dimension-by-dimension review, the coach SHALL perform a **cold-read pass** through every LID doc in scope — reading each doc as if no conversation context is available — and surface content that is unclear, ambiguous, or evidently dependent on context not on the page. This pass is the detection mechanism for the residues of the *docs carry current intent* tenet that have no telltale surface form — meaning that only resolves for someone who was in the conversation, and conversational fossils: future sessions open without the conversation that produced the doc, so anything load-bearing that lived only in chat or in the author's head is unreachable. Unclear writing is either lost implicit context or writing that could be tighter; either way it is worth surfacing. The skill SHALL NOT reduce this pass to grepping for specific phrases ("obviously", "of course", "as discussed"), because a checklist approach trains the agent to pattern-match and miss the deeper pattern.

## Conversational Guidance

- `[ ]` **LID-COACH-052**: The coach SHALL carry a load-on-demand FAQ at `references/lid-faq.md` covering common LID adoption patterns (multi-repo organization, PRDs upstream of HLD, mode-fit changes, the upstream-ownership reframe, arrow-segment splitting). When the user invokes `/lid-coach` with a question about how to use LID for a specific situation rather than a request for a project review, the coach SHALL load the FAQ as its knowledge substrate and engage the user conversationally instead of producing the review report. The FAQ SHALL describe the *shape* of good answers without prescribing specific tools or filesystem layouts.
