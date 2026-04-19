# EARS Specs

Structured requirements using **EARS** (Easy Approach to Requirements Syntax).

Each spec file groups related requirements for one feature and lives at `docs/specs/<feature>.md`.

## ID Format

`{FEATURE}-{TYPE}-{NNN}`

- **FEATURE**: Short uppercase tag, e.g. `AUTH`, `PAY`, `SEARCH`.
- **TYPE**: Layer or concern, e.g. `UI`, `API`, `DB`, `BIZ`, `INFRA`.
- **NNN**: Zero-padded sequence number, unique within the feature+type pair.

Examples: `AUTH-UI-001`, `PAY-API-014`, `SEARCH-DB-003`.

## Status Markers

- `[x]` implemented and verified
- `[ ]` active gap — specified but not yet implemented
- `[D]` deferred — intentionally not implemented now

## EARS Patterns

- **Ubiquitous**: "The system shall <behavior>."
- **Event-driven**: "When <trigger>, the system shall <response>."
- **State-driven**: "While <state>, the system shall <behavior>."
- **Unwanted behavior**: "If <condition>, then the system shall <response>."
- **Optional feature**: "Where <feature is included>, the system shall <behavior>."

See `_template.md` for a per-feature spec file template.
