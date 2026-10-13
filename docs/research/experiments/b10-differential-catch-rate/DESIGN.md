# Experiment B10 — Differential Catch Rate on Seeded Intent Gaps (DESIGN)

**Date**: 2026-08-01
**Status**: DESIGNED; pre-registration amended 2026-08-02 (see § Pre-registration amendment) — run in progress
**Motivation**: The attestation stance — that review can shift from reading every line to verifying that what landed traces to what was meant — rests on adversarial instruments whose detection power is currently asserted, not measured. That makes the standing defense against the hollow-test failure mode ("that's why the instruments exist") circular: unguarded attestation demonstrably fails (B-series data, the regeneration gap log), therefore trust the guards — but there is no data on the guards. "Adversarial audit can carry what line-reading carried" is a promissory note until the instruments have a **measured catch rate**.
**Relationship to prior experiments**: B1/B2 established single-direction differentials; B9 ran the bidirectional unit on 6 real filter-arrow EARS and found 5/6 BD-DRIFT plus one flagged latent bug — strong *sensitivity* evidence on natural drift, but with no ground-truth answer key, B9 cannot compute recall or precision. B10 closes that gap by seeding known intent gaps and scoring detection against a sealed key.

---

## Hypothesis

The bidirectional differential detects seeded intent gaps with recall ≥ 0.70 at the fresh-subagent independence tier, with recall varying measurably by (a) gap class and (b) verifier independence tier. Pre-registered secondary expectation: the hollow-test class (H) scores lowest — it is the load-bearing number for the open question of whether audited traces can carry what human line-reading carries, and it is reported prominently whatever it shows.

## Fixture

Primary: **portfolio-tracker** (public repo), one mid-size segment with 20–40 EARS and healthy test coverage — `sheets-view` or equivalent. Pilot option: `examples/urlshort` implementation (small, self-contained) to shake out the harness before spending on the full run.

## Seeded gap classes

Each seed is applied **in isolation** (own branch/worktree) so attribution is clean. All seeds must compile, pass CI, and keep every existing `@spec` citation resolving — a seed that trips the mechanical layer is testing the wrong instrument and gets redesigned. Seeds are drawn from the regeneration gap-log taxonomy (wire formats, exact constants, error semantics, boundary behavior, tie-breaking) so they are realistic, not synthetic strawmen.

- **Class U — unstated intent in code** (expect B-direction elevation; B9 codes B-ONLY-DRIFT or BD-DRIFT): add a real behavior no spec states — input normalization, a retry with backoff, a tie-break rule, a silent default — with tests pinning it.
- **Class P — phantom spec** (expect A-direction divergence): add or alter a spec line that nothing enforces, or weaken the implementation so an existing spec is no longer honored, while the suite stays green.
- **Class H — hollow test** (the gap-log failure mode; hardest): alter code to subtly violate an existing spec and adjust tests so they pass by pinning the narrowed behavior. This is "Sonnet repeatedly wrote tests pinning its own narrowed implementation," reproduced deliberately.

**n**: 6–8 seeds per class (18–24 total), plus an **equal-size control set** of untouched specs for the false-alarm rate.

## Seeding protocol

1. Seeder is a separate session (or the human) from every auditor session; auditors never see seed diffs or this design's answer key.
2. The answer key (seed → affected EARS → expected detection direction) is written before any audit runs and kept out of the audited tree.
3. Each seed gets a one-line realism justification citing which gap-log category it instantiates.

## Independence tiers

Per the HLD's context-independence spectrum:

- **T1** — same-session self-audit (weakest; the agent that can see the seed-application context).
- **T2** — fresh zero-context subagent, same model (the standard `/bidirectional-differential` posture). **This is the headline tier.**
- **T3** — different-provider model as auditor (strongest available).

**Runs**: match B9 — 3 runs per direction per spec per tier, so stability is measurable. INCONSISTENT-BLIND from the B9 code set is retained as an outcome, not discarded.

## Cost containment (choose before running)

Full grid ≈ (24 seeds + 24 controls) × 3 tiers × 6 calls = **864 subcalls** — B9's 36-call session ×24. Reduced design: full grid at **T2 only** (288 calls), with T1 and T3 sampled on an 8-seed/8-control subset (192 calls) ≈ **480 subcalls total**. The reduced design still answers the headline question (T2 recall by class) and gives a directional independence gradient. Record tokens and wall-clock per call so the RESULTS can state cost-per-spec honestly — the economics question is as real as the recall question.

