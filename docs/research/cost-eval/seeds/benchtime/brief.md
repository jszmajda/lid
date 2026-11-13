# BenchTime

I manage a small shared laboratory, and I'd like you to build BenchTime for us. We'll use it to reserve our instruments, check them out, and keep equipment that isn't ready out of circulation. Each of our instruments is an individual piece of equipment, not one of a pool. I run the lab, and the people booking instruments are our researchers and staff.

You're designing the interface, so this brief says what the lab needs to be able to do and the rules we've settled on, not how the software should expose them.

## Our records

Our records need to get into the system. We keep:

- the lab's time zone, its opening hours for each day of the week, and the dates it closes as lab holidays;
- our instruments, each with a name and a cleaning allowance in minutes;
- our people, each with a name;
- qualifications, each recording that one person may use one instrument, valid from one date and time until another.

## Booking

People can book an instrument outright, or place a provisional hold first. A hold lasts ten minutes, and confirming it makes it a confirmed booking without it becoming a different booking. Each booking or hold is one lasting record of who booked which instrument, when, any note they added, and whether it started as a hold or as a confirmed booking.

A booking or hold can't start in the past, and it has to fit inside one opening period on a day that isn't a lab holiday, in the lab's own time zone.

Two bookings or live holds on the same instrument can't overlap. One can end exactly when the next begins, as long as no cleaning allowance applies.

To book or hold an instrument, a person needs a recorded qualification for each instrument they're booking, valid at the time of the booking.

Each person can have at most three upcoming confirmed bookings.

Cancelling a hold or a confirmed booking that hasn't been used frees its time for someone else.

People need to be able to ask whether a booking would work before they make it. The answer has to match exactly what would happen if they made a confirmed booking right then, for the same person, instruments, and times.

## Using an instrument

Checking an instrument out happens during a confirmed booking: from the moment the booking starts up to, but not including, the moment it ends. A booking can have at most one checkout outstanding.

When an instrument comes back, the booking and the instrument wait for inspection. If an inspection fails, it can be done again, and the first inspection that passes completes the booking.

We also need to see an instrument's physical state: ready, checked out, or waiting for inspection. That's separate from the calendar, so a future booking or a maintenance closure doesn't change it.

## Maintenance

We record maintenance closures on instruments. A closure stops new bookings and holds that would overlap it. It doesn't cancel confirmed bookings that already exist; those can still be used.

## Time

Anything that depends on the time uses the current time straight away. Nothing waits for a background job to catch up, and the times the system records come from the same clock.

## Running it

Our IT team needs these, exactly:

- Python 3.12, FastAPI, and SQLite.
- One command, documented in the README, starts the service.
- All of the service's data lives in one location that the start command uses.
- The service reads the current time from the system clock.
