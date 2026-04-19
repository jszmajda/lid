# shortener-core specs

**LLD**: docs/llds/shortener-core.md

Status markers: `[x]` implemented · `[ ]` active gap · `[D]` deferred

All specs start `[ ]` — this is intent only. Flip to `[x]` as tests/code land that satisfy each spec.

---

## Encoding

- `[ ]` **USH-CORE-001**: The system SHALL encode an integer ID into a base62 string using the alphabet `0-9A-Za-z` (62 characters), with `0` mapping to digit `0` and `61` mapping to digit `z`.
- `[ ]` **USH-CORE-002**: The system SHALL produce the minimum-length base62 encoding for any given non-negative integer ID — no leading zeros except when the ID is literally 0.
- `[ ]` **USH-CORE-003**: The system SHALL decode a base62 string back to the integer ID it encodes, such that `decode(encode(n)) == n` for all non-negative integers up to 2^63 - 1.
- `[ ]` **USH-CORE-004**: When given a short code containing any character outside the base62 alphabet, the system SHALL return a decoding error without consulting storage.

## Shortening

- `[ ]` **USH-CORE-005**: When `shorten(url)` is called with a syntactically valid URL that has never been stored, the system SHALL allocate a new integer ID via storage, encode it to a short code, persist the mapping, and return `{ code, url }` where `url` is byte-for-byte identical to the input.
- `[ ]` **USH-CORE-006**: When `shorten(url)` is called with a URL that has already been stored, the system SHALL return the existing `{ code, url }` without allocating a new ID. The returned code MUST equal the code returned by the original call.
- `[ ]` **USH-CORE-007**: When two concurrent `shorten(url)` calls are made with the same URL, both callers SHALL receive the same short code, and exactly one storage `put` SHALL allocate a new ID.
- `[ ]` **USH-CORE-008**: The system SHALL NOT perform URL normalization (lowercasing, query-parameter sorting, trailing-slash stripping, etc.) before storage. URLs that differ by any byte are stored as distinct entries.

## Resolving

- `[ ]` **USH-CORE-009**: When `resolve(code)` is called with a valid base62 code that exists in storage, the system SHALL return `{ url }` where `url` is byte-for-byte identical to the URL stored at that ID.
- `[ ]` **USH-CORE-010**: When `resolve(code)` is called with a valid base62 code that does not exist in storage, the system SHALL return `null`.
- `[ ]` **USH-CORE-011**: When `resolve(code)` is called with a malformed code (characters outside the base62 alphabet, empty string), the system SHALL return `null` without consulting storage.

## URL Validation

- `[ ]` **USH-CORE-012**: The system SHALL accept URLs with `http://` or `https://` scheme and reject all other schemes (including but not limited to `file://`, `javascript:`, `data:`, `ftp://`).
- `[ ]` **USH-CORE-013**: The system SHALL reject empty strings, strings consisting only of whitespace, and strings without a scheme as invalid URLs.
- `[ ]` **USH-CORE-014**: The system SHALL NOT validate that the URL's destination is reachable, safe, or non-malicious.

## Error Propagation

- `[ ]` **USH-CORE-015**: When the underlying storage operation fails, the system SHALL propagate the error to the caller without swallowing it or returning a placeholder result.
