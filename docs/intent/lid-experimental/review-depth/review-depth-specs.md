# review-depth experiment specs

**LLD**: docs/intent/lid-experimental/review-depth/review-depth-design.md
**Implementing artifacts**:
- plugins/lid-experimental/skills/review-depth/SKILL.md

Status markers: `[x]` implemented · `[ ]` active gap · `[D]` deferred

Pure-prose experiment skill — no eval harness; `[x]` marks behavior the SKILL.md embodies.

---

## Declaration and Depth

- `[x]` **EXP-DEPTH-001**: When the user has declared a review depth (in their instruction file or in-session), the system SHALL run every workflow phase, stopping per-phase at and above the declared depth and consolidating deeper phases' outputs into one review at the declared boundary — a user-declared behavior that suspends the per-phase stop default of LID-CORE-005 for the phases below the declared depth.
- `[x]` **EXP-DEPTH-002**: When entering a change under a declared review depth, the system SHALL state the change's eligibility — segment-local, no HLD or structural LLD work anticipated — and confirm the fork-log location (creating the file if absent), and SHALL proceed consolidated only on the user's go.
- `[x]` **EXP-DEPTH-003**: If work under a declared review depth touches the HLD, restructures an LLD, or cascades across a segment boundary, the system SHALL revert to per-phase stops for the remainder of the change.

## Fork Protocol

- `[x]` **EXP-DEPTH-004**: When a specification fork falls within — or plausibly within — a declared judgment area, the system SHALL surface it to the user immediately, regardless of the declared depth; classification doubt resolves toward surfacing.
- `[x]` **EXP-DEPTH-005**: When a specification fork falls outside the declared judgment areas, the system SHALL record it in the fork log at detection — before routing work around it — and SHALL NOT resolve it silently.
- `[x]` **EXP-DEPTH-006**: While a fork is unresolved, the system SHALL NOT write tests or code against the forked spec line.
- `[x]` **EXP-DEPTH-007**: If an unresolved fork blocks all remaining work in the change, the system SHALL surface it to the user immediately.
- `[x]` **EXP-DEPTH-008**: At the consolidated boundary, the system SHALL present parked forks by reading the fork log — grouped by kind, never reconstructed from memory — alongside the LLD delta, spec delta, and failing tests.
- `[x]` **EXP-DEPTH-009**: When the user rules on parked forks, the system SHALL offer an update to the declared judgment areas reflecting the revealed pattern.
- `[x]` **EXP-DEPTH-010**: The system SHALL keep the fork log under `docs/arrows/_experiments/review-depth/` when the arrow-maintenance overlay is present, and otherwise at a location the user names once in their depth declaration.
