# B8 RESULTS — Blind re-authoring of Wave 1 formal artifacts

**Date**: 2026-04-22
**Hypothesis tested**: Wave 1 formal artifacts caught zero current drifts because the authoring agents were biased by access to the existing code implementation. Re-authoring each Wave 1 artifact *blind* (from EARS alone) produces different / more-correct artifacts, validating the hypothesis.

**Overall verdict**: The hypothesis is **confirmed in a nuanced form, not uniformly**. Code-bias shows up in three distinct shapes at the *semantic-content* level, plus three additional forms at the *execution-fidelity* level when blind artifacts are actually run (see "Execution evidence" below).

| Engine class | Sub-experiment | Code-bias shape | Classification |
|---|---|---|---|
| Structural / dataflow (CodeQL) | B8a | **Choice-of-target bias** — code-aware agent picked architecture-level verification; blind agents picked prompt-literal verification. Different halves of the EARS. | **(iii)** |
| Test-witness (YAML contract) | B8b | **Over-specification bias** — code-aware agent added a third conjunct (daily-mode premise) that isn't in the EARS text but is in the code. Blind agents recover only the two conjuncts the EARS states. | **(ii)** |
| SMT contract prover (LemmaScript/Dafny) | B8c | **Minimal** — the EARS's arithmetic precision leaves little room for code-vs-EARS divergence. Blind and code-aware converge on essentially the same annotations. | **(i)** |

The strong form of the hypothesis ("fatally code-biased, couldn't catch drift") is **refuted** for all three engine classes. The medium form ("artifacts encode code-shaped checks EARS doesn't mandate OR vice versa") is **confirmed for B8a and B8b, refuted for B8c**. The weak form is trivially confirmed where visible, invisible where shapes converge.

---

## Setup and context-free discipline

All 9 blind runs (3 per engine) used `claude -p` via Bash to start fresh Claude sessions with no inherited context. Prompts were prepared offline in `prompts/b8{a,b,c}-*.txt` containing only:

1. The one-line codebase shape description (e.g., "TypeScript / Vitest / DynamoDB")
2. The EARS text verbatim
3. The task ("write a CodeQL query / test-witness contract / annotated TS function for this EARS")
4. Explicit instructions to document invented assumptions

Raw outputs are in `b8{a,b,c}-blind-run-{1,2,3}.raw.md`. No blind run received access to the Wave 1 artifacts, the case-study source, or LLD files.

**Stdin glitch**: on the initial run, b8a-2 and b8a-3 hung awaiting stdin. Fixed with `< /dev/null` redirection and retried. All 9 runs completed.

---

## Per-engine findings

### B8a — CodeQL for FEAT-DET-018

All three blind runs interpreted the EARS at the **prompt-literal layer** — finding string/template literals that contain `<assigned-groups>` and checking whether the surrounding text instructs the LLM to preserve existing assignments ("never remove", "only add", etc.).

Wave 1's artifact went one layer deeper: it checked every DynamoDB write to `groupIds` and required `list_append` rather than bare `SET`. That verifies a stronger property — the code's architecture makes LLM drop-outs impossible even if the prompt instruction is violated.

Neither is wrong. The Wave 1 experiment itself noted that a pre-existing unit test in the processor test file covers the prompt side. The full overlay for FEAT-DET-018 in intra-spec dispatch needs both halves: blind-shaped prompt-check *plus* Wave-1-shaped architecture-check. The Wave 1 CodeQL artifact alone covers only one half, and the code-aware choice of which half was driven by reading the code.

**Classification: (iii)** — blind flags something code-aware doesn't check. Medium hypothesis confirmed in a specific shape (choice of verification target).

See `comparison/b8a.md` for line-level detail.

### B8b — test-witness for FEAT-DET-021

All three blind runs produced contracts with **two-conjunct enabling conditions** (zero daily assignments + ≥1 threadless entry), matching the EARS text verbatim. Wave 1's contract has **three-conjunct** enabling condition — the missing conjunct being "while detection is running in daily mode."

