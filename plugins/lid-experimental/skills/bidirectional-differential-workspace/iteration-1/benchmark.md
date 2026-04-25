# Iteration 1 benchmark — bidirectional-differential

| Configuration | Pass rate | Mean tokens / eval | Mean wall-clock / eval |
|---|---|---|---|
| **with_skill** | 15/18 (83.3%) | 50,447 | 214s |
| **without_skill** (baseline) | 6/6 (100.0%) | 23,067 | 54s |

## Classification correctness

All 3 with_skill runs hit the expected classification on the headline outcome:

- eval-0 (SCORE-001) → `BD-COHERENT` ✅
- eval-1 (PREF-001) → `BIDIRECTIONAL-DRIFT` ✅
- eval-2 (DEDUP-001) → `B-ONLY-DRIFT` ✅

All 3 without_skill (baseline) runs reached the same drift shape via careful direct review — identified coherent / bidirectional drift / B-only drift respectively, with similar reconciliation recommendations.

## Failed assertions (3 of 18 with_skill)

Two are fixture-design issues, one is a harness limitation. None is a skill-protocol failure.

1. **eval-1: A-direction expected ≥2 tiebreaker variants, observed 3/3 byte-identical.** The PREF-001 EARS as written admits a single naive reading; modern TS coalesces all three A-runs to `(x, y) => x ?? y`. Classification still landed correctly because B-direction did the lifting.
2. **eval-2: A-direction expected at least one Set-based (unordered) dedup, observed all 3 used `[...new Set(ids)]`.** That construct IS Set-based but happens to be order-preserving in practice (JS Set spread). Modern TS idiom is too strong here; "deduplicate" pulls naive impls onto a single shape.
3. **eval-0: per-arrow rollup user summary not written to disk.** The skill's protocol calls for a per-run summary alongside the per-EARS audit record; the subagent harness blocked `summary.md` writes from sub-tasks ("subagents should return findings as text, not write report files"), so the summary content surfaced in the agent's text reply instead. This is a test-harness boundary, not a skill failure — but worth noting that on real `/differential-audit` invocations (no sub-task harness in the way), the user summary is expected to render in-conversation.

For iteration 2: rewrite eval-1 and eval-2 EARS to use more abstract verbs ("select one of two values" / "produce a normalized list") so A-direction variance materializes; figure out a harness pattern that lets summary.md land on disk for grading.

## Skill vs baseline cost

with_skill costs **~2.2× the tokens** and **~4× the wall-clock** of a careful manual review. On 3 small self-contained fixtures the baseline lands the same answer cheaper.

The skill's expected value-add isn't visible at this scale — it emerges when:
- Auditing N≥10 EARS systematically (manual review of every pair becomes infeasible)
- Producing structured cascade-shaped audit records that become git artifacts (the baseline doesn't write the record at all)
- The blind reconstructions surface drift the human reviewer would have explained away (more relevant on EARS the reader has prior beliefs about)

Iteration 1 doesn't exercise those at-scale advantages. The data still validates the protocol works end-to-end and produces correctly-classified, well-structured records.

## Notable signals from the run

- **Stripping spot-checks all passed** (overlap 17–26%, well below ~70% threshold). The stripping rules are doing their job; B-direction reconstructions describe behavior, not echo vocabulary.
- **N=5 split-rule never fired.** Within-direction agreement was high enough at N=3 that no re-runs were needed across all 3 evals. Default N=3 looks well-calibrated for fixtures of this complexity.
- **Subprocess invocation pattern worked end-to-end.** Each with_skill subagent spawned 6 parallel `claude -p` calls via Bash background invocations with `< /dev/null`. All 18 subprocess calls returned cleanly — no hangs, no JSON parse failures, no model errors.
- **A-direction was tighter than fixture authors expected.** This is the most important real finding: modern TS idioms produce surprisingly convergent naive implementations from EARS. The skill remained robust because B-direction did most of the drift detection — confirming the bidirectional design (B is the stronger detector; A disambiguates).
- **All audit records use the cascade-shaped recommendation format** (validate → LLD → EARS → tests → code) per the redesign. Recommendations are concrete and actionable, not vague.

## Per-eval drilldown

- Per-run grading: `{eval-dir}/{with_skill|without_skill}/grading.json`
- Per-EARS audit records produced by with_skill runs: `{eval-dir}/with_skill/project/docs/arrows/experiments/bidirectional-differential/{segment}/{EARS-ID}.md`
- Timing data: `{eval-dir}/{with_skill|without_skill}/timing.json`
