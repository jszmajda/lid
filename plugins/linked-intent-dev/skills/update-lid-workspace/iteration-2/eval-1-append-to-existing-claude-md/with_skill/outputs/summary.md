# Eval 1 — Append to existing CLAUDE.md (with_skill)

## Detection

Ran the detection signals from `update-lid` SKILL.md against `/tmp/update-lid-eval-fixtures/eval-1/project/`:

- `CLAUDE.md` present — contained team conventions, no LID directives.
- `grep` for `"linked-intent-dev"` / `"Linked-Intent Development"` in CLAUDE.md — no match.
- `grep` for `## LID Mode:` — no match.
- `docs/` directory — absent.
- `docs/arrows/` — absent.
- `docs/planning/` — absent.

Dispatched state: **CLAUDE.md exists, no LID directives → Append directives.** Mode defaulted to **Full** (user did not specify; skill default).

## Changes made

### `CLAUDE.md` — appended (existing content preserved verbatim)

Original `# My Project` heading and `## Conventions` list left untouched. The following sections were appended below the existing content, in order:

1. `## LID Mode: Full` — mandatory mode marker.
2. `## Linked-Intent Development (MANDATORY)` — the directives block (consult-skill mandate, arrow diagram, new-feature/bug-fix/unsure guidance, stop-after-each-phase, mutation-not-accumulation).
3. `### Navigation` — table with rows for HLD (`docs/high-level-design.md`), LLDs (`docs/llds/`), and EARS specs (`docs/specs/`). The arrow-overlay row was omitted because `docs/arrows/` is not present (per the conditional-include rule in the template).
4. `### Terminology` — definitions for HLD, LLD, EARS, Arrow, Arrow segment, Cascade.
5. `### Code annotations` — `@spec` annotation convention with placement guidance.

No `## LID Scope` section was added (mode is Full — section is omitted entirely per template).
No `## LID Tooling` section was added (no project tooling to declare — section omitted per template's conditional-include rule).

### Directories created

- `docs/`
- `docs/llds/` (empty placeholder)
- `docs/specs/` (empty placeholder)

### Files created

- `docs/high-level-design.md` — scaffolded from the HLD template. All standard sections present (Problem, Approach, Target Users, Goals, Non-Goals, System Design, Key Design Decisions, Success Metrics, References), each marked `*(not yet specified — ...)*` so the gaps are visible. Project name set to "My Project" from the existing CLAUDE.md H1.

## Verification

- Existing `## Conventions` content preserved byte-for-byte.
- `## LID Mode: Full` marker present.
- No `## LID Scope` and no `## LID Tooling` sections written (correct for Full mode with no tooling).
- Arrow-overlay navigation row omitted (correct — `docs/arrows/` absent).
- All required directories from the skill's "Directory structure" section exist.
- `docs/planning/` not created (per skill's explicit rule).
