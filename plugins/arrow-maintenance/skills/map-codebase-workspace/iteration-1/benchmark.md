# map-codebase eval iteration 1 — benchmark

**Date**: 2026-04-18
**Skill**: map-codebase
**Iteration**: 1

Note: `/map-codebase` is a multi-phase workflow with user-in-the-loop STOPs at each phase boundary. Iteration 1 runs cover the invocation response, Phase 1 (sweep), Phase 2 (lens proposals), and dispatch-branch behavior (partial-LID, fully-LID redirect). Assertions about Phase 3+ (slicing, artifact generation, terminal verification) are deferred to iteration 2 with a human reviewer in the loop.

## Summary

| Configuration | Pass rate (testable assertions) | Notes |
|---|---|---|
| **with_skill** | **9/9 (100%)** | Followed skill dispatch, produced lens proposals with anti-pattern exclusions, correctly held files |
| without_skill (baseline) | 4/9 (44%) | Missed token warning, no lens multiplicity, redirect less clean |
| **Delta** | **+56%** | Largest delta of three skills — map-codebase structure is hard to replicate unguided |

## Eval 0: brownfield-small-codebase (Phase 1 + Phase 2 coverage)

| Assertion | with_skill | without_skill |
|---|---|---|
| Token-intensity warning at invocation | ✓ (explicit, upfront) | ✗ (no warning) |
| Asks for starting scope (whole project vs. specific parts) | ✓ (also noted mode implication) | partial (asked about scope of *pass*, not LID scope) |
| Offers subagent-parallel mapping | ✓ (recommended single-agent for small codebase) | ✗ (not mentioned) |
| Phase 2 presents 3+ fundamentally different lens-based clusterings | ✓ (4 lenses: Domain, User-facing, Behavioral, Data flow) | partial (proposed 2 arrows, no lens multiplicity) |
| **Subtotal (testable)** | **4/4** | **1.5/4** |

**Deferred (Phase 3+, needs user-in-loop)**: slicing granularity, artifact generation, flesh-out prompt, terminal CLAUDE.md verification. Mark these as pending iteration 2.

**Observations**:
- with_skill explicitly excluded anti-pattern lenses (frontend/backend, deploys-together, team ownership, generic utils) in its proposal framing — ARROW-MAINT-008 behavior nailed.
- The Phase 1 sweep produced structured per-file reports matching MAP-CODE-026 exactly: purpose, exports, dependencies, data shapes, side effects, role, observations.
- with_skill correctly held back all file writes until Phase 2 lens selection (user approval required) — ARROW-MAINT-027 (STOPs) and MAP-CODE-012 (no generation until approval) upheld.
- without_skill jumped to proposing an arrow structure without multi-lens exploration; it missed the edge-detection value of surfacing alternatives for the user to choose.

## Eval 1: partial-lid-dispatch

| Assertion | with_skill | without_skill |
|---|---|---|
| Detects partial LID state and asks user about authority vs. supersede | ✓ (explicit Option A / Option B) | partial (flagged state, suggested dispatch to arrow-maintenance — different framing) |
| Does NOT silently overwrite | ✓ | ✓ |
| **Subtotal** | **2/2** | **1/2** |

**Observations**:
- with_skill posed the exact choice MAP-CODE-003 specifies: "Treat existing docs as authoritative (skeletons only for uncovered segments) or supersede them?"
- without_skill saw the problem but reached for "dispatch to the arrow-maintenance skill" as its mental model — which isn't wrong in this case but doesn't frame the choice the way MAP-CODE-003 specifies.

## Eval 2: redirect-on-fully-lid-no-overlay

| Assertion | with_skill | without_skill |
|---|---|---|
| Detects fully-LID state but missing `docs/arrows/` | ✓ | ✓ |
| Redirects to `/arrow-maintenance` | ✓ (clean, single recommendation) | partial (offered 3 options including re-mapping) |
| No new LLDs, EARS specs, or arrow docs created | ✓ | ✓ |
| **Subtotal** | **3/3** | **1.5/3** |

**Observations**:
- with_skill produced the clean redirect specified in MAP-CODE-004: "`/map-codebase` is for brownfield bootstrap — wasted work here. Run `/arrow-maintenance` instead." One recommendation, clear.
- without_skill offered three options (add overlay / audit / re-map), which is technically reasonable but adds decision fatigue. The redirect's value is in decisiveness.

## Spec coverage exercised (testable portion)

- MAP-CODE-001 (scope question at invocation, mode-implied)
- MAP-CODE-002 (subagent parallelism offer)
- MAP-CODE-003 (partial-LID dispatch)
- MAP-CODE-004 (fully-LID redirect to /arrow-maintenance)
- MAP-CODE-005, -006 (sweep extraction, no segmentation)
- MAP-CODE-008 (lens-based multi-clustering with anti-patterns excluded)
- MAP-CODE-012 (no generation until approval)
- MAP-CODE-024 (token-intensity warning)
- MAP-CODE-025, -026 (read every file + structured reporting)
- MAP-CODE-028 (Five Critical Rules discipline visible in behavior)

Specs deferred to iteration 2 (require multi-turn user-in-loop):
- MAP-CODE-007 (sweep overflow + per-subagent files)
- MAP-CODE-009 (subagent conflict flagging)
- MAP-CODE-010, -011, -012 (reconciliation interaction)
- MAP-CODE-013 through -020 (artifact generation with STOPs)
- MAP-CODE-019 (spec-ID prefix collision → ask for namespacing)
- MAP-CODE-021, -022 (flesh-out prompt)
- MAP-CODE-023 (slicing granularity)
- MAP-CODE-027 (STOP after each artifact sub-step)
- MAP-CODE-029, -030 (brownfield EARS status semantics, `[inferred]` markers)
- MAP-CODE-031 (terminal verification via lid-setup with caller-provided mode)
- MAP-CODE-032, -033 (capacity-constraint override)

## Verdict

**Cascade validated on the testable portion.** Largest baseline-vs-skill delta of all three skills (+56%) — map-codebase's structure (token warning, scope-vs-mode conflation, multi-lens Phase 2, clean dispatch) is genuinely hard to replicate from an unguided agent's prior. The skill prose encodes real, learned discipline.

**Iteration plan**:
- Iteration 2 runs should exercise the full multi-phase flow with a human reviewer in the loop, using the eval-viewer for per-phase qualitative review.
- Candidate additions: capacity-constraint override path (MAP-CODE-032/033), spec-ID prefix collision prompt (MAP-CODE-019), STOP discipline after each artifact sub-step (MAP-CODE-027).
