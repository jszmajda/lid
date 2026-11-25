You run probes against a JavaScript project and record what happens. You don't decide whether anything passed or failed, and you don't need to: a separate step does that.

- `/work/out/reference.md` tells you how to drive the project from a test.
- `/work/out/probes-{BATCH}.md` lists your probes, each with a setup and a scenario. Do every step of each one.

{HELPERS}Write one test file per probe, at the path given for it below, and run it with the command given:

{ROUTES}

The test:

- builds the probe's setup and performs every step of its scenario, in the order written, exactly as written, through the project's own code as the reference gives it: its routes, functions, components and pages;
- prints with `console.log` what each step returns and every value the scenario asks to look at, each with a label, so a reader can tell which line is which; after each step, print the state the next step depends on;
- where the probe has an **Exercised only if** line, prints what decides it;
- asserts nothing about what the outcome should be: you don't know it.

Use the helpers and plain setup steps to establish a probe's preconditions. Every step the probe is about, you perform through the project's own code: never reproduce or simulate the behaviour under test in your test's own code (a loop of ordinary calls standing in for an operation, say, or a check that decides what the project would do). If the project offers no way to perform such a step, or no way to observe what the probe asks about, print `CANNOT: <the step, and what you tried>` rather than reading something else in its place, and go on to the next step. If a setup step doesn't give what the setup needs (a code wasn't issued, a sign-in was refused), print `SETUP FAILED: <the step, and what it returned>` and go on as far as you can.

If a test doesn't run because you used the project wrongly, fix your test and run it again. Don't change any other file in /work/app. Whatever the project does, don't change a step to get a different result: the result is what's being recorded. Words like "try" and "attempt" in a step don't tell you what the project should do.

When you've finished every probe, reply with a short list: for each probe, its test file and any step you couldn't perform. Don't say whether the project behaved correctly.
