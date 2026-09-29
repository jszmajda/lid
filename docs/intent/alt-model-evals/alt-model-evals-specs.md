# Alternate-Model Eval Runs Specs

**LLD**: docs/intent/alt-model-evals/alt-model-evals-design.md
**Implementing artifacts**:
- tools/alt-model-evals/run_eval.py
- tools/alt-model-evals/Dockerfile
- tools/alt-model-evals/test_run_eval.py
- tools/alt-model-evals/testdata/stub_harness.py
- tools/alt-model-evals/testdata/opencode-events-*.jsonl

Status markers: `[x]` implemented · `[ ]` active gap · `[D]` deferred

"The runner" in every line below is `tools/alt-model-evals/run_eval.py`. The `ALT-EVAL-REC` lines are process specs for whoever grades and records results; the runner never automates them. Each is marked `[x]` once a `tested_with` entry has been recorded by following it.

---

## Invocation

- `[x]` **ALT-EVAL-CLI-001**: The runner SHALL accept three positional arguments, in order: a skill directory name, an eval-ID selector, and an OpenRouter model ID.
- `[x]` **ALT-EVAL-CLI-002**: The runner SHALL resolve the skill name to exactly one `plugins/*/skills/<name>/` directory holding an `evals/evals.json`; when the name matches zero or more than one such directory, the runner SHALL exit non-zero before staging anything and name the matches (or their absence).
- `[x]` **ALT-EVAL-CLI-003**: The runner SHALL accept an eval-ID selector that is either the word `all` or a comma-separated list whose items are each a single integer ID or an inclusive range written `A-B`, matched against each eval's `id` field.
- `[x]` **ALT-EVAL-CLI-004**: When an integer named as a single item in the selector does not exist in the suite, or a range item matches no existing ID, the runner SHALL exit non-zero before running any eval and name the offending items; a range item selects the existing IDs within its bounds, and gaps inside it are not errors.
- `[x]` **ALT-EVAL-CLI-005**: The runner SHALL accept `--runs N` (a positive integer, default 1) and run each selected eval N times, completing all runs of one eval before starting the next, with evals taken in ascending ID order.
- `[x]` **ALT-EVAL-CLI-006**: The runner SHALL accept `--timeout SECONDS` (a positive integer, default 600) as the per-run wall-clock limit on the harness, measured from the moment the harness process starts.
- `[x]` **ALT-EVAL-CLI-011**: Where `--variant NAME` is given, the runner SHALL pass NAME unchanged to the harness's `--variant` option for every run in the batch; where it is omitted, the runner SHALL pass no variant.
- `[x]` **ALT-EVAL-CLI-012**: The runner SHALL accept `--effort LEVEL` (default `medium`) and, unless LEVEL is `default`, SHALL write it into the run's `opencode.json` as the `reasoning.effort` option of the model under test, for every run in the batch; with `--effort default` it SHALL write no effort option.
- `[x]` **ALT-EVAL-CLI-007**: The runner SHALL execute runs sequentially, one at a time.
- `[x]` **ALT-EVAL-CLI-008**: When a batch ends, the runner SHALL print a human-readable summary with one line per run giving the eval ID, run number, status, and cost, followed by the batch directory's path.
- `[x]` **ALT-EVAL-CLI-009**: The runner SHALL use only the Python standard library.
- `[x]` **ALT-EVAL-CLI-010**: The runner SHALL be executable as `tools/alt-model-evals/run_eval.py` from the repository root, and SHALL take the repository root to be the parent of the parent of the directory containing the runner (`tools/alt-model-evals/../..`), not the current directory.

## Credentials

