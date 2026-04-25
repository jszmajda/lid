# Formal Verification Overlay for LID — Exploration

**Status**: Exploration / not adopted. Research notes, not a decision.
**Date**: 2026-04-22 (v3 — multi-layer coherence + provenance substrate)

## 0. Background and prerequisites

This document is written against several pieces of context that live outside it. Readers landing here fresh can use this section as a pointer sheet.

**LID (Linked-Intent Development)** is the methodology this repo documents. It treats code as compiled output and *intent* as the authoritative artifact, with intent structured as a one-way chain: `HLD → LLDs → EARS → Tests → Code`. For the full framing, see `/Users/jess/src/lid/docs/high-level-design.md`.

- **HLD** (high-level design) — one project-level document (problem, approach, architecture). Lives at `docs/high-level-design.md`.
- **LLD** (low-level design) — component-level design documents, one per intent component. Live in `docs/llds/`.
- **EARS** (Easy Approach to Requirements Syntax) — a format for single-line, uniquely-IDed requirements, optimized for `grep`-based traversal. IDs take the shape `{FEATURE}-{TYPE}-{NNN}` (e.g. `AUTH-LOGIN-003`). Four canonical patterns: ubiquitous ("shall X"), event-driven ("when E, shall X"), state-driven ("while S, shall X"), unwanted ("if U, shall X"). Live in `docs/specs/`.
- **`@spec` annotation** — a code comment (e.g. `// @spec AUTH-UI-001, AUTH-UI-002`) placed at the entry point of a behavior's implementation graph, linking code (or a test) to one or more EARS IDs. The authoritative pointer from implementation up to intent.
- **Arrow** — the unidirectional chain HLD → LLDs → EARS → Tests → Code. An **arrow segment** is the territory owned by one LLD (its specs, tests, code); segments are defined by EARS `{FEATURE}` prefix. `docs/arrows/` and `docs/arrows/index.yaml` belong to an optional navigation overlay (the `arrow-maintenance` plugin).
- **Cascade discipline** — the existing LID rule: when one level of the arrow changes, downstream levels update in the same session. Within a segment, cascade is free; across segment boundaries, the agent pauses and verifies before propagating.
- **Status markers** (existing on EARS) — `[x]` implemented, `[ ]` active gap, `[D]` deferred. This document proposes verification markers (`[V] [Vp] [Vx] [Vn] [?]`) that *compose* with the EARS markers — e.g. `[x][V]` = implemented and verified.

**The case-study codebase** is a separate, real project the experiments run against — a long-running LID user with a populated arrow, kept anonymous in this published write-up. Throughout this doc, `FEAT-*` and `FLT-*` EARS IDs (e.g. `FEAT-DET-018`, `FEAT-LIFE-001`, `FEAT-DATA-001`, `FEAT-NAR-003`, `FLT-SCORE-001`) belong to the case-study's specs; generic paths like `<case-study>/docs/llds/FEAT.md`, `<case-study>/docs/specs/FEAT.md`, and generic source paths referenced below all live in the case-study's repo, not in this one. EARS prefix decoder: `DET` = daily/weekly classification, `LIFE` = lifecycle, `DATA` = data shape, `NAR` = narrative/LLM-shaped, `TIER` = retention-tier invariants, `FLT` = agent-filter processing.

**External references used here**:

