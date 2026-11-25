We're running a research study comparing how different ways of working with AI coding agents perform as software is changed over time. We look at two things: what the work costs, and how faithfully the software keeps doing what its owner intended. The approaches range from using an agent with no special process, through lightweight discipline, to structured methods that keep requirement and design documents next to the code.

In each run, an agent builds a small application from a product brief and then makes a sequence of changes to it. Each change happens in a fresh session, so the agent remembers nothing from earlier sessions beyond what is in the repository. A simulated product owner holds a fuller, hidden description of what they want (the "oracle") and answers the agent's questions from it. Model-based graders then check whether the running software still does everything the owner wants.

You proposed BenchTime as a project for this study, and we chose it for the pilot. Your proposal is included at the end for reference. Now I need you to write the hidden materials for it. A different writer will produce the product brief from your materials later, so you don't need to write the brief.

## How the materials are used

- **The product brief** is given to the agent at the start. It contains your interface specification and every item marked "stated at start", and nothing else from the oracle.
- **The simulated owner** holds the oracle and answers questions from it according to each item's disclosure kind (defined below). It never volunteers anything except where the change script says it does.
- **Each change in the change script** is given to the agent in a fresh session, in the owner's words.
- **Graders** check the running software against every item in force, through the external interface only. They can't see the source code. They can set the clock and reset all state.

## Part 1: Interface specification

An HTTP JSON API for the first version, within the V1 boundary of your proposal. Fix everything a grader needs: methods, paths, request fields, response fields with types, status codes, and one error format. Include:

- **The stack and run command.** Python 3.12, FastAPI, and SQLite, started with one command, for example `python -m benchtime --port 8000 --db ./benchtime.db`.
- **Reset.** An endpoint such as `POST /_admin/reset` that clears all state.
- **Clock.** A way to set the current time that every time-dependent rule uses, including expiry of provisional holds, for example `PUT /_admin/clock`.
- **Setup data.** How the lab's time zone, opening hours, holidays, instruments, people, and qualifications get into the system, for example `POST /_admin/setup` with one JSON document. Give a small example setup document with realistic values.

Later changes may add endpoints or fields. If a change does, specify them in that change, not here.

## Part 2: The oracle

**The narrative.** Write the owner's own account of what they want from BenchTime as narrative product prose, the way a lab manager would explain it to a colleague who is going to build it. Don't write it as a numbered list of formal requirements, and don't use "shall" or "when ..., the system shall" phrasing.

**The item table.** After the narrative, give a table of items. For each item, give:

- an ID (BT-01, BT-02, ...);
- one plain sentence stating the behaviour, written so it can be checked through the interface;
- its disclosure kind (below);
- the point where it comes into force (start, or change N);
- the change that retires it, if any;
- a short sketch of how a grader would check it through the interface, including any clock settings.

**Disclosure kinds:**

- **Stated at start:** in the product brief.
- **Stated in change N:** in that change's request.
- **Askable:** the owner knows it and gives it when asked about that topic, but wouldn't think to write it down.
- **Recognized on sight:** the owner can't put it into words unprompted, but rejects a plan or proposal that gets it wrong.
- **Emerging at change N:** the owner doesn't know it yet. Before change N they answer questions on the topic with "no preference, use your judgment". At change N they raise it unprompted, because using the system has taught them something.
- **Realized on symptom:** the owner notices it only when the software does it wrong. It enters the study as a bug report describing what they saw.

**Rules for the items:**

- About 30 to 45 items in total.
- Roughly: a third stated at start, a quarter stated in later changes, a quarter askable, a few recognized on sight, 2 or 3 emerging, and 2 realized on symptom.
- Each disclosure kind should be plausible for a real lab manager. Askable items are things a lab manager knows but wouldn't think to write down. Emerging items are things they would only realise after running the lab on the system for a while.
- Every item must be checkable through the interface, using the clock and reset.
- Every name, path, or literal value a grader needs to check an item must appear in the interface specification or in the text that discloses the item.
- No item may depend on specialist knowledge of laboratory practice or regulation. Anything domain-specific is the owner's own rule.
- Time-zone and daylight-saving items should be no more than about a fifth of the total. Keep inspection, qualification, closure, and limit rules as the heart of the project.

## Part 3: The change script

About 10 changes, in order. For each change, give:

- its number and type (from the list below);
- the owner's request, in their own words, as they would hand it to a developer;
- the items it introduces, retires, or relies on;
- any emerging item the owner raises during it, with the exact words;
- any realized-on-symptom report scheduled at this point: the symptom in the owner's words, and the condition under which it fires, meaning what the software would have to be doing wrong.

**Change types to cover, each at least once:**

- a rule that applies across the whole system;
- a reversal of an earlier decision;
- a change that needs the reason behind an earlier tradeoff;
- a bug report describing only a symptom;
- an ordinary local feature;
- a copy or configuration change;
- a dependency upgrade or a pure refactor with no change in behaviour;
- a change that touches many areas.

Put at least two changes late in the script that depend on rules established in the first three changes and not restated in the request.

**Redirects.** Two of the changes include a redirect:

- one change of mind, delivered early, when the agent first shows a plan or asks for approval;
- one clarification, delivered late, after code exists.

Give the redirect's exact words and the items it changes.

**Probe request.** Separately from the sequence, write one probe request. It must make sense at any point in the project's life, from just after the first build to after the last change, and it must touch several earlier rules. It will be run from several points in the sequence and then thrown away.

Keep the first build at about 1,800 to 2,700 lines of application code, and keep the growth across the changes modest.

## Format and constraints

- Write in Markdown with three top-level sections: Interface specification, Oracle, Change script. Then add the probe request.
- Don't name or allude to any particular development method, tool, or framework for working with coding agents.
- Where your proposal's details conflict with these instructions, follow these instructions. You may also improve on the proposal.

## Your original proposal, for reference

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

