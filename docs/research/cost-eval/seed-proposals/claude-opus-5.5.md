# Project proposals from Claude Opus 5.5 (`claude-opus-5-5`)

- **Date:** 2026-11-12
- **Prompt:** [prompt.md](prompt.md), sent unchanged
- **Route:** `claude -p` in an empty directory, with no tools and no project context
- **Reasoning effort:** medium
- **Usage:** 15150 output tokens; Claude Code's estimate $1.05

The text below is the model's reply, unedited.

---

# Five candidate project domains for the agent-process study

All five need a clock you can set. Every candidate has time-dependent rules, so each one should accept an `as_of` value (a request header, a CLI flag or an event timestamp) instead of reading the system time. Without that, graders can't produce the same result twice.

---

## 1. Tickclock: SLA timer service for a support desk

**Summary.** Tickclock receives ticket events from a help desk and tracks each ticket's service-level clocks: first response, next reply and resolution. It reports warnings and breaches. It counts business time against support calendars, holidays and pause states, and support leads use it to decide what to work on next.

**Interface (HTTP)**
```
POST /calendars                     {tz, weekly_hours, holidays[]}
POST /accounts                      {name, calendar_id, tier}
POST /tickets                       {account_id, priority, created_at}
POST /tickets/{id}/events           {type: status|public_reply|internal_note|priority|customer_reply, at, ...}
GET  /tickets/{id}/sla?as_of=       -> per-clock {target, elapsed, remaining, state: ok|warning|breached|paused|met}
GET  /breaches?as_of=&account=
```

**Hidden rules**
1. Business time follows the customer account's calendar and time zone. It does not follow the agent's or the server's, and a "day" ends at midnight in the account's time zone.
2. Urgent tickets run on a 24×7 clock no matter which calendar applies.
3. The clock pauses while a ticket is in "waiting on customer". It restarts only when the customer replies. An agent moving the ticket back to "open" does not restart it.
4. Only a public reply from an agent satisfies first response. An internal note or an automatic acknowledgement does not count.
5. A breach is permanent. If the priority is lowered afterwards, the recomputed target still cannot clear an existing breach.
6. If a priority changes, the target is recomputed from the ticket's original creation time using the new priority's target. It is not recomputed from the moment of the change.
7. A ticket reopened within 7 calendar days continues its original resolution clock, with paused time excluded. After 7 days the reopen starts a fresh clock.
8. The warning fires at 75% of the target, measured in business time rather than wall-clock time.

**Components and unwritten contracts**
- **Event ingestion / state machine.** Events may arrive out of order. The evaluator assumes ingestion has already sorted them by `at` and removed duplicates.
- **Business-time calendar engine.** It returns half-open UTC intervals `[start, end)`. Everything downstream assumes it never returns overlapping intervals and that it has already applied holidays.
- **SLA policy evaluator.** It owns the permanent-breach flag. Reporting reads that flag and never recomputes it.
- **Query / reporting layer.** It treats "paused" as a state the evaluator reports, not one it works out from the ticket status.
- **Storage.** Events are append-only, and the evaluator replays them to rebuild state.

**Ten later changes**

| # | Change | Kind |
|---|---|---|
| 1 | Rename the `pending` status to `awaiting_customer` in output, but keep accepting `pending` as input. | Local |
| 2 | Move from naive datetimes plus offset arithmetic to `zoneinfo`-aware types, or upgrade the date library a major version. | Refactor/upgrade |
| 3 | Add a "solved" status that closes the ticket automatically after 3 business days. This must use the account calendar (rule 1) and leave the pause rules alone (rule 3). | Depends on earlier rule |
| 4 | Calendars move from accounts to support teams, and tickets can change team partway through. The owner wants elapsed time frozen at handoff and the remaining time counted on the new team's calendar. | Cross-cutting |
| 5 | "A customer in Auckland says their ticket breached overnight before anyone was at work on Monday." The cause is a day boundary computed in server time or a mishandled DST change. | Symptom-only |
| 6 | Breaches stop being permanent in one case: if a priority was set by mistake and corrected within 10 minutes, the ticket is re-evaluated as though the wrong priority never happened. | Reversal of rule 5 |
| 7 | Add monthly SLA attainment percentages per account. Month boundaries use the account's time zone, and a reopened ticket counts once (rule 7). | Depends on earlier rule |
| 8 | Enterprise tier gets its own targets and a configurable warning threshold, which touches the evaluator, the API and reports. | Cross-cutting |
| 9 | Add a next-reply SLA. The first instruction is "every customer message restarts the next-reply clock." Midway the owner changes their mind: "No, only the first unanswered customer message starts it, and follow-ups don't reset it." | Change of mind mid-change |
| 10 | Add a bulk import of historical tickets. Midway the owner clarifies that imported tickets must not send warnings or breach notifications after the fact, but they must count in reports. | Clarification mid-change |

