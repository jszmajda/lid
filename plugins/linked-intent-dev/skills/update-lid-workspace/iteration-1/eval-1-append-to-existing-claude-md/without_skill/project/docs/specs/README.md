# EARS Specs

Testable requirements written in Easy Approach to Requirements Syntax (EARS).

## ID scheme

`{FEATURE}-{TYPE}-{NNN}` — for example `AUTH-UI-001`, `BILLING-API-014`.

- `FEATURE`: short uppercase area name
- `TYPE`: layer or aspect (`UI`, `API`, `DATA`, `PERF`, ...)
- `NNN`: zero-padded sequence within the feature + type

## Status markers

Every spec line starts with a status marker:

- `[x]` implemented
- `[ ]` active gap (intended but not yet implemented)
- `[D]` deferred (explicitly parked)

## EARS patterns (cheat sheet)

- **Ubiquitous**: _The system shall <response>._
- **Event-driven**: _When <trigger>, the system shall <response>._
- **State-driven**: _While <state>, the system shall <response>._
- **Unwanted behavior**: _If <condition>, then the system shall <response>._
- **Optional feature**: _Where <feature is included>, the system shall <response>._

## Template

```markdown
# <Feature> specs

- [ ] AUTH-UI-001 — When a user submits valid credentials, the system shall
      create a session and redirect to the dashboard.
- [ ] AUTH-UI-002 — If authentication fails, then the system shall display a
      generic error without revealing which field was wrong.
```

Reference these IDs from code with `@spec` comments and from test names so
traceability works in both directions.
