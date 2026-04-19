# Project

This project uses **Linked-Intent Development (LID)**: design intent flows from high-level design through low-level designs, EARS specs, and implementation plans, all the way to code and tests.

## Where to start

- **Big picture:** [`docs/high-level-design.md`](docs/high-level-design.md)
- **Component designs:** [`docs/llds/`](docs/llds/)
- **Requirements (EARS):** [`docs/specs/`](docs/specs/)
- **Implementation plans:** [`docs/planning/`](docs/planning/)

## Workflow

```
HLD -> LLD -> EARS -> Plan -> Tests -> Code
```

- **New features:** full workflow.
- **Bug fixes:** coherence check (verify existing specs/tests/code align).

See [`CLAUDE.md`](CLAUDE.md) for detailed guidance — including EARS patterns, semantic IDs, `@spec` annotations, and status markers.
