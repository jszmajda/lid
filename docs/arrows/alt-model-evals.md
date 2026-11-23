# Arrow: alt-model-evals

The alternate-model eval runner — runs LID's existing behavioral eval suites on non-Claude models through OpenRouter, driving the opencode coding agent inside a hardened container and capturing outputs in `skill-creator`'s per-eval shape for grading. Optional evidence for maintainers, never a merge gate.

## Status

**MAPPED** — new leaf segment (#78), sampled 2026-09-27, not yet audited. 128 of 129 specs implemented; the `ALT-EVAL-REC` process specs are satisfied by `tested_with` entries: 001 to 004 by the 1.4.0 capability roster's, and `ALT-EVAL-REC-005` (recording a batch run on a copy with the capability subsystem removed) by the Gemini 4 Argon and Muse Glimmer 30B entries of 2026-10-16. `ALT-EVAL-REC-006` (cost probes are never graded or recorded) is marked once a recording follows it.

## References

### HLD
- `docs/high-level-design.md` § *Code and tests for LID* — *Alternate-model runs* (optional evidence); tenets *Design for the pair, not the model* and *LID runs on the agent, not a runtime*

### LLD
- `docs/intent/alt-model-evals/alt-model-evals-design.md`

### EARS
- `docs/intent/alt-model-evals/alt-model-evals-specs.md` (129 specs, prefix `ALT-EVAL-*`, facets `CLI`, `KEY`, `STAGE`, `BOX`, `RUN`, `ROSTER`, `COST`, `OUT`, `REC`)

### Tests
- `tools/alt-model-evals/test_run_eval.py` — 132 tests against a stub `docker`/`npx`/`git` (`testdata/stub_harness.py`) and a local copy of OpenRouter's model list, plus recorded opencode 1.18.32 event streams (`testdata/opencode-events-*.jsonl`). Run: `python3 tools/alt-model-evals/test_run_eval.py`.

### Code
- `tools/alt-model-evals/run_eval.py` — the runner (stdlib Python, 3.9+)
- `tools/alt-model-evals/Dockerfile` — the harness image
- `tools/alt-model-evals/rosters.json` — roster presets (`capability`)

## Architecture

**Purpose:** Widen the set of models LID's eval results speak for, without making any contributor need an OpenRouter key, a container runtime, or the runner.

**Key Components:**
1. **Staging** — per run, a random scratch directory under `$XDG_CACHE_HOME/lid-alt-evals/` holding the fixture (a one-commit git repo), a copy of the invocation's `plugins/` snapshot (exactly the files its recorded tree ID covers, minus every `evals/` and `*-workspace/`), and the generated harness config.
2. **Harness container** — opencode (pinned) with the fixture read-write, plugins read-only, read-only root, dropped capabilities, 2 GiB / 512-process limits, key passed by name only.
3. **Capture container** — a second container with no network and no key produces `changes.patch` and `git-log.txt`, so host git never runs over the model-writable `.git`.
4. **Outputs** — `skill-creator`'s per-eval shape plus `batch.json` recording the `plugins/` git tree ID, which makes a dirty-tree batch citable once the tested text is committed.
5. **Rosters** — presets in `rosters.json` (`capability`: a model's capability-flag evidence roster) run across suites and models, batches interleaved by model and run in lanes, with per-model harness-error and cost stops.
6. **Cost** — every turn priced at OpenRouter's published prices; `--estimate` projects a batch's or roster's cost and time from a two-run probe, and `--max-cost` caps each model's spend.

## Spec Coverage

| Category | Spec IDs | Implemented | Gaps |
|---|---|---|---|
| Invocation | ALT-EVAL-CLI-001 to 018 | 18 | 0 |
| Credentials | ALT-EVAL-KEY-001 to 004 | 4 | 0 |
| Staging | ALT-EVAL-STAGE-001 to 015 | 15 | 0 |
| Harness and sandbox | ALT-EVAL-BOX-001 to 019 | 19 | 0 |
| Run lifecycle | ALT-EVAL-RUN-001 to 013 | 13 | 0 |
| Rosters | ALT-EVAL-ROSTER-001 to 012 | 12 | 0 |
| Cost | ALT-EVAL-COST-001 to 020 | 20 | 0 |
| Outputs | ALT-EVAL-OUT-001 to 022 | 22 | 0 |
| Recording (process) | ALT-EVAL-REC-001 to 006 | 5 | 1 (REC-006, marked at the next recording) |
| **Total** | | **128** | **1** |

## Key Findings

1. **The sandbox has to hold in both directions.** Capture runs in its own container because host git executes programs named in a repository's own config (`core.fsmonitor`, filter and diff drivers); the tests plant such a config and a symlinked `.git` and assert the host never touches them.
2. **The event-stream parser is pinned to real output.** Recorded opencode 1.18.32 streams are committed test fixtures, so a harness bump that changes the stream's shape fails a test rather than silently mis-grading.
3. **Spend tracks reasoning, not price.** Across the models run so far, spend on the same roster varied more than tenfold, mostly with how much a model reasons, so the runner estimates from a two-run paid probe rather than from earlier rosters' token counts.
4. **Cross-segment obligations:** `linked-intent-dev` documents the `harness` field on `tested_with`, and its *Capability Flags* names the test projects the `capability` roster preset runs.

## Work Required

### Nice to Have
1. Deferred in the LLD: baseline (without-skill) runs, a second harness, a per-batch minted key, egress limited to OpenRouter.
