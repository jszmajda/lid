# Implementation Plans

One file per planned change (feature, refactor, or non-trivial fix). A plan
turns HLD + LLD + EARS specs into an ordered, reviewable sequence of steps.

Suggested filename: `docs/planning/<YYYY-MM-DD>-<slug>.md`.

## Template

```markdown
# <Change title>

Status: draft | in-progress | done
Related HLD: docs/high-level-design.md#<section>
Related LLD(s): docs/llds/<component>.md
Specs touched: AUTH-UI-001, AUTH-UI-002

## Summary
One or two sentences on what this change accomplishes and why.

## Steps
1. ...
2. ...
3. ...

## Tests
- Which specs get covered, and how.

## Risks / rollback
- What could go wrong, and how to back out.
```
