# LID setup — `/update-lid`

You asked me to set up LID. The project is **already configured for LID**, so this was a reconcile pass rather than a fresh bootstrap. Here is what I detected and the one thing I'm flagging for your decision.

## What I detected

I ran the skill's detection signals against `CLAUDE.md` and the `docs/` tree:

| Signal | Result |
|---|---|
| LID directives in `CLAUDE.md` | Present (`## Linked-Intent Development (MANDATORY)`) |
| `## LID` block | Present and well-formed |
| Mode | **Full** (no `## LID Scope` section, correct for Full) |
| Version | **1.2.0** — matches the installed `linked-intent-dev` plugin (1.2.0). No version-walk needed. |
| `docs/high-level-design.md` | Present |
| `docs/intent/` | Present (empty except `.gitkeep`) |
| `docs/arrows/` overlay | Absent — so no arrow-navigation row belongs in the template, and none is present (consistent) |
| Legacy `docs/planning/` | Absent |
| `prefix:` arrays / overloaded node folders | None (no design docs authored yet) |

**Dispatch:** directives + a current, well-formed `## LID` block, no mode change requested → **reconcile conventions**. The mode/version block is correct and current; I changed nothing there.

## One drift item — proposed, NOT applied (your call)

**The `## Linked-Intent Development (MANDATORY)` directive section is heavily truncated relative to the current 1.2.0 template.**

Your `CLAUDE.md` keeps the opening line and the `HLD → LLDs → EARS → Tests → Code` arrow, but is missing the rest of the standard directive block:

- The change-type bullets (new features/refactors → full six-phase workflow; bug fixes → walk the arrow; if unsure → full workflow)
- The "stop after each phase" + **"Docs carry current intent, written to be read cold"** guidance paragraph
- The `### Navigation` table (where to find the HLD, the `docs/intent/` design tree, EARS specs, decision docs)
- The `### Terminology` section (HLD / LLD / sub-HLD, EARS, Arrow, Arrow segment, Cascade)
- The `### Code annotations` section (`@spec` usage and placement)

The skill treats reconcile-conventions differences as **proposed updates requiring confirmation**, and rewriting `CLAUDE.md` prose you may have trimmed on purpose is a judgment call — so I have not applied it.

**Recommendation:** replace the divergent directive section with the current template body from
`plugins/linked-intent-dev/skills/update-lid/references/claude-md-template.md`
(everything from `## Linked-Intent Development (MANDATORY)` through `### Code annotations`), preserving your existing `# My Project` heading and the current, correct `## LID` block above it. The `## LID Tooling` section stays omitted unless you have a coherence-check script to declare. If you intentionally slimmed this block, say so and I'll leave it.

To apply, reply to proceed and I'll make the edit and read it back to you.

## Not drift — just an unfinished project (informational)

- `docs/high-level-design.md` is a stub (`## Problem` → *not yet specified*).
- `docs/intent/` holds no design docs yet.

These are empty-but-present, which is fine for configuration. Authoring the HLD and LLDs is the `linked-intent-dev` workflow's job, not `/update-lid`'s — so I left both untouched.

## Files changed

**None.** The project was already configured and version-current; the single divergence is surfaced above for your decision rather than auto-applied.
