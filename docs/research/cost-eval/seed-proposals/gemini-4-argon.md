# Project proposals from Gemini 4 Argon (`google/gemini-4-argon`)

- **Date:** 2026-11-12
- **Prompt:** [prompt.md](prompt.md), sent unchanged
- **Route:** OpenRouter, one chat-completions call, no system prompt
- **Reasoning effort:** high
- **Usage:** 692 prompt tokens, 16265 completion tokens (4925 reasoning); about $0.16

The text below is the model's reply, unedited.

---

Here are five candidate project domains designed for studying how AI coding workflows hold up across multi-session software evolution. Each domain avoids standard tutorial tropes, fits within a 1,000–3,000 LOC initial implementation, and features the kind of implicit domain invariants and cross-component assumptions that degrade rapidly when context is lost between sessions.

---

### Candidate 1: **FabQuota** — Shared Fabrication Lab Scheduler & Grant-Billing Engine

#### 1. Product Summary
**FabQuota** is a scheduling, safety-interlock, and billing backend for a shared university nanofabrication facility where researchers reserve specialized tools and charge usage against sponsored research grants. It reconciles advance calendar bookings against physical badge-in/badge-out and tool-state telemetry to calculate subsidized rates, overrun penalties, preventative maintenance locks, and monthly grant invoices.

#### 2. External Interface
An HTTP JSON API with endpoints to:
```http
POST /tools                      # Register tool rates, cooldowns, and maintenance thresholds
POST /grants & POST /users       # Register grants (caps, subsidy tiers) and user certifications
POST /bookings                   # Reserve a tool window against a specific grant
POST /telemetry/events           # Ingest badge-in, badge-out, and fault/maintenance events
GET  /tools/{id}/availability    # Query bookable slots for a date range
POST /billing/close-period       # Reconcile bookings vs. telemetry and emit grant invoices
```

#### 3. Hidden Rules (Held by the Product Owner)
1. **Peak/Off-Peak Split Boundary**: Bookings spanning across 18:00 local lab time are split into peak (08:00–18:00) and off-peak (18:00–08:00) segments for billing, *except* on designated institutional holidays, when all 24 hours bill at the off-peak rate.
2. **Post-Run Cooldown Shadow**: Tools with vacuum or thermal recovery require a post-run cooldown window. This window blocks the calendar for subsequent users, does *not* bill the departing user, and does *not* count against the user's weekly reservation hour quota.
3. **Grace Period vs. Overrun Asymmetry**: Badging in up to 10 minutes early is free. Badging out more than 5 minutes after reservation end bills the entire overrun at 200% of the active segment rate; if the overrun encroaches on another user's reservation, the displaced user’s minimum booking charge is automatically waived.
4. **No-Show Penalty Waiver on Tool Fault**: Unused reservations normally bill a 50% dead-time penalty, *unless* the tool enters an unscheduled fault or maintenance state during the reservation or within 30 minutes prior to its start.
5. **Certification Horizon & Recency**: A user's safety certification for a tool class must be valid through the *end* of the requested booking (not just at booking submission time) and automatically lapses if more than 90 days have elapsed since their last actual badge-in on that tool class.
6. **Grant Cap Ordering**: Grants have a monthly subsidized-rate cap; once exceeded, additional usage bills at the unsubsidized commercial rate. Cap exhaustion is ordered strictly by the timestamp when each usage segment *occurred*, not when the booking was created.
7. **Wear-Hour Maintenance Trigger**: Preventative maintenance locks trigger after $N$ cumulative hours of *actual physical tool runtime* (including staff calibration runs), not reserved hours. Existing future bookings on a newly locked tool are marked `AT_RISK` rather than deleted.

#### 4. Components and Unwritten Contracts
*   **Reservation & Interlock Service**: Validates schedule conflicts, user certifications, weekly quotas, and grant eligibility.
*   **Telemetry Reconciler**: Pairs raw badge events with scheduled bookings, handles missing badge-outs, and produces canonical usage spans.
*   **Grant Rating & Ledger Engine**: Prices usage spans, tracks monthly subsidy caps, and compiles period invoices.
*   **Tool Lifecycle & Maintenance Monitor**: Tracks cumulative runtime hours, fault states, and blackout windows.

**Unwritten Contracts:**
*   The *Reservation Service* includes cooldown windows when checking calendar availability, but strips cooldown windows out of the billable interval payload expected by the *Grant Rating Engine*.
*   The *Telemetry Reconciler* pre-splits any span crossing 08:00, 18:00, or midnight local time and sorts spans chronologically before handing them to the *Ledger Engine*, which assumes spans never cross rate boundaries and arrive in strict temporal order.
*   Staff calibration runs are emitted by the *Telemetry Reconciler* with `billable: false`; the *Maintenance Monitor* must still count them toward physical wear hours while the *Ledger Engine* ignores them.