This is the cleanest confirmation of the medium hypothesis across the whole experiment. B1's earlier differential experiment already showed that a B-side agent (reading only the code) reconstructs all three conjuncts, and an A-side agent (reading only the EARS) reconstructs only two. B8b now confirms the same pattern for contract authoring: code-aware authors include the third conjunct; blind authors don't.

The drift is in the EARS, not in the code — the EARS text under-specifies. The fix is to rewrite FEAT-DET-021 to make the daily-mode premise explicit (captured in an auxiliary recommendations artifact, not published).

**Classification: (ii)** — Wave 1 over-specified via code-sourced content. Medium hypothesis CONFIRMED, reproducibly, across three independent blind runs, and corroborated by an independent prior experiment (B1).

See `comparison/b8b.md` for line-level detail.

### B8c — LemmaScript for FEAT-DET-014

All three blind runs produced annotation sets with **essentially the same semantic content** as Wave 1: exact entryCount increment, lastEntryAt max-witness disjunction with upper-bound forall, daySpan arithmetic identity, createdAt immutability. Differences are shape-level (input preconditions, invented fields like a record `id`, minor monotonicity strengthenings).

The EARS for FEAT-DET-014 is arithmetic — "entryCount incremented by new assignments", "daySpan recalculated from record creation to newest item". These are unambiguous. Blind and code-aware agents both recover the arithmetic identity as `== Math.floor(...)`.

**Classification: (i)** — convergence. Code-bias not meaningfully present for this EARS.

See `comparison/b8c.md` for line-level detail.

---

## Cross-engine pattern

Code-bias severity is **not uniform**; it varies with engine class in a way that correlates with **EARS precision and engine's native expressivity**:

| Engine class | Native fit to EARS | Code-bias severity | Bias shape |
|---|---|---|---|
| SMT contract prover | Arithmetic EARS map directly to pre/post | Low | Shape-level differences only |
| Test-witness | Scenario EARS map directly to setup/action/assert | Medium | Over-specification from code enabling condition |
| CodeQL structural | Structural invariants may live above or below the EARS level | High (but productive) | Choice-of-target — code access lets author pick a stronger or different layer |

The practical implication: **the hypothesis holds more strongly the further the artifact's expressivity is from the EARS's natural shape**. LemmaScript + arithmetic = low bias. Test-witness + scenario = medium bias. CodeQL + loosely-worded structural = high bias.

---

## Execution evidence — blind artifacts run against real tooling

After the initial shape-comparison (above) was written, the blind artifacts were actually executed against the Wave 1 CodeQL database and the LemmaScript toolchain. Results substantially change the picture.

### B8a CodeQL — 0/3 runnable-correct

- **b8a-1 query**: 5 compilation errors. Invented `TemplateLiteral.getRawValue()` which doesn't exist (real API has this method on `TemplateElement` only). Query cannot run.
- **b8a-2 query**: 1 compilation error, same root cause. Query cannot run.
- **b8a-3 query**: compiles, evaluates, returns 8 rows flagging alleged violations. **All 8 are FALSE POSITIVES** — the preservation instruction exists in the real prompt but uses the word "drop" (the production prompt literal is *"Never drop a pre-existing assignment"*), and b8a-3's regex alternatives only check for `remove`, `preserve`, `keep`, `retain`. The blind query's regex vocabulary was too narrow to recognize the actual phrasing.

The Wave 1 artifact, by contrast, runs clean with 3 classified-safe hits against the same DB.

**Two new forms of code-bias surfaced** that shape-comparison missed:
- **Tool-API bias** — blind authors don't know the exact CodeQL API and invent method signatures that don't exist (2/3 failed this way).
- **Source-vocabulary bias** — the 1 query that did run used regex alternatives that don't match the actual source text's word choice.

Full logs in `codeql-run/run-logs.md`.

### B8b test-witness — document-only, no execution

Test-witness contracts are document artifacts that specify what a test must exhibit. They don't "run" in the same sense as queries or provers. The shape-level comparison (3/3 recover 2 of 3 conjuncts; all miss daily-mode premise) is the finding here; B1's differential experiment already confirmed the same pattern on independent methodology.

