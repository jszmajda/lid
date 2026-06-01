# Changelog

## [1.2.0]

### Migration (v1.1 → v1.2)
- Node-as-folder: each LLD lives in docs/intent/<node>/ as <node>-design.md (plus <node>-specs.md).
- A design doc whose `prefix:` frontmatter is an array is an unresolved multi-prefix marker; resolve by collapse into <LEAF>-<TYPE> facets, promote to a sub-HLD over child leaves, or split into sibling leaves. A `prefix:` array must not survive the walk.
