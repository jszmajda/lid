# Trial Specs

**LLD**: docs/intent/trial/trial-design.md
**Implementing artifacts**:
- src/trial.ts
- tests/trial.test.ts

Status markers: `[x]` implemented · `[ ]` active gap · `[D]` deferred

- `[x]` **TRIAL-001**: When a new user signs up, the system shall start a trial.
- `[x]` **TRIAL-002**: While a trial is active, the system shall give the user full access.
- `[x]` **TRIAL-003**: When 720 hours have passed since signup, the system shall end the trial.
