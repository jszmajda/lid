# LID Review

## Summary: Nothing set up yet — clean slate

I reviewed the project directory and there is **nothing here at all**. It's a completely empty directory: no source code, no `docs/`, no `CLAUDE.md` (or `AGENTS.md`), and no LID artifacts of any kind.

So the honest answer to "how am I doing with LID?" is: you haven't started yet. That's not a problem — it just means there's nothing to audit and everything to set up. Here's where you stand against the pieces LID expects.

## What LID expects vs. what you have

| LID artifact | Purpose | Status |
|---|---|---|
| `CLAUDE.md` / `AGENTS.md` | Project instructions that point agents at the LID workflow and set the LID mode | Missing |
| `docs/high-level-design.md` | The HLD — the top of the arrow of intent | Missing |
| `docs/llds/` | Low-level designs per component | Missing |
| `docs/specs/` | EARS specs with semantic IDs (`{FEATURE}-{TYPE}-{NNN}`) | Missing |
| `docs/arrows/index.yaml` + segment docs | Arrow-of-intent navigation/tracking overlay (for larger codebases) | Missing |
| `@spec` code annotations | Links from code back to EARS IDs | N/A — no code yet |

Score: 0 of 6. But again — empty project, so this is a starting line, not a failing grade.

## Recommendation: bootstrap LID before you write code

The single most valuable thing you can do right now is start with intent rather than retrofitting it later. LID's whole premise is that intent and code stay coherent because intent comes first and code traces back to it. Concretely:

1. **Decide what you're building.** Have a one-paragraph description of the system ready.

2. **Bootstrap the LID workflow.** In Claude Code, run `/linked-intent-dev` with your description. For a fresh, empty project the workflow bootstraps LID inline — it will walk you through the phases in order:
   - **HLD** → high-level design (what and why)
   - **LLDs** → low-level designs per component (how)
   - **EARS** → structured requirements with semantic IDs and status markers (`[x]` implemented, `[ ]` gap, `[D]` deferred)
   - **Tests** → tests-first, derived from the EARS specs
   - **Code** → implementation, annotated with `@spec` comments linking back to EARS IDs

3. **Add project instructions.** Create a `CLAUDE.md`/`AGENTS.md` so every future agent session knows to consult the LID workflow for all code changes and knows the chosen LID mode.

4. **Defer the arrow overlay.** The `docs/arrows/` navigation/tracking overlay (and `/map-codebase`) matters once a codebase outgrows a single context window. For a brand-new project you don't need it yet — add it later via the arrow-maintenance plugin when the project grows.

## Bottom line

You're not "doing badly" with LID — you simply have not begun, and the project is empty so there is nothing that could have drifted. The good news: starting from zero is the *ideal* place to adopt LID, because you can put intent first instead of reverse-engineering it from existing code. Begin with `/linked-intent-dev` and a short description of what you want to build, and let the workflow lay down the HLD → LLD → EARS → Tests → Code arrow from the start.
