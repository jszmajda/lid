# Research: Instruction-file idioms in minimal / AGENTS.md-native harnesses

**Snapshot date: 2026-07-05.** These tools ship weekly; specifics drift (Codex's cap is user-configurable, Junie's AGENTS.md preference is recent, Claude Code's import hop limit has already changed across doc versions). Re-verify load-bearing facts before reusing this for a new decision.

**Question.** For OpenAI Codex CLI, Aider, Zed (agent mode), Amp (Sourcegraph), goose (Block), Continue.dev, and JetBrains Junie: what is idiomatic in each user base for (1) project instruction files, (2) instruction-file size and token budgets, (3) pointing at or importing additional docs, (4) vendoring generated methodology files into repos, and (5) how existing spec-driven kits distribute their workflows?

**Method.** Multi-agent research run: 5 search angles, 20 sources fetched (primary docs prioritized), 97 claims extracted, top 25 adversarially verified by 3-vote panels (23 confirmed, 2 refuted). Purpose: ground the distribution design for LID's workflow on non-plugin hosts.

## Per-tool instruction-file mechanics

| Tool | Instruction file | Auto-read? | Notes |
|---|---|---|---|
| Codex CLI | `AGENTS.md` | Yes | Hierarchical: `~/.codex/AGENTS.md` + repo root + cwd, concatenated root-down (closer files positionally override). Combined content hard-capped at `project_doc_max_bytes` (default **32 KiB**), **silently truncated** beyond it — warning request closed not-planned (openai/codex#7138). |
| Zed (agent mode) | `AGENTS.md` | Yes | Project file plus `~/.config/zed/AGENTS.md`. |
| Amp | `AGENTS.md` | Yes | Hierarchical (cwd + parents to `$HOME` always; subtree files lazily on touch). First-class deterministic imports: `@`-mentions with relative/absolute paths and **glob patterns** (`@specs/**/*.md`). Amp itself generates AGENTS.md and writes project skills to `.agents/skills/`, recommending they be committed. |
| goose | `AGENTS.md` (also `.goosehints`) | Yes | Hierarchical AGENTS.md reading. |
| JetBrains Junie | `AGENTS.md` (formerly `.junie/guidelines.md`) | Yes | Now prefers AGENTS.md. |
| Aider | none by default | **No** | Nothing auto-loads. Conventions reach the model via `/read`, `--read`, or a `read:` key in `.aider.conf.yml`. Maintainer recommends read-only loading explicitly for **prompt-cache economics**. Practical bridge: `.aider.conf.yml` at repo root *is* auto-read, so a committed config with `read: AGENTS.md` gives repo-wide auto-loading (Aider-AI/aider#4363 asks for this to be documented). |
| Continue.dev | outside the AGENTS.md convention | — | Absent from the agents.md roster; own mechanism (config rules) not covered by surviving claims. Open question. |

The AGENTS.md spec itself imposes **no schema, no size guidance, and no import syntax** — the only standardized multi-file behavior is nested-file precedence in monorepos. An import-support request on the spec repo (agentsmd/agents.md#11) remains unadopted. Any pointer convention is per-tool.

## Size and token budgets

Always-loaded instruction tokens are treated as constrained everywhere explicit guidance exists:

- Codex: hard 32 KiB combined cap, silent truncation.
- Aider: canonical framing is prompt-cache cost; read-only files sit in the cacheable prefix.
- Anthropic (Claude Code, the ecosystem's most explicit norm): target **under 200 lines** per file — "longer files consume more context and reduce adherence."
- Imports do not escape the budget: Claude Code `@imports` are expanded eagerly at launch ("help organization but do not reduce context").

## Pointer reliability: two classes

- **Deterministic (harness-processed):** Amp `@`-mentions; Claude Code `@imports` (recursive, max ~4 hops). Following the pointer never depends on the model.
- **Model-dependent (everything else):** a prose "go read this file first" in AGENTS.md relies on model compliance on Codex, Zed, goose, and Junie. Documented failure exists (openai/codex#8601: model ignored a read-this-file pointer inside an already-loaded AGENTS.md) — though evidence is a single issue, not systematic measurement. Treat prose pointers as **best-effort** on most of the roster; anything load-bearing needs a fallback in the always-loaded file.

## Vendoring norms and kit distribution shapes

Every surveyed spec-driven kit vendors generated files into the user's repo; none distributes by URL:

- **GitHub spec-kit**: `specify init` writes `.specify/` (constitution, templates, scripts) + per-agent slash-command/prompt files; 30+ agents via `--integration` (roster coverage: Amp, Codex, goose, Junie, Zed; Aider and Continue.dev absent).
- **OpenSpec**: `openspec init` vendors an `openspec/` tree + generated agent instruction files for 30+ assistants.
- **BMAD**: installs three root directories (`_bmad`, `_bmad-output`, `docs`).
- **Ruler** (multi-tool instruction manager, ~2.8k stars): single committed source (`.ruler/`) generating 30+ tools' native files — which are **gitignored by default** as derived artifacts (committing is opt-out).

**Sentiment is footprint-sensitive, not vendoring-hostile.** BMAD's three root directories drew "invasive and encroaching — makes it look like BMAD is the project" (bmad-code-org/BMAD-METHOD#2337); tidy dot-directory kits drew no comparable pushback in the surveyed record (argument from search silence). BMAD's maintainer defends separation of config from output against a real failure mode: *the LLM randomly overwriting vendored config* — design implication: generated-file headers plus drift detection on vendored docs.

## Refuted during verification (do not rely on)

- "Nearest AGENTS.md wins" as a universal resolution model — resolution is per-tool; Codex concatenates root-down rather than nearest-wins.
- "spec-kit excludes Zed/Amp/Junie" — its integration list includes them; the genuine absences are Aider and Continue.dev.

## Open questions

1. Continue.dev's actual instruction mechanism and whether it is moving toward AGENTS.md.
2. Systematic pointer-following reliability on Codex/Zed/goose/Junie (only one anecdotal failure surfaced; this is the load-bearing assumption behind any pointer-based design).
3. Whether goose, Junie, or Zed have any deterministic import mechanism, or Amp is genuinely unique among AGENTS.md-native harnesses.
4. Organic community length norms for AGENTS.md in the Codex/Zed/goose/Junie user bases (only tool-enforced caps and Anthropic's guidance surfaced).

## Key sources

Primary: agents.md · developers.openai.com/codex/guides/agents-md · openai/codex source (`agents_md.rs`, `config_toml.rs`) · aider.chat/docs/usage/conventions.html + caching.html · ampcode.com/manual + news/globs-in-AGENTS.md · zed.dev/docs/ai/instructions · junie.jetbrains.com/docs/guidelines-and-memory.html · code.claude.com/docs/en/memory · github.com/github/spec-kit (+ integrations.md) · github.com/Fission-AI/OpenSpec · github.com/intellectronica/ruler · bmad-code-org/BMAD-METHOD#2337, #1852 · agentsmd/agents.md#11 · openai/codex#7138, #8601 · Aider-AI/aider#4363
