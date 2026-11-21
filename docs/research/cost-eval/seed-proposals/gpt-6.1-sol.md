# Project proposals from GPT-6.1 Sol (`openai/gpt-6.1-sol`)

- **Date:** 2026-11-12
- **Prompt:** [prompt.md](prompt.md), sent unchanged
- **Route:** OpenRouter, one chat-completions call, no system prompt
- **Reasoning effort:** high
- **Usage:** 640 prompt tokens, 8894 completion tokens (4571 reasoning); about $0.09

The text below is the model's reply, unedited.

---

## Common study envelope

All five can start as a single-process application using SQLite, JSON/CSV, and a controllable clock, without a UI or live third-party services. The size estimates below are for application code, excluding tests and fixtures.

“Hidden rules” should be available from the owner when asked. For analysis, distinguish rules never elicited from rules previously communicated and subsequently lost; explicit reversals should replace the relevant old requirement, not create an impossible obligation to satisfy both. Deliver mid-change interventions at a consistent milestone, such as after the agent’s first implementation attempt.

---

## 1. BenchTime — shared laboratory instrument reservations

### Product summary
A small laboratory uses BenchTime to reserve instruments, check them out, and keep unavailable equipment out of circulation. It must reconcile booking promises with operator qualifications, cleaning buffers, and maintenance closures.

**V1 boundary:** One laboratory, individually identified instruments, fixed opening hours, reservations, checkout/return, and maintenance holds; approximately **1,800–2,700 lines**.

### External interface
```text
POST /reservations             GET /availability
POST /reservations/{id}/cancel
POST /checkouts                POST /checkouts/{id}/return
POST /maintenance              GET /instruments/{id}/status
```
Fixtures define instruments, qualifications, opening hours, and the laboratory’s time zone.

### Hidden rules
1. Reservations are half-open intervals, but an instrument-specific cleaning buffer extends the occupied period after the booking.
2. Opening hours and “next business day” use the laboratory’s time zone and its explicit holiday calendar.
3. An operator’s qualification must remain valid for the entire reserved interval, not just when booking.
4. Returning an instrument does not make it available: a required inspection must first pass.
5. An expired provisional hold stops consuming capacity even if no cleanup job has deleted its database row.
6. Planned closures prevent new bookings but initially honor existing confirmed bookings.
7. Per-person booking limits count confirmed future reservations, not expired holds, cancellations, or completed sessions.

### Components and unwritten contracts
- **Calendar and availability engine:** Supplies occupied intervals, including buffers, rather than merely stored reservation times.
- **Reservation service:** Must use the same availability and qualification checks for creation, rescheduling, and eventual waitlist promotion.
- **Checkout/inspection workflow:** Owns physical availability; a free calendar slot does not override an uninspected return.
- **Persistence and reporting:** State transitions and capacity changes must be atomic; reports must interpret expired holds using the same clock as booking operations.

### Ten later changes
1. **Local:** Add a short display label for each instrument without changing its stable identifier.
2. **Depends on an earlier rule:** Add “copy this reservation to the next business day,” preserving local wall-clock time and respecting holidays.
3. **Refactor/upgrade:** Extract date calculations behind a calendar adapter, preserving existing behavior.
4. **Cross-cutting:** Allow a reservation to require two instruments atomically; neither may remain held if the other is unavailable.
5. **Depends on an earlier rule — mid-change clarification:** Add rescheduling. After the first implementation, the owner clarifies that qualification must cover the *new complete interval*, even when the original booking was valid.
6. **Reversal — mid-change change of mind:** While adding closure notifications, the owner decides safety closures must cancel existing future bookings too, but must not silently terminate an active checkout.
7. **Symptom-only bug report:** “On the clock-change weekend, the instrument appears free in search, but booking the displayed slot fails.”
8. **Cross-cutting:** Add a second laboratory with its own time zone and holidays, while keeping booking limits global per person.
9. **Local:** Add an optional purchasing-reference field that is stored and returned without affecting allocation.
10. **Depends on an earlier rule:** Add waitlist promotion, rechecking qualifications, expired holds, cleaning buffers, and booking limits at promotion time.

