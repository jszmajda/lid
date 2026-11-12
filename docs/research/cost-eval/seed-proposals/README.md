# Candidate projects for the pilot seed

Three models from three families each answered the same prompt ([prompt.md](prompt.md)) on 2026-11-12. The prompt describes the study without mentioning LID or any other named system. Each model's full reply is in this folder, with a header recording how it was produced:

- [claude-opus-5.5.md](claude-opus-5.5.md): a fresh `claude -p` session with no tools and no project context.
- [gpt-6.1-sol.md](gpt-6.1-sol.md): one OpenRouter call at high reasoning effort.
- [gemini-4-argon.md](gemini-4-argon.md): one OpenRouter call at high reasoning effort.

**Status:** waiting for the maintainer to pick.

## All fifteen at a glance

"Rank" is the proposing model's own ranking among its five. "Rules at the core" lists the kinds of hidden rule that do most of the work.

| Project | Proposer (rank) | What it is | Interface | Rules at the core | Risk the proposer flagged |
|---|---|---|---|---|---|
| Tickclock | Opus (1) | Service-level timers for a support desk | HTTP | Business time on the customer's calendar and time zone, pause rules, breaches that never clear | Mostly calendar arithmetic, so it might measure date skill rather than intent |
| Rostercalc | Opus (2) | Shift pay for casual event staff | CLI | Overtime against night and holiday premiums, rounding in the worker's favour, closed pay periods | Models may import real labour law; overlaps with Tickclock |
| Pantry Ledger | Opus (3) | Food-bank inventory and distribution | CLI | Append-only ledger, personal data never exported, per-household visit limits | Broad surface; the first build may exceed 3,000 lines |
| Shedshare | Opus (4) | Community tool library | HTTP | Loan periods counted in open days, holds, a fine-free reversal | Close to a textbook exercise |
| Fixturely | Opus (5) | Amateur league fixtures and standings | CLI | Tiebreaker order, withdrawals, forfeits | Heavily represented in training data |
| BenchTime | Sol (1) | Lab instrument reservations | HTTP | Cleaning buffers, qualifications valid for the whole booking, inspection before reuse | Scheduling patterns are familiar to models |
| ReleaseDesk | Sol (2) | Embargoed archive publication | HTTP | Embargo plus approval, takedowns that reach old download bundles, restricted records invisible everywhere | Security breadth |
| LoopCrate | Sol (3) | Reusable packaging returns depot | HTTP | Custody separate from the paying account, idempotent retries, compensating entries | Could drift into full accounting software |
| RoundTable | Sol (4) | Community microgrant review | HTTP | Immutable application versions, reviewer conflicts, blind views in every export | Needs care to avoid subjective grading |
| FieldLedger | Sol (5) | Offline habitat-survey reconciliation | CLI | Tombstones, edits tied to a base revision, coordinate privacy | Sync complexity may dominate |
| FabQuota | Argon (1) | Shared fabrication-lab scheduling and grant billing | HTTP | Reserved, tool-busy, and billable time kept distinct; cooldowns; grant caps | Interval and DST arithmetic |
| SplitLedger | Argon (2) | Royalty waterfall for creative collectives | CLI | Waterfall order, recoupment kept per project, banker's rounding remainders, tax escrow | Floating-point money |
| ProtoWindow | Argon (3) | Clinical-trial visit windows and drug kits | HTTP | Visits anchored to day 0, a blinding rule that must never leak, a one-way dose ratchet | Graders need concrete date tables |
| ThermAudit | Argon (4) | Cold-chain shipment temperature audit | CLI and HTTP | Temperature budgets inherited across lot splits, calibration offsets | Needs physics given in the brief |
| GridShare | Argon (5) | Community-solar credit settlement | CLI and HTTP | Time-of-use credit cascade, first-in-first-out credit bank, income-based quotas | Unfamiliar jargon |

## Patterns across the three

- **The three proposers independently converged on shared-resource booking.** Sol's top choice (BenchTime) and Argon's (FabQuota) are nearly the same domain: booking shared lab equipment, with buffers, qualifications, and inspection or cooldown. Opus's top choice (Tickclock) is a close relative: time rules that depend on a calendar and a state.
- **All three asked for a clock the grader can set.** Each said, without being asked, that time-dependent rules need an injectable clock (an `as_of` value) so graders can reproduce results. The plan review asked for the same thing.
- **Time zones and daylight-saving changes appear in almost every proposal.** Opus warned that this can turn the study into a test of date arithmetic rather than of keeping intent. A seed where time is one rule family among several, or a brief that pins a date library, keeps that in proportion.
- **A rule that every new surface must obey is the clearest test of intent across sessions.** ReleaseDesk (restricted records), ProtoWindow (blinding), Pantry Ledger (personal data), and RoundTable (blind views) each have one, and a black-box grader can check it by looking for a leak through any endpoint.
- **Argon's proposals are the most intricate,** with several rules interacting in each one, and the hardest to build within 3,000 lines. One of its change sketches (ProtoWindow change 8) contains a visible slip where the model reconsiders its own bug mid-sentence. Drafts written by models need a careful read before they become seeds.
