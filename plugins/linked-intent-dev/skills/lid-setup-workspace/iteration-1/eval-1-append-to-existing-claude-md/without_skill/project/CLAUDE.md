# My Project

## Conventions

- Prefer functional style where possible.
- Use TypeScript strict mode.
- Don't add dependencies without discussion.

## Linked-Intent Development (LID)

This project follows linked-intent development: all code changes start from
explicit intent that cascades through design documents down to code. Design
before code, and keep documents and code in sync.

### Flow

```
HLD → LLDs → EARS specs → Implementation Plan → Tests → Code
```

- **New features**: Walk the full flow. Write/update the HLD, add or update
  the relevant LLD, draft EARS specs, then a short implementation plan, then
  tests, then code.
- **Bug fixes**: Skip document creation. Verify existing specs, tests, and
  code still align with intent, fix the drift, and update any docs that turn
  out to be wrong.
- **If unsure**: Use the full flow.

Docs reflect current intent (mutation, not an append-only history). When
intent changes, update the docs in place.

### Where things live

| What | Where |
|---|---|
| High-level design | `docs/high-level-design.md` |
| Low-level designs | `docs/llds/` |
| EARS specs | `docs/specs/` |
| Implementation plans | `docs/planning/` |

### EARS specs

Specs use Easy Approach to Requirements Syntax (EARS) with semantic IDs of
the form `{FEATURE}-{TYPE}-{NNN}` (for example `AUTH-UI-001`). Each spec
carries a status marker:

- `[x]` implemented
- `[ ]` active gap (not yet implemented)
- `[D]` deferred

### Code annotations

Link code back to the specs it satisfies with `@spec` comments so intent is
traceable from either direction:

```ts
// @spec AUTH-UI-001, AUTH-UI-002
export function signIn(...) { ... }
```

Test files should reference the same spec IDs.
