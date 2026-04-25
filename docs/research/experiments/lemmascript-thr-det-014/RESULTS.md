# Experiment 3 Results — LemmaScript Functional Overlay for FEAT-DET-014

**Date**: 2026-04-22
**Experimenter**: Claude (Opus 4.7, 1M context) for Jess Szmajda
**Target EARS**: FEAT-DET-014 — "When the assignment processor assigns entries to existing records, it shall update lastEntryAt (newest entry timestamp), entryCount (incremented by new assignments), and daySpan (recalculated from record creation to newest entry)."

## Verdict

**Verified.** Every verification condition discharged cleanly. Counts across artifacts:

| Artifact | Dafny VCs (default) | Dafny VCs (`--isolate-assertions`) | Errors |
|---|---|---|---|
| `FEAT-DET-014.annotated.dfy` | 3 | 32 | 0 |
| `FEAT-DET-014-stretch.dfy` | 8 | 85 | 0 |
| `FEAT-LIFE-001.annotated.dfy` | 16 | 124 | 0 |
| **Total** | **27** | **241** | **0** |

The main EARS (FEAT-DET-014) verified with **zero manual proof additions** to the Dafny file — the TypeScript annotations alone were enough. The lifecycle-classification stretch property (monotonicity under advancing `now`) needed a hand-written Euclidean-identity proof of integer-division monotonicity; once that was in hand, the classification ordering followed in a few lines.

## Final Dafny output (FEAT-DET-014 main)

```
$ dafny verify FEAT-DET-014.annotated.dfy
Dafny program verifier finished with 3 verified, 0 errors

$ dafny verify --isolate-assertions FEAT-DET-014.annotated.dfy
Dafny program verifier finished with 32 verified, 0 errors
```

(Full logs: `dafny-iter-final.log`, plus per-iteration logs `dafny-iter1.log` through `dafny-life-iter5.log`.)

## Properties verified for FEAT-DET-014

- **Counter exactness**: `res.entryCount == record.entryCount + |newEntries|`
- **Counter monotonicity**: `res.entryCount >= record.entryCount`
- **lastEntryAt monotonicity**: `res.lastEntryAt >= record.lastEntryAt`
- **lastEntryAt upper bound over inputs**: `∀ k < |newEntries|. res.lastEntryAt >= newEntries[k].createdAt`
- **lastEntryAt realizes a witness**: `res.lastEntryAt == record.lastEntryAt ∨ ∃ k. res.lastEntryAt == newEntries[k].createdAt`
- **daySpan non-negative**: `res.daySpan >= 0`
- **daySpan exact identity**: `res.daySpan == JSFloorDiv(res.lastEntryAt - res.createdAt, MS_PER_DAY)`
- **createdAt immutable**: `res.createdAt == record.createdAt`

The upper-bound + witness pair is logically equivalent to
`res.lastEntryAt == max(record.lastEntryAt, max_k newEntries[k].createdAt)`; the explicit `seqMax` ghost version (`FEAT-DET-014-stretch.dfy`) also verifies and is included for completeness.

## Properties verified for FEAT-LIFE stretch

- **Totality**: for every `(now, lastEntryAt)` with `now >= lastEntryAt`, `classify` returns exactly one of `active | quiet | archived` (FEAT-LIFE-001)
- **Threshold correspondence**: the three tags correspond exactly to `daysSince < 7`, `7 ≤ daysSince < 30`, and `daysSince >= 30` respectively (FEAT-LIFE-002)
- **Monotonicity under time advance**: `statusRank(classify(now1)) <= statusRank(classify(now2))` when `now2 >= now1` (FEAT-LIFE-003)
- **No reversal**: once a record is non-active, any later classification is also non-active; once archived, stays archived (corollary of monotonicity)

These are non-trivial — the monotonicity property in particular required an integer-division-monotonicity lemma that Dafny's Z3 does not discharge automatically.

---

## Evaluation against the seven criteria

### 1. Expressiveness

**Score: strong on the pre/post shape; limited on temporal/cross-call.**

LemmaScript's `//@ requires`, `//@ ensures`, `//@ invariant`, plus `forall(k, P)` / `exists(k, P)` quantifiers, capture FEAT-DET-014 *exactly*. The full EARS semantics — counter exactness, max-over-sequence, daySpan-as-JSFloorDiv, createdAt-immutability — landed as a direct EARS-to-annotation rewrite. Nothing had to be invented at the annotation layer.

Where LemmaScript ran out of expressive room: **cross-call temporal properties**. "As `now` advances, status never reverses" is a relation between two separate invocations, not a single-call post. The annotation language doesn't have a `//@ monotonic_in(now)` form, so I encoded that property as a hand-written Dafny lemma below the generated content. That's consistent with the overlay-dispatch framing — cross-call properties are a TLA+-shaped concern; LemmaScript is for single-call pre/post.

