# storage specs

**LLD**: docs/llds/storage.md

Status markers: `[x]` implemented · `[ ]` active gap · `[D]` deferred

---

## `put(url)` Contract

- `[ ]` **USH-STORE-001**: When `put(url)` is called with a URL that has never been stored, the system SHALL allocate a new unique integer ID (strictly greater than any previously-allocated ID), persist the `{ id, url }` mapping, and return `{ id, code, url, is_new: true }` where `code` is the base62 encoding of `id`.
- `[ ]` **USH-STORE-002**: When `put(url)` is called with a URL that is already stored, the system SHALL return the existing `{ id, code, url, is_new: false }` without allocating a new ID.
- `[ ]` **USH-STORE-003**: When two concurrent `put(url)` calls are made with the same URL, exactly one call SHALL receive `is_new: true` with a newly-allocated ID, and all other concurrent calls SHALL receive `is_new: false` with the same ID.
- `[ ]` **USH-STORE-004**: After `put(url)` returns successfully, subsequent `get(id)` and `lookup_by_url(url)` calls SHALL return the stored mapping immediately — no eventual-consistency window.
- `[ ]` **USH-STORE-005**: When `put` fails (e.g., backend unavailable, disk full), the system SHALL NOT leave a partial mapping. The mapping is either fully stored or not stored at all.

## `get(id)` Contract

- `[ ]` **USH-STORE-006**: When `get(id)` is called with an integer ID that exists in storage, the system SHALL return `{ url, code }` where `url` is byte-for-byte identical to the URL passed to the `put` that created the mapping, and `code` is the base62 encoding of `id`.
- `[ ]` **USH-STORE-007**: When `get(id)` is called with an ID that does not exist in storage, the system SHALL return `null`.
- `[ ]` **USH-STORE-008**: When `get(id)` is called successively at times T1 and T2 (T2 > T1) with the same ID and both calls succeed, both calls SHALL return the same URL.

## `lookup_by_url(url)` Contract

- `[ ]` **USH-STORE-009**: When `lookup_by_url(url)` is called with a URL that exists in storage (byte-for-byte match), the system SHALL return the `{ id, code }` of the existing mapping.
- `[ ]` **USH-STORE-010**: When `lookup_by_url(url)` is called with a URL that does not exist in storage, the system SHALL return `null`.
- `[ ]` **USH-STORE-011**: `lookup_by_url` SHALL match URLs byte-for-byte. Two URLs differing by case, trailing slash, query-parameter order, or any single character SHALL be treated as distinct entries.

## Data Integrity

- `[ ]` **USH-STORE-012**: IDs allocated by `put` SHALL be monotonically ascending. Gaps in the ID sequence (from aborted puts) SHALL be permitted.
- `[ ]` **USH-STORE-013**: The system SHALL support IDs up to 2^63 - 1 (64-bit signed integer). 32-bit IDs are insufficient.
- `[ ]` **USH-STORE-014**: The system SHALL preserve URL content exactly — no truncation, no re-encoding, no normalization — from `put` input through `get` output.

## Error Propagation

- `[ ]` **USH-STORE-015**: When the underlying backend is unavailable, the system SHALL return an error from any of `put`, `get`, or `lookup_by_url` rather than returning stale or fabricated data.