### Why it distinguishes approaches—and its risks
This exposes whether early temporal and state-machine rules survive new entry points. A locally correct rescheduling endpoint can still violate qualifications, while a correct calendar calculation can still overlook physical inspection state.

Its main weakness is familiarity: a strong model may recognize standard scheduling patterns. Keep the distinctive inspection, qualification, and closure semantics; avoid making recurrence, optimization, or real calendar integration part of V1.

---

## 2. RoundTable — community microgrant intake and review

### Product summary
A community fund uses RoundTable to collect applications, establish eligibility, and coordinate independent reviews. It produces deterministic rankings and audit records while keeping applicant identity out of designated reviewer views.

**V1 boundary:** One funding round, structured application fields, declared conflicts, two reviews per application, and CSV exports; approximately **1,600–2,500 lines**. No payments, document parsing, or subjective AI assessment.

### External interface
```text
POST /applications             POST /applications/{id}/submit
POST /assignments              POST /reviews
POST /applications/{id}/eligibility
GET /rankings                  GET /exports/{view}
```
A fixture-backed actor header supplies applicant, reviewer, or administrator identity.

### Hidden rules
1. Submission closes at 17:00 in the round’s time zone; saving a draft before the deadline does not count as submitting.
2. Submission creates an immutable snapshot. A permitted resubmission creates a new version rather than overwriting evidence.
3. Reviews attach to an exact application version; scores never silently carry over to a replacement version.
4. A reviewer’s declared organizational conflict disqualifies them even if they have already started a review.
5. Blind views omit identifying structured fields everywhere, including exports and nested metadata; arbitrary free-text anonymization is outside scope.
6. Ineligible or withdrawn applications do not rank, but their reviews and decisions remain in the audit history.
7. Ranking uses exact integer scores, then submission time, then stable application ID as deterministic tie-breakers.

### Components and unwritten contracts
- **Application/version store:** Exposes immutable submitted versions and distinguishes them from editable drafts.
- **Eligibility and assignment service:** Must enforce conflicts both when assigning and when accepting a review.
- **Scoring/ranking engine:** Consumes only eligible, current-version, valid reviews; display order cannot introduce a different tie-breaker.
- **View/export layer:** Applies the same role-based field projection to JSON, CSV, and nested objects.

### Ten later changes
1. **Local:** Rename the public-facing “funding round” label to “funding opportunity.”
2. **Depends on an earlier rule:** Add reviewer reassignment, retaining old reviews for audit while excluding invalid assignments from ranking.
3. **Cross-cutting:** Add downloadable blind-review packets using the same identity restrictions as the API.
4. **Depends on an earlier rule — mid-change clarification:** Add eligibility appeals. Halfway through, the owner clarifies that an appeal can change eligibility but cannot edit the submitted application or reopen its scores.
5. **Refactor/upgrade:** Move score aggregation into a separate module and replace floating-point intermediate calculations with integer arithmetic.
6. **Reversal — mid-change change of mind:** During a bulk-correction feature, the owner reverses the frozen-budget policy: administrators may correct requested amounts after closing, creating a new version whose old reviews remain audit-only until reconfirmed.
7. **Symptom-only bug report:** “A withdrawn application disappeared from the list, but the funding cutoff still seems to include it.”
8. **Local:** Add configurable help text to the round-information response.
9. **Depends on an earlier rule:** Add a second round in another time zone, including applications submitted near each round’s closing boundary.
10. **Cross-cutting:** Separate eligibility administrators from scoring administrators, updating permissions, exports, audit records, and assignment operations.

