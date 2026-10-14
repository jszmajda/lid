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
- `plugins/linked-intent-dev/skills/update-lid/evals/evals.json` — 14 fixtures; 8–13 cover workflow-doc vendoring (LID-UPDATE-048–053: no offer at bootstrap, user-requested vendoring, a preserved decline, version-walk re-sync, modified-doc surfacing, Aider bridge)
- `plugins/linked-intent-dev/skills/update-lid-workspace/` (skill-creator iteration outputs; iteration-4, 2026-08-08, 52/52 with-skill assertions, new-fixture baseline 63%; the 1.4.0 roster ran 11 configurations on the fixtures unchanged since, and fixtures 2, 6 and 8-10, revised afterward for on-demand vendoring, were piloted on claude-sonnet-5-5; from 2026-10-17 to 2026-10-24 seven more configurations ran all 14 fixtures as they stand)

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
| Version-Walk | LID-UPDATE-036..043, 054..057 | 12 | 0 | 0 |
| Workflow doc, memory directive, Aider (added after this table was first drawn) | LID-UPDATE-044..053 | 10 | 0 | 0 |
| **Total** (recounted from the spec file) | | **57** | **0** | **0** |

**Summary:** All 57 active specs implemented. The version-walk fires only on major.minor lag (`LID-UPDATE-037`, `039`); a project newer than the installed plugin, patch included, gets a suggestion to update the LID plugins and no changes (`054`); a malformed `- Version:` is read for what parses and walked (`055`); reconcile-conventions records the installed version when it applies an update (`057`); and the skill is model-invocable (`056`). Evals 14–20 exercise these, with eval 3 covering a malformed block that keeps its recorded version (`004`).

## Key Findings

1. **`@spec` annotations live in the spec header, not the skill prompt (LID-on-LID inversion).** `docs/intent/linked-intent-dev/update-lid/update-lid-specs.md` carries the `**Implementing artifacts**:` header; the `SKILL.md` body stays clean.

## Work Required

No must-fix items. Future work cascades from HLD-level changes when they land.
