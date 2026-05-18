A note before the report: you asked me to run `/lid-coach` and then fix any issues I find. `/lid-coach` is deliberately **advisory** — it surfaces recommendations but does not edit project files. Silent edits inside a coach run would bypass your review on exactly the decisions where review matters most (what your HLD should say, how your intent decomposes into LLDs and specs). So I'll produce the review below and point you at the commands that apply the fixes — `/update-lid` for the configuration and bootstrap work, and `/linked-intent-dev` if you have a concrete build in mind. The "what is working / what to do next" is all here; you stay in the loop on application.

---

# LID Coach Review

## Executive summary

**Posture:** *Bootstrapping — configuration in place, content not yet authored.*

This is a correctly-wired but empty project: the LID directives and mode marker are present and well-formed, the standard directory skeleton exists, but the arrow has no content yet. That's a normal place to be at the start; the review below is about what to fill in, not drift to repair.

**Scorecard**
- ✓ Configuration — `CLAUDE.md` has LID directives and a valid `## LID Mode: Full` marker
- ✓ Directory skeleton — `docs/llds/` and `docs/specs/` exist (placeholder-kept)
- ✗ HLD content — present but boilerplate ("We are building a thing")
- ✗ LLDs — none authored
- ✗ Specs — none authored
- ⚠ Mode fit — Full is declared; can't yet confirm it matches reality with no content to judge against

**Headline:** The wiring is right and the mode is declared explicitly rather than defaulted — that's the foundation LID needs and it's solid. The single most valuable next step is authoring a real HLD; everything downstream (LLDs, specs, tests, code) cascades from it, so the boilerplate HLD is the one finding blocking the arrow from being walkable at all.

## Findings (4 total · 3 high · 1 medium)

- **F1 (high):** HLD is boilerplate — "We are building a thing", no problem/approach/goals · *HLD is architecture and rationale*
- **F2 (high):** No LLDs authored — `docs/llds/` holds only `.gitkeep` · *one LLD per intent component*
- **F3 (high):** No EARS specs authored — `docs/specs/` holds only `.gitkeep` · *effective intent-tree alignment*
- **F4 (medium):** `CLAUDE.md` is minimal — directive present but no navigation, terminology, or annotation conventions · *minimum surface, maximum discipline*

## Detailed findings

**F1 — High. The HLD is a placeholder.** `docs/high-level-design.md` contains only a `# HLD` heading, a `## Problem` section, and the sentence "We are building a thing." Under *HLD is architecture and rationale* — the HLD carries the project's *why*: problem, approach, target users, goals and non-goals, key design decisions, success metrics. Why this matters: the HLD is the root of the arrow. Every LLD traces to an HLD section and every spec's `{FEATURE}` prefix traces to an architecture concept; with no real HLD there is nothing for the rest of the arrow to hang from, and any LLDs or specs written now would have no upstream to stay coherent with. Recommended action: run `/linked-intent-dev` with a description of what you're building — its Phase 1 will walk you through authoring the HLD properly. If you're not building yet and just want the project configured, `/update-lid` will bootstrap the structure and prompt you for the HLD content.

**F2 — High. No LLDs exist.** `docs/llds/` contains only `.gitkeep`. Under *one LLD per intent component* — each "thing" a user would name (a subsystem, feature, or service) gets its own LLD. In Full mode an empty `docs/llds/` is only a gap when there is observed behavior that should be documented; there's no code here yet, so this isn't drift — it's simply the next phase of the arrow waiting to be authored once the HLD is real. Why this matters: LLDs are where the solution space gets closed enough that two agents reading them land on compatible implementations; without them, the first code-generating session fills the edges in itself and intent drift enters immediately. Recommended action: author LLDs as part of the `/linked-intent-dev` workflow once the HLD names the components — don't write LLDs ahead of a real HLD, or they'll have nothing to trace to.

**F3 — High. No EARS specs exist.** `docs/specs/` contains only `.gitkeep`. Under *effective intent-tree alignment* — spec `{FEATURE}` prefixes correspond to LLD intent components, which correspond to HLD architecture concepts. Why this matters: specs are the grep-anchored, testable statements of intent; with none, there is nothing for tests to cite and nothing the arrow-walker can traverse. As with F2, this is sequencing, not drift — specs follow LLDs in the canonical `HLD → LLDs → EARS → Tests → Code` shape. Recommended action: let specs come out of the `/linked-intent-dev` workflow after the LLDs exist.

**F4 — Medium. `CLAUDE.md` carries the directive but little else.** The file has `## LID Mode: Full` and a one-line "Consult the linked-intent-dev skill" directive — that's enough for the skill to trigger and for the mode to be explicit (good — *modes are declared, not inferred* is satisfied). What's absent is the supporting scaffolding most LID projects carry: a navigation table (where the HLD / LLDs / specs / arrows live), terminology, and the `@spec` annotation convention. Under *minimum surface, maximum discipline* this is not a demand to bloat the file — but a navigation table and the annotation convention are the standard minimum, not custom surface, and they pay for themselves the first time a fresh session has to find anything. Why this matters: a future agent reading this `CLAUDE.md` cold learns the project does LID but not how this project's arrow is laid out, so it re-derives that every session. Recommended action: run `/update-lid` — it reconciles `CLAUDE.md` to the standard directive block (navigation, terminology, annotation convention) without over-configuring.

## What was audited

- Read fully: `CLAUDE.md`, `docs/high-level-design.md`
- Enumerated: `docs/llds/` (empty — `.gitkeep` only), `docs/specs/` (empty — `.gitkeep` only)
- No arrow-maintenance overlay present (`docs/arrows/` absent) — no structural audit delegated
- No code or test files present — no `@spec` sampling possible
- Dispatch: LID directives + valid Full mode marker present; `docs/llds/` and `docs/specs/` unpopulated → reduced review of what exists, missing phases surfaced as high-priority findings (per the coach's dispatch table)

## On your request to "fix any issues"

I'm not applying these as edits from inside the coach, by design — the advisory posture is load-bearing here. The fixes for F1–F3 aren't mechanical anyway: they require *your* intent (what problem this solves, how it decomposes), which is precisely the input `/linked-intent-dev` is built to elicit. Concretely, the fastest path:

1. **`/linked-intent-dev`** with a description of what you're building — this drives F1 (real HLD) and then cascades into F2 (LLDs) and F3 (specs) in order, the way the arrow is meant to be authored.
2. **`/update-lid`** to round out `CLAUDE.md` (F4) — run it any time; it's independent of the build.

If you're not ready to build yet, run `/update-lid` alone first: it bootstraps the structure and gives you a populated `CLAUDE.md`, leaving the HLD/LLD/spec authoring for when you start the first feature.

## Offer to help

Want me to walk through any of these findings in more detail, or talk through how to frame the HLD for what you're building before you run `/linked-intent-dev`? Pick a finding and we can work it.

If you have broader questions about using LID — where a PRD fits relative to the HLD, when Full vs. Scoped mode is the right call for a project this early, or how to stage the first few LLDs — I can help with those too.
