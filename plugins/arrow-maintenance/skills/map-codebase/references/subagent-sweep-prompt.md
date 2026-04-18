# Sweep Worker Prompt Template

Use this when spawning parallel subagents for Phase 1 reconnaissance. Adapt the scope block to whatever slice of the codebase the subagent is handling.

---

## Task

You are a reconnaissance subagent for a brownfield mapping operation. Your job is to **read every file** in your assigned scope and produce a structured per-file report. Do not attempt to segment, cluster, or design — that happens later.

## Scope

{describe the subagent's slice — e.g., "files under `src/api/`", "files under `packages/auth/`", or a concrete file list}

## For each file, record

Produce one entry per file. Format:

```yaml
- path: {relative path from repo root}
  purpose: {one-line, what this file appears to do}
  exports: {functions, classes, types, endpoints exposed to other parts of the system}
  dependencies: {what it imports or calls — list the specific symbols or modules, not just "various"}
  data_shapes: {structures it produces or consumes, briefly}
  side_effects: {filesystem, network, database, logs, external services — "none" if pure}
  role: {how this file fits in the larger system — UI component / API handler / background job / data transform / pure utility / config / test / etc.}
  observations: {anything unusual: deprecated comments, TODO markers, inconsistent patterns, tight coupling, references to code that doesn't exist}
```

## Constraints

- **Read every file.** Do not skip.
- **Read actual content, not filenames.** A file called `utils.ts` may be the payment gateway.
- **Trace to file and line** when noting observations. `observations: "deprecated comment at line 42"` is useful; `observations: "looks old"` is not.
- **Don't infer design intent.** If you can only see what the code does, not why, say so. "Appears to retry with exponential backoff, up to 3 attempts" is good. "Implements the team's retry policy" is speculation.

## Output

Write your report to `{path-given-by-orchestrator}` (typically something like `.lid/map-codebase/sweep-{N}.md`). Do not emit the report inline in the response — the orchestrator will consume your file. The orchestrator may not have room to hold all subagent outputs at once, so file-based handoff is the mechanism.

End your response with a brief summary: how many files you read, any scope issues (files you couldn't read, unexpected file types, scope boundaries that seemed ambiguous).
