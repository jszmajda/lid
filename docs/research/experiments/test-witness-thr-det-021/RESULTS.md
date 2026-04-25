# Experiment 2 Results — Test-Witness Overlay for FEAT-DET-021

**Date**: 2026-04-22
**Target EARS**: FEAT-DET-021 (daily-to-weekly classification escalation)
**Engine**: test-witness
**Verdict**: `[V]` — contract satisfied, witness found, tests run green

---

## TL;DR

- **Witness found.** Four tests in `<case-study>/src/runner.test.ts` under `describe('daily-to-weekly escalation')` cover the positive case and three negation cases. Each already carries a `/** @spec FEAT-DET-021 */` annotation and runs green under vitest.
- **Contract written and mechanically verified.** A 180-line YAML contract specifies a precondition schema (3 facts + 1 forbidden pattern), action schema, postcondition (5 obligations), and three negation cases (with discriminators). A 250-line TypeScript verifier reads the contract, extracts `it()` bodies by AST-lite bracket matching, evaluates obligation detectors against each, and runs the test suite. All 23 mechanical obligations pass.
- **Rigor ceiling honestly identified.** The test-witness engine can be made **moderately rigorous** — far beyond "we have a test with a post-it note," but structurally short of proof. The three load-bearing gaps are documented as contract `limitations:` L1, L2, L3. Closing L2 (mock-vs-real coupling) would require a companion engine, not a better test-witness schema.

The core research question — **can the test-witness engine be made rigorous, or does it degrade to "we have a test"?** — has a nuanced answer: *yes* you can get to mechanically-checkable obligations with MC/DC-shaped negation coverage, *and* there is a structural ceiling at the test-is-mocked boundary. The overlay gives you the first and is honest about the second.

---

## Evaluation against the 7 shared criteria

### 1. Expressiveness — does the contract capture the EARS semantics?

The EARS is event-driven: "When E, the system shall X." Mapping that shape to contract fields is direct:

| EARS element | Contract field | Notes |
|---|---|---|
| "When daily classification produces zero total assignments…" | `precondition.facts[P1, P2]` | P1 = daily mode, P2 = zero assignments |
| "…and at least one item has no pre-existing groupIds" | `precondition.facts[P3]` | structured as "item literal lacks groupIds OR uses []" |
| "the system shall escalate by re-running detection in weekly mode" | `postcondition.obligations[O1, O2, O3]` | twice-called, second call weekly |
| "for that user" | `postcondition.obligations[O5]` | per-user discipline; weakened to "implied by shared mock" when userIds has length 1 |

What the EARS does **not** say but a rigorous contract **must**:

- **Escalation is observable** (O4 — log line). EARS is silent on observability, but test-witness needs a handle. Adding O4 is a decision the schema author makes, worth flagging — this is the point where EARS → contract stops being purely mechanical.
- **Negation cases.** EARS says "when X, Y." Rigorous reads: "and when not-X, not-Y." The source code at `runner.ts:169-171` has a three-way conjunction guard: `(mode === 'daily') && (assignments === 0) && hasUnassignedEntries`. MC/DC discipline requires one negation per conjunct; the contract has exactly three (N1/N2/N3), each flipping one conjunct.

**Verdict on expressiveness**: High for event-driven EARS. The five-part schema (precondition/action/postcondition/negation/witness) captures everything the EARS says, and the negation-case recipe captures what rigor requires beyond the EARS. Missing dimensions: **liveness** (EARS says "shall escalate" — should that be "eventually" or "immediately"? No bound exists, and the contract inherits that imprecision); **concurrency** (the contract is sequential by construction — a second simultaneous daily run is undefined behavior in both EARS and contract).

### 2. Translation fidelity — did EARS → contract feel mechanical?

**Partially.** The positive case translates mechanically — each EARS clause maps to a contract field. Negation cases and negation-case **discriminators** do not translate from the EARS alone; they translate from the **source code's enabling conditions**. This is a real finding:

