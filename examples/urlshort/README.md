# urlshort — LID example project

A URL shortener, specified as pure LID intent — HLD, LLDs, and EARS specs. **No code.**

This example exists to demonstrate a single claim: *if LID is working, you should be able to delete all tests and code and regenerate them from the intent alone.* What's in this directory is the intent tree. What you produce from it, by handing it to an agent, is the implementation.

## How to use

1. Clone this directory into a working location (anywhere outside the LID repo).
2. Open it in your agentic coding tool. On Claude Code, install the LID plugins for the richest integration:
   ```
   /plugin marketplace add jszmajda/lid
   /plugin install linked-intent-dev@jszmajda-lid
   ```
   On other tools (Cursor, Windsurf, Copilot, Aider, Continue, Junie, Codex, Zed), drop the matching rule file from [`docs/setup.md`](../../docs/setup.md) into this example directory.
3. Tell the agent something like:
   > "Read the docs/ tree. I want to implement the URL shortener it specifies. Pick a stack (the HLD is deliberately stack-agnostic — recommend one, then we'll proceed). Use the LID workflow to generate tests first, then code, with `@spec` annotations citing the EARS IDs."
4. Review what the agent proposes, approve at each phase stop, and let it build.
5. When the coherence check passes — every EARS spec has a test citing its ID, every `@spec` annotation resolves — you have an implementation that traces to intent.

Run the same prompt twice, on two different machines, with different stack recommendations, and you'll get two different codebases. Both should satisfy the specs. That's the point.

## What's in here

```
docs/
├── high-level-design.md            # Problem, approach, goals, design decisions
├── llds/
│   ├── shortener-core.md           # Encode/decode, short-code format, collisions
│   ├── api.md                      # HTTP surface: endpoints, request/response shapes
│   └── storage.md                  # Persistence contract: operations, consistency
└── specs/
    ├── shortener-core-specs.md     # USH-CORE-* EARS specs
    ├── api-specs.md                # USH-API-* EARS specs
    └── storage-specs.md            # USH-STORE-* EARS specs
```

Three intent components, three LLDs, three spec files. The HLD ties them together and names the decisions that cross component boundaries.

## Why not ship the code?

Because *code is downstream of intent* — and this example is a pedagogical argument for treating it that way. A GitHub repo full of TypeScript would invite you to read the TypeScript first and treat the docs as commentary. That's backwards for LID.

If you want to see a full LID project with code, the containing repository (`jszmajda/lid`) is itself a LID project — specifying the LID plugins. Look there for a larger, already-implemented example.

## Regeneration invariants

If your regenerated implementation is honest about the intent, these should all hold:

- Every test that passes cites at least one EARS spec ID via `@spec`.
- Every behavioral EARS spec in the three spec files is cited by at least one test.
- `grep "USH-CORE-001"` across your codebase returns the spec, the tests that verify it, and the code that implements it.
- Deleting all tests and all code — leaving the three LLDs and three spec files — and re-running the regeneration prompt produces a working implementation again. Maybe a different one; that's fine.

If any of these break, there's an intent gap in the docs. File an issue against this example.

## Mode

This example is written in **Full LID** mode: every section of the HLD is filled, every LLD is complete, and every spec has its status marker. No `*(not yet specified)*` placeholders, no `[inferred]` markers. A freshly-implemented version of this example starts all specs as `[ ]` (unimplemented) and flips them to `[x]` as code lands.
