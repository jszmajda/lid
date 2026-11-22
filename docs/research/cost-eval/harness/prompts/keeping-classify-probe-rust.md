You rule on dependency probes that failed after a change to a Rust project. The project has two crates: a core library (clowder-core) that holds the game's state and rules, and a terminal shell (clowder-tui) that draws that state and sends the player's keys to the core. Each probe checks that the two agree after the change: that what the shell shows, counts, offers, or refuses follows what the core holds or decides. It compares the shell with the core, never with a fixed value, so whatever value the owner settles on passes it as long as both sides agree. Whoever made the change never saw it.

The change, as its owner asked for it:

<change>
{CHANGE}
</change>

The evidence, in numbered entries. For each failing probe: its failure output (`failure output`); when that output compares two JSON values, the harness's key-by-key difference between them (`json difference`, which names each value as the output does: left and right, or first and second in the order they appear); the probe's source (`test source`), and the source where the failure happened when that is outside the probe (`failure site`); and the functions in the probe's own files that the failing statement calls (`helper source`). Each entry's lines are numbered: source lines with the file's own line numbers, the other entries from 1.

<evidence>
{EVIDENCE}
</evidence>

A probe has two kinds of checks. Its comparison of shell and core decides the dependency. Its preconditions and readings only let it get there: assertions and expectations whose message begins `fixture:`, and the steps that find and read the text the shell draws (a line containing given words, a number in a given place).

For each probe, one classification:

- **settled precondition:** the check that failed is one of the probe's preconditions or readings, not its comparison of shell and core, and the change request itself settles the value, wording, or layout that check assumed: the owner asked for that very thing to be different. The probe then couldn't decide the dependency either way.
- **dependency failure:** anything else. The shell and the core disagree; a precondition or reading failed that the change request doesn't settle (the build broke something the probe relies on that the owner didn't ask to change); the library panicked; or the evidence doesn't show enough to tell.

Return JSON matching the schema you were given: one ruling per probe, with its `test` name as the evidence writes it, its `classification`, a `reason` in one or two sentences, and `evidence`: each entry the ruling rests on, as its `seq` and the `lines` within it that show it (at least one entry, each with at least one line).
