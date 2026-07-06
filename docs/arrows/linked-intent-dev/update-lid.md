# Arrow: linked-intent-dev / update-lid

The behavioral `update-lid` skill (invokable as `/update-lid`) — bootstraps a project into a LID-ready state and idempotently reconciles drift, mode changes, and version-walks on later runs. A leaf under the `LID` sub-HLD.

## Status

**AUDITED** — last audited 2026-06-07 (git SHA `65a143750760`). `update-lid` complete (53/53 specs `[x]`; workflow-doc vendoring 048-053 added after the last audit).

## References

### HLD
- `docs/high-level-design.md` § Architecture / Plugins (linked-intent-dev plugin); § Versioning

### LLD
- `docs/intent/linked-intent-dev/update-lid/update-lid-design.md` — this segment's leaf LLD.
- `docs/intent/linked-intent-dev/linked-intent-dev-design.md` — parent `LID` sub-HLD for plugin-level concerns (mode detection, spec ID format, eval-metadata schema).

### EARS
- `docs/intent/linked-intent-dev/update-lid/update-lid-specs.md` (53 specs, prefix `LID-UPDATE-*`)
- `plugins/linked-intent-dev/skills/update-lid/references/workflow-doc.md` (shipped vendoring asset, release-assembled)

### Tests / Evals
- `plugins/linked-intent-dev/skills/update-lid/evals/evals.json`
- `plugins/linked-intent-dev/skills/update-lid-workspace/` (skill-creator iteration outputs; iterations 1 and 2)

### Code (skill prompt and references)
- `plugins/linked-intent-dev/skills/update-lid/SKILL.md` + `references/claude-md-template.md`

No command stub — the skill is directly invokable as `/update-lid` per Claude Code's skills model.

## Architecture

**Purpose:** Put a project into a LID-ready state and keep it there. Owns the state-dispatch table (bootstrap / append-directives / add-LID-block / version-walk / reconcile / mode-transition), `## LID` block management (`- Mode:` / `- Version:`), detection signals, version-walk against the CHANGELOG's `Migration` sections, arrow-maintenance coordination, and show-what-changed verification.

## Spec Coverage

| Category | Spec range | Implemented | Active gap | Deferred |
|---|---|---|---|---|
| Invocation / Dispatch | LID-UPDATE-001..006 | 6 | 0 | 0 |
| Mode Interaction / Transitions | LID-UPDATE-007..014 | 8 | 0 | 0 |
| Directory / Legacy | LID-UPDATE-015..019, 035 | 6 | 0 | 0 |
| Idempotency / Detection | LID-UPDATE-020..024 | 5 | 0 | 0 |
| Arrow-Maintenance Coordination | LID-UPDATE-025..026 | 2 | 0 | 0 |
| Verification | LID-UPDATE-027..029 | 3 | 0 | 0 |
| Scope Declaration | LID-UPDATE-030..034 | 5 | 0 | 0 |
| Version-Walk | LID-UPDATE-036..043 | 8 | 0 | 0 |
| **Total** | | **43** | **0** | **0** |

**Summary:** All 43 active specs implemented; `update-lid` is feature-complete relative to its current LLD scope.

## Key Findings

1. **`@spec` annotations live in the spec header, not the skill prompt (LID-on-LID inversion).** `docs/intent/linked-intent-dev/update-lid/update-lid-specs.md` carries the `**Implementing artifacts**:` header; the `SKILL.md` body stays clean.

## Work Required

No must-fix items. Future work cascades from HLD-level changes when they land.