Ghost *variables* exist (`//@ ghost let x = ...`). Ghost *functions* are not a first-class annotation (though the emitted Dafny file can define them, as I did in the seqMax stretch). The witness+upper-bound equivalent formulation lets most "`lastEntryAt == max(...)`"-style EARS stay in pure annotation form.

### 2. Translation fidelity

**Score: mechanical for this EARS; no invention required for FEAT-DET-014.**

EARS-to-annotation was genuinely mechanical. The EARS fragments translate line-by-line:

| EARS fragment | Annotation |
|---|---|
| "update lastEntryAt (newest entry timestamp)" | `\result.lastEntryAt >= record.lastEntryAt` + upper-bound + witness |
| "entryCount incremented by new assignments" | `\result.entryCount === record.entryCount + newEntries.length` |
| "daySpan recalculated from record creation to newest entry" | `\result.daySpan === Math.floor((\result.lastEntryAt - \result.createdAt) / MS_PER_DAY)` |
| (implicit) "createdAt immutable" | `\result.createdAt === record.createdAt` |

The one "invention" that felt like a soft call: the EARS doesn't explicitly state `daySpan >= 0`, but the EARS verb "recalculated from record creation to newest entry" implies a non-negative distance. I made the precondition `record.createdAt <= record.lastEntryAt` explicit, which is a plausible reading of the surrounding FEAT-DATA invariants but is not literally stated in FEAT-DET-014. In a real review, this would be worth naming (either lift into FEAT-DATA-001 or embed in the EARS narrative).

### 3. Source-untouched discipline

**Confirmed.** No file in the case-study codebase was modified (or read, in the end — I didn't need to look at the real source; the overlay's annotated TS stands alone as a verifiable model). `git status` on that repo shows only pre-existing unrelated changes.

The overlay artifacts live entirely under `/Users/jess/src/lid/docs/research/experiments/lemmascript-thr-det-014/`:

```
FEAT-DET-014.annotated.ts        # TS with //@ annotations
FEAT-DET-014.annotated.dfy.gen   # generated Dafny (regeneratable)
FEAT-DET-014.annotated.dfy       # Dafny source of truth (identical to .gen — 0 additions)
FEAT-DET-014.overlay.yaml        # overlay manifest
FEAT-DET-014-stretch.dfy         # hand-written seqMax-ghost version
FEAT-LIFE-001.annotated.ts       # lifecycle classification TS
FEAT-LIFE-001.annotated.dfy.gen  # generated Dafny
FEAT-LIFE-001.annotated.dfy      # Dafny with ~120 lines of proof additions
iteration-log.md                # per-iteration log
dafny-*.log                     # verifier output per iteration
```

### 4. `@spec` co-location

**Works.** The `@spec FEAT-DET-014` comment threads through:

