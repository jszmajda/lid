Earlier you wrote the hidden materials for BenchTime: an interface specification, an oracle, and a change script. A reviewer then edited the oracle and the change script. The edited versions are below, and the reviewer's edits listed further down must be kept.

The study has changed one thing: **the agent now designs its own interface.** The brief no longer contains an interface specification. It contains the owner's description of what they need and the items marked "stated at start", plus these fixed operating requirements:

- Python 3.12, FastAPI, and SQLite.
- One command, documented in the README, starts the service.
- All of the service's data lives in one location that the start command uses.
- The service reads the current time from the system clock. The study controls that clock from outside.

How the lab's setup data (time zone, opening hours, holidays, instruments, people, and qualifications) gets into the system is the agent's choice.

Before grading, a separate step reads the agent's code and running service and writes a reference to the interface the agent built. Graders use that reference to exercise the service, while the study controls the clock and resets state.

Please revise the oracle and the change script for this.

## 1. The change script

Each change is now only the owner's words. Remove every "Interface delta" section. For each rule a delta contained:

- if the owner would naturally say it when asking for the change, put it into the owner's request, in their words;
- if it is a rule the owner cares about but wouldn't think to say, make it an oracle item, usually askable;
- if it only describes the shape of the interface (paths, field names, status codes, or response formats), drop it.

Keep the delivery rules, the redirects, the emerging statements, the scheduled symptom reports with their fire conditions, the type tags, and the "Introduces / Retires / Relies on" lines, updated to match. Write fire conditions and diagnostics in terms of operations, not endpoints.

## 2. The oracle's item table

- Restate every item as behaviour the owner cares about, in terms of operations (place a hold, confirm it, check availability, check out, return, inspect, close an instrument for maintenance, and so on), not endpoints, field names, or status codes. Write "refused" instead of "returns 409", and "rejected as invalid" instead of "returns 400".
- Rewrite each grading sketch in terms of operations and clock settings.
- Drop items that only concern the shape of the interface. Reword any item that depended on the fixed setup endpoint or the administrative clock, for example BT-14.
- Add items for rules moved out of interface deltas, with IDs continuing from BT-44, and give each one a disclosure kind.
- Keep the IDs of existing items. Mark a dropped item "Dropped" in the table, with a one-line reason, rather than deleting it.

## 3. The narrative

Keep its structure: one section the owner knows from the start, and one section per change, released as the trajectory reaches that change. Change the wording only where it refers to the interface.

## 4. The probe request

Rewrite it in the owner's words only, and describe how a grader checks it in terms of operations. The grader can compare it against the service's own way of checking whether a booking would succeed.

## 5. Grading fixtures

Describe the example lab (time zone, hours, holiday, instruments, people, and qualifications) as data the grader loads through whatever setup mechanism the agent built, not as a JSON document for a fixed endpoint.

## Reviewer edits to keep

- **BT-04** says a qualification must be "valid at the time of the booking". It must not say the qualification covers the booking's start. BT-16, which is askable, carries the whole-booking rule.
- **BT-39** (why a booking was canceled) is emerging at change 7, raised with the purchasing-reference request. Records canceled before change 7 aren't graded.
- **BT-40** (copying fails rather than hunting for a later date) is stated in change 8's request.
- **BT-43** (one live hold per person) is emerging at change 8.
- **The narrative** is released in sections, and symptom sections are released at their scheduled change.
- **The probe** is the slot finder: every 15-minute start on a local date at which a real confirmed booking would succeed now.
- **Changes 7 and 8** are tagged as carrying emerging items.

## Format and constraints

- Reply with the revised oracle in full under "# Oracle" (narrative, conventions, grading fixtures, item table, and recognized-on-sight responses), then the revised change script in full under "# Change script", including the probe.
- Don't name or allude to any particular development method, tool, or framework for working with coding agents.
- Don't use "shall" or "when ..., the system shall" phrasing.
- The original interface specification is included for reference only. It no longer goes to the agent.