### Why it distinguishes approaches—and its risks
The difficult part is preserving distinctions among identity, version, eligibility, and ranking—not implementing CRUD. Documentation and tests should help prevent a later “small correction” from silently reusing scores or leaking applicant fields.

It becomes a poor test if graders make subjective judgments about application quality or expect sophisticated anonymization. Use explicit structured fields, declared conflicts, deterministic scoring, and fixture-defined roles.

---

## 3. LoopCrate — reusable packaging returns depot

### Product summary
A packaging cooperative uses LoopCrate to issue reusable crates, accept returns, inspect damage, and track refundable deposits. Physical custody and financial responsibility must stay consistent even when a different person returns a crate or a transaction is retried.

**V1 boundary:** One depot, serialized crates, fixed deposit schedules, returns, inspection, washing, and an account ledger; approximately **1,900–2,900 lines**. No payment processor or accounting-system integration.

### External interface
```text
POST /checkouts                POST /returns
POST /inspections              POST /wash-batches/{id}/complete
GET /crates/{id}               GET /accounts/{id}/ledger
GET /reports/daily
```
Mutation requests carry a caller-supplied event ID for retry handling.

### Hidden rules
1. A crate has exactly one physical state and, while checked out, one responsible account.
2. A returned crate is not issuable until inspection and washing both pass; damaged crates enter quarantine.
3. Deposit amounts are integer minor units and are snapshotted at checkout, not recalculated from today’s price list.
4. Initially, refunds become payable after inspection, not merely when a return is recorded.
5. Refunds belong to the original paying account, regardless of who physically returns the crate.
6. Repeating an event ID with the same payload is a no-op; repeating it with a different payload is an error.
7. Damage deductions cannot exceed that crate’s original deposit.
8. Financial corrections use compensating entries. Closed daily reports are not rewritten, and posting dates use the depot’s time zone.

### Components and unwritten contracts
- **Crate state machine:** Determines custody and issuability; financial status cannot substitute for physical readiness.
- **Deposit ledger:** Stores immutable entries, original payer, and original deposit terms.
- **Transaction coordinator:** Commits state changes, ledger entries, and idempotency records together.
- **Daily reporting:** Uses ledger posting dates, not return occurrence dates or mutable crate state.

### Ten later changes
1. **Local:** Add an optional shelf label to crate records.
2. **Depends on an earlier rule:** Add bulk return intake, including retries after a partially received HTTP response.
3. **Refactor/upgrade:** Extract ledger calculations into a pure module without changing entry identities or rounding behavior.
4. **Cross-cutting:** Add a second depot and inter-depot transfers, distinguishing physical location from the responsible account.
5. **Depends on an earlier rule — mid-change clarification:** Add courier-assisted returns. After implementation begins, the owner clarifies that the courier must never receive the refund; the original payer does.
6. **Reversal — mid-change change of mind:** While adding an express-return lane, the owner changes policy: new express returns receive immediate refunds, with later damage recorded as a separate capped charge. Existing pending returns retain their original policy.
7. **Symptom-only bug report:** “After the server restarted, retrying yesterday’s inspection increased the customer’s credit again.”
8. **Depends on an earlier rule:** Add lost-crate declarations and late recovery, using compensating entries rather than editing closed-day charges.
9. **Local:** Change the printable return-receipt heading and footer text.
10. **Cross-cutting:** Add corporate accounts with multiple authorized operators, preserving the immutable paying account on every checkout and refund.

### Why it distinguishes approaches—and its risks
This tests whether physical and monetary invariants remain connected across retries, migrations, and policy changes. An implementation can look correct through its current balances while having corrupted audit history or made the same crate available twice.

The danger is drifting into full accounting software. Keep one currency, a small explicit fee policy, no taxes, and no external settlement; otherwise specialist knowledge and implementation volume may dominate the comparison.

---

## 4. ReleaseDesk — embargoed archive publication

### Product summary
A small archive uses ReleaseDesk to ingest text records, approve publication, and release public search results and download bundles. Publication depends on embargo dates, content approval, and takedowns, with restricted records remaining invisible to public callers.

