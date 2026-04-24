# Experiment B5 Results — LemmaScript Stretch: Cross-Call Immutable-Digest Invariant

**Date:** 2026-04-22
**Experimenter:** Claude (Opus 4.7, 1M context) for Jess Szmajda
**Target property** (from the case-study codebase's LLD §"Retention Tiers > Key Properties"):

> **Immutable after generation.** Digests are generated once when an item crosses a tier boundary, then never changed.

Formally, for every `(itemId, groupId)` pair: once `item.groupDigests[groupId].shd` is written, no subsequent operation changes its `digest`, `tags`, or `generatedAt` fields. Same for `.lhd`. This is a cross-call temporal property, not a single-function pre/post.

**EARS/code linkage:** `FEAT-TIER-020` (short-horizon digest generation, `generateShortDigest`) and `FEAT-TIER-021` (long-horizon digest generation, `generateLongDigest`). Both functions already implement the immutability guard by checking the slot and returning `null` when set.

---

## Verdict

**The hypothesis from Wave 1 was wrong — but in an interesting and narrow way.**

Wave 1's concluding claim was that LemmaScript "doesn't reach cross-call temporal properties." Under the most direct reading — "a property relating two separate function calls cannot be expressed as a `//@ ensures`" — this is confirmed: Approach D (quantifying over results of a helper function inside an `ensures`) is genuinely blocked by Dafny's rule that expressions cannot invoke methods.

But a **reformulation trick lifts the wall**: compute the entire call trajectory INSIDE ONE FUNCTION, and quantify over indices of its output. Approach H does exactly this, captures the full `∀ i ≤ j, traj[i].set ⇒ traj[j] = traj[i]` cross-prefix immutability invariant in a single method postcondition, and verifies cleanly with **zero hand-written Dafny proof** (48 isolated VCs, all clean).

The tighter wall characterization is therefore: LemmaScript's `//@` annotations **can** express cross-call temporal properties **whenever the trajectory of interest can be computed within the function under verification**. They **cannot** express relationships between the *results of separate function invocations*, because LemmaScript emits `method` (not pure `function`) for most non-trivial definitions, and Dafny disallows method invocation inside expression contexts.

For this specific EARS, the trajectory IS computable in one function (it's a simple fold), so the temporal property was reachable. For genuinely distributed temporal properties — multiple actors, interleaved operations, liveness — the story would be different (see TLA+ section).

| Artifact | Dafny VCs (default) | Dafny VCs (`--isolate-assertions`) | Errors | Hand-written proof |
|---|---|---|---|---|
| `DIGEST-IMMUT.attempt-A.dfy` (per-call protocol) | 4 | — | 0 | none |
| `DIGEST-IMMUT.attempt-B.dfy` (disjunctive + 3-step composition) | 8 | — | 0 | none |
| `DIGEST-IMMUT.attempt-C.dfy` (fold + loop invariant) | 4 | — | 0 | none |
| `DIGEST-IMMUT.attempt-C2.dfy` (split fold) | 8 | — | 0 | none |
| `DIGEST-IMMUT.attempt-D.dfy` (quantify over prefix results) | — | — | **8 type errors** | — |
| `DIGEST-IMMUT.attempt-E.dfy` (recursive fold + hand proof) | 12 | 121 | 0 | ~70 lines |
| `DIGEST-IMMUT.attempt-F.dfy` (ghost state) | 3 | — | 0 | none |
| `DIGEST-IMMUT.attempt-G.dfy` (pairwise fold) | 4 | — | 0 | none |
| `DIGEST-IMMUT.attempt-H.dfy` (trajectory in output) | **4** | **48** | **0** | **none** |
| `DIGEST-IMMUT.hand-written.dfy` (richer data model + long-requires-short) | 21 | — | 0 | ~190 lines (all of it) |
| `DIGEST-IMMUT.negative-fixture.dfy` (regression check) | 1 | — | **2 (expected)** | — |
| **Winning artifact: attempt H** | **4** | **48** | **0** | **0** |

---

## Evaluation against §11.2 criteria

### 1. Expressiveness — does LemmaScript's `//@` annotation model reach cross-call properties?

**Score: YES, for the specific shape of "linear trajectory of operations on a single data structure."**

The trajectory reformulation in Approach H captures the full temporal invariant:

```
// In LemmaScript TS:
//@ ensures forall(i: nat, i < \result.length ==>
//@   forall(j: nat, i <= j && j < \result.length && \result[i].generatedAt !== 0
//@     ==> \result[j].generatedAt === \result[i].generatedAt))
```

This is **stronger** than per-call protocol (Approach A) and **equivalent to** the hand-written Dafny prefix-immutability lemma (`short_immutable_across_prefixes`). It's discharged without hand-written proof, purely from the loop invariant.

**The expressive limits are not about temporal reasoning per se — they are about:**
1. **Method-vs-function distinction.** LemmaScript emits `method` for anything with a `while` loop OR a `//@ ghost let` declaration. Methods can't be invoked in `ensures` expressions, which blocks Approach D. Workarounds: (a) use tail recursion (Approach E — emitter produces `function`, but needs hand proof), (b) internalize the trajectory (Approach H — stays a `method` but is self-contained).
2. **Single-variable quantifiers.** `forall(i: nat, j: nat, P)` does not parse. Must nest: `forall(i: nat, P1 ==> forall(j: nat, P2))`. Cosmetic but real.
3. **No standalone lemmas.** LemmaScript has no `//@ lemma foo` form. Each `//@ ensures` lives in a function signature. Inductive lemmas that should sit at top level (like `applyOps_append`) have no annotation form and must be written as hand-written Dafny below the gen line.
4. **Ghost state is per-function.** `//@ ghost let` works but creates a local ghost variable that does not persist across calls. There is no "shared ghost state" annotation.

**What this means for the engine-selection recommendation in §3:** LemmaScript's reach on cross-call properties depends on whether you can *fold the trajectory into a single function's output*. For most "invariant over a sequence of operations on a single aggregate" EARS — which is a common shape — yes, reachable. For "invariant relating operations on multiple independently-evolving aggregates" — maybe not, without escape-hatch to hand-written Dafny or TLA+.

### 2. Translation fidelity — A/B/C, hand-written Dafny, or TLA+?

**Answer: Approach H captured the property in pure LemmaScript. No escape-hatch needed for the core invariant.**

The EARS text reads: *"Immutable after generation. Digests are generated once when an entry crosses a tier boundary, then never changed."*

The Approach H postcondition:

```
ensures forall i, j: i <= j && j < |res| && res[i].generatedAt != 0
        ==> res[j] == res[i]
```

This is a line-by-line translation of "once set (`res[i].generatedAt != 0`), never changed (`res[j] == res[i]` for any later `j`)". No invention required.

The hand-written Dafny version is richer — it models the keyed (`itemId`, `groupId`) structure with both short-horizon and long-horizon slots, adds the long-horizon-requires-short-horizon hierarchy as a state invariant, and gives a more case-study-shaped data model. But the *core cross-call immutability claim* is the same shape as Approach H's. The hand-written version is not needed for the core claim; it's needed for **wider property stacking** (long-horizon-requires-short-horizon, hierarchy ordering).

Translation fidelity score: **mechanical for the headline property (Approach H); invention required for the stretch properties (hand-written).**

### 3. Source-untouched discipline

**Confirmed.** The case-study codebase was not modified for this experiment. `git status` shows only pre-existing unrelated changes on a separate branch. None of those are in the primary arrow or touch `processor.service.ts` or the primary LLD.

The experiment lives entirely under `/Users/jess/src/lid/docs/research/experiments/b5-lemmascript-immutable-digest/`. Its references to the real code shape are by inspection only (via `grep`), not by modifying source.

### 4. Coherence-stack fit — does this validate that different layers want different engines?

**Strongly yes — the three-way comparison (LemmaScript, hand-Dafny, TLA+) makes the engine-selection case crisply:**

| Engine | What it verified | Lines of spec/proof | Ceiling |
|---|---|---|---|
| LemmaScript (Approach H) | Core cross-call immutability over a fold | 63 lines TS, 0 hand proof | Single-function trajectory |
| Hand-written Dafny | Cross-call immutability + long-requires-short state invariant over keyed map | 190 lines Dafny, all hand-written | Richer data model + stackable invariants |
| TLA+ (sketch) | All of the above + liveness + multi-actor ordering | 30 lines TLA+, no proof work in the sketch | Protocol/state-machine shapes |

TLA+ expressed the same property in **one line** per field:

```tla
ShortImmutableStrong ==
    \A e \in Items, t \in Groups, x \in SlotType :
        [] (x # UNSET /\ groupDigests[e][t].shd = x =>
            [] (groupDigests[e][t].shd = x))
```

Compare to the ~140 lines of Dafny proof (5 core + 5 supporting lemmas) that establish the same property in `hand-written.dfy`. Ratio: **1:40** for specification. TLA+ is drastically more concise for this shape.

But TLA+ cannot verify a real TypeScript implementation — it verifies a hand-built model. Dafny + LemmaScript runs against the real code shape (modulo emitter-fidelity caveats), closing the artifact↔code coherence gate that TLA+ does not touch.

This is exactly what §4 of `formal-verification-exploration.md` predicted: **different layers want different engines**. For code-proximate verification of "sequence-of-ops over a single aggregate" cross-call invariants, **LemmaScript is now confirmed to reach via the trajectory reformulation.** For state-machine / multi-actor / liveness shapes, TLA+ is the native fit. Hand-written Dafny sits in between — implementation-proximate like LemmaScript, but able to handle richer data models and stack multiple invariants via state predicates.

### 5. Cost — iteration count, wall-clock, manual lemma effort

**Setup cost:** Zero. Dafny 4.11.0 and LemmaScript 0.x were already installed from Wave 1 (`/Users/jess/src/lid/docs/research/experiments/lemmascript-thr-det-014/node_modules`). Reused via symlink.

**Iteration count:** 12 distinct attempts — A, B, C, C2, D (blocked), E (needed hand proof), F, G, H-iter1 (parse error), H-iter2 (worked), hand-written, negative fixture. 15+ Dafny verification runs total.

**Wall-clock:** ~3.5 hours end-to-end — reading background docs + 12 experimental attempts + hand-written escape-hatch + TLA+ sketch + this writeup.

**Token cost:** Several hundred-thousand tokens for background reading, code generation, and writeup. Justified by the research goal of characterizing the wall precisely.

**Manual lemma effort breakdown:**
- Approach H (the winner): **0 lines of hand proof.** Pure LemmaScript annotations.
- Approach E (recursive form): ~70 lines of hand-written Dafny proof below the gen line (to close the inductive proof that the auto-generated empty lemma body couldn't).
- Hand-written Dafny: ~190 lines of pure Dafny. This is the full escape hatch — data model, operations, 10 lemmas, state invariant preservation.
- TLA+ sketch: ~30 lines of spec, not proven (no TLC run).

**Observation on effort distribution:** the *successful* LemmaScript approach (H) took ~15 minutes once the trajectory idea was in hand. The *blocked* approach (D) took ~10 minutes of trying to get Dafny to accept methods in expression context. The bulk of the time went to *exploring* the wall — figuring out that the emitter's method-vs-function distinction was the real constraint, not some intrinsic annotation-language limit.

### 6. Maintenance signal — if digest generation code changed, would the overlay catch a violation?

**Yes, concretely and at the precise call site that matters.**

Demonstrated via `DIGEST-IMMUT.negative-fixture.ts`:

```typescript
// BROKEN applyOp — unconditionally overwrites. Should fail verification.
export function applyOpBroken(current: DigestSlot, op: GenOp): DigestSlot {
  //@ requires op.now > 0
  //@ ensures current.generatedAt !== 0 ==> \result.generatedAt === current.generatedAt
  //@ ensures current.generatedAt !== 0 ==> \result.digest === current.digest
  return { generatedAt: op.now, digest: op.digest };  // no check — bug!
}
```

Dafny output:
```
DIGEST-IMMUT.negative-fixture.dfy(17,0): Error: a postcondition could not be proved on this return path
   Related location: ensures ((current.generatedAt != 0) ==> (applyOpBroken(current, op).generatedAt == current.generatedAt))
```

If a future refactor of `generateShortDigest` accidentally removes the `if (existingDigest) return null` guard (lines 827-835 of `processor.service.ts`), the overlay's equivalent annotated model would raise the identical error.

**Specific regressions the overlay would catch:**

| Change | What breaks | Specific error |
|---|---|---|
| Remove existing-digest guard | applyOp ensures fails | "postcondition could not be proved: if current was set, result equals current" |
| Change `generatedAt` to a mutable counter | loop invariant fails in applyOps | "loop invariant does not hold" |
| Change immutability to "re-generate if old" | postcondition H fails for `i < j, both set` case | "forall i, j... does not hold" |
| Add a third digest tier (PP?) | datatype mismatch in overlay; type error | "member 'pp' not found" (immediate break) |
| Change long-horizon to allow generation without short-horizon | long-requires-short state invariant fails | "invariant LongImpliesShort does not hold" (hand-written) |

The LemmaScript-side signal is *sharp*: the error points at the exact postcondition line that the code broke. This is substantially more precise than a failing integration test.

**Caveat:** The overlay verifies a *model*, not the real code directly. Emitter-fidelity assumption: the annotated TS's applyOp function has the same "check-then-write" shape as the real `generateShortDigest`. If the shape diverges (e.g., if generation starts *always* happening, with mutation guarded inside the write path instead of the read path), the overlay's model is no longer faithful. The test is then: does the overlay detect its own staleness? Partial — the `@spec` / filename linkage is a human-readable pointer, but the "is this still the right model" check is not automatic.

---

## Where does LemmaScript hit its wall? (headline question)

**Precise characterization of the wall:**

1. **Weakest claim (what Wave 1 said):** "LemmaScript doesn't reach cross-call properties."
   - **This claim is WRONG** as stated. Approach H reaches the cross-call immutability property in pure LemmaScript.

2. **Narrower claim (what's actually true):** "LemmaScript's `//@ ensures` cannot quantify over the results of other function invocations, because LemmaScript emits `method` (not `function`) for most non-trivial definitions, and Dafny disallows method invocation in expression contexts."
   - **This claim is correct.** Approach D failed on exactly this constraint.

3. **Engineering workarounds for claim #2:**
   - (a) Write the definition recursively (no loops, no ghost state) — emitter produces `function`. Works syntactically but the auto-generated `_ensures` lemma is empty, so non-trivial inductive proofs need hand-written additions. Approach E.
   - (b) Internalize the trajectory in the function under verification. Quantify over indices of its OWN output. Emitter stays at `method`, but you're not calling anything else from the `ensures`. Approach H. **This is the clean win.**
   - (c) Pairwise fold — take two sequences, prove the invariant over one concrete decomposition. Approach G. Works but requires a meta-argument that every trajectory decomposes this way.

4. **Still-genuinely-blocked cases:**
   - Properties relating operations on **multiple independently-evolving aggregates** (e.g., "whenever entry A's digest is set, no entry B's digest is ever changed either" — cross-actor, cross-state). Can't fold into a single trajectory.
   - **Liveness** properties ("every long-horizon digest eventually gets computed") — LemmaScript/Dafny is for safety.
   - Properties requiring **ghost state persistent across function-call boundaries** (e.g., an audit log shared by many functions). No annotation form exists.

**Engine-selection corollary:**

| Temporal property shape | LemmaScript reach | Default engine |
|---|---|---|
| Single-aggregate sequence-of-ops safety | REACHABLE via trajectory reformulation | LemmaScript (Approach H shape) |
| Cross-aggregate / multi-actor safety | unlikely — needs hand Dafny or TLA+ | hand Dafny for small N, TLA+ otherwise |
| Liveness / fairness | out of scope | TLA+ |
| Richer data-model invariants (long-requires-short etc.) | reachable via hand Dafny escape hatch | hand Dafny |

### Is this a LemmaScript limit or a Dafny limit?

**Mostly a LemmaScript limit, not a Dafny one.**

Dafny itself supports:
- Pure `function` definitions invokable from `ensures` — just need LemmaScript to emit `function` not `method`.
- Standalone `lemma` declarations — but no `//@` form exists to write them.
- Recursive functions with inductive ensures lemmas — works when LemmaScript emits a `function`, but the auto-gen lemma body is empty, so inductive proofs need hand additions.
- Ghost functions, ghost predicates, state-invariant preservation — all straightforward in raw Dafny, but no `//@` surface.
- Modules, class invariants, dynamic frames — all beyond LemmaScript's emitter.

The **emitter** is the constraint, not the prover. Enriching LemmaScript with `//@ lemma` forms, a `//@ pure` annotation that forces `function` emission, and top-level `//@ ghost predicate`/`//@ ghost function` declarations would eliminate most of the workarounds observed in this experiment.

### Does TLA+ fit this natively?

**Yes — one line per field vs. ~140 lines of Dafny proof.** See `DIGEST-IMMUT.tla-sketch.tla`.

The temporal-logic form `[] (P => [] P)` is LITERALLY the meaning of "once set, never changed". TLA+'s state-machine reasoning is first-class — prefix bookkeeping, composition lemmas, and the inductive step structure that hand-written Dafny needs ~5 supporting lemmas to establish, fall out of TLC's `Spec = Init /\ [][Next]_vars` pattern for free.

Ratio:
- **TLA+:** ~30 lines for the entire module (header + state + init + next + 5 property definitions), one line per property.
- **Hand-written Dafny:** ~190 lines for the comparable model, with ~140 of them being proof.
- **LemmaScript (Approach H):** ~65 lines of TS for the headline property only, zero hand proof.

**TLA+ is the right engine for full-shape temporal safety on state-machine models.** LemmaScript is the right engine for code-proximate verification when the trajectory folds into a single function. Hand-written Dafny is the bridge — implementation-proximate like LemmaScript but able to handle richer data models with stackable invariants.

This directly validates the §3 engine-landscape table in `formal-verification-exploration.md`: *different engines live at different altitudes*. Our experiment didn't demonstrate that TLA+ is "better" than LemmaScript; it demonstrated that **for this property**, both fit, with TLA+ winning on spec conciseness and LemmaScript winning on source-proximity and maintenance signal on real code drift.

---

## Artifacts produced

```
DIGEST-IMMUT.attempt-A.ts       # per-call protocol only
DIGEST-IMMUT.attempt-A.dfy.gen  # generated Dafny
DIGEST-IMMUT.attempt-A.dfy      # source of truth (identical to gen)
DIGEST-IMMUT.attempt-B.ts       # disjunctive postcondition + N-step composition
DIGEST-IMMUT.attempt-B.dfy.gen
DIGEST-IMMUT.attempt-B.dfy
DIGEST-IMMUT.attempt-C.ts       # fold over seq<Op> with loop invariant (from-start claim)
DIGEST-IMMUT.attempt-C.dfy.gen
DIGEST-IMMUT.attempt-C.dfy
DIGEST-IMMUT.attempt-C2.ts      # two-phase fold (from-any-intermediate claim)
DIGEST-IMMUT.attempt-C2.dfy.gen
DIGEST-IMMUT.attempt-C2.dfy
DIGEST-IMMUT.attempt-D.ts       # quantify over prefix results in ensures — BLOCKED
DIGEST-IMMUT.attempt-D.dfy.gen
DIGEST-IMMUT.attempt-D.dfy
DIGEST-IMMUT.attempt-E.ts       # recursive fold + hand-written Dafny proof
DIGEST-IMMUT.attempt-E.dfy.gen
DIGEST-IMMUT.attempt-E.dfy      # includes ~70 lines of hand proof
DIGEST-IMMUT.attempt-F.ts       # ghost state (downgrades to method)
DIGEST-IMMUT.attempt-F.dfy.gen
DIGEST-IMMUT.attempt-F.dfy
DIGEST-IMMUT.attempt-G.ts       # pairwise two-sequence fold
DIGEST-IMMUT.attempt-G.dfy.gen
DIGEST-IMMUT.attempt-G.dfy
DIGEST-IMMUT.attempt-H.ts       # trajectory in output — THE WINNER
DIGEST-IMMUT.attempt-H.dfy.gen
DIGEST-IMMUT.attempt-H.dfy
DIGEST-IMMUT.hand-written.dfy   # full escape hatch: richer model, long-requires-short
DIGEST-IMMUT.tla-sketch.tla     # TLA+ spec for engine-comparison purposes
DIGEST-IMMUT.negative-fixture.ts # regression-catch demonstration
DIGEST-IMMUT.negative-fixture.dfy.gen
DIGEST-IMMUT.negative-fixture.dfy
DIGEST-IMMUT.overlay.yaml       # schema-v0.2 manifest
attempts-log.md                 # chronological attempts log
RESULTS.md                      # this file
attempt-*.log                   # per-iteration Dafny + lsc output
```

Node dependencies linked from `../lemmascript-thr-det-014/node_modules/`.

---

## What this experiment says about LID + LemmaScript + cross-call properties

**Positive findings:**

1. **Cross-call temporal properties ARE reachable from pure LemmaScript** via the trajectory-in-output reformulation (Approach H). Previous hypothesis needs updating — LemmaScript's wall is narrower than "no cross-call." It's "no quantification over other function-call results from inside an expression context" — which has a clean workaround for single-aggregate properties.

2. **Approach H verified with zero hand-written proof.** 48 isolated VCs, all clean. This is the first demonstration in the LID experiment series that a *universally quantified* cross-call temporal invariant is discharged end-to-end by SMT without manual proof additions.

3. **The overlay/sidecar pattern scales cleanly.** Multiple approaches (A-H) coexist in the same directory, each with `.ts`, `.dfy.gen`, `.dfy`, log. Per-attempt verification is fast (<1s Dafny wall-clock). No source modifications. Three-way merge for regeneration works as before.

4. **Negative fixtures demonstrate maintenance signal.** A deliberately broken `applyOp` fails verification with a pointed error at the exact postcondition that was violated. This is the expected CI-hook behavior.

**Caveats:**

1. **Emitter-fidelity assumption is load-bearing.** The annotated TS models a "check-then-write" fold; the real code has the check inside `generateShortDigest` and the write happens in a runner. These have the same *logical shape* (no write unless unset) but diverge on code structure. If the real code's check-pattern changes (e.g., moves to a different guard or becomes implicit via DDB conditional writes), the overlay's model might no longer match without someone noticing. Human inspection is still the validator of emitter fidelity.

2. **The trajectory reformulation is elegant but not "universal."** It works when the property is "invariant over a sequence of operations on a single aggregate." Properties like "whenever item A's short-horizon digest is set, item B's long-horizon digest was not changed in any subsequent operation" — relating two distinct aggregates — cannot be folded into a single trajectory without loss.

3. **LemmaScript has real ergonomic gaps uncovered by this experiment:**
   - `forall(a, b, P)` with two variables doesn't parse
   - `//@ ghost let` downgrades the function to a `method`
   - No `//@ lemma` form for standalone proofs
   - Auto-generated `_ensures` lemma body is empty; non-trivial inductive proofs need hand-written Dafny below the gen line

4. **TLA+ remains the engine of choice for protocol shapes.** For this experiment, TLA+ was a reference sketch — we didn't run TLC because nothing about the property needs model-checking. But if the property were "digests are generated concurrently by two actors and conflict resolution yields a canonical digest," TLA+ would be decisive and LemmaScript would not fit.

**Verdict as input to the research program:**

For the LID coherence stack — specifically §11.2's question "where does LemmaScript's wall sit" — the answer from this experiment is:

- **The wall is at the emitter, not the prover.** Dafny can verify everything LemmaScript can't express; the `//@` annotation language simply doesn't cover Dafny's whole surface.
- **For the class of cross-call temporal invariants that fold into a single-function trajectory**, LemmaScript reaches clean verification with zero hand proof.
- **For richer data-model invariants** (long-requires-short as a stackable state invariant, keyed aggregates, conditional-on-slot preconditions), the hand-written Dafny escape hatch is straightforward and reuses the same Dafny toolchain.
- **For state-machine / liveness / protocol** properties, TLA+ is the right dispatch target, and the one-line-vs-140-lines ratio for this property's spec demonstrates the architectural case.

The §3 engine-selection recommendation stands, with one update: **LemmaScript's cross-call reach is better than previously advertised, conditional on a reformulation trick the user needs to know.** That trick (trajectory-in-output) deserves to be documented in LemmaScript's SPEC.md as the canonical pattern for sequence-of-ops temporal invariants.

---

## Followups / future work (not in scope here)

- Propose to LemmaScript upstream: `//@ lemma` form for standalone inductive lemmas; `//@ pure` annotation to force `function` emission; two-variable `forall(a, b, P)` parsing; `//@ ghost predicate` for top-level state invariants.
- If LID adopts the trajectory pattern as canonical: document in `docs/overlay/README.md` (or wherever the engine-dispatch recommendations live) with Approach H as the reference exemplar.
- Run TLC on the TLA+ sketch (needs `brew install tla+`; ~2 min) to confirm `GEImmutableStrong` and `LPImpliesGE` check under TLC's bounded model. This would add a fourth data point and is ~30 min of work.
- Repeat the experiment for a genuinely multi-aggregate temporal property (e.g., "long-horizon digest must come *temporally* after its corresponding short-horizon digest" across multiple items) to probe where the trajectory-reformulation trick runs out. This is the natural next stretch.