- `[x]` **ALT-EVAL-KEY-001**: The runner SHALL read the OpenRouter key only from the `OPENROUTER_API_KEY` environment variable.
- `[x]` **ALT-EVAL-KEY-002**: When `OPENROUTER_API_KEY` is unset or empty, the runner SHALL exit non-zero before staging anything, with a message naming `OPENROUTER_API_KEY`.
- `[x]` **ALT-EVAL-KEY-003**: The runner SHALL pass the OpenRouter key to the harness only through process environments, SHALL NOT place the key's value in the argument list of any process it starts (the `docker` command included), and SHALL NOT write the key's value into any file.
- `[x]` **ALT-EVAL-KEY-004**: Before writing a run's outputs to the workspace, the runner SHALL replace every literal, byte-for-byte occurrence of the OpenRouter key with `[REDACTED]` in every captured regular file — `events.jsonl`, `stderr.log`, `response.md`, `changes.patch`, `git-log.txt`, and every regular file under the captured `project/` — leaving symbolic links untouched and each file's permission mode unchanged.

## Staging

- `[x]` **ALT-EVAL-STAGE-001**: For each run, the runner SHALL create a new scratch directory under `$XDG_CACHE_HOME/lid-alt-evals/` (or `~/.cache/lid-alt-evals/` when `XDG_CACHE_HOME` is unset), whose name is random and contains no part of the skill name, eval ID, or eval name.
- `[x]` **ALT-EVAL-STAGE-002**: The runner SHALL write each entry of the eval's `files` list to `project/<path>` inside the scratch directory with the entry's `content` exactly as given, applying no normalization, and creating parent directories as needed.
- `[x]` **ALT-EVAL-STAGE-003**: When any selected eval has a `files` entry whose `path` is absolute, contains a `..` segment, or has `.git` as its first segment, the runner SHALL exit non-zero before running any eval, naming the eval and the path.
- `[x]` **ALT-EVAL-STAGE-004**: The runner SHALL initialize `project/` as a git repository and make one commit of its full contents, with author and committer identity `eval <eval@localhost>` and the commit message `fixture`; for an eval with no files, that commit SHALL be an empty commit with no placeholder file.
- `[x]` **ALT-EVAL-STAGE-005**: The runner SHALL copy the repository's `plugins/` tree to `plugins/` inside the scratch directory, preserving its relative layout.
- `[x]` **ALT-EVAL-STAGE-006**: The staged `plugins/` copy SHALL contain no directory named `evals` and no directory whose name ends in `-workspace`, at any depth.
- `[x]` **ALT-EVAL-STAGE-007**: The runner SHALL write the harness configuration to `opencode.json` in the scratch directory, containing exactly four top-level keys and no others: `"autoupdate": false`, `"share": "disabled"`, a `provider` object whose `openrouter` entry's API key option is the literal string `{env:OPENROUTER_API_KEY}`, and a `skills` object whose `paths` list holds exactly the staged `plugins/` directory as the harness sees it.
- `[x]` **ALT-EVAL-STAGE-008**: The runner SHALL send the model one message built from a fixed template that states, in order: that it is executing one eval run of an agent skill and the current directory is the whole repository; the skill's name, to be loaded with the harness's skill tool, and the directory holding sibling skills; the eval's `prompt`, quoted verbatim, to execute per the skill with any file changes made directly; that the run is non-interactive, so where the skill would ask the user it takes the skill's stated default and states in its final response which defaults it took, and today's date; and that its final message must be the exact user-facing response and nothing else.
- `[x]` **ALT-EVAL-STAGE-009**: The run prompt SHALL NOT contain the eval's ID, the eval's name, or any assertion text.
- `[x]` **ALT-EVAL-STAGE-010**: When a run's outputs have been captured, the runner SHALL delete that run's scratch directory, whatever the run's status.
- `[x]` **ALT-EVAL-STAGE-011**: When a batch starts, the runner SHALL compute the git tree ID of the repository's `plugins/` directory as it exists on disk (tracked and untracked files, excluding gitignored ones) using a temporary index, without modifying the repository's own index, working tree, or history.

## Harness and sandbox