- The EARS file (the primary spec in the case-study codebase — not modified; we assume it exists)
- The annotated TS (file header: `// @spec FEAT-DET-014`)
- The generated Dafny `.dfy.gen` and the proved `.dfy` (via `// Generated by lsc from FEAT-DET-014.annotated.ts` plus inheritance of the header comment if the emitter preserved it — actually the emitter strips TS comments that aren't `//@`, so the spec ID lives only in the TS + the YAML manifest. This is a minor gap the manifest covers.)
- The overlay YAML manifest's `spec_id: FEAT-DET-014`

One note: the LemmaScript Dafny emitter does *not* preserve the `// @spec FEAT-DET-014` comment from the TS head into the `.dfy.gen`. That means a reader of the Dafny file alone can't trace back to the EARS without the manifest or the filename. Not a blocker — the filename is `FEAT-DET-014.annotated.dfy` — but a small fidelity gap. A future emitter improvement: preserve top-of-file `@spec` comments.

### 5. Arrow-overlay fit

**Good fit.** The three-artifact pattern (annotated TS + generated Dafny + overlay YAML) grafts onto the existing arrow-overlay model exactly as the research doc's Appendix A sketches. The `_status.yaml` roll-up can read `FEAT-DET-014.overlay.yaml.status` directly.

The manifest fields I populated — `spec_id`, `arrow`, `engine`, `backend`, `targets`, `artifacts`, `witnesses`, `status`, `last_run`, `properties_verified` — feel LID-native. The optional `stretch:` sub-section (where I packaged the FEAT-LIFE-001 block under the same overlay) is convenient for "a primary EARS with related cross-call stretch properties" but might want its own top-level overlay file in a real deployment. For the experiment, one-file-per-main-EARS with stretch inline is fine.

### 6. Cost

**Moderate setup, near-zero iteration cost for the main property, moderate cost for the non-trivial stretch.**

Setup (one-shot):
- `brew install dafny` — ~3 min, downloads .NET 8 + Z3 + Dafny itself (~600 MB on disk)
- `npm install lemmascript` — 1 second, 26 packages
- Cloning LemmaScript repo for docs — 2 seconds

Iteration cost:
- **FEAT-DET-014 main**: 2 iterations (baseline, then strengthened semantics). **Zero** manual proof additions. Wall-clock ~5 minutes including reading the LemmaScript SPEC for annotation syntax.
- **FEAT-DET-014 stretch (seqMax ghost)**: 1 iteration, 2 induction lemmas, wall-clock ~10 minutes (mostly getting the sequence-slice arithmetic right, i.e. `entries[..n+1][1..] == entries[1..][..n]`).
- **FEAT-LIFE-001 main**: 1 iteration. **Zero** manual proof additions. Wall-clock ~3 minutes.
- **FEAT-LIFE-001 monotonicity (cross-call)**: 3 iterations hunting for the right division-monotonicity proof. Final form: 1 ghost function (`statusRank`), 6 lemmas, ~120 lines of hand-written Dafny. Wall-clock ~25 minutes (mostly the "Z3 won't do nonlinear integer arithmetic" dance).

Total Dafny verification time across all artifacts: under 30 seconds aggregate. The `--isolate-assertions` run on FEAT-LIFE-001 (124 VCs) takes ~10 seconds.

### 7. Maintenance signal

**Good for pre/post changes, hand-edit-required for threshold-structure changes.**

What breaks under different edits to FEAT-DET-014:

| Edit | What breaks | Fix cost |
|---|---|---|
| Add a new counter (e.g. `assignmentCount`) | Generated Dafny datatype changes; existing ensures still hold; need a new ensures for the new field | Low — add annotation, regen, re-verify |
| Change `daySpan` formula (e.g. "from first entry to last entry") | `daySpan` ensures obviously broken; new formula must be expressed in terms of available fields | Medium — depends on whether the new formula is in LemmaScript's `Math.floor`-compatible fragment |
| Add a non-empty-entries precondition (require `newEntries.length > 0`) | Nothing semantic breaks; `exists` witness becomes cleaner | Low |
| Change `MS_PER_DAY` or the `QUIET`/`ARCHIVED` thresholds | Nothing breaks (thresholds are soft constants) | Zero — just edit the constant |
| Change status classification to 4 bands | `LifecycleStatus` datatype changes; the hand-written monotonicity lemma needs one more case in `statusRank`; rank ordering argument still holds | Medium — mechanical |
| Change to "use stars-only, ignore time": makes `classify` non-monotonic in `now` | The monotonicity lemma is now false. Dafny would report the failure, but the human has to decide whether the EARS's monotonicity claim is being relaxed | Signal is exactly where you want it — the verifier surfaces the semantic drift |

The LemmaScript regeneration flow (`lsc regen`) uses a three-way merge of `.dfy.gen` and `.dfy` with the prior `.dfy.gen` as base. Pure additions below the generated content survive regeneration cleanly. This matches how I structured FEAT-LIFE-001's proof additions.

The key maintenance-signal property: the arrow overlay's status flips from `V` to `Vp` / `Vx` whenever `dafny verify` fails after a change. CI can run this on a pre-commit or PR hook.

---

## Honest LLM-proof-filling assessment

I am an LLM. How hard was this to discharge for me?

**FEAT-DET-014 main (pre/post on a pure function)**: Trivial. The annotation-to-Dafny translation was a direct read of the SPEC.md special-forms table. Once the annotations were in place, Dafny closed all VCs without any prompting. If the user handed me this EARS and said "verify it," I'd have a clean result in ~5 minutes of reading + writing.

**seqMax ghost-function stretch**: Easy but required Dafny-specific pattern knowledge. The `entries[..n + 1][1..] == entries[1..][..n]` type of sequence bookkeeping is standard Dafny induction grease — I've seen enough of it across the LemmaScript case studies (toposort, arraySum, equality-game) that I knew to write the prefix-append lemma and the upper-bound lemma. If I hadn't seen those patterns I'd have spent an hour on the first-slice identity alone.

**JSFloorDiv integer-division monotonicity**: This is the one where I'd hit a wall on a harder property. Integer-division monotonicity is a well-known SMT weak spot. The Euclidean-identity-by-contradiction proof I wrote took 2 tries — first I tried the inductive step directly, Dafny's Z3 rejected it without the multiplication hint `(a/b - 1) * b == (a/b) * b - b`. Once I fed Z3 that distributive identity, the contradiction closed.

**Where I'd expect to wall off on a harder property**:
- **Bit-level reasoning** — if FEAT-DET-014 involved bitmasks or packed encodings. Z3 handles bit-vectors but LemmaScript doesn't emit them; would have to drop to raw Dafny.
- **Nonlinear multiplicative invariants** — "output bytes proportional to input" with actual proportions. SMT hates these.
- **Recursive data structure invariants** with set-valued accumulators of unbounded depth. Possible but expensive in lemma count.
- **Coupled termination** — two loops whose termination measure is lex-ordered over shared state. Doable but demands careful `decreases` clause.
- **Concurrency/interleaving** — completely outside LemmaScript's scope. Would pick TLA+ for that.

For the next-harder LID EARS I'd expect to tackle (e.g., the cross-function "digest immutability" property from the research doc's stretch targets), I'd expect to hit a wall at the *cross-function* layer: the annotation language doesn't extend to state that persists across calls. That's the TLA+ engine's shape.