- [**LemmaScript**](https://github.com/midspiral/LemmaScript) — an SMT-backed prover for TypeScript (Dafny + Z3 under the hood) with LLM proof-filling. Case studies cited in this doc (`hono`, `node-casbin`, `equality-game`, `charmchat`) are drawn from its repository and our experiment run in `docs/research/experiments/lemmascript-thr-det-014/`. "SMT-backed" means the prover discharges verification conditions via an SMT solver (here, Z3).
- **Basilisk** (OSDI 2025; Zhang, Chajed, Kapritsos, Parno) — a distributed-protocol verification tool. It synthesizes inductive invariants by decomposing a complex global invariant into many simple local *provenance* invariants, and augments hosts with an append-only log so invariants can quantify over history. LID is not a distributed protocol; what we take from Basilisk here is the *framing*, not the algorithm. See §5.
- **CodeQL / Semgrep Pro** — code-as-a-database query engines from GitHub and Semgrep respectively. Used in this doc for structural / dataflow / reachability invariants.
- **Dafny, Why3, TLA+, Alloy, Lean, Coq, F\*, Liquid Haskell** — a family of verification-adjacent tools with different reach (pre/post contracts, model-checked state machines, interactive theorem provers, refinement types). They appear in the engine table (§3) without deep discussion.
- **Differential re-interpretation / A/B round-trip** — the practice of having an LLM regenerate a downstream artifact from an upstream one (A direction) *and* a reconstructed upstream from the real downstream (B direction), then comparing each against ground truth. A- and B-side diffs surface translation drift that a formal checker cannot see. Defined in detail at §4; used in experiments B1 and B2.
- **Test-witness** — a bespoke pattern introduced by this research, not a product: a test file paired with a YAML contract that asserts the test's scenarios and assertions correspond to a specific EARS. The contract is what makes "we have a test" into "this test verifies this requirement."
- **MC/DC** — Modified Condition/Decision Coverage, a coverage metric from aviation software (DO-178C) that requires each condition in a boolean decision to independently influence the outcome. Used here to reason about arm-flipping negation tests for conjunctive EARS.
- **VC** — *verification condition*, the unit of proof obligation a prover discharges (e.g. "753 VCs" means the prover discharged 753 such obligations).
- **DDB** — DynamoDB. The case-study uses DynamoDB; `list_append`-only update expressions are a structural property we verify for FEAT-DET-018.

### 0.1 Provenance of this document

This file is the working synthesis from an exploratory research session on 2026-04-22. It grew across many turns; earlier drafts framed the problem more narrowly (as "translate EARS to machine-checked obligations"). The current framing — multi-layer coherence across HLD → LLDs → EARS → Code, with formal verification as one of several complementary engines — emerged mid-session when a differential-re-interpretation hypothesis was added.

Three experiment sweeps feed §11:

- **Wave 1** — three experiments (CodeQL on FEAT-DET-018, test-witness on FEAT-DET-021, LemmaScript/Dafny on FEAT-DET-014 + FEAT-LIFE-001..003) proving the EARS-shape-dispatched formal overlay works end-to-end. Writeups under `docs/research/experiments/{codeql-thr-det-018, test-witness-thr-det-021, lemmascript-thr-det-014}/RESULTS.md`.
- **Wave 2** — seven follow-up experiments (B1–B7) stress-testing the architecture along other dimensions (differential round-trip, inductive maintenance, scale, adversarial CodeQL, git-provenance). Writeups under `docs/research/experiments/b{1..7}-*/RESULTS.md`.
- **Wave 3** — two experiments (B8 blind re-authoring audit; B9 bidirectional differential on the filter arrow with 6 fresh EARS across three complexity tiers) testing refinements that Wave 2 surfaced. Writeups under `docs/research/experiments/{b8-blind-reauthoring, b9-bidirectional-differential-filter}/RESULTS.md`.

When the body of this doc says "our first experiment," "Wave 2 cross-cutting findings," "§11.1 said X but B5 refutes," "Wave 3 upgraded differential from advisory to co-gate," etc., those refer to the experiments above. Some residual session-scoped phrasing ("this session," "the earlier framing") remains — treat them as referring to this document's own drafting history, not to a conversation the reader has access to.

## 1. The goal — multi-layer coherence

Could LID grow a layer that verifies **intent has actually made it into implementation** — and that the implementation's behavior still matches that intent as both evolve?

An earlier draft of this document framed the question more narrowly as "translate EARS to machine-checked obligations." That framing was too narrow. Intent doesn't live only in EARS. It passes through a chain:

```
Human intent → HLD → LLDs → EARS → Code + Tests
            (1)   (2)    (3)    (4)
```

Each junction has its own coherence question, and each junction is where drift can occur:

- (1) **Intent → HLD**: did the human write down what they actually meant?
- (2) **HLD → LLDs**: do the LLDs collectively address the HLD's concerns? Orphan LLDs? Gaps?
- (3) **LLDs → EARS**: do the EARS faithfully derive from the LLDs' design commitments? Does every design decision have an EARS? Does every EARS have a motivating LLD section?
- (4) **EARS → Code/Tests**: does the code actually satisfy what the EARS says?

A formal verification *overlay* (in the sense explored in this document) addresses only one slice of gate (4). That's still valuable — but we should be honest about scope. The goal is multi-layer coherence, and different layers want different verification engines.

## 2. Why EARS ↔ code coherence is mechanically approachable

EARS patterns map nearly mechanically to temporal-logic operators:

| EARS pattern | Temporal logic |
|---|---|
| Ubiquitous ("shall X") | `□ X` |
| Event-driven ("when E, shall X") | `□ (E → ◇ X)` |
| State-driven ("while S, shall X") | `□ (S → X)` |
| Unwanted ("if U, shall X") | `□ (U → X)` |

This isn't coincidental. EARS was designed to eliminate the same ambiguities formal methods care about. LID has accidentally been building the human-friendly front-end formal methods has always lacked. Authoring a verification obligation from scratch is hard; authoring one from existing EARS is a translation problem.

## 3. The engine landscape — classes, not tools

Different engines live at different altitudes and verify different shapes. To avoid overrotating on specific tools (especially LemmaScript, which only covers TypeScript), the table below names engines by **class** with per-language instances. The architecture's claims depend on the class; the tool is an implementation choice per codebase.

| Engine class | What it verifies | Invasive? | Representative instances |
|---|---|---|---|
| **Structural / dataflow query** | AST patterns, call graphs, reachability, taint | Overlay | CodeQL (polyglot), Semgrep / Semgrep Pro (polyglot), Infer, Error Prone (Java), Clang SA (C/C++), go vet / staticcheck (Go), custom ts-morph / typescript-eslint rules |
| **Test-witness** | Behavioral scenario via test runner + contract | Overlay | Language-agnostic (any test runner — Vitest, Jest, pytest, go test, JUnit) |
| **SMT-backed contract prover** | Pre/post conditions, invariants on pure fragments | Inline or overlay sidecar | LemmaScript → Dafny (TS); Verus, Creusot, Prusti, Kani (Rust); Frama-C + ACSL (C); OpenJML, KeY (Java); SPARK (Ada); F\* (F#/ML); Gobra (Go); CrossHair (Python) |
| **State-machine / protocol checker** | Safety/liveness over a model | Sidecar | TLA+, Alloy, Promela/SPIN, P, mCRL2 (all language-agnostic — you model the system) |
| **Full proof assistant** | Arbitrary theorems — crypto, PL, heavy math | Sidecar | Lean 4, Coq, Isabelle/HOL, Agda, F\*, Idris |
| **Refinement-type native** | Predicates encoded in the type system | Inline (language-native) | Liquid Haskell, Stainless (Scala), F\*, refinement-F# |
| **Type-system native** | Baseline type checking | Inline (language-native) | tsc, mypy, rustc, javac, go build — any statically-typed language |
| **Runtime contracts / validators** | Boundary enforcement at ingress/egress | Inline at boundaries | io-ts / zod / typia (TS), pydantic (Python), bean validation (Java), clojure.spec, Racket contracts |
| **Differential re-interpretation** | Translation fidelity at any layer, bidirectionally | Overlay (generative) | Language-agnostic (LLM A/B round-trip over prose or code) |
| **Blind re-authoring audit** | Whether existing formal artifacts encode code-sourced constraints EARS doesn't mandate | Overlay (generative) | Language-agnostic (fresh LLM session given EARS only, no code) |
| **Git-provenance** | Correlation of EARS edits with code edits over history | Overlay (advisory) | Language-agnostic (git log + `@spec` grep) |
| **Manual review signoff** | Qualitative claims a machine can't reach | Overlay | Language-agnostic |

Several observations that matter for the architecture:

- **Most classes are language-agnostic or polyglot.** Only three are deeply language-specific: SMT-backed contract provers, refinement types, type-system native. This means the overlay architecture ports beyond TypeScript more easily than LemmaScript alone suggests.
- **The LLM-proof-filling economics vary across the contract-prover row.** Dafny (LemmaScript's backend) has the strongest LLM support today; F\* is growing; Lean is improving; Ada/C/Java provers are mature tools with weak LLM support. When you see "SMT-backed contract prover" in the rest of this doc, the strength claim is highest for TS/Dafny and weakest for C/Java.
- **Per-arrow, per-layer engine profile.** Not universal. Not one prover. (The obvious counter — "wouldn't a single formal backend be simpler?" — fails because artifacts at each layer and in each codebase have different shapes; a single backend forces every property into its expressible fragment and strands everything else. Dispatching on shape preserves reach.)

## 4. The coherence stack — formal scales down, differential scales up

Once coherence is framed as a chain of gates, engine effectiveness is asymmetric along the stack:

| Gate | Formal-overlay reach | Differential reach |
|---|---|---|
| (1) Intent ↔ HLD | Very weak | Moderate (user-in-loop) |
| (2) HLD ↔ LLDs | Weak (too narrative) | Strong |
| (3) LLDs ↔ EARS | Medium (structural extraction) | Strong |
| (4) EARS ↔ Code | Strong | Strong |

**Formal verification scales down the stack; differential re-interpretation scales up.** This isn't a flaw — it's the architectural recommendation. The asymmetry follows from artifact shape:

- At the **code-proximate** end, artifacts are near-formal (EARS) or fully formal (code). Formal engines (CodeQL, LemmaScript, test-witness contracts) are rigorous, deterministic, regression-resistant.
- At the **narrative end**, artifacts are prose-rich (LLDs, HLDs). LLMs read and write prose fluently, so LLM-based differential round-trip is tractable there — but its output is probabilistic (a diff to review), not pass/fail. Differential cannot be a gate precisely because of this non-determinism (§10).

The two approaches are complementary:

- **Formal overlay** mechanically enforces that code matches a formal artifact. Silent about whether the artifact is a faithful translation of upstream intent.
- **Differential re-interpretation** surfaces translation drift by round-tripping (forward: upstream → generated downstream; reverse: real downstream → reconstructed upstream). Silent about whether the resulting property is actually preserved.

Together they close the intent-coherence loop at every gate.

### Three natural workflow patterns

**Pattern 1 — Bootstrap** (differential first, formal second). Run A/B round-trip on EARS + code. Where it drifts, either update the upstream (surface hidden property), update the downstream, or write a formal overlay artifact to lock the now-explicit property. Differential expands coverage; formal locks it in.

**Pattern 2 — Audit** (formal first, differential as auditor). Write formal artifacts where shape fits. Periodically run differential as coverage audit: does the reconstructed upstream mention properties the formal overlay doesn't enforce? Gaps become candidate new artifacts.

**Pattern 3 — Continuous round-trip**. On every change, both run. Formal blocks CI on regression (deterministic). Differential produces review comments (probabilistic). They occupy different stages of the loop.

## 5. Provenance as substrate — a Basilisk-inspired framing

Basilisk (OSDI 2025; Zhang, Chajed, Kapritsos, Parno; see §0) automatically finds inductive invariants for distributed protocols by decomposing one complex global invariant into many simple local *provenance invariants* — each tracing "why is this state the way it is" back through protocol steps and messages. The technique doesn't port directly (LID isn't a distributed protocol), but the **framing** is exactly right for multi-layer coherence:

> Complex global coherence ("intent is preserved through implementation") = conjunction of many simple local provenance invariants, each tracking one layer's derivation from the layer above it, collectively inductive over every change.

Four implications for LID:

### 5.1 Provenance as the native structure

Every artifact at every layer should know *why it exists* — which upstream thing caused it. LID already has the forward half (`@spec {ID}` annotations pointing code → EARS; see §0). What's missing is the **reverse half** — each EARS knowing which LLD section motivated it; each LLD knowing which HLD concern it addresses. A simple frontmatter field (YAML at the top of the markdown file, or per-spec/per-section) is enough:

```yaml
# docs/specs/FEAT.md header (per-EARS or per-section)
FEAT-DET-021:
  derives_from:
    - doc: docs/llds/FEAT.md
      section: "Processing Architecture > Daily classification > Escalation heuristic"
```

With the reverse half populated, the overlay becomes a **provenance graph**, and orphan detection at every layer becomes mechanical:
- An EARS with no `derives_from:` — design decision that skipped the LLD, or a misplaced requirement
- An LLD section with no EARS pointing back — design commitment that wasn't pinned to a verifiable requirement
- A `@spec` pointer with no matching EARS — code written against deleted/renamed intent

**`derives_from:` is optional, and its value scales with project size.** For small projects (single-LLD or few-LLD; low EARS count) an LLM can collate LLD + EARS into one context window and do this reasoning on demand — no explicit annotation needed. The ROI of populating `derives_from:` kicks in when (a) the project has many LLDs, (b) the LLD count makes single-context-window collation unreliable, or (c) orphan checks need to run mechanically (CI hook, not per-run LLM call). A good rule of thumb: stay in-context up to roughly the size where the case-study sits today (~1 LLD, ~50 EARS). Populate `derives_from:` once the project grows past that, ideally via a one-time LLM backfill pass rather than hand-authored. Git-provenance (§5.4) already gives you forward traceability without `derives_from:`; the explicit field is a *reverse* link whose cost/value case gets stronger as you scale.

### 5.2 Coherence invariants as a conjunction of simple local checks

Instead of trying to state "intent is preserved" as one global property, state it as many simple local provenance invariants:

- Every `@spec ID` in code has a matching EARS with that ID
- Every EARS has a `derives_from:` pointing at a real LLD section
- Every LLD section referenced by EARS exists
- Every LLD cross-reference points at a real LLD
- Every EARS change in a given commit is accompanied by `@spec`-referenced code change in the same or adjacent commit (history-preservation; see §5.4)

Each individual check is trivial. The conjunction is what gives coherence its teeth. This is Basilisk's "many simple local provenance invariants" pattern transferred to a documentation graph.

### 5.3 Inductive maintenance over diffs

Basilisk's invariants aren't just true once — they're preserved by every protocol step. The LID analog: coherence invariants should be preserved by every **change**. A single commit that breaks coherence is a violated inductive step. This reframes what a CI hook actually is: not just "run some checks," but "verify coherence invariants still hold after this diff."

### 5.4 Git as history-preservation substrate

Basilisk augments hosts with an append-only log of past states so invariants can quantify over history. We have git for free. "This EARS changed at commit X; did the `@spec`-referenced code change at X or within ±N commits?" is a provenance query over git log. Drift across history — "the EARS changed three months ago and the code never followed" — becomes visible without any new tooling. This is nearly free to enable and nobody does it systematically today.

### 5.5 Coherence shards

Basilisk identifies *shards* — groups of variables always updated atomically. The LID analog: EARS that always change together because they derive from the same LLD claim. With `derives_from:` populated, shards fall out of the graph automatically. When one EARS in a shard changes without its siblings, flag for review. This is what the existing cascade discipline is trying to capture; provenance makes it mechanical.

## 6. LemmaScript as one engine in the family

[LemmaScript](https://github.com/midspiral/LemmaScript) (see §0) is a concrete existence proof that EARS-shaped intent can be verified by an SMT-backed prover with LLM proof-filling. Its published case studies (sourced from its repository, not re-verified here):

- **hono** (the web framework): two real CVEs verified in-place (CVE-2026-39409, CVE-2026-39410), 51 Dafny lemmas.
- **node-casbin**: brownfield, 5 functions verified, 217 existing tests still pass.
- **equality-game**: sound + complete decision procedure for arithmetic equality. 753 verification conditions (VCs), 0 errors, 0 `assume`s, 0 axioms.
- **charmchat**: Kahn's topological-sort algorithm — memory safety, output bounds, completeness. 736 VCs.

In the overlay model LemmaScript is **one engine**, used for EARS that fit a pre/post shape on a pure-fragment function. The overlay adaptation is small: store annotated TS in an overlay sidecar (using LemmaScript's `//@ requires / ensures / invariant` comment syntax on a copy of the TS) rather than inlined in source, let the toolchain compose at check time. Source stays untouched — the motivation is decoupling LID's artifacts from language-native toolchains, so the overlay can be removed or swapped without rewriting source.

- **Effective for**: invariant preservation, pure algorithm correctness, arithmetic identities, state-machine transition functions.
- **Not for**: concurrency, effects, async, structural flow across many functions (CodeQL fits better), scenario-shaped behavioral specs (test-witness fits better), qualitative EARS (unverifiable `[Vn]`).

## 7. The overlay-dispatch model

### EARS-shape → default engine

Examples below reference case-study specs (see §0). "LLM-shaped / qualitative" means an EARS whose subject is an LLM's output quality (vocabulary, tone, narrative faithfulness) — structurally unverifiable by a formal checker, marked `[Vn]` (not a verification candidate).

| EARS shape | Example (case-study) | Default engine |
|---|---|---|
| Structural / flow invariant | FEAT-DET-018 "never remove existing group assignments" | CodeQL |
| Behavioral / scenario | FEAT-DET-021 "zero daily assignments ⇒ escalate to weekly" | Test-witness |
| Functional / pre-post | FEAT-DET-014 "itemCount incremented by N, lastItemAt = max..." | LemmaScript/Dafny |
| Configuration / data-shape | FEAT-DATA-001 "stores records with these fields" | Type-system-native |
| LLM-shaped / qualitative | FEAT-NAR-003 "preserve exact vocabulary" | `[Vn]` (or manual-review signoff) |

The overlay *dispatches* on shape; it doesn't force everything through one engine. **One EARS may dispatch to multiple engines** — demonstrated by the Wave 1 CodeQL experiment (see §11.1), where FEAT-DET-018 needed both CodeQL (code-side) and a pre-existing unit test (prompt-side) to cover both halves of the EARS.

### Overlay tree

```
docs/specs/FEAT.md                    ← EARS (unchanged)
docs/llds/FEAT.md                     ← LLD (unchanged)
docs/arrows/FEAT.md                   ← arrow graph (unchanged)
docs/overlay/primary/
  FEAT-LIFE-001.overlay.yaml          ← per-spec manifest
  FEAT-DET-018.codeql                 ← CodeQL query
  FEAT-DET-018.test-witness.yaml      ← (intra-spec 2nd engine)
  FEAT-DET-014.annotated.ts           ← LemmaScript sidecar
  FEAT-DET-021.test-witness.yaml      ← test contract
  FEAT-DET-021.differential.md        ← differential round-trip record
  _status.yaml                        ← roll-up across the arrow
```

### Manifest schema v0.2 (post-experiment)

```yaml
spec_id: FEAT-DET-021
arrow: primary
derives_from:
  - doc: docs/llds/FEAT.md
    section: "Processing Architecture > Daily classification"
engines:                                       # list — intra-spec dispatch
  - engine: test-witness
    artifact: FEAT-DET-021.test-witness.yaml
    status: V
  - engine: differential
    artifact: FEAT-DET-021.differential.md
    status: Vp
targets:
  - type: function
    selector: "runner.ts::runDailyClassification"
witnesses:
  - path: "runner.test.ts"
    describes: "daily-to-weekly escalation"
limitations:                                    # new in v0.2
  - "mock fidelity — real classification may diverge"
  - "structural assertion matching, not semantic equivalence"
status: V                                       # or Vp, Vx, Vn, ?
last_run:
  timestamp: 2026-04-22T14:38:00Z
  result: verified
  hash: ...
```

Schema changes from v0.1 (the unwritten "one engine per EARS, no provenance" baseline this work started from):
- `engines:` is a list (one EARS → many engines)
- `derives_from:` populated (provenance graph)
- `limitations:` field (engines carve out their own blind spots)
- Detector patterns in engine-specific artifacts should be scope-aware (from test-witness experiment learnings)

### Status markers

- `[V]` verified end-to-end
- `[Vp]` verification in progress (obligations remain, known plan)
- `[Vx]` attempt stuck (blocker documented)
- `[Vn]` not a verification candidate (LLM-shaped / qualitative)
- `[?]` not yet classified

Compose with EARS markers: `[x][V]` = implemented and verified, `[x][?]` = implemented but unverified.

### Differential / blind-audit classification codes (engine-specific)

Used by the differential and blind-reauthoring engines as their `last_run.result` payload. Per an EARS's bidirectional-differential audit (see Appendix I):

- **BD-COHERENT** — neither the A-direction diff nor the B-direction diff surfaces anything material; EARS and code are mutually coherent for this property.
- **A-ONLY-DRIFT** — A-diff surfaces drift; B-diff doesn't. EARS under-specifies an implementation detail the code has but doesn't really need to pin.
- **B-ONLY-DRIFT** — B-diff surfaces drift; A-diff doesn't. Code has unstated constraints the EARS should state.
- **BIDIRECTIONAL-DRIFT (BD-DRIFT)** — both directions surface the same/related gap. Strong drift evidence; reconcile EARS or code before promoting.
- **INCONSISTENT-BLIND** — runs within a direction disagree too much to classify. Re-run with refined prompts before acting.

These codes are advisory in `last_run.result` but feed the gate rule documented in §11.5.

### Cascade discipline extends naturally

When an EARS changes, LID's existing cascade rule (see §0) extends by one step: re-run the overlay engine(s). Same operator, new node type. CI hook: `@spec` ID appears in a diff → dispatcher re-runs the relevant engine → result updates `_status.yaml` (the per-arrow rollup defined in Appendix F).

## 8. Packaging — new optional skill, not baked into core

Earlier drafts of this document argued against packaging the overlay as its own plugin, citing LID's minimum-surface discipline. That framing was wrong. Minimum-surface says *don't grow surface without earning it*, not *never grow surface*. This work has earned a surface — seven experiments, a working dispatcher, schema through v0.3, concrete real-world recommendations — and it is a **deeper level of alignment than mainstream LID needs**. Most LID projects (CRUD apps, typical SaaS, marketing sites) will correctly never adopt it.

The right packaging: a **new optional plugin**, sibling to `arrow-maintenance`, installed only by projects that want overlay-level verification. Call it (candidate names): `coherence-overlay`, `verification-overlay`, or `overlay-maintenance` (symmetric with `arrow-maintenance`). If long-term use shows it's universally valuable, folding back into core `linked-intent-dev` is always possible — outside-in absorption is easy; inside-out extraction is painful.

What the new plugin provides:

- New directory convention: `docs/overlay/<arrow>/`
- New file types: `.overlay.yaml` manifest + engine-specific artifacts
- New frontmatter (optional — see §5.1): `derives_from:` on EARS and LLD sections
- New status markers (above)
- Dispatcher (Python or equivalent) that invokes each engine based on manifest
- Slash commands / ambient skills: `/overlay-check` (run dispatcher), `/overlay-audit` (provenance + coverage report), maybe `/overlay-shard` (coherence-shard detection over `derives_from:`)
- CI hook wiring that plugs the dispatcher into the project's existing CI

What it reads (never modifies): existing LID artifacts — EARS, code, arrows, tests, LLDs. Source stays untouched; the overlay is a pure sidecar. Provenance-completion (`derives_from:`) is the one incremental LID-artifact-level change, and it's per-doc frontmatter, not structural.

### 8.1 State persistence over diffs — feasibility in layers

The "inductive maintenance over diffs" framing (§5.3) implies a system that tracks verified state across commits, invalidates correctly when upstream changes, and re-verifies on the affected subset. Three feasible layers, pick based on scale:

**Layer 0 — commit `_status.yaml`.** The dispatcher writes `_status.yaml` after every run with `last_run:` timestamps, git SHA, artifact/target hashes. Commit the file. Git gives you history for free; diffs show verification drift over time; reverts roll state back with the code. Works today with the prototype in `docs/research/dispatcher/`. Sufficient for projects up to ~50-100 specs where full re-runs are cheap.

**Layer 1 — content-addressable result cache.** Key `(artifact_hash, target_content_hash, engine_version) → result`. Skip re-running when inputs unchanged. This is the Bazel / Turborepo / Nix pattern applied to verification instead of builds. Added to the dispatcher in a few hundred lines of code. Turns a 1000-spec overlay from 8-hour full re-run into a few-minute incremental. The `target_hashes:` field added to schema v0.3 (Appendix F) is the substrate for this.

**Layer 2 — full build graph.** Every engine invocation is a node; dependencies include upstream `derives_from:` artifacts; invalidation propagates transitively. Full Bazel analog. Real engineering, but well-understood tech. Only needed at thousands of specs with rich cross-spec dependency graphs — no evidence yet this is required, but the path is open.

The scale curve: Layer 0 works up to ~100 specs; Layer 1 carries through ~5000; Layer 2 beyond that. Git is the shared substrate for all three — it's the append-only history-preservation log Basilisk (§5) quantifies over.

### 8.2 Scale considerations

Directory layout at scale: `docs/overlay/<arrow>/<spec-id>.*`, one `_status.yaml` per arrow plus an optional top-level cross-arrow rollup. At 1000 specs across ~20 arrows, that's ~50 specs per directory — git-performant, grep-fast, dispatcher can shard CI runs per arrow in parallel.

Parallelism: each spec's verification is independent (dispatch is data-parallel). A 16-way parallel dispatcher + Layer 1 caching brings 1000 specs to minutes for typical partial invalidation, tens of minutes for a full re-run.

Per-arrow sharding also means partial adoption is natural — one arrow can have a richly populated overlay while another has `overlay: disabled`. Teams can adopt incrementally.

## 9. Extensibility

**New engines: additive.** Adding a new engine (e.g., TLA+ for a state-machine EARS, Liquid Haskell for a Haskell codebase) means a new dispatcher entry and a new artifact file type. The manifest schema doesn't change.

**New languages: most classes port naturally.** Per the class-based table in §3, only three classes are deeply language-specific — SMT-backed contract provers, refinement types, and type-system native. For these, the overlay architecture requires picking a per-language instance (Verus for Rust, Frama-C for C, etc.) but doesn't otherwise change shape. The other classes (structural/dataflow query, test-witness, state-machine, proof assistant, runtime contracts, differential, git-provenance, manual-review) work across languages either natively or via language-agnostic patterns.

**Per-arrow escape.** Any arrow can declare `overlay: disabled` if the cost/benefit isn't there. Partial adoption across a codebase is supported (and expected).

## 10. Honest skeptical case

- Formal methods have existed 50 years and never become mainstream. What's different is LLMs collapsing proof-authoring cost, not the methods.
- Most codebases don't need this. CRUD apps, typical SaaS — maintenance cost exceeds benefit. LID should never push this universally.
- **Translation-fidelity leak** (new). The formal overlay verifies "code satisfies artifact," but artifact-to-EARS translation is human-authored. A CodeQL query, test-witness contract, or LemmaScript annotation can mis-encode the EARS while mechanically verifying clean. Differential re-interpretation at the same gate is the countermeasure. Alone, each engine has blind spots; paired, they cover each other.
- **Code-bias in formal artifact authoring (two-dimensional, from B8).** When the authoring agent has access to both EARS and code, the artifact is influenced on two axes. (1) *Semantic content* — the artifact over-specifies by encoding code-sourced constraints not in the EARS (per B8b test-witness), or picks a stronger but different verification target than the EARS literally asked for (per B8a CodeQL). SMT contract provers on arithmetic EARS appear least susceptible (B8c converged). (2) *Execution fidelity* — blind artifacts routinely fail to run because the author lacks tool-API knowledge (invented CodeQL methods), source-vocabulary knowledge (regex matches `remove` but the real prompt says `drop`), or tool-fragment-subset knowledge (for-loops where LemmaScript requires while-loops). Code access confers both informational bias AND operational capability; removing code access exposes both. Countermeasure: periodic blind re-authoring audits (with a normalization pre-pass for tool-fragment conformance) plus bidirectional differential (§4) for semantic drift.
- **Overlay-specific: stale artifacts.** Code drifts; overlay files don't auto-update. The CI hook is load-bearing. Without it, overlay pass/fail lies.
- **Overlay-specific: test-witness weakness.** A test *referencing* an EARS is not proof that assertions correspond to EARS semantics. Contract schema has to make the correspondence explicit; otherwise degrades to "we have a test."
- **Overlay-specific: dispatch coherence.** Multiple engines might verify different properties and agree — but that's three different facts, not one. Manifest must make *what* is verified by *which* engine explicit.
- **Differential-specific: non-determinism.** LLM output varies; a single run may miss or add properties spuriously. Ensembles and structured prompts help but don't eliminate noise. Output is a diff for human review, not a pass/fail gate.
- **Differential-specific: shared blind spots.** Both A (forward) and B (reverse) agents may share the same blind spot (e.g., both miss a subtle concurrency property). Agreement ≠ correctness.
- Emitter fidelity (TS → Dafny for LemmaScript) is still inspection-validated, not machine-checked.
- LLM proof-filling is economically load-bearing for prover engines.

---

# 11. Experiments

## 11.1 First wave — EARS ↔ code (gate 4), all three shape-classes

Ran 2026-04-22. All three verified on the case-study's actual code with no source modifications.

| # | EARS | Engine | Verdict | Notes |
|---|---|---|---|---|
| 1 | FEAT-DET-018 (structural) | CodeQL | `[V]` | 6 query iterations, ~35 min. `list_append`-only DDB pattern confirmed; negative-fixture flags 5 synthetic violations. |
| 2 | FEAT-DET-021 (behavioral) | Test-witness | `[V]` | 4 existing tests carry `@spec`. 250-line mechanical verifier; 23/23 obligations pass. 3 documented limitations. |
| 3 | FEAT-DET-014 + FEAT-LIFE-001..003 (functional) | LemmaScript/Dafny | `[V]` | Dafny 4.11 + Z3. Main verified with zero proof hints; lifecycle required ~120 lines hand-written Dafny. 27 default / 241 isolate-assertion VCs, all clean. |

See `docs/research/experiments/{codeql-thr-det-018, test-witness-thr-det-021, lemmascript-thr-det-014}/RESULTS.md` for full writeups.

### Cross-cutting findings

- Overlay **confirms architecture, doesn't discover bugs** — right outcome for a first wave.
- Each engine has a **well-defined wall** (refined in Wave 2, §11.2). CodeQL can't reason about LLM behavior. Test-witness checks structural assertion presence, not semantic correspondence. LemmaScript's `//@` annotations (LemmaScript's pre/post/invariant comment syntax) are single-function-scoped — but cross-call temporal properties reformulated as *trajectory-in-output* patterns (§11.2/B5; full pattern in Appendix G) verify cleanly. Real LemmaScript wall is at the emitter (method-vs-function), not the prover.
- **Intra-spec dispatch is real** (FEAT-DET-018 needed two engines).
- **`@spec` coverage gap** surfaced without touching source — the enforcement function has no `@spec` annotation, only the prompt-builder does. Overlay can nudge without editing source.
- **Schema v0.2 needed**: scope-aware detectors, MC/DC-style negation discriminators, `limitations:` field, `engines:` as list.
- **Maintenance-resistance signal is strong** across all three — each would auto-catch specific future regressions.

## 11.2 Second wave — gates 3 and 4, differential, inductive maintenance, scale

Ran 2026-04-22 in parallel. All seven verified or produced actionable findings; none blocked.

| # | Experiment | Gate / Engine | Verdict | Headline |
|---|---|---|---|---|
| B1 | Differential on FEAT-DET-021 | (4) / differential | `[V]` | 3/3 A-runs mirror EARS shape (flat, no conjuncts); 3/3 B-runs recover all three conjuncts explicitly. Differential mechanically surfaces the gap Wave 1 had to back-derive from code. |
| B2 | LLD ↔ EARS differential (primary arrow) | (3) / differential | `[V]` | 11 concrete coherence gaps across 3 subsections in ~9 min compute. 10 LLD commitments without EARS coverage. Inverse pattern also found: real EARS sometimes more decomposed than LLD. |
| B3 | Inductive-maintenance (FEAT-DET-014) | (4) / LemmaScript | `[V]` | 10/10 breaks caught, 11/12 compats pass. 12th exposed a LemmaScript emitter bug (record-field ordering), not an annotation false positive. CI-hookable with a 3-line emitter patch or ESLint rule. |
| B4 | Scale to 10 EARS | (4) / all | `[V]` + v0.3 proposal | 10/10 terminal (9V + 1Vn). Schema v0.2 substantially holds. Two concrete v0.3 additions (MC/DC arm-counting; codified coverage semantics). Cross-spec shards fall out mechanically. |
| B5 | LemmaScript immutable digest | (4) / LemmaScript | `[V]` via trajectory-in-output | **Narrowed the §10 limitation claim on LemmaScript reach.** Full cross-prefix immutability invariant verifies in a single `//@ ensures` via trajectory reformulation. Zero hand-written proof. Real wall is the emitter (method-vs-function), not the prover. TLA+ expresses the same property one-liner-per-field; Hand-Dafny needs ~140 lines. |
| B6 | CodeQL adversarial (long-requires-short taint) | (4) / CodeQL | `[V]` | **Broadened the CodeQL reach claim.** 100% catch rate across 10 adversarial fixtures covering 8 dimensions (aliasing, object-wrap, collection, sanitizer, async, dynamic, renamed, cross-file). Walls are naming-convention coupling (soft), distributed dynamic access (hard), content-preserving transforms not modeled as sanitizers (hard). |
| B7 | Git-provenance for FEAT-DET-* | (4) / git-provenance | `[V]` as advisory | Raw forward drift 11.9%; **kind-aware drift 0%**. Substantive EARS edits matched 3/3. 0 genuine drift events in 2-month slice; 2 actionable annotation-coverage gaps. Value proposition shifts to "coverage gaps," not "drift." Advisory dashboard, not CI gate. |

See `docs/research/experiments/{b1..b7}/RESULTS.md` for full writeups.

## 11.3 Wave 2 cross-cutting findings

**1. Overlay-dispatch + differential + provenance architecture is validated across dimensions.** Schema holds at 10× scale (B4). Inductive maintenance works (B3). Engines reach further than expected with characterizable walls (B5, B6). Differential produces real signal at both gate 3 and gate 4 (B1, B2). Seven independent stress tests confirmed the architecture from different angles.

**2. Two prior claims in this document were wrong and have been softened.**
- An earlier version of §11.1 asserted "LemmaScript doesn't reach cross-call temporal properties." B5 refutes: the trajectory-in-output reformulation captures cross-prefix immutability in one `//@ ensures` with zero hand-written proof. See Appendix G.
- Earlier versions of §7 and §10 implicitly treated CodeQL as limited to "convenient structural patterns." B6 refutes: CodeQL with `TaintTracking::Global` (CodeQL's global dataflow library) plus custom barriers handles 8 adversarial dataflow dimensions cleanly.

**3. The differential-re-interpretation hypothesis — added mid-session as a pivot away from the original EARS-to-formal-obligation framing — was the highest-leverage bet of this work.** B1 and B2 both produced signal-not-noise, surfacing coherence gaps that formal overlay engines structurally cannot see. This is the core new contribution to LID from this research pass.

**4. Basilisk's framing is literal, not analogical** (B3). The invariant-as-conjunction-of-local-provenance view works exactly as described: each `//@ ensures` catches a specific violation class with correctly-attributed diagnostics; the conjunction is preserved by every semantically-compatible diff. Metaphor stands up to direct mechanical test.

**5. Git-provenance's value proposition needed honest adjustment** (B7). The initial framing ("catches drift") overstates signal on a disciplined project. Real value: surfacing annotation-coverage gaps (2 actionable in 22 specs) rather than catching drift (0 genuine cases in 2 months). Advisory dashboard posture, not CI gate.

**6. Schema v0.3 has a concrete, narrow proposal.** See Appendix F. Consolidates B1/B2/B4/B7 findings:
- `ears_logical_structure:` field for MC/DC arm counting (B4)
- Codified coverage semantics: `coverage = |V ∪ Vp ∪ Vn| / total` (B4)
- `engine: differential` promoted to first-class (B1, B2)
- `engine: git-provenance` added with default `posture: advisory` (B7)
- Canonical LemmaScript pattern: trajectory-in-output for cross-call temporal (B5)

**7. Real artifacts emerged as byproducts** — evidence the methodology produces concrete outputs, not just research signal:
- B1 recommended rewriting FEAT-DET-021 with explicit three-conjunct EARS text
- B2 identified 9 prioritized EARS additions (3 P1 / 3 P2 / 3 P3)
- B3 documented a LemmaScript emitter bug at `node_modules/lemmascript/tools/dist/dafny-emit.js:337` with a 3-line fix proposed
- B6 recommended naming-convention standardization to remove the CodeQL sink-regex dependency
- B7 identified 2 EARS needing `@spec` annotations

**8. Cost characterization for overlay at scale.** Per-EARS overlay cost ~10-20 minutes once engine templates exist (B4 hit ~11 min/EARS average). CodeQL iteration dominates. Dispatch automation, `_status.yaml` rollup generation, and engine-reference library would drop this further. Steady-state economics look workable.

**9. The promotion question resolves (Wave 2 position, superseded by Wave 3 — see §11.5 item 6).** "Promotion" here means moving this work out of `docs/research/` and into a new optional plugin (see §8). The overlay is ready to graduate as a separate skill — sibling to `arrow-maintenance`, installed only by projects that want this deeper alignment level. Most LID projects (CRUD, typical SaaS) should correctly never adopt it. If long-term adoption shows it's universally valuable, folding back into core `linked-intent-dev` is always possible later.

Engine readiness at promotion (Wave 2 cut; Wave 3 upgraded differential from advisory to co-gate — see §11.5):
- **CI-gated** (Wave 2 cut): structural/dataflow query (CodeQL etc.), SMT-backed contract prover, type-system native, test-witness
- **Advisory** (Wave 2 cut; Wave 3 promoted differential to co-gate): differential re-interpretation, git-provenance
- **Already present**: manual-review signoff for qualitative EARS
- **Remaining pre-promotion work**: `derives_from:` rollout tooling (optional per §5.1); Layer 1 caching if target projects are at scale (§8.1); plugin scaffolding and slash commands per §8; blind-audit pass over every existing overlay artifact before promotion (per §11.5 item 7).

## 11.4 Third wave — blind re-authoring + bidirectional differential as audit unit

Ran 2026-04-22 (B8) and 2026-04-23 (B9). Two experiments testing refinements to the overlay architecture surfaced by Wave 2.

| # | Experiment | Target | Verdict | Headline |
|---|---|---|---|---|
| B8 | Blind re-authoring of Wave 1 formal artifacts | FEAT-DET-018 (CodeQL), FEAT-DET-021 (test-witness), FEAT-DET-014 (LemmaScript) | Mixed — (ii)/(iii)/(i) by engine | Medium-form code-bias hypothesis confirmed for CodeQL and test-witness; refuted for LemmaScript on arithmetic EARS. Added three new code-bias axes visible only at execution time (tool-API, source-vocabulary, tool-fragment-subset). 0/3 blind CodeQL queries produce correct output; 0/3 blind LemmaScript compiles through lsc. The Wave 1 test-witness contract's three-conjunct daily-mode premise (not in the EARS text) is now confirmed independently by both B1 differential and B8 blind re-authoring. |
| B9 | Bidirectional differential on 6 fresh EARS (filter arrow) | 2 simple, 2 moderate, 2 complex from the filter-arrow specs | 5/6 BD-DRIFT, 1/6 BD-COHERENT | First experiment running A and B together as a unified audit on fresh territory. Simple ≠ coherent — simple-tier EARS show drift too. Moderate tier surfaces "spec-decomposition gap" (sibling EARS don't cross-reference). Complex tier bifurcates: bounded-output + exhaustive enumeration → BD-COHERENT (canonical example: FLT-SCORE-001's 2×2 scoring matrix); unbounded-output filter → BD-DRIFT via "operational halo" (central rule clear; error/config/boundary silent). |

See `docs/research/experiments/{b8-blind-reauthoring, b9-bidirectional-differential-filter}/RESULTS.md` for full writeups.

### Worked examples

Three examples from the B9 audit that illustrate the classification codes in practice:

**BD-COHERENT — FLT-SCORE-001 (four-case scoring matrix).** The EARS enumerates all four `(domainTag × focus)` combinations with explicit point values. Real code: a 3-case if-ladder with default-zero. Every A-run reconstructs the function; every B-run reconstructs the matrix. The bounded output domain `{0,1,2,3}` plus exhaustive enumeration closes the drift gap by construction. **Why coherent**: EARS leaves the implementer zero sub-decisions.

**BD-DRIFT (missing sub-decision) — FLT-UE-004 (prefer normalizedText over content).** EARS says only "prefer." Real code: `item.normalizedText || item.content || ''` then `if (!text) continue;` (drops item if both missing). Three A-runs diverged on the operator (2× `??`, 1× explicit length check); none drop the item. Three B-runs convergently split the real EARS into 004a (selection with "present and non-empty" qualifier) + 004b (unwanted-behavior: omit item on both-missing). **Why bidirectional**: EARS silent on two behaviorally-meaningful sub-decisions; A-runs invent different answers; B-runs elevate both missing EARS-level obligations.

**BD-DRIFT (operational halo) — FLT-UE-001 (four-conjunct incorporated predicate + fallback).** Central rule (four conjuncts, empty-summary override) reconstructs cleanly both directions. What drifts is the *halo* around the rule: partial-results-on-error contract (silent degradation on DynamoDB mid-scan failure), unconfigured-table short-circuit (misconfiguration yields zero entries rather than error), missing-`processedAt` default, whitespace-only summary treated as empty. A-direction misses all of these; B-direction elevates them as separate unwanted-behavior EARS. **Why halo-shaped**: unbounded output domain (a filter over an entry list); enumeration alone can't close the gap; companion unwanted-behavior EARS are needed.

### Bug vs. spec-drift classification

Across the 5 B9 BD-DRIFT cases and similar B8 findings, the drift splits roughly 1/3 real-or-likely bugs, 1/3 latent refactoring hazards, 1/3 pure documentation drift:

- **Probable real bugs (or real product-intent questions)**: FLT-UE-003 "oldest-vs-newest-20" semantics (the test counts entries but not which ones survive — a newest/oldest swap passes silently); FLT-SCORE-003 transitive tie-chaining ambiguity.
- **Risky undocumented behaviors**: FLT-UE-001's partial-results-on-error (user is never notified that domain agents ran on partial data); unconfigured-table silent short-circuit (silent failure on config error).
- **Documentation drift with latent refactoring risk**: FLT-UE-004's empty-string fallthrough (code uses `||`; a future "modernize to `??`" refactor would silently change behavior); drop-on-both-missing (output-shape contract downstream consumers may be relying on implicitly).
- **Pure documentation drift**: whitespace-trim on summary text; FLT-CTX-001's cluster-decomposition drift (code is correct; single-EARS readers just can't see the full requirement).

The methodology doesn't distinguish these automatically — that requires human judgment. But it **concentrates review** on 5-10 specific cases per audit rather than re-reading the full spec, and **names** each case precisely enough that triage takes 30-60 seconds per case. Even pure-documentation drift has compounding cost: every unstated sub-decision is a refactor landmine for future implementers (human or LLM).

## 11.5 Wave 3 cross-cutting findings

**1. Simple ≠ coherent.** B9's two simple-tier EARS both showed bidirectional drift. The prior expectation — that single-claim, unambiguous EARS should trivially converge — is refuted. Simplicity concentrates drift into a single unspecified sub-decision rather than eliminating it.

**2. Drift has recognizable signatures per tier.**
- *Simple*: missing sub-decision (empty-string fallthrough, oldest-vs-newest).
- *Moderate*: spec-decomposition gap — sibling EARS correctly factor an implementation across multiple atomic EARS, but individual EARS don't cross-reference each other, so single-EARS blind readers under-implement.
- *Complex with bounded output*: BD-COHERENT if the EARS enumerates exhaustively.
- *Complex with unbounded output*: operational-halo drift — central rule clear, error/config/boundary silent.

These signatures suggest **drafting rules**: enumerate exhaustively for bounded-output EARS; add companion unwanted-behavior EARS for unbounded/filter-shaped EARS; add cross-references between decomposed sibling EARS.

**3. B-direction is the stronger drift detector.** Across all B9 runs, within-direction variance is near-zero for B-runs (three independent reconstructions agree) and moderate for A-runs (different blind agents pick different plausible sub-decisions). B-runs consistently surface unstated constraints. A-runs disambiguate *whether the constraint is real* (A-runs split) or *decorative* (A-runs all converge on the same wrong answer). Both directions are needed; B does the heavier lifting.

**4. Bidirectional differential on plain code has no execution-fidelity issues** (unlike B8 engine-specific blind re-authoring). Plain TypeScript and plain EARS round-trip cleanly through fresh `claude -p` sessions; no tool-API/source-vocabulary/fragment-subset bias surfaces. This means bidirectional differential is **safer as a generalist audit** than blind re-authoring of engine-specific artifacts. Use blind re-authoring for existing formal artifacts; use bidirectional differential for freshly-authored EARS + code.

**5. Code-bias in Wave 1 formal artifacts is real but varies by engine.** B8 confirmed the medium-form code-bias hypothesis cleanly for test-witness (three-conjunct daily-mode premise came from code, not EARS) and partially for CodeQL (choice-of-target bias — verified architecture layer instead of the EARS's literal prompt layer). LemmaScript on arithmetic EARS was immune (bounded enumeration again). **Two prior claims elsewhere in this document are now under suspicion**: the Wave 1 CodeQL artifact verifies a real property but not the one the EARS grammatically states; the Wave 1 test-witness contract includes a conjunct the EARS doesn't specify.

**6. Promotion position strengthened: differential + blind-audit become co-gates.** The architectural claim "the overlay catches intent drift" splits cleanly:
- Formal engines catch *future regressions* from a fixed artifact baseline (validated by B3's 10/10 synthetic-variant matrix).
- Formal engines do NOT catch *current drift* between EARS and code (validated by Wave 1's zero-drift-catch finding combined with B8 showing the Wave 1 artifacts themselves embody drift).
- Bidirectional differential catches current drift (validated by B1, B2, B8b, B9 — five independent experimental confirmations).

Neither alone delivers both. Concrete promotion rule proposed:

> An EARS's formal artifact can be promoted to `[V]` only when its `last_blind_audit` records BD-COHERENT or A-ONLY-DRIFT. BD-DRIFT requires reconciliation (EARS or code edit) before promotion. B-ONLY-DRIFT is advisory (may warrant EARS addition but doesn't block). INCONSISTENT-BLIND requires re-run with refined prompts.

Schema v0.3 gains a `last_blind_audit:` field alongside `last_run:` (see Appendix F). The dispatcher gains an `overlay audit` subcommand that runs bidirectional differential on any EARS whose `last_blind_audit.git_sha` is older than the most recent edit to the EARS or its `@spec`-referenced code.

**7. Every existing overlay artifact is under suspicion until re-audited.** If Wave 1 artifacts were code-biased (and at least B8b proves one of them was), promoting any existing artifact without a blind-audit pass would bake the bias in. Three remediation paths, specific to the Wave 1 cases:
- FEAT-DET-021 test-witness: either promote the three-conjunct daily-mode premise to the EARS text (recommended; captured in an auxiliary recommendations artifact, not published), or drop it from the contract
- FEAT-DET-018 CodeQL: add a prompt-literal sibling artifact to the overlay (intra-spec dispatch) alongside the existing architecture query
- FEAT-DET-014 LemmaScript: no remediation needed (B8c showed convergence); optional cheap strengthening to explicit `daySpan` monotonicity

**8. Cost characterization for Wave 3 audits.** Per-EARS bidirectional differential: ~6 `claude -p` calls (3 A + 3 B), ~2-3 min wall-clock at parallel execution, plain text in/out. Per-engine blind re-authoring: ~3 `claude -p` calls per engine per EARS, plus toolchain normalization pre-pass, ~5-10 min wall-clock including execution. Both are cheap enough to run on every EARS promotion; neither is cheap enough to run on every commit (use the cache layers in §8.1 instead).

## 11.6 Tooling produced this session

Three concrete artifacts sit alongside this doc and are part of the promotion decision:

- **`docs/research/dispatcher/`** — a ~500-line Python dispatcher prototype (`dispatcher.py` + `README.md`). Reads `*.overlay.yaml` manifests, invokes the declared engine(s), aggregates results into `_status.yaml`, exits non-zero when any gate engine reports `Vx` or `?`. Supports all engine classes listed in §3. Run end-to-end against the B4 overlay tree produces 6V + 1Vn + 3Vx = 70% terminal coverage; the 3 Vx cases are real findings (2 workspace-import resolution issues in overlay TS that need `project_root:` support; 1 CodeQL query with 2 unexpected rows needing investigation). Current caching posture is **Layer 0** (§8.1) — full re-run every invocation. Schema v0.3's `target_hashes:` (Appendix F) is the substrate for Layer 1 incremental caching, a natural next increment once scale demands it. This closes the "dispatcher prototype" line item previously listed as pending work.
- An auxiliary recommendations artifact (not published) — a consolidated proposal document carrying byproducts from §11.3 item 7 (prioritized EARS edits combining B1's FEAT-DET-021 rewrite with B2's additions, `@spec` coverage gaps, an upstream LemmaScript emitter bug report, and a naming-convention observation) in a case-study-reviewable format.
- **`docs/research/experiments/{codeql-thr-det-018, test-witness-thr-det-021, lemmascript-thr-det-014, b1..b7-*}/`** — Wave 1 + Wave 2 experiment artifacts: per-experiment `RESULTS.md`, working overlay manifests, engine-specific artifacts (`.codeql`, `.test-witness.yaml`, `.annotated.ts`, `.dfy`, `.differential.md`), and per-experiment iteration logs.
- **`docs/research/experiments/{b8-blind-reauthoring, b9-bidirectional-differential-filter}/`** — Wave 3 experiment artifacts: blind-reauthoring audit of Wave 1 formal artifacts (B8), and bidirectional-differential audit of 6 fresh EARS from the filter arrow across three complexity tiers (B9). Each directory contains raw `claude -p` outputs, per-artifact comparisons, per-EARS classifications, tier summaries (B9), and full RESULTS.md writeups.

The deliverables are cohesive: the experiments produced the schema v0.2/v0.3 evidence plus the Wave 3 co-gate promotion rule, the dispatcher operationalizes the schema end-to-end, and the recommendations doc is the first real-world output the overlay produces. If promotion happens, these become the seed of the new LID extension.

## 11.7 Deferred (not in any wave)

- HLD ↔ LLD differential (gate 2) — narrative prose at both ends produces high noise in B-side reconstruction; defer until gate 3 (LLD ↔ EARS) has proven the noise/signal ratio is tractable.
- Intent ↔ HLD (gate 1) — user-in-loop by necessity; the ground-truth intent lives in the user's head, so no automated round-trip has access to an authoritative upstream.
- Multi-language port beyond TS — the §3 class-based table establishes that most engines port naturally; the remaining work is identifying per-language instances of the three language-specific engine classes. Premature until the overlay's first real deployment (on a TS project) stabilizes.
- Basilisk-style inductive-invariant *synthesis* — different problem shape; LID is not a distributed protocol, so the synthesis algorithm doesn't apply. §5 uses Basilisk's *framing*, not its method.
- Layer 2 build graph (§8.1) — only needed at thousands of specs; Layer 0/1 carries the architecture through the current scale.
- TLA+ experiment — no protocol-shaped EARS (distributed coordination, concurrent state machines, liveness) present in the case-study, so there is no natural test case in scope.

---

## Appendix A — Overlay manifest schema v0.2

See §7 for current example. Schema contract:

```yaml
spec_id: required
arrow: required
derives_from:                # list of upstream references
  - doc: <path>
    section: <heading or anchor>
engines:                     # list — intra-spec dispatch
  - engine: codeql | test-witness | lemmascript | tla+ | differential | type-system | manual-review
    artifact: <filename in this directory>
    status: V | Vp | Vx | Vn | "?"
targets:                     # code regions
  - type: function | file | pattern
    selector: <engine-appropriate selector>
witnesses:                   # optional, test-witness mostly
  - path: <test file glob>
    describes: <describe name or selector>
limitations:                 # honest carve-outs
  - <free text>
last_run:
  timestamp: <ISO>
  result: verified | stuck | pending
  hash: <artifact hash>
notes: |
  <free text>
```

## Appendix B — CodeQL draft for FEAT-DET-018 (verified)

Lives in `docs/research/experiments/codeql-thr-det-018/FEAT-DET-018.codeql`.
Query confirmed `list_append`-only DDB writes. 3 hits in tree, all safe.

## Appendix C — Test-witness contract for FEAT-DET-021 (verified)

Lives in `docs/research/experiments/test-witness-thr-det-021/FEAT-DET-021.test-witness.yaml`.
Schema v0.2 with precondition/action/postcondition structure, MC/DC-style negation discriminators, `limitations:` carve-outs.

## Appendix D — LemmaScript annotated TS for FEAT-DET-014 (verified)

Lives in `docs/research/experiments/lemmascript-thr-det-014/FEAT-DET-014.annotated.ts`.
Main property verified with zero proof hints; lifecycle monotonicity verified with ~120 lines hand-written Dafny.

## Appendix E — Differential engine artifact shape (new)

```markdown
# FEAT-DET-021 — Differential round-trip
## A-direction (EARS → implementation)
Agent input: the EARS text only (no code, no LLD)
Agent output: <generated test code / generated artifact>
Ground truth: <real test / real code>
Diff vs. ground truth: <diff summary, key misses, key additions>

## B-direction (implementation → EARS)
Agent input: the real implementation only (no EARS)
Agent output: <generated EARS>
Ground truth: <real EARS>
Diff vs. ground truth: <diff summary>

## Coherence findings
- Gaps in upstream surfaced by B: ...
- Gaps in downstream surfaced by A: ...
- Recommended action: update EARS / update code / add formal artifact covering X
```

## Appendix F — Schema v0.3 proposal

Draws on B1, B2, B4, B5, B7. Narrow, additive, backward-compatible with v0.2.

```yaml
# docs/overlay/<arrow>/<SPEC-ID>.overlay.yaml
spec_id: required
arrow: required

# v0.2 — unchanged
derives_from:
  - doc: <path>
    section: <heading or anchor>

# v0.3 NEW — logical structure metadata for dispatcher
ears_logical_structure:          # NEW in v0.3
  type: conjunctive | disjunctive | exception | unconditional
  arms:                          # for conjunctive/disjunctive
    - id: C1
      description: "daily-mode premise"
    - id: C2
      description: "zero assignments"
    - id: C3
      description: "≥1 unassigned entry"
  exception_of: <spec-id>        # for exception-shaped EARS

engines:
  - engine: codeql | test-witness | lemmascript | tla+ | differential | git-provenance | type-system | manual-review
    artifact: <filename>
    status: V | Vp | Vx | Vn | "?"
    posture: gate | advisory     # NEW in v0.3 — differential and git-provenance default to advisory
    mc_dc_arms:                  # NEW in v0.3 — for engines with arm-flipping tests
      - arm: C1
        negation_artifact: <filename>
      - arm: C2
        ...

targets:
  - type: function | file | pattern | ast-query
    selector: <engine-appropriate selector>

witnesses:
  - path: <glob>
    describes: <selector>

limitations:
  - <free text>

exceptions:                      # NEW in v0.3 — structural carve-outs
  - <free text>                  # e.g. "negative requirement — not annotatable"

last_run:
  timestamp: <ISO>
  git_sha: <commit SHA>            # NEW in v0.3 — repo commit at verify time
  dirty: <bool>                    # NEW in v0.3 — was working tree clean?
  result: verified | stuck | pending | advisory
  artifact_hash: <sha256 of the overlay artifact>
  target_hashes:                   # NEW in v0.3 — content hashes of each target (enables Layer 1 cache)
    - selector: <target-selector>
      hash: <sha256 of the target file/function slice>

last_blind_audit:                  # NEW in v0.3 — gates [V] promotion per Wave 3 (§11.5 item 6)
  timestamp: <ISO>
  git_sha: <commit SHA>
  mode: bidirectional-differential | blind-reauthoring
  a_runs: N                        # how many A-direction (EARS → code) fresh sessions
  b_runs: N                        # how many B-direction (code → EARS) fresh sessions
  classification: BD-COHERENT | A-ONLY-DRIFT | B-ONLY-DRIFT | BD-DRIFT | INCONSISTENT-BLIND
  drift_findings:                  # concrete items surfaced
    - <short text>
  reconciliation_required: <bool>  # true if BD-DRIFT and nothing's been edited yet

notes: |
  <free text>
```

**Why `git_sha` + `target_hashes` matter.** Without a git SHA, `last_run: verified` is ambiguous — was it the current tree or three commits ago? With it, you can falsify a cached result against the current working tree in one comparison. With `target_hashes`, you can skip re-running the engine entirely when none of the target slices changed, even if the broader repo moved forward. That's what makes Layer 1 caching (§8.1) possible — the cache key is `(artifact_hash, target_hashes, engine_version)`, and the result is valid at any git SHA where those three hashes match.

### `_status.yaml` roll-up (per-arrow)

```yaml
# docs/overlay/<arrow>/_status.yaml
arrow: <name>
as_of: <ISO>
git_sha: <commit SHA>                 # NEW in v0.3 — rollup labelled with repo state
dirty: <bool>                         # NEW in v0.3
total_specs: N

# v0.3 NEW — codified coverage semantics
coverage:
  formula: "|V ∪ Vp ∪ Vn| / total"    # terminal-complete counts as covered
  value: 0.90                          # concrete number

by_status:
  V: N
  Vp: N
  Vx: N
  Vn: N
  "?": N

by_engine:
  codeql: [<spec-id>, ...]
  test-witness: [...]
  lemmascript: [...]
  type-system: [...]
  differential: [...]
  git-provenance: [...]
  manual-review: [...]

by_arrow:                              # NEW in v0.3 — for cross-arrow rollups
  <arrow-name>: [<spec-id>, ...]

shards:                                # NEW in v0.3 — coherence shards
  - name: classifyStatus
    specs: [FEAT-LIFE-001, FEAT-LIFE-002, FEAT-LIFE-003]
    derives_from: "docs/llds/FEAT.md#lifecycle-thresholds"

gaps:
  - spec: <id>
    note: <reason>
```

## Appendix G — LemmaScript trajectory-in-output pattern (B5)

Canonical form for single-aggregate cross-prefix temporal invariants. Use when you need to prove a property "for every step i and every later step j, P(state[i], state[j])" on a sequence of operations, but LemmaScript's single-function `//@` scope would naively block you.

### Pattern

Return the full trajectory of intermediate states alongside (or instead of) the final result. Quantify over trajectory indices in `//@ ensures`.

```typescript
interface DigestSlot {
  digest?: string;
  tags?: string[];
  generatedAt?: number;
}

interface Op {
  kind: 'Short' | 'Long';
  digest: string;
  tags: string[];
  at: number;
}

function applyOp(slot: DigestSlot, op: Op): DigestSlot { /* ... */ }

//@ ensures \result.length === ops.length + 1
//@ ensures \result[0] === initial                                   // initial state preserved
//@ ensures forall(i, 0 <= i && i < ops.length ==>                   // step-correctness
//@   \result[i + 1] === applyOp(\result[i], ops[i]))
//@ ensures forall(i, forall(j, 0 <= i && i < j && j < \result.length &&
//@   \result[i].digest !== undefined ==>
//@   \result[i].digest === \result[j].digest))                     // immutability across prefixes
export function runTrajectory(initial: DigestSlot, ops: Op[]): DigestSlot[] {
  const trajectory: DigestSlot[] = [initial];
  let i = 0;
  while (i < ops.length) {
    //@ invariant trajectory.length === i + 1
    //@ invariant forall(k, 0 <= k && k < i ==>
    //@   trajectory[k + 1] === applyOp(trajectory[k], ops[k]))
    trajectory.push(applyOp(trajectory[i], ops[i]));
    i++;
  }
  return trajectory;
}
```

### Why this works where a single-function `ensures` over a helper fails

LemmaScript's emitter produces Dafny `method` (not pure `function`) for any TS function with a `while` loop or a `//@ ghost let`. Dafny disallows method invocation inside expression contexts, so you cannot call a helper function inside an `ensures` to quantify over "results of the helper at every step." The trajectory pattern **internalizes the sequence** — the trajectory is just an array value, not a function call, so the `ensures` quantifier has concrete indices to range over.

### When to use this

- Cross-prefix immutability ("once set, never changed")
- Monotonicity over a sequence of operations
- Any "for all pairs of steps (i, j), property holds" claim on a single aggregate type

### When this doesn't reach

- Multi-aggregate temporal invariants ("long-horizon digest timestamps temporally ordered after corresponding short-horizon timestamps across multiple items") — trajectory grows combinatorially; escape to TLA+ or hand-written Dafny with inductive lemmas
- Concurrency / liveness properties — different engine family entirely

### Cost comparison (from B5, immutable-digest case)

| Engine | Core-property lines | Hand-written proof |
|---|---|---|
| LemmaScript trajectory-in-output | 65 TS lines | 0 |
| Hand-written Dafny | 190 lines | ~140 |
| TLA+ sketch | 30 lines | 0 (not run through TLC) |

LemmaScript reaches TLA+-comparable expressive power for single-aggregate cross-prefix properties via this pattern.

## Appendix H — Git-provenance engine (B7)

A lightweight overlay engine that queries git history for coherence drift between EARS edits and `@spec`-annotated code edits. Not a formal verifier — a triage surface.

### Engine contract

Given a spec ID `<SPEC-ID>`:
1. `git log -S "<SPEC-ID>"` on the EARS spec file → EARS-edit commits
2. `git grep -l "<SPEC-ID>"` at HEAD → files currently annotated
3. `git log --follow` on those files → code-edit commits
4. Correlate: for every EARS-edit commit, find a code-edit commit within ±3 commits or ±24h
5. Classify each uncorrelated case by edit-kind (`new | marker-only | rephrase | substantive`)

### Output shape

```yaml
# docs/overlay/<arrow>/<SPEC-ID>.git-provenance.yaml
spec_id: FEAT-DET-021
as_of: <ISO>
ears_edits: N
code_edits: N
correlations:
  aligned: N
  drift_benign: N                # rephrase / marker-only
  drift_investigate: N           # substantive w/o code change
  no_atspec_annotation: bool
exceptions:
  - "negative requirement — not annotatable"
findings:
  - commit: <sha>
    date: <iso>
    kind: substantive-drift
    note: <hand-judgment>
```

### Default posture: advisory

Git-provenance engines MUST NOT block CI: raw-forward-drift signal is noisy enough on a disciplined project (B7 found 11.9% raw drift but 0 genuine drift after kind-aware filtering) that gating CI on it would produce false positives faster than real ones. Output feeds an arrow-audit dashboard instead. Per B7, the engine's real value on a disciplined LID project is surfacing annotation-coverage gaps (specs with no `@spec` anywhere in code) rather than drift (very rare on a well-run project).

### When to use

- Arrow audits (quarterly or at milestone boundaries)
- Coverage gap detection (which EARS have no `@spec` annotations anywhere?)
- Post-refactor sanity check (did a big refactor leave the `@spec` trail intact?)

### Known limitations

- Blind to semantic drift where EARS and code change together but one is updated wrong (that's gate-4 verifier territory)
- Negative requirements ("shall not X") are structurally unannotatable — use the `exceptions:` field
- False-positive noise on legacy files where `@spec` annotations post-date substantial commit history — filter to post-annotation commits

## Appendix I — Bidirectional differential + blind re-authoring (B8, B9)

Two related LLM-based drift-detection patterns introduced by Wave 3 experiments. Both rely on fresh, context-free LLM sessions (via `claude -p` or equivalent) to audit coherence between an EARS requirement and its implementation. They attack different concerns and produce different artifact shapes.

### Pattern 1 — Bidirectional differential (B9)

**Purpose**: validate that an EARS and its implementation describe mutually-coherent intent.

**Inputs to the audit**:
- The EARS text
- The real implementation code (for the EARS's `@spec`-annotated code region)

**Procedure** (per EARS):

1. **A-direction (EARS → code)**: spawn 3 fresh LLM sessions, give each ONLY the EARS text plus a one-line description of the target codebase. Task each: *"Produce a TypeScript (or target-language) function that implements this EARS. List every assumption you had to invent."*

2. **B-direction (code → EARS)**: spawn 3 fresh LLM sessions, give each ONLY the real implementation code (stripped of `@spec` markers, EARS IDs, and spec-leaking identifiers). Task each: *"Reconstruct the EARS requirement that this code implements, using standard EARS syntax."*

3. **Compare**:
   - A-diff summary: across the 3 A-runs, what did blind agents consistently produce vs. what the real code does?
   - B-diff summary: across the 3 B-runs, what did blind agents reconstruct vs. what the real EARS says?

4. **Classify** per the codes in §7 "Differential / blind-audit classification codes":
   - **BD-COHERENT** — both converge; no material drift
   - **A-ONLY-DRIFT** — EARS under-specifies a detail that doesn't need spec coverage
   - **B-ONLY-DRIFT** — code has unstated constraints the EARS should state
   - **BD-DRIFT** — both surface the same gap; strong drift
   - **INCONSISTENT-BLIND** — within-direction variance too high to classify

### Pattern 2 — Blind re-authoring audit (B8)

**Purpose**: validate that an existing formal overlay artifact (CodeQL query, test-witness contract, LemmaScript annotation) encodes only what the EARS specifies — not additional constraints derived from code access at authoring time.

**Inputs to the audit**:
- The EARS text
- The target engine's conventions (e.g., "write a CodeQL query for a TypeScript codebase")

**Procedure** (per existing formal artifact):

1. **Blind re-author**: spawn 3 fresh LLM sessions, give each ONLY the EARS and the target-engine description. Task: *"Produce the overlay artifact (query / contract / annotated TS) that would verify this EARS."*

2. **Compare**: run the blind artifacts against the same target as the original, if possible. Compare both the artifacts' semantic content (what they claim to check) and their execution fidelity (whether they run at all).

3. **Classify**:
   - **(i) Convergence** — blind and code-aware artifacts check the same thing
   - **(ii) Over-specification** — code-aware artifact adds checks not in EARS
   - **(iii) Different target** — code-aware artifact verifies a stronger but different property than EARS literally names
   - **Execution-fidelity failures** — blind artifacts may fail to run at all due to tool-API bias, source-vocabulary bias, or tool-fragment-subset bias (B8 found 0/3 blind CodeQL queries runnable-correct; 0/3 blind LemmaScript compiles)

### When to use which

| Situation | Use pattern | Reason |
|---|---|---|
| Auditing a fresh EARS + code pair for coherence before first `[V]` promotion | Pattern 1 (bidirectional) | Plain-text both ends; no tool-API bias; catches drift in both directions |
| Auditing an existing formal overlay artifact that's been `[V]` for a while | Pattern 2 (blind re-authoring) | Tests whether the artifact is code-biased; exposes tool-API / source-vocabulary / fragment-subset failure modes |
| Every promotion to `[V]` (gate rule, §11.5 item 6) | Pattern 1 | Required; cheaper; plain-text inputs |
| Periodic audit of existing promotions (~quarterly) | Pattern 2 | Catches code-bias in artifacts authored before the co-gate rule existed |

### Execution-fidelity pre-pass for Pattern 2

Blind agents produce target-engine artifacts using canonical syntax, not necessarily the tool-specific supported fragment. A dispatcher running blind re-authoring audits should include normalization before evaluation:
- **Tool-fragment-subset normalization**: for LemmaScript, rewrite C-style `for (init; cond; update)` loops to `while` loops before passing to `lsc`. For other tools, equivalent subset conformance.
- **Source-vocabulary expansion**: for structural regex queries, pre-teach blind agents common source-text synonyms (e.g., `remove | drop | delete | omit | strip`) OR run multiple blind agents with different vocabulary seeds and union their matches.
- **Tool-API validation**: compile/lint blind artifacts before evaluating their semantic correctness; failures are *authoring* issues, not *verification* issues.

Without these pre-passes, blind re-authoring produces noise (2 of 3 blind CodeQL queries in B8 failed to compile due to invented API methods).

### Cost and frequency

- **Bidirectional differential**: ~6 `claude -p` calls per EARS (3 A + 3 B), ~2-3 minutes parallel wall-clock. Run on every EARS promotion; optionally on every EARS edit via CI hook.
- **Blind re-authoring**: ~3 `claude -p` calls per engine per EARS, plus normalization, ~5-10 minutes wall-clock. Run quarterly or at milestone boundaries; run ad-hoc whenever an artifact's authored style is suspect.

### Both patterns: `last_blind_audit:` field

Each audit writes a `last_blind_audit:` block to the EARS's `.overlay.yaml` manifest (see Appendix F). The gate rule (§11.5 item 6) reads this field: an EARS is promotable to `[V]` only when `last_blind_audit.classification` is BD-COHERENT or A-ONLY-DRIFT, and `last_blind_audit.git_sha` is at-or-after the current EARS commit. Older audits trigger re-run before gating.
