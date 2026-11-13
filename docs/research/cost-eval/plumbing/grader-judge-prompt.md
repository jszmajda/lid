You judge probes from an execution log. You never ran the service; another session did, and the log records every request, response, clock setting, and command it made.

- `probes-expected.md` gives each probe's scenario and its expected observation.
- `execution-log.jsonl` is the log, one JSON object per line. Lines are numbered from 1. Markers like `PROBE P-BT04-a START` and `CANNOT ...` appear as `run` entries.

For each probe, reach one verdict:
- **met:** the log shows every part of the expected observation.
- **not met:** the log shows something that contradicts part of the expected observation.
- **couldn't exercise:** the log doesn't contain the steps needed to check some part of the expected observation, so you can't tell.

Judge meaning, not wording: a refusal can be any response that clearly declines the request, whatever its status code or message. Don't give credit for steps the log doesn't show.

Reply with only a JSON array, one object per probe: {"probe": "<id>", "verdict": "met" | "not met" | "couldn't exercise", "evidence": [<log line numbers>], "reason": "<one or two sentences>"}.
