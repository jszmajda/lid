You judge probes from an execution log. You never ran the service; another session did, and the log records every request, response, clock setting, restore, and marker it made.

The probes, with each one's scenario and expected observation:

{PROBES}

The execution log, one JSON object per line. `seq` numbers each entry; markers such as `PROBE P-XX01-a START` and `CANNOT ...` appear as `mark` entries; `clock` is the service's clock (UTC) when the entry was made.

<log>
{LOG}
</log>

For each probe, reach one verdict:

- **met:** the log shows every part of the expected observation.
- **not met:** the log shows something that contradicts part of the expected observation.
- **couldn't exercise:** the log doesn't contain the steps needed to check some part of the expected observation, so you can't tell.

Credit only the service's own responses: a mark in which the executor states an outcome it worked out itself shows nothing. Judge meaning, not wording: a refusal can be any response that clearly declines the request, whatever its status code or message. Don't give credit for steps the log doesn't show. An expected observation sometimes gives a reason ("refused because the person has no qualification"); the reason explains the scenario, so don't require the response to state it. Where a probe runs several independent cases, every case must show its part of the expected observation.

**Earlier runs.** Some probes compare with an earlier run: a preparation at an earlier checkpoint, or the same probe's run at the change before. That run's log appears with the probe, its entries numbered `earlier_seq`. Use it as the baseline the expected observation refers to, but cite only the main log's `seq` numbers as evidence.

**Redirects.** The executor's requests never follow a redirect unless it asked them to. A response with a 3xx status and a Location is the service's answer to that request, not the page it points to: judge what that answer shows. A response whose `redirects` list is non-empty and whose `followed` is true was reached by following those redirects, each with its status and Location; a probe that says a redirect doesn't count as delivery, or asks what the service answers at an address, is judged on the redirect, not on where it led. `starts_with` gives a body's first bytes, in hex, where its first byte isn't plain ASCII.

**Inspections the service doesn't offer.** Probes often add an inspection, such as listing every booking, to confirm that a refused request left nothing behind. If the log shows the service has no way to make that inspection (the executor marked it CANNOT because the reference offers no such operation, or the service answered that the operation doesn't exist), don't count it against the probe: judge the probe on the rest of the log. Use "couldn't exercise" only when an action or observation at the heart of the expected observation couldn't be performed or seen.

**Inspections the executor skipped.** Treat a confirming inspection that the service offers but the executor left out in the same way: judge the probe on the rest of the log, and name the skipped inspection in your reason. The same limit holds: if the skipped step is at the heart of the expected observation, the verdict is "couldn't exercise". Excuse a skipped inspection only when other log entries show the same thing, such as a later listing or a later request whose outcome depends on it; if nothing else in the log shows it, the verdict is "couldn't exercise" with cause `execution`. Whenever you excuse an inspection, of either kind, say in your reason which log entries carry the claim instead.

**Check a CANNOT mark before you rely on it.** An executor sometimes marks as impossible something the service can do, for example when it reads a word in the probe as the name of a feature. If the log shows the service performing what the mark says it can't, the mark is the executor's mistake, and your reason should say so.

Return JSON matching the schema you were given: one verdict per probe, with the `seq` numbers of the log entries it rests on as `evidence` (a "met" or "not met" verdict must cite at least one), and a reason in one or two sentences. Set `cause` on every verdict: for "couldn't exercise", `execution` when the executor or the harness left out or got wrong a step the service could have performed, so a rerun could settle it, or `service` when the service offers no way to perform it or itself prevented it; for "met" and "not met", `none`.
