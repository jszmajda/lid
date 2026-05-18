# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Linked-Intent Development (MANDATORY)

This project uses **Linked-Intent Development (LID)**. All code changes start with intent:

```
HLD → LLDs → EARS → Tests → Code
```

- **New features**: Full workflow (HLD → LLD → EARS → Plan → Tests → Code)
- **Bug fixes**: Coherence check only (verify existing specs/tests/code align)
- **If unsure**: Use the full workflow

Mutation, not accumulation — docs reflect current intent, not history.

### Navigation

| What you need | Where to look |
|---|---|
| High-level design | `docs/high-level-design.md` |
| Low-level designs | `docs/llds/` |
| EARS specs | `docs/specs/` |
| Implementation plans | `docs/planning/` |

### Terminology

- **HLD**: High-level design — system-wide architecture and intent
- **LLD**: Low-level design — detailed component design docs in `docs/llds/`
- **EARS**: Easy Approach to Requirements Syntax — structured requirements in `docs/specs/`. Markers: `[x]` implemented, `[ ]` active gap, `[D]` deferred
- **Arrow**: A traced dependency from HLD through code

### Semantic IDs

EARS specs use semantic IDs in the format `{FEATURE}-{TYPE}-{NNN}`, e.g. `AUTH-UI-001`, `PAY-API-003`.

### Code Annotations

Annotate code with `@spec` comments linking to EARS IDs:

```
// @spec AUTH-UI-001, AUTH-UI-002
```

Test files also reference specs for traceability.

### EARS Patterns

Use these EARS phrasings in specs:

- **Ubiquitous**: "The system shall <do X>."
- **Event-driven**: "When <trigger>, the system shall <response>."
- **State-driven**: "While <state>, the system shall <behavior>."
- **Unwanted behavior**: "If <condition>, then the system shall <response>."
- **Optional feature**: "Where <feature is included>, the system shall <behavior>."

### Workflow

1. Draft or update `docs/high-level-design.md` with the big-picture intent.
2. Break it into LLDs under `docs/llds/<component>.md` for each component/subsystem.
3. For each LLD, write EARS specs under `docs/specs/<feature>.md` with semantic IDs.
4. Create an implementation plan under `docs/planning/<feature>.md`.
5. Write tests that reference spec IDs (`@spec` annotations).
6. Implement the code, annotating with `@spec` tags.
7. Flip status markers `[ ]` -> `[x]` as specs are satisfied.
