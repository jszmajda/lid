# Arrow: lid-coach

Advisory principle-review skill for LID projects. Reads a project's LID artifacts, reasons against LID's own principles, and produces a coach-toned report with a posture line, scorecard, and prioritized findings. Auto-invocation disabled; reachable only via `/lid-coach`. A leaf segment under the `LID` sub-HLD, alongside the workflow skill (`core`) and `update-lid`; it earns its own leaf LLD because the embedded principle body and report-shaping requirements are substantial enough to dominate a shared document.

## Status

**MAPPED** — segment was split out from `linked-intent-dev` on 2026-05-05. Skill body committed; skill-creator iteration-1 run 2026-05-15 (8 fixtures, with-skill 38/38 assertions = 100%, baseline 83%). 18 of 52 LID-COACH specs flipped to `[x]` on iteration-1 eval evidence; 34 remain `[ ]` (not exercised by the current fixture set).

## References

### HLD
- `docs/high-level-design.md` § Architecture / Plugins (linked-intent-dev plugin) — names the coach as one of three skills in the plugin.
- `docs/high-level-design.md` § Key Design Decisions / The arrow for LID itself — establishes the behavioral-skill arrow shape (`HLD → LLD → EARS → evals + SKILL.md + references/`).
- `docs/high-level-design.md` § Approach sections, § Tenets, § Goals, § Key Design Decisions — the canonical source for the coach's embedded principle body. When this content changes, cascade reaches the coach SKILL.md via the LID-on-LID workflow.

### LLD
- `docs/intent/linked-intent-dev/lid-coach/lid-coach-design.md` — this segment's leaf LLD.
- `docs/intent/linked-intent-dev/linked-intent-dev-design.md` — parent `LID` sub-HLD for plugin-level concerns (mode detection, spec ID format, LID-on-LID linkage inversion, eval metadata schema). The coach LLD references this rather than re-specifying.

### EARS
- `docs/intent/linked-intent-dev/lid-coach/lid-coach-specs.md` (52 specs, prefix `LID-COACH-*`)

### Tests / Evals
- `plugins/linked-intent-dev/skills/lid-coach/evals/evals.json` — eight prompt fixtures with assertions (unconfigured-project handoff, healthy full-project posture/scorecard/voice, HLD bloat, accumulation antipattern, scoped missing scope, advisory posture, lid-shaped-without-directives, index.yaml-driven arrow sampling).
- skill-creator iteration-1 at `lid-coach-workspace/iteration-1/` (run 2026-05-15): with-skill 38/38 assertions (100%, ±0), baseline 83% (±19). evals 0/3/4/5 are non-discriminating (baseline already passes) — candidates to strengthen in iteration-2.

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
| State Dispatch | LID-COACH-003..007 | 2 | 3 | 0 |
| Inputs | LID-COACH-008..013 | 1 | 5 | 0 |
| Principle Body | LID-COACH-014..015 | 0 | 2 | 0 |
| Review Dimensions | LID-COACH-016..029 | 2 | 12 | 0 |
| Mode Interaction | LID-COACH-030..032 | 0 | 3 | 0 |
| Report Structure | LID-COACH-033..038 | 4 | 2 | 0 |
| Advisory Posture | LID-COACH-039..040 | 2 | 0 | 0 |
| Arrow-Maintenance Relationship | LID-COACH-041..042 | 0 | 2 | 0 |
| Voice and Tone | LID-COACH-043..044 | 2 | 0 | 0 |
| Lenient Dispatch | LID-COACH-045..046 | 2 | 0 | 0 |
| Teach While Correcting | LID-COACH-047 | 0 | 1 | 0 |
| Sampling Strategy | LID-COACH-048..049 | 1 | 1 | 0 |
| Quantitative Signals | LID-COACH-050 | 1 | 0 | 0 |
| Cold-Read Pass | LID-COACH-051 | 0 | 1 | 0 |
| Conversational Guidance | LID-COACH-052 | 1 | 0 | 0 |
| **Total** | | **18** | **34** | **0** |

**Summary:** Skill body committed; skill-creator iteration-1 (2026-05-15, 8 fixtures) passed 38/38 with-skill assertions. 18 specs flipped to `[x]` on that eval evidence. The 34 remaining `[ ]` are not exercised by the current fixtures — chiefly invocation/frontmatter (001–002), input-reading (008–012), principle-body (014–015), most review dimensions (016–032 less 019/023), and 036/038/041/042/047/048/051. Closing them is iteration-2 fixture work, not skill-body gaps.

## Key Findings

1. **Iteration-1 run; 18 specs verified.** skill-creator iteration-1 (2026-05-15) passed all 38 with-skill assertions across 8 fixtures; 18 LID-COACH specs are now `[x]`. The 34 remaining `[ ]` are unexercised by the current fixtures, not skill-body gaps — they need new iteration-2 fixtures (notably for invocation, input-reading, principle-body, and the review dimensions beyond HLD-bloat/accumulation).
2. **`@spec` annotations live in the spec header, not the SKILL.md prose (LID-on-LID inversion).** The coach SKILL.md is prompt content; embedding `@spec` IDs in its body would bend runtime behavior. The spec file's `**Implementing artifacts**:` header carries the linkage downward (`docs/intent/linked-intent-dev/lid-coach/lid-coach-specs.md:1-10`).
3. **HLD-to-coach cascade contract.** The embedded principle body is a downstream artifact of LID's HLD in the LID-on-LID arrow. When the HLD's Approach sections, Tenets, Goals, or key Design Decisions change, cascade should reach this segment's SKILL.md. Drift between LID's HLD and the embedded principles is itself a dogfooding violation.

## Work Required

### Must Fix
1. Author iteration-2 fixtures covering the 34 unexercised specs — invocation/frontmatter (001–002), input-reading (008–012), principle-body embedding/cascade (014–015), the review dimensions beyond HLD-bloat/accumulation (016–018, 020–032), structural-handoff (036, 041–042), persistence (038), teach-the-why in isolation (047), large-project sampling threshold (048), and the cold-read pass (051). Several need larger fixture projects (>15 LLDs or >200 `@spec` files) to exercise 048.
2. Update eval-3's assertion text: it references the retired "mutation-not-accumulation" principle name; the principle is now *docs carry current intent, written to be read cold* (the skill cited the current name correctly — the assertion is stale, not the skill).

### Should Fix
3. Strengthen or replace evals 0/3/4/5 — iteration-1 showed baseline (no skill) already passes them, so they are non-discriminating and do not measure the skill's contribution.
4. Run a Threadkeeper-style real-project review (the original false-negative case that motivated LID-COACH-045/046) to confirm the lenient dispatch produces a useful review on a real project whose `CLAUDE.md` uses precursor naming, beyond the synthetic eval-6 fixture.
