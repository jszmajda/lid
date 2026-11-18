You are writing an interface reference for a Rust library. Graders who have never seen it will write Rust integration tests against it using only your reference: they build the state a scenario needs, call the library, and print what they observe. They will not see the source, the docs, or the existing tests.

The library is the Cargo workspace at /work/app. Don't change anything in it, except one throwaway test file while you check your examples (step 3). Run cargo with `CARGO_TARGET_DIR=/work/target` and `--offline`, so later steps reuse the build.

1. See what the most recent change did: `cd /work/app && git diff {BASE} HEAD --stat`, then the diff itself. Read the code it touches, and enough of the public API around it to use it.
2. Work out how a test outside the crates reaches it: the crate names to `use`, the public modules, types, constructors, and functions, and how to get the library into the states tests need (a fresh start, a loaded save, time passing, a particular quantity of something). Cover the calls the change added or altered, and the basic calls for building state and reading it back.
3. Check every example you document: put them in `crates/<crate>/tests/zz_reference_check.rs`, run `cargo test --offline -p <crate> --test zz_reference_check -- --nocapture`, fix the reference until they compile and run, then delete that file.
4. Write the reference to /work/out/reference.md: for each operation, its name in plain words, the exact Rust to call it (the `use` lines and a short example that compiles), and what it returns, with a real value printed from your check where it helps.

The reference says how to call things, never what they are for or what rules apply. Don't state requirements, rules, limits, or reasons, and don't quote docs, specs, comments, or test names. If a call you checked happened to return an error or refuse something, you may show it as an example of how refusals look, without saying why.
