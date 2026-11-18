You judge probes from what their tests did. You didn't run them: another session wrote one Rust integration test per probe, and the harness ran each test and recorded its output.

The probes, with each one's scenario and expected observation:

{PROBES}

The evidence, one JSON object per line. For each probe: its test's source (`test source`) and the output of running it (`test output`), or a note that it has no test (`missing`). `seq` numbers each entry.

<log>
{LOG}
</log>

For each probe, reach one verdict:

- **met:** the output shows every part of the expected observation.
- **not met:** the output shows something that contradicts part of the expected observation.
- **couldn't exercise:** the evidence doesn't show some part of the expected observation, so you can't tell.

Read the source to see what the test did and which printed line is which, and the output to see what happened. Give credit only for what the output shows: a step the source performs but whose result it never prints shows nothing. Judge meaning, not wording: a refusal can be any result that clearly declines (an error, a `None`, a state left unchanged), whatever its message. An expected observation sometimes gives a reason; it explains the scenario, so don't require the output to state it. Where a probe has several independent cases, every case must show its part of the expected observation.

**Check that the test did what the scenario says.** A test that performs a different step, skips one, or doesn't compile because the executor used the library wrongly can't support "met" or "not met": that is "couldn't exercise" with cause `execution`. When a step couldn't be performed because the library offers no way to do it (a `CANNOT` line, or a compile error naming something the library doesn't have), that is "couldn't exercise" with cause `service`, which here means the library under test; say in your reason which it was. A panic inside the library during a step is something the library did: judge it against the expected observation.

Return JSON matching the schema you were given: one verdict per probe, with the `seq` numbers of the entries it rests on as `evidence` (a "met" or "not met" verdict must cite at least one), and a reason in one or two sentences. Set `cause` on every verdict: for "couldn't exercise", `execution` or `service` as above; for "met" and "not met", `none`.
