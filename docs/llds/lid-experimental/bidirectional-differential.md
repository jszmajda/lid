# Bidirectional Differential

Sub-LLD under `docs/llds/lid-experimental.md`. Experimental LID skill that audits EARS↔code coherence via parallel blind LLM reconstructions. Distributed as a standalone plugin: `plugins/lid-experimental/`, installed via `/plugin install lid-experimental@jszmajda-lid`. Opt-in; not part of the default LID install.

## Context and Design Philosophy

Bidirectional differential runs two fresh Claude sessions in parallel against a single EARS-and-code pair. One reconstructs code from the EARS (A-direction); the other reconstructs the EARS from stripped code (B-direction). The relationship between A's diff against the real code and B's diff against the real EARS classifies the coherence of the pair. The audit surfaces intent the code encodes but the EARS doesn't state, and requirements the EARS states but the code under-pins.

The mechanism is deliberately simple: plain text in, plain text out, language-agnostic, no binary to install beyond Claude Code itself. The audit is **advisory, not a gate** — findings concentrate human review on specific drift cases, and acting on findings is always user-judged.

Four principles shape every design choice below:

1. **Scope is a user choice, not a heuristic.** The skill opens with a conversation because deciding what to audit is the user's judgment call — no auto-selection or prior-driven recommendation is applied. The conversation interprets natural-language descriptions ("the login flow") into concrete arrows and confirms alignment before spawning anything.
2. **Arrow-maintenance is a hard precondition.** This skill is heavier maintenance than arrow-maintenance itself. A project without the discipline to keep arrow overlays clean will not act on differential audit findings either. The hard abort protects users from adopting this layer before the layer beneath it is in place.
3. **Experiment artifacts live in a reserved sibling subtree.** Audit records land under `docs/arrows/experiments/bidirectional-differential/` — they do not mutate existing arrow overlay files. Retirement is `rm -rf`; promotion is a single move.
4. **Repair walks the full arrow.** The audit technique compares EARS and code, but the LID arrow is HLD → LLD → EARS → Tests → Code. When drift is found, the recommended repair path always starts by validating the discovered intent with the user, then checks LLD coherence, then cascades EARS → Tests → Code. Tests are a first-class layer; the skill does not recommend a code change without first ensuring tests exist to assert the intended behavior.

**Tool dependency.** The protocol shells out to `claude -p` for context-free subagent sessions. First-iteration support is Claude-Code-only; porting to other agentic coding tools depends on each tool exposing an equivalent one-shot mode.

**Cost shape.** Per-EARS audit: ~6 short `claude -p` calls (3 per direction at default N=3) — a few cents of Anthropic API spend at Sonnet rates. Per-arrow (5–20 EARS): a fraction of a dollar. Per-codebase (hundreds of EARS): tens of dollars. Wall-clock is left unspecified — LLM-based subprocess timing is too variable to commit a number to. The scoping conversation exists to prevent casual invocation of the per-codebase shape.

## Mechanism

For each scoped EARS + its `@spec`-annotated code:

- **A-direction**. Spawn a fresh `claude -p` session with *only* the EARS text and a one-line codebase description. Ask it to write a naive implementation. Compare against the real code. Differences = places the code has content the EARS doesn't pin down.
- **B-direction**. Spawn a parallel fresh session with *only* the stripped code (see §Stripping rules) and a one-line EARS-syntax reminder. Ask it to reconstruct the EARS. Compare against the real EARS. Differences = places the code embeds intent the EARS doesn't state.

The **relationship between A's diff and B's diff** classifies the coherence of the pair. Running N independent sessions per direction (default N=3) catches LLM non-determinism and allows a split-result rule (below).

### Classification codes

| Code | Meaning | Default action |
|---|---|---|
| `BD-COHERENT` | Both directions converge on the real artifact. Intent and code are mutually self-reconstructable. | `acknowledged-coherent` |
| `A-ONLY-DRIFT` | A-runs diverge from real code; B-runs converge on real EARS. EARS under-pins an arbitrary implementation choice. | `advisory` |
| `B-ONLY-DRIFT` | A-runs converge on real code; B-runs elevate unstated invariants (order-preservation, empty-input behavior). Code encodes intent the EARS doesn't state. | `reconcile-EARS` |
| `BIDIRECTIONAL-DRIFT` | Both directions disagree with ground truth in correlated ways. Missing sub-decision, operational halo, or decomposition gap. Highest-signal finding. | Triage per finding: possible-bug → `reconcile-code`; latent-refactor-hazard → `reconcile-EARS`; pure-doc → `reconcile-EARS`. |
| `INCONSISTENT-BLIND` | Within-direction variance too high to classify. EARS is under-specified. | `reconcile-EARS` (refine, re-audit) |
| `UNANNOTATABLE` | EARS is a negative requirement with no `@spec` sink in production code. Out-of-scope for this technique. | Signpost: pair with unwanted-behavior EARS + test, or defer to a sibling absence-audit experiment. |

