---
name: bidirectional-differential
description: Audit coherence across an arrow of intent by running two parallel fresh Claude sessions — one reconstructs code from a single EARS, the other reconstructs the EARS from stripped code — then classifies the drift between them. Use when the user invokes /differential-audit, asks to audit EARS-to-code drift for a feature or segment, wants a differential round-trip on a specific spec, or reaches Phase 6 code-complete in linked-intent-dev with arrow-maintenance overlay present and a touched-EARS set to consider. Surfaces intent that the code encodes but the EARS doesn't state, and requirements the EARS states but the code under-pins. Requires docs/arrows/ overlay. Heavy per-EARS cost in subprocess spawns and Anthropic API spend; scope via the opening conversation before running.
---

# Bidirectional Differential

This skill runs a bidirectional differential audit on EARS↔code pairs. The audit is **advisory** — findings concentrate human review on specific cases, and acting on findings is always user-judged. When the audit surfaces drift, the recommended repair path walks the whole arrow: validate intent with the user, then cascade EARS → Tests → Code.

## When to act

**Command mode** — user invokes `/differential-audit`:
- No arguments → open the scoping conversation (see §Scoping).
- One or more EARS IDs as arguments → audit them directly with configured defaults; skip the scoping conversation.

**Ambient mode** — at linked-intent-dev's Phase 6 boundary (code is complete for a change) in a project where arrow-maintenance's overlay exists and ambient triggering is not disabled. Emit **one batched prompt** listing every EARS the change touched, offering `all`, `none`, a comma-separated subset, or `skip-arrow`. If ambient is disabled in the project's `CLAUDE.md` (see §Configuration), do not fire.

Ambient mode is advisory: declining, skipping, or any classification outcome MUST NOT block Phase 6 completion.

## Hard precondition — arrow-maintenance overlay

Before spawning any blind sessions in either mode, verify the arrow-maintenance overlay exists:

- `docs/arrows/index.yaml` present, and
- at least one per-arrow overlay file under `docs/arrows/`.

If absent, abort with:

> *Bidirectional differential audits attach to the arrow-maintenance overlay. Run /lid-setup and then /arrow-maintenance first to establish the arrow surface this skill extends.*

Do not spawn any `claude -p` sessions and do not write any files when the overlay is absent. This skill is heavier maintenance than arrow-maintenance; a project without the lighter layer in place will not act on this skill's findings either.

## Scoping

The scoping conversation is the first user-facing moment. The audit itself runs without further input once scope is fixed. Full script in `references/scoping-conversation.md`.

Users describe what they want audited in natural terms — "the login flow", "the billing pipeline", "the scoring rules" — more often than in arrow or LLD names. The scoping conversation interprets those descriptions, maps them to arrows/LLDs in the overlay, and confirms the mapping with the user before moving to EARS-level scope. Then it captures the final EARS set and the runs-per-direction (default 3) and shows a cost estimate before spawning anything.

**Do not auto-select EARS.** The skill does not have a reliable heuristic for picking which EARS to audit within a chosen arrow — that choice is the user's, and the scoping conversation exists precisely to surface it.

## Audit protocol

For each scoped EARS, execute the six-step protocol in `references/audit-protocol.md`. Summary:

1. **Resolve inputs**. EARS text from `docs/specs/`; implementing code from regions annotated with `@spec {EARS-ID}`. If no `@spec` points at the EARS, surface a coverage-gap entry and skip this EARS.
2. **Strip leaky identifiers** from the code before the B-direction receives it — `@spec` annotations, EARS ID mentions, vocabulary-echoing identifiers, comments paraphrasing the EARS, test describe/it strings that echo EARS phrasing. See `references/audit-protocol.md §Stripping rules`. The B-direction session must not be able to reconstruct the EARS by reading it back out of the code.
3. **Spawn N A-direction sessions** in parallel via `claude -p`. Each gets only the EARS text + a one-line codebase description. Task: produce naive implementation.
4. **Spawn N B-direction sessions** in parallel via `claude -p`, concurrent with A-direction. Each gets only the stripped code + a one-line EARS-syntax reminder. Task: reconstruct the EARS.
5. **Compare and classify**. Within-direction variance first (do A-runs agree with each other; do B-runs agree with each other); between-direction alignment second (does A's diff against real code correspond to B's diff against real EARS). Pick one of the six codes:
   - `BD-COHERENT`, `A-ONLY-DRIFT`, `B-ONLY-DRIFT`, `BIDIRECTIONAL-DRIFT`, `INCONSISTENT-BLIND` — see `references/classification-codes.md` for decision rules and worked examples.
   - `UNANNOTATABLE` — signpost for negative requirements with no production sink (see §Unwanted below).
6. **Write the per-EARS audit record** to `docs/arrows/experiments/bidirectional-differential/{segment-name}/{EARS-ID}.md` using the template in `references/audit-report-template.md`. Re-running replaces the file (mutation, not accumulation — commit the old audit before re-running if before/after comparison matters).

**Default N=3.** If within-direction runs split 2-vs-1 on the classification-relevant dimension, re-run the affected direction at N=5 and classify on the majority. If the 5-run result still splits or the split shape changes between runs, classify `INCONSISTENT-BLIND` — don't force a code.

