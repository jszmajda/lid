# Coach follow-up turns

Read after the coach's report, when the user takes up the offer to help. The report itself is produced from `SKILL.md`; this file covers the conversation that follows.

## Subsequent user-driven turns — detail or working session

After the user responds to the offer, the coach engages. Possible shapes:

- **Walk through findings** (or a subset). Render detailed finding paragraphs (the form below) for the requested subset — all, the high-priority ones, a specific theme, etc. **Don't re-render the inventory, audit content, or executive summary** — those were in the report.
- **Focus on a theme or priority.** Render only the relevant subset.
- **Working session on a specific finding.** Engage on that finding directly — discuss, refine, or plan a fix — without re-rendering the broader report.
- **Skip detail, jump to action.** Surface concrete next steps for the highest-impact findings without restating each.

When the user picks no specific direction, default to walking through findings in priority order.

## Detailed finding paragraph form (subsequent turns)

When detailed findings are rendered, each finding is **one paragraph**, not a sub-bullet form. The paragraph weaves four elements together:

- The **observation** — concrete, naming files or lines where useful, with evidence inline where the reader needs it to see the pattern. Findings *may* cite specific counts when the count is the observation itself (e.g., "the spec file has 3 IDs in the legacy 1000-block alongside semantic-naming IDs"), but never as a numeric grade.
- The **LID principle** the finding relates to, cited by name with a plain-English gloss appended inline.
- **Why this matters** — a sentence or two explaining the consequence of leaving the drift in place, or the benefit of fixing it. Draw from the principle's motivation (in the principle body in `SKILL.md`) grounded in *this* user's project — what gets harder, what compounds, what gets more reliable. The coach teaches while correcting.
- A closing **recommended action** — concrete, naming files or commands. See *Recommended-action targets* below.

**Example of the paragraph form** — showing how observation, principle-with-gloss, *why this matters*, and action weave as prose:

> **F2 — Medium. A few superseded LLDs are still living in `docs/intent/` alongside current ones.** `keeper-three-phase-orchestration.md`, `keeper-orchestration-integration-testing-strategy.2025-08-01.md`, and `bedrock-throttling-retry-system.2025-01-31.md` all describe themselves (or are marked in the arrow index) as superseded; `docs/intent/old/mobile-app-architecture-ux.md` sits in an `old/` subdirectory. Under *mutation, not accumulation* — docs reflect current intent and git preserves history — this is the pattern LID is specifically designed to remove. The cost of leaving them in place is that every future agent session has to figure out which LLD is live and which is historical before it can reason about the current design; that overhead compounds as more sessions touch the same segment, and eventually the current LLD gets harder to find than the outdated one. The git tag `three-phase-working` already holds the old narrative; removing the files will make the live arrow the obvious one to walk. Try deleting these four (run `git log` on each first if you want to confirm the replacement narrative is in place).

Use bullet lists within a finding only when enumerating genuinely parallel items — e.g., "the following four files…" — not as the finding's structural backbone.

## Remedies for decision capture and tenet conflicts

A finding's remedy is given here, when the user asks about it, not in the first report.

- **Under-captured decision** (dimension 18). Recommend the smallest capture that settles the question, usually a fuller Decisions row naming the rejected alternative and the accepted cost. Decision docs are a big deal, and a healthy project has few. Reserve recommending one for a choice that warrants a debate on the record: researched options weighed against criteria, at a resolution a future reader could re-run, where the memory of that deep work shapes the intent of the rest of the system. A debate having happened is not the test; a table row can come out of a long argument. When other design nodes restate or rely on the decision's reasoning (they repeat its numbers, or size and schedule themselves around it), say that a decision doc is an option if the team wants the full option space on record. Name it as an option, not a recommendation over the row; the doc itself is written in the core workflow, where its options can be argued with the user, not drafted by the coach from the landed docs. Reliance never makes a decision worth flagging; it only makes the doc worth naming once a decision is flagged.
- **Tenet or goal conflict** (dimension 19). Offer the remedies as the user's choice, without picking one: change the design, record the exception (a Decisions row naming the tenet or goal traded against, and why), or revise the tenet. Recording the exception also closes a decision-capture finding on the same choice, so mention that when both were reported; the user may still choose a different remedy for the tenet.

## Recommended-action targets

When a finding implies a configuration change, the recommended action is **`/update-lid`**. The skill state-dispatches: unconfigured projects get bootstrap, configured projects get reconciliation. One command for both cases — there's no separate setup command.

Two callouts:

- **Fresh-project users with a code change in mind** should typically be pointed at **`/linked-intent-dev`** (with a description of what they want to build) rather than `/update-lid` standalone. The workflow's Phase 1 calls the bootstrap branch as a sub-step and then walks the change forward.
- When a finding's follow-up is **structural** (orphans, reverse orphans, adjacent-level drift enumeration), point at **`/arrow-maintenance`** instead — the coach surfaces the pattern; arrow-maintenance enumerates it precisely.