### Split-result rule at small N

At N=3, a 2-vs-1 within-direction split on the classification-relevant dimension triggers a re-run of the affected direction at N=5. Majority wins. If the 5-run outcome still splits, or the split shape changes between runs, the result is `INCONSISTENT-BLIND` — no classification forced.

## Invocation modes

**Dual-mode**, per parent LLD §"Component Variant":

- **Command mode**: `/differential-audit` (no args) opens the scoping conversation. `/differential-audit <EARS-ID> [<EARS-ID>...]` skips the conversation and audits the listed EARS with defaults.
- **Ambient mode**: the skill triggers at `linked-intent-dev`'s Phase 6 boundary (code complete) with a single batched prompt listing every EARS the change touched. User responds `all`, `none`, a comma-separated subset, or `skip-arrow` (suppresses for this arrow for the rest of the session).

Both modes require arrow-maintenance (§Dependency). Both honor the same config surface.

### Project configuration

Per-project overrides live in `CLAUDE.md`:

```
## LID Experimental
bidirectional-differential:
  ambient: false           # disable the Phase 6 hook
  default-runs: 5          # override N=3
```

## Scoping conversation

The scoping conversation is the first user-facing moment. The audit itself runs without further input once scope is fixed. The conversation has four jobs:

1. **Interpret the user's description**. Users typically describe audit targets in feature-level terms ("audit the login flow", "check the billing pipeline") rather than arrow or LLD names. The skill reads the arrow overlay's segment descriptions, proposes candidate arrows, and confirms alignment with the user before proceeding.
2. **Present the EARS inventory for each confirmed arrow**. Show IDs, status markers, and first-sentence snippets so the user can pick targets explicitly.
3. **Capture the user's explicit EARS selection and runs-per-direction** (default N=3).
4. **Confirm the final plan with a cost estimate** before spawning any `claude -p` sessions.

The conversation does **not** attempt to auto-select, rank, or recommend a subset of EARS to audit. The skill has no reliable heuristic for which EARS yield high-signal audits in an arbitrary project, and a false recommendation is worse than no recommendation. Picking targets is the user's judgment call; the conversation surfaces the inventory and the cost so the user can make the call well.

## Dependency: arrow-maintenance

The skill checks for `docs/arrows/index.yaml` + per-arrow overlay files on invocation. If absent, it aborts with:

> *Bidirectional differential audits attach to the arrow-maintenance overlay. Run /lid-setup and then /arrow-maintenance first to establish the arrow surface this skill extends.*

Audit records live in a reserved sibling subtree at `docs/arrows/experiments/bidirectional-differential/`. They do not mutate existing per-arrow overlay files. This keeps arrow-maintenance's audit loop hands-off the experiment's artifacts. The reserved-namespace convention is documented in `docs/llds/arrow-maintenance.md` §"Experiment-produced artifacts (reserved namespace)".

`docs/arrows/index.yaml` is not extended today. The key `arrows.<segment>.experiments` is reserved for future metadata tracking.

## Audit protocol

1. **Scoping conversation** (unless called with explicit EARS IDs).
2. **Arrow-maintenance precondition**. Abort if the overlay is absent.
3. **For each scoped EARS**:
   1. **Resolve inputs**. EARS text from `docs/specs/`; real code from `@spec`-annotated regions; existing tests (optional context). If no `@spec` annotation points at the EARS, surface as a coverage gap and skip.
   2. **Strip leaky identifiers** from the code (see §Stripping rules).
   3. **Spawn N A-direction sessions** via `claude -p`. Each gets only the EARS text + a one-line codebase description. Task: produce naive implementation.
   4. **Spawn N B-direction sessions** in parallel. Each gets only the stripped code + a one-line EARS-syntax reminder. Task: produce reconstructed EARS.
   5. **Compare and classify** (§Classification codes). Within-direction variance first; between-direction alignment second. Apply split-result rule at 2-vs-1.
   6. **Write per-EARS audit record** to `docs/arrows/experiments/bidirectional-differential/<segment-name>/<EARS-ID>.md`.
4. **Surface summary** to the user: per-arrow classification counts, top-priority drift findings, recommended actions.

