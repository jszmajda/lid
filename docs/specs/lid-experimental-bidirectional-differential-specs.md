# bidirectional-differential specs

**LLD**: docs/llds/lid-experimental/bidirectional-differential.md
**Implementing artifacts** (planned — skill not yet built):
- plugins/lid-experimental/skills/bidirectional-differential/SKILL.md
- plugins/lid-experimental/skills/bidirectional-differential/commands/differential-audit.md
- plugins/lid-experimental/skills/bidirectional-differential/references/audit-protocol.md
- plugins/lid-experimental/skills/bidirectional-differential/references/classification-codes.md
- plugins/lid-experimental/skills/bidirectional-differential/references/signal-priors.md
- plugins/lid-experimental/skills/bidirectional-differential/references/scoping-conversation.md
- plugins/lid-experimental/skills/bidirectional-differential/references/stripping-rules.md
- plugins/lid-experimental/skills/bidirectional-differential/references/audit-report-template.md

**Scope**: These specs cover the `/differential-audit` command-mode behavior and the Phase-6 ambient-mode entry point. Per-EARS timeout behavior and the scoping-conversation's full script are deferred to Phase 4 edge audit / reference files and are not EARS'd here.

Status markers: `[x]` implemented · `[ ]` active gap · `[D]` deferred

---

## Invocation and Scoping

- `[ ]` **BIDIFF-001**: When `/differential-audit` is invoked with no arguments, the system SHALL open a scoping conversation that asks the user which part of the project to audit, translates natural-language descriptions into specific arrows using the arrow-overlay's segment descriptions, captures the final EARS selection and runs-per-direction, and confirms the plan with a cost estimate before spawning any blind sessions.
- `[ ]` **BIDIFF-002**: When `/differential-audit` is invoked with one or more explicit EARS IDs as arguments, the system SHALL skip the scoping conversation and audit the listed EARS using configured defaults.
- `[ ]` **BIDIFF-003**: During the scoping conversation, the system SHALL present the EARS inventory for each confirmed arrow (IDs, status markers, first-sentence snippets) and accept the user's explicit scope selection — individual EARS IDs, all `[x]` EARS in an arrow, or a mix across arrows — without auto-selecting, ranking, or recommending a subset.

## Precondition — Arrow-Maintenance Overlay

- `[ ]` **BIDIFF-005**: Before spawning any blind sessions in either command or ambient mode, the system SHALL verify `docs/arrows/index.yaml` exists and at least one per-arrow overlay file is present under `docs/arrows/`.

## Audit Protocol

- `[ ]` **BIDIFF-006**: For each scoped EARS, the system SHALL resolve the EARS text from `docs/specs/` and the implementing code from regions annotated with `@spec {EARS-ID}` in the codebase.
- `[ ]` **BIDIFF-007**: Before spawning the B-direction session for each EARS, the system SHALL strip leaky identifiers from the code input per `references/stripping-rules.md` — removing `@spec` annotations and EARS ID mentions, renaming vocabulary-echoing identifiers, stripping or genericizing comments that paraphrase the EARS, and genericizing or excluding test files whose describe/it strings echo EARS phrasing.
- `[ ]` **BIDIFF-008**: For each scoped EARS, the system SHALL spawn N A-direction `claude -p` subprocess sessions in parallel. Each A-direction session SHALL receive only the EARS text plus a one-line codebase description, with no access to the existing code.
- `[ ]` **BIDIFF-009**: For each scoped EARS, the system SHALL spawn N B-direction `claude -p` subprocess sessions in parallel, concurrent with the A-direction sessions. Each B-direction session SHALL receive only the stripped code plus a one-line EARS-syntax reminder, with no access to the existing EARS text.
- `[ ]` **BIDIFF-010**: The default value of N SHALL be 3 per direction. The system SHALL accept a `--runs=N` argument override, and SHALL honor `bidirectional-differential.default-runs` from `CLAUDE.md` project configuration when set.
- `[ ]` **BIDIFF-011**: After collecting A- and B-direction outputs, the system SHALL compute within-direction variance first (do A-runs agree with each other; do B-runs agree with each other), then between-direction alignment (does the A-diff against real code correspond to the B-diff against real EARS), and classify the pair as one of `BD-COHERENT`, `A-ONLY-DRIFT`, `B-ONLY-DRIFT`, `BIDIRECTIONAL-DRIFT`, or `INCONSISTENT-BLIND` per `references/classification-codes.md`.
- `[ ]` **BIDIFF-012**: When within-direction runs split 2-vs-1 on the classification-relevant dimension at N=3, the system SHALL re-run the affected direction at N=5 and classify on the majority. If the 5-run outcome still splits or the split shape changes between runs, the system SHALL classify the pair as `INCONSISTENT-BLIND`.

