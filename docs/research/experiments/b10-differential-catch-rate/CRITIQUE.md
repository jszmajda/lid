# B10 CRITIQUE — External Adversarial Review of Design and Interpretation

**Date**: 2026-08-07
**Method**: B10's claims and interpretation were put through structured adversarial review: eight zero-context reviewer configurations with distinct critical postures (competing-methodology author, empiricist skeptic of delegated verification, evals researcher, staff practitioner, engineering executive, review-craft curator), run across two rounds — six Claude-family reviewers, then two re-run cross-family on GPT-5.6 Sol via this experiment's own harness. Reviewers critiqued a **prose summary of B10's claims** (not the raw RESULTS/answer-key), so some critiques are answered by protocol details the summary omitted; each item below is labeled accordingly.
**Labels**: `OPEN` (genuine gap), `ANSWERED` (RESULTS/answer-key already addresses it — cite it when presenting), `PARTIAL` (partially addressed; residue named).

**Meta-finding worth recording first**: the two cross-family (Sol) reviewers surfaced the single most important critique (A1 below) that all twelve same-family reviews missed across both rounds. This is a live empirical anecdote for the context-independence spectrum: same-family review passes shared a blind spot that one cross-family pass exposed immediately. It should temper how much confidence repeated same-family review buys.

---

## A. Scope-of-claim critiques (what B10 does and does not support)

**A1. `OPEN` — No comparative arm.** B10 has no human-reader baseline, no ordinary-critic (single-prompt reviewer) baseline, no single-direction-audit baseline, and no non-LID spec-structure baseline. It pre-registered a *threshold for audit recall*, not a *comparative decision rule between audit and reading*. Therefore B10 demonstrates that the bidirectional differential recovers seeded trace-coherence gaps; it does **not** support any claim of the form "audited traces can carry what human line-reading carried." The supported form is narrower: *the audit may remove a measurable subset of trace-coherence work from the human reviewer.* (Both Sol reviewers, independently; missed by all same-family reviews.)

**A2. `OPEN` — Trace expressiveness boundary.** Maintainability, comprehensibility, architectural degradation, security posture, and locally-reasonable-choices-that-compound-badly are often not encoded in any spec, test, or citation — they are outside the trace's expressible surface, so no trace-coherence catch rate bears on them. B10's metric must not be allowed to silently redefine "what review is for" as "trace coherence."