> Test-witness contracts cannot be authored from EARS in isolation. They require reading either the implementation or the LLD to recover the conjunction structure of the enabling condition.

For FEAT-DET-021 the LLD (`docs/llds/FEAT.md:68`) *does* describe the escalation heuristic, but without the conjunction's component structure — the three enabling conditions only become explicit when reading the code. A stricter LLD discipline would require enabling-condition decomposition in the LLD itself, which would make contract authoring fully mechanical from docs.

The contract format also forced me to make decisions the EARS ducks:

- Scope ("for that user") — contract had to pick between explicit assertion and structural guarantee (see O5's `strictness: required_or_implied_by_shared_mock`).
- Observability — contract had to add O4 to make escalation detectable by a test.
- Post-escalation semantics — the contract pointedly does *not* assert that the *weekly* call returns non-empty assignments. That would be over-specifying; weekly might still legitimately return zero.

### 3. Source-untouched discipline

**Confirmed.** No files in the case-study codebase were modified during this experiment. The mechanical verifier reads the test file and runs the test suite; writes go only to `/Users/jess/src/lid/docs/research/experiments/test-witness-thr-det-021/`. `npm install` was done only inside the experiments dir (for `yaml` + `tsx` deps), not in the case-study — the case-study's `node_modules` were already installed.

The only technically "modifying" operation was running `vitest run` against the case-study tree, which writes to `.vite/` and potentially `.stryker-cache/` — both are gitignored build artifacts. No source, spec, test, or design file was edited.

### 4. `@spec` co-location

**Strong.** The ID traces through cleanly:

- **Source**: `<case-study>/src/runner.ts:168` — `// @spec FEAT-DET-021: Escalate daily → weekly when zero assignments and unassigned entries exist`
- **Test**: `<case-study>/src/runner.test.ts:477` — `/** @spec FEAT-DET-021 — escalation from daily to weekly when zero assignments */`
- **EARS**: `docs/specs/FEAT.md:36` — the canonical statement
- **LLD**: `docs/llds/FEAT.md:68` — narrative design rationale
- **Overlay**: new `FEAT-DET-021.overlay.yaml` + `FEAT-DET-021.test-witness.yaml`

All five nodes carry or reference `FEAT-DET-021`. The overlay formalizes the **bidirectional** link — before the overlay, the ID was grep-reachable from spec to code/test and back, but nothing declared the test was the *authoritative witness*. The overlay's `witness.describe_path` + `obligation_map.positive.it` make the correspondence explicit, machine-readable, and mechanically checkable.

One mild sharp edge: the `@spec` annotation is on the outer `describe()`, not on each `it()`. The verifier accepts that by scanning the whole file, but a stricter schema could require per-`it` annotations matching the spec ID. That would be unambiguous but noisy. Current compromise is fine.

### 5. Arrow-overlay fit

**Good fit, additive.** The manifest sits in a new `docs/overlay/primary/` tree alongside the existing `docs/arrows/primary.md`. The arrow overlay can read `_status.yaml` (per-arrow roll-up) to annotate each EARS ID with its verification state. The status marker `[x][V]` composes cleanly with the existing `[x]` — implemented AND verified.

The cascade story also works: when FEAT-DET-021's text changes, the arrow overlay already cascades to the LLD and code. The formal-verification overlay adds one more step — re-run the dispatcher's test-witness engine on the modified spec. Because the engine's input is the contract YAML + the test file, the cascade is a re-run of `verification-script.ts --contract ... --repo ...` wrapped in CI.

The natural home for this cascade is a CI hook on `docs/specs/*.md` or `@spec` diffs, which is exactly where the LID cascade lives for other artifacts.

### 6. Cost

Total wall time (for this experiment) was ~45 minutes:

- ~10 min: reading the research doc, understanding the repo layout, locating source + tests
- ~5 min: reading escalation source code and deciding conjunction structure
- ~15 min: drafting the contract (three parts — precondition, postcondition, negations)
- ~10 min: writing and iterating the verifier script
- ~5 min: running the verifier, finding two contract bugs (P3 and NF1 detectors too loose), tightening them, re-running

Two iteration cycles on the contract were needed:

1. First run: P3 regex too permissive (needed `[\s\S]` dotall), NF1 anti_regex scoped to the whole body instead of just the item-mock block (false-positive on `groupId:` in the group mock).
2. Second run: `(?s)` inline flag not supported in JS regex; swept to `[\s\S]*?`.

These iterations were *productive* — they surfaced scope-confusion hazards in the schema itself (how tightly must scope be specified to avoid false positives?). That is the kind of bug the schema exists to expose.

Token cost: moderate. Contract + verifier + RESULTS is ~1000 lines of YAML + ~250 lines of TypeScript + this writeup. Reasonable for the value delivered.

Amortization matters: once the schema and verifier exist, adding the N+1st test-witness contract is cheap — copy-paste contract, swap the spec-id-specific fields, point at a different it() block. The expensive part (schema design) is one-shot.

### 7. Maintenance signal — what breaks if FEAT-DET-021 changes?

Six failure modes, in decreasing mechanical-detectability:

1. **Spec text changes but tests don't.** If FEAT-DET-021 changes to "escalate after **two** consecutive daily runs with zero assignments," the contract's P2 still matches (zero assignments), but the test's mock setup is single-call, so it should no longer satisfy the spec. The contract would not detect this because it measures the test shape, not the spec text. **Mitigation**: cascade hook that invalidates the contract when spec text changes, forcing the author to re-verify P2/O1-O3 against the new spec.

2. **Source escalation logic changes.** If someone rewrites the guard to `(mode === 'daily') && assignments.length < 3`, the mocks still produce zero assignments so tests pass — but the "zero vs <3" distinction is silently lost. The contract now lies. **Mitigation**: companion CodeQL query that asserts the guard structure. Out of scope for test-witness; in scope for the overlay at large.

3. **Test refactored.** If the `describe`/`it` titles change, the contract's `witness.describe_path`/`obligation_map.*.it` break. **Mechanically detected**: the verifier returns `[Vx]` with "`it(...)` not found." Good signal.

4. **Assertion shape changes.** If a maintainer replaces `expect(mockDetect).toHaveBeenCalledTimes(2)` with `expect(mockDetect).toHaveBeenCalled()`, O1's detector fails. **Mechanically detected**: `[Vx]`. Good signal — and note the maintainer could legitimately do this and it would be a regression.

5. **`@spec` annotation removed.** Verifier returns `[Vx]`. Good signal.

6. **EARS wording changes but semantically equivalent.** E.g., "shall escalate" → "shall trigger weekly-mode detection." Contract should be unaffected. **Mechanically detected**: no change. Good.

The maintenance signal is therefore: **test-witness detects test-level drift reliably; it cannot detect source-level drift without a companion engine (CodeQL) and cannot detect spec-level semantic drift without a human-in-the-loop.** That's the real shape of the test-witness ceiling.

---

## Concrete test-existence verdict

**Witness found.**

- **File**: `<case-study>/src/runner.test.ts`
- **Describe path**: `Runner > daily-to-weekly escalation` (lines 477–722)
- **Tests (4)**:
  1. **Positive**: `should escalate to weekly when daily assigns zero entries and unassigned entries exist` (line 479) — witnesses P1, P2, P3, O1–O5.
  2. **N1**: `should NOT escalate when daily assigns at least one entry` (line 558) — witnesses the "mode='daily', assignments=1" counter-condition.
  3. **N2**: `should NOT escalate when all entries already have groupIds` (line 614) — witnesses "mode='daily', assignments=0, but no unassigned entries."
  4. **N3**: `should NOT escalate when already in weekly mode` (line 669) — witnesses "mode='weekly'" (weekly is terminal; does not self-escalate).
- **`@spec` annotation**: Present at line 477 (describe-level).
- **Runner**: `vitest 2.1.9` under `<case-study>/node_modules/.bin/vitest`. All 4 tests pass in <1s. (vitest reports 8 passed because the CDK build duplicates the compiled test file into a generated asset path; the verifier accepts multiples of `expected_passed`.)

---

## The core research question — how rigorous can test-witness be?

I'll answer this directly.

**The naive version ("we have a test annotated with @spec") is weak.** It proves only that *some test* names the spec ID. It says nothing about whether the test's preconditions, action, or assertions correspond to the spec's semantics. A test titled "FEAT-DET-021" that asserts `expect(true).toBe(true)` would pass the naive check.

**The contract-based version ("the test body matches a structured obligation map") is rigorous-enough for a useful regime.** Concretely, here is what the contract mechanically guarantees when verification returns `[V]`:

1. The named `it()` block **exists** at the specified `describe`/`it` path.
2. The test body contains the specified **action invocation** (`runThreadProcessing(...)`).
3. The test body installs a mock setup matching each **precondition fact**'s detector (e.g. `mockResolvedValueOnce({ assignments: [] })` for P2).
4. The test body contains assertions matching each **postcondition obligation**'s detector (e.g. `toHaveBeenNthCalledWith(2, ..., detectionMode: 'weekly')` for O3).
5. The test body **does not** contain **forbidden** patterns (e.g. pre-populated non-empty `groupIds` on the entry mock, which would falsify P3 semantically).
6. The negation tests exist, satisfy their negation-specific obligations, AND their **discriminators** (e.g. N2 must actually install non-empty groupIds on the entry mock; otherwise it collapses to the positive case).
7. All the tests **run green** under the project's own runner.

That is a lot — it is meaningfully stronger than "we have a test." But it has **three load-bearing gaps**:

- **L1 (Mock fidelity).** The contract can't tell whether the mock values used in setup semantically resemble a real daily-detection scenario. The contract says "mock returns `{ assignments: [] }`"; it cannot tell whether production ever reaches an analogous state. This is the test-in-isolation problem.
- **L2 (Mock-vs-real coupling).** If `runner.ts` stopped reading `result.assignments` altogether and always escalated, the tests would still pass — they mock the classifier. The test-witness engine cannot see into the production control flow. Closing this gap requires a **companion engine** — a CodeQL query over the source that asserts "the escalation branch is reachable only when `assignments.length === 0`." Overlay dispatch was designed for exactly this scenario; test-witness alone doesn't close L2.
- **L3 (Semantic correspondence, not structural).** Regex-based detectors catch structural assertion shapes. If someone writes `expect(mockDetect).toHaveBeenCalledTimes(2)` but the 2 comes from a duplicate retry loop unrelated to escalation, the detector passes. AST-aware detection (via ts-morph) would tighten this; full semantic check requires symbolic execution.

So the honest answer: **test-witness is an overlay on top of a test, which is itself an overlay on top of production code.** Each layer preserves some information and drops some. The contract makes the test-level obligations explicit and checkable. It cannot recover information the tests themselves didn't capture (L1), it cannot see into production (L2), and it cannot judge semantics from shape alone (L3).

**Is it "just we have a test with a post-it note"?** No, because the contract:

- forces authors to decompose enabling conditions into facts,
- mandates negation cases with MC/DC discipline,
- requires negation discriminators (preventing a negation test from collapsing into the positive case),
- binds each obligation to a specific assertion shape verifiable by regex/AST,
- runs the tests and requires green.

These are substantive, machine-checkable obligations. A real-world test suite without the overlay would routinely fail half of them — this contract failed two of its own detectors on the first pass even with a test suite written by a careful author, because writing rigorous scope-aware detectors is *itself* subtle work.

**Is it formal verification?** No. It is **structured empirical evidence** with machine-checkable obligations. It belongs in the same family as property-based testing with declared properties — it is stronger than plain unit testing because the properties are declared adversarially (positive + negation + discriminator), but it is weaker than a proof because the SUT is executed, not reasoned about.

**To push it further you would need:**

1. **AST-aware detectors.** Replace regex with ts-morph queries that walk the assertion's call expression. Eliminates L3-class false positives.
2. **Mutation testing integration.** Use Stryker (the repo already has `stryker.config.mjs`) to mutate the escalation branch and confirm the escalation tests fail on at least one mutant per conjunct. This closes L2 partially — if mutating the escalation logic doesn't break the tests, the tests don't actually witness the behavior.
3. **Companion CodeQL or LemmaScript engine.** For properties that test-witness structurally can't verify (e.g., "the escalation branch is reachable only under the conjunction"), dispatch to a different engine. This is the overlay-dispatch thesis — test-witness does what it's good at, other engines cover the gaps.

With (1) + (2), the test-witness engine would be *genuinely rigorous* for behavioral EARS of this shape. Without them, it's "structured empirical evidence with documented limitations" — which is still a massive improvement over the status quo.

---

## What the overlay directory should actually look like

After this experiment, the per-arrow overlay for the primary arrow would contain (for this EARS alone):

```
docs/overlay/primary/
  FEAT-DET-021.overlay.yaml          # manifest (Appendix A)
  FEAT-DET-021.test-witness.yaml     # contract (schema 0.2)
  _status.yaml                      # roll-up of all primary-arrow specs
```

Multiplied across the case-study's ~200 EARS-like items in the primary arrow (at approximate count), the overlay tree grows meaningfully. That cost is real and should be budgeted — not every EARS is worth an overlay contract. The per-arrow escape hatch (`overlay: disabled`) and the per-EARS `[Vn]` (not a verification candidate) markers exist for exactly this. A reasonable discipline would be: **overlay every event-driven and functional EARS; skip qualitative ones with `[Vn]`; review per-arrow cost quarterly.**

---

## Artifacts produced

- `FEAT-DET-021.overlay.yaml` — manifest per Appendix A schema; points at contract + witness + last_run.
- `FEAT-DET-021.test-witness.yaml` — 210-line contract; schema v0.2.
- `verification-script.ts` — 250-line mechanical verifier; reads contract, extracts it()-bodies, evaluates detectors, runs tests, reports pass/fail per obligation.
- `package.json` / `node_modules/` — local (experiments-dir only) deps for `yaml` + `tsx`, not committed. Not needed if the verifier is later rewritten with a zero-dep YAML parser and `node --experimental-strip-types`.
- `RESULTS.md` — this file.
- (No `draft-test.ts` — witness exists in-tree.)

---

## Recommendation for adoption

If LID wants to pilot a formal-verification overlay starting with test-witness:

1. **Adopt the contract schema** (the v0.2 YAML shape) as the MVP. It is expressive enough for event-driven EARS and has honest `limitations:` carve-outs.
2. **Require discriminators on negation cases.** This experiment's surprise finding was that without `N2.P3neg`, the N2 test can trivially satisfy its postcondition while installing the *same* setup as the positive test — i.e., not actually be a negation case at all. Discriminators close that.
3. **Run the verifier in CI.** On any commit touching a `@spec FEAT-DET-021`-annotated source or test, re-run `verification-script.ts --contract ...` and block merges on `[Vx]`.
4. **Pair with a mutation-testing pass per arrow**, not per EARS. This is where the coupling-to-production gap (L2) starts to close without requiring a second engine.
5. **Budget the overlay at the arrow level.** Not every EARS needs a contract; not every arrow needs a complete overlay. Minimum-system discipline applies.

The experiment converged. Test-witness can be meaningfully rigorous. It is not proof. It is much better than nothing.