- `[x]` **ALT-EVAL-BOX-001**: The runner SHALL invoke the harness as `opencode run --pure --auto --format json -m openrouter/<model-id> <prompt>`, passing each element as a separate argument with no shell interpretation, and with stdin closed.
- `[x]` **ALT-EVAL-BOX-002**: The runner SHALL define the harness version as a single constant, and use that constant for the image build, the `--no-container` invocation, and every recorded `harness` value, written `opencode-ai@<version>`.
- `[x]` **ALT-EVAL-BOX-003**: `tools/alt-model-evals/Dockerfile` SHALL build from a Node base image pinned to an exact version tag, and install `git`, `ripgrep`, and `opencode-ai` at the version passed as a build argument.
- `[x]` **ALT-EVAL-BOX-004**: The runner SHALL tag the image with the harness version and a hash of the Dockerfile's contents, and SHALL build the image when no image with that tag exists.
- `[x]` **ALT-EVAL-BOX-005**: Unless `--no-container` is given, the runner SHALL execute each run's harness inside a new container started through the `docker` command.
- `[x]` **ALT-EVAL-BOX-006**: When `--no-container` is not given and `docker info` fails, the runner SHALL exit non-zero before staging anything, stating that no container runtime is reachable and naming `--no-container` as the unsandboxed alternative.
- `[x]` **ALT-EVAL-BOX-007**: The container SHALL mount the run's `project/` read-write at `/work/project` as its working directory, the run's `plugins/` read-only at `/work/plugins`, the run's `opencode.json` read-only at `/work/opencode.json` with `OPENCODE_CONFIG` set to that path, and a generated `passwd` file and `group` file read-only at `/etc/passwd` and `/etc/group`, each holding one entry for the invoking user's UID and GID with home directory `/home/eval`.
- `[x]` **ALT-EVAL-BOX-008**: The container SHALL have no host mounts other than those named in ALT-EVAL-BOX-007.
- `[x]` **ALT-EVAL-BOX-009**: The container SHALL run with a read-only root filesystem, and with `/home/eval` and `/tmp` on in-memory filesystems writable by the invoking user's UID.
- `[x]` **ALT-EVAL-BOX-010**: The container SHALL run as the invoking user's UID and GID.
- `[x]` **ALT-EVAL-BOX-011**: The container SHALL run with all Linux capabilities dropped, with privilege escalation disabled, with a memory limit of 2 GiB, and with a limit of 512 processes.
- `[x]` **ALT-EVAL-BOX-012**: The container's environment SHALL contain only `OPENROUTER_API_KEY`, `HOME=/home/eval`, `OPENCODE_CONFIG`, `GIT_AUTHOR_NAME` and `GIT_COMMITTER_NAME` set to `eval`, `GIT_AUTHOR_EMAIL` and `GIT_COMMITTER_EMAIL` set to `eval@localhost`, and locale variables, in addition to what the image defines.
- `[x]` **ALT-EVAL-BOX-016**: When `--no-container` is not given and the container runtime reports less total memory (`docker info` `MemTotal`) than the container memory limit of ALT-EVAL-BOX-011, the runner SHALL exit non-zero before staging anything, stating both amounts and that the runtime needs more memory.
- `[x]` **ALT-EVAL-BOX-017**: Unless `--no-container` is given, the runner SHALL produce `changes.patch` and `git-log.txt` by running git inside a second container started from the same image, with the settings of ALT-EVAL-BOX-009 through ALT-EVAL-BOX-011, no network, the run's project mounted read-write at `/work/project`, an empty output directory mounted read-write at `/work/out`, the `passwd` and `group` files of ALT-EVAL-BOX-007, and no `OPENROUTER_API_KEY` in its environment.
- `[x]` **ALT-EVAL-BOX-018**: Unless `--no-container` is given, once a run's harness has started the runner SHALL NOT run git on the host in, or on any path inside, that run's project directory, and SHALL NOT read, write, or delete any path inside the project's `.git`.
- `[x]` **ALT-EVAL-BOX-019**: The capture step's git commands SHALL disable `core.fsmonitor`, set `core.hooksPath` to `/dev/null`, and pass `--no-ext-diff` and `--no-textconv` to `git diff`.
- `[x]` **ALT-EVAL-BOX-013**: When `--no-container` is given, the runner SHALL print a warning, before the first run starts, that the model can read any file the invoking user can read.
- `[x]` **ALT-EVAL-BOX-014**: When `--no-container` is given, the runner SHALL run the harness through `npx -y opencode-ai@<version>` in the run's `project/` directory, with `HOME` and every `XDG_*` base directory set inside a throwaway directory created for that run alone, outside the scratch directory, and deleted when the run ends; and with an environment containing only `OPENROUTER_API_KEY`, `PATH`, `HOME`, the `XDG_*` variables, `OPENCODE_CONFIG`, the git identity variables of ALT-EVAL-BOX-012, locale variables, and `npm_config_cache` set to the invoking user's npm cache.
- `[x]` **ALT-EVAL-BOX-015**: When `--no-container` is given, the run prompt SHALL give the skill paths under the scratch directory's `plugins/` instead of `/work/plugins`.

