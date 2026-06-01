# LID setup — append to existing CLAUDE.md

## What I detected

Your project already had a `CLAUDE.md` with your team's conventions and **no LID
artifacts** at all:

- `CLAUDE.md` present, but **no LID directives** (no `linked-intent-dev` /
  `Linked-Intent Development` strings).
- **No `## LID` block.**
- **No `docs/` tree** (and no `docs/arrows/` overlay, no legacy `docs/planning/`).
- No `CHANGELOG.md` in the project, so there is **no version-walk** to run — this
  is fresh adoption, not a migration.

That maps to exactly one branch of the skill: **Append directives** — add the LID
block to your existing `CLAUDE.md` without overwriting anything, and create the
required `docs/` scaffold. Installed LID conventions version is **1.2.0**.

## What I changed (applied — mechanical / clearly-correct)

1. **Appended the LID directives block to `CLAUDE.md`.** Your existing
   `# My Project` / `## Conventions` content is untouched at the top of the file;
   the LID material is appended after it. The appended sections are:
   - `## LID` metadata block — `- Mode: Full`, `- Version: 1.2.0`.
   - `## Linked-Intent Development (MANDATORY)` — the arrow workflow, navigation
     table, terminology, and `@spec` code-annotation guidance.

   Conditional sections were **correctly omitted** per the template rules:
   - No `## LID Scope` section (Full mode → entire project in scope).
   - No "Arrow of intent overlay" navigation row (`docs/arrows/` not present).
   - No `## LID Tooling` section (no coherence-check script to declare).

2. **Created the required directory scaffold:**
   - `docs/`
   - `docs/intent/`
   - `docs/high-level-design.md` — a **template skeleton** with the standard HLD
     section headings, each marked `*(not yet specified)*` so the gaps are visible
     rather than hidden behind placeholder prose.

   I did **not** create `docs/decisions/` (created lazily, only when the first
   decision doc is written) or `docs/planning/` (LID explicitly does not use it).

## Verification

- `CLAUDE.md` read back: original lines 1–7 preserved verbatim; LID block appended
  below.
- Final tree: `CLAUDE.md`, `docs/high-level-design.md`, `docs/intent/`.
- Confirmed no Scope / arrows-row / Tooling content leaked in.

## Judgment items — surfaced, NOT auto-applied

These need your decision; I applied a default only where the skill mandates one.

1. **Mode = Full (applied as the skill's default).** The skill's mode-elicitation
   ritual belongs to a *full bootstrap*; this was the append path, and with no
   interactive prompt available I took the documented default (Full), which also
   matches your framing ("my team's conventions… adopt LID" — whole project).
   **Recommendation:** keep **Full** if LID governs the entire project. If you
   instead want LID to anchor only a bounded scope inside a larger non-LID
   codebase, run `/update-lid` and switch to **Scoped**, supplying the in-scope
   (and any excluded) path globs — that will add a `## LID Scope` section.

2. **Author the HLD content.** `docs/high-level-design.md` is currently a skeleton
   of headings only. Filling in Problem / Approach / Target Users / Goals /
   Non-Goals / Tenets / System Design / Key Design Decisions / Success Metrics is
   genuine elicitation work, not mechanical scaffolding, so I left it for you.
   **Recommendation:** run `/linked-intent-dev` and let its Phase 1 walk you
   through drafting the HLD (and the first LLDs/EARS) from your project's current
   intent. Until then the `*(not yet specified)*` markers keep the gaps honest.

## Next steps

- Decide Full vs. Scoped (item 1 above).
- Run `/linked-intent-dev` to author the HLD and begin the design tree under
  `docs/intent/` (item 2).
- If/when you adopt the navigation+tracking overlay, install `arrow-maintenance`
  and re-run `/update-lid` — it will add the arrow-overlay navigation row.
