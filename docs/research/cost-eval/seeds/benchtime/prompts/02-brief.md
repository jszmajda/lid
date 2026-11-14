Please write a product brief: the document the owner of a small shared laboratory hands to a developer who is going to build a service called BenchTime. Use only the material below.

## What you have to work with

**Product context.** A small shared laboratory uses BenchTime to reserve individually identified instruments, check them out, and keep unavailable equipment out of circulation. The owner manages the lab, and the people booking are its researchers and staff.

**The owner's up-front rules.** These are the only rules the owner has decided to state in the brief:

- A successful reservation creates one stable record retaining its person, instrument, times, note, and initial held or confirmed state.
- Reservations on the same instrument cannot overlap, and touching endpoints are permitted when no cleaning buffer applies.
- A reservation must start no earlier than now and fit wholly within one opening interval on a non-holiday date in the lab's time zone.
- Creating a reservation or hold requires a recorded qualification for every requested instrument, valid at the time of the booking.
- A provisional reservation has a ten-minute lifetime and can become confirmed without changing its reservation ID.
- Canceling an unused held or confirmed reservation releases its reserved capacity.
- Checkout requires a confirmed reservation at a clock time in its half-open booked interval and creates at most one outstanding checkout for that reservation.
- Return puts the reservation and instrument into awaiting-inspection state, where failed inspections may be retried until the first pass completes the reservation.
- Maintenance prevents new reservations whose protected instrument interval overlaps the closure.
- Adding maintenance leaves existing confirmed reservations usable rather than canceling them.
- Each person may have at most three upcoming confirmed reservations.
- Availability gives the same yes-or-no decision as an immediate attempt to create a new confirmed reservation with the queried allocation.
- Instrument status reports physical readiness, checkout, or pending inspection independently of calendar reservations and maintenance.
- Clock-dependent decisions use the persisted administrative clock immediately, without waiting for real time or a background task.

**The interface specification** follows at the end. It's a contract the developer has to follow exactly.

## How to write the brief

- Open with what BenchTime is for and who uses it, in a paragraph or two.
- Then explain the owner's up-front rules in plain product language, the way a lab manager would explain them to a developer. Group them naturally.
- Keep each rule's meaning as given. Some rules are worded loosely on purpose, so don't tighten them, resolve them, or add examples or edge cases that go beyond them. Don't add any rule, behaviour, or example of behaviour that isn't in the material.
- Then reproduce the interface specification in full, keeping every endpoint, field, type, status code, and the error format exactly as given. Make only these changes to it:
  - Remove the sentence about how many lines of code the first build should be.
  - Where the specification mentions graders, reword it as a requirement on the system. For example, "Graders may submit other setup documents satisfying this schema" becomes "The system must accept any setup document that satisfies this schema."
- Write for a competent developer. Aim for about 600 to 1,200 words before the interface specification.
- Don't use "shall" or formal requirement phrasing, and don't number the rules with IDs.
- Don't mention testing, grading, a study, or AI, and don't name any development method or tool beyond the stack in the specification.

Reply with the brief in Markdown and nothing else.

## Interface specification

# Interface specification

## Scope and runtime

BenchTime V1 is a JSON-only service for one laboratory. It covers individually identified instruments, reservations, provisional holds, checkout, return, inspection, and maintenance closures.

Use **Python 3.12, FastAPI, and SQLite**. Start it with:

```bash
python -m benchtime --port 8000 --db ./benchtime.db
```

The database, including the controlled clock, survives process restarts. Successive versions must open the existing database without requiring a reset.

The first build should be approximately **1,800–2,700 lines of application code**. There is no browser interface, authentication, recurrence, notification delivery, billing, or external calendar integration. Later changes retain the single-laboratory boundary.

## Protocol conventions

- All bodies and responses are JSON.
- Object keys use `snake_case`.
- IDs are case-sensitive strings. Setup IDs match `[A-Za-z0-9_-]{1,64}`. Generated IDs are opaque; graders must not assume particular values.
- Input timestamps use `YYYY-MM-DDTHH:MM:SSZ` or `YYYY-MM-DDTHH:MM:SS±HH:MM`. An explicit offset is required; fractional seconds are not supported.
- Output timestamps use UTC, with seconds and a trailing `Z`.
- Time arithmetic uses exact seconds, without rounding.
- Dates use `YYYY-MM-DD`. Local opening times use `HH:MM`.
- Unless stated otherwise, unknown fields, malformed values, duplicate IDs within an ID array, and missing required fields produce `400`.
- Unknown referenced IDs produce `404`.
- Collection responses are JSON arrays, in insertion order, without pagination.
- Strings are stored verbatim unless a constraint below says otherwise.
- There is no general promise that repeated writes are idempotent. Only explicitly specified retry behavior is graded.
- Every successful write is visible to the next request. Concurrent requests must not violate the rules in force.
- There is no authentication, including on administrative endpoints.

### Errors

Every non-success response uses this shape, including validation and unknown-route errors:

```json
{
  "error": {
    "code": "conflict",
    "message": "Human-readable explanation",
    "details": {}
  }
}
```

| HTTP status | `code` | Meaning |
|---|---|---|
| 400 | `invalid_request` | Invalid JSON, fields, types, or syntactic constraints |
| 404 | `not_found` | Unknown resource or referenced ID |
| 405 | `method_not_allowed` | Unsupported method |
| 409 | `not_configured` | A business endpoint was used before setup |
| 409 | `conflict` | An in-force business rule prevents the operation |
| 500 | `internal_error` | Unexpected server failure |

`message` is not compared verbatim. `details` is always an object and may be empty. Where several rules prevent an operation, graders do not require a particular rule to be reported first.

## Administrative controls

### Reset

```http
POST /_admin/reset
{}
```

Returns `200`:

```json
{
  "reset": true,
  "now": "2026-01-05T08:00:00Z"
}
```

This clears **all** setup and operational data and sets the frozen clock to the timestamp shown. No business endpoint is usable until setup is supplied again. Reset is available even before setup.

### Clock

```http
PUT /_admin/clock
{"now":"2026-01-05T08:10:00Z"}
```

Returns `200`:

```json
{"now":"2026-01-05T08:10:00Z"}
```

```http
GET /_admin/clock
```

Returns the same shape.

The clock is frozen, not an offset from real time. All business decisions and generated timestamps use it, including provisional-hold expiry. It may advance or remain unchanged; moving it backwards returns `409`. Use reset to begin an earlier scenario.

### Setup

```http
POST /_admin/setup
```

Accepts one complete setup document. Returns `201` with the normalized document. Setup may be performed only once after reset; another setup request returns `409`. Invalid setup is rejected atomically.

```http
GET /_admin/setup
```

Returns `200` with the current normalized setup document.

Setup fields:

| Field | Type and constraints |
|---|---|
| `timezone` | Valid IANA time-zone string |
| `opening_hours` | Object containing keys `"1"` through `"7"` for Monday through Sunday |
| Each day's value | Empty array, or one object with `open` and `close` |
| `open`, `close` | Local times; `open < close`; no overnight interval; `24:00` allowed only as `close` |
| `holidays` | Array of unique local dates |
| `instruments` | Array of instrument setup objects |
| Instrument `id` | Unique setup ID |
| Instrument `name` | String, 1–120 characters |
| Instrument `cleaning_minutes` | Integer, 0–120 |
| `people` | Array of `{id, name}`; unique IDs; names 1–120 characters |
| `qualifications` | Array of qualification objects |
| Qualification fields | `person_id`, `instrument_id`, `valid_from`, `valid_until` |
| Qualification constraints | Known person and instrument; `valid_from < valid_until`; at most one qualification per person/instrument pair |

An absent qualification means that no qualification has been recorded for that pair.

Example:

```json
{
  "timezone": "Europe/London",
  "opening_hours": {
    "1": [{"open":"08:00","close":"18:00"}],
    "2": [{"open":"08:00","close":"18:00"}],
    "3": [{"open":"08:00","close":"18:00"}],
    "4": [{"open":"08:00","close":"18:00"}],
    "5": [{"open":"08:00","close":"18:00"}],
    "6": [],
    "7": []
  },
  "holidays": ["2026-01-06"],
  "instruments": [
    {
      "id": "scope-1",
      "name": "Imaging microscope",
      "cleaning_minutes": 15
    },
    {
      "id": "spin-1",
      "name": "Benchtop centrifuge",
      "cleaning_minutes": 10
    }
  ],
  "people": [
    {"id":"maya","name":"Maya Patel"},
    {"id":"leo","name":"Leo Grant"},
    {"id":"nora","name":"Nora Ellis"}
  ],
  "qualifications": [
    {
      "person_id": "maya",
      "instrument_id": "scope-1",
      "valid_from": "2025-01-01T00:00:00Z",
      "valid_until": "2027-01-01T00:00:00Z"
    },
    {
      "person_id": "maya",
      "instrument_id": "spin-1",
      "valid_from": "2025-01-01T00:00:00Z",
      "valid_until": "2027-01-01T00:00:00Z"
    },
    {
      "person_id": "leo",
      "instrument_id": "scope-1",
      "valid_from": "2025-01-01T00:00:00Z",
      "valid_until": "2026-01-05T17:00:00Z"
    }
  ]
}
```

January 6 is this laboratory's own holiday; it need not be a public holiday.

Graders may submit other setup documents satisfying this schema, including different zones, hours, qualification dates, and cleaning durations.

## Resource shapes

These are V1 shapes. Later fields are specified only in their introducing changes.

### Instrument

```json
{
  "id": "scope-1",
  "name": "Imaging microscope",
  "cleaning_minutes": 15
}
```

### Person

```json
{"id":"maya","name":"Maya Patel"}
```

### Reservation

```json
{
  "id": "opaque-reservation-id",
  "person_id": "maya",
  "instrument_ids": ["scope-1"],
  "start": "2026-01-05T09:00:00Z",
  "end": "2026-01-05T10:00:00Z",
  "status": "confirmed",
  "expires_at": null,
  "created_at": "2026-01-05T08:00:00Z",
  "note": null,
  "checkout_id": null
}
```

