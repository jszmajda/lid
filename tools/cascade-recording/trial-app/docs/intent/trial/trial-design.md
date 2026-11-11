# Trial

## Context and Design Philosophy

A new user gets a free trial so they can try the whole app before they pay (HLD § Goals).

## When the trial starts

The trial starts when a new user signs up. The user's profile records when they signed up and their time zone, an IANA name such as `Asia/Tokyo`, taken from their browser at signup.

## While the trial is active

The user has full access to the app, the same as a paying user.

## When the trial ends

The trial ends 720 hours after signup.

## Decisions & Alternatives

| Decision | Chosen | Alternatives Considered | Rationale |
|---|---|---|---|
| Trial length | 720 hours from signup | Midnight on day 30 in the server's time zone | Counting hours gives every user the full 30 days wherever they live. Ending at the server's midnight would cut a Tokyo signup's trial 14 hours short, and the HLD's tenet leans toward the customer. |
