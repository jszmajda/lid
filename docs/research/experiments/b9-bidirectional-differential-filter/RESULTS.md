# B9 RESULTS — Bidirectional Differential on Filter-Arrow EARS

**Date**: 2026-04-23
**Scope**: 6 EARS from the case-study codebase's filter arrow specs, across 3 complexity tiers, each audited with bidirectional differential (A direction: EARS → code; B direction: code → EARS; 3 runs each direction).
**Agents**: 3 parallel sub-agents (simple, moderate, complex), 36 `claude -p` sub-calls total.
**Hypothesis tested**: bidirectional differential as a standard audit unit surfaces intent drift where single-direction audits miss it.

## Background (context for first-time readers)

This experiment lives inside a larger research program exploring a **formal verification overlay for Linked-Intent Development (LID)** — a methodology where EARS requirements (`{FEATURE}-{TYPE}-{NNN}` IDed, with four canonical patterns — ubiquitous, event-driven, state-driven, unwanted) are kept coherent with implementation via an arrow chain `HLD → LLDs → EARS → Tests → Code`. The full research doc is at `/Users/jess/src/lid/docs/research/formal-verification-exploration.md`.

**Bidirectional differential** as tested here is a coherence-audit pattern:
- **A direction**: an agent given ONLY the EARS text produces naive implementation code. Compare to the real code. Differences surface EARS under-specification or code's implementation-specific details.
- **B direction**: an agent given ONLY the real code produces a reconstructed EARS. Compare to the real EARS. Differences surface properties the code enforces that the EARS doesn't say.
- **Signal**: the *relationship* between the two diffs, not either diff alone.

Classification codes used below:
- **BD-COHERENT** — neither A-diff nor B-diff surfaces anything material; EARS and code are mutually coherent for this property.
- **A-ONLY-DRIFT** — A-diff surfaces drift; B-diff doesn't. EARS under-specifies an implementation detail that doesn't really need spec coverage.
- **B-ONLY-DRIFT** — B-diff surfaces drift; A-diff doesn't. Code has unstated constraints the EARS should pin.
- **BIDIRECTIONAL-DRIFT** (BD-DRIFT) — both directions surface the same/related gap. Strong drift evidence.
- **INCONSISTENT-BLIND** — runs within a direction disagree too much to classify.