**A3. `PARTIAL` — Saturation reading.** The instrument blew past its pre-registered 0.70 threshold (0.96) and the independence gradient flatlined — jointly the signature of an exam the instrument saturated, which is what the synthetic-seeding-inflation literature predicts. The honest framing: B10 is a successful **calibration pilot** — the harness works, the exam needs to get harder. (RESULTS' confounds section discloses the ingredients but does not draw the saturation conclusion; this doc does.)

## B. Design and statistical critiques

**B1. `PARTIAL` — Estimand and unit of analysis.** "23/24" needs its aggregation rule stated wherever it appears: detected-by-any-of-3-runs, majority, or single fixed pass are different estimands with different variances. RESULTS defines detection as key-matched surfacing for the affected EARS but does not surface the aggregation rule prominently; state it alongside every use of the number.

**B2. `OPEN` — Uncertainty.** 23/24 carries a Wilson interval of roughly [0.80, 0.99]. Presentations should say "23 of 24," once, with the interval — not "96%" as a stable property.

**B3. `OPEN` — H-seed construction circularity.** Class-H seeds *by definition* leave spec text intact, which is exactly the condition that makes the A-direction collide with the narrowed B-direction. In the wild, an agent that narrows an implementation frequently narrows or reinterprets the spec too, or the spec was ambiguous from the start. 8/8 therefore means "hollow tests of the constructed-detectable kind are caught," not "the hollow-test failure mode is solved."

**B4. `PARTIAL` — Synthetic-seed inflation.** External result (arXiv 2606.15689, Jun 2026): mutation-injected bugs overestimate AI-reviewer recall ~10× vs. real bugs. B10's mitigations (gap-log-derived taxonomy; intent-layer substrate; disclosed confound) are *arguments, not data*. The natural-gap replication — scoring the differential against gaps recovered from real bug-fix history — is not a follow-up; it is **the** experiment.

**B5. `ANSWERED`→`PARTIAL` — B9 as recall cross-check is invalid.** B9 (5/6 BD-DRIFT on untouched specs) has no ground-truth denominator; it shows *yield/sensitivity on natural drift*, never recall. Any defense of B10's recall citing B9 as corroboration must be retired. The incidental REAL findings on B10's controls (including one production bug) are likewise usefulness evidence, not recall evidence — and dirty controls complicate false-alarm estimation.

**B6. `ANSWERED`/`PARTIAL` — Adjudication and precision forensics.** Questions raised: who saw the key when; match criteria; whether rulings were blind to arm/tier; inter-rater agreement; false-alarm denominators per audit unit per tier. RESULTS answers much of this (key-match protocol, Fable↔Sol agreement 83.6% with a pre-registered trigger, full human pass recorded, per-arm control-finding counts) and discloses partial blinding (realness adjudicators had filesystem access wide enough to diff seed trees). Residue: per-unit false-alarm rates by tier are derivable but not tabulated; inter-rater stats for the human pass don't exist (n=1 human).

**B7. `OPEN` — Detection-under-instruction vs. monitoring.** The audit prompt frames the task as an audit; natural drift arrives unannounced. Whether operating-condition recall matches exam recall is untested.

**B8. `OPEN` — Seeder contamination.** Seeds were authored by a model that knew the instrument existed — i.e., drawn from a distribution plausibly close to the detector's expectation distribution. Gap-log-derived categories mitigate but do not eliminate this; the natural-gap replication eliminates it.

## C. Verifier-independence critiques

**C1. `OPEN` — Correlated verifiers, sharpened.** The flat independence gradient at high recall is *consistent with* seeds living inside the shared-competence region of one model family — the instrument may catch what all these models can see and be structurally blind to what none can, and **no within-family experiment can distinguish those worlds**. Supporting literature: frontier-model errors are increasingly correlated (ICML 2025, "Great Models Think Alike and this Undermines AI Oversight"); same-family judge leniency (ICLR 2026, "Preference Leakage"). A seed set built to separate the tiers, with cross-family seeding as well as cross-family auditing, is the follow-up.

**C2. `PARTIAL` — Family concentration across roles.** Seeder, most auditors, and both AI adjudicators came from a small frontier-model pool. RESULTS discloses the arms; the concentration's effect is what C1 tests.

## D. What the universal miss actually exposes

**D1. `OPEN` — Annotation reach is an open-world problem, not a boundary condition.** The audit guards only the annotated surface; behavior nobody annotated is invisible *by construction*, and syntactic orphan checks cannot find it (they check citations, not coverage). Needed: a **measured reach instrument** — candidate operationalization: fraction of behavior-bearing changed lines within `@spec` reach, per commit — so reach decay is observable before production is.

**D2. `OPEN` — Annotation-incentive hazard (Goodhart).** The agent that writes the code typically places the annotations: annotator and auditee are the same process, and under-annotation is the cheapest way to pass attestation. No evidence yet on whether this pressure operates in practice; it is a named, testable hazard ("a catch rate on a surface the auditee chose").

**D3. `OPEN` — External validity / brownfield.** Single fixture; greenfield; LID-native from first commit; single author. No data on retrofitted arrows, legacy codebases, or multi-author repos. The honest public statement until then: everything measured here is on the author's own arrow-native code.

## E. Consolidated follow-up queue (priority order)

1. **Natural-gap replication** (kills B4/B8; partially addresses A3): score the differential against gaps recovered from real bug-fix history, Macroscope-style, with a sealed key built from the fixes.
2. **Comparative arms** (kills A1): pre-registered head-to-head — expert human line-reading vs. trace-assisted human vs. ordinary LLM critic vs. single-direction audit vs. differential, on the same gap set; report recall, precision, time, and cost per arm; pre-register the decision rule.
3. **Tier-separating seed set** (addresses C1): seeds designed to differ in family-visibility; cross-family seeding and auditing; report the gradient that B10's ceiling hid.
4. **Reach instrument** (D1): implement and validate the coverage metric; then track reach longitudinally on a live repo.
5. **Capture–recapture, patched** (upgrades the residual-risk idea): naïve Lincoln–Petersen is invalid here — correlated captures inflate overlap and *underestimate* the unseen population, the worst failure mode for a residual-risk number; heterogeneous catchability across gap classes violates it further. Use Chao/jackknife-class estimators with cross-family panels; publish overlap matrices before any point estimate.
6. **ID-stripped navigation ablation** (adjacent claim hygiene): same repo, spec IDs stripped from comments, same tasks; measure whether agents find the intent docs — converts the accidental-grep mechanism claim from observation to receipt.
7. **Operating-condition study** (B7): differential run without audit framing on drifted-but-unannounced fixtures.
8. **Annotation-incentive study** (D2): measure annotation coverage of agent-authored changes with and without coverage gating.

## Relation to RESULTS.md

RESULTS' own confounds section already discloses: single codebase, n=8/class, seeder awareness, partial adjudicator blinding, ceiling-limited gradient, incomplete Sol sample. This critique adds the *interpretive* consequences (A1–A3), the statistical hygiene items (B1–B3), the independence sharpening (C1), and the system-level hazards the miss exposes (D1–D3). Nothing here contradicts the recorded data; most of it constrains what the data may be said to mean.
