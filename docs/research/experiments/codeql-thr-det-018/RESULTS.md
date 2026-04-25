# Experiment 1 Results — CodeQL structural overlay for FEAT-DET-018

**Date**: 2026-04-22
**Status**: VERIFIED
**Artifact**: `FEAT-DET-018.codeql` (executable as `FEAT-DET-018.ql` via symlink)
**Manifest**: `FEAT-DET-018.overlay.yaml`
**DB location**: `/tmp/codeql-thr-det-018/db` (not committed — rebuild instructions below)

---

## Verdict

**Verified** — the structural half of FEAT-DET-018 is enforced by the case-study
codebase. Every production code path that writes an Entry's `groupIds` is
monotonically additive. The CodeQL query surfaced exactly three hits in the
the case-study tree, all classified safe:

1. **ADDITIVE** — `<case-study>/src/runner.ts:687`
   The only DynamoDB write to `groupIds` uses
   `SET groupIds = list_append(if_not_exists(groupIds, :empty), :newThread)`.
   `list_append` is the DynamoDB expression-language operator for array
   concatenation; composed with `if_not_exists` it creates-or-appends. This
   operator cannot drop existing elements, full stop.

2. **PROPAGATION** — `<case-study>/src/persistence/types.ts:671`
   The marshaller `itemToRecord` does `record.groupIds = item.groupIds`.
   Identity copy — does not mutate.

3. **PROPAGATION** — `<case-study>/src/persistence/types.ts:700`
   The unmarshaller `recordToItem` does the mirror identity copy.
   Does not mutate.

Zero VIOLATION, zero UNCLASSIFIED, zero PUT-COMMAND, zero PUT-REQUEST hits
in production code.

### Negative control

A synthetic fixture at `/tmp/codeql-thr-det-018-negative/src/fake-violation.ts`
intentionally commits five kinds of violation. The same query flags each one:

| Synthetic violation | Line | Classification |
|---|---|---|
| `SET groupIds = :t` (bare SET) | 14 | VIOLATION (channel 1) |
| `PutCommand({ Item: { ..., groupIds: [...] } })` | 26 | VIOLATION + PUT-COMMAND |
| `BatchWriteCommand({ RequestItems: { ..., [{ PutRequest: { Item: { ..., groupIds: [...] } } }] } })` | 36 | VIOLATION + PUT-REQUEST |
| `item.groupIds = ['reset']` (in-memory non-empty literal) | 44 | VIOLATION (channel 4) |
| `item.groupIds = freshVar` (opaque RHS) | 49 | UNCLASSIFIED |

This gives the query teeth: it fires on the shapes we care about, and the
the case-study tree happens to contain none.

### Coverage boundary

The overlay verifies the **code-visible** half of FEAT-DET-018: whatever
`groupIds`-writing code the system has, it preserves pre-existing elements.
The **prompt-visible** half — the LLM being instructed not to drop
assignments — is behavioral; the existing unit test at
`<case-study>/src/services/processor.service.test.ts:205`
(`/** @spec FEAT-DET-018 */`) asserts the prompt contains the
`never.*drop.*pre-existing` phrase. That's a good complement: even if the
model ignores the instruction, the DB layer physically cannot drop
assignments, because the only write path uses `list_append`. The two
together make the EARS stick at both ends.

---

## Evaluation against the seven research criteria

### 1. Expressiveness

Does CodeQL actually capture the EARS semantics, or only approximate it?

**Mostly captures, with an honest boundary.** The EARS reads:

> The classification prompt shall instruct the model to never remove existing
> group assignments shown in `<assigned-groups>` tags — only add new
> assignments.

Literally the EARS is about an LLM prompt. CodeQL cannot reason about an
LLM's behavior. But the behavioral invariant the EARS is trying to enforce —
"the pipeline's final `groupIds` for an entry is a superset of its input
`groupIds`" — is exactly structural, and CodeQL captures it cleanly. The
key insight is that **the case-study's architecture has already made this
impossible to violate even if the LLM misbehaves**: the LLM's output doesn't
go through a replacement write; it goes through an additive update. CodeQL
verifies that architectural choice.