### Stripping rules

The goal is a B-direction session that cannot cheat by reading the EARS out of identifiers or comments.

- **Annotations and ID mentions**. Remove `@spec FEATURE-TYPE-NNN` comments and any textual occurrence of the EARS ID.
- **Vocabulary-echoing identifiers**. Rename variables, functions, and fields whose name restates the EARS text. Example: an EARS saying "cap unincorporated entries at N" with code using `unincorporatedEntriesCap` → rename to `maxItems`. Semantics preserved, surface-level spec hints removed.
- **Comments paraphrasing the EARS**. Strip or genericize. Comments explaining *implementation choices* stay; comments restating *requirement intent* go.
- **Test names and describe/it strings**. Genericize if they echo EARS phrasing, or exclude test files from the B-direction input.
- **File and directory names**. Flag but leave alone unless they textually embed the EARS ID. Renaming paths changes too much surrounding context.

**Stripping-failure spot-check**: if B-direction reconstruction produces an EARS that textually matches the real EARS at > ~70% word overlap, treat as suspect and manually verify the B-direction input had no leaked vocabulary. A false `BD-COHERENT` from leaked identifiers is the skill's most dangerous failure mode.

## Output shape

Audit records live at:

```
docs/arrows/experiments/bidirectional-differential/<segment-name>/<EARS-ID>.md
```

Record structure:

```markdown
# Differential audit — <EARS-ID>

**Audit run**: <ISO timestamp>
**Git SHA at audit**: <commit>
**Runs per direction**: <N>
**Classification**: <code>
**Action**: <reconcile-EARS | reconcile-code | advisory | acknowledged-coherent>

## EARS (verbatim)
<paste>

## Code locations
<file:line anchors, stripping applied to B-direction input>

## A-direction — EARS → code (N runs)
<summary: convergent produced code; divergent choices; sub-decisions invented>

## B-direction — code → EARS (N runs)
<summary: reconstructed EARS; elevated sub-decisions; cluster-splits if applicable>

## Drift findings
- <item>: surfaced by A / B / both; severity: possible-bug / latent-refactor-hazard / pure-documentation
- ...

## Recommended reconciliation
- update EARS: <text>
- update code: <change>
- leave as-is: <justification>
- add companion unwanted-behavior EARS for <halo>
```

New audits replace the file. Historical audits remain in git; before/after comparison uses `git diff` across audit commits.

## Integration with linked-intent-dev phases

The skill does not change the six phases. At **Phase 6 (code complete)** it offers a single batched ambient hook:

> *"This change touches 3 EARS: `KWP-UE-004`, `KWP-UE-005`, `KWP-SCORE-001`. Run a differential audit? Bidirectional round-trip against the code you just wrote — surfaces EARS under-specification or code-sourced constraints that the EARS doesn't state. Reply `all`, `none`, a comma-separated subset, or `skip-arrow`."*

Declining is free; the audit is advisory and does not gate completion.

Phase 6 is deliberately chosen over earlier phases. LID's ordering is EARS → Tests → Code. The audit's strongest claim — "code and EARS are mutually coherent" — requires both artifacts in final shape. Running pre-test or pre-code audits an incomplete arrow.

## Skill surface

```
plugins/lid-experimental/skills/bidirectional-differential/
  SKILL.md                         ← prose skill body
  references/
    audit-protocol.md              ← six-step protocol, stripping rules, split-result rule
    classification-codes.md        ← code decision rules + worked examples + Action mapping
    scoping-conversation.md        ← conversation script: interpreting descriptions, capturing scope
    audit-report-template.md       ← per-EARS audit-record template
  commands/
    differential-audit.md          ← /differential-audit command
  evals/
    evals.json                     ← fixture EARS+code pairs with expected classifications
```

No shared code or state with other experiments (parent LLD §"Plugin Structure" rule).

## Eval suite — 10 fixtures

Each fixture is a self-contained EARS + TypeScript code pair with an expected classification. The eval harness runs the skill end-to-end and asserts the classification matches the expected value in ≥4 of 5 eval runs (accepting LLM non-determinism). Fixtures prefixed `KWP-` model real specs from the Threadkeeper case-study codebase; others are synthetic.

**Classification fixtures (6):**

