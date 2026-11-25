You judge probes from what their tests did. You didn't run them: another session wrote one test per probe for a JavaScript project, and the harness ran each test and recorded its output.

The probes, with each one's scenario and expected observation:

{PROBES}

The evidence, one JSON object per line. For each probe: its test's source (`test source`) and the output of running it (`test output`), or a note that it has no test (`missing`). `seq` numbers each entry.

<log>
{LOG}
</log>

For each probe, reach one verdict:

- **met:** the output shows every part of the expected observation.
- **not met:** a confirmed absence: the test did what the scenario says and printed the observation that decides the probe, and that observation shows the required behaviour absent or contradicted.
- **not exercised:** only for a probe with an **Exercised only if** line: the output shows that line's condition doesn't hold on this build (what it needs wasn't built), so the probe can be neither met nor not met. A probe without that line is never "not exercised".
- **couldn't exercise:** the test couldn't show either way. This is the grader's error, never the project's, so the probe is run again. Name what went wrong as `fault`:
  - `compile`: the test doesn't run because the executor used the project wrongly (an import or call that doesn't exist, a syntax error in the test);
  - `fixture`: the test couldn't build the probe's setup;
  - `interface`: the test couldn't find how to perform a step (a `CANNOT` line, or an error naming something the project doesn't have);
  - `observation`: the test ran but didn't print the observation that decides the probe, or performed a different step, or skipped one.

A step the expected observation depends on that the test performed with its own logic rather than through the project's code (a loop of ordinary calls standing in for an operation, a check in the test deciding what the project would do) is the grader's fault too, `interface`: never "met" or "not met", whatever it printed. So is a stand-in: a test that read something else in place of what the probe asks about (another field, a log entry, a related value) because it found no way to observe the thing itself.

Read the source to see what the test did and which printed line is which, and the output to see what happened. Give credit only for what the output shows: a step the source performs but whose result it never prints shows nothing, and is a fault, not a "not met". Judge meaning, not wording: a refusal can be any result that clearly declines (an error status, an error message, a state left unchanged), whatever its words. An expected observation sometimes gives a reason; it explains the scenario, so don't require the output to state it. Where a probe has several independent cases, every case must show its part of the expected observation. An error thrown by the project during a step is something the project did: judge it against the expected observation.

When a setup step failed (a `SETUP FAILED` line, or a step before the one the probe is about didn't give what the setup needed), set `failed_postcondition` to what that step needed, in a few words ("a phone code is issued"), and `postcondition_row` to the ID of the row below whose behaviour that step relies on, if one does, else `none`. Otherwise set them to "" and `none`. The rows of this change:

{ROWS}

Return JSON matching the schema you were given: one verdict per probe, with the `seq` numbers of the entries it rests on as `evidence` (a "met", "not met" or "not exercised" verdict must cite at least one), and a reason in one or two sentences. Set `cause` and `fault` on every verdict: for "couldn't exercise", `cause` is `execution` and `fault` one of the four above; for the others, both are `none`.
