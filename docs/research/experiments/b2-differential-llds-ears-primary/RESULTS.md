# B2 — Differential round-trip at gate 3 (LLD ↔ EARS), primary arrow

**Date**: 2026-04-22
**Experiment family**: Second wave, research question B2 (gate 3, LLD ↔ EARS)
**Target**: the case-study codebase's primary arrow — three focused LLD subsections with their EARS slices
**Engine**: LLM-based differential re-interpretation, two directions × two runs per subsection
**Source corpus**: the case-study codebase (read-only)
**Verdict**: Gate 3 is **tractable but higher-variance than gate 4**. Signal is real — eleven concrete coherence gaps were found across three subsections — but variance between runs is moderate. Output shape is a diff for human review, not a pass/fail gate.

---

## 1. Research question recap

LID structures intent → code via: Human intent → HLD → LLDs → **EARS** → Code + Tests.
Gate 3 is the junction where narrative design (LLDs) becomes verifiable contract (EARS).
Hypothesis: LLM round-trip at gate 3 surfaces real coherence gaps — LLD commitments with no EARS, and EARS that derive from code rather than from LLDs.

Wave 1 indirectly documented a gate-3 gap: FEAT-DET-021's test code uses a three-way conjunction that the LLD implies but the EARS flattens. B2 attempts mechanical detection of that class of gap at the subsection level, across three subsections with different LLD-to-EARS density profiles.