**Why it tells the approaches apart.** The rules that matter look like parameter choices in the code: which calendar to use, which event counts, whether a flag ever clears. Nothing in the code records why, so a fresh session is likely to change one "harmlessly". Changes 3, 6 and 7 work only if the agent can recover rules stated many sessions earlier. Approaches that keep design notes or specs should do much better there, and approaches with no process should regress quietly. Grading is precise because `GET /sla?as_of=` produces deterministic answers.

**Risks.** It's mostly computation with little surface area, so a strong model may get the calendar arithmetic right whatever the process. The study could then end up measuring date-handling skill instead of how well intent is kept. Some failures, especially DST, depend on the library rather than on the process.

---

## 2. Rostercalc: shift pay for casual event-venue staff

**Summary.** Rostercalc turns clock-in and clock-out records for casual staff at an event venue into pay lines. It applies the owner's own rule set for minimum engagement, overtime, night and holiday premiums. It closes pay periods and issues payslips, and corrections are carried forward as auditable adjustments.

**Interface (CLI)**
```
rostercalc import punches.csv          # worker_id, venue, event, timestamp
rostercalc compute --period 2026-W45   # -> pay lines JSON
rostercalc close --period 2026-W45
rostercalc payslip --worker W123 --period 2026-W45
rostercalc adjust --worker W123 --ref <line> --reason ...
```

**Hidden rules**
1. A shift belongs to the day it started, in the venue's time zone, even if it runs past midnight.
2. Minimum engagement is 3 paid hours, unless the worker chose to leave early (a flag on the punch).
3. Overtime applies after 10 hours in one shift or 38 hours in a pay week. The week starts Monday at 00:00 venue time. A minute never gets overtime twice, so whichever rule pays more applies to it.
4. Night premium (+25%, 00:00–06:00) stacks with the weekend premium but not with overtime. Overtime replaces it.
5. Clock-in times round to the nearest 15 minutes, but only in the worker's favour. Clock-out times are never rounded.
6. Shifts over 5 hours lose an unpaid 30-minute meal break unless the worker punched a break.
7. Public holidays pay 2.5×, but only for the minutes that fall on the holiday.
8. A closed pay period can't be changed. Corrections go into the next open period as adjustments that reference the original line.

**Components and unwritten contracts**
- **Punch normalizer.** It outputs UTC and orders punches. The shift builder trusts that unmatched punches have already been flagged.
- **Shift builder.** It pairs punches, assigns each shift to a day (rule 1) and deducts breaks. The rules engine assumes every shift it receives already has its break removed.
- **Rules engine.** It splits each shift into rate segments by the minute. The ledger assumes these segments never overlap and add up to the paid time.
- **Pay-period ledger.** It enforces that closed periods stay closed. Every other component assumes it can only append.
- **Payslip renderer.** It assumes all money arrives as integer cents, already rounded.

**Ten later changes**

| # | Change | Kind |
|---|---|---|
| 1 | Show only the last 4 digits of a worker's ID on payslips. | Local |
| 2 | Change the column order of the CSV export to match what the accountant's software expects. | Local |
| 3 | Replace float money with integer cents throughout, without changing any past result. | Refactor |
| 4 | Add a split-shift allowance for two shifts on the same day. "Same day" depends on rule 1 when one shift crosses midnight. | Depends on earlier rule |
| 5 | Open a second venue in another time zone, with workers who work at both. Which venue's Monday starts the overtime week? | Cross-cutting |
| 6 | "Ana got paid less the week the clocks went back." A 25-hour night was cut short, or the minute arithmetic used local wall-clock time. | Symptom-only |
| 7 | Stop rounding in the worker's favour and pay exact minutes from now on. Closed periods stay as they were. | Reversal of rule 5 |
| 8 | Apply a rate increase backdated two periods. It must go through adjustments (rule 8) and must not reopen closed periods. | Depends on earlier rule |
| 9 | Add a junior rate (under 18 at 70%). The first instruction is "no overtime for juniors, cap shifts at 8 hours." Midway the owner changes their mind: "Let them work overtime, paid at the adult overtime rate." | Change of mind mid-change |
| 10 | Add an on-call allowance. Midway the owner clarifies that on-call hours that turn into a callout are paid as worked time only, never both. | Clarification mid-change |

