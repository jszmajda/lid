You rule on existing tests that failed after a change to a JavaScript project. Each test was in the project before the change and passed there, checking behaviour the project had then; whoever made the change could see it, but the test runs here exactly as it was before the change. A failing test counts against keeping the project's behaviour, unless the only difference its failure reports is state the change itself adds, at its empty value.

The change, as its owner asked for it:

<change>
{CHANGE}
</change>

The evidence, in numbered entries. For each failing test: its failure output (`failure output`: the assertion's message, with the actual and expected values where the runner gave them, and the first lines of the stack); when both values are JSON, the harness's key-by-key difference between them (`json difference`, naming them actual and expected); and the test's source (`test source`). Each entry's lines are numbered: source lines with the file's own line numbers, the other entries from 1.

<evidence>
{EVIDENCE}
</evidence>

For each test, one classification:

- **new state only:** every difference the failure reports is state this change adds (a field, key, entry, or the like that holds what the change asks for) at its empty value: null, undefined, an empty string, array or object, zero, or false. A difference the test sets aside before comparing doesn't count: read the source to see what it compares.
- **keeping failure:** anything else. State that existed before the change differs or is missing; state the change adds holds a value that isn't empty; state appears that this change doesn't call for; the failure isn't a difference in state at all (an error thrown, a wrong count, an element not found, a timeout); or the evidence doesn't show enough to tell.

Return JSON matching the schema you were given: one ruling per test, with its `test` name as the evidence writes it, its `classification`, a `reason` in one or two sentences, and `evidence`: each entry the ruling rests on, as its `seq` and the `lines` within it that show it (at least one entry, each with at least one line).
