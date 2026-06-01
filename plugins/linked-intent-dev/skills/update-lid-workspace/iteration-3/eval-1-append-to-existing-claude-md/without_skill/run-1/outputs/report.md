# LID setup via append (baseline, no skill)

LID is set up via the "append directives" path, with all existing CLAUDE.md content preserved verbatim and the scaffolding created.

What I changed:
- `CLAUDE.md` (appended, nothing overwritten) — the three team conventions are untouched. Appended below them: a `## LID` block (`Mode: Full`, `Version: 1.2.0`) plus the `## Linked-Intent Development (MANDATORY)` directive with navigation table, terminology, and `@spec` convention. Full mode (no `## LID Scope` section). Arrow-overlay nav row and `## LID Tooling` omitted.
- `docs/high-level-design.md` (new) — HLD skeleton with standard sections marked *(not yet specified)*.
- `docs/intent/.gitkeep` (new) — empty design-tree root.

Did not create `docs/decisions/` (lazy) and did not fabricate HLD content.
