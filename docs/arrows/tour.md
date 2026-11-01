# Arrow: tour

The newcomer tour segment: the short introduction LID offers a person the first time they meet it inside their coding agent, the topics they can go further into, the notes during their first change, how their answer is recorded, and the content of the marketing site's Tour page.

## Status

**MAPPED**, landed with issue #84 in 1.4.3. All 129 specs implemented, including the by-eye render check (`TOUR-080`).

## References

### HLD
- `docs/high-level-design.md` § Goal 5; Tenets (*Friendly over exacting when introducing LID*, *Introduce LID fast*); Key Design Decisions *Introducing LID inside the agent*, *Product documents and the HLD*, and *Harness capabilities: used when present, never required*

### LLD
- `docs/intent/tour/tour-design.md`

### EARS
- `docs/intent/tour/tour-specs.md` (129 specs, prefix `TOUR-*`)

### Tests / Evals
- Scenario evals carrying `TOUR-*` IDs: `linked-intent-dev` evals 4–7, `update-lid` evals 21–23, `map-codebase` eval 3 (and one assertion on eval 2).
- `PKG-CHECK-039` (packaging checks) keeps `tour.md` and `tour-topics.md` out of the workflow skill's reference list.
- The content check: a blind reader given only the tour files and the specs checks the fixed text against the requirements.

### Code (owned artifacts)
- `plugins/linked-intent-dev/skills/linked-intent-dev/references/tour-offer.md`: who sees the offer, the card, answers, the memory record; assembled into the workflow doc
- `plugins/linked-intent-dev/skills/linked-intent-dev/references/tour.md`: the five steps, the notes, the example, the markers
- `plugins/linked-intent-dev/skills/linked-intent-dev/references/tour-topics.md`: the 19 topics

The routes' own passages (the workflow skill, `update-lid`, `map-codebase`) and the site's Tour page belong to those segments.

## Architecture

**Purpose:** Give a person meeting LID for the first time a short, friendly introduction at the moment they meet it, without holding up their work, and keep that introduction coherent with the HLD.

**Key Components:**
1. **The offer card**: a quoted card at the top of the route's first message, with the route's own message below it. Carrying on declines it.
2. **The opening**: five steps, one per message, built on a 30-day free-trial example.
3. **Topics**: short, self-contained explanations of LID's other capabilities, reachable during the tour or at any time.
4. **The record**: one fact in the harness's per-person memory, never in the project's files.

## Spec Coverage

| Category | Spec IDs | Implemented | Deferred | Gaps |
|---|---|---|---|---|
| Files, who sees it, card, answers | TOUR-001–021, 089–091, 111, 112, 129 | all `[x]` | 0 | 0 |
| Opening and example | TOUR-022–047, 092–094, 113–122 | all `[x]` | 0 | 0 |
| Topics | TOUR-048–054, 095–099, 123 | all `[x]` | 0 | 0 |
| Notes | TOUR-055–061, 100–104 | all `[x]` | 0 | 0 |
| Claims and words | TOUR-062–072, 105, 124–128 | all `[x]` | 0 | 0 |
| Looks | TOUR-073–080 | all `[x]` | 0 | 0 |
| Recording and hosts without plugins | TOUR-081–088, 106–110 | all `[x]` | 0 | 0 |

## Key Findings

1. **The routes own *when*; this segment owns *how*.** Each route's passage only checks memory and points to `tour-offer.md`, so changes to the tour's wording never reach the routes, and the arrow index has no loop.
2. **Two files ship to hosts without plugins differently.** `tour-offer.md` rides in the workflow doc; `tour.md` and `tour-topics.md` are fetched by link only when asked for.
3. **The tour is downstream of the workflow and of every capability its topics describe.** Changes there review the matching tour text (`TOUR-098`, `TOUR-099`).

## Work Required

### Nice to Have
1. Run the tour evals across more models than the one smoke run so far, and record them in each suite's `tested_with`.