**Why it tells the approaches apart.** The rules interact: overtime against night premium, rounding against minimum engagement, break deduction against the 10-hour threshold. A local edit can quietly break a rule set many sessions earlier, and the test fixtures can make that happen on purpose. Rule 8 (closed periods can't change) is a classic invariant that holds across the whole system and that a fresh agent breaks easily when making the backdated change or the cents refactor.

**Risks.** Models may bring in real labour law (FLSA, Australian awards) without being asked. That is a useful signal of assuming instead of asking, but graders have to score strictly against the owner's rules. The rules engine could grow past the line budget. It is also heavy on computation, so it overlaps with Tickclock.

---

## 3. Pantry Ledger: food-bank inventory and distribution

**Summary.** Pantry Ledger tracks donated food by lot and expiry date and records what goes out to registered households, enforcing per-household limits. It also produces donor acknowledgements and the monthly count of people served for the funder.

**Interface (CLI, SQLite file)**
```
pantry receive --item "black beans" --qty 24 --unit kg --best-by 2027-03-01 --donor D7
pantry household add --members "1961,1988,2023" --zip 21201
pantry visit H42 --take "black beans:2,milk:1"
pantry void-visit V1009 --reason ...
pantry report monthly --month 2026-10
pantry donor-receipt D7 --year 2026
```

**Hidden rules**
1. Stock goes out earliest-expiry first. Shelf-stable items can go out up to 6 months past their best-by date. Dairy and infant items can't go out at all past that date.
2. Each visit has a points allowance scaled by household size, and a household gets one visit per week (Monday–Sunday, local time). Households with a member aged 65 or over get two.
3. Members count toward household size only if they have a birth year on record.
4. Donor receipts never show a dollar value for food, only quantity and weight. Cash donations are listed separately.
5. The funder report counts unduplicated individuals per month. Someone listed in two households counts once, matched on name and birth date.
6. Distributions are never deleted. A void creates reversing entries that send stock back to its original lots.
7. Weight is stored in grams. Reports show pounds, rounded only at the final step.
8. Personal information never appears in any export. Zip code and age band are the most an export may show.

**Components and unwritten contracts**
- **Lots/inventory.** It returns lots in earliest-expiry order, and the visit engine takes the first eligible lot without checking again.
- **Household registry.** It owns the duplicate-matching key. The report trusts that key and does not do its own matching.
- **Visit engine.** It writes ledger entries and checks limits by reading the ledger, not a counter.
- **Reporting/receipts.** They sum ledger entries and assume reversals are already in the ledger.
- **Unit conversion.** It always stores canonical grams, and every other component assumes that.

**Ten later changes**

| # | Change | Kind |
|---|---|---|
| 1 | Add a dietary-needs field (halal, vegetarian, allergies) to households. | Local |
| 2 | Rename "points" to "credits" everywhere in output. | Local |
| 3 | Add an infant formula category. It can never go out past best-by (rule 1) and only to households with a child under 1 (rule 3). | Depends on earlier rule |
| 4 | Open a second distribution site with its own inventory. A household's visit limit is shared across both sites. | Cross-cutting |
| 5 | "The October report says we served 40 more people than September, but our sign-in sheets are flat." Duplicates across sites, or voids, are being counted twice. | Symptom-only |
| 6 | Change weekly visits to twice a month (days 1–15 and 16 to month end). The senior exception stays. | Reversal of rule 2 |
| 7 | Replace raw `sqlite3` calls with a migration-managed schema or ORM. | Refactor/upgrade |
| 8 | Add an emergency box that bypasses the limits. The first instruction is that it doesn't count. Midway the owner changes their mind: "It counts toward next period's limit after all." | Change of mind mid-change |
| 9 | Add a funder CSV export. Midway the owner clarifies "zip only, never street address, and age bands instead of birth years" (rule 8). | Clarification mid-change |
| 10 | Let a void happen after a later visit by the same household, which affects the limit for the following period (rule 6). | Depends on earlier rule |

**Why it tells the approaches apart.** It has several quiet rules that apply everywhere: the ledger is append-only, personal information never leaks, the duplicate key belongs to the registry, and weights are canonical grams. A fresh session adding an export or the second site can break each of them without any test failing. The domain is realistic and not common in tutorials.

**Risks.** The surface is broad: inventory, people, reports and receipts. The first build could exceed 3,000 lines, and grading reports by model is laborious. Earliest-expiry-first is well known. The rule against showing a value for food donations depends on knowledge of tax practice and must be stated as the owner's rule.

---

## 4. Shedshare: community tool-lending library

**Summary.** Shedshare runs a neighbourhood tool library: membership tiers, loans, holds, renewals and late fees for tools and kits. The library is open only a few days a week, and that schedule drives most of the rules.

**Interface (HTTP)**
```
POST /members  {tier, waivers[]}         POST /items {kind: tool|kit|consumable, category, replacement_value}
POST /loans    {member_id, item_id, at}  POST /loans/{id}/return {at, missing_components[]}
POST /loans/{id}/renew                    POST /holds {member_id, item_id}
GET  /members/{id}/balance?as_of=         GET /items/{id}/availability?as_of=
```

**Hidden rules**
1. Loan periods count only days the library is open (Tue, Thu and Sat), and a due date always falls on an open day.
2. Late fees accrue per open day, only on "chargeable" (power) tools, and never exceed the tool's replacement value.
3. A member with a balance over $10 can't borrow, but can still return items and place holds.
4. Holds are first come, first served, except that volunteers move ahead of non-volunteers. Volunteers stay in order among themselves. A hold expires 2 open days after the member is notified.
5. A kit lends as one unit. If any component is missing, the whole kit becomes unavailable.
6. Each tier has a maximum number of concurrent loans. A kit counts as one loan, and consumables don't count.
7. A loan can't be renewed while someone has a hold on the item. A renewal extends from the original due date, not from today.
8. Borrowing from a dangerous category such as chainsaws requires a safety waiver signed within the last 12 months.

**Components and unwritten contracts**
- **Calendar.** It does open-day arithmetic. Circulation and fees both assume it is the only place that knows about closures.
- **Catalog.** It stores kits and components. Availability is derived from circulation and never stored.
- **Circulation.** It handles loans, holds and renewals, and asks the fee ledger whether a member is blocked.
- **Fee ledger.** It computes fees when read or accrues them daily (an implicit choice that later changes depend on).
- **Member registry.** It stores tiers and waiver dates.

**Ten later changes**

| # | Change | Kind |
|---|---|---|
| 1 | Add `manufacturer` and `model` fields to items. | Local |
| 2 | Make the $10 block threshold configurable and set it to $15. | Local |
| 3 | Add one-off holiday closures. These must change both due dates and fee days (rules 1 and 2). | Depends on earlier rule |
| 4 | Open a second branch. Items can be returned at either branch, and holds have a pickup location. | Cross-cutting |
| 5 | "A member was charged a late fee for the Saturday we closed for the street fair." Closures were applied to due dates but not to fee accrual. | Symptom-only |
| 6 | Go fine-free. Late fees are abolished, and members are blocked after 14 days overdue. Existing late fees are forgiven, but damage charges remain. | Reversal of rule 2 |
| 7 | Upgrade the web framework or validation library a major version (for example, Pydantic v1 to v2). | Refactor/upgrade |
| 8 | Add date-range reservations. Midway the owner changes their mind: "Only for kits, not single tools." | Change of mind mid-change |
| 9 | Enforce waiver expiry. Midway the owner clarifies that 12 months means the same calendar date a year later, and a waiver that expires during a loan does not recall the tool. | Clarification mid-change |
| 10 | Let members renew through the API themselves. This brings in rule 7 and raises the question of whether blocked members may renew (rule 3). | Depends on earlier rule |

**Why it tells the approaches apart.** The open-day calendar and the block-versus-hold distinction are easy to lose. The fine-free reversal tests whether old rules get removed cleanly or left half in place.

**Risks.** Library management is a classic textbook exercise, so a lot of the structure may be memorized and the domain moves toward tutorial territory. The rules are friendlier and more guessable than in Tickclock or Rostercalc.

---

## 5. Fixturely: recreational league scheduler and standings

**Summary.** Fixturely generates a season's fixtures for an amateur league from team lists and field availability. It records results and computes standings using the league's own tiebreakers and forfeit rules.

**Interface (CLI)**
```
league init --season 2027-spring
league teams add "Otters" ; league fields add "Park 2" --slots "Sun 09:00,Sun 10:30"
league schedule generate --seed 7
league result record F12 3-1     ; league forfeit F13 --team Otters
league withdraw Badgers          ; league standings [--as-of-round N]
```

**Hidden rules**
1. A win is worth 3 points and a draw 1. A forfeit is recorded as 0–3 and gives the forfeiting team 0 points. A team that forfeits twice is removed (see rule 6).
2. Tiebreakers in order: points, then head-to-head as a mini-league among all the tied teams, then goal difference, goals scored, fewest forfeits, and finally a seeded coin flip.
3. Goal difference is capped at ±5 per game, as a mercy rule.
4. No team plays twice in a day, and no team gets the late slot more than 2 weeks in a row.
5. A rescheduled game keeps its original round number for "standings as of round N".
6. A team that withdraws having played fewer than half its games has all its results deleted. Otherwise its remaining games become forfeits.
7. Slot times are local wall-clock times. "Sunday 09:00" stays 09:00 local across DST changes.

**Components and unwritten contracts**
- **Fixture generator.** It pads odd team counts with a bye. Standings assume byes never appear as results.
- **Results ledger.** Results must reference fixtures that are actually scheduled, and a forfeit is a flag on a result rather than a separate record.
- **Standings calculator.** It reads each team's withdrawal status from the registry and applies rule 6 when it reads results.
- **Season/team registry.** It holds seed, season and status. Stored fixtures are never regenerated.

**Ten later changes**

| # | Change | Kind |
|---|---|---|
| 1 | Add team colours and a captain contact. | Local |
| 2 | Add `--as-of-round N`, which brings in rule 5. | Depends on earlier rule |
| 3 | Add divisions that share fields. Cross-division friendlies don't count toward standings. | Cross-cutting |
| 4 | "The Otters are above the Badgers but lost to them twice!" Head-to-head was done pairwise instead of as a mini-league in a 3-way tie. | Symptom-only |
| 5 | Remove the goal-difference cap from next season, keeping it for the current one, so rules become versioned by season. | Reversal of rule 3 |
| 6 | Replace the greedy scheduler with backtracking. Existing seasons' stored fixtures must not change. | Refactor |
| 7 | Add a playoff bracket for the top 4. Midway the owner changes their mind: "Top 6, with byes for the top 2." | Change of mind mid-change |
| 8 | A team withdraws. Midway the owner clarifies that "half their games" means half of the scheduled games, not half of the games played so far (rule 6). | Clarification mid-change |
| 9 | Export an ICS calendar for each team, keeping local times correct across DST (rule 7). | Cross-cutting |
| 10 | Add a referee-assignment constraint: a referee can't officiate a game involving their own team's division. | Depends on earlier rule |

**Why it tells the approaches apart.** Tiebreaker order and withdrawal handling are the kind of rule that lives only in the owner's head. Making rules depend on the season tests whether notes and specs keep up with the code.

**Risks.** Sports standings and round-robin scheduling are heavily represented in training data, so it is the closest of the five to a memorized solution. Constraint-solving work in the scheduler could dominate the cost and make the comparison noisy.

---

## Ranking

1. **Tickclock**
2. **Rostercalc**
3. **Pantry Ledger**
4. **Shedshare**
5. **Fixturely**

Tickclock is the best test. Its rules live outside the code as choices with no reasons attached: which calendar, which event counts, whether a breach ever clears. It's small enough to build cheaply, deterministic to grade with `as_of`, and its changes naturally reach back many sessions to depend on or reverse those early rules. That puts the most weight on what the repository records about intent, which is the thing the approaches differ in. Rostercalc is a close second, and the two would pair well if you want a second domain to check that results hold up.
