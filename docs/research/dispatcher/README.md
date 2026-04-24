# LID overlay dispatcher — prototype

Reads `*.overlay.yaml` manifests from a directory, invokes each manifest's
declared engine(s), aggregates results into `_status.yaml`, and reports
pass/fail for CI.

This is a **research prototype**. Not production-grade. Written to validate
the overlay-dispatch architecture in `docs/research/formal-verification-exploration.md`.

## Quick start

```sh
python3 dispatcher.py <overlay-dir> [--write-status] [--verbose] \
                     [--codeql-db PATH] [--json]
```

Example (runs against the B4 experiment's 10-spec sample):

```sh
python3 dispatcher.py \
  /Users/jess/src/lid/docs/research/experiments/b4-scale-10-ears/ \
  --codeql-db=/tmp/codeql-thr-det-018/db \
  --write-status --verbose
```

Output: per-spec per-engine verdict on stderr, optional `_status.yaml`
rollup in the overlay dir, optional JSON to stdout.

Exit code: `0` if every gate engine produced a terminal-positive status
(V, Vp, or Vn); `1` if any gate engine reports Vx or ?.

## Supported engines

| Engine | Invokes | Posture |
|---|---|---|
| `manual-review` | Reads signoff metadata (pass-through) | gate |
| `lemmascript` | `lsc check` via `node_modules/.bin/lsc` if available; else `?` | gate |
| `lemmascript-dafny` | `dafny verify <artifact>.dfy`; parses "N verified, M errors" | gate |
| `test-witness` | Validates contract YAML + checks witness file has declared describe/it | gate |
| `type-system` | `tsc --noEmit` via `node_modules/.bin/tsc` (upward search, dispatcher-dir fallback) | gate |
| `codeql` | `codeql query run --database=<db> <artifact>` (handles `.codeql` extension) | gate |
| `git-provenance` | `git log -S <spec-id>` + `git grep -l @spec <spec-id>` correlation | advisory |
| `differential` | Reads artifact and confirms findings section present | advisory |

## Tested against

- B4 experiment (`experiments/b4-scale-10-ears/`): 10 specs, 6 engine types,
  Wave-1 CodeQL DB. Result: 6V + 1Vn + 3Vx (70% terminal coverage); the
  3 Vx cases are real findings (2 missing workspace-package resolution,
  1 CodeQL query with 2 unexpected rows).

## Design notes

- **Gate vs advisory**: advisory engines (differential, git-provenance)
  never fail CI. They produce evidence for review but don't block.
- **Overall status aggregation** (per spec, across gate engines):
  Vx dominates; any V lifts to V; Vp next; Vn only when all-or-most Vn;
  else ?. A sibling engine's `?` (couldn't run) does not disqualify a
  V from another gate engine.
- **CodeQL `.codeql` vs `.ql`**: codeql CLI insists on `.ql`. Dispatcher
  auto-copies to `<artifact>.dispatcher-tmp.ql` for the run and cleans up.
- **Binary discovery**: `tsc` and `lsc` are looked up in `node_modules/.bin/`
  walking upward from the overlay dir, then in the dispatcher's own
  directory as a fallback.

## Limitations / known issues

- **Workspace-package imports** (e.g. a monorepo's `@pkg/types`) in overlay TS files
  aren't resolved — overlay artifacts should be self-contained. Real
  solution: dispatcher honors a `project_root:` field for tsc resolution.
- **CodeQL pack setup** is manual: each overlay dir using CodeQL needs
  its own `qlpack.yml` + `codeql-pack.lock.yml`. Dispatcher could
  auto-copy from a reference location.
- **lsc binary discovery** requires `npx lsc` or a local install;
  `lemmascript-dafny` sibling usually covers this.
- **test-witness is structural only** — checks the witness file contains
  the declared describe/it block. Does NOT run the tests. A companion
  test-runner integration would tighten this.
- **No caching**: every run re-invokes every engine. A hash-based
  result cache would help at scale.
- **No parallelism**: engines run sequentially. Trivial to parallelize
  per spec via `concurrent.futures.ThreadPoolExecutor`.
- **Negation-case / MC/DC verification not implemented** — the v0.3
  schema proposal includes `mc_dc_arms:`, but the dispatcher doesn't
  consume it yet.

## Next steps if promoted to production

1. Caching layer (hash each engine-artifact-input tuple)
2. Parallelize per spec
3. `derives_from:` provenance validation (orphan EARS detection)
4. MC/DC arm verification consuming v0.3's `ears_logical_structure:`
5. Pluggable engine registry (so new engines don't require editing this file)
6. Proper CLI with subcommands (`dispatcher run`, `dispatcher validate`,
   `dispatcher coverage`)
