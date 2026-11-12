# BenchTime Product Brief

## What BenchTime Is and Who Uses It

BenchTime is the booking and equipment-tracking service for our small shared laboratory. I manage the lab as its owner, and our researchers and staff are the people who book and use the equipment day to day. Rather than booking generic pools of gear, our team reserves individually identified instruments, checks them out when using them at the bench, and returns them for inspection afterward so we can keep unavailable equipment out of circulation.

This brief covers the first version of BenchTime, which you will build as a JSON-only service for our single laboratory using Python 3.12, FastAPI, and SQLite. We do not need a browser interface, user authentication, recurring bookings, notifications, billing, or external calendar integrations. What we need is a reliable service that manages our lab setup, instrument catalog, researcher roster, equipment qualifications, reservations, provisional holds, physical checkouts and returns, post-use inspections, and maintenance closures.

## How the Lab Works

Before day-to-day booking begins, I configure the service with a single setup document that defines our lab's operating environment. That setup establishes our local IANA time zone, our opening hours for each day of the week from Monday through Sunday, our lab-specific holidays, the list of people who work in the lab, our individually identified instruments along with each instrument's required cleaning time in minutes, and the recorded qualifications that authorize a specific person to use a specific instrument between a start and end timestamp.

Once setup is in place, BenchTime enforces the operating rules below across reservations, holds, availability checks, bench usage, maintenance, and timekeeping.

### Scheduling, Qualifications, and Booking Limits

Every booking has to fit within our operating schedule and respect who is trained on each piece of hardware. A reservation must start no earlier than now and fit wholly within one opening interval on a non-holiday date in the lab's time zone. On top of the calendar constraints, creating a reservation or hold requires a recorded qualification for every requested instrument, valid at the time of the booking.

To keep any single researcher or staff member from tying up too much future schedule capacity, each person may have at most three upcoming confirmed reservations. And on the equipment side, reservations on the same instrument cannot overlap, and touching endpoints are permitted when no cleaning buffer applies.

### Reservations, Provisional Holds, Cancellations, and Availability

When someone books an instrument, they can either create a confirmed reservation right away or place a provisional hold first. Either way, a successful reservation creates one stable record retaining its person, instrument, times, note, and initial held or confirmed state. If a booking starts out as a hold, that provisional reservation has a ten-minute lifetime and can become confirmed without changing its reservation ID.

When plans change, canceling an unused held or confirmed reservation releases its reserved capacity so the slot is no longer tied up.

Researchers also need a way to ask the service whether a particular slot can be booked. In BenchTime, availability gives the same yes-or-no decision as an immediate attempt to create a new confirmed reservation with the queried allocation. Instead of only checking whether there is a time conflict on the calendar, the availability endpoint answers whether creating that new confirmed reservation right now would succeed under all of our rules in force.

### Checkout, Return, Inspection, and Instrument Status

Having a confirmed slot on the calendar is only the first half of the workflow; we also track what happens physically at the bench. Checkout requires a confirmed reservation at a clock time in its half-open booked interval and creates at most one outstanding checkout for that reservation.

When the researcher finishes and brings the instrument back, it cannot go straight back into general use without being checked. Return puts the reservation and instrument into awaiting-inspection state, where failed inspections may be retried until the first pass completes the reservation.

Because what is happening physically on the bench is distinct from what is written on the schedule, we track hardware state separately. Instrument status reports physical readiness, checkout, or pending inspection independently of calendar reservations and maintenance.

### Maintenance Closures

As the lab manager, I occasionally need to block off time on an instrument for maintenance. Maintenance prevents new reservations whose protected instrument interval overlaps the closure. At the same time, we do not kick researchers off slots they have already locked in: adding maintenance leaves existing confirmed reservations usable rather than canceling them.

### The Administrative Clock

Finally, BenchTime does not use the server's real-time wall clock to make decisions. Instead, the service maintains a persisted, frozen administrative clock in the database that survives restarts and is controlled through an administrative endpoint. Clock-dependent decisions use the persisted administrative clock immediately, without waiting for real time or a background task.

The interface specification below is the exact contract for building the service.

# Interface specification

## Scope and runtime

BenchTime V1 is a JSON-only service for one laboratory. It covers individually identified instruments, reservations, provisional holds, checkout, return, inspection, and maintenance closures.

Use **Python 3.12, FastAPI, and SQLite**. Start it with:

```bash
python -m benchtime --port 8000 --db ./benchtime.db
```

The database, including the controlled clock, survives process restarts. Successive versions must open the existing database without requiring a reset.

There is no browser interface, authentication, recurrence, notification delivery, billing, or external calendar integration.

## Protocol conventions

- All bodies and responses are JSON.
- Object keys use `snake_case`.
- IDs are case-sensitive strings. Setup IDs match `[A-Za-z0-9_-]{1,64}`. Generated IDs are opaque; the system does not need to produce particular values.
- Input timestamps use `YYYY-MM-DDTHH:MM:SSZ` or `YYYY-MM-DDTHH:MM:SS±HH:MM`. An explicit offset is required; fractional seconds are not supported.
- Output timestamps use UTC, with seconds and a trailing `Z`.
- Time arithmetic uses exact seconds, without rounding.
- Dates use `YYYY-MM-DD`. Local opening times use `HH:MM`.
- Unless stated otherwise, unknown fields, malformed values, duplicate IDs within an ID array, and missing required fields produce `400`.
- Unknown referenced IDs produce `404`.
- Collection responses are JSON arrays, in insertion order, without pagination.
- Strings are stored verbatim unless a constraint below says otherwise.
- There is no general promise that repeated writes are idempotent. The system only needs to support explicitly specified retry behavior.
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

`message` is free text for people to read. `details` is always an object and may be empty. Where several rules prevent an operation, the system does not need to report a particular rule first.

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

The system must accept any setup document that satisfies this schema, including different zones, hours, qualification dates, and cleaning durations.

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
