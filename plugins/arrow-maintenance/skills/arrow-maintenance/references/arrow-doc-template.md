# Arrow Doc Template

Use this structure when creating a new arrow doc in `docs/arrows/`.

```markdown
# Arrow: {name}

One-line description of what this domain covers.

## Status

**{STATUS}** — last audited YYYY-MM-DD (git SHA `{audited_sha}`). One-line summary of current state.

## References

### HLD
- docs/high-level-design.md (relevant section)

### LLD
- docs/llds/{name}.md

### EARS
- docs/specs/{name}-specs.md (spec count)

### Tests
- path/to/test/files

### Code
- path/to/source/files

## Architecture

**Purpose:** What this subsystem does.

**Key Components:**
1. Component A — role
2. Component B — role

## Spec Coverage

| Category | Spec IDs | Implemented | Deferred | Gaps |
|----------|----------|-------------|----------|------|
| Core     | XX-001 to XX-005 | 5 | 0 | 0 |
| Advanced | XX-006 to XX-010 | 2 | 3 | 0 |

**Summary:** 7 of 10 active specs implemented; 3 deferred.

## Key Findings

1. **Finding title** — explanation with file:line references
2. **Finding title** — explanation

## Work Required

### Must Fix
1. Description (spec IDs affected)

### Should Fix
2. Description

### Nice to Have
3. Description
```

## Guidelines

- Keep arrow docs **focused on status and references**, not design (that's the LLD's job).
- Use file:line references so findings are greppable.
- The **References** and **EARS Coverage** sections are *derived views* — they are regenerated during audit from source scans (grep for `@spec`, file existence checks, eval-citation checks). Do not hand-edit them in ways that contradict source.
- The "Work Required" section drives the `next` field in `index.yaml`.
- For brownfield-inferred segments, `Key Findings` may record observations without clear design intent; flag these so they can be confirmed or refuted in later sessions.