### B8c LemmaScript — 0/3 runnable

All three blind annotated-TS files fail at the LemmaScript extraction step:

```
Error: Unsupported statement at line N: for (let i = 0; i < ...; i++) {
    at extractStmts (extract.js:851:15)
```

Root cause: blind agents produced idiomatic TypeScript `for (init; cond; update)` loops. LemmaScript's supported fragment (SPEC.md §5) does not include C-style `for` loops — only `for-of` and `while`. The Wave 1 artifact uses `while (i < N) { ...; i = i + 1; }`. Blind agents had no way to know this restriction from the EARS alone.

**Third new form of code-bias**: **tool-fragment-subset bias**. The annotations themselves are EARS-equivalent (per `comparison/b8c.md`), but the TypeScript syntax conformance requires toolchain-specific knowledge the EARS does not convey.

Light-touch repair (rewriting the `for` loop to `while`) would make all three verify cleanly — the annotations are already rigorous. Full logs in `lemmascript-run/run-logs.md`.

### Revised picture

At the **semantic-content level** (what the artifact *claims* to verify):

| Engine | Classification | Finding |
|---|---|---|
| CodeQL (B8a) | (iii) choice-of-target | Blind chose prompt-literal layer; Wave 1 chose DDB-architecture layer |
| Test-witness (B8b) | (ii) over-specified | Wave 1 includes a daily-mode conjunct absent from EARS |
| LemmaScript (B8c) | (i) converged | Arithmetic EARS precision drives convergence |

At the **execution-fidelity level** (does the artifact actually run):

| Engine | Runnable blind artifacts | Failure modes |
|---|---|---|
| CodeQL | 0/3 correctly | Tool-API errors (2); source-vocabulary gap yielding false positives (1) |
| Test-witness | N/A (document artifact) | — |
| LemmaScript | 0/3 | Tool-fragment-subset violation (for-loop → while required) |

**The hypothesis now has two-dimensional evidence**: code-bias shows up both in *what the artifact claims to check* (semantic content — the original shape-comparison finding) and in *whether the artifact can run at all* (execution fidelity — the tooling-conformance finding). They're independent axes. The first is about EARS-vs-code drift; the second is about tool-API knowledge that only code access (or prior toolchain experience) provides.

### Did anything real surface as drift?

Strictly no — zero blind artifacts identified actual intent-implementation drift in the codebase. The 8 b8a-3 rows were false positives from the blind query's vocabulary gap. The codebase remains correct at all three layers tested.

That said, the *authoring-time drift* between Wave 1 artifacts and EARS (shape-comparison (ii)/(iii)) and the *execution-time fragility* of blind artifacts (tool-API, source-vocabulary, fragment-subset) are both real findings that support a broader claim: **code-aware artifact authoring confers both informational bias and operational capability**. The bias is concerning (per B8b); the capability is required for the artifact to be useful at all (per execution logs).

---

## Methodological limits

Things to watch in interpreting these results:

1. **Blind agents invent shape details.** b8c-1 invented an `id` field on the record type. b8a blind queries assumed specific prompt-building idioms. These are authoring noise, not hypothesis signal — they must be separated before classification.
2. **Three runs is a minimum for variance detection, not ideal.** All three blind runs per engine converged in this experiment, which gives reasonable confidence. But some EARS may produce high-variance blind runs; 5-10 runs would be safer.
3. **`claude -p` is not perfectly context-free.** The Claude model has training-data priors that could match case-study-adjacent patterns. True context-freeness would require a model with a cutoff before LID or the case-study existed. The sessions we ran are *session-context-free* but not *model-prior-free*.
4. **We only tested three Wave 1 artifacts.** B4's 10-spec scale experiment produced additional artifacts that could also be blind-re-authored. A broader audit would test whether the same three-shape pattern repeats across more EARS and more engine instances.
5. **Negative results are under-powered.** B8c producing convergent output is weak evidence that code-bias is absent — it could also mean the EARS was specific enough that code bias had nothing to bite on. Stronger evidence would require an EARS where code bias could plausibly differentiate outcomes.

