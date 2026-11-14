# Plumbing scripts

Throwaway scripts from the plumbing test (milestone M1 in [../plan.md](../plan.md)). They are research notes, not the harness: the harness walks LID's arrow from an intent node under `docs/intent/` (see "Harness code" in [../README.md](../README.md)). Findings are in [../log.md](../log.md).

| File | What it is |
|---|---|
| `executor.Dockerfile` | Linux image for executor sessions: Python 3.12, uv, `libfaketime`, Claude Code pinned to 2.1.323, a neutral git identity, a non-root user, and its configuration in `/cfg` so a volume can hold each arm's sessions |
| `faketime-check.Dockerfile`, `faketime-check-app.py` | A FastAPI and SQLite app that reports Python's and SQLite's idea of now, for checking `libfaketime` |
| `gt` | A grading tool that sets the service's clock, resets it, makes requests, and runs setup commands inside its container, appending every call to an execution log |
| `with-token.sh` | Runs a command with the maintainer's subscription token in `CLAUDE_CODE_OAUTH_TOKEN`, without printing it |
| `extraction-prompt.md` | The prompt for the interface-extraction session, with the template appended |
| `grader-execute-prompt.md`, `grader-judge-prompt.md` | The two grading prompts: one runs probes and records, the other judges the log |
| `extraction-template-draft.md` | A first draft of the interface-extraction template |
| `host-flags.sh` | Flags that isolate a `claude -p` session on the maintainer's machine, before the container recipe was proposed |
| `reset-benchtime-plumbing.sh` | Starts the bare build of BenchTime from its checkpoint image on empty data, under the fake clock, keeping the last clock setting. Its start command is hard-coded from the interface reference |
| `acct.py` | Compares a session's reported usage with its main and subagent transcripts |

The probes used with `gt` quote the oracle's fixtures, so they're in the seed's private `hidden/` folder.
