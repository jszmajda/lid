---
parent: lid-experimental
prefix: EXP-DEPTH
---

# LLD: Review Depth (experiment)

## Context

The core workflow stops at every phase boundary, and the human rules at every stop (LID-CORE-005; HLD tenet *Every phase is inspected*). For a small change inside a mature, well-specified segment, the interrupt count is the methodology's most-cited friction. The core's instrument framing already lets the human change *who* inspects at a stop; it deliberately does not change *how many stops there are* — cadence collapse is exactly what this experiment tests before core may absorb it.

This experiment adds a **declared review depth**: the human names the phase depth they personally review; deeper phases still run in full, but their outputs consolidate into one review at the declared boundary. Nothing in `linked-intent-dev` changes — this skill overlays guidance beside it, ships opt-in in the `lid-experimental` plugin, and per-phase stops remain the default and only advertised behavior everywhere.

Skill variant: pure-prose (guides agent behavior alongside the core workflow; no deterministic procedure). Verification is dogfooding; `[x]` marks behavior the SKILL.md embodies.

## Declaring a review depth

The declaration is **user-authored prose**, not LID-written configuration. LID defines no bullet, key, or section for it — the user writes their preference in their own instruction file (or states it in-session), and this skill recognizes it. A recommended shape, documented for copy-adaptation:

> Review depth: I review through LLD; below that, consolidate to one review.
> Judgment areas: naming and API shapes; anything touching auth.

Depth values follow the phases: *through HLD*, *through LLD*, *through EARS*, *through tests* — "through X" means phases at or above X stop per-phase; deeper phases consolidate. **Judgment areas** name the kinds of specification forks the human wants routed to them immediately regardless of depth.

This keeps the core decision (`docs/decisions/inspection-instrument-selection.md`) fully intact: LID still writes no inspection configuration anywhere; the user's own prose is the declaration, exactly as that decision anticipated for standing preferences.

## Depth semantics and guardrails

- **Every phase still runs.** What collapses is the interrupt count, not the phase set or the discipline. Phase outputs below the declared depth accumulate and present as one consolidated review at the declared boundary: LLD delta, spec delta, fork-log disposition, and failing tests.
- **Eligibility is declared at entry, per change.** The agent states why the change qualifies — segment-local, no HLD or structural LLD work anticipated — and proceeds consolidated only on the user's go. Eligibility is never the agent's silent call.
- **Fail-open.** If the work touches the HLD, restructures an LLD, or cascades across a segment boundary mid-change, the remainder of the change reverts to per-phase stops.
- **Overrides stand.** *The user is always right — with warning* applies unchanged in both directions: a user may collapse further or restore per-phase at any moment.

## Fork protocol

Specification forks — a spec or draft admitting more than one reading (LID-CORE-050 territory) — are latent-intent questions only the human can answer. Depth changes when the human *reviews*; it never changes who resolves a fork.

- **In a declared judgment area → interrupt immediately**, whatever the depth.
- **Outside judgment areas → park, never resolve.** The fork is written to the **fork log at detection, before work routes around it** — externalized so retention never depends on the model holding state across the change. An entry is lean: the spec line, the divergent readings, area classification, status.
- **Dependency rule:** no tests or code land against a spec whose fork is unresolved; the agent does the independent work first.
- **Critical-path escape:** a fork that blocks all remaining work interrupts immediately regardless of classification.
- **At the boundary, read — don't recall.** The consolidated review presents parked forks by reading the log, grouped by kind. Each ruling comes with an offer to update the declared judgment areas to match the revealed pattern — the judgment map is living, and the accumulated fork taxonomy is this experiment's most valuable output.

**Fork log location** (confirmed at change entry, file created if absent): `docs/arrows/_experiments/review-depth/<segment>/fork-log.md` when the arrow-maintenance overlay is present — the reserved experiment namespace, excluded from audits, removable at retirement. On overlay-less projects the skill asks once and the answer rides the user's declaration prose.

## Promotion and retirement

Stated up front, per experiment discipline:

- **Promote** — as **quiet absorption**: a documented, discoverable core capability that LID never advertises or suggests; per-phase stops remain the visible default. Bar: at least five dogfooded declared-depth changes across at least two projects in which no consolidated review surfaced a correction a per-phase stop would have caught earlier at lower rework cost, and the friction reduction is affirmatively reported by the user. Promotion reopens the no-configuration decision with evidence in hand.
- **Retire** — if consolidated reviews repeatedly trigger multi-phase rework (the boundary feedback invalidating already-drafted work), or if the fork protocol's parking proves unsafe in practice.

Rework cost at the consolidated boundary — not interrupt count alone — is the honest metric: feedback arriving after five phases can invalidate all five.

## Known limitations

Eligibility is agent self-assessment. The fail-open triggers key on structural acts — an HLD edit, an LLD restructuring, a boundary crossing — so an architectural decision the agent does not recognize as architectural fires none of them and reaches the user inside the consolidated review. This is not designed away: detecting it would require the agent to notice what it failed to notice, and in practice agents tend to over-suggest HLD involvement rather than under-suggest it, which bounds the risk. The promotion evidence bar measures exactly this failure: a consolidated review that surfaces a correction a per-phase stop would have caught earlier counts against promotion.

## Decisions & Alternatives

| Decision | Chosen | Alternatives Considered | Rationale |
|---|---|---|---|
| Declaration declaration form | User-authored prose, recognized by the skill | LID-defined `- Review:` bullet in the `## LID` block (licensed by the inspection-instrument decision doc's experimental carve-out); conversational-only | A structured bullet makes LID the author of inspection config it elsewhere refuses to write; conversational-only makes the user re-declare each session, which is itself the friction under test. Prose the user writes is a standing declaration with zero LID-defined surface — and a minimal-harness user is exactly the user who writes their own instruction file. |
| Fork log home | `docs/arrows/_experiments/review-depth/` (overlay present); ask-once otherwise | A new `.lid/` working directory; conversation memory | The `_experiments/` namespace exists for precisely this — experiment state attached to the overlay, audit-excluded, `rm -rf` at retirement. A parked fork held only in conversation memory is silently lost to context compaction, which is the failure the write-at-detection rule exists to prevent. |
| Consolidated-stop placement | One boundary after tests, before code | Boundary before tests; per-rung mini-boundaries | The review must contain failing tests to preserve tests-first edge detection; earlier placement reviews intent nobody has tried to pin executably yet. The rework risk this creates is the experiment's central measurement, not a flaw to design away. |

## Open Questions & Future Decisions

1. **Fork taxonomy shape** — the kinds that emerge from dogfooding (naming, ordering, scope, error-shape…) are unknown; the boundary review's grouping vocabulary should form from real logs, not be pre-designed.
2. **Cross-session parked forks** — a change abandoned mid-flight leaves a fork log behind; whether resumption pre-flight should surface stale logs is deferred until one actually goes stale.

## References

- `docs/intent/lid-experimental/lid-experimental-design.md` — parent sub-HLD.
- `docs/decisions/inspection-instrument-selection.md` — the no-configuration decision this experiment's declaration form preserves.
- `docs/intent/linked-intent-dev/core/core-design.md` — the stop discipline and instrument framing this experiment overlays.
- `plugins/lid-experimental/skills/review-depth/SKILL.md` — the artifact.
