# LLD: storage

## Context and Design Philosophy

Storage is the persistence layer for URL ↔ code mappings. This LLD specifies the *contract* — what operations must exist and what guarantees they must provide. It deliberately does **not** specify the backend. SQLite, Postgres, Redis, DynamoDB, a JSON file on disk, or any equivalent system can satisfy this contract; the implementation picks one.

Why contract-only: separating the persistence contract from the shortener-core lets the implementation evolve independently and lets reviewers verify *intent* rather than *plumbing*.

## Operations

Three operations. All are synchronous from the caller's point of view; async implementations wrap them behind a uniform interface.

### `put(url) → { id, code, url, is_new }`

Store a URL and return its ID and short code. If the URL was already stored, return the existing mapping — `is_new` is `false` in that case, `true` when a new ID was allocated.

**Atomicity**: `put` is atomic with respect to concurrent calls for the *same URL*. Two concurrent `put("X")` calls both return the same `{ id, code }` — exactly one saw `is_new: true`, the other saw `is_new: false`. Implementations typically achieve this with:

- A unique index on the URL column and a `INSERT ... ON CONFLICT DO UPDATE RETURNING` (Postgres / SQLite).
- A check-then-set loop using optimistic concurrency (Redis, DynamoDB).
- A transaction with `SELECT ... FOR UPDATE` + conditional insert (Postgres).

No specific approach is mandated — the guarantee is.

### `get(id) → { url, code } | null`

Return the URL mapping for a given integer ID, or null if the ID is not stored.

**Consistency**: returns the value of the most recently-committed `put` with that ID (or a later assignment), never returns a value that was never stored, never returns a mid-transaction state. A code that existed at time T1 (per a `get` call) and exists at time T2 MUST have the same URL at both times.

### `lookup_by_url(url) → { id, code } | null`

Return the ID and code for a given URL, or null if the URL is not stored.

This is the duplicate-detection operation used by `put` internally. Implementations with a unique index on URL can implement `lookup_by_url` as a simple indexed read.

## Data Shape

Each stored entry has at minimum:

- `id` — integer, ascending, assigned by the store on `put`.
- `url` — the submitted URL, stored byte-for-byte.
- `code` — the base62 encoding of `id`. Can be derived on read rather than stored; implementations choose.
- (optional) `created_at` — timestamp. Not required by any behavior; operators may want it for operational visibility.

IDs are monotonically ascending. `put` allocates the next available ID atomically. Gaps in the ID sequence are permitted (e.g., if a failed `put` consumed an ID before aborting).

## Consistency Guarantees

- **Strong read-after-write** within a single code: a successful `put` makes the mapping visible to `get` and `lookup_by_url` immediately. No "newly-created code returns 404 for a few seconds."
- **No partial writes**: a `put` either completes (mapping is fully stored) or fails (mapping is not stored at all). There is no state where `id` exists but `url` is empty.
- **Idempotent puts**: calling `put(X)` many times returns the same mapping every time. Storage does not deduplicate *submissions* (incrementing a counter is fine) but *logical state* is unchanged.

The store does not need to provide cross-key transactions. No operation touches multiple keys atomically.

## Error Cases

- **Backend unavailable** (network, process crash, etc.): operations return an error; the shortener-core propagates it; the API returns 503.
- **Unique-index conflict during `put`**: handled internally by the atomicity mechanism (retry / conflict resolution). Callers never see this error directly.
- **Corrupt data** (stored URL is non-UTF-8, truncated, etc.): not a normal operating condition. Implementations may panic or surface a 500. Not spec'd further.

## Sizing

Order-of-magnitude targets, not hard requirements:

- **Codes generated**: up to ~10^9 for a hobby deployment, ~10^11 for a large one. A 64-bit integer ID covers this easily; avoid 32-bit.
- **URL length**: up to ~2000 characters (browser practical limit for GET URLs; POST submissions could theoretically exceed this). Storage columns should accommodate.
- **Throughput**: low for hobby use (< 10 `put` per second, < 1000 `get` per second). Implementations backed by a single-file SQLite on a small VM handle this easily.

## Decisions & Alternatives

| Decision | Chosen | Alternatives Considered | Rationale |
|---|---|---|---|
| Backend | Unspecified (contract only) | Mandate SQLite / Postgres / Redis | Implementation should pick the backend that fits its deployment. The contract is what matters. |
| Atomicity mechanism | Caller-opaque; contract-level | Require explicit transactions in the API | Different backends have different primitives (SQL transactions, Redis MULTI, DynamoDB ConditionExpression). Exposing this in the contract would couple the API to a specific backend family. |
| Code generation location | Derivable from ID; storage may or may not store it | Always store code as separate field | Deriving keeps the authoritative source as the integer. But implementations that want to index by code directly can store it. Either works. |
| URL canonicalization | None at storage layer | Normalize before store | The HLD's byte-for-byte fidelity goal means storage stores exactly what `put` received. Canonicalization is an HLD-level decision already rejected. |
| Cross-key transactions | Not required | Snapshot-isolation across all keys | No operation touches multiple entries atomically. Single-key guarantees suffice. |

## Open Questions & Future Decisions

### Resolved

1. ✅ Contract-only LLD; implementer picks backend.
2. ✅ Atomic per-URL puts.
3. ✅ 64-bit IDs, ascending, gaps permitted.

### Deferred

1. **Bulk operations.** `put_many` and `get_many` for clients submitting many URLs at once. Not required by current API; an obvious optimization if write throughput becomes a concern.
2. **Backup and restore.** Operational concern, not intent. Implementations pick a backup strategy based on backend.
3. **Archival / deletion.** Operators may want to delete mappings after some criterion. Not in scope; would require a new operation.

## References

- `docs/high-level-design.md`
- `docs/llds/shortener-core.md` — the only consumer of this contract.
- `docs/specs/storage-specs.md`
