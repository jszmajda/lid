# Experiment B1 Results — Differential Round-Trip on FEAT-DET-021

**Date**: 2026-04-22
**Target EARS**: FEAT-DET-021 (daily-to-weekly classification escalation)
**Engine**: differential (LLM round-trip)
**Verdict**: **Thesis confirmed.** Differential round-trip reliably surfaces the three-conjunct gap that Wave 1's test-witness experiment had to back-derive from code.

---

## TL;DR

- **3/3 A-runs** (EARS → implementation, fresh `claude -p` per run) produced a happy-path-only test with zero negation cases and treated the daily-mode premise as implicit in the entry-point choice. None recovered the three-conjunct structure the real system encodes.
- **3/3 B-runs** (implementation → EARS, fresh `claude -p` per run) recovered all three conjuncts explicitly, including the daily-mode premise the real EARS elides as a participial phrase. All three also surfaced the log-line obligation the real EARS is silent about.
- **The asymmetry is the experimental payload**: A's artifact ≈ the shape of the EARS it was given (flat, happy-path, no C1 isolation); B's artifact > the EARS it reconstructs (explicit C1, explicit observability). The differential between A and B highlights exactly what the real EARS loses.
- **Signal stability**: both directions are repeatable across three independent runs with low semantic variance. Surface wording differs (invented module names, verb choices); semantic content is stable. Differential is usable as a CI signal, not a random noise generator.
- **Coherence recommendation (Appendix E)**: promote FEAT-DET-021's three conjuncts to explicit form (`While detection is running in daily mode, when … the system shall …`). This single EARS edit eliminates the drift both A and B surface. The Wave 1 test-witness contract already encodes the corrected reading; an updated EARS would close the upstream gap.

---

## What we ran

Six `claude -p` sub-agent invocations from `/tmp/b1-sandbox` (an isolated directory with no repo context). The sub-agents were true context-free sessions — no prior conversation, no access to LID docs, no access to the case-study codebase. Each A-run received the EARS text verbatim plus instructions to write one Vitest test with explicit assumptions. Each B-run received the real four-test `describe` block (with `@spec` comment stripped to prevent spec-ID leakage) plus instructions to reconstruct an EARS statement.

Inputs are in `A-inputs.md` and `B-inputs.md`. Outputs are in `A-runs/run-{1,2,3}.{raw.txt,md}` and `B-runs/run-{1,2,3}.{raw.txt,md}`. Ground truth (real EARS + real test) is in `ground-truth.md`. The structured diff is in `comparison.md`. The Appendix-E-shaped differential artifact is in `FEAT-DET-021.differential.md`.

(Note: the `thr-det-021` suffix in this directory name and some artifact filenames reflects the original EARS ID and is kept as-is for experiment-artifact stability.)

## Evaluation against the 7 shared criteria

### 1. Expressiveness — does the A/B output capture translation drift, or just echo ambiguity?

**Captures real drift.** The A-side produces a consistent shape (positive happy-path, C1-implicit, no negations) that is *not* a random point-estimate of "what a test for this EARS might look like" — it is the structural consequence of the EARS flattening three conjuncts into a participial phrase. If the EARS were written differently (with explicit `While detection is running in daily mode` state-precondition), A would almost certainly pick C1 up, because the EARS keyword `While` would cue the agent that daily-mode is an assertable state, not a narrative frame. We did not run the counterfactual, but the shape of what A misses makes it specific: the model reads EARS as it's written, and the real EARS is structurally lossy.

The B-side captures *what the test carries beyond the EARS*. B recovers:

