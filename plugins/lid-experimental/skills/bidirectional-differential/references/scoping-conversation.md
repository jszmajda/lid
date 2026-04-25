# Scoping conversation

The first user-facing moment of `/differential-audit`. The audit itself runs without further input once scope is fixed, so this conversation is where alignment with the user happens.

**Goal**: help the user pick the EARS they actually want audited, and confirm the selection before spawning blind sessions. The scoping conversation does **not** attempt to auto-select or recommend a scope — picking targets is the user's judgment call.

## Step-by-step

### 1. Interpret the user's description

Users typically describe audit targets in feature-level terms — *"audit the login flow"*, *"check the billing pipeline"*, *"I want to look at the scoring rules"* — rather than by arrow or LLD name. Translate.

Read `docs/arrows/index.yaml` and scan the arrows' LLD pointers and per-segment overlay files to surface candidate mappings. Present the mapping to the user:

> *"When you say '{user's phrase}', I think you mean the {arrow-name} arrow — that's {one-line description from the arrow doc or its LLD's Context section}, covered by {LLD path}. Is that the right scope, or did you mean something else?"*

If multiple arrows plausibly match, list them and ask:

> *"'{user's phrase}' could match:*
> - *{arrow-1} — {one-line description}*
> - *{arrow-2} — {one-line description}*
>
> *Which of these did you mean, or both?"*

If no arrow clearly matches, say so and offer to list the full arrow inventory. Do not guess.

If the user named arrows or LLDs directly (e.g., *"audit the `auth` arrow"* or *"the specs in `billing.md`"*), skip the interpretation step and confirm the literal mapping.

### 2. Confirm the arrow-level scope

Wait for the user to confirm which arrow(s) are in scope before moving on. Alignment here matters — an audit run on the wrong arrow wastes the user's money and attention.

### 3. Pick EARS within the chosen arrow(s)

Once arrow-level scope is confirmed, show the EARS inventory for each selected arrow:

> *"In {arrow-name}, the EARS are:*
> - *{EARS-ID-1} {status marker}: {first-sentence snippet of the EARS text}*
> - *{EARS-ID-2} {status marker}: {first-sentence snippet}*
> - *...*
>
> *Which would you like audited? You can list IDs, say 'all implemented' (every `[x]` EARS in the arrow), or ask questions about specific specs."*

Accept:
- **Explicit list** — `KWP-UE-004, KWP-UE-005, KWP-SCORE-001`.
- **All implemented** — every `[x]` EARS in each selected arrow. Skip `[ ]` (active gaps — no code yet to audit) and `[D]` (deferred).
- **Mix across arrows** — e.g., *"all of scoring, plus just PREF-001 from pref"*.

Do not auto-select or rank-by-heuristic. The user decides which specs pay.

### 4. Capture N (runs per direction)

Default is **3**. Ask:

> *"How many runs per direction? Default is 3, which costs roughly ${count × ~$0.10} in Anthropic API spend (each EARS does N × 2 short `claude -p` calls). Higher N gives more confidence at higher cost; lower N is cheaper but risks split results."*

Accept an integer. The configured `default-runs` in `CLAUDE.md`'s `## LID Experimental` section is the baseline when the user does not specify.

### 5. Confirm before spawning

Show the final plan and cost estimate:

> *"About to audit:*
> - *{EARS-ID-1} — {one-line EARS snippet}*
> - *{EARS-ID-2} — {one-line EARS snippet}*
> - *...*
>
> *At N={N} runs per direction. Estimated Anthropic API cost: ~${count × ~$0.10}. Proceed?"*

Only spawn `claude -p` sessions after explicit confirmation.

---

## Defaults when scoping is skipped

When the skill is invoked in command mode with explicit EARS IDs as arguments (`/differential-audit KWP-UE-004 KWP-SCORE-001`), skip the scoping conversation entirely. Use the configured `default-runs`.

When the skill is invoked ambiently at Phase 6 with a touched-EARS set, emit the batched ambient prompt directly (see SKILL.md §When to act) — the user picks the subset via `all`/`none`/subset/`skip-arrow`.

---

## Notes

- **Cost transparency matters.** Users should never be surprised by per-audit Anthropic API spend. Surface the rough estimate before confirmation and again in the per-run user summary at the end.
- **Do not audit `[ ]` or `[D]` EARS.** `[ ]` (active gap) means no implementing code exists yet to audit against. `[D]` (deferred) means the EARS is intentionally not current — auditing it produces noise.
- **Respect the user's scope picks even when they seem odd.** If the user asks to audit one EARS in isolation from its siblings, do not push back — they may be investigating a specific drift hypothesis. The user is always right about scope.
