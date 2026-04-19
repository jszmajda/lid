# LLD: shortener-core

**Created**: 2026-04-18
**Status**: Design Phase (intent-only example; code to be generated)

## Context and Design Philosophy

The shortener core is the one component whose behavior stays fixed regardless of transport or storage backend. It turns an ascending integer ID into a compact short code and back again, and ensures that submitting the same URL twice produces the same code.

The core depends on storage (for the `lookup-by-url`, `put`, `get` operations) but not on the API layer. It exposes a small functional interface; the API calls it and the core calls storage. See `storage.md` for the storage contract.

## Short-Code Encoding

Short codes are base62-encoded ascending integer IDs.

**Alphabet**: `0-9`, `A-Z`, `a-z` — 62 characters total.

**Encoding**: Take the integer ID, repeatedly divide by 62 and emit the alphabet character for each remainder, least-significant first, then reverse. Value 0 encodes to `"0"`; value 61 encodes to `"z"`; value 62 encodes to `"10"`; value 3843 (62² - 1) encodes to `"zz"`; value 238327 (62³ - 1) encodes to `"zzz"`.

**Decoding**: The reverse — parse each character as a base-62 digit (0-9 → 0-9, A-Z → 10-35, a-z → 36-61), accumulate by multiplying. Any character outside the alphabet is an invalid code.

Variable length is a deliberate choice. Six characters covers 62⁶ ≈ 56 billion entries; seven characters covers 62⁷ ≈ 3.5 trillion. The system never produces a code with leading "0" unless the code *is* "0" — `encode(62)` is `"10"`, not `"010"`.

## Duplicate Handling

Before assigning a new short code, the core checks whether the submitted URL has already been assigned one via storage's `lookup-by-url` operation. If it has, the existing code is returned. If not, a new ID is allocated from storage, encoded, and persisted.

This requires storage to support reverse lookup (URL → ID), not just forward lookup (ID → URL). See `storage.md`.

The operation is **strongly consistent**: two concurrent requests for the same URL MUST NOT produce two different codes. Storage must serialize the `lookup-by-url` + `put` pair atomically. Implementations can achieve this with a database transaction, an optimistic retry loop, or an insert-ignore + re-read pattern.

## URL Validation

Before attempting to shorten a URL, validate that the input is a syntactically-valid URL. Accept `http://` and `https://` schemes. Reject empty strings, strings without a scheme, and strings with disallowed schemes (`file://`, `javascript:`, `data:`, etc.).

Normalization is deliberately **not** performed. The HLD's Round-Trip Fidelity goal means `http://example.com/` and `http://example.com` are treated as different URLs and receive different short codes. Users who want canonicalization normalize before submission.

## Interface

The core exposes three operations. Signatures are illustrative; exact shape is the implementer's choice.

- `shorten(url) → { code, url }` — validates the URL, looks up existing code, or allocates a new one via storage. Returns the short code and the stored URL (byte-for-byte with input).
- `resolve(code) → { url } | null` — decodes the code to an ID, calls storage's `get(id)`, returns the URL or null if the ID is not stored.
- `validate(url) → ok | { error }` — pure function; checks scheme and syntax without touching storage.

## Error Cases

- **Invalid URL** (malformed, unsupported scheme): `shorten` returns a validation error without touching storage.
- **Invalid short code** (characters outside base62 alphabet, empty): `resolve` returns null without touching storage.
- **Valid-looking code but no stored mapping**: `resolve` returns null. This is how unknown codes get a 404 at the API layer.
- **Storage unavailable**: core propagates the error upward. API translates to 5xx.

## Decisions & Alternatives

| Decision | Chosen | Alternatives Considered | Rationale |
|---|---|---|---|
| Encoding | Base62 | Base58 (Bitcoin-style; omits ambiguous chars); Base64 URL-safe (65 chars if + and / substituted); hash | Base62 balances compactness with URL safety. Base58 is marginally shorter but needs separate digits; Base64's two special characters complicate URLs. Hashes require collision handling. |
| Encoding direction | Ascending integer ID | Per-URL hash; random | Ascending is free (storage already has an autoincrement ID or equivalent) and produces the shortest possible codes. Hashes and randoms require collision checks and waste bytes. |
| Concurrency model | Serialized `lookup + put` | Optimistic retry; per-URL locking | The serialized model is simplest and pushes the complexity to storage where it belongs. Two concurrent submissions of the same URL both see the same result. |
| URL normalization | None | Lowercase scheme and host, sort query params | Breaks Goal 1 (round-trip fidelity). Users can normalize before submitting. |

## Open Questions & Future Decisions

### Resolved

1. ✅ Base62 with variable-length codes.
2. ✅ Deterministic per-URL (duplicate handling).
3. ✅ No normalization; byte-for-byte fidelity.

### Deferred

1. **Code reservation / vanity codes.** Not in scope; explicitly non-goal per HLD. Could be added later with a second `put-with-code` storage operation.
2. **Sharding of the ID counter.** For implementations distributing storage, a single ascending counter is a bottleneck. A 64-bit integer and per-shard offsets or a Snowflake-style ID would solve it. Not needed at the example's scale.

## References

- `docs/high-level-design.md`
- `docs/llds/api.md` — how the core is invoked.
- `docs/llds/storage.md` — the contract the core depends on.
- `docs/specs/shortener-core-specs.md`