**V1 boundary:** Plain-text attachments, structured metadata, simple substring search, one archive time zone, and ZIP bundles; approximately **1,700–2,600 lines**. No PDF extraction, OCR, or production authentication.

### External interface
```text
POST /records                  POST /records/{id}/versions
POST /records/{id}/approve      POST /records/{id}/takedown
GET /search                    POST /bundles
GET /bundles/{id}/download
```
Fixture actors represent staff, public users, and later named researchers.

### Hidden rules
1. A release date begins at 00:00 in the archive’s time zone; an absent date means indefinitely closed.
2. Embargo expiry is necessary but insufficient: the current content version must also be approved.
3. A folder’s default embargo is initially copied at ingest and then frozen; moving a record does not silently change it.
4. Restricted records are absent from public lists, counts, search results, filenames, and bundles—not merely blocked on direct download.
5. Replacing content invalidates approval; editing a non-policy display label does not.
6. A takedown overrides dates and approvals and must affect previously created bundles when they are downloaded.
7. Public outputs must not expose restricted provenance, blocked record IDs, or staff-only reasons.

### Components and unwritten contracts
- **Ingest/version store:** Separates content changes from harmless metadata edits and gives each content version a stable identity.
- **Policy engine:** Answers access questions for a specific actor, version, and time.
- **Search/catalog projection:** Must not implement a weaker approximation of the policy engine.
- **Bundle service and audit trail:** Recheck access at download time; audit detail is not automatically public metadata.

### Ten later changes
1. **Local:** Rename the public metadata label “folder” to “collection,” preserving identifiers.
2. **Depends on an earlier rule:** Add a scheduled daily release manifest, respecting local midnight and current-version approval.
3. **Refactor/upgrade:** Consolidate access decisions behind one policy interface without changing public outputs.
4. **Cross-cutting:** Grant named researchers access to selected embargoed records without making those records public.
5. **Depends on an earlier rule — mid-change clarification:** Add bundle previews. Halfway through, the owner clarifies that public previews must omit blocked items entirely; only staff may see exclusion reasons.
6. **Reversal — mid-change change of mind:** During folder-policy editing, the owner decides existing unpinned records should follow the folder’s current embargo after all, even if a stricter date makes a previously public record private again.
7. **Symptom-only bug report:** “Search no longer shows the withdrawn letter, but last week’s download link still contains it.”
8. **Local:** Rewrite CLI help text and examples without changing command behavior.
9. **Depends on an earlier rule:** Allow content replacement within an existing catalog record, ensuring old approval does not authorize the new bytes.
10. **Cross-cutting:** Require two distinct staff approvals for a sensitive collection, updating approval history, release decisions, search, and bundles.

### Why it distinguishes approaches—and its risks
This creates many opportunities for policy drift: an endpoint, cache, export, or saved artifact can preserve an obsolete interpretation. Structured requirements should help agents identify every affected surface when publication policy changes.

Its weakness is security breadth. Keep authentication simulated and access rules explicit; do not score unspecified penetration resistance, natural-language redaction, or production-grade storage security.

---

## 5. FieldLedger — offline habitat-survey reconciliation

### Product summary
A conservation team uses FieldLedger to import observations collected on disconnected devices and reconcile later corrections. It produces accepted datasets and public summaries without silently duplicating observations, reviving deletions, or exposing precise locations.

**V1 boundary:** CSV/JSON imports, station metadata, explicit revision numbers, a conflict queue, and exports; approximately **1,800–2,800 lines**. No maps, GIS engine, species recognition, or general-purpose synchronization protocol.

### External interface
```text
fieldledger import FILE --batch-id ID
fieldledger inspect OBSERVATION_ID
fieldledger resolve CONFLICT_ID --choice ...
fieldledger export --audience public|internal --format csv|json
fieldledger summarize --from DATE --to DATE
```
Imports contain stable observation IDs, event IDs, and base revisions.