Put differently: the EARS expresses an *intent*; the overlay verifies a
*property* that makes the intent redundant. If the LLM drops an assignment,
the `list_append`-only write path cannot remove it. That's a stronger
guarantee than the prompt alone provides, and CodeQL is the right tool to
check it.

The edge where expressiveness gets thin: the `PROPAGATION` classification
trusts that the source object is itself legally-shaped. This is a local
invariant; a truly sound check would trace origin back to either a DB read
or an Entry constructor. The CodeQL JavaScript dataflow libraries can express
this with `DataFlow::Configuration`, but the extra cost isn't justified for
the handful of call sites and the strong TS type wall around `Entry`. Noted
in the manifest as a soundness-by-convention leak.

### 2. Translation fidelity

Does EARS → CodeQL feel mechanical, or does it require creative judgment?

**Mostly creative judgment, once.** The mechanical part was: "write a
structural invariant checker for groupIds." The creative part was
identifying the right structural invariant — `list_append`-only —and the
right write channels — DDB UpdateExpression strings, PutCommand.Item,
BatchWriteCommand.PutRequest.Item, and in-memory PropWrites. That required
reading the enforcement code and deciding what counts as a "write" in a
DynamoDB-first TypeScript service. A cold EARS-to-query machine couldn't
have produced this.

However, the translation is reusable. "Find every write to field F; each
must be provably additive" is a pattern that applies to any collection-
typed field whose EARS is "never remove." I suspect a template query could
parameterize over field name, path filters, and channel list, and regenerate
90 percent of this artifact for the next preservation-shaped EARS.

Iteration count: six query versions (v1-debug → v6-final), five query runs
on the case-study, two query runs on negative control. The first version was a
discovery query to find where `groupIds` lives. The second tried a regex
shape that was too strict (zero hits). The third got the DDB channel
correct. The fourth tried to encode four channels at once and tripped a
CodeQL library bug (`overlay[local]` dependency cycle in a pack unrelated
to my code, diagnosed by process of elimination). The fifth got three
channels working but the fourth channel used the wrong AST anchor — the
negative fixture surfaced this; the sixth corrected it.

### 3. Source-untouched discipline

Confirm no modifications to the case-study codebase.

**Confirmed.** `git diff --stat` on the three files touched by the query
(`<case-study>/src/runner.ts`,
`<case-study>/src/services/processor.service.ts`,
`<case-study>/src/persistence/types.ts`) shows zero bytes changed.
The CodeQL database was built against an unmodified source root; all query
artifacts live in `/Users/jess/src/lid/docs/research/experiments/` (the
research repo, not the case-study). The only the case-study write path was
CodeQL's own extractor creating a `src.zip` inside `/tmp/codeql-thr-det-018/db`,
which is a CodeQL working directory, not the source tree.

### 4. `@spec` co-location

Does threading the ID through EARS → code → query feel natural?

**Yes, with one gap.** The EARS ID `FEAT-DET-018` appears in:

- `docs/specs/FEAT.md` (the EARS itself)
- `<case-study>/src/services/processor.service.ts:108`
  (`@spec FEAT-DET-016, FEAT-DET-018` — on the system-prompt builder)
- `<case-study>/src/services/processor.service.test.ts:205`
  (`/** @spec FEAT-DET-018 */` — on the prompt-side unit test)
- The overlay artifact filename and `@id` annotation in the `.codeql` file
- The overlay manifest `spec_id` field

What's missing is an `@spec FEAT-DET-018` annotation on `addGroupIdToItem`
itself — the function that structurally enforces the invariant. Currently
the code-side of FEAT-DET-018 is only annotated at the prompt-builder, which
is the *upstream* half. If someone greps for FEAT-DET-018 looking for the
enforcement, they land on the prompt, not the write. This is a legitimate
opportunity for the overlay to nudge back into the source as a review-time
comment (not as a LID code edit — per the source-untouched rule — but as a
human task surfaced by `_status.yaml`).

Concretely: when the overlay reports "FEAT-DET-018 verified structurally at
runner.ts:687," a reviewer can optionally add an `@spec`
comment there on a future unrelated edit. The overlay doesn't force it, but
it provides the evidence that would motivate it.

