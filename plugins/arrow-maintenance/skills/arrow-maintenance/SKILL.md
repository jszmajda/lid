---
name: arrow-maintenance
description: Manage the arrow of intent tracking system for complex projects. Use when working with docs/arrows/ directory, auditing spec-to-code coherence, mapping new system areas, or maintaining the arrow dependency graph. Compatible overlay on top of linked-intent-dev — adds navigation and tracking for projects too large to hold in one context window.
---

# Arrow Maintenance

The arrow system tracks design-to-code coherence across a complex project. It's a scaling layer on top of the linked-intent-dev workflow — when a project has too many LLDs and spec files to navigate from memory, arrows provide the map.

## Core Concepts

**Arrow of intent**: The chain `HLD → LLDs → EARS → Tests → Code`. Each arrow represents one domain or subsystem with its own chain.

**Arrow doc** (`docs/arrows/{name}.md`): Tracks one arrow's references, implementation status, findings, and remaining work.

**Index** (`docs/arrows/index.yaml`): The dependency graph. Load this first to understand what's available, what's blocked, and what needs work.

## Starting a Session

1. Read `docs/arrows/index.yaml`
2. Find arrows with no blockers: check `blockedBy: []`
3. Read the arrow doc for your target domain
4. Follow its references to LLDs, spec files, and code

## Arrow Statuses

| Status | Meaning |
|--------|---------|
| UNMAPPED | Not yet explored |
| MAPPED | Structure known, specs not verified against code |
| AUDITED | Specs verified — implementation status understood |
| OK | Fully coherent — all specs implemented |
| PARTIAL | Some specs missing or partial |
| BROKEN | Code and docs have diverged significantly |
| STALE | Docs exist but outdated |
| OBSOLETE | Superseded, kept for historical reference |
| MERGED | Combined into another arrow (use merged_into field) |

**Normal progression**: UNMAPPED → MAPPED → AUDITED → OK

## Workflows

### Auditing an Arrow

1. Read arrow doc references (LLD, spec file, code locations)
2. For each EARS spec, grep codebase for implementing code
3. Verify behavior matches spec intent
4. Record in arrow doc: implemented / partial / missing per spec category
5. Update index.yaml: status, audited date, next action, drift

### Mapping a New Arrow

1. Explore code and docs for the domain (take a "core sample")
2. Add entry to `arrows` section in index.yaml
3. Create `docs/arrows/{name}.md` — see [arrow-doc-template.md](references/arrow-doc-template.md)
4. Remove from `unmapped` section if listed there

### Fixing an Arrow

When specs and code disagree, determine which is wrong:
- **Code is wrong**: Write failing tests first, then fix code to match specs
- **Specs are wrong**: Update specs, cascade changes (follow linked-intent-dev)
- **Both**: Fix specs first, then code

After fixing, update arrow doc and index.yaml status.

### Retiring an Arrow

1. Set status to OBSOLETE in index.yaml
2. Clear blockedBy/blocks relationships
3. Set next and drift to null
4. Update arrow doc with what superseded it

### Splitting / Merging

**Split** (one → two): Create new arrow, move relevant specs, cross-reference both arrow docs.

**Merge** (two → one): Consolidate into primary, set secondary to `status: MERGED` with `merged_into: primary-name`.

## Index.yaml Schema

```yaml
schema_version: 1
last_updated: YYYY-MM-DD

arrows:
  domain-name:
    status: AUDITED
    sampled: YYYY-MM-DD
    audited: YYYY-MM-DD
    blocks: []
    blockedBy: []
    detail: domain-name.md
    next: "next action needed"
    drift: "spec-code divergence description, or null"

unmapped:
  # Items not yet explored
```

## EARS Spec Status Markers

Arrow maintenance reads and summarizes spec statuses from `docs/specs/` files. The markers (defined in linked-intent-dev) are:

- `[x]` — implemented
- `[ ]` — active gap
- `[D]` — deferred (correct intent, not needed yet)

Specs that are no longer wanted should be **deleted**. Git preserves history.

Summarize in arrow docs: "15 of 20 active specs implemented; 5 deferred"

## Relationship to linked-intent-dev

The linked-intent-dev skill defines the core workflow: HLD → LLD → EARS → Tests → Code. Arrow maintenance adds:
- **Navigation**: index.yaml tells agents where to start
- **Tracking**: Arrow docs record what's implemented vs. missing
- **Dependencies**: blockedBy/blocks relationships prevent wasted work

Use linked-intent-dev for individual changes. Use arrow-maintenance for system-wide coherence.
