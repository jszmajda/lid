# Harness

The code that runs the eval. Its design is "The harness" in [../design.md](../design.md). It serves this study, so it sits outside LID's arrow, and it has tests wherever a quiet bug would bias the results.

It needs Python 3.12 (standard library only), Docker, and the executor image built from [../plumbing/executor.Dockerfile](../plumbing/executor.Dockerfile). Run the tests from this folder:

```
python3.12 -m unittest discover -s tests
```

| Module | What it does |
|---|---|
| `costeval/usage.py` | Reads a session's token usage by model and token class, from its result record or, for a run that left none, from its transcripts. A resumed session's totals are cumulative, so each turn's usage is the difference between consecutive results |
| `costeval/executor.py` | Runs one `claude -p` turn in the executor container, with the arm's workspace and configuration volumes and the token passed by name, and checks the session's start-up record against the arm and the pinned versions. Also runs harness roles (the simulator, extraction, graders) in the container, with only the tools they name |
| `costeval/simulator.py` | The simulated owner: parses the seed's oracle, change script, and owner items (each askable item's salience tier and recall line), releases what the owner knows by change, works out what it is shown at each stop and splits it into numbered passages, makes one model call per stop (repairing slips with one right answer, retrying only structural faults), applies attention and recall with seeded draws (the constants are `OwnerModel`), inserts drawn recall lines after the trim, times and inserts redirects, and builds the leak judge's prompt |
| `costeval/trajectory.py` | Arms, the first prompt of each change, the arm's workspace volume, and the loop that runs one change between the agent and the owner, recording every turn and owner call (with every draw) and committing at the end |
| `run_trajectory.py` | Runs one arm's trajectory through a seed's changes, or continues one that stopped. `--replicate` (required) sets the seed the owner's draws share across compared trajectories, `--owner-model-config` the owner's constants; both are recorded. Each change starts from the owner as saved after the one before, and the first build from an empty owner. Records go to `../runs/`, which git ignores |
| `arms/` | The arm configurations: `bare`, `cheap-discipline` (with its `AGENTS.md`), and `lid-full`, plus `bare-aa` (the A/A check) and `positive-control` (a deliberately careless arm) |
| `costeval/grading.py` | Grading one checkpoint: parsing the probes, exporting the commit, extraction, app containers, setups, probe batches, judgment, and item verdicts |
| `grade_checkpoint.py` | Grades one checkpoint of a trajectory with parallel workers; also runs a symptom change's diagnostic |
| `audit_owner.py` | Runs the leak judge over a real trajectory's owner replies |
| `run_probe.py` | Runs the seed's probe request on a disposable fork of a trajectory's checkpoint |
| `rejudge.py` | Judges a graded checkpoint's logs again, with the same or another model, for test-retest and judge comparisons; `--probes` judges against the probe version the logs were executed under |
| `report.py` | Summarizes a stage's trajectories per arm: items met (by disclosure kind, and by guessability band where the seed has one), agent and owner cost, owner replies, words shown, touchpoint kinds, leak flags, cost by change, and the probe-request forks |
| `sample_verdicts.py` | Builds spot-check packets of sampled verdicts for whoever checks the graders in the maintainer's place |
| `classify_touchpoints.py`, `prompts/touchpoints.md` | Sorts each request the agent made of the owner into the kinds in "Human cost", from what the owner saw, never from its reply |
| `grading/control.py` | The control server inside each app container: starts the arm's service under libfaketime, forwards requests, sets the clock, restarts, restores setups, runs only named setup commands, and writes the execution log |
| `grading/gt` | The graders' only way to reach the service, through the control server |
| `prompts/owner-trim.md` | Cuts the owner's draft answers and corrections to what the question or the quoted wrong words need |
| `prompts/extraction.md`, `prompts/extraction-template.md` | The interface-extraction session and its fixed reference template |
| `prompts/grade-setup.md`, `prompts/grade-execute.md`, `prompts/grade-judge.md` | The graders' three sessions: loading setups, running probes, judging logs |
| `prompts/simulator.md` | The owner's prompt template. The oracle content is filled in at run time, so the template itself holds nothing hidden |
| `prompts/leak-judge.md` | The leak judge's prompt: given everything the owner was given and the reply it sent, it lists what the reply shared without licence |

Executor sessions need the maintainer's subscription token in `CLAUDE_CODE_OAUTH_TOKEN`. [../plumbing/with-token.sh](../plumbing/with-token.sh) sets it without printing it.
