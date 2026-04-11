# Implementation Plan Templates

Implementation plans provide checkbox-based execution guides tied to EARS specifications.

## File Location

Create plans in `/docs/planning/` with date suffix:
- `user-authentication-implementation-plan.2025-01-15.md`
- `checkout-flow-refactor.2025-02-01.md`

Move completed plans to `/docs/planning/old/` when finished.

## Standard Structure

```markdown
# [Feature] Implementation Plan

**Created**: YYYY-MM-DD
**Owner**: [Team/Person]
**Status**: Planning | In Progress | Complete
**Design Doc**: `/docs/llds/[design-doc].md`
**EARS Specs**: `/docs/specs/[specs-doc].md`

## Overview

Brief description of what's being implemented.

## Success Criteria

Measurable outcomes that define success.

## Implementation Phases

### Phase 1: [Name]

**Goal**: What this phase achieves

#### Deliverables

1. **[Component Name]**
   - **Specs**: AUTH-UI-001, AUTH-UI-002
   - Details...

#### Testing Requirements

- ✅ **AUTH-UI-001**: Test description
- ✅ **AUTH-UI-002**: Test description

#### Definition of Done

- [ ] All deliverables implemented with @spec annotations
- [ ] Unit tests passing
- [ ] Code review approved

### Phase 2: [Name]
...

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| ... | ... |

## References

- Links to related docs
```

## Phase Structure

Each phase should include:

### 1. Goal Statement
Brief description of what the phase achieves.

### 2. Deliverables
Numbered list with spec references:

```markdown
#### Deliverables

1. **Login form component**
   - **Specs**: AUTH-UI-001, AUTH-UI-002, AUTH-UI-003
   - Email/password inputs with validation
   - "Remember me" checkbox
   - Error state handling

2. **Authentication service**
   - **Specs**: AUTH-API-001, AUTH-API-002, AUTH-API-003
   - JWT token management
   - Refresh token rotation
   - Logout cleanup
```

### 3. Testing Requirements
Checkmarks with spec references:

```markdown
#### Testing Requirements

**Unit tests** (verify specs with @spec annotations):
- ✅ **AUTH-UI-004 to AUTH-UI-008**: Form validation
- ✅ **AUTH-API-001**: Token generation
- ✅ **AUTH-API-003**: Token refresh

**Integration tests**:
- ✅ **AUTH-UI-015**: Full login flow
- ✅ **AUTH-API-010**: API authentication middleware

**E2E tests**:
- ✅ **AUTH-UI-020**: Login from landing page
- ✅ **AUTH-UI-021**: Session persistence across reload
```

### 4. Definition of Done
Checklist with spec coverage:

```markdown
#### Definition of Done

- [ ] **All deliverables implemented** with @spec annotations
- [ ] **Phase specs verified**: AUTH-UI-001 through AUTH-UI-015 (15 total)
- [ ] **Unit tests passing** (100% coverage for business logic)
  - Validation specs verified (AUTH-UI-004 to AUTH-UI-008)
  - Token specs verified (AUTH-API-001 to AUTH-API-003)
- [ ] **Integration tests passing**
  - Auth flow specs verified (AUTH-UI-015, AUTH-API-010)
- [ ] **Security audit completed**
  - Token storage reviewed
  - CSRF protection verified
- [ ] **Code review approved** by 2+ engineers
- [ ] **Deployed to staging**
```

## Spec Traceability

Summarize which specs each phase covers:

```markdown
## Requirements Traceability

### Phase 1 (Core Auth)
- UI Components: AUTH-UI-001 through AUTH-UI-010
- API Endpoints: AUTH-API-001 through AUTH-API-005
- Security: AUTH-SEC-001 through AUTH-SEC-003

**Total Phase 1 Requirements**: 18

### Phase 2 (Enhanced Security)
- MFA: AUTH-MFA-001 through AUTH-MFA-008
- Session Management: AUTH-SES-001 through AUTH-SES-004

**Total Phase 2 Requirements**: 12
```

## Progress Updates

Check off items as you complete them:

```markdown
#### Definition of Done

- [x] **All deliverables implemented** with @spec annotations
- [x] **Unit tests passing**
- [ ] **Integration tests passing**  <-- Currently here
- [ ] **Code review approved**
```

## Risk Assessment Table

Include for each phase:

```markdown
## Risk Assessment

### High Risk

**1. Third-party auth provider outage**
- **Mitigation**: Implement fallback to email/password
- **Fallback**: Graceful degradation with user notification

### Medium Risk

**2. Token refresh race conditions**
- **Mitigation**: Mutex lock on refresh, queue pending requests
- **Fallback**: Force re-login on conflict
```

