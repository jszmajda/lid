# Arrow: lid-coach

Advisory principle-review skill for LID projects. Reads a project's LID artifacts, reasons against LID's own principles, and produces a coach-toned report with a posture line, scorecard, and prioritized findings. Auto-invocation disabled; reachable only via `/lid-coach`. Lives inside the `linked-intent-dev` plugin alongside the workflow skill and `update-lid`, but has its own LLD and arrow segment because the embedded principle body and report-shaping requirements are substantial enough to warrant separation.

## Status

**MAPPED** — segment was split out from `linked-intent-dev` on 2026-05-05. Skill body committed; all 52 LID-COACH specs still marked `[ ]` pending skill-creator iteration-1.

## References

### HLD
- `docs/high-level-design.md` § Architecture / Plugins (linked-intent-dev plugin) — names the coach as one of three skills in the plugin.
- `docs/high-level-design.md` § Key Design Decisions / The arrow for LID itself — establishes the behavioral-skill arrow shape (`HLD → LLD → EARS → evals + SKILL.md + references/`).
- `docs/high-level-design.md` § Approach sections, § Tenets, § Goals, § Key Design Decisions — the canonical source for the coach's embedded principle body. When this content changes, cascade reaches the coach SKILL.md via the LID-on-LID workflow.

### LLD
- `docs/llds/lid-coach.md` — this segment's LLD.
- `docs/llds/linked-intent-dev.md` — sibling LLD for plugin-level concerns (mode detection, spec ID format, LID-on-LID linkage inversion, eval metadata schema). The coach LLD references this rather than re-specifying.

### EARS
- `docs/specs/lid-coach-specs.md` (52 specs, prefix `LID-COACH-*`)

### Tests / Evals
- `plugins/linked-intent-dev/skills/lid-coach/evals/evals.json` — seven prompt fixtures with assertions (unconfigured-project handoff, healthy full-project posture/scorecard/two-turn delivery/voice, HLD bloat, accumulation antipattern, scoped missing scope, advisory posture, lid-shaped-without-directives, index.yaml-driven arrow sampling).
- No skill-creator iteration runs yet (skill not implemented).

### Code (skill prompts and bundled content)
- `plugins/linked-intent-dev/skills/lid-coach/SKILL.md` — embedded principle body (description + *why it matters* + audit signal per principle), dispatch table, scorecard format, coach-voice guidance, advisory posture, cold-read pass directive, conversational-mode pointer.
- `plugins/linked-intent-dev/skills/lid-coach/references/lid-faq.md` — load-on-demand conversational guidance covering multi-repo organization, PRDs upstream of HLD, mode-fit changes, the upstream-ownership reframe, and arrow-segment splitting.

The skill is directly invokable as `/lid-coach` — no command stub needed per Claude Code's skills model.

## Architecture

**Purpose:** Provide an advisory, principle-level review of a project's LID usage. Distinct from `update-lid` (configuration reconciliation) and `arrow-maintenance` (deterministic structural audit) — the coach reasons interpretively from LID's own principles and teaches *why* drift matters alongside *what* to do about it.

**Key Components:**
1. **Dispatch.** Six-row table covering unconfigured projects (refuse, recommend `/update-lid`), LID-shaped-but-no-directives projects (proceed; flag the directive gap as high-priority), missing-directories cases (reduced review), Scoped-without-scope (conservative project-wide review), corrupt overlay (flag and offer reduced/pause), and fully-configured (full review).
2. **Principle body (embedded in `SKILL.md`).** Curated distillation of LID's HLD — Approach sections, Tenets, Goals, key Design Decisions — with each principle paired with a *why-it-matters* layer and an audit signal. The *why-it-matters* layer is what the coach draws on to teach during findings.
3. **Review flow.** Read CLAUDE.md, HLD, LLDs, specs, sampled code/tests, overlay (when present); reason across review dimensions (arrow completeness, linkage hygiene, LLD granularity, HLD discipline, LLD sufficiency, intent-tree alignment, semantic legibility, mutation-vs-accumulation, scope disambiguation, tests-first, cascade health, brownfield inferred content, arrow shape, mode fit); prioritize findings high → medium → low.
4. **Report.** Inline rendering. Executive summary (categorical posture line + ✓/⚠/✗ scorecard + headline naming what is working). Findings as paragraphs (not labeled sub-bullets), each weaving observation, principle-with-gloss, *why this matters*, and recommended action. "What was audited" inventory. Out-of-scope note in Scoped mode only.
5. **Advisory posture.** No file changes. Configuration recommendations point at `/update-lid`; structural enumeration recommendations point at `/arrow-maintenance`.