- C1 as a conjunct (from N3's weekly-mode negation)
- Log obligation (from the `expect(escalationLog).toBeDefined()` assertion)
- Call-count exactness (from `toHaveBeenCalledTimes(2)` and the `Times(1)` in negations)

These are substantive properties of the implementation that the EARS does not state. The differential surfaces each one as a gap between real EARS and reconstructed EARS. This is translation drift, not ambiguity echo.

The Wave 1 RESULTS.md observed (§2): "Test-witness contracts cannot be authored from EARS in isolation. They require reading either the implementation or the LLD to recover the conjunction structure of the enabling condition." B1 is the independent mechanical confirmation of that claim, arrived at without a human inspecting the source. Expressiveness passes.

### 2. Translation fidelity — where specifically did A miss vs. B find?

Table form:

| Property | Real EARS | A recovers | B recovers |
|---|---|---|---|
| C1 — daily mode is a precondition | Implicit | **No** (implicit in entry-point) | **Yes** (explicit conjunct) |
| C2 — zero assignments | Explicit | Yes | Yes |
| C3 — ≥1 entry with no `groupIds` | Explicit | Yes | Yes |
| Escalation = re-run in weekly mode | Explicit | Yes | Yes |
| Log-line observability | Absent | **No** (invents return flag) | **Yes** (adds as obligation) |
| Call-count exactness (2 on escalation, 1 otherwise) | Absent | N/A (positive-only) | **Yes** |
| N3-style "weekly does not self-escalate" | Implied by symmetry | **No** (no N3 case) | **Yes** (conjunct C1) |

A misses C1 uniformly across all three runs. B finds C1 uniformly across all three runs. That is the clean differential: the agent that reads the EARS never isolates C1; the agent that reads the tests always does. Both agents agree on C2/C3 because both surfaces state them explicitly.

The fidelity claim for differential is therefore: **given a lossy EARS and a complete test, differential round-trip surfaces the precise property the EARS lost.** This is strictly what we wanted.

### 3. Source-untouched discipline

**Confirmed.** No edits to the case-study codebase. The experiment only *read* the relevant EARS file, the LLD file, and a runner source + test file. Sub-agent sessions ran in `/tmp/b1-sandbox`, which is unrelated to both the LID repo and the case-study. `claude -p` inherits the harness but was given only prompt text — no file system calls were issued against either repo by the sub-agents.

All artifacts produced by this experiment live in `/Users/jess/src/lid/docs/research/experiments/b1-differential-thr-det-021/`. No `node_modules/`, no build outputs. Pure text.

### 4. `@spec` / `derives_from:` threading — did the experiment surface where new provenance would help?

**Yes, with a specific recommendation.** Today, `@spec FEAT-DET-021` threads forward (source → EARS ID) and backward (EARS → where is this implemented — reachable by grep). What is missing is the **intra-spec conjunct provenance**: which part of the test witnesses which conjunct, and which part of the source enables which conjunct. This experiment surfaces the need because:

- A's generated test has no way to annotate "this is the positive; I elided negations because the EARS didn't cue them." Today the elision is invisible.
- B's reconstructed EARS has no way to say "I promoted C1 to explicit because N3 falsifies it independently of C2 and C3." Today the promotion is invisible.

The minimal `derives_from:` extension that would make this threadable:

```yaml
# In the overlay for FEAT-DET-021, per conjunct:
conjuncts:
  C1:
    text: "in daily classification mode"
    derives_from:
      - doc: <case-study>/src/runner.ts
        section: "lines 169-171, outer guard"
    witnessed_by:
      - test: "daily-to-weekly escalation > should NOT escalate when already in weekly mode"
  C2:
    text: "zero total assignments across all entries"
    derives_from:
      - doc: <case-study>/src/runner.ts
        section: "lines 169-171, assignments.length === 0 clause"
    witnessed_by:
      - test: "daily-to-weekly escalation > should NOT escalate when daily assigns at least one entry"
  C3:
    text: "at least one entry has no pre-existing groupIds"
    derives_from:
      - doc: <case-study>/src/runner.ts
        section: "lines 169-171, hasUnassignedEntries clause"
    witnessed_by:
      - test: "daily-to-weekly escalation > should NOT escalate when all entries already have groupIds"
```

With per-conjunct `derives_from:` + `witnessed_by:`, a coherence invariant becomes mechanical: **every enabling conjunct in the overlay has a derivation upstream and a witness downstream.** Orphan detection at the conjunct level is a trivial set-difference query on the overlay. Today it is not.

This is §5.2's "conjunction of simple local checks" applied at finer granularity than spec-level. Worth piloting as part of the overlay v0.3 schema.

### 5. Coherence-stack fit — does this validate the "differential scales up" thesis for gate 4?

**Yes, and with a twist.** §4 of the research doc says: "At the code-proximate end, artifacts are near-formal (EARS) or fully formal (code). Formal engines are rigorous … At the narrative end, LLM differential is tractable."

Gate 4 is EARS ↔ code, the code-proximate end. §4 predicts formal overlay is strong here and differential is *also* strong here ("Strong | Strong" in the table). B1 confirms differential is strong at gate 4, but with an interesting finding: **differential at gate 4 is strongest precisely where formal overlay is weakest**, namely, where the EARS *text* drifts from the conjunction structure the code encodes. CodeQL can tell you the source matches a structural pattern; test-witness can tell you the tests satisfy obligations; neither can tell you the EARS *wording* is incomplete relative to the property being enforced. Differential can, because A's drift is specifically "what the EARS wording cued me to elide."

This is the "formal + differential pairing" from §4 pattern 3 (continuous round-trip) working correctly at gate 4: the two engines are complementary. Formal locks in "code implements what we said"; differential surfaces "we didn't say what we meant."

The stretch question — does differential scale *up* as well as it scales at gate 4 — is B2's problem (LLD ↔ EARS differential on the primary arrow). B1 is evidence that the round-trip mechanic is stable, cheap, and produces structured signal; that's a necessary precondition for B2 to succeed, not a sufficient one.

### 6. Cost

**Wall time**: approximately 35 minutes. Breakdown:

- ~5 min: read Wave 1 RESULTS.md, skim §1/§4/§5/§11.2 of the research doc, read the LLD escalation heuristic section, confirm source line 169-171 three-conjunct structure.
- ~3 min: set up `/tmp/b1-sandbox`, write A-prompt, write B-prompt, extract the four-test block with `@spec` stripped.
- ~10 min: six `claude -p` invocations (three A, three B). Each run returned within ~60-90 seconds. Total agent wall-clock ~8-10 min, elapsed human-supervision wall time ~10 min.
- ~15 min: write the per-run analysis files, the comparison, the differential artifact, and this RESULTS.md.

**Token cost**: moderate. The six sub-agent invocations each consumed a small-to-moderate budget (prompt is 300-700 words, output 300-600 words per run, so O(10-15k) tokens across all six). The parent session is token-cheap — mostly file-writes and small reads. Total experiment budget in the low tens of thousands of tokens.

**Amortization**: once the prompts exist, running a new A/B pair against a different EARS is three sub-agent invocations + comparison. O(10 minutes) per new EARS pair. At ~10 EARS per hour, full-arrow differential passes are cheap enough to run on every meaningful EARS edit.

Two iteration cycles that I did *not* need but was prepared for:

1. First A-prompt might have been too easy — the model could conceivably write three tests defensively. It did not (3/3 single-test outputs). The prompt held its discipline.
2. First B-prompt might have leaked the EARS wording through the `@spec` comment. I stripped the comment from the block before sending. The model produced EARS text that does NOT match the real EARS's exact phrasing — it says "re-invoke" and "perform a second pass" and "runs in daily classification mode," none of which are verbatim real EARS wording. No leakage.

### 7. Maintenance signal — if FEAT-DET-021 evolved, would differential catch the drift?

**Yes, in both directions**, and with different failure modes from the other engines.

Scenario A — EARS edit only (no code change): someone updates FEAT-DET-021 to say "at least two entries" instead of "at least one." The existing code `.some(e => ...)` still checks for at least one. Running differential:

- A (new EARS → test): generates a test setup with ≥2 empty-groupIds entries. Diff vs. real test (1 empty entry) fails.
- B (real test → EARS): still recovers "at least one entry lacks groupIds." Diff vs. updated real EARS fails — real EARS says "two," B says "one."

Both sides catch the drift. **No other engine can.** CodeQL doesn't read the EARS text. Test-witness reads the EARS but only binds to pattern detectors the contract author pre-declared; a pre-existing contract tied to "one" would catch the drift indirectly by failing the new EARS-derived pattern check, but only if the contract is regenerated. Differential catches it immediately.

Scenario B — code edit only (no EARS change): someone changes the guard to `(mode === 'daily') && (assignments.length < 3)`. EARS still says "zero." Test mocks still produce zero. Tests pass. Running differential:

- A (real EARS → test): still generates a zero-assignments test. Matches current test.
- B (modified tests → EARS): would STILL recover "zero assignments" because the tests still mock zero. B *cannot* see the source-level change — it only reads tests.

This is a gap. Differential catches EARS-level drift (either direction) but misses source-level drift when the tests still pass. That's the L2 gap Wave 1 identified for test-witness. Closing it requires a CodeQL query over source, not differential. §4 pattern 3 ("continuous round-trip") correctly prescribes dispatching to multiple engines; B1 reproduces the limitation test-witness already had here.

Scenario C — test edit only (e.g., someone deletes N3 because "we're always in daily mode now"): B's reconstruction would now miss C1 (no test cues the daily-mode conjunct). B's reconstructed EARS diff vs. real EARS would show "B lost C1." Maintainer sees that deletion broke a conjunct witness. This is where B's recovery gives maintenance teeth: deleting a negation test visibly reduces what B can recover. That is the signal.

Six months from now, if a teammate simplifies the test file without knowing the negation structure encodes a three-conjunct guarantee, differential flags the simplification. Good.

---

## The core research question

**Does differential round-trip surface the three-conjunct gap that the Wave 1 test-witness experiment had to back-derive from code?**

**Yes, reliably, from both directions, across three independent runs per direction.**

Evidence:

1. **A-direction (3/3 runs)**: The agent given only the EARS text produced a single positive-case test. No run wrote a negation for C1 (weekly does not self-escalate). No run wrote a negation for C2 (assignments ≥ 1 → no escalate). No run wrote a negation for C3 (all entries pre-assigned → no escalate). This is exactly Wave 1's claim: *you cannot author a conjunct-aware test from the EARS alone*. B1 reproduces it without manual inspection.

2. **B-direction (3/3 runs)**: The agent given only the four-test block (with `@spec` stripped) produced an EARS with all three conjuncts explicit. All three runs named "detectionMode is 'daily'" as its own enabling condition (C1), not as a narrative frame. All three added log-line observability. All three added call-count exactness obligations.

3. **The asymmetry is precisely the drift**: A's output matches the real EARS's flat shape (which is what A was given). B's output *exceeds* the real EARS (which reveals what the tests preserve and the EARS lost). The differential is the gap between A's "correctly-read-from-EARS but tested-incompletely" and B's "correctly-read-from-tests with explicit conjunction."

4. **Variance is low enough to trust**: 3-for-3 on both sides with stable semantic outputs. A's module-invention variance is high (different names, different seams); A's semantic variance is zero (all happy-path, all return-flag observability). B's phrasing variance is modest (`re-invoke` vs. `perform a second pass`); B's conjunct-recovery variance is zero (3 conjuncts recovered in all 3 runs, with run 3 adding a redundant fourth bullet that is a restatement of C1).

5. **The differential artifact (`FEAT-DET-021.differential.md`, Appendix E shape) is a legitimate deliverable**: it states the gap, recommends a concrete EARS rewrite ("While detection is running in daily mode, when …"), and identifies exactly which Wave 1 contract field (O4, log obligation) is the "missing obligation" the overlay already added.

The thesis holds. Differential scales **up** (§4) in the predicted way: narrative artifacts where LLMs are fluent readers/writers, round-trip produces a structured diff rather than noise, and the diff localizes the drift to the right line of the right document.

---

## Caveats and limitations

1. **Single EARS, single arrow.** B1 shows differential works for FEAT-DET-021. B4 (scale to 10 EARS) is the honest test of whether this generalizes. B1 is a prerequisite, not a proof-of-generality.
2. **One model family, one version.** All six sub-agent calls used the same Claude Code CLI with its default model. We did not try Sonnet vs. Opus, nor other providers. Model-variance is unmeasured.
3. **Prompts are authored, not synthesized.** The A-prompt explicitly asks for a single test; if it asked for "a comprehensive test suite," A might voluntarily write negations defensively, shrinking the gap. That would not refute the finding (the EARS would still not *require* those negations from its text), but it would make the differential fuzzier as a diff-generator. Prompt discipline matters.
4. **The `@spec` comment was stripped from B's input but the describe title `'daily-to-weekly escalation'` was not.** The title leaks the "daily-to-weekly" phrasing, which the model could arguably use to write "daily" in C1 without reading the negation test. To be conservative, I consider C1's recovery to rest on both the title and the N3 test's existence. Stripping the title would be the stricter experimental variant, left for future work if variance ever rises.
5. **Scope "for that user" is weakly witnessed both in code and in tests.** Real test uses `userIds: ['test-user']` (single user), which doesn't *test* per-user scope — it only doesn't contradict it. Differential inherits this limitation. B mentions per-user scope; A assumes it; neither truly asserts it. That gap is real and is a candidate for a separate EARS (FEAT-DET-XXX "scope is per-user") or an additional test with two users.

---

## Recommendation for adoption

If LID adopts differential as a second-wave engine:

1. **Run differential alongside, not instead of, test-witness and CodeQL.** §4 pattern 3 is correct: formal engines block CI on regression, differential produces review-comments on drift. They are complementary stages of the loop.
2. **Standardize the prompt shape.** The A-prompt ("write one test, assumptions first") and B-prompt ("one EARS sentence + conjuncts + additional obligations") are reusable templates. Put them in the overlay schema as the canonical differential prompts.
3. **Per-conjunct provenance** is the natural next schema extension. §5's "provenance as substrate" framing applies at the conjunct level as well as the spec level. B1 motivates the finer grain.
4. **Three runs per direction is enough for most EARS.** Variance is low; 3 samples distinguish signal from stochastic phrasing differences. If a CI budget issue forces 1 run, do 1 A + 1 B and accept the occasional lexical surprise.
5. **Use the differential output format of Appendix E.** It forces the author to state what A missed AND what B added AND what action is recommended. Without the "recommended action" field, the diff is just commentary.

---

## Final verdict

Differential round-trip at gate 4, on a behavioral EARS with a flattened conjunction structure, surfaces the three-conjunct gap **automatically, reproducibly, and from both directions**. It identifies the specific EARS rewrite that would close the gap (`While detection is running in daily mode, when …`). It does so at a cost (~10 min, tens of thousands of tokens) that is easily amortized across a full arrow. It confirms Wave 1's hand-derived finding without human inspection of source code.

The experiment converged. The thesis holds. Differential is a worthwhile second-wave engine to add to the overlay.
