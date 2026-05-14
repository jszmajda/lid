# Summary — Bootstrap empty project (without_skill)

## Files created

Paths are relative to the project directory (`.../without_skill/project/`):

- `README.md` — top-level project README explaining LID and pointing at the docs tree.
- `CLAUDE.md` — project instructions for Claude Code describing the LID workflow, navigation, terminology, EARS patterns, semantic ID scheme, status markers, and `@spec` code annotations.
- `docs/high-level-design.md` — HLD starter template with Purpose, Scope, Context, Architecture Overview, Components, Key Decisions, Open Questions, and Arrows sections.
- `docs/llds/README.md` — explains the LLD directory.
- `docs/llds/_template.md` — LLD template (Summary, Intent, Interfaces, Dependencies, Data Model, Behavior, Error Handling, Specs, Open Questions).
- `docs/specs/README.md` — explains EARS spec directory, ID format, status markers, and the five EARS patterns.
- `docs/specs/_template.md` — per-feature EARS spec template with example entries in ubiquitous, event-driven, and deferred forms.
- `docs/planning/README.md` — explains the planning directory.
- `docs/planning/_template.md` — implementation plan template (Goal, Covered Specs, Task Breakdown, Test Strategy, Rollout/Risk, Out of Scope).

No files were modified (project was empty).

## Prose response to user

I've set up Linked-Intent Development in your project. Here's what you now have:

- `CLAUDE.md` at the project root — tells Claude Code to use LID for every change, and documents the workflow (`HLD -> LLD -> EARS -> Plan -> Tests -> Code`), EARS phrasing patterns, the `{FEATURE}-{TYPE}-{NNN}` semantic ID scheme, the `[x] / [ ] / [D]` status markers, and the `@spec` code-annotation convention.
- `docs/high-level-design.md` — the single HLD file. Start here: fill in Purpose, Scope, Architecture Overview, and list your components and arrows.
- `docs/llds/` — one low-level design per component. Copy `_template.md` to `<component>.md` as you break the HLD down.
- `docs/specs/` — EARS requirements grouped per feature. Copy `_template.md` to `<feature>.md` and give each requirement a semantic ID.
- `docs/planning/` — implementation plans that turn specs into ordered tasks with test strategy. Copy `_template.md` to `<feature>.md` per feature.
- `README.md` — a lightweight pointer to the docs tree.

Recommended next step: open `docs/high-level-design.md` and sketch the Purpose, Scope, and Components sections. Once the HLD has shape, create an LLD per component, then EARS specs, then a plan — and only then start writing tests and code. The templates have all the section headings you need; just copy, rename, and fill in.
