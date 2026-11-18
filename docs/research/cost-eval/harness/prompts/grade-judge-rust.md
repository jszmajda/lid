You judge probes from what their tests did. You didn't run them: another session wrote one Rust integration test per probe, and the harness ran each test and recorded its output.

The probes, with each one's scenario and expected observation:

{PROBES}

The evidence, one JSON object per line. For each probe: its test's source (`test source`) and the output of running it (`test output`), or a note that it has no test (`missing`). `seq` numbers each entry.

<log>
{LOG}
</log>

For each probe, reach one verdict:

- **met:** the output shows every part of the expected observation.
- **not met:** a confirmed absence: the test did what the scenario says and printed the observation that decides the probe, and that observation shows the required behaviour absent or contradicted.
- **couldn't exercise:** the test couldn't show either way. This is the grader's error, never the library's, so the probe is run again. Name what went wrong as `fault`:
  - `compile`: the test doesn't compile because the executor used the library wrongly;
  - `fixture`: the test couldn't build the probe's setup;
  - `interface`: the test couldn't find how to perform a step (a `CANNOT` line, or a compile error naming something the library doesn't have);
  - `observation`: the test ran but didn't print the observation that decides the probe, or performed a different step, or skipped one.

A step the expected observation depends on that the test performed with its own logic rather than by calling the library (a loop of ordinary calls standing in for an operation, a check in the test deciding what the library would do) is the grader's fault too, `interface`: never "met" or "not met", whatever it printed.

Read the source to see what the test did and which printed line is which, and the output to see what happened. Give credit only for what the output shows: a step the source performs but whose result it never prints shows nothing, and is a fault, not a "not met". Judge meaning, not wording: a refusal can be any result that clearly declines (an error, a `None`, a state left unchanged), whatever its message. An expected observation sometimes gives a reason; it explains the scenario, so don't require the output to state it. Where a probe has several independent cases, every case must show its part of the expected observation. A panic inside the library during a step is something the library did: judge it against the expected observation.

Return JSON matching the schema you were given: one verdict per probe, with the `seq` numbers of the entries it rests on as `evidence` (a "met" or "not met" verdict must cite at least one), and a reason in one or two sentences. Set `cause` and `fault` on every verdict: for "couldn't exercise", `cause` is `execution` and `fault` one of the four above; for "met" and "not met", both are `none`.