1. `BD-COHERENT` — bounded exhaustive matrix. EARS: scoring table with four explicit branches. Code: the literal matrix. Models KWP-SCORE-001.
2. `BIDIRECTIONAL-DRIFT` — missing sub-decision. EARS: "shall prefer X over Y." Code: `X || Y || ''` then `if (!text) continue;`. Both directions surface empty-string and both-missing sub-decisions. Models KWP-UE-004.
3. `BIDIRECTIONAL-DRIFT` — operational halo. EARS: four-conjunct filter predicate. Code: predicate plus unconfigured-store short-circuit, pagination loop, partial-results-on-error. B-direction elevates 3+ halo requirements. Models KWP-UE-001.
4. `A-ONLY-DRIFT` — arbitrary implementation detail. EARS: "k most recently created entries." Code: correct implementation via one particular sort+slice. A-runs invent different valid combinations; B-runs converge.
5. `B-ONLY-DRIFT` — code has unstated invariant. EARS: "deduplicate a list of IDs." Code: dedupes *and* preserves first-occurrence order *and* is stable on empty input. A-runs produce various dedup implementations; B-runs uniformly elevate order-preservation.
6. `INCONSISTENT-BLIND` — intentionally vague EARS. "The system shall handle errors gracefully." A-runs diverge wildly on error types and strategies. Recommendation: refine the EARS before re-auditing.

**Edge-case fixtures (4):**

7. No `@spec` annotation. EARS exists; matching code exists; no link. Skill detects the coverage gap, skips cleanly, surfaces in summary.
8. Multiple `@spec` regions (distributed implementation). One EARS annotated on 3 files (API handler, domain service, DB write). Skill bundles all three regions into the B-direction input and does not split across them.
9. Cross-spec cluster (decomposition drift). EARS is one of 5 siblings (CTX-001..005). Code implements the full cluster. B-runs reconstruct 5+ EARS; classification is `BIDIRECTIONAL-DRIFT` with a decomposition-gap subcategory. Models KWP-CTX-001.
10. Negative requirement — structurally unannotatable. EARS: "shall NOT mutate the input collection." No production sink to annotate. Skill emits `UNANNOTATABLE` with a recommendation path (companion unwanted-behavior EARS + test, or defer to a sibling absence-audit experiment).

**Stress extras** (second eval iteration, not baseline):

- Recently-edited EARS vs. its `@spec` code (git-provenance adjacency).
- EARS whose code sink is in a test file but not in production (test-witness adjacency).
- Very large code region (>1000 lines) against a single EARS (B-direction prompt-size stress).
- EARS with identifiers that collide with common vocabulary (`error`, `continue`) — stripping-rule stress.

## EARS coverage

Feature prefix: `BIDIFF`. EARS drafted at Phase 3 after LLD acceptance. Expected coverage shape:

- **Precondition / scoping** — arrow-maintenance dependency check; scoping-conversation contract (interpret descriptions, present EARS inventory, capture explicit scope, confirm before spawning).
- **Core behavior** — EARS/code resolution; stripping rules; context-free session spawning; parallel execution; comparison and classification.
- **Output** — classification codes; audit-record path and structure; user summary; git SHA capture; arrow-cascade reconciliation guidance.
- **Ambient** — Phase 6 batched hook; disable flag; config keys.
- **Unwanted behavior** — missing `@spec` handling; `INCONSISTENT-BLIND` variance threshold; missing-overlay abort; `UNANNOTATABLE` handling for negative requirements; stripping-failure spot-check.

Expected rough count: ~15–22 EARS.

## Lifecycle

Promotion, retirement, and community feedback are governed by the parent LLD (§"Lifecycle", §"Community Feedback"). Experiment-specific notes:

- **Primary promotion target**: `linked-intent-dev`. The audit's natural home is Phase 6 integration and the resumption-coherence pre-flight.
- **Secondary promotion target**: `arrow-maintenance`. If audit-report-maintenance code dominates the implementation, promoting there may be a better fit. Decide on real-usage data.
- **Value stories to watch for** (promotion signal): audit caught a real bug the user would have shipped; scoping conversation reliably produces a confirmed scope the user acts on; concrete cost/benefit sweet spot reported.
- **Structural-failure retirement trigger**: chronically low-signal classification (wrong too often), or irreducible non-determinism at N=5.

## Decisions & Alternatives