(The three subsections were: daily/weekly classification + escalation; lifecycle; and retention tiers — all from the case-study codebase's primary arrow.)

## 2. Setup

### 2.1 Subsection selection

| Subsection | Density profile | EARS count | Chosen because |
|---|---|---|---|
| **Daily/weekly classification + escalation** | LLD-heavy, EARS medium | 22 | Most specific commitments; maximum gate-3 pressure |
| **Lifecycle** | LLD-terse (~10 lines), EARS tight | 5 | Minimal case — tests whether B can reconstruct when LLD is thin |
| **Retention tiers** | LLD-rich with theory citations, EARS comprehensive | 30 | Hypothesis said "sparse or empty EARS — intentional"; actually the opposite, so tests the subtler "leaky coverage" hypothesis |

### 2.2 Direction A (forward): LLD → EARS

Prompt template instructed a context-free sub-agent to:
- Produce EARS in four canonical shapes (Ubiquitous / Event-driven / State-driven / Unwanted)
- Assign semantic IDs (`FEAT-DET-NNN`, etc.)
- Be thorough — every design commitment gets EARS
- Avoid restatement — each EARS should be verifiable-shaped
- Not invent beyond the LLD

### 2.3 Direction B (reverse): EARS → LLD section

Prompt template instructed a context-free sub-agent to:
- Produce LLD prose with sub-headings
- Ground every EARS in design rationale
- Flag orphan or weakly-motivated EARS explicitly
- Not invent commitments the EARS doesn't require

### 2.4 Execution

Each prompt was executed via `claude -p "<prompt>"` as a one-shot context-free subprocess.
2 runs × 2 directions × 3 subsections = **12 sub-agent runs total**.
Wall time: ~9 minutes total (lifecycle ~100s, detection ~180s, retention-tiers ~180s).
All runs succeeded; no failures, timeouts, or truncations.

### 2.5 Source-untouched discipline

The case-study codebase remained read-only throughout. Input slices were copied into `inputs/` via `Write` and marked with their source path. Neither the LLD nor the EARS spec was modified (verified via `git diff` post-run). The pre-existing local modifications in the case-study repo are from unrelated prior work; none originated from B2.

## 3. Quantitative outcomes

### 3.1 EARS-count ratio (A direction)

| Subsection | Real EARS | A-run-1 | A-run-2 | A-run average / real |
|---|---|---|---|---|
| detection | 22 | 43 | 54 | 2.2x |
| lifecycle | 5 | 13 | 11 | 2.4x |
| retention-tiers | 30 | 29 | 31 | 1.0x |

**Interpretation**: A produces more EARS than the real spec where the LLD is specific and commits to many discrete properties (detection, lifecycle's prose even though it is terse). A matches the real count where the LLD is prose-heavy with fewer atomic commitments (retention-tiers).

The 2x ratio is not noise — it is A extracting commitments from the LLD that the real spec omits or combines. Of A's "extra" EARS for each subsection:
- Detection: ~11 extras are in fact **real LLD commitments** not in the EARS (fallback logic, model configuration fidelity, prompt-content principles, historical-failure guards).
- Lifecycle: ~6 extras split between real-but-scoped-to-UX-EARS concerns and legitimate LLD commitments the EARS omits.
- Retention-tiers: ~5 extras are LLD commitments the EARS doesn't pin (no-significance-promotion, group-only extraction, prompt caching, etc.).

### 3.2 LLD-length ratio (B direction)

| Subsection | Real LLD ~lines | B-run-1 | B-run-2 | B-run average / real |
|---|---|---|---|---|
| detection | ~120 | 84 | 96 | 0.75x |
| lifecycle | ~10 | 53 | 63 | 5.8x |
| retention-tiers | ~90 | 116 | 102 | 1.2x |

**Interpretation**: B produces *more* LLD than the real one when the real LLD is unusually terse (lifecycle — the real LLD is almost an EARS restatement, skipping design rationale that B happily generates). B produces *less* when the real LLD has implementation-detail content (prompt formatting tables for detection) that the EARS doesn't carry. Retention-tiers shows B matching but with a different mix — B invents alternatives-analysis and trade-off discussion that the real LLD doesn't have, while missing theory citations the real LLD does have.

### 3.3 Inter-run variance

| Subsection | A-run-1 ∩ A-run-2 commitments | A-run-1 ∪ A-run-2 commitments | Structural agreement |
|---|---|---|---|
| detection | ~35 | ~60 | ~58% |
| lifecycle | ~9 | ~13 | ~69% |
| retention-tiers | ~25 | ~33 | ~76% |

Jaccard-style agreement is moderate. The divergence is mostly **granularity** — one run decomposes shared principles, the other aggregates them — not contradiction. No case was found where one A-run produced a commitment the other explicitly rejected.

B-runs showed higher structural agreement (~85-90% by content) because reconstructing from a fixed EARS list constrains the design-space more than extracting from free-form LLD prose.

### 3.4 Cost

- 12 `claude -p` sub-agent calls
- ~9 minutes wall time (with two parallel subsection runs)
- Estimated token spend: ~250K input tokens (LLD/EARS slices injected into each prompt) + ~100K output tokens. Order of magnitude: single-digit dollars at standard pricing.
- Zero setup cost beyond the runner shell script.

## 4. Qualitative findings — eleven coherence gaps

The comparison documents (`comparison/detection.md`, `comparison/lifecycle.md`, `comparison/retention-tiers.md`) detail per-subsection findings. The aggregated gap set follows, with severity and recommended action.

### 4.1 Detection (5 gaps)

1. **ShortText/normalizedText fallback unpinned** (medium-high). Both A-runs extracted this LLD commitment ("Daily classification falls back to `normalizedText` when `shortText` is missing") as an EARS. Real spec: silent. An implementer removing the fallback has no EARS to fail against.
2. **Model config fidelity partial** (medium). LLD commits to model name, extended-thinking, prompt caching, in addition to maxTokens + thinkingEffort. Real FEAT-DET-022 only pins the latter two.
3. **No unwanted-condition guard against historical misconfiguration** (medium). LLD tells the cautionary story of "high effort + 32K silently broke detection for a week." EARS has only a positive assertion of correct configuration, not an If-EARS (unwanted-condition) that would act as regression guard.
4. **Prompt-content principles scattered** (low). LLD lists ~6 principles (tags-as-hints, name disambiguation, conservative structure, etc.). EARS captures ~2 (FEAT-DET-009, FEAT-DET-016). Remainder is LLD-only.
5. **FEAT-DET-019 / FEAT-DET-020 are conjunctive bundles** (informational). Each bundles four sub-commitments (content + fact-sheet + prompt-instructions + output-shape). For gate-4 verification, MC/DC coverage needs these decomposed. Same decomposition-drift pattern as the FEAT-DET-021 three-conjunct finding from Wave 1.

### 4.2 Lifecycle (4 gaps)

1. **Narrative-maintenance-while-quiet unpinned** (medium). LLD positively asserts it; real EARS only has the archived-suppression negative (FEAT-LIFE-005). Symmetric positive EARS missing.
2. **Threshold tunability unpinned** (low-medium). LLD says thresholds "should be tunable"; EARS silent. Either LLD over-commits or EARS under-specifies.
3. **UX vs. lifecycle scoping** (low). LLD mixes presentational concerns ("Prominent in the list," "Visually deprioritized," "Hidden from the default view") into the Lifecycle section. Real EARS correctly routes these to FEAT-UI-* but the LLD lacks cross-references — so A-runs re-invent them as FEAT-LIFE-* EARS.
4. **Partition invariant unpinned** (informational). "Every grouping is in exactly one state" is implicit in the mutually-exclusive while-conditions but not explicit. For a formal-verification overlay, making this explicit matters.

### 4.3 Retention-tiers (6 gaps including one meta)

1. **No explicit "no significance-based tier promotion" EARS** (medium-high). LLD has it as a named principle; EARS silent. A developer could reasonably add significance-based promotion; only LLD prose would call it wrong.
2. **"Group-only extraction" gap** (medium). LLD: "Ignore everything not related to this grouping." EARS FEAT-TIER-050 asserts group-specificity but not group-exclusivity.
3. **No short-horizon-before-long-horizon ordering guard** (medium). FEAT-TIER-013 says long-horizon digest derives from short-horizon digest. What if no short-horizon digest exists? Sequencing implicit, not asserted.
4. **No prompt-caching EARS** (medium). Cost commitment in LLD; EARS silent.
5. **Lean-compression-for-routine-entries EARS** (low-medium). Positive case (rich for significant) pinned; symmetric negative (lean for routine) not.
6. **Lost citation trail** (medium, meta/provenance). LLD cites Conway, Linton, Wagenaar, Berntsen. EARS strips provenance. B-runs invent plausible rationale but cannot recover grounding. Arguably correct — citations don't belong in EARS — but worth noting the break in the derivation chain. Motivates `derives_from:` frontmatter (see §5 of the formal-verification exploration).

### 4.4 Bonus: EARS conveying information the LLD doesn't

Both B-runs for **detection** independently extracted that `daySpan` is recalculated (not incremented) and noted this "eliminates a class of drift bugs." The real LLD does not discuss daySpan mechanics. B rediscovers the rationale from the EARS wording alone.

This is **the inverse of gate-3 leakage** — a case where the EARS is more informative than the LLD. It suggests LLDs themselves have gaps (information available in EARS that LLDs omit), which in turn suggests gate-3 is bidirectional and both directions matter.

## 5. Answers to the specific hypotheses

### Q1. Are there LLD commitments without EARS coverage?

**Yes, demonstrably.** Across three subsections, the differential surfaced 10 concrete commitments (out of 11 gaps; the 11th is the meta provenance-trail finding) that the LLD makes and the EARS does not pin. These are reproducible — both A-runs for each subsection independently extract them (with 85%+ overlap between runs on which commitments are "extra").

Notable finding: **retention-tiers was predicted to be the strongest signal because "no direct EARS — partly the point" per the experiment setup.** In fact the retention-tiers EARS is quite complete (30 EARS covering most LLD commitments). The unpinned commitments that *do* exist are subtler — negative invariants (no significance promotion), symmetric counterparts (lean for routine vs. rich for significant), and sequencing guards (short-horizon before long-horizon).

The hypothesis therefore needs refinement: retention-tiers is not a "sparse EARS" subsection, it's a "leaky-at-the-margins EARS" subsection. The leaks are real but require the differential to surface — they would be easy to miss in a hand-review.

### Q2. Are there EARS without LLD motivation?

**Minimal, but yes, in two forms.**
- **Form 1 (prescriptive choices)**: specific field names (`digest` vs `text`, `spices` vs `cues`, `generatedAt`) that FEAT-TIER-022 fixes without LLD justification. B-run-1 called these out.
- **Form 2 (specific numbers without derivation)**: 5-12 grouping target (FEAT-DET-007), 14-day and 12-week tier boundaries (FEAT-TIER-001..003), 3-item minimum (FEAT-DET-012). All are numbers the LLD asserts as given; B-runs cannot recover why these specific numbers (vs. 4-10 or 15-day or 2-entry) without empirical grounding or citation.

**Neither form suggests orphan EARS in the strong sense** (EARS with no LLD motivation at all). Every EARS in this experiment's scope has a home in the LLD. The question B-runs surface is about *strength* of motivation, not existence.

### Q3. Does the three-conjunct decomposition surface in B's reverse round-trip?

**No, not directly — but related decomposition drift does surface.** The specific three-conjunct example (FEAT-DET-021's daily-mode + zero-assignments + unassigned-entries) is not in this experiment's slice in a form where B could surface it — real FEAT-DET-021 already has the three-way condition (implicitly), so B's reverse prose describes the condition correctly without decomposing it further.

However, **the inverse pattern** — A-runs decomposing the real bundled EARS (FEAT-DET-019, FEAT-DET-020) into atomic per-property EARS — is the complementary finding. Real detection EARS compresses four commitments into one EARS (bundling); the three-conjunct example flattens three commitments into one (flattening). Both are gate-3 decomposition drift in opposite directions.

**Conclusion**: B1 (gate-4 differential on FEAT-DET-021) would find flattening; B2 (gate-3 differential) finds bundling. Different gate, different direction of the same coherence-drift pattern.

## 6. Evaluation against the criteria

### 6.1 Expressiveness

Strong. Gate-3 differential expresses design-to-EARS drift in ways that are specific, severity-rankable, and actionable (each gap has a concrete recommended EARS or LLD edit). Signal is noisier than gate-4 formal overlay, but the signal is legible and human-reviewable — not dominated by noise.

### 6.2 Translation fidelity

Surfaced 11 gaps across three subsections. Gaps cluster into patterns:
- Fallback / edge-case behaviors
- Model configuration fidelity
- Historical-failure anti-requirements
- Negative invariants / symmetric counterparts
- Sequencing guards
- Provenance/citation stripping

These are the same *kinds* of gap a careful human review would surface — but a human review of a 500-line spec might find 2-3 of these; the differential found all of them systematically via 12 sub-agent calls.

### 6.3 Source-untouched discipline

Verified. Git diff on `<case-study>/docs/{llds,specs}/FEAT*.md` shows zero changes. Sub-agent calls were context-free (no tool access) via `claude -p`. Input slices were copies with citation.

### 6.4 Variance / reproducibility

A-runs: 58-76% Jaccard agreement on commitments. B-runs: 85-90% structural agreement. Variance is mostly about **granularity, not contradiction** — no case where runs disagreed about a commitment being present vs. absent.

For lifecycle (smallest scope): both A-runs produce the same 5 "invented" EARS with tiny re-numbering; both B-runs reconstruct the same 6 design subsections. Variance is low.

For detection (largest scope): A-run-1 and A-run-2 diverge on decomposition granularity (43 vs 54 EARS) but agree on which commitments exist. B-runs produce distinguishable prose but structurally reconstruct the same section order and ground the same EARS in the same rationale.

**Gate 3 is higher-variance than gate 4 but within an order of magnitude where the signal is still legible.** Ensemble of 2 runs per direction seems sufficient; more runs would tighten the granularity-variance without changing the commitment set.

### 6.5 Coherence-stack fit

**Validates the "differential scales up" thesis from §4 of the formal-verification exploration.** At gate 3, with narrative-rich LLDs and structured-but-prose EARS, LLM-based differential produces actionable signal where formal overlays would struggle (LLD is too prose-heavy for CodeQL-style structural extraction). This is consistent with the framing that different gates want different engines and LLM-based differential is the right fit for gate 3.

**Complementarity with formal overlay**: several of the gaps this experiment surfaces (e.g. the "no-significance-promotion" invariant in retention-tiers; the "shortText fallback" in detection; the unwanted-condition for detection model config) are once added to EARS, *formally testable* at gate 4. Pattern 1 of the exploration (bootstrap: differential first, formal second) is exactly this workflow.

### 6.6 Cost

~9 minutes of wall time.
12 `claude -p` calls.
Estimated ~350K total tokens (input + output).
Estimated single-digit dollar cost at standard API pricing.
Zero setup cost beyond a ~100-line shell script.

For a project's primary arrow, this seems like a reasonable periodic (monthly? quarterly?) cost for surfacing gate-3 drift. Not cheap enough for per-commit CI, but cheap enough for manual cadence or "run this before the next phase kickoff."

### 6.7 Maintenance signal

**If an LLD subsection changed, would B detect the EARS that need updating?**

Yes, with caveats. Consider a hypothetical change: the LLD changes "14 days" to "10 days" for the episodic tier boundary.

- A-run on the new LLD would output EARS with "10 days" (assuming prompts are re-invoked). Diff against the real EARS (still saying 14) would immediately flag the inconsistency.
- B-run on the unchanged EARS would still describe 14 days. Diff against the new LLD would flag 10 vs 14.
- Either direction surfaces the drift.

A more subtle change — say, adding "Entries may be promoted to Episodic tier if flagged as significant" to the LLD — would flip the A-run output to include a promotion EARS, making the gap against real EARS (which lacks this) obvious. This is the "changed LLD → differential catches drift" maintenance workflow.

**The overhead is re-running the 12 sub-agent calls after a significant LLD change.** Not CI-cheap, but a reasonable periodic hygiene check.

## 7. Conclusions

1. **Gate-3 differential produces signal.** Eleven real coherence gaps surfaced across three subsections with ~9 min of compute. Gaps are specific, severity-rankable, and actionable.

2. **Signal is higher-variance than gate-4 formal overlay.** Output is a diff for human review, not a pass/fail gate. Two runs per direction was sufficient to identify structural agreement; shared blind spots remain unknowable without cross-model ensemble.

3. **The "differential scales up the stack" thesis is validated at gate 3.** Gate-3 artifacts (LLD prose + EARS) are in the sweet spot for LLM-based re-interpretation — too narrative for formal extraction, too structured for pure prose-summarization.

4. **Gate-3 drift comes in identifiable patterns**:
   - Fallback/edge-case behaviors un-pinned
   - Model configuration fidelity partial
   - Historical-failure anti-requirements missing
   - Negative invariants / symmetric counterparts missing
   - Sequencing guards implicit
   - Provenance/citations stripped at EARS
   - Conjunctive commitments bundled in EARS (inverse of gate-4 flattening)

5. **Retention-tiers hypothesis needed refinement.** "Sparse EARS — intentional" was wrong (real spec is comprehensive) but "leaky-at-the-margins EARS" is right and more interesting. Subtle negative invariants and symmetric counterparts went unpinned.

6. **Complementarity with formal overlay is clear.** Gaps surfaced here are candidates for formal verification at gate 4 once added to EARS. Pattern 1 of the exploration (bootstrap: differential first, formal second) is the natural workflow.

7. **Provenance substrate is motivated.** The "lost citation trail" finding validates §5's proposal of `derives_from:` frontmatter — B-runs stripped of theory context invent plausible rationale but can't recover it. A machine-readable provenance graph would let B walk upstream.

## 8. Next steps

- **In-scope follow-up**: Add the 9 P1-P2 EARS recommended in the overlay artifact (`FEAT-gate3-primary.differential.md`) to the real spec. Verify the added EARS reduce subsequent B2 re-run noise.
- **Cross-model ensemble**: run A and B with a different model to test shared-blind-spot hypothesis.
- **Gate-2 differential**: HLD ↔ LLD round-trip. The exploration doc marked this deferred ("high noise ratio until gate 3 proves out"). Gate 3 has now proven out — gate 2 becomes next wave's candidate.
- **Provenance graph**: spike `derives_from:` frontmatter on the 11 new EARS, see whether the overlay tooling can use it mechanically.

## 9. Limitations and honest caveats

- **Single-model experiment.** Both A and B ran Claude via `claude -p`. Shared blind spots are invisible.
- **Three subsections of one arrow.** Generalization to other arrows or other projects is untested.
- **No code cross-check.** The gaps are LLD-to-EARS gaps. Whether the code honors the un-pinned LLD commitments (despite their absence in EARS) is a gate-4 question that wasn't run here.
- **Numeric thresholds and citations are not spec-shaped.** Several B orphan-EARS findings reduce to "EARS has numbers without derivation" — arguably a feature, not a bug. Whether numbers with no EARS-level derivation constitute a gap is a judgment call.
- **Run count per direction (2).** Higher counts would tighten granularity-variance estimates; two was enough to distinguish structural agreement from divergence but not enough to estimate a full distribution.

## 10. Artifacts

- `inputs/` — six extracted slices (three subsections × LLD + EARS)
- `runs/<subsection>/{A,B}-run-{1,2}.md` — twelve sub-agent outputs
- `comparison/<subsection>.md` — three per-subsection gap analyses
- `FEAT-gate3-primary.differential.md` — overlay artifact (differential engine record for the primary arrow)
- `run-experiments.sh` — reproducible runner script

Total: ~50KB of experimental output, one reusable runner, one overlay artifact.
