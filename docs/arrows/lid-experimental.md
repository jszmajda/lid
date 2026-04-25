# Arrow: lid-experimental

The opt-in third plugin — a structural container for novel LID capabilities under evaluation. The container itself has no behavioral surface; each experiment is its own arrow segment.

## Status

**MAPPED** — bootstrapped on 2026-04-25 (git SHA `b64c439`). One active experiment (`bidirectional-differential`), tracked in its own segment. Container LLD status line refreshed in this run.

## References

### HLD
- `docs/high-level-design.md` § Architecture / Plugins (lid-experimental, opt-in); § Key Design Decisions / Experimental features as a separate plugin

### LLD
- `docs/llds/lid-experimental.md` (container)

### EARS
- None on the container itself. Per the LLD: *"This LLD is structural and currently has no behavioral surface of its own — the plugin is a container, and EARS coverage attaches to individual experiments."*

### Tests / Evals
- None on the container.

### Code (plugin scaffolding)
- `plugins/lid-experimental/.claude-plugin/plugin.json` — manifest with the opt-in description
- `plugins/lid-experimental/skills/` — one subdirectory per experiment (currently: `bidirectional-differential/`)

## Architecture

**Purpose:** Houses experiments under evaluation for promotion into core (`linked-intent-dev` or `arrow-maintenance`). Resolves the tension between Goal 2 (minimum system) and the need for somewhere to try novel surface under realistic conditions. Three properties make the separation load-bearing: opt-in installation, same-arrow obligation as core, explicit promotion-or-retirement lifecycle.

**Key Components:**
1. The plugin shell — manifest, skills directory, no shared code or shared state across experiments.
2. Per-experiment subdirectories — each a self-contained skill so promotion or retirement is a single-directory operation.

## Spec Coverage

| Category | Spec IDs | Implemented | Active gap | Deferred |
|---|---|---|---|---|
| Container | (none — see note) | — | — | — |

Container has no specs. Per-experiment specs live in sibling segments (currently: `bidirectional-differential`).

## Key Findings

1. **Container has no spec file by design.** When/if the container itself acquires behavioral surface (e.g., an experiment-listing command, shared eval scaffolding), `docs/specs/lid-experimental-specs.md` should be created at that point — open question per the LLD § *Open Questions / Eval scaffolding*.
2. **Community-feedback mechanism is aspirational.** Channel, cadence, and aggregation are deferred per the LLD § *Community Feedback*. The first experiment shapes the answers.

## Work Required

### Nice to Have
1. As additional experiments land, add each as its own segment under `taxonomy.experimental` in `index.yaml` rather than nesting them into this container's segment.
