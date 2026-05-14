# LLD: lid-coach Skill

## Context and Design Philosophy

The `lid-coach` skill is one of three skills shipped by the `linked-intent-dev` plugin. It is described in its own Low-Level Design rather than alongside its sibling skills because the coach reasons from a substantial body of LID theory — a curated distillation of LID's HLD principles paired with audit signals and *why-it-matters* explanations — and that body would dominate any LLD it shared. Per the principle of *one LLD per intent component* the plugin's pure-prose workflow skill and `update-lid` are described in `docs/llds/linked-intent-dev.md`; this LLD is the home of the coach.

Plugin-level concerns (mode detection, spec ID format, the LID-on-LID linkage inversion, `index.yaml` update mechanics, eval metadata schema) live in the sibling LLD. This document describes them by reference rather than re-specifying them.

This LLD describes intent; the `SKILL.md` under `plugins/linked-intent-dev/skills/lid-coach/` is the compiled outcome. Terms like *arrow*, *segment*, *drift*, *coherence*, and *cascade* are defined in the HLD's Glossary section.

**A note on actors.** "The skill" refers to the prose guidance contained in the coach's `SKILL.md`. The skill does not act on its own — it is content the agent consults. When this LLD says "the skill surfaces X" or "the skill warns," the mechanism is: the agent, after consulting the skill, performs the surfacing or warning in the assistant turn it produces.

Two design constraints shape the coach:

- **Advisory only.** The coach reads, reasons, and reports. It never edits project files. Recommendations are surfaced; the user applies them. Silent edits would bypass user review on exactly the decisions where review matters most.
- **Coach voice, not grader voice.** The report's tone is load-bearing — the skill's value depends on the user feeling guided, not graded. Findings are forward-looking; principles are taught alongside corrections.

## Skill Structure

The coach lives at `plugins/linked-intent-dev/skills/lid-coach/` with this shape:

- `SKILL.md` — principle content embedded directly (description, *why it matters*, audit signal per principle), dispatch table, review flow, scorecard format, advisory posture, conversational-guidance pointer. The principle body stays in `SKILL.md` because it's needed on every review; if total SKILL.md size approaches the skill-creator progressive-disclosure budget (~500 lines), Open Question 1 covers extracting it.
- `references/lid-faq.md` — load-on-demand conversational guidance covering common LID adoption patterns (multi-repo organization, PRDs upstream of HLD, mode-fit changes, the upstream-ownership reframe, arrow-segment splitting). Read by the coach when the user invokes `/lid-coach` with an adoption / pattern question rather than a project review.
- `evals/evals.json` — per the eval-metadata convention specified in `docs/llds/linked-intent-dev.md § Eval Metadata Conventions`.

The skill is directly invokable as `/lid-coach` — no command stub is needed. Per Claude Code's skills model, a skill named `lid-coach` is reachable as `/lid-coach` from the slash menu, and a separate command file would be shadowed by the skill anyway.

## Intent

Review a project's current LID usage against LID's principles and produce a prioritized report of recommendations for getting more out of the methodology. The posture is advisory, not corrective: the project works; the coach identifies where usage is drifting from principle or leaving value on the table. The coach is distinct from both sibling skills:

- `update-lid` reconciles *configuration* (directory layout, CLAUDE.md directives, mode marker) against a template. Its judgments are deterministic.
- `arrow-maintenance` (when the overlay is installed) performs deterministic *structural* audit — orphans, reverse orphans, coherence between adjacent arrow levels, `index.yaml` drift.
- `lid-coach` performs interpretive *principle-level* review — "is the LLD at the right granularity?", "are EARS specs phrased universally when they should be scoped?", "are `@spec` annotations at implementation-graph entry points or scattered through helpers?"

The three are complementary and non-duplicative: they look at different layers of the same project. A coach finding may overlap *in subject* with something `arrow-maintenance` would enumerate more precisely (e.g., the coach notices a reverse-orphan pattern during sampling; arrow-maintenance would enumerate every instance). In that case the coach surfaces the pattern-level finding and recommends `/arrow-maintenance` for the deterministic enumeration — it does not attempt to duplicate the overlay's structural audit from a sample.

## Invocation

The skill is invoked as `/lid-coach`. There is no alias. Auto-invocation is disabled (`disable-model-invocation: true` in the SKILL.md frontmatter) — a principle-based review reads a broad sample of the project's LID artifacts and is too expensive to run opportunistically. The user opts in explicitly.