## Run lifecycle

- `[x]` **ALT-EVAL-RUN-001**: The runner SHALL assign each run exactly one status: `completed`, `harness_error`, `timeout`, or `interrupted`.
- `[x]` **ALT-EVAL-RUN-002**: When the harness exits with code zero and its event stream contains no top-level event of type `error` (a line of the stream that parses as a JSON object whose own `type` field is `error`), the runner SHALL record the run as `completed`, including when the final message is empty.
- `[x]` **ALT-EVAL-RUN-003**: When the harness exits non-zero, or its event stream contains a top-level event of type `error` (as defined in ALT-EVAL-RUN-002), the runner SHALL record the run as `harness_error`, with the error's message; a failed tool call inside the stream does not by itself make a run a `harness_error`.
- `[x]` **ALT-EVAL-RUN-004**: When a run reaches its wall-clock limit, the runner SHALL stop it and record it as `timeout`.
- `[x]` **ALT-EVAL-RUN-005**: When the runner stops a run, it SHALL stop the run's container, or under `--no-container` the harness's whole process group, by sending a termination signal and then killing whatever remains after 10 seconds, before capturing outputs; the capture step SHALL remove any leftover `.git/index.lock` in the project before running git.
- `[x]` **ALT-EVAL-RUN-006**: The runner SHALL capture outputs for every run, whatever its status, including partial project state from runs that errored, timed out, or were interrupted.
- `[x]` **ALT-EVAL-RUN-007**: When two runs in a row within a batch end as `harness_error`, counted across eval boundaries, the runner SHALL run nothing further in the batch and record the batch as `aborted`.
- `[x]` **ALT-EVAL-RUN-008**: When the runner receives an interrupt, it SHALL stop the current run, record it as `interrupted`, capture its outputs, delete its scratch directory, record the batch as `aborted`, and exit non-zero.

## Outputs