### Hidden rules
1. Observation identity is based on its stable device/observation identifier, never species, coordinates, or observation time.
2. Replaying an event with identical normalized content is idempotent; reusing its ID with different content is a conflict.
3. An edit must name its base revision. A stale edit is quarantined and cannot overwrite the accepted version merely because it arrived later.
4. Deletion creates a tombstone; an ordinary delayed edit cannot restore it. Restoration must explicitly reference the tombstone revision.
5. Reporting dates use the station time zone captured with the observation. Later station configuration changes do not silently rewrite historical dates.
6. Naive local times that are ambiguous during a clock change are rejected unless an offset is supplied.
7. Unconfirmed species observations count toward total observations but not confirmed per-species totals.
8. Public exports round coordinates; internal exports retain precision. Public outputs must not include raw rejected rows as a side channel.

### Components and unwritten contracts
- **Import normalizer:** Produces canonical values for comparison; filenames and CSV row order do not establish identity.
- **Revision/conflict engine:** Owns acceptance, tombstones, and explicit resolution; import code cannot bypass it.
- **Validation/quarantine store:** Preserves rejected evidence without making it part of the accepted dataset.
- **Summary/export projections:** Read accepted revisions only and share date, certainty, and privacy semantics.

### Ten later changes
1. **Local:** Change human-readable species labels in a supplied catalog without changing species codes.
2. **Depends on an earlier rule:** Support reimporting renamed files and overlapping batches without duplicating observations.
3. **Refactor/upgrade:** Replace the CSV parser to support quoted newlines while preserving normalization and event identity.
4. **Cross-cutting:** Add life-stage observations, updating validation, revision handling, summaries, and both export formats.
5. **Depends on an earlier rule — mid-change clarification:** Add an edit command. After its first implementation, the owner clarifies that observation timestamps never resolve conflicts; explicit base revisions do.
6. **Reversal — mid-change change of mind:** While adding conflict-resolution tooling, the owner decides stale edits to disjoint fields should merge automatically. Overlapping edits still require resolution, and tombstones still prevent resurrection.
7. **Symptom-only bug report:** “Observations we deleted last month returned after a ranger uploaded an old tablet.”
8. **Local:** Add a verbose import-progress option that does not change stored data or machine-readable results.
9. **Depends on an earlier rule:** Add surveys spanning midnight, reporting activity by each observation’s captured local date rather than upload date.
10. **Cross-cutting:** Introduce species-specific public-location restrictions, including complete coordinate suppression, across CSV, JSON, summaries, and conflict-related exports.

### Why it distinguishes approaches—and its risks
This stresses the preservation of identity, provenance, and projection contracts across several ingestion paths. Agents that remember only current schemas are likely to mishandle delayed events, tombstones, or newly added fields.

Its main risk is that synchronization complexity overwhelms the intended process comparison. Keep concurrency bounded to explicit base revisions and field-level conflicts; exclude CRDTs, automatic clock reconciliation, real GIS, and arbitrary distributed histories.

---

## Ranking

1. **BenchTime:** Best overall balance of accessibility, hidden temporal rules, cross-component invariants, and bounded implementation cost.
2. **ReleaseDesk:** Particularly strong for detecting policy drift across APIs, search, exports, and saved artifacts.
3. **LoopCrate:** Strong transactional and historical invariants, with unusually clear observable failures.
4. **RoundTable:** Excellent versioning and visibility tests, but requires discipline to avoid subjective grading.
5. **FieldLedger:** Highly discriminating, but synchronization expertise may contribute more variance than the development process itself.

**Top choice: BenchTime.** Its rules are understandable without specialist knowledge, yet later changes repeatedly require the agent to recover decisions that are not evident from the endpoint being edited—precisely the situation where repository-resident plans, tests, notes, and specifications should differ in value.