## Dispatch

On invocation, the skill inspects the project and selects one of these actions:

| Detected state | Action |
|---|---|
| No `CLAUDE.md` AND no LID-shaped artifacts in the project (no `docs/high-level-design.md`, no LLD files in `docs/llds/`, no spec files in `docs/specs/`, no `docs/arrows/index.yaml`) | Inform the user the project is not LID-configured and recommend `/update-lid`. Do not proceed with coaching. |
| `CLAUDE.md` missing LID directives **but** the project has at least one LID-shaped artifact present | Proceed with review anchored on the existing artifacts (default Full mode). Surface the missing directives as a high-priority finding and recommend `/update-lid` to reconcile. Do **not** refuse — a project with a populated arrow is LID-shaped regardless of whether CLAUDE.md has caught up with the directive naming. |
| LID directives present, required directories missing | Proceed with a reduced review of what does exist; surface the missing pieces as high-priority findings and recommend `/update-lid` to reconcile. |
| Scoped mode with missing or empty `## LID Scope` | Surface as a high-priority finding; perform a conservative project-wide review (matching the `linked-intent-dev` skill's misconfiguration fallback). |
| `docs/arrows/index.yaml` present but malformed / unparseable | Flag to the user before any principle review, since the overlay is a primary signal source; offer to proceed with a reduced review that treats the overlay as absent, or pause for the user to repair the overlay. |
| Fully configured | Proceed with full review. |

**Detection threshold for "LID-shaped artifacts present."** The coach treats the project as LID-shaped when any of these is true:

- `docs/high-level-design.md` exists with non-trivial content (more than a stub).
- `docs/llds/` contains at least one `.md` file other than `README.md` or `index.md`.
- `docs/specs/` contains at least one `.md` file other than `README.md` or `index.md`.
- `docs/arrows/index.yaml` exists.

The threshold is deliberately lenient. A richly-populated arrow overlay is the strongest possible signal a project is "doing LID" — if the directive block in `CLAUDE.md` is missing or uses a precursor name, that is *drift to be surfaced*, not a reason to refuse coaching. Refusing to coach a visibly LID-shaped project is a false negative the coach was specifically designed to avoid.

**"Fully configured"** for the last dispatch row means: LID directives present in `CLAUDE.md`, a valid `## LID Mode:` marker, and the standard directories (`docs/llds/`, `docs/specs/`, `docs/high-level-design.md`) all exist. Content completeness (how much has been authored) is a *review dimension*, not a dispatch condition — an empty-but-present HLD or LLD directory does not block coaching; it becomes a finding.

Dispatching to `/update-lid` rather than silently bootstrapping preserves the invocation boundary between skills — `lid-coach` reads and reasons, it does not configure.

## Inputs

The skill reads the project's LID artifacts to build its review:

- `CLAUDE.md` — mode marker, scope declaration (if Scoped), directive-block coherence with the current template.
- `docs/high-level-design.md` — presence, section coverage against the HLD template, evidence of active intent versus boilerplate prose.
- `docs/llds/*.md` — count and granularity relative to the project's structure (one LLD per intent component?), alignment with HLD architecture.
- `docs/specs/*.md` — EARS format compliance, scope-disambiguation hygiene, ID uniqueness and namespacing, status-marker usage.
- Code and tests — sampled review of `@spec` annotations (entry-point placement, coverage) and tests-first evidence for behavioral specs.
- `docs/arrows/index.yaml` and arrow docs — when the overlay is installed, the overlay's own status signals feed findings.

The skill does not require exhaustive reading of the code tree. What matters is whether the *patterns* align with LID principles, not every individual file. Sampling strategy follows two rules:

1. **Arrow-path sampling for large projects.** When the project has more than 15 LLDs, or more than 200 files carrying `@spec` annotations, the coach samples at least one complete arrow path per arrow segment — HLD section → LLD → at least one EARS spec → at least one test citing that spec → at least one code file citing that spec. End-to-end sampling catches drift that single-level inspection misses (specs that read well but have no implementation; code that exists for behaviors that have no spec; LLD claims contradicted by the code that's supposed to satisfy them). Below those thresholds, sampling depth is judgment.
2. **`docs/arrows/index.yaml` is a high-signal guide when present.** The arrow-maintenance overlay's index enumerates segments and carries `status`, `audited`, `audited_sha`, `next`, and `drift` fields per segment — direct evidence of what the project itself thinks is in flight. Use it to pick which segments to arrow-path-sample, and to inform cascade-health and arrow-completeness findings (e.g., a segment whose `drift` field has been non-null for many sessions is itself a finding). When the overlay is installed, the index is read first; segment selection follows from there.

The coach trusts the project's declared mode and scope rather than second-guessing them. When mode is Scoped, paths outside scope are not reviewed and not treated as gaps; when HLD sections are marked "not yet specified" in Scoped mode, that is an intentional choice, not a finding. The coach's job is to surface drift *relative to the declared intent*, not to nag about shape choices the project has deliberately made.

## Principle body

The coach's principle content — a curated distillation of LID's own HLD pairing each principle (from the Approach sections, Tenets, Goals, and key Design Decisions) with *audit signals* and *why-it-matters* explanations — lives **embedded in the coach's `SKILL.md` body**, not in a separate reference file. Embedding is the right default because the principles are always needed during a coach invocation (unlike a phase-specific template loaded only on demand), so splitting them into `references/` would just add a file without enabling progressive disclosure.

For each principle, the embedded body carries three parts:

1. A short **description** of what the principle says.
2. A **why it matters** layer — what the principle protects against, what compounds if it is ignored. This is the layer the coach draws on when a finding needs to *teach*, not just correct. Carrying this layer at all is the difference between a coach and a checklist; without it, findings can name a principle but cannot explain why caring about it pays off.
3. An **audit signal** — what drift from the principle looks like in a real project.

The principle content travels with the plugin because LID's own HLD does not travel to installed projects; the user's `docs/high-level-design.md` is *their* project's HLD, not LID's.

The principle content is a downstream artifact of LID's HLD in the LID-on-LID arrow. Cascade from HLD changes into the coach's SKILL.md is the skill's contract with its own theory; drift between LID's HLD and the embedded principles is itself a dogfooding failure and surfaces through the standard coherence verification on HLD changes.

The embedded content is not a rule list. It is a structured set of principled lenses; the coach reasons with them, not through a checklist. The coach's report cites principles by name (e.g., "mutation, not accumulation") rather than by anchor or numeric ID — cross-reference frequency in real LID projects is low enough that formal citation stability is not worth the mechanism.

If the principle body grows beyond the skill-creator progressive-disclosure budget (roughly ~500 lines total for the SKILL.md), Open Question 1 below revisits extracting it into `references/`.

## Review dimensions

At minimum the coach addresses the dimensions below during a review. The authoritative enumeration — with audit signals, *why-it-matters* explanations, and exemplar drift patterns — is embedded in the coach's SKILL.md body; the list here is illustrative:

- **Arrow completeness** — does each phase of the arrow exist for components in scope?
- **Linkage hygiene** — do `@spec` annotations point to specs that exist? In LID-on-LID, do spec files cite their implementing artifacts?
- **LLD granularity** — are LLDs per intent component, or are they lumped (one giant LLD) or over-fragmented (dozens of tiny LLDs)?
- **HLD discipline** — is the HLD about problem, approach, and architectural rationale, or has it accumulated implementation detail that belongs in LLDs? HLD bloat is a common antipattern; a swollen HLD raises maintenance cost and obscures architecture behind specifics.
- **LLD sufficiency** — does each LLD close enough of the solution space that two reasonable agents reading it land on compatible implementations? Under-specified LLDs with unclosed solution edges are a common antipattern; tests after the fact cannot compensate. Conversely, an LLD that over-specifies crosses into code territory.
- **Effective intent-tree alignment** — do specs trace to identifiable intent components, and do the intent components trace to the HLD's architecture? Specs that exist but have no home in the intent tree, or specs whose `{FEATURE}` prefix corresponds to nothing in the HLD or LLDs, are drift signals. Missing specs for LLD-described behavior is the other side of the same misalignment.
- **Semantic legibility** — do names, types, and module structure echo the specs and LLDs, or is semantic drift evident?
- **What is currently here is the truth** — LID docs describe *current* intent, not the history of how intent evolved (accumulation side: "this was X before, now it's Y" narration, "we will eventually..." planning-ahead text, `[obsolete]`-marked specs kept alongside replacements, changelog-style append-only sections, history sections in LLDs). And docs must read **context-free** — future sessions open without the conversation that produced the doc, so anything load-bearing that lived only in chat or in the author's head is lost when the session ends. The context-free check is performed by the cold-read pass; see *Cold-read pass* below.
- **Scope disambiguation** — are ubiquitous specs truly ubiquitous, or are they scoped-but-phrased-universally?
- **Tests-first evidence** — do behavioral specs have tests citing them? Do tests read as intent documents (outside-in) or as post-hoc verification (inside-out)?
- **Cascade health** — are there obvious stale segments? Evidence of recent within-segment cascades?
- **Brownfield inferred content** — LLDs carrying `[inferred]` markers in Decisions & Alternatives that have sat unconfirmed for a long time. Flag them to the user to triage — either confirm and remove the marker, or refute and revise the decision.
- **Arrow shape** — does the project's arrow match the canonical `HLD → LLD → EARS → Tests → Code` ordering or deviates (extra phases inserted, phases collapsed)? Surface the deviation as a finding and reason with the user about implications rather than assuming canonical shape.
- **Mode fit** — whether the declared mode (Full or Scoped) matches project reality.

## Cold-read pass

Beyond the dimension-by-dimension review, the coach performs a **cold-read pass** through every LID doc in scope — reading each doc as if no conversation context is available, no memory of what was discussed, no idea what the author meant by "of course" or "as we discussed." This is the detection mechanism for the **context-free** half of the *what is currently here is the truth* tenet: future sessions open without the chat that produced the doc, so anything load-bearing that lived only in conversation or in the author's head is unreachable. The cold-read pass simulates that future session and surfaces what doesn't stand on its own.

The pass is deliberately not specified as a checklist. Reducing it to "grep for *obviously*, *of course*, *as discussed*" trains the agent to pattern-match for surface phrases and miss the deeper drift — context leaks rarely use those phrases. The directive in the SKILL.md is: read each doc cold; surface what's unclear, ambiguous, or evidently dependent on context not on the page. The unclear content is either lost implicit context (the high-value finding) or writing that could be tighter (still a valuable surface). Both are coach-shaped findings.

## Conversational mode

`/lid-coach` is also reachable when the user isn't asking for a project review but is asking how to *use* LID for a specific situation — multi-repo organization, where PRDs fit, when to switch modes, what to do when an arrow segment outgrows its boundaries, why the upstream-ownership shift feels uncomfortable. When the user's prompt is a question of that kind rather than a request for a review, the coach engages conversationally instead of producing the review report.

The knowledge substrate for conversational mode is `references/lid-faq.md` — a load-on-demand resource describing the *shape* of good answers to common adoption questions, without prescribing specific tools or filesystem layouts. The FAQ is loaded only when the user's prompt looks like an adoption / pattern / how-do-I question; it stays out of the always-loaded SKILL.md body so it doesn't pull review behavior toward FAQ topics on every run.

When a question doesn't fit any FAQ topic, the coach reasons from the principle body and from the project specifics with the user, rather than guessing.

## Mode interaction

Mode detection mechanics (CLAUDE.md `## LID Mode:` heading, fallback behavior, multiple-CLAUDE.md handling) are specified in `docs/llds/linked-intent-dev.md § Mode Detection Mechanics`. The coach uses those mechanics directly.

- **Full LID** — review spans the whole project.
- **Scoped LID** — review covers paths declared in-scope only; out-of-scope areas are explicitly listed in the report as excluded, not silently skipped. A misconfigured Scoped project (missing `## LID Scope`) surfaces that misconfiguration as a high-priority finding before any other review content.

## Report structure

The coach produces a **single inline report** in response to `/lid-coach`, followed by user-driven turns for any detail or working session. The report is digestible because findings are rendered as a tight inventory (one line per finding), not as detailed paragraphs — detail is reserved for the user-driven turns that follow.

**Why one message.** An earlier design called for two messages (data, then synthesis), but Claude Code emits assistant turns as continuous output: "---" separators don't produce user-perceivable message boundaries, and the structure rendered as one long block anyway. Putting the whole report in one message and keeping findings as a one-line inventory achieves the same goal — the report is short enough to read, and depth comes only when the user asks.

**Voice throughout is coach, not grader.** The coach leads with what is working before calling out drift; frames findings as opportunities to tighten rather than violations; uses "consider," "try," "you could" rather than evaluative language ("violation," "failure," "wrong," "broken"). Reports are forward-looking — where to go from here — not backward-looking verdicts. A user reading the report should feel encouraged to improve, not graded. This voice is load-bearing; a grader-toned report technically delivers the same information but leaves the user less likely to act on it.

### Report sections, in order

1. **Executive summary** — three elements:
   - A **posture line**: a short categorical tag summarizing overall health (e.g., *Healthy, with accumulation drift* / *Drifting linkage* / *Bootstrapping*). Never a numeric score, letter grade, or point total — those are gameable, demoralizing, and imply false precision.
   - A **scorecard**: a brief per-dimension health check, rendered as a short bulleted list (one line per dimension) using ✓ (strong) / ⚠ (drifting) / ✗ (weak) markers with a short word label. Clusters principle categories (e.g., *Linkage*, *Cascade*, *Mutation hygiene*, *Mode fit*, *HLD discipline*, *LLD quality*) so the user gets a fast read across the whole arrow. "Scorecard" is the user-facing name — it reads as a health dashboard, not as jargon. Composable across runs so users can see improvement over time.
   - A **one-sentence headline** naming what is working and the single most valuable next step. "What is working" comes first — it is not throat-clearing; it is the tonal anchor for the rest of the report.
2. **Findings inventory** — a tight list, one line per finding: priority + title + the principle the finding cites. The inventory's job is to show the surface area of what the coach noted, not to detail each finding. Example shape: `**F2 (medium):** Superseded LLDs accumulating in docs/llds/ · *mutation, not accumulation*.`
3. **What was audited** — files read, areas sampled, depth of sampling, and **quantitative signals** (counts of `@spec` references, LLDs reviewed, arrow segments sampled, files read). Quantitative claims belong in this section because they describe scope of inspection, not project quality. They do **not** appear as numeric grades elsewhere in the report.
4. **Out-of-scope note** — when mode is Scoped, lists what was deliberately not reviewed. Omitted entirely in Full mode.
5. **Offer to help** — close the report with two distinct invitations, so both pathways are discoverable:
   - A line inviting the user to direct review follow-up: "I can walk you through findings in detail, focus on a theme or priority, or work through specific items together. What would be most useful?"
   - A line hinting that the coach can also help with broader LID-usage questions: "If you have broader questions about using LID for your project — multi-repo setups, where PRDs fit, mode transitions, what to do when a segment grows too large — I can help with those too." The hint enables FAQ discoverability without forcing a single user invocation to choose between the two pathways.

### Subsequent user-driven turns — detail or working session

Driven by the user's response to the offer. Possible shapes:

- **Walk through findings (or a subset).** Render detailed finding paragraphs in priority order, using the paragraph form below. Don't re-render the executive summary, the inventory, or the audit content — they were in the report.
- **Focus on a theme or priority.** Render only the relevant subset of findings as paragraphs.
- **Working session on a specific finding.** Engage on that finding directly (discuss, refine, plan a fix) without re-rendering the broader report.
- **Skip detail, jump to action.** Surface concrete next steps for the highest-impact findings without restating each.

When the user picks no specific direction, default to walking through findings in priority order.

### Detailed finding paragraph form (user-driven turns)

When detailed findings are rendered, each finding is **one paragraph** (not a sub-bullet form with labeled fields). The paragraph weaves four elements together:

- The observation — concrete, naming files or lines where useful; evidence inline where it helps the reader see the pattern. Findings *may* cite specific counts when the count is the observation itself (e.g., "the spec file has 3 IDs in the 1000-block alongside semantic-naming IDs"); they do **not** assign numeric grades.
- The LID principle the finding relates to, cited by name with a **plain-English gloss appended inline** — e.g., "*Mutation, not accumulation* — docs reflect current intent; git preserves history." Never cite a principle by name alone; the reader may not yet be fluent in LID terminology.
- **Why this matters** — the consequence of leaving the drift in place, or the benefit of fixing it. A finding that explains only *what* to do is a grader's move; a coach's move also teaches *why*. The "why" draws from the principle's motivation grounded in the user's project — what gets harder, what compounds, what gets more reliable.
- A closing recommended action — concrete, naming files or commands. When the follow-up is structural (orphans, adjacent-level drift enumeration), point at `/arrow-maintenance`. When the follow-up is configuration, see *Recommended-action targets* below.

The four elements weave as prose, not as labeled sub-bullets. Bullet lists are reserved for genuinely parallel items *within* a finding (e.g., "these four files could be removed"), not as the finding's structural backbone.

Teaching the "why" requires the coach to have a theory of what each principle protects against, not only how to detect its absence. The principle body embedded in the skill carries both layers — description, what drift looks like, and what the drift costs over time. Findings that skip the "why" layer reduce the coach to a checklist.

### Recommended-action targets

When a finding implies a configuration change, the recommended action is **`/update-lid`** — the single command for both initial bootstrap and ongoing reconciliation. The skill state-dispatches: unconfigured projects get bootstrap; already-configured projects get reconciliation. Use it for precursor directive naming, missing scope declaration, drifted CLAUDE.md template, missing standard directories, mode transitions, or any other case where LID configuration needs bringing into alignment.

The coach refers users who want to *start a code change at the same time as bootstrap* to `/linked-intent-dev` instead — the workflow skill's Phase 1 calls `update-lid`'s bootstrap branch as a sub-step before drafting the HLD. That is a code-change entry point, not a configuration one, so it does not displace `/update-lid` as the configuration recommendation; it is the right pointer when the user's framing is "I want to build X on a fresh project," not "configure my project for LID."

## Advisory posture

The coach **does not make file changes**. Recommendations are surfaced; the user applies them by editing directly, by running `/update-lid` for configuration or convention changes, or by invoking `/arrow-maintenance` when a structural audit would answer a specific finding faster than the coach can.

The rationale for an advisory-only posture: principle-based judgments are interpretive and silent edits would bypass user review on exactly the decisions where review matters most. An advisory coach makes its reasoning visible; a corrective coach would smuggle interpretation into diffs. This matches the user-is-always-right tenet: the skill's job is to make the cost of current patterns visible, not to overwrite them.

## Relationship to `arrow-maintenance`

`arrow-maintenance` and `lid-coach` are complementary. The overlay's structural audit is deterministic and cheap; the coach's principle review is interpretive and expensive. A finding in the coach's report may recommend running `/arrow-maintenance` when the follow-up diagnosis is structural (e.g., "this looks like a reverse-orphan pattern — run `/arrow-maintenance` to enumerate them"). The coach does not require the overlay to be installed, but consumes overlay signals when present — `index.yaml` status markers and drift flags feed findings at the cascade-health dimension.

## Relationship to `skill-creator` evals

The coach is a behavioral skill; its arrow is `HLD → LLD → EARS → evals + SKILL.md + references/`. Evals follow the schema described in `docs/llds/linked-intent-dev.md § Eval Metadata Conventions`. Because the output is prose (a report) rather than file edits, assertions graded by `skill-creator`'s harness will generally be about *report content* — for example, "the report flags the missing LLD for the stub feature" or "the report cites the scope-disambiguation principle when the fixture has a universal-sounding scoped spec" — rather than about filesystem state.

## Decisions & Alternatives

| Decision | Chosen | Alternatives Considered | Rationale |
|---|---|---|---|
| Coach skill: separate vs. folded into `update-lid` | Separate skill (`lid-coach`) | New dispatch branch inside `update-lid`; branch inside `linked-intent-dev` | Coach's principle body is shaped differently from setup's state-dispatch logic — folding would conflate two unrelated skill bodies under one frontmatter. Folding into `linked-intent-dev` would bloat the pure-prose workflow skill that triggers on every code change. One new command is an acceptable minimum-system cost for a distinct capability. |
| Coach LLD: separate vs. inside `linked-intent-dev` LLD | Separate LLD (`docs/llds/lid-coach.md`) | Section inside `docs/llds/linked-intent-dev.md` | Coach reasons from a substantial body of LID theory (principles + audit signals + *why-it-matters*); embedding that body in a sibling LLD would dominate the document. *One LLD per intent component* makes the coach its own LLD; plugin-level concerns (mode detection, spec ID format, eval metadata schema) stay in the parent LLD, referenced from here. |
| Coach theory location | Embedded in the coach's SKILL.md body | Bundled `references/lid-principles.md`; read user's `docs/high-level-design.md` at runtime | Principles are always needed during a coach run, so progressive disclosure (the reason to extract content into `references/`) provides no benefit; splitting just adds a file. Reading the user's HLD would mistake their project's HLD for LID's theory — a category error. Embedded keeps the skill to a single file under the skill-creator size budget, with the option to extract later if the content grows. |
| Coach posture | Advisory (no file changes) | Corrective (applies fixes); hybrid (propose diffs to approve) | Principle-based judgments are interpretive; silent edits would bypass user review on exactly the decisions where review matters most. Approve-diffs UX is reasonable but adds a second interaction mode for marginal gain over "user sees recommendations and applies manually." |
| Coach auto-invocation | Disabled (command only) | Auto-triggered periodically; auto-triggered on specific signals | Review is broad-sample and expensive; opportunistic triggering would burn tokens across unrelated tasks. The user opts in when they want a review. |
| Coach dispatch on unconfigured project | Recommend `/update-lid`, do not coach | Silently bootstrap, then coach; refuse and exit | Preserves invocation boundary — the coach reads and reasons, it does not configure. Silent bootstrap would violate advisory posture. A flat refusal loses the handoff signal. |
| Coach dispatch on LID-shaped-but-no-directives project | Proceed with full review; surface CLAUDE.md gap as a high-priority finding | Refuse on strict literal directive grep; recognize a hardcoded list of precursor names | Strict literal grep is a false-negative trap (real example: a project with a 30-segment arrow overlay calling its directives "design-driven-dev"). The structural arrow is the authoritative signal that a project is doing LID; the directive string is communication, not gating. Hardcoded precursor names would not generalize and would rot over time. |
| Coach overall summary form | Categorical posture + ✓/⚠/✗ scorecard | Numeric score (0–100); letter grade (A–F); pass/fail | Numeric and letter forms are gameable, demoralizing, and imply false precision. Categorical posture conveys overall health without baggage; the scorecard adds dimensional specificity in a "health dashboard" presentation that reads naturally to users new to LID. The user-facing name is "Scorecard" so the section reads as a score; "dimensional strip" was earlier internal vocabulary and was retired before user exposure. |
| Coach voice | Coach (forward-looking, encouraging) | Auditor (clinical, neutral); grader (evaluative) | The voice is load-bearing for whether users act on findings. A grader-toned report delivers the same information but reduces follow-through; an auditor-toned report misses the teaching opportunity. Coach voice — "consider," "try," lead with what is working — keeps the user moving forward. |
| Findings: paragraph form vs. labeled sub-bullets | Paragraph form weaving observation, principle, *why it matters*, and action — but only when detailed findings are rendered in user-driven turns; the report itself uses one-line inventory entries | Sub-bullet form with explicit Observation/Principle/Action fields | The labeled-sub-bullet form reads like a compliance report and clusters around the labels rather than the prose. Paragraph form forces the four elements to flow naturally and makes the *why-it-matters* layer integrate rather than slot in awkwardly. |
| Teach-the-why requirement | Required: each finding explains why the drift matters, not only what to do | Optional / nice-to-have | "What to do" is a checklist; "why it matters" is coaching. Requiring the *why* layer in every finding is what separates the coach from a linter, and it is what users coming to LID for the first time need to learn the methodology rather than just patch their project. |
| Citation style for principles | By name with a plain-English gloss inline | By numeric ID; by file anchor; by name alone | Numeric IDs and file anchors require a glossary lookup that breaks the read. Name-alone citations gate findings behind LID jargon the reader may not have. Name + plain-English gloss is self-contained at every appearance. |
| Report delivery: single message with inventory-form findings, detail on user direction | Single inline report (exec summary + scorecard + one-line findings inventory + audit + offer); detailed paragraphs only when the user directs in a follow-up turn | Two-message split (data first, synthesis second); full detailed paragraphs in the immediate response | The wall-of-detail problem on mature projects is solved by keeping findings as one-line inventory entries in the report rather than detailed paragraphs — the report stays short. The two-message split (briefly tried earlier) is rejected because Claude Code emits assistant turns as continuous output: "---" separators do not produce user-perceivable message boundaries, so the structure renders as one long block anyway. One message with disciplined inventory form, detail on user request, is the actually-deliverable shape. |
| Quantitative signals: in findings vs in audit section | In "what was audited" only; findings do not assign numeric grades | Inline numeric scores per finding; per-dimension percentage grades; project-wide score | Numbers in findings turn into grades, with all the gameability and demoralization that brings. Numbers in the audit section describe scope of inspection — useful transparency, not judgment. Findings may cite counts when the count is the observation itself, but never as a grade. |
| Arrow-path sampling threshold for large projects | More than 15 LLDs OR more than 200 `@spec`-annotated files triggers per-arrow path sampling | Always sample all arrows; never sample (judgment only); fixed numeric threshold like 25 LLDs | Below the thresholds the agent can read more freely without missing arrows; at scale, end-to-end sampling per arrow is the only way to catch arrows where one level disagrees with another. The exact thresholds are practical choices, refinable as the coach is run on more projects. |
| `docs/arrows/index.yaml` as primary arrow-sampling guide when present | Yes — read first, drives segment selection, drift fields feed findings | Treat as just another input file; ignore unless overlay-specific findings | The index is high-signal: it enumerates the project's view of its own segments, with explicit drift and audit timestamps. Using it as guide makes the coach efficient on large projects and grounds findings in what the project itself thinks is in flight. |
| Context-free reading: enhance existing tenet vs. add a new principle | Enhance *what is currently here is the truth* to cover both halves — current intent (no historical residue) and context-free reading (no reliance on the conversation that produced the doc) | New standalone principle for implicit-context drift; treat as a sub-case of one of the dimensions | Both halves share the same underlying claim: the doc tree is what travels to the next session, and the next agent reads it cold. Splitting them weakens both halves; folding them keeps the tenet legible and load-bearing. The audit signals on each side differ, but the principle is the same. |
| Cold-read pass: prescriptive checklist vs. directive | Directive ("read each doc cold; surface what's unclear") | Checklist of phrases to grep for ("obviously", "of course", "as discussed", etc.) | A checklist trains the agent to pattern-match for surface phrases and miss the deeper pattern; context leaks rarely use those phrases. The directive keeps the cold-read pass open-ended, which is the only shape that catches the failure mode. |
| Conversational guidance: separate skill vs. FAQ resource inside the coach | Load-on-demand `references/lid-faq.md` consulted by the coach in conversational mode | New skill dedicated to LID adoption Q&A; embed conversational content in the SKILL.md body; no FAQ at all | A separate skill would expand the surface beyond minimum-system for content that is naturally co-resident with the coach's principle body. Embedding in SKILL.md would pull review behavior toward FAQ topics on every run, since the body is always loaded. A load-on-demand reference is the cleanest middle path — the conversational layer exists, the review layer stays focused, and the FAQ loads only when the user's prompt asks for it. |

## Open Questions & Future Decisions

1. **Principle body — shape and granularity.** The embedded principle content is "each principle paired with a description, *why it matters*, and an audit signal." Exact structure (flat list vs. grouped by arrow level vs. grouped by dimension) and the cadence at which the body is regenerated from HLD changes are to be settled during implementation. If total SKILL.md length approaches the progressive-disclosure budget (~500 lines), extract principles into `references/lid-principles.md` at that time.
2. **Sampling strategy for large projects.** For projects beyond a single context window's worth of LID artifacts, what does the coach sample and how? Candidates: read all docs + sample code, read recent-change areas, read overlay-flagged areas first, ask the user to nominate a slice. To be refined after running the coach on real projects.
3. **Output persistence.** Inline-only is the default; some users may want the report as a file for later reference. Whether `/lid-coach --save-report <path>` or similar grows as an affordance is deferred.
4. **Scorecard dimensions — fixed vs. project-adaptive.** The current LLD says the coach picks 4–6 dimensions most salient for the project under review. Whether to standardize a fixed dimension list (composable but possibly noisy) or keep project-adaptive selection (more legible per-run but less comparable across runs) is to be settled after seeing real reports.

## References

- `docs/high-level-design.md` — the HLD this LLD traces from. Approach sections, Tenets, Goals, and key Design Decisions are the upstream source for the coach's embedded principle body.
- `docs/llds/linked-intent-dev.md` — sibling LLD covering the plugin's pure-prose workflow skill and `update-lid`. Plugin-level concerns (mode detection, spec ID format, the LID-on-LID linkage inversion, `index.yaml` update mechanics, eval metadata schema) live there and are referenced from this LLD rather than re-specified.
- `docs/llds/arrow-maintenance.md` — sibling plugin LLD; the deterministic-structural-audit behavior the coach defers to lives there.
- `docs/specs/lid-coach-specs.md` — the EARS specs derived from this LLD.
- `skill-creator` plugin — the eval harness used for behavioral-skill evals.
