# urlshort example

## LID Mode: Full

## Linked-Intent Development (MANDATORY)

**Consult the `linked-intent-dev` skill for ALL code changes.** All changes flow through the arrow of intent in one direction:

```
HLD → LLDs → EARS → Tests → Code
```

This is an intent-only LID example. When an implementation is generated here, the `linked-intent-dev` skill guides the agent through HLD check → LLD check → EARS → intent-narrowing edge audit → tests-first → code, with stops between each phase.

### Navigation

| What you need | Where to look |
|---|---|
| High-level design | `docs/high-level-design.md` |
| Low-level designs | `docs/llds/` |
| EARS specs | `docs/specs/` |

### Terminology

- **HLD**: High-Level Design.
- **LLD**: Low-Level Design — detailed component design. One per intent component.
- **EARS**: structured one-line requirements with globally unique IDs in `docs/specs/`. Markers: `[x]` implemented, `[ ]` active gap, `[D]` deferred.

### Code annotations

When implementation is generated, code and tests should carry `@spec` comments citing EARS IDs:

```typescript
// @spec USH-CORE-001
export function encodeShortCode(id: number): string { /* ... */ }
```

Place the annotation at the entry point of the behavior's implementation graph, not every helper.
