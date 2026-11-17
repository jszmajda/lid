A note for posterity on the approach used to build portfolio-tracker — distinctive enough to be
worth remembering and reusing.

## The shape

Two clean phases, in order:

1. **Author the *entire* intent tree, collaboratively, before any code.** HLD → every LLD → every
   EARS spec, across all segments, walking the linked-intent workflow's phase stops with the user
   and hardening as we went. Nothing was implemented until the whole arrow existed.
2. **Implement it all with a background workflow.** Once the intent was complete and coherent, a
   single orchestrated workflow built the code TDD-first, segment by segment, with adversarial
   review baked in.

The bet: intent-authoring is where human bandwidth matters most (narrowing latent intent, choosing
among defensible options, catching edge cases) — so do it richly and interactively. Implementation
against a precise, frozen intent is mechanical, parallelizable, and adversarially checkable — so
hand it to a workflow.

## Phase 1 — authoring the intent (interactive)

- HLD drafted from competing architecture options + elicited tenets; revised live as the user's
  thinking changed (e.g. Sheets-as-source-of-truth replaced SQLite mid-design).
- Each segment got an LLD then its EARS, with a **mandatory stop** at every phase boundary for the
  user to react. Decisions (FMV-at-vest basis, residency-stamped tax, ppm rates, the two-tier cache
  fingerprint, the gilt "Ledger" TUI theme, ratatui) were surfaced as *choices*, not guesses.
- Every LLD was hardened by a **zero-context adversarial edge-probe** (a subagent hunting that
  component's own gaps) before its EARS were written; findings were triaged with the user.
- `tui` was promoted to a **sub-HLD** (entry + views) when one leaf outgrew itself.
- After the whole tree existed, a **cross-segment Phase-4 seam audit** ran **7 parallel auditors**,
  one per seam-cluster. That audit found the biggest gap in the design: a missing **`runtime`**
  segment (the unowned Sheets-access layer + advisory lock + replay/marks orchestration) that three
  auditors independently pointed at. It was added before any implementation.

Result: HLD + 10 segments + EARS, mutually coherent within and across segments.

## Phase 2 — implementing the intent (workflow)

- A **foundation workflow** built `pt-core` + `ledger-core` first, to establish the verified-kernel
  template: TDD (red `@spec` tests fanned out per facet → green), then Verus + Kani. Standing up
  the toolchain surfaced real lessons that became reusable rules:
  - Verus can't see cross-crate consts (mirror them inside `verus!{}`); `div_euclid`/`rem_euclid`
    need a tightly-scoped `assume_specification`; meaningful `ensures` (conservation, rounding)
    matter, not just no-overflow.
  - **Kani bit-blasts `i128`, so a symbolic divisor hangs** — keep divisors *concrete* and target
    the arithmetic kernel, never the heap-collection fold (that stays in bounded `#[test]`s).
  - **Every Verus/Kani invocation is wrapped in `gtimeout … 300s`** — a run past 5 minutes is a
    smell and is treated as a failure.
- The **build-app workflow** (34 agents, ~5 h) then implemented the remaining 9 segments in
  dependency order. Each segment: TDD → (Verus+Kani for the verified `tax` kernel, capped) →
  **N zero-context bidirectional adversarial reviewers** (forward: is every spec faithfully
  implemented; backward: does the code do anything the specs don't state, and is the intent
  complete) → **resolve**. It finished by wiring the `pt` binary, the end-to-end `ci.sh`
  (build·test·capped-Verus·capped-Kani·`@spec`-coverage·e2e), a GitHub Actions file, and a
  **real-Sheets e2e** that round-trips against a live workbook.

## The discipline that made it work

- **EARS are frozen during implementation.** Tests and code are free; the specs are the contract.
- **Adversarial review at both phases.** Per-segment edge-probes while authoring; zero-context
  bidirectional review while implementing. Skeptics with no conversation context keep the output
  distribution honest.
- **Intent gaps are logged, not silently applied.** The implementation review surfaced **59
  intent-completeness gaps** (places the code had to make a sensible call the EARS never pinned —
  e.g. the federal-only stacked-rate ceiling, the import commit-lock isolation, TUI empty-state
  wording). Those were *reported*, not folded into EARS mid-build.

## The cleanup tail (don't skip it)

Design-first-then-workflow is **not** one-shot. Implementation reveals intent the authoring phase
didn't pin, so the method has a reconciliation tail: **triage the logged EARS-gap findings and fold
the legitimate ones back into the specs** (a normal LID cascade — EARS → tests → code), restoring
the arrow to full coherence. The code is green and self-consistent before this; the cleanup makes
the *intent* complete again.

## Artifacts

- The intent tree: `docs/high-level-design.md` + `docs/intent/**`.
- The workflow scripts are persisted under the session's `workflows/scripts/` (re-runnable /
  resumable).
- The `jj` history reads as the story: design layer → ledger-core foundation → Verus hardening →
  Kani fix → all remaining arrows.
