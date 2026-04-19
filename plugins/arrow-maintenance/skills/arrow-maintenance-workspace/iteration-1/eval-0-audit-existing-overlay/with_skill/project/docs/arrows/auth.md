# Arrow: auth

Authentication.

## Status

**MAPPED** — last audited 2026-04-18 (git SHA `efa20068050b7dd75b8eedf5a8cb84d12570f9e2`). Design docs in place; no tests or code exist yet, so spec coverage is unverified.

## References

### HLD
- docs/high-level-design.md (stub — no section for auth yet)

### LLD
- docs/llds/auth.md

### EARS
- docs/specs/auth-specs.md (1 spec: AUTH-001)

### Tests
- (none)

### Code
- (none)

## Spec Coverage

| Category | Spec IDs | Implemented | Deferred | Gaps |
|----------|----------|-------------|----------|------|
| Core     | AUTH-001 | 0           | 0        | 1    |

**Summary:** 1 active behavioral spec; 0 eval assertions citing it. Coverage cannot be verified until tests exist.

## Key Findings

1. **No eval coverage for AUTH-001** — spec is marked `[x]` in `docs/specs/auth-specs.md` but no test file cites the spec ID. Either the implementation is missing, or tests exist but are unlinked.
2. **HLD is a stub** — `docs/high-level-design.md` contains only a title; no auth section to anchor the arrow doc's HLD reference.
3. **No code or tests linked** — arrow doc's Tests and Code sections are empty because no such files exist yet.

## Work Required

### Must Fix
1. Add an eval assertion for AUTH-001, or downgrade the `[x]` marker to `[ ]` until implemented.

### Should Fix
2. Expand the HLD with an Authentication section so the arrow doc's HLD reference is meaningful.

### Nice to Have
3. Populate Tests and Code reference lists once implementation begins.