### 5. Arrow-overlay fit

Does the manifest + artifact pattern feel LID-shaped?

**Yes.** The artifact is a file with a shebang-like header (`@name`,
`@description`, `@id`, `@tags`). The manifest is a YAML sidecar that
declares engine, targets, witnesses, status, and last_run. The directory
structure sits naturally alongside `docs/arrows/` and `docs/specs/` — you
could drop `docs/overlay/primary/` into the case-study tree and the
existing LID tooling wouldn't blink. The status marker (`V` here)
composes with EARS's `[x]` and the arrow's own markers.

The one shape question: the research doc proposes storing overlay files
per-arrow (`docs/overlay/primary/*`). I put this one in a research
experiments directory instead, because it's research, not production
overlay. But the layout is identical — rename the directory, it's ready.
This suggests the research-to-production promotion is one `mv`.

The `_status.yaml` roll-up isn't modeled here (one spec, no siblings), but
the manifest would slot into one trivially. `last_run.result: verified` is
exactly the shape a roll-up would aggregate.

### 6. Cost

Setup time, install steps, query iteration count, any paid tools needed.

| Phase | Cost |
|---|---|
| Install CodeQL CLI (`brew install --cask codeql`) | 1 minute (background) |
| `codeql pack download codeql/javascript-all` | 30 seconds |
| Build CodeQL DB on the case-study (`codeql database create`) | 1 min 18 sec |
| First passing query | Query 3 (after 2 throwaway drafts) |
| Final query | Query 6 |
| Wall-clock start to final result | ~35 minutes elapsed |
| Paid tools | None |

The CodeQL CLI, JavaScript extractor, and `codeql/javascript-all` library
pack are all free and open source (GitHub). The Homebrew cask ships CodeQL
2.25.2. The only compatibility wrinkle was that version 2.25.2 of the CLI
plus version 2.6.27 of `codeql/javascript-all` emit spurious
`overlay[local] but depends on global entity` errors for queries that
transitively import `ApiGraphs.qll` — specifically triggered by anything
that pulls the full `semmle.javascript.dataflow` graph. The fix was to stay
inside the smaller surface area (`DataFlow::PropWrite`, `NewExpr`,
`ObjectExpr`, `Property`). This didn't materially limit me; it just meant
the query is a touch more syntactic than it could be with full dataflow.

Iteration discipline: each failed query produced a specific, actionable
delta. No query was thrown away on vibes. The negative-control fixture
was critical — it flushed out the Channel-2 bug (wrong AST anchor for
nested `Item.groupIds`) that I would otherwise not have noticed, since
the case-study tree has zero PutCommand-with-groupIds writes.

Token usage: moderate. The file reads were surgical (targeted offset/limit
on a 1081-line file), the grep results were parsed locally, and the query
writes were small diffs. No whole-codebase dumps were needed.

### 7. Maintenance signal

If FEAT-DET-018 changed tomorrow, what about the overlay would need updating?

Three cases:

**(a) EARS weakens** — "drops allowed when group is archived". The
query wholly misrepresents the new spec. The manifest `status` should flip
to `[Vx]` (attempted, blocked) pending a revised query; the query either
needs a predicate "write is allowed if the group is archived" (hard — would
need taint-tracking to connect the groupId to a group record) or the
engine should change (manual-review signoff, or runtime contracts). The
overlay dispatcher should read the EARS diff and flag the query for
re-authoring.

**(b) EARS strengthens** — "never remove AND never reorder". Channel 4's
`PROPAGATION` classification still holds (copy preserves order). Channel 1's
`list_append` preserves order. Adding "never reorder" probably costs one
extra query predicate checking for `sort`, `reverse`, `filter`, etc. called
on a groupIds value. That's a 10-minute edit.

