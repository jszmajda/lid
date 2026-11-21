You rule on held-out tests that failed after a change to a Rust project. Each test was written before the change, to check behaviour the project had then, and whoever made the change never saw it. A failing test counts against keeping the project's behaviour, unless the only difference its failure reports is state the change itself adds, at its empty value.

The change, as its owner asked for it:

<change>
{CHANGE}
</change>

The evidence, in numbered entries. For each failing test: its failure output (`failure output`); when that output compares two JSON values, the harness's key-by-key difference between them (`json difference`, which names each value as the output does: left and right, or first and second in the order they appear); the test's source (`test source`), and the source where the failure happened when that is outside the test (`failure site`); and the functions in the test's own files that the failing statement calls (`helper source`). Each entry's lines are numbered: source lines with the file's own line numbers, the other entries from 1.

<evidence>
{EVIDENCE}
</evidence>

For each test, one classification:

- **new state only:** every difference the failure reports is state this change adds (a field, key, entry, or the like that holds what the change asks for) at its empty value: null, None, an empty string or collection, zero, false, or its type's default. A difference the test sets aside before comparing doesn't count: read the source to see what it compares.
- **keeping failure:** anything else. State that existed before the change differs or is missing; state the change adds holds a value that isn't empty; state appears that this change doesn't call for; the failure isn't a difference in state at all (a panic, a wrong count, an error returned); or the evidence doesn't show enough to tell.

Return JSON matching the schema you were given: one ruling per test, with its `test` name as the evidence writes it, its `classification`, a `reason` in one or two sentences, and `evidence`: each entry the ruling rests on, as its `seq` and the `lines` within it that show it (at least one entry, each with at least one line).
