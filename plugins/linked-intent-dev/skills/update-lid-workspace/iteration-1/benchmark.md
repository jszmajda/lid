# update-lid eval iteration 1 — benchmark

**Date**: 2026-04-18
**Skill**: update-lid
**Iteration**: 1

## Summary

| Configuration | Pass rate | Assertions passed |
|---|---|---|
| **with_skill** | **100%** | 13/13 |
| without_skill (baseline) | 62% | 8/13 |
| Delta | **+38%** | +5 |

The skill produces the specified behavior across all three test cases. The baseline — same prompts, no skill guidance — makes up its own conventions and fails the assertions that depend on LID-specific conventions (mode marker, directives-block detection, no-planning rule, idempotency).

## Eval 0: bootstrap-empty-project

| Assertion | with_skill | without_skill |
|---|---|---|
| docs/llds/ exists | ✓ | ✓ |
| docs/specs/ exists | ✓ | ✓ |
| docs/high-level-design.md populated | ✓ | ✓ |
| docs/planning/ NOT created | ✓ | ✗ (baseline created it) |
| CLAUDE.md has `## LID Mode: Full` | ✓ | ✗ (no mode marker) |
| CLAUDE.md has LID directives | ✓ (grep=2) | ✗ (grep=0) |
| Response summarizes changes | ✓ | ✓ |
| **Total** | **7/7** | **4/7** |

**Observations**:
- with_skill correctly routed through Full bootstrap path, created .gitkeep in empty dirs, populated HLD from template verbatim, and omitted the arrow-nav row (no overlay present).
- without_skill used its own mental model: created README.md at root, `_template.md` files in each docs/ subdir, and a `docs/planning/` directory — demonstrating the specific value the skill adds.

## Eval 1: append-to-existing-claude-md

| Assertion | with_skill | without_skill |
|---|---|---|
| Original content preserved | ✓ (4/4 patterns match) | ✓ (4/4) |
| LID directives appended | ✓ (grep=2) | ✓ (grep=1) |
| `## LID Mode:` heading | ✓ | ✗ (absent) |
| Response summarizes changes | ✓ | ✓ |
| **Total** | **4/4** | **3/4** |

**Observations**:
- Both configurations preserved existing content correctly. Skill adds the mode marker explicitly, which the baseline doesn't know to do.
- with_skill's output exactly matches the claude-md-template (mode marker + directives block format).
- without_skill invented its own directives structure and called the section "Linked-Intent Development (LID)" — close enough that the presence-detection assertion passed, but lacks the mode marker entirely.

## Eval 2: idempotent-on-configured-project

| Assertion | with_skill | without_skill |
|---|---|---|
| No file changes made | ✓ (CLAUDE.md and HLD bytes + mtime unchanged) | ✗ (created docs/planning/) |
| Response informs user what was detected | ✓ (full state report + drift surfaced) | partial (reported, but acted) |
| **Total** | **2/2** | **1/2** |

**Observations**:
- with_skill correctly detected convention drift (truncated directives in CLAUDE.md) and **surfaced it for user decision rather than auto-applying** — UPDATE-LID-005 behavior.
- without_skill misread the state and created `docs/planning/` because its mental model still includes Plan as a required artifact. This is exactly the kind of drift the cascade was designed to fix.

## Spec coverage exercised

Across the three evals, the assertions cited these UPDATE-LID spec IDs:

- UPDATE-LID-002, UPDATE-LID-003, UPDATE-LID-008, UPDATE-LID-009, UPDATE-LID-015, UPDATE-LID-016, UPDATE-LID-017, UPDATE-LID-020, UPDATE-LID-021, UPDATE-LID-022, UPDATE-LID-027, UPDATE-LID-028.

Specs not yet exercised by evals (candidates for iteration 2):
- UPDATE-LID-001 (sub-step reachability from `/linked-intent-dev` Phase 1 and from `/map-codebase` terminal verification).
- UPDATE-LID-004 (add mode marker when directives present but no marker).
- UPDATE-LID-005, UPDATE-LID-029 (drift reconciliation + decline path).
- UPDATE-LID-006, UPDATE-LID-011, UPDATE-LID-012, UPDATE-LID-013, UPDATE-LID-014 (mode transitions).
- UPDATE-LID-007, UPDATE-LID-010 (mode prompting + uncertainty).
- UPDATE-LID-018, UPDATE-LID-019 (legacy docs/planning/ handling).
- UPDATE-LID-023 (mode marker detection regex).
- UPDATE-LID-024, UPDATE-LID-025, UPDATE-LID-026 (arrow-maintenance coordination).

## Verdict

**Cascade validated**. The skill prose, as shipped, produces the specified behaviors. The delta vs. baseline (+38% pass rate) confirms the skill is adding measurable value. The one subtle observation — with_skill eval-2 surfaced drift rather than silently idempotent-no-op — is per UPDATE-LID-005 and is the intended behavior; the grader's "no file changes" assertion passed because surfacing does not modify files.

**Iteration plan**:
- No skill-prose iteration needed in this pass — all assertions passed.
- Expand iteration-2 evals to cover mode transitions, drift reconciliation paths, alias routing, and arrow-maintenance coordination.
- Run the same baseline-vs-skill benchmark on `arrow-maintenance` and `map-codebase` next.