| Decision | Chosen | Alternatives Considered | Rationale |
|---|---|---|---|
| Name | `bidirectional-differential` | `ears-code-differential`, `blind-audit` | Names the mechanism clearly — two directions (EARS→code and code→EARS), a differential between them. |
| Variant | Dual-mode (command + ambient) | Pure-prose; command-only; ambient-only | Command mode supports exploratory and forensic use; ambient mode integrates with LID's phase cadence. Scoping conversation applies to both. |
| Arrow-maintenance dependency | Hard abort on missing overlay | Soft warn + bootstrap in-skill; independent overlay | Audit reports live under `docs/arrows/`; bootstrapping that surface in-skill duplicates arrow-maintenance's job and lets projects adopt the heavy layer before the light one. |
| Audit-record location | `docs/arrows/experiments/bidirectional-differential/<segment>/<EARS-ID>.md` | Augment existing arrow overlay files; parallel `docs/audits/` tree; inside-skill DB | Reserved sibling subtree keeps arrow-maintenance hands-off, makes retirement `rm -rf`, makes promotion a single move, preserves segment locality. |
| Ambient trigger phase | Phase 6 (code complete) | Phase 3 (post-EARS draft); Phase 5 (tests first) | The audit's strongest claim requires both EARS and code in final shape. Earlier phases audit incomplete arrows. |
| Ambient prompt shape | One batched prompt per change | One prompt per touched EARS | Habituation: per-EARS prompting trains users to reflex-skip. Batched prompt respects attention budget. |
| Runs per direction (default) | N=3, split-rule re-run to N=5 | N=1; N=5 always; N=2 | Cost-vs-confidence: N=3 catches most non-determinism cheaply; the 2-vs-1 re-run rule handles borderline cases without paying N=5 every time. |
| Scope selection in conversation | User describes abstractly ("the login flow"); skill interprets to arrows and confirms; user picks EARS explicitly | Skill auto-selects by shape-based priors; skill asks for arrow names directly | Abstract descriptions are how users actually think about their code. The skill has no reliable project-agnostic heuristic for picking EARS targets, so auto-selection would at best match a specific project and at worst mislead; an explicit user selection via a well-built inventory prompt is more honest. |
| EARS drafted in this LLD | No; deferred to Phase 3 | Draft alongside the LLD | Front-running EARS inverts LID's phase workflow and pre-freezes decisions the Phase 4 edge audit is meant to shape. |
| Classification code set | 5 coherence codes + `UNANNOTATABLE` signpost | 3-code set (pass/fail/unclear); 8-code finer-grained set | 5 codes map cleanly to distinct reconciliation actions; finer grain would require more discrimination than the differential technique reliably produces. `UNANNOTATABLE` is a separate signpost because negative requirements are out-of-technique, not a classification outcome. |
| Tool dependency | `claude -p` only (Claude Code) | Tool-agnostic shell abstraction from day one | The shell abstraction is design overhead for unproven value. Port if the skill earns promotion. |
| Plugin packaging | Separate plugin `lid-experimental` | Bundled into `linked-intent-dev` | Opt-in installation is the parent LLD's contract for experimental skills. |

## Open Questions & Future Decisions

### Resolved

1. ✅ Name, dependency stance, variant, ambient phase, overlay path, eval-suite size — see Decisions & Alternatives.
2. ✅ Whether to draft EARS in this LLD — no, deferred to Phase 3.
3. ✅ Overlay integration shape — reserved sibling subtree, not augmentation of existing overlays.
4. ✅ Scope auto-selection — dropped. The user picks EARS explicitly via the inventory the scoping conversation presents.

### Deferred

1. **Stripping rules as project config.** Built-in list plus judgement today. Projects with domain-specific leaky vocabulary may need a `bidiff-stripping.yaml` override. Placeholder lives alongside arrow-maintenance overlay if needed.
3. **Cross-arrow classifications rollup.** A view that surfaces global coherence posture across all arrows. Out of scope for the experiment; add if adoption warrants.
4. **Caching layer.** Re-running without input changes repeats the cost. Hash-based result cache per (EARS-hash, code-hash, N) is an obvious optimization if users re-audit frequently.
5. **Sibling `blind-overlay-audit` experiment.** The B8 blind re-authoring technique (entire overlay reconstruction rather than per-EARS) is a related but distinct experiment; proposed after this one gains traction.
6. **Tool-agnostic subprocess abstraction.** Needed if the skill is ever ported to Cursor / Aider / Continue. Design deferred until promotion.

## References

- Parent LLD: `docs/llds/lid-experimental.md`
- Arrow-maintenance LLD: `docs/llds/arrow-maintenance.md` §"Experiment-produced artifacts (reserved namespace)"
- LID LLD template: `plugins/linked-intent-dev/skills/linked-intent-dev/references/lld-templates.md`
- Research provenance: `docs/research/formal-verification-exploration.md` §11.4, §11.5, Appendix I; underlying experiments at `docs/research/experiments/{b1,b2,b8-blind-reauthoring,b9-bidirectional-differential-keepers}/`
