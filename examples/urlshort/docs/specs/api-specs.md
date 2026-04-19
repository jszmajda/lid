# api specs

**LLD**: docs/llds/api.md

Status markers: `[x]` implemented · `[ ]` active gap · `[D]` deferred

---

## POST /shorten

- `[ ]` **USH-API-001**: When a client sends `POST /shorten` with a JSON body `{ "url": "<valid URL>" }`, the system SHALL respond with HTTP 200, `Content-Type: application/json`, and a body `{ "code", "short_url", "url" }` where `code` is the short code, `short_url` is the full URL for sharing, and `url` echoes the input byte-for-byte.
- `[ ]` **USH-API-002**: When `POST /shorten` receives a request body that is not valid JSON, or that is JSON without a `url` string field, the system SHALL respond with HTTP 400 and a JSON error body.
- `[ ]` **USH-API-003**: When `POST /shorten` receives a URL that `shortener-core` rejects as invalid (bad scheme, empty, etc.), the system SHALL respond with HTTP 400 and a JSON body `{ "error": "invalid_url", "message": "<human-readable message>" }`.
- `[ ]` **USH-API-004**: When the same URL is submitted via `POST /shorten` multiple times, the system SHALL return the same `code` on every response (idempotency via USH-CORE-006).
- `[ ]` **USH-API-005**: When `POST /shorten` fails due to storage unavailability, the system SHALL respond with HTTP 503 and a JSON body `{ "error": "storage_unavailable", "message": "<details>" }`.

## GET /:code

- `[ ]` **USH-API-006**: When a client sends `GET /:code` where `:code` resolves to a stored mapping, the system SHALL respond with HTTP 302 and a `Location` header containing the stored URL byte-for-byte, with no response body required.
- `[ ]` **USH-API-007**: When `GET /:code` is called with a code that does not exist in storage, the system SHALL respond with HTTP 404 and a plain-text body `Short code not found.` or equivalent.
- `[ ]` **USH-API-008**: When `GET /:code` is called with a code containing characters outside the base62 alphabet, the system SHALL respond with HTTP 404 and SHALL NOT invoke storage.
- `[ ]` **USH-API-009**: The system SHALL treat short codes as case-sensitive — `GET /1A` and `GET /1a` SHALL resolve to different codes (or both 404), never collapse to the same lookup.
- `[ ]` **USH-API-010**: When `GET /:code` fails due to storage unavailability, the system SHALL respond with HTTP 503 and a plain-text message indicating storage is temporarily unavailable.

## Content Type & Routing

- `[ ]` **USH-API-011**: `POST /shorten` SHALL respond with `Content-Type: application/json` regardless of the request's `Accept` header.
- `[ ]` **USH-API-012**: Requests to the root path `/` and to any path not matching `/shorten` (POST) or `/:code` (GET) SHALL respond with HTTP 404.
- `[ ]` **USH-API-013**: The system SHALL NOT serve a landing page, favicon, or health-check endpoint from within this API. Those are operator concerns placed outside this service.

## Non-Behavior (explicitly out of scope)

- `[D]` **USH-API-014**: The system does not include authentication. Any request that would succeed with auth also succeeds without it; this is deliberate and may change in a future version.
- `[D]` **USH-API-015**: The system does not include CORS headers. Browser-origin deployments add CORS at a reverse proxy or gateway.
- `[D]` **USH-API-016**: The system does not include rate limiting. Operators add limits at the edge.
