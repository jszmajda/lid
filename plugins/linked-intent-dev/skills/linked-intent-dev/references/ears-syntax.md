# EARS Syntax Reference

EARS (Easy Approach to Requirements Syntax) provides structured patterns for writing unambiguous, testable requirements.

**Source**: https://alistairmavin.com/ears/

---

## Spec File Format

Specs live in `/docs/specs/` files with status markers. Each requirement is one line:

```markdown
- [x] **{ID}**: {Requirement statement}
- [ ] **{ID}**: {Requirement statement}
- [D] **{ID}**: {Requirement statement}
```

### Status Markers

- `[x]` — **Implemented**: Code and tests exist that realize this spec
- `[ ]` — **Active gap**: Should be implemented, work to do
- `[D]` — **Deferred**: Correct intent, not needed yet (e.g., scaling optimization not needed at current user count)

### Removing Specs

**Delete specs that are no longer wanted.** Do not mark them — just remove the line. Git preserves history if the rationale needs to be recovered later. A spec's presence means the intent is current; absence means the intent was withdrawn.

### Example

```markdown
## User Authentication

- [x] **AUTH-UI-001**: The system shall display a login button on the home screen.
- [x] **AUTH-UI-002**: When the user taps the login button, the system shall navigate to the authentication flow.
- [ ] **AUTH-API-001**: The system shall validate JWT tokens on every authenticated API request.
- [D] **AUTH-API-002**: Where multi-factor authentication is enabled, the system shall require a second factor.
```

---

## Semantic ID Format

The default shape is `{FEATURE}-{TYPE}-{NNN}` — e.g., `AUTH-UI-001`, `CART-API-003`.

- **FEATURE**: prefix for the feature or segment (commonly 2–4 letters, e.g., `AUTH`, `CART`, `DASH`).
- **TYPE**: Component type (`UI`, `API`, `DATA`, `NAV`, `BE`, `PROC`).
- **NNN**: Sequential number, zero-padded.

**Extensible namespacing.** The format is flexible: longer IDs with additional segments are permitted when namespacing matters. `AUTH-LOGIN-UI-001` distinguishes login-UI specs from login-API specs. `BILLING-INVOICE-RENDERING-004` disambiguates nested features. Constraints:

- **Global uniqueness across the project.** Two specs cannot share an ID, even across different LLDs.
- **Grep-friendliness.** IDs use uppercase letters, digits, and hyphens only. No other characters. `grep "FEATURE-TYPE-003"` should find every annotation, test, and spec file citation of a given ID.
- **ID stability.** Once assigned, an ID does not move. Revisions mutate text, not IDs. Deletion is permanent; the number is not recycled.
- **Namespacing on conflict.** When drafting a new spec whose natural prefix already exists for an unrelated feature, surface the collision and ask the user for a disambiguating namespace segment rather than silently picking.

Keep IDs stable — don't renumber when inserting requirements.

---

## EARS Requirement Patterns

### 1. Ubiquitous (always true)

**Pattern**: "The system shall..."

```
- **CART-UI-001**: The system shall display the item count in the cart icon.
```

### 2. Event-Driven (triggered by action)

**Pattern**: "When [trigger], the system shall..."

```
- **CART-UI-002**: When the user taps "Add to Cart", the system shall add the item and show a confirmation.
```

### 3. State-Driven (while condition is true)

**Pattern**: "While [state], the system shall..."

```
- **CART-UI-003**: While the cart is empty, the system shall display an empty state message.
```

### 4. Optional (feature-dependent)

**Pattern**: "Where [feature enabled], the system shall..."

```
- **AUTH-OPT-001**: Where biometric auth is enabled, the system shall prompt for Face ID before checkout.
```

### 5. Unwanted (error handling)

**Pattern**: "If [unwanted condition], then the system shall..."

```
- **CART-UI-004**: If the network request fails, then the system shall display cached data with an error banner.
```

---

## Scope Disambiguation

A spec should be interpretable correctly even if found via grep without its surrounding section or file context. The dangerous anti-pattern is a spec that **reads as a universal rule but is actually scoped to a specific mode, variant, or context** — it becomes an implementation trap when a second variant is added.

### Checklist

1. **Name the scope in the WHEN clause.** If a spec applies to a specific mode, pass, or context, state it explicitly — don't rely on the section header.
2. **Litmus test:** "If a second variant of this behavior existed, would this spec still be unambiguous?" If no, the scope is implicit and needs to be stated.
3. **Cross-file domain concepts:** When a spec references a concept defined in another spec file, include a brief parenthetical — not a full definition, but enough to prevent a plausible-but-wrong implementation.

### Watch ubiquitous specs

Ubiquitous specs ("The system shall...") are most vulnerable — they have no WHEN clause to carry scope. Ask: is this truly ubiquitous, or does it just feel that way because there's currently only one context?

### Examples

**Bad** — sounds universal, actually scoped to one notification channel:
```
- **NOTIF-BE-003**: Notifications shall use a 30-second delivery timeout.
```

**Good** — scope is explicit:
```
- **NOTIF-BE-003**: Both email and push notifications shall use a 30-second delivery timeout.
```

**Bad** — cross-file concept with no inline context:
```
- **CART-API-012**: When processing retry queue items, the system shall implement a 500ms delay between requests.
```

**Good** — parenthetical prevents wrong interpretation:
```
- **CART-API-012**: When processing retry queue items (failed payment attempts re-queued after gateway timeout), the system shall implement a 500ms delay between payment gateway requests.
```

---

## Code Annotations

Reference specs in implementation:

```typescript
// @spec CART-UI-001, CART-UI-002
export function CartIcon({ ... }) {
  // Implementation
}
```

In tests:

```typescript
// @spec CART-UI-002
it('adds item to cart on tap', () => {
  // Test implementation
});
```

---

## Traceability

In implementation plans, map specs to phases:

```markdown
## Phase 1: Core Cart UI
Specs: CART-UI-001 through CART-UI-010
```
