# Eval Iteration 1 — Cross-Skill Summary

**Date**: 2026-04-18
**Scope**: First eval pass across all three behavioral skills (`lid-setup`, `arrow-maintenance` command mode, `map-codebase`).

## Headline

All three skills pass every testable assertion with_skill (100% × 3). Baseline-vs-skill deltas are consistent and substantial (+36% to +56%), confirming the skill prose encodes real, learned discipline that an unguided agent does not reproduce on its own.

| Skill | with_skill | without_skill | Delta |
|---|---|---|---|
| lid-setup | 13/13 (100%) | 8/13 (62%) | +38% |
| arrow-maintenance (command) | 11/11 (100%) | 7/11 (64%) | +36% |
| map-codebase | 9/9 testable (100%) | 4/9 (44%) | +56% |
| **Aggregate** | **33/33 (100%)** | **19/33 (58%)** | **+42%** |

## What the deltas tell us

- **lid-setup (+38%)**: Baseline created `docs/planning/` from old convention and skipped the `## LID Mode:` heading. The skill's discipline around the *current* convention — and its explicit "don't create planning" rule — closes both gaps.
- **arrow-maintenance (+36%)**: Baseline set `audited_sha: null` because it didn't understand the field's purpose, used an ad-hoc "status checklist" instead of the `UNMAPPED/MAPPED/AUDITED/OK` enum, and unnecessarily modified CLAUDE.md. The skill's explicit schema references prevent each of these.
- **map-codebase (+56%)**: Largest delta. Baseline missed the token-intensity warning entirely, didn't produce multiple lens-based clusterings, and offered three ambiguous options instead of a clean redirect. These are all learned behaviors the skill encodes.

## What was validated

**Dogfooding signals are green.**

- **Process signal** — every cascade-originating change traced through an LLD or spec update; no `SKILL.md` edit without upstream anchor. The earlier cold-reads caught the few drifts (skeleton-lld-template.md, EARS Coverage heading mismatch, CLAUDE.md metadata bleed) and we repaired them.
- **Coherence signal** — each behavioral skill has LLD → EARS → evals without gaps. All assertions in this iteration cite spec IDs; spec files reference LLDs authoritatively; LLDs reference the HLD.

**Observed real-world quality beyond assertions.** Several runs surfaced *actual* useful findings the assertions didn't explicitly check for:

- arrow-maintenance eval-0 caught a real coherence gap (AUTH-001 marked `[x]` with no implementation) and surfaced it for user decision — exactly the ARROW-MAINT-013 behavior.
- arrow-maintenance eval-1 created `docs/arrows/README.md` from the template on its own — closing cold-read finding #15 without being told to.
- map-codebase eval-0's lens proposals explicitly excluded anti-pattern lenses (frontend/backend, deploys-together, team ownership, generic utils) — MAP-CODE-008's constraint enforced.
- map-codebase eval-0 simulated the STOP discipline correctly — halted at the first real user decision point without fabricating answers.

## Limitations of this iteration

- **No quantitative timing data.** Agent notifications from the Task tool would carry `duration_ms` and `total_tokens`; I didn't capture these systematically. Future iterations should persist them for per-eval timing comparisons.
- **map-codebase only tested through Phase 2.** Phase 3+ (slicing, artifact generation with inter-phase STOPs, terminal verification) requires user-in-loop evaluation with the eval-viewer. Deferred to iteration 2.
- **Not run through `skill-creator`'s full eval harness.** I spawned subagents and graded inline rather than using the `aggregate_benchmark` + HTML viewer flow. Benchmarks are markdown summaries per skill. Equivalent information, less structured for per-iteration diffing.

## Next steps (candidates, not commitments)

1. **Iteration 2 evals with user-in-loop** for `/map-codebase` Phases 3–6, so the richer assertions (STOP discipline, lens + slicing two-step, artifact generation, brownfield EARS status semantics) can be graded.
2. **Expand coverage**: rename lifecycle atomicity (ARROW-MAINT-017), incremental audit (ARROW-MAINT-007), drift reconciliation (LID-SETUP-005 and -029), spec-ID prefix collision prompt (MAP-CODE-019), coherence-script delegation (ARROW-MAINT-025).
3. **Description optimization** on the three behavioral skills' frontmatter via `skill-creator`'s `run_loop.py` once iteration 2 is done — validates trigger accuracy, not just behavior.
4. **Bootstrap this repo's own `docs/arrows/` overlay**, then run `/arrow-maintenance` against itself as a dogfooding demonstration.

## Artifacts

- `plugins/linked-intent-dev/skills/lid-setup-workspace/iteration-1/benchmark.md`
- `plugins/arrow-maintenance/skills/arrow-maintenance-workspace/iteration-1/benchmark.md`
- `plugins/arrow-maintenance/skills/map-codebase-workspace/iteration-1/benchmark.md`
- Per-eval `eval_metadata.json` alongside each benchmark
- Fixture projects and subagent outputs under each workspace
