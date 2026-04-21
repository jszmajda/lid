# Setup for agentic coding tools

LID is a methodology, not a tool. It works with any agentic coding system that can read per-project instructions. This page has one section per tool — pick yours, copy the adapter file into your LID project, and the agent will follow the workflow on every task.

Two concepts to keep straight:

- **Your LID project** — the codebase you're building. Its `docs/` tree holds your HLDs, LLDs, and EARS specs. Its root has an `AGENTS.md` file that names the workflow.
- **This repository** — distributes the methodology and the Claude Code plugins. You don't add tool adapters *here*; you add them *in your own project*.

The workflow is identical across tools (`HLD → LLDs → EARS → Tests → Code`). What differs is *how* the agent is reminded to follow it on each turn.

## What to generate in your LID project first

Every adapter below assumes your project has:

1. An `AGENTS.md` at the root that describes the LID workflow for your project.
2. A `docs/` tree with `high-level-design.md`, `llds/`, `specs/`.

If you're a Claude Code user, `/linked-intent-dev:lid-setup` generates both automatically. If you're not, copy the template from [this repo's `AGENTS.md`](../AGENTS.md) and `docs/` layout into your own project as a starting point, or run `/lid-setup` once from a Claude Code session just to scaffold — the scaffolding is tool-agnostic.

---

## Claude Code

Richest integration. The plugins automate phase gates, auto-invoke the workflow skill on code-change tasks, provide slash commands for setup and arrow audits, and run eval suites.

```
/plugin marketplace add jszmajda/lid
/plugin install linked-intent-dev@jszmajda-lid
/plugin install arrow-maintenance@jszmajda-lid
/linked-intent-dev:lid-setup
```

After setup, describe what you want to build. The `linked-intent-dev` skill activates automatically.

Claude Code also reads `AGENTS.md` via the `CLAUDE.md` symlink this repo ships. If your own project has only `AGENTS.md`, Claude Code will still read it.

---

## Cursor

Cursor reads rule files from `.cursor/rules/*.mdc`. Ship one rule file in your LID project that tells Cursor to apply the workflow to all edits:

**`.cursor/rules/lid.mdc`**
```markdown
---
description: Linked-Intent Development workflow — design before code
alwaysApply: true
---

Follow the Linked-Intent Development workflow in `AGENTS.md` for all code changes.

Intent flows in one direction: HLD → LLDs → EARS → Tests → Code. Before
writing code, verify the arrow is coherent — the HLD names the problem,
an LLD names the component, EARS specs state testable claims, and tests
exist before implementation.

- New features: full workflow.
- Bug fixes: find where intent diverged, cascade from there.
- Mutation, not accumulation — delete obsolete specs; don't annotate history.

See `docs/high-level-design.md`, `docs/llds/`, `docs/specs/`, and any
`docs/arrows/index.yaml` navigation overlay. Code and tests carry
`@spec SPEC-ID` annotations linking back to EARS IDs.
```

For phase-specific rules (e.g. a glob-attached rule that fires only when editing `docs/specs/**`), add another `.mdc` file with `globs:` frontmatter instead of `alwaysApply`.

---

## Windsurf

Windsurf reads `.windsurf/rules/*.md` with frontmatter similar to Cursor's. Ship:

**`.windsurf/rules/lid.md`**
```markdown
---
trigger: always_on
description: Linked-Intent Development workflow
---

Follow the Linked-Intent Development workflow in `AGENTS.md` for all code changes.

HLD → LLDs → EARS → Tests → Code. Before writing code, verify the arrow
is coherent. New features use the full workflow; bug fixes walk the arrow
to find where intent diverged. Docs reflect current intent, not history.

Navigation: `docs/high-level-design.md`, `docs/llds/`, `docs/specs/`.
Code and tests carry `@spec SPEC-ID` annotations.
```

Legacy `.windsurfrules` at the repo root is still honored if you prefer a single file.

---

## GitHub Copilot

Copilot (VS Code, JetBrains, Visual Studio, GitHub.com chat, Copilot CLI) reads `.github/copilot-instructions.md`:

**`.github/copilot-instructions.md`**
```markdown
# Project instructions

This project uses Linked-Intent Development. See `AGENTS.md` for the full
methodology. The short version:

- Intent flows downstream: HLD → LLDs → EARS → Tests → Code.
- New features use the full workflow; bug fixes walk the arrow to find
  where intent diverged.
- Design docs are the source of truth. Code is the output.
- Tests come before code and carry `@spec SPEC-ID` annotations that link
  to EARS IDs in `docs/specs/`.
- Mutation, not accumulation — delete obsolete specs rather than marking
  them historical.

Navigation: `docs/high-level-design.md`, `docs/llds/`, `docs/specs/`.
```

For path-scoped rules (e.g. "when editing `docs/specs/**`, follow EARS syntax"), add files under `.github/instructions/*.instructions.md` with `applyTo:` frontmatter globs.

---

## Aider

Aider uses `CONVENTIONS.md` plus an opt-in `read:` entry in `.aider.conf.yml` to load it on every session:

**`CONVENTIONS.md`** (at project root — can be a symlink to `AGENTS.md`)

**`.aider.conf.yml`**
```yaml
read:
  - AGENTS.md
  - docs/high-level-design.md
```

Aider will preload these into the context on every session. Add specific LLDs to the `read:` list when working in a particular arrow segment.

---

## Continue.dev

Continue reads `.continue/rules/*.md`:

**`.continue/rules/lid.md`**
```markdown
---
name: Linked-Intent Development
alwaysApply: true
---

Follow the Linked-Intent Development workflow in `AGENTS.md` for all code changes.

HLD → LLDs → EARS → Tests → Code. Design docs are the source of truth;
code is output. Tests precede code and carry `@spec SPEC-ID` annotations.
Mutation, not accumulation. See `docs/high-level-design.md`, `docs/llds/`,
and `docs/specs/`.
```

---

## JetBrains Junie

Junie reads `.junie/guidelines.md`:

**`.junie/guidelines.md`**
```markdown
Follow the Linked-Intent Development workflow in `AGENTS.md` for all code changes.

Intent flows downstream: HLD → LLDs → EARS → Tests → Code. Tests precede
code. Code carries `@spec SPEC-ID` annotations linking to EARS IDs in
`docs/specs/`. Mutation, not accumulation.

Full methodology in `AGENTS.md` and `docs/`.
```

JetBrains AI Assistant (the separate product) also honors `AGENTS.md` directly as of the 2025.3 line — no extra file needed.

---

## Zed, OpenAI Codex CLI, Jules, Cline, Amp, Sourcegraph

All of these honor `AGENTS.md` at the project root directly — no per-tool adapter needed. Nested `AGENTS.md` files in subdirectories are supported (nearest-wins) if you want scoped guidance.

---

## Any tool not listed

If the tool supports per-project instructions in any form (a config file, a rules file, a system prompt prefix), point it at `AGENTS.md` or copy its contents inline. The workflow is the same; the invocation varies.

If the tool *doesn't* support per-project instructions, you'll need to paste the LID workflow into your prompt at the start of each session. The short form:

> This project uses Linked-Intent Development. Before code changes, verify the arrow (HLD → LLDs → EARS → Tests → Code) is coherent. Design docs are the source of truth. See `AGENTS.md` and `docs/`.

---

## Maintenance

When you update `AGENTS.md`, the rule adapters above don't need to change — they already delegate to `AGENTS.md`. If you inline the workflow content into a rule file instead of pointing at `AGENTS.md`, keep the two in sync or the adapter will drift.
