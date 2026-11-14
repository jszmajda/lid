# Decisions

Every decision about this research that still stands, newest last, with its date and who made it. The reasons and context are in [log.md](log.md) and [log-archive/](log-archive/). What each decision means for the design is in [design.md](design.md).

When a decision is replaced, remove its line and add the new one, so this list only ever shows what currently stands. The log keeps the history.

- 2026-11-11, maintainer: Keep the comparison with other SDD systems. People ask about it more than anything else.
- 2026-11-11, maintainer: Also compare LID with a bare agent and with cheap discipline.
- 2026-11-11, maintainer: Staging is the main session's call.
- 2026-11-11, maintainer: Invite the maintainers of the compared systems to run the eval on their own systems, and document how.
- 2026-11-11, maintainer: This is a research spike, not a gate.
- 2026-11-11, maintainer: LID's bidirectional-differential skill is the idea behind measuring intent fidelity.
- 2026-11-11, maintainer: The eval includes redirects, where the user changes their mind or clarifies an unclear intent partway through a change.
- 2026-11-11, maintainer: Human attention is a headline measure, and so is its kind. Saying "ok" differs from having to think hard.
- 2026-11-11, maintainer: SlopCodeBench is worth trying alongside a bespoke eval. SLUMP and EvoClaw are optional.
- 2026-11-11, maintainer: Measure top-tier and mid-tier models.
- 2026-11-11, maintainer: Plan mode is a reasonable cheap-discipline baseline.
- 2026-11-11, maintainer: For Spec Kit, use the configuration closest to LID, and document it carefully.
- 2026-11-11, maintainer: Leave Kiro out. A plan-plus-EARS arm (cc-sdd) stands in for it.
- 2026-11-11, maintainer: Mining old transcripts (stage 0) is dropped.
- 2026-11-11, maintainer: Work in public, with a draft pull request that gets regular pushes, and keep the notebook.
- 2026-11-12, maintainer: Graders are models. They are calibrated before they're trusted, and the maintainer spot-checks their verdicts, most heavily at fidelity level 2.
- 2026-11-12 (later), maintainer: BenchTime is the pilot seed and ReleaseDesk the second, as recommended in the main session.
- 2026-11-12 (later), maintainer: Every point in the plan review is adopted.
- 2026-11-12 (later), maintainer: The owner's latent intent can arrive late. Each oracle item has a disclosure point: stated, askable, recognised on sight, emerging at change k, or realised on a symptom.
- 2026-11-12 (later), maintainer: Cost is a real constraint. Graders, the simulator, and the classifier run through `claude -p` on the maintainer's subscription where possible, with Haiku 5.5 tried first for grading. OpenRouter money is limited to authorship, a cross-family sample, and the later stage with other executor families.
- 2026-11-12 (evening), maintainer: The main session should use its own judgment on Sol's drafts rather than pass them through unchanged.
- 2026-11-12 (evening), main session: Edits to seed drafts may fix consistency, gradability, realism, and scope. They may not change the mix of change types or move items to favour a predicted direction. Every edit is logged with its reason.
- 2026-11-12 (evening), main session: The hidden oracle and change script stay out of the public repository until the runs that use them finish. Their hashes will be published before any counted run.
- 2026-11-12 (night), maintainer: Each arm designs its own interface, and a step before grading extracts it for the grader. The brief is in the owner's words and fixes only the stack, one start command, one data location, and reading the current time from the system clock.
- 2026-11-13, maintainer: Grading needs a defined protocol: what a verdict is, how it is reached and checked, and how verdicts are scored and reported. The main session wrote it into design.md.
- 2026-11-13 (later), maintainer: BenchTime's materials are accepted, including the three edits marked for review.
- 2026-11-13 (later), maintainer: The log is compacted from time to time by a subagent, which can be Haiku.
- 2026-11-13 (later), main session: Compact when log.md passes about 2,000 words. Keep the newest entries up to about 1,000 words, move older ones word for word to log-archive/, and keep standing decisions in this ledger.
- 2026-11-13 (later), main session: The "Earlier, in brief" summary stays under about 300 words.
- 2026-11-13, main session: the grading container runs in UTC. The brief makes the lab's time zone setup data, so a service that relies on the server's time zone is the arm's choice and is graded like any other.
- 2026-11-13 (evening), main session: grading execution runs in batches of a few probes per session, and judgment reads each batch's log in one session.
- 2026-11-13 (night), maintainer: every executor session runs in a Linux container from the pinned executor image, with each arm's configuration in its own volume and the maintainer's subscription token.
- 2026-11-13 (night), maintainer: no force-pushes to the pull request branch, because they could disturb a collaborator's checkout. Mistakes in pushed commits get a forward fix.
- 2026-11-13 (night), maintainer: a Claude Fable review stands in for the maintainer's detailed review of probes; the main session applies its fixes and Fable checks them again.
- 2026-11-13 (night), maintainer: grading replays the previous checkpoint's calls without a model; a model executes a probe only when it is new or its replay fails, and the judge sees only probes whose responses changed.
- 2026-11-13 (night), maintainer: the harness stays outside LID's arrow during the spike, beside the notebook in harness/; it becomes a segment if its results come to back a claim LID ships.
- 2026-11-13 (night), main session: the harness has three parts (trajectories, grading, reports) handing records to each other, keeps raw records first, gives every arm one treatment, is runnable by others, and has tests where a quiet bug would bias results.