After per-EARS records are written, produce a **user summary** with per-arrow classification counts, top-priority drift findings across the audited scope, and recommended next steps per §Repair path.

## Output location

Audit records live in a reserved sibling subtree under arrow-maintenance's root:

```
docs/arrows/experiments/bidirectional-differential/{segment-name}/{EARS-ID}.md
```

**Do not mutate existing per-arrow overlay files** (`docs/arrows/{segment}.md`, `docs/arrows/index.yaml`). Experiment artifacts stay in the reserved subtree so arrow-maintenance's audit loop can ignore them. Retirement of this experiment is `rm -rf docs/arrows/experiments/bidirectional-differential/`; promotion is a single move to a core namespace.

## Repair path — cascade through the arrow

LID's arrow is HLD → LLD → EARS → Tests → Code. When the audit surfaces drift, the recommended repair path walks the arrow in order. Every reconciliation recommendation in the audit record (and every finding in the user summary) takes this shape:

1. **Validate the discovered intent with the user.** The B-direction's reconstructed EARS or the A-direction's divergent implementations represent *candidate* intent. The user decides which version matches what was actually meant. No edit happens before this confirmation.
2. **Check LLD coherence.** Does the current LLD reflect the validated intent, or does the LLD itself need updating? An LLD that already captures the invariant makes the EARS edit mechanical; an LLD that does not is a cascade starting point.
3. **Update the EARS.** Reword the spec to cite the validated invariants, or add a companion unwanted-behavior EARS where the original is under-specified in a way a single rewrite can't capture.
4. **Update the tests.** The updated EARS needs tests that assert it. If the test suite does not currently cover the validated invariant, adding test coverage is the *next* step, not an afterthought — this is LID's tests-first discipline applied retroactively.
5. **Adjust the code only if needed.** If the validated intent matches current behavior, steps 1–4 leave the code untouched. If the validated intent differs (a real bug), the code change comes last, after the EARS and tests are updated to describe and assert the intended behavior.

The default Action in the audit record (`reconcile-EARS`, `reconcile-code`, etc.) names which layer the cascade *starts with* — but the cascade always walks LLD → EARS → Tests → Code in order, not just the named layer.

## Unwanted-condition handling

- **Overlay absent** → abort with the §Hard precondition message. No sessions, no files.
- **No `@spec` annotation for a scoped EARS** → emit a coverage-gap entry in the summary; do not spawn blind sessions for that EARS.
- **Negative requirement with no production sink** (e.g., `shall NOT mutate the input`) → emit `UNANNOTATABLE` with a signpost recommending either (a) pair with an unwanted-behavior EARS and a test that asserts the negation — the test carries the `@spec`, and future audits target the test file — or (b) defer to a sibling absence-audit skill if one exists. Do not force a coherence classification code for such EARS.
- **B-direction reconstruction word-overlap > ~70% with the real EARS** → flag as a *suspected stripping-rule failure*. Surface the spot-check in the audit record rather than silently emitting `BD-COHERENT`. A false coherent from leaked identifiers is this skill's most dangerous failure mode; the spot-check is the mitigation.

## Configuration

Project-level overrides live in `CLAUDE.md`:

```
## LID Experimental
bidirectional-differential:
  ambient: false           # disable the Phase-6 ambient hook for this project
  default-runs: 5          # override N=3
```

Absent keys use skill defaults. `--runs=N` on the command line overrides both per-run.

## Coordination with other LID skills

| Concern | Owner |
|---|---|
| Arrow overlay presence, per-segment arrow docs, `index.yaml` | arrow-maintenance |
| EARS authoring, `@spec` annotation placement, phase cascade | linked-intent-dev |
| Phase 6 ambient trigger surface (this skill emits the prompt; linked-intent-dev sets the phase boundary) | bidirectional-differential (this skill) |
| Audit record files under `docs/arrows/experiments/bidirectional-differential/` | bidirectional-differential (this skill) |
| Reconciliation cascade (validate → LLD → EARS → Tests → Code) | linked-intent-dev's phase workflow, triggered by the user after reviewing audit records |

## Subprocess invocation pattern

Blind sessions run via `claude -p`. The Bash tool invocation pattern:

```bash
claude -p --output-format json "<prompt-with-only-EARS-or-only-stripped-code>" < /dev/null
```

`< /dev/null` prevents inherited stdin hangs when spawning in parallel. Parse the JSON output for the assistant message body. Run A-direction and B-direction sessions concurrently via multiple background invocations.

Each session is **fresh context**. Do not pass additional tools, MCP servers, or project files into the subprocess — the audit depends on the session seeing only what was given.

## Reference files

- `references/audit-protocol.md` — full six-step protocol, stripping rule categories, split-result rule with examples.
- `references/classification-codes.md` — decision rules and worked examples for each code; Classification → Action mapping.
- `references/scoping-conversation.md` — conversation script: interpreting user descriptions, mapping to arrows, capturing scope and N.
- `references/audit-report-template.md` — per-EARS audit-record output template.

Test fixtures (3 baseline, more pending) live in `evals/evals.json`.