**(c) Storage layer moves off DynamoDB** — say to Postgres. Channels 1-3
become unreachable (there are no DDB `UpdateCommand` strings in the code).
Channel 4 becomes load-bearing, which is where the current query's weakest
coverage lives. The manifest `engine` field might stay `codeql` but the
`targets` would change, and the query would need new channels for SQL query
strings (or an ORM's equivalent). Expected cost: 2-3 query iterations to
find the new write sites.

**(d) A new entries-write path is added** — e.g. a migration script using
`PutCommand` with an Entry shape. The query will auto-catch it: a
`PUT-COMMAND` classification forces human review. No manifest changes
needed; the overlay's CI hook does its job. This is the strongest
maintenance-win of the whole setup — new write channels surface
automatically without manual re-translation.

---

## How to rerun

```sh
# 1. Ensure CodeQL is installed
brew install --cask codeql

# 2. Install the JS pack (one-time)
codeql pack download codeql/javascript-all

# 3. Build the DB (if not already present)
cd /tmp && mkdir -p codeql-thr-det-018 && cd codeql-thr-det-018
codeql database create ./db \
  --language=javascript-typescript \
  --source-root=/path/to/case-study \
  --overwrite

# 4. Install this query's pack deps
cd /Users/jess/src/lid/docs/research/experiments/codeql-thr-det-018
codeql pack install

# 5. Run the invariant check
codeql query run --database=/tmp/codeql-thr-det-018/db FEAT-DET-018.ql

# 6. Run against the negative control (confirms the query has teeth)
codeql query run --database=/tmp/codeql-thr-det-018-negative/db FEAT-DET-018.ql
```

Expected output on the case-study DB:

```
| 'SET th ... = :now' | ADDITIVE — <case-study>/src/runner.ts:687 — ... |
| item.groupIds      | PROPAGATION — <case-study>/src/persistence/types.ts:671 — ... |
| threadI ... readIds | PROPAGATION — <case-study>/src/persistence/types.ts:700 — ... |
```

Three rows, all green. If a future change introduces a fourth row with
classification VIOLATION, PUT-COMMAND, PUT-REQUEST, or UNCLASSIFIED, the
overlay CI hook should fail and escalate to human review.

---

## Artifacts

| File | Purpose |
|---|---|
| `FEAT-DET-018.codeql` | Canonical overlay artifact (readable, `@name`-annotated) |
| `FEAT-DET-018.ql` | Symlink to `.codeql`; lets `codeql query run` invoke the file directly |
| `FEAT-DET-018.overlay.yaml` | Overlay manifest per research-doc Appendix A |
| `qlpack.yml` | CodeQL pack metadata (declares `codeql/javascript-all` dep) |
| `codeql-pack.lock.yml` | Pinned library pack versions |
| `RESULTS.md` | This file |
| `v3-ddb-groupIds-writes.ql` | Intermediate — channel-1-only; kept for reference |
| `v4-full-invariant.ql` | Intermediate — triggered the CodeQL lib bug; kept as a cautionary tale |
| `v5-full-invariant.ql` | Intermediate — three channels, working; promoted to v6 after negative-control feedback |
| `v6-full-invariant.ql` | Final working version; identical content to `FEAT-DET-018.codeql` (the `.codeql` differs only in the doc header) |

The CodeQL DB itself (`/tmp/codeql-thr-det-018/db`, 328 MB) is deliberately
NOT in this directory — rebuild from source per the steps above.

---

## Closing note

This experiment was favorable-case in one important way: the case-study's
enforcement code is *one function*, and the DDB `list_append` pattern is
both syntactically obvious and semantically unambiguous. The CodeQL overlay
didn't do heroic work — it correctly identified a property the code was
already structured to guarantee. That's the *right* outcome for a first
experiment: the engine shouldn't be discovering bugs from thin air; it
should be confirming architectural choices that humans made for good
reasons, with a mechanical artifact that stays honest as the code evolves.

Where it would earn its keep is on the next change. If a developer adds a
migration path that writes entries with `PutCommand`, the overlay fires
automatically. If someone "simplifies" `list_append` to `:set`, the overlay
fires. If the code moves to SQL, the overlay gracefully degrades — the
query runs clean (because there are no DDB writes to flag) and a reviewer
notices that the overlay is now vacuously satisfied, which itself is a
useful signal.

The biggest question left open isn't about CodeQL — it's about the
*overlay dispatcher*. One query per EARS works for an experiment. A fleet
of 50 queries across 5 engines, auto-dispatched on EARS diff, is a
different engineering problem. That's Experiment 3's territory, and
beyond.
