---
name: review-depth
description: Experimental let-go review depth for linked-intent development. Use when a LID project's instruction file declares a review posture in prose (e.g. "Review posture - I review through LLD; below that, consolidate to one review") or the user asks to batch phase reviews, consolidate stops, or let go below a phase depth. Overlays the linked-intent-dev workflow — every phase still runs; interrupts consolidate. Never activates on its own judgment.
---

# Review Depth (experiment)

An experimental overlay on the `linked-intent-dev` workflow: the user declares the phase depth they personally review; deeper phases still run in full, but their outputs consolidate into **one review at the declared boundary** instead of stopping per phase. Per-phase stops remain LID's default — this skill changes nothing unless the user has declared a posture.

## Recognizing the posture

The posture is the **user's own prose** — in their instruction file or stated in-session. LID writes no configuration for it. Recommended shape (offer it to users who want a standing declaration):

> Review posture: I review through LLD; below that, consolidate to one review.
> Judgment areas: naming and API shapes; anything touching auth.

Depth values track the phases — *through HLD*, *through LLD*, *through EARS*, *through tests*. "Through X": phases at and above X stop per-phase as usual; deeper phases consolidate. **Judgment areas** name the fork kinds the user wants routed to them immediately (see below). No declaration means no change: full per-phase stops.

## Entering a change

Declare eligibility before consolidating — never decide it silently:

> This change qualifies for consolidated review: segment-local, no HLD or structural LLD work anticipated. Proceeding under your through-LLD posture — per-phase for HLD/LLD, one consolidated review after tests. OK?

**Fail-open.** If the work turns out to touch the HLD, restructure an LLD, or cascade across a segment boundary, revert to per-phase stops for the remainder of the change and say so.

## Fork protocol

A specification fork — a spec or draft line admitting more than one reading — is a latent-intent question. Depth changes how the user *reviews*; it never changes who *resolves* a fork:

- **In a declared judgment area:** surface immediately, whatever the depth.
- **Outside judgment areas:** park it — **write it to the fork log at detection, before routing around it.** Never resolve it silently. Entry shape: the spec line, the divergent readings, kind, status.
- **Dependency rule:** write no tests or code against an unresolved fork's spec line; do the independent work first.
- **Critical-path escape:** a fork blocking all remaining work surfaces immediately.

**Fork log location:** `docs/arrows/_experiments/review-depth/<segment>/fork-log.md` when `docs/arrows/` exists; otherwise ask the user once and record the answer in their posture prose. The log is externalized state — retention must never depend on holding forks in working memory across the change.

## The consolidated review

At the declared boundary, present one review containing:

1. The LLD delta and spec delta.
2. **Parked forks, read from the fork log** — grouped by kind, never reconstructed from memory. The user rules on each; resolutions land as narrowing edits or new atomic spec lines (per the core Phase 4 rule).
3. An offer to update the declared judgment areas when the rulings reveal a pattern ("both forks were naming calls — add naming to your judgment areas?"). The judgment map is living.
4. The failing tests, per tests-first.

Then proceed to code with the core workflow's normal Phase 6 coherence verification.

## Standing rules

- Every phase runs; only the interrupt count collapses. The consolidated review must preserve per-phase edge detection — if it can't (too much accumulated), say so and fall back to per-phase.
- The user may override in either direction at any time (*the user is always right — with warning*).
- This is an **experiment** (`lid-experimental`). Promotion target and evidence bar live in `docs/intent/lid-experimental/review-depth/review-depth-design.md`.
