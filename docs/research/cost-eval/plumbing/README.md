# Plumbing scripts

Throwaway scripts from the plumbing test (milestone M1 in [../plan.md](../plan.md)). They are research notes, not the harness: the harness walks LID's arrow from an intent node under `docs/intent/` (see "Harness code" in [../README.md](../README.md)). Findings are in [../log.md](../log.md).

| File | What it is |
|---|---|
| `executor.Dockerfile` | Linux image for executor sessions: Python 3.12, uv, `libfaketime`, Claude Code pinned to 2.1.323, a neutral git identity, a non-root user |
| `faketime-check.Dockerfile`, `faketime-check-app.py` | A FastAPI and SQLite app that reports Python's and SQLite's idea of now, for checking `libfaketime` |
| `gt` | A grading tool that sets the app's clock, resets it, and makes requests, appending every call to an execution log |
| `extraction-template-draft.md` | A first draft of the interface-extraction template |
| `host-flags.sh` | Flags that isolate a `claude -p` session on the maintainer's machine, before the container recipe was proposed |
| `acct.py` | Compares a session's reported usage with its main and subagent transcripts |

The probes used with `gt` quote the oracle's fixtures, so they're in the seed's private `hidden/` folder.