Types:

- `id`, `person_id`: string.
- `instrument_ids`: array of strings; **exactly one instrument in V1**.
- `start`, `end`, `created_at`: timestamp.
- `status`: `held`, `confirmed`, `checked_out`, `awaiting_inspection`, `completed`, `canceled`, or `expired`.
- `expires_at`: timestamp or `null`. For a reservation originally created provisionally, this retains its original hold-expiry timestamp after subsequent transitions.
- `note`: string of 0–1,000 characters or `null`.
- `checkout_id`: string or `null`.

### Checkout

```json
{
  "id": "opaque-checkout-id",
  "reservation_id": "opaque-reservation-id",
  "person_id": "maya",
  "instrument_ids": ["scope-1"],
  "checked_out_at": "2026-01-05T09:00:00Z",
  "returned_at": null,
  "inspection_result": null
}
```

`returned_at` is a timestamp or `null`. `inspection_result` is `null`, `pass`, or `fail`; it reflects the latest inspection result.

### Inspection

```json
{
  "id": "opaque-inspection-id",
  "checkout_id": "opaque-checkout-id",
  "result": "pass",
  "note": null,
  "recorded_at": "2026-01-05T10:05:00Z"
}
```

`result` is `pass` or `fail`. `note` has the same type and limit as reservation notes.

### Maintenance closure

```json
{
  "id": "opaque-maintenance-id",
  "instrument_ids": ["scope-1"],
  "start": "2026-01-05T13:00:00Z",
  "end": "2026-01-05T14:00:00Z",
  "note": null,
  "created_at": "2026-01-05T08:00:00Z"
}
```

`instrument_ids` contains exactly one ID in V1. `note` has the same type and limit as reservation notes.

### Instrument status

```json
{
  "instrument_id": "scope-1",
  "state": "ready",
  "checkout_id": null
}
```

`state` is `ready`, `checked_out`, or `awaiting_inspection`. `checkout_id` identifies the physical checkout causing a non-ready state, otherwise it is `null`.

## V1 endpoints

All business endpoints below require setup.

| Method and path | Request | Success |
|---|---|---|
| `GET /instruments` | No body | `200`, array of Instrument |
| `GET /people` | No body | `200`, array of Person |
| `GET /instruments/{id}/status` | No body | `200`, Instrument status |
| `POST /reservations` | Creation body below | `201`, Reservation |
| `GET /reservations` | No body or filters | `200`, array of Reservation |
| `GET /reservations/{id}` | No body | `200`, Reservation |
| `POST /reservations/{id}/confirm` | `{}` | `200`, Reservation |
| `POST /reservations/{id}/cancel` | `{}` | `200`, Reservation |
| `GET /availability` | Query below | `200`, Availability result |
| `POST /checkouts` | `{"reservation_id":"..."}` | `201`, Checkout |
| `GET /checkouts` | No body | `200`, array of Checkout |
| `GET /checkouts/{id}` | No body | `200`, Checkout |
| `POST /checkouts/{id}/return` | `{}` | `200`, Checkout |
| `POST /inspections` | `{"checkout_id":"...","result":"pass","note":null}` | `201`, Inspection |
| `GET /inspections` | Required query `checkout_id` | `200`, array of Inspection |
| `POST /maintenance` | Maintenance creation body below | `201`, Maintenance closure |
| `GET /maintenance` | No body | `200`, array of Maintenance closure |
| `GET /maintenance/{id}` | No body | `200`, Maintenance closure |

Reservation creation:

```json
{
  "person_id": "maya",
  "instrument_ids": ["scope-1"],
  "start": "2026-01-05T09:00:00Z",
  "end": "2026-01-05T10:00:00Z",
  "provisional": false,
  "note": null
}
```

`person_id`, `instrument_ids`, `start`, and `end` are required. `provisional` defaults to `false`; `note` defaults to `null`.

Maintenance creation:

```json
{
  "instrument_ids": ["scope-1"],
  "start": "2026-01-05T13:00:00Z",
  "end": "2026-01-05T14:00:00Z",
  "note": null
}
```

All except `note` are required. Every interval has `end > start`; otherwise return `400`.

Availability query:

```http
GET /availability?person_id=maya&instrument_id=scope-1&start=2026-01-05T09:00:00Z&end=2026-01-05T10:00:00Z
```

All four query fields are required. In V1, `instrument_id` occurs exactly once.

Returns:

```json
{
  "person_id": "maya",
  "instrument_ids": ["scope-1"],
  "start": "2026-01-05T09:00:00Z",
  "end": "2026-01-05T10:00:00Z",
  "available": true
}
```

This is a decision about creating a **new confirmed reservation**, not merely whether a calendar row overlaps. A syntactically valid query that fails a business rule returns `200` with `available:false`, not `409`. Unknown IDs and malformed queries retain their normal error statuses.