## Scoring

- **Recall**, by class × tier: a seed counts as detected when the differential's classification for its affected EARS surfaces the seeded gap (correct direction and substance, adjudicated blind against the key).
- **Precision / false-alarm rate**, on controls — with one required subtlety: a "false positive" on a control may be a *genuine natural-drift finding* (B9 found 5/6 on real specs). Blind-adjudicate every control finding first; adjudicated-real findings are excluded from the false-alarm count and reported separately as incidental discoveries.
- **Stability**: agreement rate of classification across the 3 runs per direction.
- **Cost**: tokens, wall-clock, and dollars per spec per tier.

## Pre-registered readouts

1. Headline: overall T2 recall (threshold: ≥ 0.70 makes "the instruments guard attestation" defensible; below that, the number is published anyway and the question stays open — now with data).
2. Class H recall, reported regardless of result — this is the number the trace-vs-reader question actually turns on.
3. Independence gradient: does T3 > T2 > T1 hold? (If independence buys nothing, the correlated-verifier objection stands.)
4. Stability and cost, stated plainly.

## Confounds and limits (state in RESULTS)

Seeder realism (seeds authored knowing the instrument exists); single codebase; small n; adjudicator bias (mitigated by blind adjudication, not eliminated); model version drift between runs; controls share a repo with seeds (a detected seed could theoretically prime a same-session auditor — mitigated by per-seed isolation and zero-context auditors at T2+).

## Runbook sketch

1. Pick segment; snapshot baseline; verify coherence gate green.
2. Author seeds + answer key (separate session); one branch per seed; realism note per seed.
3. Pilot: 2 seeds end-to-end on urlshort or the smallest segment to validate prompts and scoring.
4. Run the chosen grid (`claude -p` per B9's harness pattern; reuse B9's prompts/ and runs/ layout).
5. Collect classifications; blind adjudication against the key; adjudicate control findings.
6. Score recall/precision/stability/cost; write `RESULTS.md` in this directory per B-series conventions (Verdict up top, per-seed table, key findings).
7. Publish the headline numbers in this directory's `RESULTS.md`; anything downstream cites from there.

---

## Pre-registration amendment (2026-08-02 — recorded before any seeding or audit runs)

Agreed with Jess 2026-08-01/02. The original text above is preserved unedited; where this section conflicts with it, this section governs.

### Model policy: measure the instrument as deployed