**Engine classes** referenced below (from the overlay architecture's §3 table): structural-dataflow query (e.g. CodeQL), test-witness (test file + contract), SMT-backed contract prover (e.g. LemmaScript → Dafny), differential (this engine), git-provenance, manual-review. Status markers `[V] / [Vp] / [Vx] / [Vn] / [?]` compose with EARS markers `[x] / [ ] / [D]`.

Earlier experiments in the program (`docs/research/experiments/b1-*` through `b8-*`) tested single-direction differentials and code-aware-authoring audits. B9 is the first to run A and B *together* as a standard audit unit across fresh territory (the filter arrow, not previously exercised in earlier waves).

## Overall verdict

**5 of 6 EARS classify as BIDIRECTIONAL-DRIFT. 1 classifies as BD-COHERENT.**

| Tier | EARS | Classification | One-line finding |
|---|---|---|---|
| Simple | FLT-UE-003 (cap at 20) | BD-DRIFT | EARS doesn't say which 20 survive; code keeps oldest-by-`createdAt`. A-runs diverge (2× input-order, 1× newest). B-runs elevate "oldest first" + flag possible latent bug. |
| Simple | FLT-UE-004 (prefer `normalizedText`) | BD-DRIFT | EARS silent on empty string and both-missing. Code uses `\|\|` (empty falls through) + drops item if both missing. A-runs diverge on operator; none drop. B-runs split the rule into two EARS. |
| Moderate | FLT-SCORE-003 (descending sort) | BD-DRIFT | Tie-handling silent in this EARS (FLT-WAVE-002 covers it separately, but no cross-ref). A-runs all produce stable sort; B-runs correctly split into descending-sort + tie-randomization + elevate non-mutation and a flagged-possible-bug transitive chaining. |
| Moderate | FLT-CTX-001 (questions-only visibility) | BD-DRIFT | EARS says what's excluded; code and sibling EARS (CTX-002..005) add agent-name attribution, XML wrapping, dedup instruction. A-runs produce filter-only interpretations missing all of those. B-runs cleanly reconstruct the full CTX-001..005 cluster. |
| Complex | FLT-UE-001 (four-conjunct incorporated + fallback) | BD-DRIFT | Central rule reconstructs cleanly both directions. The *operational halo* around it (error handling, pagination, configuration short-circuit, missing-processedAt default) is uniformly missing from A-runs and uniformly elevated by B-runs. |
| Complex | FLT-SCORE-001 (four-case scoring matrix) | **BD-COHERENT** | Exhaustive 2×2 enumeration with bounded integer output. A-runs produce essentially the real function; B-runs reconstruct the matrix. One B-run offered an equivalent additive decomposition as a preference, correctly flagged as not drift. |

## Key findings

### 1. "Simple" does not mean "coherent"

Both simple-tier EARS produced BD-DRIFT. The stronger prior — that single-claim, unambiguous EARS should trivially converge — is refuted by this sample. Simplicity concentrates drift into a single unspecified sub-decision (which 20? what about empty string?) rather than eliminating it. The drift amplitude is smaller in absolute terms but surfaces reliably in B-direction round-trips.

### 2. Moderate tier shows "spec-decomposition gap" as a characteristic failure mode

Where simple-tier drift is about a single missing sub-clause, moderate-tier drift is about **uncoordinated decomposition across sibling EARS**. Real spec authors correctly factor one implementation across multiple atomic EARS (e.g., CTX-001..005 together cover what a blind reader needs), but individual EARS don't cross-reference each other. A blind A-reader sees only one EARS at a time and under-implements. A blind B-reader sees the full code and reconstructs the full cluster.

Fix is **cross-reference addition**, not within-EARS rewording.

### 3. Complex tier bifurcates by output-domain boundedness

Complex EARS split into two modes:
- **Exhaustive-enumeration with bounded output** (FLT-SCORE-001: 2×2 → {0,1,2,3}): **BD-COHERENT**. The output domain's finiteness forces explicit enumeration; there's nowhere for code to quietly add constraints and nowhere for EARS to leave gaps.
- **Unbounded-output filter/loader** (FLT-UE-001: filters a list): BD-DRIFT via "operational halo" — the central rule is complete but the surrounding error/config/boundary surface is entirely silent in EARS while the code has real defaults and fallbacks.

This is a specific, actionable pattern: **for bounded-output complex EARS, exhaustive enumeration closes the drift gap. For unbounded-output EARS, add companion unwanted-behavior EARS covering store-unavailable, partial-failure, and degenerate-input paths.**

### 4. B-direction produces stronger signal than A-direction

Across all 6 EARS and 18 runs per direction:

- **B-runs converged tightly** (near-zero semantic variance; within a tier the 3 B-runs always identified the same drift items with only minor phrasing differences)
- **A-runs diverged more**, because missing sub-decisions split along plausible alternatives (stable/unstable sort, input-order vs. timestamp-order, `||` vs. `??`)

The asymmetry is informative: **B is the stronger drift detector; A disambiguates whether the drift is real (A-runs split) or decorative (A-runs all converge on the same missing detail)**. Both are needed, but B does the heavier lifting.

### 5. No INCONSISTENT-BLIND outcomes

In 6 EARS × 6 runs = 36 sub-calls, zero produced variance so high that classification failed. Three runs per direction is adequate for triage; 2 runs per direction would be enough in production (the agents noted this).

### 6. No tool-execution-fidelity failures

Unlike B8 (where blind CodeQL queries failed to compile and blind LemmaScript annotations failed extraction due to tool-API, source-vocabulary, and tool-fragment-subset biases), B9's outputs were plain TypeScript functions and plain-English EARS. Zero execution-fidelity issues. **This suggests bidirectional differential on plain-code artifacts is safer to run as a generalist audit than engine-specific blind re-authoring.** The output doesn't need to be runnable for the signal to be usable.

### 7. Incidental arrow-maintenance gaps surfaced

5 of 6 audited EARS are spec-marked `[ ]` (active gap) despite being fully implemented. The real code for these EARS also lacks `@spec` annotations in most cases. The audit incidentally surfaces arrow-maintenance gaps as a byproduct — a third layer of coherence drift beyond the A/B content-level drift.

## Cross-tier pattern: A-diff and B-diff are non-symmetric

Confirming the bidirectional-differential hypothesis: **the drift between A-diff and B-diff is the signal, not either diff alone.**

- **A-diff alone** tells you "naive implementation differs from real implementation." Cannot distinguish between (i) the EARS is ambiguous, (ii) the code has an unstated constraint, or (iii) the naive agent made an unrelated choice.
- **B-diff alone** tells you "reconstructed EARS differs from real EARS." Cannot distinguish between (i) implementation details that don't belong in EARS, (ii) details that do belong but were forgotten, or (iii) agent hallucination.
- **A-diff AND B-diff together** disambiguate. When both surface the *same* gap, it's a real coherence gap that warrants edit. When only one surfaces, the other side tells you which direction to fix.

This is the canonical bidirectional pattern. B9 validates it on a fresh arrow and a fresh subsystem (the filter arrow), with both blind directions run independently and cross-checked.

## Recommended EARS edits

Concrete, not yet applied. Suitable for carrying to the case-study codebase as a proposal document — analog of an auxiliary recommendations artifact (not published) which consolidated earlier waves' findings:

- **FLT-UE-003**: add "retaining the 20 items with the earliest `createdAt` timestamps when more than 20 are present" AND open a product question on oldest-vs-newest intent
- **FLT-UE-004**: split into FLT-UE-004a (selection with "present and non-empty" qualifier) + FLT-UE-004b (unwanted-behavior: omit item if both fields empty)
- **FLT-SCORE-003**: add explicit "See FLT-WAVE-002 for tie-handling" cross-reference; optionally add "non-mutating: the input collection is not modified"
- **FLT-CTX-001..005**: add explicit cross-references between siblings so a single-EARS reader sees the cluster boundaries
- **FLT-UE-001**: add companion unwanted-behavior EARS for (a) partial-failure/error-mid-load, (b) missing `processedAt` default, (c) unconfigured-store fallback
- **FLT-SCORE-001**: no edits needed — BD-COHERENT. Serves as a canonical "well-formed complex EARS" example.

Plus `@spec` annotation backfills for the 5 unannotated implementations.

## Signal quality summary

| Dimension | Observation |
|---|---|
| Drift-detection rate | 5/6 (83%) BD-DRIFT |
| False-negative risk | Low — BD-COHERENT was correctly assigned where code and EARS genuinely agreed |
| Within-direction variance | B: very low; A: moderate (drift-consistent) |
| Between-direction correlation | When B surfaces a gap, A fails to implement it ~80% of the time in this sample |
| Cost | 36 `claude -p` calls, ~10-15 min wall-clock per tier in parallel |
| Execution fidelity | 100% (plain TS + plain EARS; no tool-subset bias) |

## Implication for the overlay architecture

Earlier draft versions of the research doc had bidirectional differential posture-flagged as "advisory" rather than gate. B9's 5-of-6 BD-DRIFT rate on a fresh arrow — including drift on *simple* EARS where the prior expectation was trivial coherence — is strong evidence for promoting it to a **co-gate** with the formal engines (structural-dataflow query, test-witness, SMT-backed contract prover, type-system-native). Every EARS that reaches the overlay should be audited bidirectionally at least once before its formal artifact is promoted to `[V]`. The pairing is cheap (6 `claude -p` calls per EARS), produces high-signal output, and works on plain code without tool-subset infrastructure.

**Practical promotion rule proposal**: an EARS's formal artifact can be promoted to `[V]` only when its `last_blind_audit` field records a BD-COHERENT or A-ONLY-DRIFT classification. BD-DRIFT requires reconciliation (EARS or code edit) before promotion. B-ONLY-DRIFT is advisory (may warrant EARS addition but doesn't block). INCONSISTENT-BLIND requires re-run with refined prompts.

## Artifacts

All in this experiment's directory (contents other than this file are not published — they embed case-study specifics):

| Path | Count | Purpose |
|---|---|---|
| `implementation-evidence/*.md` | 6 | Real code verbatim with file:line anchors |
| `prompts/a-*.txt` + `prompts/b-*.txt` | 12 | Verbatim prompts fed to `claude -p` |
| `runs/<EARS-ID>/{a,b}-run-{1,2,3}.md` | 36 | Raw blind sub-agent outputs |
| `per-ears-analysis/*.md` | 6 | Per-EARS A-diff + B-diff analysis + classification + recommendation |
| `tier-summaries/{simple,moderate,complex}.md` | 3 | Per-tier cross-EARS synthesis |
| `RESULTS.md` | 1 | This file |

The case-study codebase not modified. No commits.