## Output Records and Summary

- `[ ]` **BIDIFF-013**: For each audited EARS, the system SHALL write a per-EARS audit record to `docs/arrows/experiments/bidirectional-differential/{segment-name}/{EARS-ID}.md`, where `{segment-name}` is the arrow segment the EARS belongs to. Re-running an audit for the same EARS SHALL replace the file contents rather than append.
- `[ ]` **BIDIFF-014**: Each audit record SHALL include an ISO timestamp of the run, the git SHA of the repository at audit time, N (runs per direction), the classification, the default recommended Action per the Classification → Action table in the LLD, the verbatim EARS text, code-location anchors (file:line), per-direction summaries, drift findings tagged with severity (possible-bug / latent-refactor-hazard / pure-documentation), and recommended reconciliations.
- `[ ]` **BIDIFF-015**: At the end of each run, the system SHALL produce a user summary with per-arrow classification counts, the top-priority drift findings across the audited scope, and the recommended reconciliation actions.
- `[ ]` **BIDIFF-023**: For every non-`BD-COHERENT` finding (in both the per-EARS audit record and the user summary), the recommended reconciliation SHALL walk the LID arrow cascade: first validate the discovered intent with the user, then check LLD coherence against the validated intent, then update the EARS, then update tests to assert the invariant, and adjust code only if the validated intent differs from current behavior. The Default Action value names the starting layer; the cascade always walks downstream layers in order.

## Ambient Mode

- `[ ]` **BIDIFF-016**: At `linked-intent-dev`'s Phase 6 boundary (code complete), when ambient mode is enabled for the project, the system SHALL emit a single batched prompt listing every EARS the change touched and offering the user the response options `all`, `none`, a comma-separated subset of EARS IDs, or `skip-arrow` (suppresses further ambient prompts for the same arrow for the rest of the session).
- `[ ]` **BIDIFF-017**: Ambient-mode audits SHALL be advisory-only: declining the prompt, skipping the arrow, or receiving any classification outcome (including `BIDIRECTIONAL-DRIFT` or `INCONSISTENT-BLIND`) SHALL NOT block completion of the Phase 6 handoff.

## Project Configuration

- `[ ]` **BIDIFF-018**: When `CLAUDE.md` contains a `## LID Experimental` section with a `bidirectional-differential:` subtree, the system SHALL honor its keys: `ambient: false` disables the Phase-6 ambient hook; `default-runs: N` overrides the default N=3. Absent keys SHALL use skill defaults.

## Unwanted Behavior

- `[ ]` **BIDIFF-019**: If the arrow-maintenance overlay is absent when the skill is invoked in either mode, then the system SHALL abort with a message directing the user to run `/lid-setup` and `/arrow-maintenance` first, and SHALL NOT spawn any `claude -p` sessions or write any files under `docs/arrows/experiments/`.
- `[ ]` **BIDIFF-020**: If a scoped EARS has no `@spec` annotation pointing at it from the codebase, then the system SHALL emit a coverage-gap entry in the user summary and SHALL NOT spawn blind sessions for that EARS.
- `[ ]` **BIDIFF-021**: If a scoped EARS is a negative requirement ("shall NOT X") with no production-code sink to annotate, then the system SHALL emit the signpost code `UNANNOTATABLE` for that EARS with a recommendation to either pair with an unwanted-behavior EARS and a test that asserts the negation (where the test carries the `@spec`), or defer to a sibling absence-audit experiment. The system SHALL NOT force one of the five coherence classification codes for such EARS.
- `[ ]` **BIDIFF-022**: If B-direction reconstruction produces an EARS with greater than approximately 70% word overlap against the real EARS, then the system SHALL flag the result as a suspected stripping-rule failure in the audit record and SHALL surface the spot-check in the user summary rather than silently emitting `BD-COHERENT`.
