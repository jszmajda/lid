# arrow-maintenance eval iteration 1 — benchmark

**Date**: 2026-04-18
**Skill**: arrow-maintenance (command mode)
**Iteration**: 1

## Summary

| Configuration | Pass rate | Assertions passed |
|---|---|---|
| **with_skill** | **100%** | 11/11 |
| without_skill (baseline) | ~64% | 7/11 |
| Delta | **+36%** | +4 |

## Eval 0: audit-existing-overlay

| Assertion | with_skill | without_skill |
|---|---|---|
| index.yaml `auth.audited` refreshed to today | ✓ | ✓ |
| index.yaml `auth.audited_sha` populated (non-null) | ✓ (real git SHA) | ✗ (left null) |
| Structured report distinguishing resolved vs. pending | ✓ | partial (no clear split) |
| All five audit classes addressed | ✓ | partial (3 of 5) |
| **Total** | **4/4** | **1.5/4** |

**Observations**: with_skill regenerated the arrow doc's derived views (`## References`, `## Spec Coverage`) from source scans, set `audited_sha` to the real git HEAD, and surfaced a finding (AUTH-001 marked `[x]` with no implementation) for user decision rather than auto-resolving. This is exactly the ARROW-MAINT-013/014 behavior. The baseline bumped `audited` but said "left as null since no code" on `audited_sha` — it didn't know the sha captures current state regardless of whether code has changed.

## Eval 1: bootstrap-overlay-from-lid-docs

| Assertion | with_skill | without_skill |
|---|---|---|
| docs/arrows/index.yaml created | ✓ | ✓ (YAML approximated) |
| Entries for both 'auth' and 'billing' | ✓ | ✓ |
| Both arrow docs created | ✓ (template-compliant) | ✓ (approximated) |
| No new HLD/LLD/EARS created | ✓ | ✓ |
| Initial status = `MAPPED` (canonical enum) | ✓ | ✗ (used "status checklist" instead) |
| **Total** | **5/5** | **3.5/5** (minus modification of CLAUDE.md unnecessarily) |

**Observations**: with_skill bootstrapped cleanly and even created `docs/arrows/README.md` from the template (nice touch, addresses cold-read finding #15). Baseline approximated the structure but used its own invented "status checklist" instead of the `UNMAPPED/MAPPED/AUDITED/OK` enum, and unnecessarily modified CLAUDE.md — exactly the kind of incidental damage the skill's discipline prevents.

## Eval 2: redirect-on-no-lid-docs

| Assertion | with_skill | without_skill |
|---|---|---|
| No changes to project | ✓ | ✓ |
| Response recommends /map-codebase or /lid-setup | ✓ | ✓ |
| **Total** | **2/2** | **2/2** |

**Observations**: Both configurations nailed this one. The "category error → redirect" response is intuitive enough that an unguided agent gets it right. Not a differentiator for the skill, but a useful check that the skill doesn't regress behavior agents get naturally.

## Spec coverage exercised

- ARROW-MAINT-002 (bootstrap from LID docs)
- ARROW-MAINT-003 (redirect on no LID)
- ARROW-MAINT-004, -005, -006, -008, -009, -010 (five audit classes)
- ARROW-MAINT-013 (reverse-orphan detection surfaces for user)
- ARROW-MAINT-014 (ambiguous findings surfaced not auto-applied)
- ARROW-MAINT-021, -022 (structured report with resolved/pending distinction)
- ARROW-MAINT-023 (index.yaml authority; derived views regenerated)
- ARROW-MAINT-024 (audited + audited_sha refreshed)
- ARROW-MAINT-027 (bootstrap uses MAPPED status)

Specs not yet exercised (candidates for iteration 2):
- ARROW-MAINT-001 (ambient vs command mode distinction when docs/arrows/ present)
- ARROW-MAINT-007 (incremental audit via audited_sha)
- ARROW-MAINT-011 (broken `docs/arrows/` state repair)
- ARROW-MAINT-012 (unambiguous fix application: status transitions, unmapped.docs cleanup)
- ARROW-MAINT-015, -016 (unmapped.docs handling)
- ARROW-MAINT-017 (split/merge/rename atomic cross-reference walk)
- ARROW-MAINT-018 (candidate split surfaces for user)
- ARROW-MAINT-025, -026 (coherence-script delegation)

## Verdict

**Cascade validated.** The skill produces the specified behaviors on all three test cases. The baseline-vs-skill delta (+36%) matches lid-setup's result (+38%), confirming the skill adds measurable, consistent value.

**Notable find**: with_skill eval-0 surfaced a genuine audit finding (AUTH-001 marked `[x]` with no implementation) that the baseline didn't catch. The skill is not just performing the spec'd behaviors — it's producing output more useful to the user.

**Iteration plan**:
- No skill-prose iteration needed from these three evals.
- Iteration 2 should cover incremental audit (ARROW-MAINT-007), rename lifecycle (ARROW-MAINT-017), unmapped.docs cleanup (ARROW-MAINT-015/016), and coherence-script delegation (ARROW-MAINT-025).
