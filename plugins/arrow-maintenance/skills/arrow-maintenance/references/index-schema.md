# `docs/arrows/index.yaml` Schema

The `index.yaml` is the manifest of all arrow segments in a project. It is authoritative for per-segment state (status, timestamps, dependencies). Agents load it first to orient before touching any per-segment arrow doc.

## Full schema

```yaml
schema_version: 2
last_updated: YYYY-MM-DD

# Taxonomy groups segments by domain cluster. Purely organizational.
taxonomy:
  {cluster-name}:
    - segment-name
    - segment-name
  {another-cluster}: standalone  # single-segment cluster

# The design tree of nodes. Leaf nodes are arrow segments (own EARS + an arrow
# doc); intermediate nodes (sub-HLDs) group children and own no segment. A flat
# depth-2 project simply has every node at the root level with no children.
arrows:
  {node-name}:
    status: UNMAPPED | MAPPED | AUDITED | OK | PARTIAL | BROKEN | STALE | OBSOLETE | MERGED
    parent: {node-name} | null    # parent in the design tree; null/omitted at the root level
    children: [node-name, ...]    # child nodes; present on intermediate (sub-HLD) nodes, omitted/empty on leaf segments
    sampled: YYYY-MM-DD           # when first mapped
    audited: YYYY-MM-DD | null    # when last audited (calendar date)
    audited_sha: <git-sha> | null # git HEAD SHA at last audit; enables incremental audit
    blocks: [other-segment, ...]  # segments blocked by this one
    blockedBy: [other-segment, ...] # segments this one depends on
    detail: {path}.md             # the doc to open on this node — a leaf's arrow doc (tree-mirrored under docs/arrows/); a sub-HLD's design doc (../intent/<path>.md), since a sub-HLD has no arrow doc
    next: "one-line next action or null"
    drift: "description of current drift or null"
    merged_into: {primary-segment}  # only present if status is MERGED

# Items found during mapping that don't yet belong to a segment.
# Arrow-maintenance cleans this up on each audit.
unmapped:
  docs:
    intent: [file-name.md, ...]
```

## Field notes

- **`schema_version`** — bump when the schema changes in a backwards-incompatible way. Agents can refuse to operate on a newer schema they don't understand. **v2** added the `parent`/`children` design-tree links and redefined `detail` as "the doc to open on this node."
- **`taxonomy`** — organizational only; arrow maintenance logic doesn't depend on taxonomy placement. Used by users to navigate large projects at a glance.
- **`parent` / `children`** — the design tree's nesting. Leaf nodes (arrow segments) own EARS specs and an arrow doc; intermediate nodes (sub-HLDs) group children and own neither. Agents walk these links to navigate a subtree (parent → children) rather than scanning the flat list. A leaf node's name is the leaf prefix of its path-concatenated EARS IDs, so re-parenting or renaming a node rewrites those IDs and their `@spec` annotations — a tooled, atomic operation, not a hand edit.
- **`status`** — see the enum table in the arrow-maintenance SKILL.md. `MERGED` segments keep their entry for tombstone purposes; `merged_into` points at the primary.
- **`sampled`** — first-mapped date. Doesn't change after initial mapping.
- **`audited` + `audited_sha`** — both get refreshed on each audit pass. `audited` is human-readable for staleness judgment; `audited_sha` enables incremental audit.
- **`blocks` / `blockedBy`** — dependency graph. Segments with non-empty `blockedBy` cannot be fully audited until their dependencies are `AUDITED` or `OK`. Agents preferentially pick unblocked segments for active work.
- **`detail`** — the doc to open on this node. A leaf segment points to its arrow doc (a path relative to `docs/arrows/`); a sub-HLD points to its design doc (`../intent/<path>.md`), since a sub-HLD has no arrow doc of its own.
- **`next`** — short actionable sentence describing pending work. Nil when the segment is `OK` or `OBSOLETE`.
- **`drift`** — short description of current drift, if any. Nil when coherent.
- **`unmapped`** — things found during exploration that don't yet belong to a segment. `linked-intent-dev` may add to this when it finds an unmapped doc; `arrow-maintenance` cleans it up on each audit.

## Querying

Agents query this file with `yq`, or read it directly for small projects. Example queries:

```bash
# Find all unblocked segments
yq '.arrows | to_entries | .[] | select(.value.blockedBy | length == 0) | .key' index.yaml

# Find segments needing work
yq '.arrows | to_entries | .[] | select(.value.status != "OK" and .value.status != "OBSOLETE") | .key' index.yaml

# Get next action for a segment
yq '.arrows["auth"].next' index.yaml
```

## Schema extensions

Extensions (new status values, additional metadata) are permitted but should be added to `docs/intent/arrow-maintenance/arrow-maintenance-design.md` first so the schema stays coherent across projects. Project-specific extensions go in the project's own `docs/arrows/README.md`.