- `[x]` **ALT-EVAL-OUT-001**: The runner SHALL write each batch to `<skill-dir>-workspace/alt-model-<YYYY-MM-DD>-<model-slug>/` beside the skill's directory, where the date is the batch's start date and `<model-slug>` is the model ID with every character outside `[A-Za-z0-9._-]` replaced by `_`.
- `[x]` **ALT-EVAL-OUT-002**: When the batch directory already exists, the runner SHALL claim the first free name formed by appending `-2`, `-3`, and so on, claiming it by creating the directory so that two concurrent batches cannot claim the same name.
- `[x]` **ALT-EVAL-OUT-003**: The runner SHALL write each eval's outputs under `eval-<id>-<name>/`, where `<name>` is the eval's `eval_name` sanitized as in ALT-EVAL-OUT-001.
- `[x]` **ALT-EVAL-OUT-004**: The runner SHALL write `eval_metadata.json` in each eval directory, containing the eval's `eval_id`, `eval_name`, `prompt`, and `assertions`, with each assertion copied unchanged from `evals.json`.
- `[x]` **ALT-EVAL-OUT-005**: The runner SHALL write each run's outputs to `with_skill/run-<n>/` in the eval directory, numbering runs from 1.
- `[x]` **ALT-EVAL-OUT-006**: Each run directory SHALL contain `events.jsonl` (the harness's stdout), `stderr.log` (its stderr), `response.md` (the text of the last event of type `text` in the stream — each such event carrying one complete text part — or empty when there is none), `timing.json`, `changes.patch`, `git-log.txt`, and `project/`.
- `[x]` **ALT-EVAL-OUT-007**: `changes.patch` SHALL contain every difference between the fixture commit and the project's final state, including files the model created and did not commit, and commits the model made.
- `[x]` **ALT-EVAL-OUT-008**: `git-log.txt` SHALL hold the output of `git log --stat` from the project's final `HEAD`.
- `[x]` **ALT-EVAL-OUT-009**: The captured `project/` SHALL hold the project's final state without its top-level `.git`, with symbolic links preserved as links and never followed, file permission modes preserved, and FIFOs, sockets, and device files omitted.
- `[x]` **ALT-EVAL-OUT-010**: `timing.json` SHALL record `model`, `harness`, `status`, `duration_ms`, `total_cost_usd`, `tokens`, `tool_calls`, `exit_code`, and `error_message`, where `total_cost_usd` and `tokens` are summed from the event stream and are `null` when the stream carries no cost or token figures.
- `[x]` **ALT-EVAL-OUT-011**: The runner SHALL write `batch.json` in the batch directory when the batch starts, recording the skill, the selected eval IDs, the model, the harness, the sandbox mode (`container` or `none`), the timeout, the run count, the repository's `HEAD` commit, the `plugins/` tree ID from ALT-EVAL-STAGE-011, whether that tree ID equals `HEAD`'s `plugins/` tree, and the state `running`.
- `[x]` **ALT-EVAL-OUT-014**: The runner SHALL record the batch's effort and variant in `batch.json` (the variant null when none was given) and SHALL append to the batch directory name the effort when it is not `medium`, then the variant when one was given.
- `[x]` **ALT-EVAL-OUT-015**: When a batch finishes, the runner SHALL report the median reasoning tokens of its completed runs and, where an effort other than `default` was requested and that median is below 500, SHALL print a warning that the model did not reason at the requested effort.
- `[x]` **ALT-EVAL-OUT-012**: When a batch finishes, the runner SHALL update `batch.json`'s state to `complete`, or to `aborted` when the batch was stopped early.
- `[x]` **ALT-EVAL-OUT-013**: The runner's event-stream parsing SHALL produce the expected response, cost, token, tool-call, and error values from event streams recorded from the pinned harness version and committed as `tools/alt-model-evals/testdata/opencode-events-*.jsonl`.

## Recording results

- `[ ]` **ALT-EVAL-REC-001**: A `tested_with` entry recording alternate-model results SHALL name the exact OpenRouter model ID and the harness as `opencode-ai@<version>`, taken from the graded runs' `timing.json`.
- `[ ]` **ALT-EVAL-REC-002**: A batch SHALL be recorded in `tested_with` only when its `batch.json` `plugins/` tree ID equals the `plugins/` tree of a commit in the repository's history.
- `[ ]` **ALT-EVAL-REC-003**: Only `completed` runs SHALL be graded; the pass rate SHALL be computed over completed runs only; `timeout` runs SHALL be reported beside the pass rate as a count; and `harness_error` and `interrupted` runs SHALL be excluded from both.
- `[ ]` **ALT-EVAL-REC-004**: A batch with no `completed` runs SHALL NOT be recorded in `tested_with`.