## Spec Coverage

| Category | Spec range | Implemented | Active gap | Deferred |
|---|---|---|---|---|
| Invocation | LID-COACH-001..002 | 0 | 2 | 0 |
| State Dispatch | LID-COACH-003..007 | 0 | 5 | 0 |
| Inputs | LID-COACH-008..013 | 0 | 6 | 0 |
| Principle Body | LID-COACH-014..015 | 0 | 2 | 0 |
| Review Dimensions | LID-COACH-016..029 | 0 | 14 | 0 |
| Mode Interaction | LID-COACH-030..032 | 0 | 3 | 0 |
| Report Structure | LID-COACH-033..038 | 0 | 6 | 0 |
| Advisory Posture | LID-COACH-039..040 | 0 | 2 | 0 |
| Arrow-Maintenance Relationship | LID-COACH-041..042 | 0 | 2 | 0 |
| Voice and Tone | LID-COACH-043..044 | 0 | 2 | 0 |
| Lenient Dispatch | LID-COACH-045..046 | 0 | 2 | 0 |
| Teach While Correcting | LID-COACH-047 | 0 | 1 | 0 |
| Sampling Strategy | LID-COACH-048..049 | 0 | 2 | 0 |
| Quantitative Signals | LID-COACH-050 | 0 | 1 | 0 |
| Cold-Read Pass | LID-COACH-051 | 0 | 1 | 0 |
| Conversational Guidance | LID-COACH-052 | 0 | 1 | 0 |
| **Total** | | **0** | **52** | **0** |

**Summary:** Skill body committed; specs remain `[ ]` until skill-creator iteration-1 verifies each behavior against the seven fixtures in `evals/evals.json`.

## Key Findings

1. **Skill committed; evals not yet run.** `plugins/linked-intent-dev/skills/lid-coach/` is in the tree but the seven prompt fixtures in `evals/evals.json` have not been exercised. Running iteration-1 is the next step before flipping implemented LID-COACH specs from `[ ]` to `[x]`.
2. **`@spec` annotations live in the spec header, not the SKILL.md prose (LID-on-LID inversion).** The coach SKILL.md is prompt content; embedding `@spec` IDs in its body would bend runtime behavior. The spec file's `**Implementing artifacts**:` header carries the linkage downward (`docs/specs/lid-coach-specs.md:1-10`).
3. **HLD-to-coach cascade contract.** The embedded principle body is a downstream artifact of LID's HLD in the LID-on-LID arrow. When the HLD's Approach sections, Tenets, Goals, or key Design Decisions change, cascade should reach this segment's SKILL.md. Drift between LID's HLD and the embedded principles is itself a dogfooding violation.

## Work Required

### Must Fix
1. Run `skill-creator` iteration-1 against the seven fixtures in `evals/evals.json`. Use the assertions to verify single-message report delivery, dispatch behavior, scorecard format, inventory-form findings (paragraphs only in user-driven follow-ups), plain-English principle gloss, *why-it-matters* presence, single-command (`/update-lid`) recommendation for configuration changes, index.yaml-driven sampling, and absence of grader language.
2. Flip implemented LID-COACH specs from `[ ]` to `[x]` as the skill body satisfies them.

### Should Fix
4. Run a Threadkeeper-style real-project review (the original false-negative case that motivated LID-COACH-045/046) to confirm the lenient dispatch produces a useful review on a project whose `CLAUDE.md` uses precursor naming.
5. Run a cold-read subagent against the SKILL.md to verify a reader unfamiliar with the conversation history reads the scorecard as a "score" and sees the *why-it-matters* layer in findings.