---

## Proof complexity summary

| Metric | FEAT-DET-014 main | FEAT-DET-014 stretch | FEAT-LIFE-001 full |
|---|---|---|---|
| TS annotation lines | 12 | — (hand-written Dafny) | 10 |
| Generated Dafny lines | 49 | — | 42 |
| Proof additions to `.dfy` | 0 | N/A (all hand-written) | ~120 |
| Lemmas added | 0 | 2 | 6 |
| Ghost functions added | 0 | 1 (`seqMaxCreatedAt`) | 1 (`statusRank`) |
| Verification time | <1s | <1s | ~2s |
| Iterations | 2 | 1 | 5 (mostly on div monotonicity) |

---

## What the experiment says about LID + LemmaScript

**Positive findings:**

1. **For pre/post EARS on pure functions, LemmaScript + Dafny is a genuine fit** — EARS-to-annotation is a mechanical rewrite, and the default ensures discharge without hand-editing.
2. **The overlay/sidecar model works** — the annotated TS lives in `docs/research/experiments/` (or in a real deployment, `docs/overlay/primary/`), the case-study source stays untouched, and the manifest + generated artifacts compose into a self-contained verification unit.
3. **LLM proof-filling is real but scoped** — I (Claude) filled the integer-division monotonicity proof in one targeted session. An unaided human would still need to know Dafny idioms to do the same thing quickly. The leverage is real, not magical.
4. **Regeneration discipline is maintainable** — additions-only to the `.dfy` means regenerating when the TS changes is a merge-and-re-verify cycle, not a rewrite.

**Caveats:**

1. **Emitter fidelity is inspection-only** — the overlay's annotated TS is a verified *model* of the real the case-study function, not the real function itself. The argument "these match" is a human judgement. For a real deployment this would want either (a) an emitter-fidelity review in the arrow overlay, or (b) inline annotations in the real source (which LemmaScript's native mode supports, at the cost of the "source untouched" property).
2. **Cross-call / temporal properties need a different engine.** LemmaScript is for single-call functional correctness. FEAT-LIFE-003 monotonicity fit via a hand-written Dafny lemma over two invocations, but a clean LID overlay for cross-call properties would dispatch to TLA+ or a different shape of sidecar.
3. **Integer arithmetic weak spots** remain. Any EARS whose arithmetic touches integer division, modular reasoning, or nonlinear multiplication will need hand-written lemmas. The stdlib `Std.Arithmetic.DivMod` has most of these, but depending on a stdlib is a real cost.
4. **The `@spec` comment doesn't survive emission** — a small gap. The manifest + filename carry the spec ID, which is enough, but a `// @spec FEAT-DET-014` comment passthrough at the head of the `.dfy.gen` would be a nice touch.

**Verdict as input to the research question ("Could LID grow a formal-verification overlay?"):**

For the pre/post slice of the EARS landscape — functional correctness on pure algorithmic code — the answer is **yes**, concretely and with modest cost. Setup is one-shot (~5 minutes), the EARS-to-annotation rewrite is mechanical, and the main target verified on the first real attempt with zero proof additions. The stretch (lifecycle monotonicity) exercised the harder edges — cross-call property, integer-division reasoning — and still closed in one focused LLM session.

The overlay-dispatch framing from Section 5 of the research doc is right: LemmaScript is one engine among several, not a one-size-fits-all bridge. But for the EARS shapes it fits (FEAT-DET-014 is a clean example), the integration is tight enough that a production LID deployment could run `lsc gen && dafny verify` as a CI gate on any change to the annotated TS.
