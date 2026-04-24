# Experiment B6 — CodeQL taint-tracking overlay for FEAT-TIER-021

**Date**: 2026-04-22
**Status**: VERIFIED (property holds on production tree; adversarial controls all pass)
**Artifact**: `LONG-REQUIRES-SHORT.codeql` (executable as `LONG-REQUIRES-SHORT.ql` via symlink)
**Manifest**: `LONG-REQUIRES-SHORT.overlay.yaml`
**DB location**: `/tmp/codeql-b6-db` (copy of `/tmp/codeql-thr-det-018/db`; independent cache lock)

---

## Verdict

**CodeQL reaches.** This experiment pushed past Wave 1's "convenient
structural pattern" into a genuinely dataflow-sensitive invariant and came
back with a working taint-tracking query. The EARS is:

> Long-horizon digests are generated from short-horizon digests, not from the original
> normalizedText. This mirrors the temporal pipeline (seasonal summaries
> compress monthly summaries, not raw entries) and ensures long-horizon compression
> builds on the editorial judgment already made at the short-horizon level.

As a structural property: **`item.normalizedText` must NOT reach the long-horizon
digest prompt-construction**. Only `item.groupDigests[groupId].shd.digest`
is allowed. This is not shape-matching — it is taint.

The final query `LONG-REQUIRES-SHORT.codeql` confirms the property on the real
the case-study tree (0 violations) while firing correctly on 10 adversarial
fixtures covering 8 dimensions. It took 6 query iterations and about 75
minutes wall-clock. One residual boundary was identified (pure dynamic access
in a file that doesn't also contain the string literal "normalizedText"), and
the trade-off was an explicit, documented heuristic rather than a spurious
false positive.

### What "works" means here

Not "CodeQL returned zero hits and we shipped." I ran the same query against
a case-study-shaped regression fixture that models the plausible future
mistake — a developer writes `item.groupDigests?.[gid]?.shd ?? { digest:
item.normalizedText, tags: [] }`. The query fires on both violation
rows, and the safe path in the same file does not. That's the maintenance
signal: if the real code drifts tomorrow, the query catches it.

---

## Evaluation against the seven research criteria

### 1. Expressiveness

**Yes, CodeQL's dataflow reaches this taint-shaped property on a real
codebase.** The specific library construct is
`TaintTracking::Global<ClarifiedToLPConfig>`, parameterized over:

- `isSource`: PropReads with property name `normalizedText`.
- `isSink`: arguments to, and parameters of, functions whose name matches
  `(?i).*(longdigest|generatelong|compresslong|buildlong).*`.
- `isBarrier`: `.digest()` method-call return values (crypto sanitizer) and
  `.groupDigests` property reads (legitimate alternative provenance).
- `isAdditionalFlowStep`: field-store promotion —
  `pw.getRhs() -> pw.getBase()`.

Each of those four knobs was required; dropping any one produced false
negatives or false positives on at least one fixture. Specifically:

- Without taint (strict flow only): missed string transforms, array+join,
  template-string interpolation, Map/get roundtrips.
- Without field-store flow step: missed object wrapping
  (`{ text: entry.normalizedText }`), property renaming, JSON
  stringify/parse roundtrips.
- Without the `digest` barrier: flagged one-way hashes as violations.
- Without the `groupDigests` barrier: false-positive fixture was expected
  to be clean but the field-store step caused spurious taint promotion
  through the whole `item` object into the short-horizon digest read.

Where the expressiveness gets thin:

- **Pure dynamic access in isolation.** `entry[k]` where `k = someVarFromAnotherFile`
  and the string "normalizedText" never appears in the same file is not
  caught. The heuristic (co-occurrence of empty-name PropRead with a
  StringLiteral "normalizedText" in the same file) is a weak proxy for the
  true property, and it would miss a sufficiently distributed obfuscation.
  In practice this is a very low-probability attack shape and would typically
  be caught on code review anyway.
- **eval/new Function()**: CodeQL JS dataflow does not cross these. Not
  in scope for this EARS.
- **Buffer/binary roundtrips**: not modeled. The content is still there
  semantically, so a full model would require additional flow steps for
  common encode/decode pairs. This query doesn't include them; a future
  iteration could.

### 2. Translation fidelity

Much more creative-judgment than Wave 1's structural query. The translation
steps:

1. **Identifying the right source and sink.** The EARS says "normalizedText
   must not flow into long-horizon digest generation." The sink is not a single
   function — it's a family of functions (`generateLongDigest`,
   `buildLongDigestPrompt`, `buildLongDigestSystemPrompt`, and any future long-horizon-prefixed
   helpers). I used a regex-on-name sink to cover the family. That encodes an
   *editorial judgment* that naming convention is load-bearing: rename the
   function to `tier3Compress` and the query loses its target. This is
   tolerable because the overlay manifest documents the coupling and the
   cost to re-author is minutes.

