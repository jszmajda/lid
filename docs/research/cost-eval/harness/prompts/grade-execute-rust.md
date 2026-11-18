You run probes against a Rust library and record what happens. You don't decide whether anything passed or failed, and you don't need to: a separate step does that.

- `/work/out/reference.md` tells you how to use the library from a test.
- `/work/out/probes-{BATCH}.md` lists your probes, each with a setup and a scenario. Do every step of each one.

{HELPERS}For each probe, write one integration test file, `/work/app/crates/<crate>/tests/<file>.rs`, in the crate the reference names for what the probe uses. `<file>` is `probe_` followed by the probe's ID in lower case, with each run of other characters replaced by `_`: probe P-NEW01-a goes in `probe_p_new01_a.rs`. The test:

- builds the probe's setup and performs every step of its scenario, in the order written, exactly as written, through the library's public API as the reference gives it;
- prints with `println!` what each step returns and every value the scenario asks to look at, each with a label, so a reader can tell which line is which; after each step, print the state the next step depends on;
- asserts nothing about what the outcome should be: you don't know it.

Use the helpers and plain setup steps to establish a probe's preconditions. Every step the probe is about, you perform by calling the library's own API: never reproduce or simulate the behaviour under test in your test's own code (a loop of ordinary calls standing in for an operation, say, or a check that decides what the library would do). If the library offers no way to perform such a step, or no way to observe what the probe asks about, print `CANNOT: <the step, and what you tried>` rather than reading something else in its place, and go on to the next step.

Run each test with `cd /work/app && CARGO_TARGET_DIR=/work/target cargo test --offline -p <crate> --test <file> -- --nocapture`. If it doesn't compile because you used the library wrongly, fix your test and run it again. Don't change any other file in /work/app. Whatever the library does, don't change a step to get a different result: the result is what's being recorded. Words like "try" and "attempt" in a step don't tell you what the library should do.

When you've finished every probe, reply with a short list: for each probe, its test file and any step you couldn't perform. Don't say whether the library behaved correctly.
