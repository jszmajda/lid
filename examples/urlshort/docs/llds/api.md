# LLD: api

## Context and Design Philosophy

The API is the HTTP surface of the URL shortener. Two endpoints: create a short code, follow a short code. The API is intentionally thin — it translates between HTTP and the shortener-core's interface, handles error-to-status mapping, and does nothing else. No authentication, no rate limiting, no analytics.

## Endpoints

### POST /shorten

**Request**:
```
POST /shorten
Content-Type: application/json

{ "url": "https://example.com/some/long/path?with=params" }
```

**Response (200)**:
```
Content-Type: application/json

{
  "code": "1A",
  "short_url": "https://short.example/1A",
  "url": "https://example.com/some/long/path?with=params"
}
```

`short_url` is the full URL the caller can share; `code` is the bare short code. The `url` field echoes back what was stored, byte-for-byte.

**Response (400)** — malformed or invalid URL:
```
Content-Type: application/json

{ "error": "invalid_url", "message": "URL must have an http or https scheme." }
```

**Response (5xx)** — storage failure:
```
Content-Type: application/json

{ "error": "storage_unavailable", "message": "..." }
```

### GET /:code

**Request**:
```
GET /1A
```

**Response (302)** when the code exists:
```
HTTP/1.1 302 Found
Location: https://example.com/some/long/path?with=params
```

No response body required. The `Location` header is exactly the stored URL (HLD goal: byte-for-byte).

**Response (404)** when the code doesn't exist (including malformed codes):
```
Content-Type: text/plain

Short code not found.
```

**Response (5xx)** — storage failure:
```
Content-Type: text/plain

Storage temporarily unavailable.
```

### Root and other paths

Requests to `/` and any path not matching `/shorten` or `/:code` return 404. This is a minimal service; no landing page, no favicon, no health endpoint. Operators add those outside the API if needed.

## Short-Code Path Handling

The `:code` path segment is matched as any string of alphanumeric characters. Paths containing characters outside the base62 alphabet (e.g., `/some%20thing`) return 404 without invoking storage.

Codes are case-sensitive. `/1A` and `/1a` are different codes and both are potentially valid — base62 uses both uppercase and lowercase.

## Content Negotiation

The API speaks JSON on `POST /shorten` regardless of `Accept` header. A 302 redirect on `GET /:code` carries no body and therefore no content negotiation. Any `Accept` header on the GET is ignored.

## CORS

Not specified here. Operators deploying this behind a browser-facing frontend configure CORS at the edge (reverse proxy, API gateway) based on their deployment model. The API does not emit CORS headers.

## Idempotency

`POST /shorten` is idempotent by construction — submitting the same URL twice returns the same short code both times (per USH-CORE-006). Callers do not need an idempotency key.

`GET /:code` is trivially idempotent — it's a read.

## Error Mapping

| Shortener-core outcome | HTTP status |
|---|---|
| `shorten` succeeds | 200 |
| `shorten` validation error | 400 |
| `shorten` storage error | 503 |
| `resolve` returns URL | 302 |
| `resolve` returns null | 404 |
| `resolve` storage error | 503 |

Storage errors map to 503 (Service Unavailable) rather than 500 (Internal Server Error) because the API's role is fine — the downstream dependency is the issue.

## Decisions & Alternatives

| Decision | Chosen | Alternatives Considered | Rationale |
|---|---|---|---|
| POST body shape | JSON `{ "url": "..." }` | Form-encoded; URL query parameter | JSON is explicit and extensible (future fields). Form-encoded complicates client libraries. Query parameters would limit URL length for the input. |
| Redirect type | 302 Found | 301 Moved Permanently; 307 Temporary Redirect | 302 is the conventional choice for shorteners. 301 is cached by clients, which interferes with future link management. 307 preserves HTTP method, which isn't needed for browser navigation. |
| 404 body | Plain text | HTML page; JSON | Plain text is smallest, works in all clients. HTML assumes a browser. JSON is overkill for a redirect endpoint. |
| Short-URL host in response | Absolute URL including host | Relative path | Operators may deploy the shortener at any domain; the response needs to carry the full short URL for the caller to share. The host is configured per-deployment. |
| Root path | 404 | Landing page; redirect to a docs URL | Minimum-viable: no product around the service. Operators add a landing page at the edge if desired. |

## Open Questions & Future Decisions

### Resolved

1. ✅ POST JSON, GET redirect.
2. ✅ 302 redirect with exact Location header.
3. ✅ No CORS, no auth, no rate limiting in this spec.

### Deferred

1. **OpenAPI / JSON Schema spec file.** The endpoint shapes above are prose; a machine-readable spec file is an obvious next deliverable if this example ever ships as a real service.
2. **Structured error codes.** Currently the error field is a short string. A richer taxonomy (`invalid_url.scheme`, `invalid_url.empty`, etc.) could help programmatic callers. Not necessary at this scale.

## References

- `docs/high-level-design.md`
- `docs/llds/shortener-core.md` — the API calls into this.
- `docs/specs/api-specs.md`
