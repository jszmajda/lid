# LID Coach Review

I ran a linked-intent coaching pass over the project. There is one dominant
finding, and it is severe: **every document in the intent chain violates the
core LID principle of "mutation, not accumulation."** The project's own
CLAUDE.md points at the linked-intent-dev workflow, whose foundational rule
(stated verbatim in the LID methodology) is:

> Mutation, not accumulation — docs reflect current intent, not history.

The HLD, the LLD, and the EARS specs are all carrying historical sediment
instead of expressing *current* intent. This is the accumulation anti-pattern,
and it is present in all four files.

---

## Headline finding: accumulation anti-pattern (pervasive)

LID docs are not a changelog, an architecture diary, or a graveyard for
superseded designs. They are a snapshot of what the system *is supposed to be
right now*. History belongs in version control, not in the intent docs. Every
sentence about the past is a sentence a future reader (human or agent) has to
disambiguate against the present — that is exactly the drift LID exists to
prevent.

### 1. docs/high-level-design.md — HLD is accumulating

Problems:

- **`## History` section** ("Originally we used polling. Then we migrated to
  webhooks in Q2... planning to move to a streaming architecture in Q4") —
  pure narrative history. Delete it. The HLD should state the *current*
  approach (webhooks are authoritative) without recounting how we got here.
- **`## Changelog` section** — this is what `git log` is for. A changelog
  embedded in the HLD is accumulation by definition. Delete it.
- **Forward-looking "planning to move to streaming in Q4"** mixed into the
  problem/approach narrative. Future intent that is not yet the system's intent
  does not belong in the authoritative HLD body. If the Q4 streaming move is
  real and committed, track it as future work (a separate planned HLD revision
  or an explicitly fenced "Future" subsection), not woven into the current
  statement of what the system does.

What the HLD should reduce to: the Problem (we track package deliveries) and
the current Approach (we receive webhook events from carriers and persist
them). Roughly three sentences. Everything else is sediment.

### 2. docs/llds/delivery-tracking.md — LLD is accumulating worse

Problems:

- **`## Previous Architecture (Redis)` section** — explicitly documents a
  design that was "deprecated in Q2." A deprecated architecture has zero claim
  on an intent doc. This is the clearest single instance of the anti-pattern
  in the repo. Delete it entirely.
- **`## Context` paragraph** ("We used to keep state in Redis, but now we use
  Postgres. The old Redis-based approach is documented below for reference.")
  — exists only to set up the historical detour. Once the Redis section is
  gone, this collapses to a single line, or vanishes.
- **`## Planned Architecture (Streaming)`** — same problem as the HLD's Q4
  note. Not current intent; should not sit in the authoritative LLD body
  alongside the design that is actually in force.

What the LLD should reduce to: the Postgres design that is actually in force —
"Shipments are rows in the `shipments` table" — plus whatever real detail that
table and its access patterns warrant (which is currently missing; see the
secondary findings below).

### 3. docs/specs/delivery-specs.md — obsolete spec retained "for reference"

Problems:

- **`DELIVERY-002` marked `[obsolete]`** with the parenthetical "Replaced by
  DELIVERY-001; kept for historical reference." This is accumulation at the
  spec level. An obsolete requirement kept around is a trap: a future agent
  doing a coherence audit has to repeatedly re-derive that DELIVERY-002 does
  not apply. Delete the line. The fact that polling was replaced by webhooks
  lives in git history and in the (now-current) DELIVERY-001.
- Note also: `[obsolete]` is not one of the LID status markers. The defined
  markers are `[x]` implemented, `[ ]` active gap, `[D]` deferred. Inventing
  an `[obsolete]` marker to keep dead specs alive is the anti-pattern wearing
  a costume — the correct action for an obsolete spec is removal, not a new
  marker.

What the spec file should reduce to: just `DELIVERY-001` (`[x]` — when a
webhook arrives, the system SHALL persist the event).

---

## Secondary findings

These matter, but they are downstream of fixing the accumulation problem.

### A. The LLD is under-specified once the history is stripped

After deleting the Redis and Streaming sections, the "Current Architecture"
content is a single sentence: "Shipments are rows in the `shipments` table."
That is too thin to be a real LLD. The accumulated history is currently
*masking* the fact that the actual design is barely documented. Once mutated,
the LLD should gain real current-intent detail: the `shipments` schema, how a
webhook event maps onto a row (insert vs. update / upsert key), idempotency on
duplicate webhook deliveries, and ordering/late-event handling. None of that
is specified today.

### B. Spec coverage is thin and traceability is absent

- Only one live requirement (DELIVERY-001), and it is coarse. Webhook
  handling realistically needs specs for: malformed/unauthenticated webhook
  payloads, duplicate delivery (idempotency), out-of-order events, and
  persistence-failure / retry behavior. The HLD even references "retry logic"
  (via its changelog entry) but no EARS spec covers it — that is a missing
  arrow.
- No `@spec` code annotations could be checked because there is no application
  code in the project; if/when code lands, DELIVERY-001 should be annotated
  and a test should reference it for traceability.

### C. CLAUDE.md is minimal but acceptable

`CLAUDE.md` declares `LID Mode: Full` and points at the linked-intent-dev
skill. That is fine for a project this small. No action needed beyond noting
that "Full" mode is what makes the accumulation findings above blocking rather
than advisory — Full mode expects HLD/LLD/EARS to be kept coherent and current.

---

## Recommended actions, in priority order

1. **Mutate the HLD**: delete `## History` and `## Changelog`; remove the
   embedded Q2/Q4 narrative; leave only the current Problem + Approach.
2. **Mutate the LLD**: delete `## Previous Architecture (Redis)`, collapse
   `## Context`, and either remove `## Planned Architecture (Streaming)` or
   move it into a clearly-fenced future-work note that is not presented as
   current intent.
3. **Mutate the spec**: delete the `[obsolete]` `DELIVERY-002` line; do not
   introduce non-standard status markers.
4. **Then re-deepen** the LLD and EARS to actually describe current intent
   (schema, idempotency, retry, error handling) — the history was hiding how
   shallow the real design docs are.

The single most important takeaway: **stop keeping the past in the intent
docs.** Git remembers history so the docs don't have to. Every "previously /
originally / planned for Q4 / kept for reference" passage in this project is a
LID violation and a future drift source.

---

*Note: I performed this review manually (the /lid-coach skill was not available
in this environment) and did not modify any project files — a coaching pass is
advisory. The mutations above are recommendations to apply via a follow-up
linked-intent-dev pass.*