2. **Picking taint over strict flow.** The EARS doesn't literally say "no
   content derived from normalizedText"; it says "long-horizon input is the short-horizon digest,
   not normalizedText." A strict interpretation would admit "normalizedText
   sliced to 200 chars" as technically-not-normalizedText. But the spirit of
   the EARS — hierarchical compression from already-edited material — is
   violated by passing *any* content derived from the raw text. Taint
   captures that spirit better than strict flow.

3. **Deciding where to barrier.** The cryptographic hash is the clean case:
   a one-way function genuinely cannot carry the original content. I added
   `digest` as a barrier. A harder question: would a summarization model's
   output of normalizedText count as sanitized? Semantically yes —
   the output is derived text, not the text. But the query currently doesn't
   model that, and arguably shouldn't, because a developer using
   `llmClient.generateText({ prompt: item.normalizedText })` and then feeding
   the result into long-horizon generation would ALSO violate the EARS (just more indirectly).
   Leaving this unsanitized is the right conservative choice.

4. **Fighting the field-store flow step.** Adding the flow step caused a
   self-inflicted wound: by promoting "x.a tainted → x tainted", the query
   began reporting paths like `item.normalizedText → item → item.groupDigests.shd`.
   This is unsound in the abstract but tolerable if you then barrier
   `groupDigests` reads — which is what I did. That's a creative judgment:
   "this read is a different source of truth, not a derivation."

Iteration count: 6 query versions (v1 exploratory → v2 naive DataFlow → v3
taint → v4 param-sinks + field-store → v5 broader source → v6 path-form +
barriers). Plus one debug query (v4b) to enumerate sinks and sources. Each
failed version produced a specific delta captured by at least one fixture.

### 3. Source-untouched discipline

Confirmed. The case-study codebase shows no modifications to
the processor service (the long-horizon digest file) or the primary LLD
(the EARS source). The existing `git status` changes on that repo are
from other work streams and predate this experiment.

The CodeQL DB reused Wave 1's build; I copied it to `/tmp/codeql-b6-db` to
avoid contending with a sibling experiment's cache lock. No source tree
writes occurred.

### 4. Adversarial depth

Ten fixtures across eight attack dimensions, all outcomes matching design
intent:

| Fixture        | Dimension                                | Design intent                    | Result |
|----------------|------------------------------------------|----------------------------------|--------|
| negative       | baseline violations                      | 3 distinct, all flagged          | 4 rows (two double-covered via param-sink) |
| aliasing       | const x = tainted; longFn(x)               | 3 flagged                        | 3 rows + 3 param-rows |
| object-wrap    | longFn({text: tainted})                    | 3 flagged                        | 3 rows + 3 param-rows |
| collection     | longFn([tainted]), array.join, Map         | 3 flagged                        | 3 rows + 3 param-rows |
| sanitizer      | slice/trim/template / digest (barrier)   | 3 flagged, 1 NOT flagged         | 3 rows + 3 param-rows, hash excluded |
| async          | await/Promise roundtrip                  | 3 flagged                        | 3 rows + 3 param-rows |
| dynamic        | entry[k], Object.entries loop, destruct  | 4 flagged (D1-D4)                | 4 rows + 4 param-rows |
| renamed        | {body: tainted}.body, JSON roundtrip     | 3 flagged                        | 3 rows + 3 param-rows |
| crossfile      | tainted read in helper file              | 1 flagged                        | 1 row + 1 param-row |
| false-positive | safe short-horizon digest flow with normalizedText   | 0 flagged (NOISE CHECK)          | 0 rows |
| regression     | the case-study-shaped wrong-turn           | 2 flagged, safe path NOT flagged | 4 violation rows on 2 violations |

The five dimensions named in the experiment prompt (aliasing, object
wrapping, array/collection, sanitizer, async) are all handled correctly.
Three additional dimensions I added (dynamic access, field renaming,
cross-file) are also handled. The false-positive and regression fixtures
give the result credibility: the query doesn't just fire on everything,
and it would catch a real-world regression.

One dimension I explicitly did NOT solve: a fully distributed obfuscation
where the property name and the access are in separate files. The
heuristic requires co-occurrence in the same file. This is the documented
coverage boundary.