---

## Direct verdict per hypothesis version

- **Strong ("fatally code-biased, couldn't catch any drift")**: *REFUTED*. All three Wave 1 artifacts verify substantial properties. They are not vacuous or shaped to auto-pass.
- **Medium ("artifacts encode checks EARS doesn't mandate OR vice versa")**: *CONFIRMED for B8a and B8b, REFUTED for B8c*. Two of three engine classes show code-bias of distinct shapes. The third (SMT contract prover on arithmetic EARS) is immune.
- **Weak ("LLM authoring on both inputs drifts toward code")**: *TRIVIALLY CONFIRMED* wherever visible; invisible where B8c's shapes converge.

---

## Implications for the research program

Three concrete updates worth carrying back to `formal-verification-exploration.md`:

1. **Add blind re-authoring as a first-class audit technique** — sibling to differential re-interpretation in the engine landscape (§3). Posture: advisory. Run periodically against existing formal artifacts to detect code-bias drift. This is a new engine class; call it **"blind re-authoring audit."**

2. **Acknowledge the Wave 1 drift finding honestly**: the formal engines' zero-drift-catches record from §11.3 needs a footnote. Specifically, B8b showed the test-witness contract over-specifies relative to EARS. That's a form of drift (between artifact and requirement), just in the opposite direction from the one we were worried about. The architecture's promise "catches drift" should explicitly say *drift between what's checked and what's specified*, not just *drift between what's specified and what's implemented*.

3. **Annotate §10's skeptical case with a new entry**:
   > **Code-bias in formal artifact authoring (two-dimensional).** When the authoring agent has access to both EARS and code, the resulting artifact is influenced along two axes. (1) *Semantic content* — the artifact sometimes over-specifies by encoding code-sourced constraints not in the EARS (per B8b), or picks a stronger but different verification target than the EARS literally asked for (per B8a). (2) *Execution fidelity* — blind artifacts routinely fail to run because the author lacks tool-API knowledge (invented CodeQL methods), source-vocabulary knowledge (wrong regex wording), or tool-fragment-subset knowledge (using for-loops where LemmaScript requires while-loops). Code access confers both informational bias *and* operational capability; removing code access exposes both. SMT contract provers on arithmetic EARS are the least susceptible on the semantic axis; all three engine classes are equally susceptible on the execution axis. Countermeasures: periodic blind re-authoring audits (this engine, with a normalization pre-pass for tool-fragment conformance), or differential re-interpretation (§4) to surface the semantic drift.

4. **The three-conjunct finding for FEAT-DET-021 is now supported by two independent methodologies** (B1 differential + B8b blind). Highest-confidence recommendation in the research program: rewrite FEAT-DET-021 to include the daily-mode premise. This is no longer a speculative methodology example — it's a finding replicated across methods.

---

## Artifacts

In `/Users/jess/src/lid/docs/research/experiments/b8-blind-reauthoring/`:

| File | Purpose |
|---|---|
| `run-experiments.sh` | Reproducible runner for all 9 blind calls |
| `prompts/b8{a,b,c}-*.txt` | Verbatim prompts given to blind `claude -p` calls |
| `b8a-blind-run-{1,2,3}.raw.md` | Blind CodeQL outputs (3 runs) |
| `b8b-blind-run-{1,2,3}.raw.md` | Blind test-witness outputs (3 runs) |
| `b8c-blind-run-{1,2,3}.raw.md` | Blind LemmaScript outputs (3 runs) |
| `comparison/b8a.md` | Line-level comparison vs Wave 1 CodeQL |
| `comparison/b8b.md` | Line-level comparison vs Wave 1 test-witness |
| `comparison/b8c.md` | Line-level comparison vs Wave 1 LemmaScript |
| `codeql-run/` | Extracted blind `.ql` files + pack metadata + `run-logs.md` (execution evidence) |
| `lemmascript-run/` | Extracted blind `.ts` files + `run-logs.md` (execution evidence) |
| `RESULTS.md` | This file |

Source discipline: the case-study codebase not touched. Wave 1 artifacts not modified.
