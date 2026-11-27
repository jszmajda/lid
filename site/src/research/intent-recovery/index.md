---
title: "What each approach leaves for the next reader"
date: 2026-11-21
status: pilot
summary: "A fresh reader rebuilt each project's rules from one approach's tests or documents. LID's files beat a bare agent's tests; a single spec file did as well or slightly better, on a project small enough for one file to hold every rule. The projects were too small to show stale files misleading anyone."
tested:
  lid: "1.4.6"
  agent: "Claude Code 2.1.323"
  model: "Claude Sonnet 5.5, medium effort"
records: "https://github.com/jszmajda/lid-research-records/tree/main/cost-eval/intent-recovery"
---

Every number here comes from pilot runs of LID 1.4.6, in Claude Code 2.1.323 on Claude Sonnet 5.5 at medium effort, in the same study as [our first report](https://linked-intent.dev/research/first-results/). Most come from ReleaseDesk, where each approach ran once and an agent can read the whole system at every change. So they show which way things point on small projects, and say little about large ones, where LID's documents are meant to matter most.

## The question

LID's documents are meant to outlast the conversation that produced them, telling a later reader, person or agent, what the system is meant to do, including rules the owner has since changed. Without them, the tests are usually the best record of intent there is. So we asked how much of the owner's intent each approach's files hand on to a reader who comes to them cold, and whether, once stale, they mislead the next change.

We compared a bare agent, which gets only the owner's request, with the same agent following LID's full workflow (LID Full), and on each project with a cheaper middle ground from the first report:

- **On BenchTime,** cheap discipline: the agent plans before it codes, writes tests, and keeps a notes file.
- **On ReleaseDesk,** the checklist: one paragraph in the agent's instruction file asking it to keep a `SPEC.md` of the system's requirements current, and to ask the owner about anything it leaves unsettled ([the whole instruction](https://github.com/jszmajda/lid/blob/main/docs/research/cost-eval/harness/arms/checklist-AGENTS.md)).

## The short answer

| | What we saw |
|---|---|
| Tests as a record of intent | On BenchTime, a reader of any approach's tests recovered 83% to 93% of the requirements each build met, against 28% from the brief alone. On ReleaseDesk, where the brief alone recovered about half, LID's tests gave 35 points more, the bare agent's 10 and the checklist's 6. |
| Documents as a record of intent | On ReleaseDesk, the checklist's spec file did as well as LID's documents or slightly better: 42 points above the brief against 36, in one run per approach, a lead about the size of the spread between readings of the same file. **ReleaseDesk is small:** the spec file and its README came to about 13,000 tokens, so one file could hold every rule. That is not evidence about larger projects, where a single file may not hold the system's rules. |
| Rules the owner had retired | Readers of LID's documents still stated 2 of the 7 as current in every reading (29%), against 5% for the checklist's spec and 19% for the bare agent's tests. With so few, each rule moves a share by 14 points. |
| Stale files | LID's runs left more stale files than the others', but as a share of files checked, its rate was below the bare agent's and above the checklist's. |
| Whether stale files misled the next change | None of 54 later requests, 18 per approach, followed a retired rule, though the simulated owner was there to correct them, and the project was too small to show that harm. |
| LID's documents without LID | In a repository LID built, a bare agent with LID's documents in reach met more requirements than on a stripped copy, at about three times the cost, and updated those documents in 10 of 12 changes, in one run per approach at each context window. |

## What the results add up to

**Written rules hand on more than a thin test suite, and on a small project they don't take LID's tree.**

**LID's tests carried almost as much intent as its documents, but they were about ten times the others' size, and we can't separate the two.**

**LID's files kept some retired intent** in this one run, though LID's cascade is meant to carry every change of mind into every document it touches.

**No one was misled, so the cost of stale intent is still unmeasured.**

## How we tested

**The reader and the judge.** A fresh session saw one source and had no one to ask: a build's tests, the same tests with names, comments and docstrings replaced by placeholders, the build's documents, or the brief every approach built from. It wrote down the system's current rules, one behaviour per rule, citing the files. A judge marked each rule against the study's private list of the owner's intent as agreeing with a requirement in force, contradicting one, stating a retired one, or matching nothing ([the reader's instructions](https://github.com/jszmajda/lid/blob/main/docs/research/cost-eval/harness/prompts/intent-from-tests.md), [the judge's](https://github.com/jszmajda/lid/blob/main/docs/research/cost-eval/harness/prompts/intent-match.md)). LID's requirement IDs were stripped from every input, so its cross-references couldn't give the answers away.

**What counts.** We scored only the requirements each build actually meets, so the measure is how well the files record what was built. A requirement counts as recovered when some rule agrees with it, in whole or in part. A strong model guesses a lot from a brief, so most results are points above a brief-only reader scored on the same requirements. Each input was read twice on BenchTime and three times on ReleaseDesk.

**The projects.**

- **BenchTime**, a small reservation service, read at change 10, three builds per approach.
- **ReleaseDesk**, a small release-approval tool grown from its brief through twenty changes, once per approach. Six of changes 11 to 20 changed direction: they retired or reversed an earlier rule, changed how far one reached, or overturned a choice the owner had left to the agent.

**Stale files, and the next change.** A blind reader checked every test and document that a change of direction touched, or should have, for anything contradicting current intent, with LID's vocabulary stripped so its files read like anyone's. Then, for each change of direction, an ordinary request in the same area that never mentions the rule ran three times, from snapshots two or three changes later, with the simulated owner on hand as in every run. Its right answer differs under the current rule and the retired one, the version the change of direction replaced.

**Checking the instrument.** Before any approach ran, we planted stale tests in a correct build, and readers caught 83% of them at change 20. That build had a single test file, so the planted tests outnumbered its own, an easier case than a real suite ([log](https://github.com/jszmajda/lid/blob/main/docs/research/cost-eval/log-archive/2026-11.md?plain=1#L148-L157)).

## What a reader recovered

### BenchTime

| Requirements each build met that the reader recovered | Bare agent | Cheap discipline | LID Full |
|---|---|---|---|
| From its tests | 83% | 89% | 93% |
| From its tests, names and comments replaced | 76% | 82% | 84% |
| From its documents | 80% | 87% | 94% |

The brief alone gave 28%. LID led every row, but its three builds overlapped cheap discipline's: from the tests, 89% to 97% against 87% to 92%. The bare agent's only document, its README, still gave 80%, so on a project this small most of what the owner asked for shows in almost anything the agent writes down. Replacing names and comments cost every approach's tests 7 to 9 points, LID's the most.

### ReleaseDesk

ReleaseDesk's brief states most of its rules, so a reader given only the brief recovered about half of what each build met (48% to 51% at change 20). Points above that reader, at change 10 and then change 20:

| | Bare agent | Checklist | LID Full |
|---|---|---|---|
| From its tests | +1, then +10 | +1, then +6 | +27, then +35 |
| From its tests, names and comments replaced | +3, then +9 | +4, then −2 | +24, then +33 |
| From its documents | not read | +34, then +42 | +31, then +36 |
| Size at change 20, tests and documents | 8,700 tokens and none | 9,700 and 13,300 tokens | 90,400 and 54,200 tokens |

The bare agent's only document was a README, and the trial reads documents only from builds with some other Markdown file ([the rule](https://github.com/jszmajda/lid/blob/main/docs/research/cost-eval/harness/growth_checkpoint.py#L284-L285)), so it has no figure here.

Readings of the same files differed by up to 14 points (the bare agent's tests), 7 for the checklist's spec and 5 for LID's documents, so the checklist's 6-point lead over LID's documents is about the size of that spread. At change 10, LID's documents had the higher raw recall, 87% against 85%; the checklist leads only once each build's own brief baseline is taken off. LID's 25-point lead over the bare agent's tests is well outside the spread.

The study predicted the bare agent's tests would lose ground as changes of direction piled up ([design](https://github.com/jszmajda/lid/blob/main/docs/research/cost-eval/design.md?plain=1#L213)). Through change 20 they gained, as did every source but the checklist's tests with names replaced.

## Retired rules and stale files

By change 20 the owner had retired seven rules. Readers of LID's documents stated two of them as current in all three readings, as did readers of LID's tests. Readers of the bare agent's tests stated one or two per reading, and readers of the checklist's spec one, in one reading of three. One of LID's two was stated from every approach's tests, so it may say more about that rule, or the judge, than about any approach. The other came from LID's files alone.

The audit of stale files points the same way:

| At change 20 | Bare agent | Checklist | LID Full |
|---|---|---|---|
| Files judged stale on the main line, of files checked | 1 of 12 | 0 of 13 | 4 of 64 |
| Reruns of a change of direction that left a stale file | 4 of 18 | 1 of 18 | 12 of 18 |
| Files judged stale in those reruns, of files checked | 6 of 34 | 1 of 41 | 18 of 186 |

LID keeps many more files, so it has more places to go stale; as a share of files checked, its rate was below the bare agent's and above the checklist's. In every rerun of every approach, the new rule worked and the retired one no longer did.

## Did stale files mislead the next change?

No. All 54 later requests followed the current rule, including three of the bare agent's runs and one of LID's that read a file the audit had judged stale. But the audit judged files as they stood at change 20, which can be several changes after a run's snapshot, so a file judged stale may not have been stale when the run read it.

The simulated owner, who holds the current rule, was also present, and LID's runs averaged about six turns with it each, against 1.3 for the bare agent's and 2.1 for the checklist's ([records](https://github.com/jszmajda/lid-research-records/blob/main/cost-eval/intent-recovery/releasedesk-m2e.md)). So for LID, following the current rule can't separate files that didn't mislead from an owner who corrected the agent.

That doesn't show stale intent is harmless. A second model reviewing the study suggested that agents read the code, which is current, so tests may not be an agent's main record of intent ([log](https://github.com/jszmajda/lid/blob/main/docs/research/cost-eval/log-archive/2026-11.md?plain=1#L82)). At change 20 the bare agent's whole service was five source files and one test file, small enough to read in full at every change ([log](https://github.com/jszmajda/lid/blob/main/docs/research/cost-eval/log-archive/2026-11.md?plain=1#L67-L76)), which is why the study stopped this test at change 20 instead of running the forty changes it had planned ([decisions](https://github.com/jszmajda/lid/blob/main/docs/research/cost-eval/decisions.md?plain=1#L106)).

## What LID's documents did for an agent that doesn't follow LID

Clowder, a game project LID's maintainer built with LID, gives a different angle: its repository holds the documents LID produced over the game's life. In a pilot, three approaches each made the same twelve changes at a 1M-token and a 200,000-token context window, one run per cell (each approach at each window): a bare agent on a stripped copy, with no documents, no agent instruction files, no requirement references and its tests thinned to about what a bare agent writes for itself; a bare agent on the full repository; and LID Full.

The bare agent on the full repository had no LID plugin but kept the repository's own instruction file, which tells agents to follow LID's workflow ([how the copies were made](https://github.com/jszmajda/lid/blob/main/docs/research/cost-eval/harness/clowder_variants.py#L12-L20)), so it is an agent without LID's tools, not one that had never heard of LID.

| | Bare agent, stripped copy | Bare agent, full repository | LID Full |
|---|---|---|---|
| Graded requirements met, 1M window | 79% | 88% | 97% |
| Graded requirements met, 200k window | 85% | 91% | 84% (27 of 32: one requirement couldn't be graded) |
| Agent cost against bare on the stripped copy, 1M and 200k | 1× | 2.9× and 3.4× | 4.3× and 3.9× |
| Changes that updated LID's documents, at each window | none: it had none | 10 of 12 | 10 of 12 |
| Largest context in any session, 1M and 200k | 98k and 76k tokens | 193k and 166k tokens | 255k and 166k tokens |

LID's 200k context figure covers 10 of its 12 changes: two were rerun after an instrument fix, and the reruns have no context record.

With LID's documents and the fuller tests in reach, the bare agent met two or three more requirements than on the stripped copy, and read more. With one run per cell, a single requirement moves a share by 3 points, so none of these differences separates the approaches or the windows.

So the study tested stale intent on a project each approach grew itself: in a repository LID built, a bare agent imitates LID's documents, and the comparison becomes one of workflows over shared documents ([design](https://github.com/jszmajda/lid/blob/main/docs/research/cost-eval/design.md?plain=1#L154), [decisions](https://github.com/jszmajda/lid/blob/main/docs/research/cost-eval/decisions.md?plain=1#L100)). The pilot also suggests LID's documents carry value of their own, apart from LID's plugin. It ran on the same versions as every other run here.

## What this doesn't show

**Larger projects.** The checklist's spec file did as well as LID's documents or slightly better on a system small enough for one file to hold every rule: the spec and its README came to about 13,000 tokens. On a larger system one file may not hold them all, and a reader may not read all of it. That's where LID's tree of linked documents is meant to help, and nothing here tested it.

**Rot.** The projects were too small for stale files to mislead anyone, so these runs say nothing about what stale intent costs over a project's life.

**A newcomer with more to go on.** Our reader saw one source. A real newcomer would read the code too, and could ask someone.

## How sure we are

**Few runs, and few retired rules.** ReleaseDesk had one run per approach, and most differences there are about the size of the spread between readings. It had seven retired rules by change 20, BenchTime two by change 10.

**Partial matches count.** Counting only requirements a single rule states in full gives much lower figures: 8% to 30% on BenchTime, and 3% to 14% on ReleaseDesk at change 20, where the brief-only reader did better, at 42% to 44%, probably because the brief and the requirements are both in the owner's words. Readers were told to write one behaviour per rule, which splits a long requirement into parts, so the stricter count likely undercounts every approach. Still, "recovered" often means "partly recovered".

**Size.** On ReleaseDesk, LID's tests were about ten times the others' size and its documents four times the checklist's. We didn't separate what an approach writes from how much.

**Grading versions.** The ReleaseDesk readings take the requirements each build met from an earlier version of the grading. The current version credits LID's build with one more, which they leave out.

**One model, and nothing fixed in advance.** Claude Sonnet 5.5 at medium effort made every change and did all the reading and judging, and we didn't fix these analyses before running them ([hypotheses](https://github.com/jszmajda/lid/blob/main/docs/research/cost-eval/hypotheses.md?plain=1#L3)).

## Open questions

- **Does a single spec file still hand on intent when a system outgrows it, and does stale intent mislead a change on a project too big to read in full?** Both need the realistically sized, long-lived project the first report calls for.
- **Why did one retired rule outlive its retirement in LID's files?** Reading which documents still state it would show whether LID's cascade missed a file.
- **How much of what LID's tests carry comes from their size?** A bare agent told to name its tests after its rules would be a cheap comparison.

## Where the details are

[The study's records](https://github.com/jszmajda/lid-research-records/tree/main/cost-eval/intent-recovery) hold the aggregate tables behind every number here: the reader's results, the stale-file and reliance counts, and the Clowder pilot's structural numbers. The study's notebook, with its design, decisions, log and code, is [`docs/research/cost-eval/`](https://github.com/jszmajda/lid/tree/main/docs/research/cost-eval) in the LID repository. The projects' private material, including the owner's requirements and every transcript, stays private, because later comparisons will reuse it.
