# Arrow: billing

Billing subsystem.

## Status

**MAPPED** — not yet audited. Overlay bootstrapped 2026-04-18 from existing LID docs; LLD is a stub and no EARS specs or code references have been discovered yet.

## References

### HLD
- docs/high-level-design.md

### LLD
- docs/llds/billing.md

### EARS
- _none found_

### Tests
- _none found_

### Code
- _none found_

## Architecture

**Purpose:** Billing — to be detailed in `docs/llds/billing.md`.

**Key Components:**
- _to be determined as LLD is fleshed out_

## Spec Coverage

| Category | Spec IDs | Implemented | Deferred | Gaps |
|----------|----------|-------------|----------|------|
| _none_   | _n/a_    | 0           | 0        | 0    |

**Summary:** No EARS specs authored yet.

## Key Findings

1. **LLD is a stub** — `docs/llds/billing.md` currently contains only a heading. Design content needs to be written before specs can be derived.
2. **No spec file yet** — no `docs/specs/billing-specs.md` exists; create one once the LLD is populated.
3. **No code or tests discovered** — bootstrap scan found no `@spec BILLING-*` annotations or test citations.

## Work Required

### Must Fix
1. Populate `docs/llds/billing.md` with the actual design content.
2. Author EARS specs in `docs/specs/billing-specs.md` derived from the LLD.

### Should Fix
3. Once specs exist, link implementing code and tests back to them with `@spec` annotations, then re-run `/arrow-maintenance` to transition this segment from MAPPED to AUDITED.

### Nice to Have
_none yet_
