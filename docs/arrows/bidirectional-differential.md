# Arrow: bidirectional-differential

The first `lid-experimental` experiment — audits EARS↔code coherence by spawning two parallel fresh `claude -p` sessions per spec (A-direction reconstructs code from EARS; B-direction reconstructs EARS from stripped code) and classifies the drift between their outputs and the real artifacts.

## Status

**MAPPED** — bootstrapped on 2026-04-25 (git SHA `b64c439`). All 22 BIDIFF specs implemented and marked `[x]`. One residual drift: BIDIFF-007's prose references a reference file (`stripping-rules.md`) that was consolidated into `audit-protocol.md`.

## References

### HLD
- `docs/high-level-design.md` § Key Design Decisions / Experimental features as a separate plugin (governs all experiments under `lid-experimental`)

### LLD
- `docs/llds/lid-experimental/bidirectional-differential.md` (sub-LLD)
- `docs/llds/lid-experimental.md` § Active Experiments / bidirectional-differential (parent container's pointer)

### EARS
- `docs/specs/lid-experimental-bidirectional-differential-specs.md` (22 specs, prefix `BIDIFF-*`)

### Tests / Evals
- `plugins/lid-experimental/skills/bidirectional-differential/evals/evals.json` (3 baseline fixtures: `bd-coherent-bounded-matrix`, `bidirectional-drift-missing-subdecision`, `b-only-drift-unstated-invariant`)
- `plugins/lid-experimental/skills/bidirectional-differential-workspace/iteration-1/` — workspace runs against the three eval fixtures

### Code (skill prompt and references)
- `plugins/lid-experimental/skills/bidirectional-differential/SKILL.md`
- `plugins/lid-experimental/skills/bidirectional-differential/references/` — `audit-protocol.md` (full six-step protocol; includes stripping rules and split-result mechanics referenced from individual specs), `classification-codes.md`, `scoping-conversation.md`, `audit-report-template.md`
- `plugins/lid-experimental/commands/differential-audit.md` (plugin-level command stub)

### Reserved output namespace
- `docs/arrows/experiments/bidirectional-differential/{segment-name}/{EARS-ID}.md` — per-EARS audit records produced by `/differential-audit` runs. Currently unpopulated in this repo.

## Architecture

**Purpose:** Detect EARS↔code drift that formal/structural engines (type systems, CodeQL, test-witness, LemmaScript) cannot see — operational-halo drift, decomposition gaps, missing sub-decisions, unstated invariants. Two-direction blind reconstruction: A-direction generates code from EARS only; B-direction reconstructs EARS from stripped code only. Within-direction variance plus between-direction alignment yields one of six classification codes (`BD-COHERENT`, `A-ONLY-DRIFT`, `B-ONLY-DRIFT`, `BIDIRECTIONAL-DRIFT`, `INCONSISTENT-BLIND`, `UNANNOTATABLE`).

**Key Components:**
1. Scoping conversation — natural-language → arrow → EARS mapping; cost-estimate confirmation before spawning subprocesses.
2. Six-step audit protocol — input resolution, identifier stripping, parallel `claude -p` spawns (N runs per direction, default 3), classification, per-EARS audit-record write.
3. Reserved output subtree — `docs/arrows/experiments/bidirectional-differential/` (sanctioned namespace per `arrow-maintenance` LLD § *Experiment-produced artifacts*).

## Spec Coverage

| Category | Spec range | Implemented | Active gap | Deferred |
|---|---|---|---|---|
| All BIDIFF | BIDIFF-001..023 (no -004) | 22 | 0 | 0 |

**Summary:** 22 of 22 active specs implemented. Reconciled in this audit run — markers had been stale since commit `b64c439`.

## Key Findings

1. **BIDIFF-007 spec text points at a non-existent reference file.** The spec says *"strip leaky identifiers from the code input per `references/stripping-rules.md`"*, but the stripping-rule content was consolidated into `references/audit-protocol.md` § *Step 2 / Stripping rule categories*. The behavior is implemented; the spec prose is stale. Recommended fix: reword BIDIFF-007 to reference `references/audit-protocol.md §Stripping rule categories`. Not auto-rewriting because spec edits should walk the LID arrow cascade with user confirmation.
2. **Hard precondition exercised in this session.** Invoking `/differential-audit` with no overlay aborted with the prescribed message (BIDIFF-005, BIDIFF-019) and spawned no `claude -p` sessions — observable evidence the precondition behavior is correct.
3. **Output namespace unused.** `docs/arrows/experiments/bidirectional-differential/` does not yet exist in this repo. First real audit run will create it.
4. **No skill-creator eval verification yet for this repo.** The three eval fixtures in `evals/evals.json` exist but have not been run against the current state. Workspace runs in `bidirectional-differential-workspace/iteration-1/` are from the implementation landing, not a post-spec-reconciliation run.

## Work Required

### Should Fix
1. Reword BIDIFF-007 to point at `references/audit-protocol.md §Stripping rule categories` instead of the non-existent `references/stripping-rules.md`. Walk the cascade per `linked-intent-dev` (LLD check, then EARS rewrite — no test or code change required since behavior is unchanged).

### Nice to Have
2. Run the eval suite (`plugins/lid-experimental/skills/bidirectional-differential/evals/evals.json`) to validate that the three baseline fixtures still classify as expected against the current SKILL.md.