LID users run Sonnet/Opus-class coding agents, not frontier research models. Every **in-instrument** call — seed authoring, A/B generation, per-tier classification — runs on deployed-class models. Classification is inside the instrument (recall is defined over "the differential's classification", which in real use the user's own model performs), so each arm's classifier runs at that arm's auditor model. Fable appears only in the **measurement layer** (orchestration, blind adjudication, scoring): that layer is not being measured, needs only accuracy, and any bias it carries applies uniformly across arms so it cannot fake a gradient. Cross-family bias in the Fable adjudicator is itself checked (below).

### Amended arms

| Arm | Auditor model | Posture | Grid | Isolates |
|---|---|---|---|---|
| Seeder | Sonnet | authors seed in own clone; must pass `scripts/ci.sh` | 24 seeds (8U/8P/8H) | — (Sonnet authorship is provenance-realistic: the gap-log failure mode was Sonnet's) |
| T1 | Sonnet | self-audit inside the seeding context | 8 seeds + 8 controls | zero-context effect (vs T2) |
| **T2 (headline)** | Sonnet | fresh, zero-context | full 24 + 24 | recall by class |
| T2-cap | Opus | fresh, zero-context | 8 + 8 | capability, within family |
| T3 | GPT-5.6 Terra | fresh, zero-context | 8 + 8 | provider independence, capability held constant |
| EXP | Haiku + GPT-5.6 Luna | fresh, zero-context | 8 + 8 each | cheap-model viability (exploratory only) |

- T3 is **Terra** (Sonnet's capability peer), superseding the original "strongest available": T2 vs T3 then isolates cross-provider independence without a capability jump riding along. Sol (the GPT-5.6 flagship) is reserved for the adjudication cross-check.
- The EXP arm is exploratory: excluded from headline readouts, run last, skippable.
- T1 controls are audited by seeder sessions against untouched specs in their own seeded clones — the same-session priming exposure the original confounds section names is precisely what T1 measures.

### Fixture pinned; controls are paired

`portfolio-tracker` / `sheets-view` (24 EARS, all `[x]`). Baseline `ba94c01af8eb725292340d83e7923d7ecc136c90`; `scripts/ci.sh` green at preflight including Verus/Kani stages and @spec-coverage (365/365). All work happens in throwaway clones; gitignored local files never enter clones; nothing is pushed. sheets-view has exactly 24 EARS, so at n=24 a disjoint untouched-spec control set is impossible; controls are the **same 24 EARS audited on the pristine baseline clone** (seeds live on isolated per-seed clones), i.e. each spec serves as its own control (paired design). The original control-adjudication subtlety stands unchanged. The pilot runs on sheets-view itself (2 seeds end-to-end, seeded first, audited and scored before bulk seeding and any grid spend); `examples/urlshort` is docs-only in this repo, so the original pilot option is unavailable.

### Adjudication cross-check (new)

To check same-family preference in the Fable adjudicator, **Sol** independently re-adjudicates a sample: all pilot items plus ≥20% of grid adjudications, stratified to include T3-arm findings. Pre-registered trigger: Fable↔Sol agreement < 0.85 on the sample → the adjudication protocol is reviewed and all disagreements re-adjudicated by the human before any recall number is published.

### Harness

Claude arms run via Claude Code's Workflow tool (fresh zero-context subagents; schema-forced classification outputs). OpenAI arms run via `harness/openai_call.py` (stdlib-only; exact per-call token usage and latency from the API response). Cost-readout granularity is asymmetric — exact per-call on the OpenAI side, per-arm aggregates from workflow journals on the Claude side — and RESULTS states this. B-direction auditors receive an audit tree containing code only (docs stripped, `@spec` annotations stripped); A-direction auditors receive only the EARS text plus a one-line codebase description, per B9. Seed patches and the sealed answer key live in `answer-key/` in this directory and never enter any audited tree.

### Pilot-gated adjustments (2026-08-02, post-pilot, pre-grid — see PILOT.md)

Agreed with Jess after the pilot readout, before bulk seeding or any grid audit ran:

1. **Classifier rubric tightened; direction semantics made explicit.** Direction A = spec-side surplus (the spec states or forces something the code does not honor — including Class P's stated-but-unenforced claims — or under-specifies a sub-decision, forcing invention); direction B = code-side surplus (code+tests enforce behavior the spec never states); BD = both directions surface the same gap. A-side behavior that traces to explicit spec text and is missing from the real code is a finding; unanimous A-side behavior with NO basis in the spec text is an assumption artifact, not a finding. Findings are listed strongest-first.
2. **Prompt freeze + pilot refold.** The pilot's audits were shakeout only. `harness/audit-prompts.md` is the frozen instrument of record; all 48 T2 grid units — including the 4 pilot specs — run (or re-run) on the frozen prompts. One Class-P unit is smoke-tested end-to-end before the full grid launches, since the pilot exercised only U and H.
3. **Prominence metrics pre-registered.** Pilot showed unit-level classification has no discriminative power (all 4 units, seeds and controls alike, classified BD-DRIFT); it is reported as descriptive only. Added secondary metrics: rank of the key-matched finding (top-finding rate) and per-unit signal-to-noise (adjudicated-REAL findings ÷ total findings). Incidental discoveries are deduped across arms when reported.
4. **Adjudication layer confirmed as load-bearing.** The blind realness pass flipped 9 of 10 control findings away from "drift" (6 CROSSREF, 3 FALSE-ALARM); it runs un-skimped at the full grid scale, with the Sol cross-check per the amendment above.

This harness is retained after the experiment as a reusable eval harness for future LID iteration (seeded-gap catch rate as a regression metric for instrument changes).

### Amended call math

≈1,000 calls: T2 full grid 288 + 48 classifiers; T1/T2-cap/T3 subsets 288 + 48; EXP 192 + 32; ~24 seeders; ~100 Fable adjudications plus the Sol cross-check sample. Growth over the original 480-call reduced sketch is the T2-cap arm and the EXP arm.
