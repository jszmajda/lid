Please write a product brief for a service called BenchTime, in the voice of the person who manages a small shared laboratory. They are handing it to a developer who will build the service. Use only the material below.

## What you have to work with

**Who and why.** A small shared laboratory uses BenchTime to reserve individually identified instruments, check them out, and keep unavailable equipment out of circulation. The person writing the brief manages the lab. The people booking instruments are its researchers and staff.

**What the lab's records contain.** This is only a list of what the lab keeps; it implies no rules:

- the lab's time zone, its opening hours for each day of the week, and the dates it closes as lab holidays;
- its instruments, each with a name and a cleaning allowance in minutes;
- its people, each with a name;
- qualifications, each recording that one person may use one instrument, with the date and time it is valid from and valid until.

**The owner's up-front rules.** These are the only rules the owner has decided to put in the brief:

- A successful booking or hold creates one stable record retaining its person, instrument, times, note, and initial held or confirmed state.
- Bookings and live holds on the same instrument cannot overlap; touching endpoints are permitted when no cleaning allowance applies.
- A booking or hold must start no earlier than the current time and fit wholly within one opening period on a non-holiday date in the lab's time zone.
- Creating a booking or hold requires a recorded qualification for every requested instrument, valid at the time of the booking.
- A provisional hold has a ten-minute lifetime and can become confirmed without changing its booking identity.
- Canceling an unused held or confirmed booking releases its reserved capacity.
- Checkout requires a confirmed booking at a time within its half-open booked interval and creates at most one outstanding checkout for that booking.
- Return puts the booking and instrument into awaiting-inspection state. Failed inspections may be retried until the first pass completes the booking.
- Maintenance prevents new bookings and holds whose protected instrument interval overlaps the closure.
- Adding maintenance leaves existing confirmed bookings usable rather than canceling them.
- Each person may have at most three upcoming confirmed bookings.
- Checking availability gives the same yes-or-no decision as an immediate attempt to make a new confirmed booking for the same person, instruments, and interval.
- Checking instrument status reports physical readiness, checkout, or pending inspection independently of calendar bookings and maintenance.
- Time-dependent decisions and recorded event times use the current system clock immediately, without waiting for a background task.

**Fixed operating requirements.** Our IT team needs these, exactly:

- Python 3.12, FastAPI, and SQLite.
- One command, documented in the README, starts the service.
- All of the service's data lives in one location that the start command uses.
- The service reads the current time from the system clock.

## How to write it

- Write in the first person, as the lab manager. Sound like a capable person explaining what they need to a developer they trust, not like a specification.
- Open with what BenchTime is for and who uses it.
- Explain the up-front rules in the owner's own words, grouped the way a lab manager would think about them. Every rule must be there, with its meaning unchanged. Some rules are worded loosely on purpose, so don't tighten them, resolve them, or add examples or edge cases that go beyond them.
- Don't add any rule, behaviour, or example of behaviour that isn't in the material.
- Don't describe an interface: no endpoints, field names, status codes, or data formats. The developer designs the interface. Say what the lab needs to be able to do, not how the software exposes it.
- Mention that the lab's records (listed above) need to get into the system, without saying how.
- End with the fixed operating requirements in a short section of their own, stated exactly as given.
- Aim for about 500 to 800 words.
- Don't use "shall" or formal requirement phrasing, and don't number the rules.
- Don't mention testing, grading, a study, or AI, and don't name any development method or tool beyond the stack above.

Reply with the brief in Markdown and nothing else.