### 5. Coherence-stack fit (pushes Wave 1's boundary)

**Yes.** Wave 1 concluded with an honest note:

> This experiment was favorable-case in one important way: the case-study's
> enforcement code is *one function*, and the DDB `list_append` pattern is
> both syntactically obvious and semantically unambiguous.

B6 picked a deliberately harder property — a content-taint invariant that
depends on "what flows where," not "what the AST looks like at a specific
call site." It required:

- Global interprocedural dataflow (Wave 1 didn't).
- Taint semantics, not strict flow (Wave 1 didn't).
- Field-store flow steps and barriers (Wave 1 didn't).
- Dynamic-access heuristics (Wave 1 didn't).
- Multiple barrier reasoning (Wave 1 didn't).

CodeQL handled all of it. The `TaintTracking::Global` module is stable on
CodeQL 2.25.2 with `codeql/javascript-all@2.6.27`, the `overlay[local]`
pack bug from Wave 1 did not recur here (the query is slightly bigger but
still scoped to the stable parts of the dataflow library), and the runtime
cost was acceptable (~20 seconds on the case-study DB).

This moves the reach boundary from "structural AST invariants" into "content
taint invariants" — a substantively larger class of EARS. It does NOT move
the boundary into:

- **Temporal invariants** (X must happen before Y in trace). Different
  engine territory (LemmaScript, runtime checking, model checking).
- **Cardinality invariants** (at most one concurrent X). CodeQL's dataflow
  doesn't model concurrency.
- **LLM behavioral invariants**. Out of scope for any static tool.

So the dispatch table updates: "dataflow-taint EARS" is now a CodeQL row,
not a "needs a different engine" row.

### 6. Cost

| Phase | Cost |
|---|---|
| Reuse Wave 1 CodeQL install and pack lock | 0 minutes |
| Copy DB to avoid cache-lock contention | ~30 seconds (1.8 GB) |
| v1 exploratory (locate function) | 2 minutes |
| v2 naive DataFlow::Global | 3 minutes write, 2 minutes fixture validation |
| v3 TaintTracking::Global | 3 minutes write, 3 minutes fixture validation |
| v4 parameter-sink + field-store step | 5 minutes write, 4 minutes fixture validation |
| v4b sink/source debug | 4 minutes (hit `desc` reserved-word and `p` keyword bugs) |
| v5 broader source heuristic | 5 minutes write, 3 minutes fixture validation |
| v6 path-problem + barriers | 6 minutes write, 3 minutes fixture validation |
| Negative + 9 adversarial fixtures | 25 minutes (fixture writing + DB builds) |
| Regression fixture | 4 minutes |
| Writeup | 20 minutes |
| **Total wall-clock** | **~80 minutes** |

Per-fixture DB build: ~3 seconds for synthetic TS (few files), ~75 seconds
for the full the case-study tree (reused, so 0 seconds incremental).

Per-query run on the case-study: 18-22 seconds. Per-query run on synthetic
fixtures: <1 second.

Token cost: moderate. Surgical reads of the processor service and the
primary LLD; no whole-file dumps. Most of the token spend was on fixture
authoring and RESULTS.md.

### 7. Maintenance signal

The regression fixture is the direct answer. It models two plausible wrong
turns:

**(a) "Fall back to normalizedText when no short-horizon digest."** This is a
well-meaning bug a future developer might introduce:

```ts
const shortDigest = item.groupDigests?.[groupId]?.shd;
const effectiveShort = shortDigest ?? { digest: item.normalizedText, tags: [] };
const prompt = this.buildLongDigestPrompt(effectiveShort, group);
```

The query fires. Two rows, pointing at lines 42 (the `?? { digest: item.normalizedText`)
and 18 (the parameter of `buildLongDigestPrompt`, reached via taint).

**(b) "New helper path that shortcuts the short-horizon lookup."** A developer writes
a helper that compresses an item directly:

```ts
async retrigger_long(input: { item: Item; group: Group }) {
  return this.buildLongDigestPrompt({ digest: item.normalizedText, tags: [] }, group);
}
```

The query fires. Both rows.

Crucially, the safe path in the same fixture file does NOT fire — the
query does not produce noise for the current legitimate pattern. This is
the signal that LID is after: new-path changes get flagged without
pre-existing-path false positives.

If the case-study moves the long-horizon path to a different naming convention (say,
renames `generateLongDigest` to `tier3Compress`), the regex in the sink
predicate needs updating. This is a cheap config change (one regex line in
the query plus the function-name predicate) but it IS a coupling. The
manifest documents the coupling in the `targets` section.

If the case-study introduces a legitimate sanitizer not currently modeled
(say a custom text-cleaning step), the query will flag it as a violation.
The fix is to add it to `isBarrier`. Again cheap, but requires judgment
about whether the sanitizer genuinely removes content.

---

## Headline answers

### Does CodeQL reach dataflow-taint-style properties on a real codebase?

**Yes, with documented boundaries.** The JavaScript taint-tracking library
is production-capable for EARS of the shape "content from source S must not
reach sink D." The required concepts (global config, barriers, additional
flow steps, path-problem output) are all first-class. The required
adversarial coverage for realistic code patterns (object wrapping, array
wrapping, string transforms, async boundaries, cross-file flow, dynamic
access) is achievable in a single query with 4-5 small predicate
definitions.

### Where does CodeQL hit its wall?

Three walls, one soft, two hard:

1. **Soft: naming-convention coupling in the sink definition.** The query
   matches long-horizon functions by regex. If the convention drifts, the query
   silently loses teeth. Documented in the manifest; recoverable by regex
   update. Not CodeQL's fault per se — any static query has to identify
   the sink somehow.

2. **Hard: truly distributed dynamic access.** `entry[k]` where `k` is a
   variable whose value came from a file that never contains the string
   "normalizedText" is outside the heuristic. A sound version would require
   value-tracking of `k` back to a literal — possible in principle with
   additional CodeQL dataflow on the key expression, but gets into
   diminishing returns fast.

3. **Hard: content-preserving transformations we don't model as
   sanitizers.** LLM summaries, custom encoders, and anything domain-specific
   requires explicit barrier modeling. CodeQL gives you the hooks; you
   have to use them correctly. For long-requires-short this isn't a practical
   problem because the only real sanitizer in play is crypto hashing and
   we covered it.

Where CodeQL would wall hard: **temporal ordering** ("X must happen before Y"
as a trace-level invariant), **concurrency** ("at most one in-flight Z"),
and **LLM behavioral** properties. Those need LemmaScript, model checking,
or runtime verification, not static dataflow.

### Is there a better engine for this shape?

Not for the case-study's scale and shape, given this experiment's results.
Candidates:

- **Semgrep Pro (paid) with dataflow**. Likely equivalent or slightly less
  expressive. Semgrep's OSS version cannot do interprocedural taint without
  Pro. If the coherence stack wanted a lower-friction "oss-friendly" option,
  Semgrep Pro would be the bridge, but CodeQL is a superset.
- **TypeScript branded types** (`Branded<string, 'GEDigest'>` vs.
  `Branded<string, 'NormalizedText'>`). This is a *compile-time* guarantee
  and is strictly better in some senses (it enforces at the edit-time
  feedback loop, not just at overlay-CI time) and strictly worse in others
  (requires invasive source modifications — violates source-untouched; and
  TS erasure means some shape-erasing operations would require casts that
  a motivated bad actor could insert). For LID, branded types should be
  **complementary** to CodeQL, not a replacement. The case-study doesn't
  currently use them; this could be a future LID recommendation.
- **Hand-written AST walker** (e.g. ts-morph). More flexible but much
  higher per-EARS cost, no library ecosystem for dataflow, no barrier/sink
  DSL. Would only win for very project-specific invariants not expressible
  in standard dataflow — which is not this case.

So: CodeQL JS taint tracking is the right tool for EARS of this shape at
this scale. Branded types are a complement worth considering. Semgrep Pro
is a reasonable fallback if CodeQL becomes unavailable.

---

## How to rerun

```sh
# 1. Ensure CodeQL is installed (reused from Wave 1)
brew install --cask codeql

# 2. Install pack deps (one-time, at experiment root)
cd /Users/jess/src/lid/docs/research/experiments/b6-codeql-lp-requires-ge
codeql pack install

# 3. Build or copy the case-study DB
#    (option A — reuse Wave 1)
cp -R /tmp/codeql-thr-det-018/db /tmp/codeql-b6-db
rm -f /tmp/codeql-b6-db/db-javascript/default/cache/.lock

#    (option B — rebuild from source)
codeql database create /tmp/codeql-b6-db \
  --language=javascript-typescript \
  --source-root=/path/to/case-study \
  --overwrite

# 4. Run the invariant check
codeql query run --database=/tmp/codeql-b6-db LONG-REQUIRES-SHORT.ql

# 5. Run all adversarial fixtures
for d in negative aliasing object-wrap collection sanitizer async dynamic renamed crossfile falsepos regression; do
  # (you'd copy fixtures/$d/src to /tmp/b6-$d/src first; see fixtures/)
  codeql database create /tmp/b6-$d/db \
    --language=javascript-typescript --source-root=/tmp/b6-$d --overwrite
  echo "=== $d ==="
  codeql query run --database=/tmp/b6-$d/db LONG-REQUIRES-SHORT.ql
done
```

Expected outputs:

- The case-study DB: zero rows (property verified).
- Negative fixture: 4 rows (3 violations, 2 double-covered).
- Aliasing, object-wrap, collection, renamed, crossfile, async: all-caught.
- Sanitizer: 3 caught; hash excluded.
- Dynamic: 4 caught.
- False-positive: zero rows.
- Regression: 4 rows (2 violations × 2 sinks each).

If the case-study ever yields a non-zero result, investigate: either the long-horizon
path has grown a new helper that reads normalizedText (check the source
location in the output), or the query's barrier set has gone stale and is
over-tainting (check the `groupDigests` barrier is still matching).

---

## Artifacts

| File | Purpose |
|---|---|
| `LONG-REQUIRES-SHORT.codeql` | Canonical overlay artifact (doc-commented, `@kind path-problem`) |
| `LONG-REQUIRES-SHORT.ql` | Symlink to `.codeql`; lets `codeql query run` invoke it directly |
| `LONG-REQUIRES-SHORT.overlay.yaml` | Overlay manifest per research-doc Appendix A |
| `qlpack.yml` | CodeQL pack metadata |
| `codeql-pack.lock.yml` | Pinned library pack versions (same as Wave 1) |
| `RESULTS.md` | This file |
| `v1-locate-generateLP.ql` | Intermediate — CodeQL saw the function |
| `v2-naive-dataflow.ql` | Intermediate — `DataFlow::Global`, caught direct and aliasing only |
| `v3-taint-tracking.ql` | Intermediate — `TaintTracking::Global`, caught string transforms |
| `v4-lpmethods-plus-wrap.ql` | Intermediate — added parameter-sinks + field-store flow step |
| `v4b-sink-debug.ql` | Intermediate — enumerated sinks/sources for the case-study, used to confirm non-vacuity |
| `v5-broader-source.ql` | Intermediate — added dynamic-access source heuristic |
| `v6-path-problem.ql` | Near-final — path-problem form + barriers; promoted to `.codeql` with documentation |
| `fixtures/negative/` | Baseline violation fixture (3 distinct violations) |
| `fixtures/aliasing/` | Adversarial — aliasing via const/let/intermediate vars |
| `fixtures/object-wrap/` | Adversarial — wrapping into object property |
| `fixtures/collection/` | Adversarial — arrays, Map.set/get |
| `fixtures/sanitizer/` | Adversarial — slice/trim/template (flag) + digest (barrier) |
| `fixtures/async/` | Adversarial — await/Promise roundtrips |
| `fixtures/dynamic/` | Adversarial — computed property access |
| `fixtures/renamed/` | Adversarial — field renaming, JSON stringify/parse |
| `fixtures/crossfile/` | Adversarial — flow through a helper in a different file |
| `fixtures/falsepos/` | Control — ge-digest only flow; must NOT flag |
| `fixtures/regression/` | Control — the case-study-shaped wrong-turn; MUST flag; safe path MUST NOT |

CodeQL DBs (`/tmp/codeql-b6-db`, `/tmp/b6-*/db`) are deliberately NOT in
this directory — rebuild from sources per the run instructions above.

---

## Closing note

B6 was designed as a stress test, and it passed. The EARS picked —
hierarchical compression — is exactly the kind of property that "looks
simple" in the LLD but requires dataflow reasoning to verify in code. LLM
instructions and unit tests cover it at two different altitudes; this
CodeQL overlay is the third check, and it covers the specific thing the
other two don't: a structural guarantee that a future change to the code
cannot silently break the invariant without setting off a lint alarm.

The combination pattern is worth naming. Wave 1 found that CodeQL verifies
*convenient structural patterns* — cases where the code has already been
architected to make violation impossible, and the query confirms the
architecture. B6 shows CodeQL also verifies *content-provenance patterns* —
cases where the code has been architected to route two superficially-
similar values through different paths, and the query confirms the
separation has not leaked.

The next layer past this is *behavioral* invariants (temporal ordering,
cardinality, concurrency), and CodeQL does not reach those. That's the
next wall to probe — likely with LemmaScript or runtime-contract engines.
B6 didn't need to find that wall; it just needed to show CodeQL's reach
extends beyond Wave 1's boundary. It does.
