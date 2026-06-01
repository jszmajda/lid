# EARS Syntax Reference

EARS (Easy Approach to Requirements Syntax) provides structured patterns for writing unambiguous, testable requirements.

**Source**: https://alistairmavin.com/ears/

---

## Spec File Format

Specs live beside their design doc as `{node}-specs.md` within the node's folder under `docs/intent/`, with status markers. Each requirement is one line:

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

**An ID is the root-to-leaf path, an optional within-leaf type/area segment, and a zero-padded number.** The path segments are tree positions; the prefix *is* the position up to the leaf that owns the spec. At depth-2 — one HLD over a flat set of LLDs, the default — the path is a single segment, so an ID is `{LEAF}-{NNN}` (`AUTH-001`, `CART-003`) or, with a within-leaf facet, `{LEAF}-{TYPE}-{NNN}` (`AUTH-UI-001`, `CART-API-012`). As the tree deepens, the path extends one segment at a time: `PEVAL-RUN-014` for the runner under prompt-eval, `PEVAL-PERF-LOAD-003` for load-testing under performance under prompt-eval.

- **The path encodes ancestry up to the leaf.** Read left to right, the path names the owning leaf and every ancestor up to the root. The cascade boundary is the *leaf's* path: two specs whose leaf paths differ belong to different segments.
- **A leaf may append one within-leaf type/area segment.** After the leaf path, a project MAY add a single facet segment that groups specs *inside* that leaf — `AUTH-UI-001` (leaf `AUTH`, UI facet), `ENGINE-LEDGER-001` (leaf `ENGINE`, ledger area). The facet is not a tree node and not a cascade boundary; it is an in-leaf grouping convention. This is the long-standing `{FEATURE}-{TYPE}-{NNN}` shape.
- **A subtree greps by construction.** Because the path *is* the position, `grep PEVAL-PERF` gathers the whole performance subtree and `grep PEVAL-RUN` gathers the runner leaf, facet and all. Prefix-grep gathers specs and code regardless of where the path/facet split falls.
- **The leaf's `prefix:` frontmatter is authoritative for where the path ends.** The path/facet boundary is not always parseable from the ID string alone (`AUTH-UI-001` could be leaf `AUTH` + facet `UI`, or a leaf at path `AUTH-UI`). The owning leaf declares its EARS prefix in `prefix:` frontmatter; that frontmatter, with `index.yaml` when the overlay is present, is the bridge from an ID to its design doc. Prefix-grep still gathers specs and code without it.

Constraints:

- **Global uniqueness across the project.** Two specs cannot share an ID. Path concatenation enforces this by construction — two leaves in different parts of the tree have different paths.
- **Grep-friendliness.** IDs use uppercase letters, digits, and hyphens only. No other characters. `grep "PEVAL-RUN-014"` should find every annotation, test, and spec-file citation of a given ID, and a prefix grep should gather a subtree or a leaf.
- **ID stability.** Ordinary growth — adding or refining specs within a segment — never renames an ID. IDs are stable **except under a deliberate, tooled re-parent or rename**, which rewrites the affected paths across spec files, docs, and `@spec` annotations together as one atomic operation (owned by the arrow-maintenance plugin). Revisions mutate text, not IDs. Deletion is permanent; the number is not recycled.
- **Numbering on conflict.** When drafting a new spec whose path already exists, surface the collision rather than silently picking — most often the new spec belongs at a deeper segment, which extends the path and resolves the conflict.

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
