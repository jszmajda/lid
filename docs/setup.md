# Setup for agentic coding tools

LID is a methodology, not a tool. It works with any agentic coding system that can read per-project instructions. Pick your tool below — in many cases, all you need is an `AGENTS.md` at your project root; a few tools need a small adapter file too.

Two concepts to keep straight:

- **Your LID project** — the codebase you're building. Its `docs/` tree holds your HLDs, LLDs, and EARS specs. Its root has an `AGENTS.md` file that describes the workflow.
- **This repository** — distributes the methodology and the Claude Code plugins. You don't add tool adapters *here*; you add them *in your own project*.

The workflow is identical across tools (`HLD → LLDs → EARS → Tests → Code`). What differs is *how* the agent is reminded to follow it on each turn.

## Scaffolding your LID project

Every tool below assumes your project has:

1. An `AGENTS.md` at the root that describes the LID workflow for your project.
2. A `docs/` tree with `high-level-design.md`, `llds/`, `specs/`.

Claude Code users get both for free: `/linked-intent-dev:lid-setup` scaffolds them. Non-Claude-Code users can copy [this repo's `AGENTS.md`](../AGENTS.md) and `docs/` layout as a starting point, or run Claude Code once just to scaffold — the artifacts themselves are tool-agnostic.

---

## The simple path: just ship `AGENTS.md`

`AGENTS.md` is the [emerging cross-tool convention](https://agents.md/) for per-project agent instructions. Drop it at your repo root and many tools read it directly — no adapter needed. Tools that honor repo-root `AGENTS.md` natively:

| Tool | Notes |
|---|---|
| **Claude Code** | Via the `CLAUDE.md` symlink this repo ships (Claude Code reads `CLAUDE.md`). The LID plugins add auto-invoking skills and slash commands on top — see the [Claude Code section below](#claude-code). |
| **OpenAI Codex CLI** | Hierarchical merge from project root down to cwd; `AGENTS.override.md` as escape hatch. [docs](https://developers.openai.com/codex/guides/agents-md) |
| **Amp** (Sourcegraph) | Walks cwd + parents up to `$HOME`; strongest hierarchical support. [docs](https://ampcode.com/manual) |
| **Jules** (Google) | "Automatically looks for `AGENTS.md` in the root of your repository." [docs](https://jules.google/docs) |
| **Zed** | Supported, but picks a single file from a 9-entry precedence list (`.rules`, `.cursorrules`, `.windsurfrules`, `.clinerules`, `.github/copilot-instructions.md`, `AGENT.md`, `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`) — first match wins. [docs](https://zed.dev/docs/ai/rules) |
| **Cline** | Supported as a cross-tool compatibility source; Cline's primary format is `.clinerules/`. [docs](https://docs.cline.bot/features/cline-rules) |
| **JetBrains Junie** | Reads repo-root `AGENTS.md` as a fallback. Lookup order: IDE custom path → `.junie/AGENTS.md` → `AGENTS.md` → legacy `.junie/guidelines.md`. [docs](https://junie.jetbrains.com/docs/guidelines-and-memory.html) |
| **GitHub Copilot** | `AGENTS.md` is read by VS Code Chat, Copilot CLI, and the Copilot coding agent (cloud) across its surfaces, as of [Aug 2025](https://github.blog/changelog/2025-08-28-copilot-coding-agent-now-supports-agents-md-custom-instructions/). IDE inline completions and GitHub.com Chat still need `.github/copilot-instructions.md` — see the [Copilot section below](#github-copilot). |
| **Windsurf** | Treated as an always-on rule by the Cascade rules engine. [docs](https://docs.windsurf.com/windsurf/cascade/memories) |
| **Cursor** | `AGENTS.md` is listed as an alternative to `.cursor/rules`; behavior when both exist isn't documented. Safer to also ship a `.cursor/rules/lid.mdc` — see the [Cursor section below](#cursor). |

Other tools that honor `AGENTS.md` per the [spec](https://agents.md/) and should work with just the root file: **Factory, goose, opencode, Warp, Devin, Gemini CLI, RooCode, Kilo Code, Augment Code**.

Nearest-wins nesting is part of the spec; Codex and Amp implement hierarchical merge, while Zed and Cline pick a single file.

**If you use only tools from this list and an `AGENTS.md` at your root, you are done.** The sections below cover tools that need something extra, or that benefit from an explicit adapter.

---

## Claude Code

Richest integration. The plugins automate phase gates, auto-invoke the workflow skill on code-change tasks, provide slash commands for setup and arrow audits, and ship an eval suite.

```
/plugin marketplace add jszmajda/lid
/plugin install linked-intent-dev@jszmajda-lid
/plugin install arrow-maintenance@jszmajda-lid
/linked-intent-dev:lid-setup
```

After setup, describe what you want to build. The `linked-intent-dev` skill activates automatically. Claude Code reads `CLAUDE.md`; this project symlinks it to `AGENTS.md` so a single source of truth covers both.

---

## Cursor

Cursor recognizes `AGENTS.md` as an alternative to `.cursor/rules`, but behavior when both files exist isn't documented. Ship both for belt-and-suspenders coverage:

**`.cursor/rules/lid.mdc`**
```markdown
---
description: Linked-Intent Development workflow — design before code
alwaysApply: true
---

Follow the Linked-Intent Development workflow for all code changes.

Intent flows downstream: HLD → LLDs → EARS → Tests → Code. Before writing
code, verify the arrow is coherent — the HLD names the problem, an LLD
names the component, EARS specs state testable claims, and tests exist
before implementation.

- New features: full workflow.
- Bug fixes: find where intent diverged, cascade from there.
- Mutation, not accumulation — delete obsolete specs; don't annotate history.

Navigation: `docs/high-level-design.md`, `docs/llds/`, `docs/specs/`, and
any `docs/arrows/index.yaml` overlay. Code and tests carry
`@spec SPEC-ID` annotations linking back to EARS IDs.

See `AGENTS.md` at the repo root for the full workflow if you need more depth.
```

For glob-scoped rules (e.g. a rule that fires only when editing `docs/specs/**`), create another `.mdc` file with `alwaysApply: false` and a `globs:` entry:

```markdown
---
description: EARS syntax reminder for spec files
alwaysApply: false
globs:
  - docs/specs/**
---
```

Cursor supports four rule-application modes: **Always** (`alwaysApply: true`), **Auto Attached** (matched by `globs:`), **Agent Requested** (the model opts in based on `description`), and **Manual** (`@rule-name`). Keep rule files under ~500 lines (Cursor's guidance). Sources: [cursor.com/docs/context/rules](https://cursor.com/docs/context/rules).

---

## Windsurf

Windsurf's Cascade rules engine treats a root-level `AGENTS.md` as an always-on rule automatically — if your project has one, Windsurf is covered. A tool-specific adapter is only useful when you want glob-scoped rules or a Windsurf-scoped variant.

Optional:

**`.windsurf/rules/lid.md`**
```markdown
---
trigger: always_on
description: Linked-Intent Development workflow
---

Follow the Linked-Intent Development workflow in `AGENTS.md` for all code changes.

HLD → LLDs → EARS → Tests → Code. Before writing code, verify the arrow
is coherent. New features use the full workflow; bug fixes walk the
arrow to find where intent diverged. Docs reflect current intent, not
history. Navigation: `docs/high-level-design.md`, `docs/llds/`,
`docs/specs/`. Code and tests carry `@spec SPEC-ID` annotations.
```

Valid `trigger:` values: `always_on`, `manual`, `model_decision`, `glob` (when `glob`, add a `globs:` key with the pattern; when `model_decision`, `description:` is what the model sees). Workspace rule files are capped at **12,000 characters** (global `global_rules.md` at 6,000). Legacy `.windsurfrules` at repo root still works as a single-file fallback. Sources: [docs.windsurf.com/windsurf/cascade/memories](https://docs.windsurf.com/windsurf/cascade/memories).

---

## GitHub Copilot

`AGENTS.md` at your repo root covers VS Code Chat, Copilot CLI, and the Copilot coding agent (the cloud agent used from GitHub.com, JetBrains, Eclipse, and Xcode) as of [August 2025](https://github.blog/changelog/2025-08-28-copilot-coding-agent-now-supports-agents-md-custom-instructions/). Nearest `AGENTS.md` wins.

For IDE inline completions and GitHub.com Chat, add a repository instructions file:

**`.github/copilot-instructions.md`**
```markdown
# Project instructions

This project uses Linked-Intent Development. See `AGENTS.md` for the full
methodology. The short version:

- Intent flows downstream: HLD → LLDs → EARS → Tests → Code.
- New features use the full workflow; bug fixes walk the arrow to find
  where intent diverged.
- Design docs are the source of truth. Code is the output.
- Tests come before code and carry `@spec SPEC-ID` annotations linking
  to EARS IDs in `docs/specs/`.
- Mutation, not accumulation — delete obsolete specs rather than marking
  them historical.

Navigation: `docs/high-level-design.md`, `docs/llds/`, `docs/specs/`.
```

This file is read by **VS Code, JetBrains, Visual Studio, Xcode, Eclipse, GitHub.com Chat, Copilot coding agent, Copilot code review, and Copilot CLI** ([support matrix](https://docs.github.com/en/copilot/reference/custom-instructions-support)).

For path-scoped rules, add files under `.github/instructions/*.instructions.md` with `applyTo:` frontmatter globs. Caveat: these path-scoped files are **not** honored by GitHub.com Chat or the Copilot coding agent (except via Eclipse Cloud Agent) — they primarily affect IDE surfaces.

Sources: [Copilot repository instructions](https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/add-custom-instructions/add-repository-instructions), [support matrix](https://docs.github.com/en/copilot/reference/custom-instructions-support).

---

## Aider

Aider does **not** read `AGENTS.md` automatically — you have to wire it in via `.aider.conf.yml`. Aider's canonical conventions filename is `CONVENTIONS.md`; symlink `AGENTS.md` to `CONVENTIONS.md` if you want a single source of truth.

**`CONVENTIONS.md`** (symlink to `AGENTS.md`, or a standalone file)

**`.aider.conf.yml`**
```yaml
read:
  - CONVENTIONS.md
  - docs/high-level-design.md
```

`read:` loads files as read-only context on every session (and caches them if prompt caching is on). The list takes explicit paths — no glob support. Add specific LLDs when working in a particular arrow segment:

```yaml
read:
  - CONVENTIONS.md
  - docs/high-level-design.md
  - docs/llds/auth.md
  - docs/specs/auth-specs.md
```

Note: there is no separate `read-only:` key — `read:` *is* the read-only entry. The sibling `file:` key adds editable files to a session. Aider looks for `.aider.conf.yml` in `$HOME`, git root, and cwd in that order; later files take priority. Sources: [aider.chat/docs/config/aider_conf.html](https://aider.chat/docs/config/aider_conf.html), [aider.chat/docs/usage/conventions.html](https://aider.chat/docs/usage/conventions.html).

---

## Continue.dev

Continue does **not** read `AGENTS.md` automatically. Inline the LID directives in a Continue rule:

**`.continue/rules/lid.md`**
```markdown
---
alwaysApply: true
description: Linked-Intent Development workflow
---

Follow the Linked-Intent Development workflow for all code changes.

Intent flows downstream: HLD → LLDs → EARS → Tests → Code. Before code
changes, verify the arrow is coherent — the HLD names the problem, an
LLD names the component, EARS specs state testable claims, and tests
exist before implementation.

- New features: full workflow.
- Bug fixes: walk the arrow to find where intent diverged; cascade.
- Mutation, not accumulation — delete obsolete specs, don't annotate
  history.

Navigation: `docs/high-level-design.md`, `docs/llds/`, `docs/specs/`.
Code and tests carry `@spec SPEC-ID` annotations linking to EARS IDs.
See `AGENTS.md` at repo root for depth.
```

Supported frontmatter keys for Markdown rules: `alwaysApply` (true/false/undefined), `globs` (string or array), `regex`, `description`. (`name` is only required for the legacy YAML rule format — don't use it in Markdown rules. `trigger` is Windsurf/Cursor naming; Continue doesn't recognize it.) Rules are loaded in lexicographical filename order and apply to Agent, Chat, and Edit modes — **not** autocomplete. Sources: [docs.continue.dev/customize/deep-dives/rules](https://docs.continue.dev/customize/deep-dives/rules).

---

## JetBrains Junie

Junie reads your repo-root `AGENTS.md` automatically — if you already ship one, you're done.

If you want a Junie-specific variant (e.g. IDE-only notes that shouldn't go in the canonical `AGENTS.md`), use `.junie/AGENTS.md` — Junie's lookup order is IDE custom path → `.junie/AGENTS.md` → `AGENTS.md` → legacy `.junie/guidelines.md`:

**`.junie/AGENTS.md`**
```markdown
Follow the Linked-Intent Development workflow in `AGENTS.md` for all code changes.

Intent flows downstream: HLD → LLDs → EARS → Tests → Code. Tests precede
code. Code carries `@spec SPEC-ID` annotations linking to EARS IDs in
`docs/specs/`. Mutation, not accumulation.

Full methodology in the repo-root `AGENTS.md` and `docs/`.
```

The file is plain Markdown, no frontmatter. Junie adds this context to every task it works on. Avoid `.junie/guidelines.md` — it still works but is legacy. Source: [junie.jetbrains.com/docs/guidelines-and-memory.html](https://junie.jetbrains.com/docs/guidelines-and-memory.html).

---

## JetBrains AI Assistant (distinct from Junie)

AI Assistant's chat mode does **not** read `AGENTS.md`. It uses its own project-rules system:

**`.aiassistant/rules/lid.md`**
```markdown
Follow the Linked-Intent Development workflow in `AGENTS.md` for all code changes.

HLD → LLDs → EARS → Tests → Code. Tests precede code. Code carries
`@spec SPEC-ID` annotations. Mutation, not accumulation. See `AGENTS.md`
for depth.
```

AI Assistant supports rule-scope modes (Always / Manually / By file patterns / etc.) configured inside the IDE — consult JetBrains' [configure project rules](https://www.jetbrains.com/help/ai-assistant/configure-project-rules.html) page for specifics. As of 2025.12, Junie is being integrated into the AI chat interface, so this Junie / AI Assistant distinction may blur in future releases.

---

## Any tool not listed

If the tool honors `AGENTS.md` (the [spec site](https://agents.md/) lists ~20 adopters), dropping the file at your repo root is the whole setup. If the tool has its own rule system, either add a short adapter that points at `AGENTS.md` or inline the LID workflow directly. If the tool doesn't support per-project instructions at all, paste the LID workflow into your prompt at the start of each session:

> This project uses Linked-Intent Development. Before code changes, verify the arrow (HLD → LLDs → EARS → Tests → Code) is coherent. Design docs are the source of truth. See `AGENTS.md` and `docs/`.

---

## Maintenance

Adapters that **delegate to `AGENTS.md`** (Cursor, Windsurf, Junie, Copilot, Aider, AI Assistant) stay in sync automatically — you update `AGENTS.md` and they read the new content on next load.

Adapters that **inline the workflow** (Continue — which doesn't fetch `AGENTS.md`) need to be kept in sync manually. When you edit `AGENTS.md`, also revisit any inline rule files.
