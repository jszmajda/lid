You are writing an interface reference for a piece of software. Graders who have never seen it will use your reference to operate it from outside: load setup data, make requests, and read the responses. They will not see the source, the docs, or the tests.

The software's repository is a copy at /home/agent/app. Don't change anything in it. Use /tmp for anything you need to write, including the service's data location.

1. Read the README and enough of the code to find how to start the service, how setup data gets in, and every operation it offers.
2. Start the service yourself on an empty data location under /tmp. Make every call you document once, and copy the real request and response into the reference. Stop the service when you're done.
3. Write the reference to /out/reference.md, following the template below exactly.

The reference says how to call things, never what they are for or what rules apply. Don't state requirements, business rules, limits, or reasons, and don't quote docs, specs, comments, or test names. Name each operation plainly ("create a booking") and give the exact call. If a real response happens to show a refusal, include it as an example of how refusals look, without explaining why it was refused.

TEMPLATE
# Interface reference: <checkpoint id>

Write this reference for someone who has never seen this software and must operate it from outside. Say how to call things. Never say what the software is meant to do, what rules it enforces, or why: no requirements, no business rules, no quotes from docs, specs, comments, or tests. Name each operation plainly ("create a booking"), then give the exact call. Verify every call you document by making it once against a fresh instance, and show the real response.

## 1. Starting the service
- Start command, exactly as the README gives it, and the directory it runs from.
- Where data lives, and how to point the service at an empty data location.
- Port and base URL. Any environment variables it needs.

## 2. Loading setup data
For each kind of setup data the software accepts (for example people, instruments, calendars, qualifications), give the exact call that loads it, with a complete worked example. Say if setup data can only be loaded in some ways (a file at start-up, a command, an HTTP call).

## 3. Operations
For each operation: its plain name; the exact call (method and path, or command); every input with its type and format; a real example request and the real response it returned; how the response reports a refusal or an invalid request (status code and body shape), with a real example.

## 4. Identifiers and times
How each kind of thing is identified, and who chooses the identifier. The format times are given and returned in, and the time zone they are read in.

## 5. Not available
Anything an outside operator might look for but the interface doesn't offer.
