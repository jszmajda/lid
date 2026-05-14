# /update-lid eval-2 summary — idempotent on configured project

## User prompt

"Please set up LID in this project."

## Detection signals (per SKILL.md "Detection signals")

Ran the skill's exact detection rules against `/tmp/update-lid-eval-fixtures/eval-2/project/`:

- **LID directives present**: YES. `CLAUDE.md` contains the literal string `Linked-Intent Development` (in the `## Linked-Intent Development (MANDATORY)` heading) and the literal string `linked-intent-dev` (in the consult instruction).
- **Mode marker present**: YES. `CLAUDE.md` contains `## LID Mode: Full` on line 3.
- **Arrow-maintenance overlay present**: NO. `docs/arrows/` does not exist.
- **Required directories**:
  - `docs/high-level-design.md` — present (stub, 5 lines).
  - `docs/llds/` — present (empty).
  - `docs/specs/` — present (empty).
- **`docs/planning/`** — absent (no legacy cleanup needed).
- **Convention drift in `CLAUDE.md` directives**: YES — see below.

## State dispatch

The detected state — LID directives + mode marker present, all required directories present, no mode change requested — maps to the **"Reconcile conventions"** row of the skill's state-dispatch table:

> *LID directives + mode marker, no mode change requested* → Reconcile conventions — check for convention drift (missing directories or files, outdated CLAUDE.md sections) and surface each detected difference as a proposed update requiring user confirmation.

Per the eval instructions, drift is surfaced but **not auto-applied** (no live user to confirm).

## Action taken

**No files modified.** The skill's framing for this state is "surface drift, await user confirmation." Since this eval has no interactive user, the appropriate behavior is to enumerate the drift and stop.

The starting project state was copied verbatim to `with_skill/project/`.

## Drift detected (would be surfaced to the user for per-item confirmation)

The `CLAUDE.md` directives block is severely truncated relative to `references/claude-md-template.md`. The current file contains only the heading, mode marker, and the opening sentence + arrow code block. Missing sections, in template order:

1. **Workflow bullets** after the `HLD → LLDs → EARS → Tests → Code` code block:
   - "New features and refactors: full six-phase workflow…"
   - "Bug fixes: walk the arrow like any other change…"
   - "If unsure: use the full workflow."
2. **Phase-stop / mutation directive**: "Stop after each phase for user review. Mutation, not accumulation — docs reflect current intent, not history."
3. **`### Navigation` table** — the four-row table pointing at `docs/high-level-design.md`, `docs/llds/`, `docs/specs/`. The arrow-overlay row should remain **omitted** (correctly) because `docs/arrows/` is absent — re-add only if the overlay is later installed.
4. **`### Terminology` section** — HLD / LLD / EARS / Arrow / Arrow segment / Cascade definitions.
5. **`### Code annotations` section** — `@spec` annotation convention and entry-point placement rule.
6. **`## LID Tooling` section** — correctly omitted per the template's conditional-include rule (no tooling to declare in this project). No action needed unless the user later adds a coherence-check script.

## What would happen with a live user

The skill would present each drift item as a discrete proposal (e.g., "Append the Navigation table?" / "Append the Terminology section?") and append confirmed items to the existing `CLAUDE.md`, preserving existing content per the "Do-not-overwrite rule." After any append, the skill would read back `CLAUDE.md` and summarize the sections added per the "Verification / show-what-changed" guidance.

If the user declined every proposal, the skill would still emit the inform-and-skip summary above before exiting (per the "Idempotency and inform-and-skip" section: "when convention drift is detected but the user declines every proposed update, still summarize what was found before exiting").

## Inform-and-skip summary (what the user sees regardless)

- Mode: **Full**
- Arrow-maintenance overlay: **not installed** (no `docs/arrows/`)
- Required directories: **all present** (`docs/high-level-design.md`, `docs/llds/`, `docs/specs/`)
- `docs/planning/` legacy directory: **absent** (no cleanup needed)
- Convention drift in `CLAUDE.md`: **detected** (six missing sections enumerated above)
