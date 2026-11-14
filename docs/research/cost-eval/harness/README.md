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
| `costeval/simulator.py` | The simulated owner: parses the seed's oracle and change script, releases the narrative and items in stages by change, and builds the owner's prompt from `prompts/simulator.md` under one of three reviewing policies |
| `prompts/simulator.md` | The owner's prompt template. The oracle content is filled in at run time, so the template itself holds nothing hidden |

Executor sessions need the maintainer's subscription token in `CLAUDE_CODE_OAUTH_TOKEN`. [../plumbing/with-token.sh](../plumbing/with-token.sh) sets it without printing it.
