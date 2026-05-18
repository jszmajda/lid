# Low-Level Designs (LLDs)

One file per major component. Each LLD should:

- Name the component and the HLD section it descends from
- Describe the component's responsibilities and public interface
- Call out data shapes, key algorithms, and error behavior
- Link to the EARS specs in `docs/specs/` that it implements

Suggested filename: `docs/llds/<component>.md`.

## Template

```markdown
# <Component> LLD

Parent: [High-Level Design](../high-level-design.md#<section>)

## Responsibility
What this component owns, and what it deliberately does not.

## Interface
Public API / entry points / events.

## Internals
Key data structures, control flow, error handling.

## Specs
- [SPEC-ID-001](../specs/<feature>.md) — short description
```