#### 5. Sequence of 10 Later Changes
1. **`[Local]`** Add an `external_po_number` field to external commercial grants and include it on generated invoice JSON summaries.
2. **`[Depends on an earlier rule]`** Add a `POST /bookings/{id}/extend` endpoint allowing an active user to extend their current session by 30–60 minutes if no conflict exists. *(Must respect the post-run cooldown shadow before the next user's booking and re-verify certification expiry through the new end time).*
3. **`[Cross-cutting]`** Introduce "Buddy-System" hazardous tools: bookings after 18:00 or on holidays require a second certified user ID on the reservation, and the tool only unlocks if both users badge in within 5 minutes of each other.
4. **`[Symptom-only bug report]`** *"Lab managers report that when a user books a 17:00–19:00 slot on a tool with a 30-minute cooldown, and badges out 10 minutes late at 19:10, the next user at 19:30 isn't getting their minimum fee waived even though the tool wasn't ready for them."* *(Root cause: encroaching into the required cooldown delays tool readiness for the next user just like encroaching into their start time).*
5. **`[Refactor/upgrade]`** Extract time-zone and holiday calendar handling into a dedicated `LabClock` module and migrate all persisted timestamps from naive local strings to UTC ISO-8601 while keeping billing rules anchored to lab-local wall-clock time (including DST transitions).
6. **`[Reversal]`** Reverse the grant cap fallback behavior: instead of spilling over into unsubsidized commercial rates when a grant hits its monthly cap, automatically split the excess charge onto the Principal Investigator's designated "department overhead" fallback grant.
   *   *Mid-task owner clarification*: Partway through, the owner clarifies: *"Wait—if the fallback grant itself doesn't have enough remaining balance for the tail end of a single booking span, don't reject the whole span; split that single span across both grants to the exact minute the primary grant ran out."*
7. **`[Depends on an earlier rule]`** Implement an auto-forgive command for snow days (`POST /admin/declare-closure`), which retroactively converts a date into an institutional holiday and voids all no-show fees. *(Must recalculate any 18:00 peak/off-peak splits on that date for users who actually worked through the closure).*
8. **`[Symptom-only bug report]`** *"Researchers are getting blocked from booking tools on Mondays because the system says their 90-day certification lapsed, even though they attended a staff-led recertification session last week."* *(Root cause: recertification was logged as a staff calibration event, which updated tool wear hours but wasn't resetting the user's 90-day badge-in recency timer).*
9. **`[Cross-cutting]`** Add "Shared-Run" batch processing for furnace tools: up to 4 researchers can co-book the same furnace slot on different grants, splitting the base hourly rate equally, except that if one researcher cancels late, the remaining researchers still pay no more than their original fractional share.
   *   *Mid-task owner change of mind*: Partway through, the owner says: *"Actually, don't bill the cancelling researcher's share to the lab—have the cancelling researcher's grant pay their 1/N share as a dead-time fee unless another researcher claims their slot before the run starts."*
10. **`[Local]`** Add a CSV export format option (`?format=csv`) to the period invoice endpoint with line-item breakdowns per booking ID.

#### 6. Why It Differentiates Approaches & Potential Pitfalls
*   **Why it tells approaches apart**: The interaction between *reserved time*, *actual badge time*, and *cooldown shadow time* creates three distinct intervals for every event. Ad-hoc agents reading code in Session 6 or 9 frequently conflate `booking.end_time` with `tool_available_at` or `billable_end_time`, breaking earlier invariants. Spec-driven workflows that explicitly document interval definitions and state transitions preserve these distinctions.
*   **What could make it a poor test**: Interval arithmetic with time zones and DST can cause weaker models to fail on low-level date math rather than architectural or specification drift. Pinning a standard datetime library in the starter scaffold prevents this from dominating the results.

---

### Candidate 2: **ThermAudit** — Cold-Chain Pharmaceutical Excursion & Stability Budget Engine

#### 1. Product Summary
**ThermAudit** is a regulatory compliance service that ingests temperature telemetry from data loggers attached to multi-leg pharmaceutical shipments and determines whether drug lots remain safe to dispense or must be quarantined. It tracks cumulative thermal stability budgets across manufacturing storage, air/ground transit legs, warehouse handoffs, and split-lot distributions.

#### 2. External Interface
A CLI and HTTP JSON API:
```http
POST /products/profiles          # Define thermal thresholds, TOR budgets, and MKT parameters
POST /lots                       # Register master manufacturing lots and initial stability state
POST /shipments                  # Create shipment legs, attach loggers, or split parent lots
POST /telemetry/upload           # Ingest batch time-series readings from a logger manifest
POST /shipments/{id}/handoff     # Record custody transfer between transit and storage facilities
GET  /lots/{id}/verdict          # Compute release/quarantine status and remaining budget
POST /qa/overrides               # Record signed quality-assurance manual dispositions
```

#### 3. Hidden Rules (Held by the Product Owner)
1. **Lifecycle Budget Inheritance (Split Lots)**: A lot's Time-Out-of-Refrigeration (TOR) budget (e.g., max 24 cumulative hours between 8°C and 15°C) belongs to the *lot lifecycle*, not the individual shipment. When a master lot of 1,000 vials is split at a hub into three regional shipments, all three child lots inherit the exact cumulative TOR already consumed by the parent lot up to the split timestamp.
2. **Logger Warmup Exemption**: When a new logger is activated at the start of a leg, readings above the upper threshold during the first 15 minutes are ignored as sensor stabilization—*unless* the lot was already in an active excursion state at the end of the preceding leg.
3. **Handoff Blind-Spot Interpolation**: Unmonitored time gaps between one logger stopping and the next logger starting at a hub are bridged via linear temperature interpolation if the gap is $\le 30$ minutes. If the gap exceeds 30 minutes, the entire gap is evaluated at the receiving facility's registered "ambient worst-case" temperature.
4. **Freeze-Event Lockout of MKT Rescue**: Minor warm excursions can normally be rescued if the Mean Kinetic Temperature (MKT) across the leg stays below 8.0°C. However, any single reading at or below the freeze threshold (2.0°C) permanently disables MKT rescue for that lot's entire remaining lifecycle and triggers an immediate `HARD_QUARANTINE`.
5. **Continuous Spike vs. Cumulative Budget**: In addition to the cumulative 24-hour TOR budget, products have a maximum *continuous* excursion limit (e.g., 4 hours continuously above 8°C). A brief dip back into range (2°C–8°C) only resets the continuous excursion timer if the lot stays within range for at least 30 consecutive minutes.
6. **Calibration Drift Correction**: Each logger manifest includes a post-trip calibration offset (e.g., `-0.4°C`). All threshold and MKT evaluations must apply this offset to raw readings *before* checking boundaries, using half-away-from-zero rounding to one decimal place.

#### 4. Components and Unwritten Contracts
*   **Telemetry Normalizer & Gap Resolver**: Applies calibration offsets, strips sensor warmup windows, aligns timestamps, and synthesizes handoff gap segments.
*   **Lot Genealogy & Custody Graph**: Tracks parent-to-child lot splits, custody timestamps, and historical state snapshots.
*   **Stability Rule Engine**: Evaluates continuous spikes, cumulative TOR depletion, freeze lockouts, and Arrhenius MKT equations.
*   **Disposition & Audit Reporter**: Generates regulatory audit trails and manages QA sign-offs.

**Unwritten Contracts:**
*   The *Telemetry Normalizer* must query the *Lot Genealogy Graph* for the terminating state of Leg $N-1$ before deciding whether to strip the 15-minute warmup window on Leg $N$.
*   The *Stability Rule Engine* assumes the time series it receives from the *Normalizer* has already been converted into uniform 5-minute intervals with calibration offsets applied and handoff gaps materialized as synthetic readings.
*   When a QA officer issues a manual override on a parent lot, the *Lot Genealogy Graph* only propagates that override to child lots if the override timestamp precedes the physical split timestamp.

#### 5. Sequence of 10 Later Changes
1. **`[Local]`** Add a `carrier_scac_code` and `air_waybill` field to air-transit shipment legs and expose them in the `/lots/{id}/verdict` response.
2. **`[Depends on an earlier rule]`** Support "Dual-Logger Redundancy" on high-value shipments where two loggers travel in the same box: evaluate rules using the average of the two calibrated readings at each timestamp, unless one logger reports a hardware fault, in which case fall back to the surviving logger. *(Must apply individual calibration offsets before averaging).*
3. **`[Symptom-only bug report]`** *"Child lot LOT-99B is passing inspection with 3.5 hours of continuous excursion on its final delivery truck, even though the parent lot already was 1 hour into an active excursion right when the pallet was split at the Memphis hub."* *(Root cause: the continuous excursion timer was reset at the lot-split boundary instead of carrying the active excursion duration across the split).*
4. **`[Cross-cutting]`** Introduce "Ultra-Cold Dry Ice" profiles (-80°C to -60°C) where loggers report every 1 minute instead of 5 minutes, and add a sublimation warning state when temperature rises faster than 1.5°C per hour even while still inside the valid range.
5. **`[Reversal]`** Reverse the handoff blind-spot rule: regulators rejected linear interpolation for gaps under 30 minutes. Change all unmonitored handoff gaps $\le 30$ minutes to hold the *higher* of the two boundary temperatures (step-function worst case) instead of interpolating.
   *   *Mid-task owner clarification*: Partway through, the owner clarifies: *"To be precise, 'worst case' means highest temperature for refrigerated (2°C–8°C) products, but if the boundary reading is below 4°C on a freeze-sensitive biologic, hold the *lowest* boundary temperature if it's closer to the 2°C freeze limit than the upper reading is to 8°C."*
6. **`[Refactor/upgrade]`** Refactor the in-memory lot lineage recalculation to cache intermediate stability snapshots at each handoff node so querying deep child lots doesn't re-parse raw CSV telemetry from the beginning of the master lot.
7. **`[Depends on an earlier rule]`** Allow retrospective logger calibration updates (`PATCH /loggers/{id}/calibration`) when a lab discovers a sensor was out of spec after delivery. *(Must invalidate cached snapshots downstream of any leg using that logger and re-evaluate whether MKT rescue or warmup stripping rules change).*
8. **`[Cross-cutting]`** Add support for "Re-Icing Interventions" at customs hubs: a logged re-icing event excuses up to 10 minutes of door-open spike above 8°C (up to 20°C max), provided the temperature returns below 8°C within 20 minutes of the intervention end.
   *   *Mid-task owner change of mind*: Partway through, the owner says: *"Actually, customs officers often forget to log the intervention end time—just make it a flat 15-minute window starting from the single intervention timestamp, and still deduct that time from the cumulative 24-hour TOR budget even though it doesn't count toward the 4-hour continuous spike limit."*
9. **`[Symptom-only bug report]`** *"A lot that dipped to 1.9°C for one reading on Leg 1, then got a signed QA Override clearing that freeze event on Leg 2, is still failing on Leg 3 because the engine refuses to apply MKT rescue to a mild 9°C bump."* *(Root cause: the boolean `freeze_occurred` flag on the lot wasn't cleared or scoped when the QA override excused the specific Leg 1 excursion).*
10. **`[Local]`** Add a summary count of total telemetry data points processed and total gap minutes synthesized to the audit certificate JSON.

#### 6. Why It Differentiates Approaches & Potential Pitfalls
*   **Why it tells approaches apart**: The system relies heavily on pipeline invariants (calibration $\rightarrow$ warmup stripping $\rightarrow$ gap synthesis $\rightarrow$ continuous/cumulative state machines across a DAG of split lots). Introducing caching in Change 6 followed by retroactive calibration updates in Change 7 and QA override scoping in Change 9 punishes agents that don't maintain a clear architectural specification of what state lives at each node.
*   **What could make it a poor test**: The Arrhenius MKT formula involves natural logarithms and activation energy constants ($E_a / R$). To avoid failing agents on physics constants, the exact MKT formula should be given in the initial brief.

---

### Candidate 3: **SplitLedger** — Collaborative Media Recoupment & Royalty Waterfall Engine

#### 1. Product Summary
**SplitLedger** is a royalty accounting CLI and service for independent game and music collectives that ingests multi-currency platform sales statements, deducts recoupable advances across multi-tiered waterfalls, and calculates period payouts for contributors. It handles derivative work splits (such as soundtrack DLCs or remixes), tax withholding holds, minimum payout thresholds, and retroactive platform clawbacks.

#### 2. External Interface
A CLI tool (backed by SQLite/JSON state) with subcommands:
```bash
splitledger register-contributor --id <id> --tax-status <valid|expired|foreign-treaty> ...
splitledger define-project --id <id> --splits <json> --waterfall <json>
splitledger record-advance --contributor <id> --project <id> --amount-cents <int> [--cross-collateral-group <gid>]
splitledger ingest-statement --period <YYYY-MM> --file <sales.json>
splitledger close-period --period <YYYY-MM>
splitledger export-payouts --period <YYYY-MM> --format <json|csv>
```

#### 3. Hidden Rules (Held by the Product Owner)
1. **Recoupment Siloing (No Default Cross-Collateralization)**: An advance paid to Contributor A on Project X can only be recouped from Contributor A's royalty share of Project X. It never reduces A's payable royalties from Project Y unless both advances/projects explicitly share a `cross_collateral_group` ID.
2. **First-Dollar Gross vs. Net Pool Compression**: Platform fees (e.g., 30% storefront cut) and refund reserves are deducted before calculating "Net Receipts." However, if a marquee contributor has a "First-Dollar Gross" split (e.g., 10% of Gross), their payout is calculated on Gross *and deducted from the remaining Net pool* before standard Net contributors split what is left (so total payouts never exceed actual cash received).
3. **Penny-Rounding Dust Allocation**: All split calculations use banker's rounding (round half to even) to integer cents per statement line. Any residual cent discrepancy between the sum of rounded contributor shares and the distributable pool is assigned to the project's designated `primary_owner`, never lost or fabricated.
4. **Tax-Hold vs. Recoupment Distinction**: If a contributor's tax form is expired at period close, their earned royalty share *still recoups their unrecouped advance balance as normal*; only payable cash above the advance is diverted into a `TAX_ESCROW` bucket (and if they are foreign without a treaty, 30% statutory withholding is deducted from payable cash, not from advance recoupment).
5. **Minimum Payout Threshold & Year-End Flush**: Payable cash balances under $50.00 (5,000 cents) roll over in the contributor's `unpaid_payable` ledger to the next month—*except* in the `YYYY-12` (December) period or upon contract termination, when any balance $\ge \$1.00$ is paid out.
6. **Clawback Non-Recourse Floor**: When a platform reports negative net revenue in a period due to refunds/chargebacks, already-paid cash from prior closed periods is never demanded back, and already-recouped advances do not "un-recoup" back into the advance bucket; instead, the contributor accrues a `negative_royalty_carryforward` that offsets future payable royalties across any project.

#### 4. Components and Unwritten Contracts
*   **Statement Ingestor & FX Converter**: Validates raw platform sales, converts foreign currencies using period spot rates, and computes Gross vs. Net receipts.
*   **Waterfall & Split Calculator**: Resolves derivative-work hierarchies, First-Dollar Gross corridors, Net splits, and penny-rounding dust.
*   **Recoupment & Carryforward State Machine**: Tracks advance pools, cross-collateralization groups, and negative refund carryforwards.
*   **Disbursement & Escrow Engine**: Applies tax withholding, $50 minimum rollover rules, and emits payout instructions.

**Unwritten Contracts:**
*   The *Waterfall Calculator* outputs integer cents that strictly sum to `net_receipts_cents` (even when negative). The *Recoupment State Machine* assumes it never receives fractional cents.
*   The *Recoupment State Machine* must run *before* the *Disbursement Engine* applies tax holds or withholding percentages, because advance recoupment is a return of pre-paid capital rather than newly disbursable cash.
*   Derivative projects (e.g., a Game + Soundtrack Bundle where 15% of bundle revenue routes to the Soundtrack project before splitting among musicians) are expanded into synthetic project revenue lines by the *Waterfall Calculator* before the *Recoupment State Machine* runs.

#### 5. Sequence of 10 Later Changes
1. **`[Local]`** Add a `payment_method` (`ACH`, `WIRE`, `CHECK`) attribute to contributors and include a per-method fee ($0 for ACH, $25 for WIRE, $5 for CHECK) deducted from the final disbursement check.
2. **`[Depends on an earlier rule]`** Implement a `splitledger update-tax-status` command that, when a contributor updates their tax form from `expired` to `valid`, releases their `TAX_ESCROW` funds into their active `unpaid_payable` balance for the next period close. *(Must still respect the $50 minimum threshold—or $1 December flush—and wire/check fees).*
3. **`[Cross-cutting]`** Add "Tiered Escalator Splits": once a project's cumulative lifetime Net Receipts cross a milestone (e.g., $100,000), the lead developer's split shifts from 20% to 35% and the publisher's split drops from 80% to 65%. If a single monthly statement crosses the $100,000 threshold mid-statement, the revenue must be pro-rated across the pre-threshold and post-threshold split tables to the exact cent.
4. **`[Symptom-only bug report]`** *"In December (`2025-12`), Contributor C-402 had $38.00 in unpaid rollover, earned $0 in December, had an expired W-9, and the system generated a $38.00 payout check for them anyway."* *(Root cause: the December $1.00 flush bypassed the tax-escrow gate when period earnings were zero).*
5. **`[Reversal]`** Reverse the First-Dollar Gross pool compression rule: the collective's lawyers ruled that First-Dollar Gross royalties must come out of the *Publisher's share* exclusively, rather than compressing the Net pool shared by minor contributors.
   *   *Mid-task owner clarification*: Partway through, the owner clarifies: *"Wait—if the Publisher's share on that project isn't large enough to cover the First-Dollar Gross payout in a given month (for instance, after an escalator shift), the overflow *does* spill back into compressing the remaining Net contributors pro-rata rather than driving the Publisher's period line negative."*
6. **`[Refactor/upgrade]`** Migrate the ledger storage from an append-only flat JSON state file to a normalized relational schema (or structured event-sourced log) supporting `splitledger audit-trail --contributor <id>` to inspect every balance mutation.
7. **`[Depends on an earlier rule]`** Add a `splitledger recoupable-expense` command for shared project expenses (e.g., $2,000 mastering or localization cost) that recoups "off the top" from Net Receipts before *any* contributor splits—except First-Dollar Gross contributors. *(Must interact properly with milestone escalator thresholds: does off-the-top expense reduce the cumulative Net Receipts counter for escalators? Owner says when asked: No, escalators trigger on Net Receipts before recoupable expenses).*
8. **`[Symptom-only bug report]`** *"When a 3-way equal split (33.33% / 33.33% / 33.33%) processes a -100 cent refund on a project, the primary owner is getting assigned -34 cents while the other two get -33 cents, which matches the dust rule—except on bundle sub-projects where the total refund across all contributors adds up to -99 cents instead of -100 cents."* *(Root cause: two-stage rounding—once at the bundle-to-subproject allocation and again at the subproject-to-contributor split—dropped a cent without routing the intermediate dust).*
9. **`[Cross-cutting]`** Support secondary "Royalty Share Transfers" where Contributor A sells 50% of their future royalty stream on Project X to Investor B effective starting period `YYYY-MM`.
   *   *Mid-task owner change of mind*: Partway through, the owner says: *"Hold on—if Contributor A still has an unrecouped advance on Project X when they transfer 50% of their stream to Investor B, Investor B shouldn't get paid cash while A is still unrecouped. Route 100% of A's original share toward recouping A's advance first, and only split the cash 50/50 with Investor B once A's advance on Project X hits zero."*
10. **`[Local]`** Add a `--dry-run` flag to `close-period` that prints the full period payout and recoupment summary table to stdout without mutating ledger state.

#### 6. Why It Differentiates Approaches & Potential Pitfalls
*   **Why it tells approaches apart**: Financial waterfall ordering (Gross $\rightarrow$ Platform Fee $\rightarrow$ Bundle Split $\rightarrow$ Off-the-top Expense $\rightarrow$ Escalator Pro-ration $\rightarrow$ Net Split $\rightarrow$ Dust Allocation $\rightarrow$ Advance Recoupment $\rightarrow$ Tax Escrow $\rightarrow$ Threshold Flush $\rightarrow$ Wire Fee) is almost impossible to reconstruct accurately from code alone once 5–6 patches have been layered onto it. Spec-driven workflows that maintain a canonical waterfall specification table dramatically outperform ad-hoc code modification.
*   **What could make it a poor test**: Floating-point representation errors can create noisy failures if an agent uses `float` instead of integer cents or fixed-point decimals. Mentioning "amounts in integer cents and basis points" in the initial brief keeps the evaluation focused on business logic rather than IEEE-754 quirks.

---

### Candidate 4: **ProtoWindow** — Clinical Study Protocol Visit & Kit Dispensing Tracker

#### 1. Product Summary
**ProtoWindow** is a clinical trial operations backend that schedules patient clinic visits, evaluates protocol window compliance, and assigns serialized investigational drug kits at study sites. It enforces minimum dosing washout intervals, adverse-event dose titrations, double-blind treatment arm protections, and site inventory expiration horizons.

#### 2. External Interface
An HTTP JSON API:
```http
POST /protocols                  # Define visit schedule, windows, titration steps, and washouts
POST /sites & POST /inventory    # Register clinic sites (time zones) and serialized drug kits
POST /patients/enroll            # Randomize a patient to a blinded treatment arm (Day 0)
POST /visits/complete            # Record an actual patient visit, vitals, and dispense a kit
POST /adverse-events             # Log graded adverse events (triggers dose reductions or holds)
GET  /patients/{id}/schedule     # Project target dates and valid windows for upcoming visits
GET  /compliance/deviations      # List protocol deviations across sites and patients
```

#### 3. Hidden Rules (Held by the Product Owner)
1. **Day-0 Baseline Anchoring (No Drift)**: Scheduled target dates for all Visits $V_1 \dots V_n$ are anchored strictly to the patient's Day 0 randomization date (e.g., $V_2 = \text{Day } 28 \pm 3\text{ days}$, $V_3 = \text{Day } 56 \pm 3\text{ days}$). If $V_2$ actually occurs late on Day 31, $V_3$'s target remains Day 56—it does *not* shift to Day 59.
2. **Dosing Washout Floor vs. Window Deviation**: Despite Day-0 anchoring, protocols enforce a minimum safety washout interval between doses (e.g., at least 24 days between kits). If a patient had $V_1$ late on Day 17 (out of window) and returns for $V_2$ on Day 38 (which is inside $V_2$'s nominal Day $42 \pm 4$ window), dispensing is blocked until Day 41 ($17 + 24$). If they wait until Day 47 (outside the nominal Day $42+4$ window) solely because of a mandatory washout, the visit is logged as an `EXCUSED_SAFETY_DELAY`, not a `WINDOW_DEVIATION`.
3. **Kit Expiry Horizon**: When dispensing a serialized drug kit at Visit $V_k$, the kit's expiration date must be strictly after the *latest allowed window date* of the patient's next scheduled visit $V_{k+1}$ (plus a 2-day grace buffer), not merely unexpired on the day of $V_k$.
4. **Blinded Arm Confidentiality**: The system knows internally whether a patient is on `PLACEBO`, `ACTIVE_50MG`, or `ACTIVE_100MG` and which serialized kit numbers correspond to each, but *no* patient, visit, or deviation API response may ever expose the treatment arm or kit formulation—only the blinded `kit_serial_number`.
5. **One-Way Titration Ratchet**: If a Grade 2 Adverse Event reduces a patient's dose step from Level 2 (`100MG`) to Level 1 (`50MG`), the reduction is permanent for the remainder of the study; resolving the adverse event later never auto-escalates the patient back to Level 2 (and for `PLACEBO` patients, the system silently tracks the "sham" step-down and dispenses matching placebo kits so site staff cannot infer the patient is on placebo).
6. **Clinic Local Calendar Day Counting**: "Study Day $N$" is always evaluated as calendar days in the *enrolling clinic site's local time zone*, where Day 0 is the local calendar date of randomization, regardless of the hour of day the enrollment or visit UTC timestamp occurred.

#### 4. Components and Unwritten Contracts
*   **Visit Calendar & Window Calculator**: Projects target dates, nominal windows, washout floors, and deviation classifications.
*   **Randomization & Blinded Titration Engine**: Tracks secret treatment arms, current dose levels (real and sham), and adverse-event holds.
*   **Site Inventory & Dispensing Allocator**: Selects FEFO (First-Expired, First-Out) kits matching site, arm, dose level, and expiry horizon.
*   **Compliance & Deviation Auditor**: Records out-of-window visits, missed visits, and unblinding events.

**Unwritten Contracts:**
*   The *Dispensing Allocator* queries the *Visit Calendar Calculator* for the upper bound of $V_{k+1}$'s window before filtering candidate kits by expiration date.
*   The *Blinded Titration Engine* must run identical state transitions for `PLACEBO` patients as for `ACTIVE` patients during adverse events so that error messages (such as `NO_MATCHING_LOWER_DOSE_KIT_AT_SITE`) and audit logs never leak whether the patient was on active drug.
*   All public DTO serializers strip `arm_code` and `dose_mg` fields before returning responses; internal services pass internal domain objects that include them.

#### 5. Sequence of 10 Later Changes
1. **`[Local]`** Add a `storage_rack_location` string to inventory kits and return it in the dispensing confirmation payload so the pharmacist knows which shelf to pull from.
2. **`[Depends on an earlier rule]`** Add a `POST /visits/{id}/replace-kit` endpoint when a patient drops or loses their medication bottle mid-cycle between $V_k$ and $V_{k+1}$. *(Must allocate a kit matching the patient's current blinded arm/dose, verify its expiry still clears $V_{k+1}$'s upper window, and NOT reset the washout timer or advance the visit counter).*
3. **`[Cross-cutting]`** Introduce "Dosing Holds": a Grade 3 Adverse Event places the patient on a temporary hold (`POST /adverse-events/{id}/hold` and `/resume`). Unlike ordinary late visits, an approved dosing hold *does* shift the anchor dates of all subsequent uncompleted visits forward by the exact number of calendar days the hold lasted.
4. **`[Symptom-only bug report]`** *"Site pharmacists in Tokyo (`Asia/Tokyo`) noticed that when a patient is enrolled at 09:00 AM local time on May 1st (which is April 30th 24:00 UTC) and returns for their Day 14 visit on May 15th, the system flags them as 1 day late on the deviation report."* *(Root cause: one module converted the enrollment timestamp to site-local date for schedule projection, while the deviation auditor subtracted raw UTC dates).*
5. **`[Reversal]`** Reverse the one-way titration ratchet for a new class of "Reversible Biologic" protocols: if a protocol has `allow_re_escalation: true`, resolving a Grade 2 Adverse Event restores the patient up one dose level on their *next* scheduled visit—provided they have completed at least one full visit cycle at the reduced dose first.
   *   *Mid-task owner change of mind*: Partway through, the owner says: *"Wait—the safety board just stipulated that a patient can only re-escalate *once* in their entire trial participation. If they have a second Grade 2 event after re-escalating, lock them at the lower dose permanently even if `allow_re_escalation` is true."*
6. **`[Refactor/upgrade]`** Split the monolithic patient state calculator into an event-replay projection over a chronological log of `Enrollment`, `Visit`, `AdverseEvent`, and `KitReplacement` domain events.
7. **`[Depends on an earlier rule]`** Implement an emergency unblinding endpoint (`POST /patients/{id}/emergency-unblind`) for medical emergencies: it reveals the patient's true treatment arm and dose history to the caller, permanently marks the patient `DISCONTINUED_UNBLINDED` (blocking future kit dispensings), and logs an audit record. *(Normal endpoints for other patients must remain strictly blinded).*
8. **`[Symptom-only bug report]`** *"When a patient on a 7-day Dosing Hold needs a replacement for a lost kit right after resuming, the system rejects every kit in the pharmacy as 'expiring too soon', even though the kits don't expire until 4 days after the original Visit $V_{k+1}$ upper window."* *(Root cause: the 7-day Dosing Hold shifted $V_{k+1}$'s upper window forward by 7 days, so kits that cleared the original window no longer clear the shifted window—Wait! Or is the bug that the replacement endpoint forgot to include the hold shift, or that the test expects the shifted window? Actually, frame the symptom so the bug is unmistakable: "A kit expiring 1 day after the original $V_{k+1}$ window was dispensed *after* a 7-day dosing hold shifted $V_{k+1}$ past the kit's expiry date.")*
9. **`[Cross-cutting]`** Allow patients to transfer between clinic sites (`POST /patients/{id}/transfer-site`) mid-study, including across time zones (e.g., `America/New_York` to `America/Los_Angeles`).
   *   *Mid-task owner clarification*: Partway through, the owner clarifies: *"When a patient transfers sites, don't retroactively recompute past visit study-days in the new time zone—freeze completed visits as they were evaluated at their original site, and evaluate future visit calendar dates in the new site's local time zone anchored to the original Day 0 local date string."*
10. **`[Local]`** Add a `/sites/{id}/reorder-alerts` endpoint that lists any blinded kit pool (reported only by an opaque `pool_hash` so it doesn't leak arm inventory counts to site staff) with fewer than 5 unexpired kits remaining.

#### 6. Why It Differentiates Approaches & Potential Pitfalls
*   **Why it tells approaches apart**: This domain has two orthogonal traps: temporal anchor/washout math and a strict security/confidentiality invariant (never leaking treatment arm data, even indirectly through placebo titration errors or inventory low-stock alerts). Agents working without explicit design specs frequently leak arm information when adding new endpoints (like Change 10) or break sham placebo parity during titration changes (Change 5).
*   **What could make it a poor test**: The distinction between "nominal window," "washout floor," and "hold-shifted anchor" can confuse an evaluator LLM if the grader rubric isn't given deterministic date examples. Providing concrete timeline tables in the hidden PO prompt makes grading crisp.

---

### Candidate 5: **GridShare** — Community Solar Virtual Net-Metering & Settlement Engine

#### 1. Product Summary
**GridShare** is a settlement and credit-allocation engine for community solar operators that distributes kilowatt-hour (kWh) generation from shared solar arrays onto subscriber utility bills across Time-of-Use (TOU) rate periods. It enforces regulatory Low-to-Moderate Income (LMI) carve-out quotas, subscriber rollover credit banks, waitlist backfilling on churn, and retroactive utility meter corrections.

#### 2. External Interface
A CLI and HTTP JSON API:
```http
POST /arrays                     # Register solar array capacity, LMI quota %, and anchor caps
POST /subscribers                # Enroll residential, LMI, or commercial anchor subscribers
POST /Waitlist/promote           # Backfill unsubscribed shares from the tier waitlist
POST /meters/generation          # Ingest monthly array kWh generation by TOU bucket
POST /meters/usage               # Ingest subscriber household utility kWh usage by TOU bucket
POST /settlements/{period}/run   # Allocate generation, apply banks, and emit bill credits
POST /meters/corrections         # Apply retroactive estimated-to-actual utility meter adjustments
```

#### 3. Hidden Rules (Held by the Product Owner)
1. **One-Way TOU Waterfall (`PEAK` $\rightarrow$ `SHOULDER` $\rightarrow$ `OFF_PEAK`)**: Solar credits generated during `PEAK` hours first offset a subscriber's `PEAK` household usage; any surplus `PEAK` credits can cascade downward to offset `SHOULDER` and then `OFF_PEAK` usage in the same month (valued at the source `PEAK` credit rate). However, `OFF_PEAK` generation credits can *never* offset `SHOULDER` or `PEAK` usage—unused lower-tier credits go straight into the subscriber's rollover bank for that specific TOU bucket.
2. **FIFO Rollover Bank Expiration**: Unused credits banked by a subscriber retain their original generation month and TOU bucket. When drawn down in future months, oldest credits within the matching TOU bucket are consumed first (FIFO), and any credit still unused 12 billing periods after its generation month expires into the array's `LMI_COMMUNITY_POOL`.
3. **Hard 30% LMI Carve-Out Isolation**: By regulation, at least 30% of an array's monthly generation must go to verified `LMI` subscribers. If active `LMI` subscribers have less than 30% of total subscription shares, the unsubscribed remainder of that 30% carve-out is deposited directly into the `LMI_COMMUNITY_POOL`—commercial `ANCHOR` tenants are prohibited from absorbing unsubscribed LMI capacity.
4. **12-Month Trailing Usage Cap**: A subscriber's initial share allocation in month $M$ cannot exceed 100% of their household's 12-month trailing average monthly kWh usage; if their contractual percentage share of a sunny summer month produces more kWh than that cap, the excess still belongs to the subscriber (it goes into their personal rollover bank rather than being denied), *unless* their personal rollover bank is already above 2x their annual usage, in which case excess spills to the `LMI_COMMUNITY_POOL`.
5. **Churn Forfeiture vs. Territory Move**: When a subscriber cancels mid-cycle, their banked rollover credits are forfeited to the `LMI_COMMUNITY_POOL`, *unless* the cancellation reason is `TERRITORY_RELOCATION`, in which case their banked credits transfer intact to their new utility account number.
6. **Retroactive True-Up Isolation**: When the utility issues a retroactive meter correction for Subscriber S in historical period $M-3$ (e.g., replacing an estimated usage read with a lower actual read), the engine must replay Subscriber S's credit consumption and FIFO bank balances across $M-3, M-2, M-1$ to compute a net dollar adjustment on the next statement, *without* altering the historical generation allocations or statements of any other subscriber on the array.

#### 4. Components and Unwritten Contracts
*   **Subscription & Quota Allocator**: Manages array share percentages, LMI 30% carve-outs, anchor tenant overflow, and waitlist promotion.
*   **TOU Credit & FIFO Bank Engine**: Runs the intra-month TOU cascade (`PEAK` $\rightarrow$ `SHOULDER` $\rightarrow$ `OFF_PEAK`) and manages per-subscriber 12-month FIFO credit lots.
*   **LMI Community Pool & Spillover Ledger**: Accumulates unsubscribed LMI shares, expired FIFO credits, and churn forfeitures, and distributes bonus credits to active LMI accounts with uncovered bill balances.
*   **Retroactive True-Up Replayer**: Re-simulates single-subscriber state chains from historical periods and computes financial delta adjustments.

**Unwritten Contracts:**
*   The *Subscription Allocator* freezes each subscriber's gross allocated kWh per TOU bucket for period $M$ as an immutable ledger entry before the *TOU Credit Engine* runs household usage netting; the *Retroactive True-Up Replayer* relies on this boundary so it can replay a single subscriber's usage netting without re-running array-wide allocation.
*   Within a single billing period, the order of credit consumption against household usage is: (1) expiring 12-month-old FIFO bank credits first, (2) current-month generation credits second, (3) non-expiring FIFO bank credits (oldest first) third, and (4) `LMI_COMMUNITY_POOL` bonus grants (for LMI users) last.
*   All kWh quantities are tracked in integer watt-hours (`Wh`) internally to prevent fractional loss across 500+ subscribers.

#### 5. Sequence of 10 Later Changes
1. **`[Local]`** Add a `utility_climate_zone` code to subscriber records and include a fixed monthly `grid_access_fee_cents` per zone on generated settlement statements.
2. **`[Depends on an earlier rule]`** Implement the automatic distribution of the `LMI_COMMUNITY_POOL` at the end of each settlement run: after all subscribers' normal allocations and personal banks have been applied, distribute any credits sitting in the `LMI_COMMUNITY_POOL` pro-rata to active `LMI` subscribers who still have uncovered household kWh usage in that period. *(Must still obey the TOU bucket rules—`OFF_PEAK` pool credits cannot cover `PEAK` household usage).*
3. **`[Symptom-only bug report]`** *"Subscriber SUB-88 had 200 kWh of 12-month-old PEAK credits about to expire in month 12, generated 300 kWh of new PEAK credits in month 12, and used 250 kWh of PEAK power at home. At the end of month 12, the system expired all 200 kWh of their old credits and left them with only 50 kWh of new credits in their bank instead of 250 kWh."* *(Root cause: current-month generation was consumed before expiring 12-month-old FIFO credits, causing the old credits to expire unnecessarily).*
4. **`[Cross-cutting]`** Support "Dual-Array Portfolios": a commercial anchor subscriber can hold subscription shares across two different solar arrays in the same utility territory, pooling their allocated credits onto a single master utility meter while keeping LMI carve-outs and array generation caps strictly separate per array.
5. **`[Reversal]`** Reverse the One-Way TOU Waterfall rule due to a new state tariff (`NEM-3.0`): `PEAK` credits can no longer cascade directly 1-for-1 in kWh to cover `OFF_PEAK` usage. Instead, cross-bucket coverage must convert using the ratio of their dollar credit rates (e.g., 1 kWh of `PEAK` at $0.30/kWh covers 2 kWh of `OFF_PEAK` usage at $0.15/kWh).
   *   *Mid-task owner clarification*: Partway through, the owner clarifies: *"Keep the subscriber's rollover bank tracked in physical kWh by original TOU bucket—only apply the dollar-value exchange ratio at the moment a `PEAK` credit is actually consumed to offset `SHOULDER` or `OFF_PEAK` usage."*
6. **`[Refactor/upgrade]`** Refactor the FIFO credit bank and settlement history so that every credit lot has a deterministic lineage ID (`lot_id`) tracing where each Wh was generated, banked, transferred, or consumed.
7. **`[Depends on an earlier rule]`** Extend `POST /meters/corrections` so that if a retroactive utility meter correction in period $M-3$ reveals a subscriber *used more power* than estimated—thus consuming FIFO credits in $M-3$ that had previously expired into the `LMI_COMMUNITY_POOL` in period $M-1$—the true-up replayer reclaims only the unspent portion of those credits from the `LMI_COMMUNITY_POOL` and bills the subscriber for any portion already distributed to LMI households.
8. **`[Cross-cutting]`** Add "Snow/Outage Minimum Generation Guarantees": if an array generates less than 50% of its seasonal expected kWh in a month, subscribers receive an operator-funded "Guarantee Credit" on their bill for the shortfall.
   *   *Mid-task owner change of mind*: Partway through, the owner says: *"Actually, don't issue Guarantee Credits as virtual kWh that go into the FIFO bank or interact with utility netting—calculate them purely as a direct dollar discount off the subscriber's owed subscription fee for that month, capped at their monthly subscription fee so we never owe them a negative invoice."*
9. **`[Symptom-only bug report]`** *"When an LMI subscriber moves across town (`TERRITORY_RELOCATION`) on the 15th of the month, their new account receives their banked FIFO credits, but the array's 30% LMI quota check fails for that month because the validator counts their old account as churned and their new account as a partial-month commercial/standard enrollment."* *(Root cause: the relocation transfer workflow didn't carry over the `verified_lmi_status` and continuity effective date to the successor account).*
10. **`[Local]`** Add an endpoint `GET /arrays/{id}/lmi-compliance-report` returning the exact percentage of kWh allocated to LMI subscribers vs. the `LMI_COMMUNITY_POOL` for each of the past 12 periods.

#### 6. Why It Differentiates Approaches & Potential Pitfalls
*   **Why it tells approaches apart**: The combination of FIFO lot consumption ordering (expiring-old $\rightarrow$ current $\rightarrow$ non-expiring-old $\rightarrow$ LMI pool), TOU bucket isolation, and single-subscriber retroactive time-travel (Changes 3, 5, and 7) creates deep invariants between the *Allocation* layer and the *Netting/Bank* layer. If an agent in Session 5 or 7 edits the netting loop without a clear spec of the consumption priority order and the allocation/netting boundary, retroactive corrections corrupt historical state.
*   **What could make it a poor test**: Community solar terminology ("virtual net metering," "LMI carve-out," "anchor tenant") may initially sound unfamiliar, though the underlying mechanics are straightforward bucketed resource allocation and FIFO inventory accounting.

---

### Ranking of the Five Candidates

1. **FabQuota (Shared Fabrication Lab Scheduler & Grant-Billing Engine)** — *Best overall*
2. **SplitLedger (Collaborative Media Recoupment & Royalty Waterfall Engine)**
3. **ProtoWindow (Clinical Study Protocol Visit & Kit Dispensing Tracker)**
4. **ThermAudit (Cold-Chain Pharmaceutical Excursion & Stability Budget Engine)**
5. **GridShare (Community Solar Virtual Net-Metering & Settlement Engine)**

**Why FabQuota is the top choice:** It combines intuitive concepts that require zero specialist background (calendars, badge swipes, cooldowns, and budgets) with three distinct, interacting representations of every event—*reserved time*, *physical tool-busy time*, and *billable time*—making it uniquely effective at exposing whether an agent workflow preserves unwritten cross-component contracts across fresh sessions.
