---
title: "What each approach leaves for the next reader"
date: 2026-11-27
status: pilot
summary: "A fresh reader rebuilt each project's rules from one approach's tests or documents. LID's files beat a bare agent's tests; a single spec file did as well or slightly better, on a project small enough for one file to hold every rule. The projects were too small to show stale files misleading anyone."
tested:
  lid: "1.4.6"
  agent: "Claude Code 2.1.323"
  model: "Claude Sonnet 5.5, medium effort"
records: "https://github.com/jszmajda/lid-research-records/tree/main/cost-eval/intent-recovery"
---

Every number here comes from pilot runs of LID 1.4.6, in Claude Code 2.1.323 on Claude Sonnet 5.5 at medium effort, in the same study as [our first report](https://linked-intent.dev/research/first-results/). The projects are small. Most of these results come from ReleaseDesk, where each approach ran once and an agent can read the whole system at every change. So they show which way things point on small projects, and say little about large ones, which is where LID's documents are meant to matter most.

## The question

LID's documents are meant to outlast the conversation that produced them. Someone who comes to a project later, a person or an agent, should be able to read them and know what the system is meant to do, including rules the owner has since changed. Without such documents, the tests are usually the best record of intent there is.

So we asked two things. How much of the owner's intent do each approach's files hand on to a reader who comes to them cold? And when those files go stale, do they mislead the next change?

We compared a bare agent, which gets the owner's request and nothing else, with the same agent following LID's full workflow (LID Full), and on each project with a cheaper middle ground from the first report:

- **On BenchTime,** cheap discipline: the agent plans before it codes, writes tests, and keeps a notes file.
- **On ReleaseDesk,** the checklist: one paragraph in the agent's instruction file asking it to keep a `SPEC.md` of the system's requirements current, and to ask the owner about anything it leaves unsettled ([the whole instruction](https://github.com/jszmajda/lid/blob/main/docs/research/cost-eval/harness/arms/checklist-AGENTS.md)).

## The short answer

| | What we saw |
|---|---|
| Tests as a record of intent | On BenchTime, a reader of any approach's tests recovered 83% to 93% of the requirements each build met, against 28% from the brief alone. On ReleaseDesk the brief alone recovered about half, so we give points above that brief-only reader: 10 for the bare agent's tests, 35 for LID's. |
| Documents as a record of intent | On ReleaseDesk, the checklist's spec file did as well as LID's documents or slightly better: 42 points above the brief against 36, in one run per approach. That lead is about the size of the spread between readings of the same file. **ReleaseDesk is small:** the spec file and its README came to about 13,000 tokens, so one file could hold every rule. That is not evidence about larger projects, where a single file may not hold the system's rules. |
| Rules the owner had retired | Readers of LID's documents still stated 2 of the 7 retired rules as current, in every reading (29%), against 5% for the checklist's spec and 19% for the bare agent's tests. With so few retired rules, each one moves a share by 14 points. |
| Stale files | LID's runs left more stale files than the others'. As a share of the files checked, LID's was below the bare agent's and above the checklist's. |
| Whether stale files misled the next change | None of 54 later requests, 18 per approach, followed a rule the owner had retired, though the simulated owner was there to correct them. The project was too small to show that harm, so this isn't evidence against it. |
| LID's documents without LID | In a repository LID built, a bare agent with LID's documents in reach met more requirements than on a stripped copy, at about three times the cost, and updated LID's documents in 10 of 12 changes. One run per approach at each context window. |

## What the results add up to

**Written rules hand on more than a thin test suite, and on a small project they don't take LID's tree.** On ReleaseDesk, the checklist's spec and LID's documents both handed on far more than the bare agent's tests or the checklist's. On a system this small, one well-kept file did as well as LID's documents, or slightly better.

**On ReleaseDesk, LID's tests carried far more intent than the others', though its suite was also about ten times their size, and we can't separate the two.** A reader of LID's tests recovered almost as much as a reader of its documents, 35 points above the brief, against 10 for the bare agent's tests and 6 for the checklist's. On BenchTime every approach's tests carried most of the intent.

**LID's files kept some retired intent.** LID's cascade is meant to carry every change of mind into every document it touches, yet in this one run readers found a retired rule in LID's documents and tests and in no other approach's files.

**No one was misled, so the cost of stale intent is still unmeasured.** Every later request followed the current rule, even in runs that read a stale file. One likely reason is that agents read the code, which is always current, and on a project this small they can read all of it. Another is that the simulated owner, who holds the current rule, was there to correct them, and LID's runs talked with it most.

## How we tested

**The reader and the judge.** A fresh session saw one source and nothing else, not even someone to ask: a build's tests as written, the same tests with test names, comments and docstrings replaced by placeholders, the build's documents, or the brief every approach built from. It wrote down the system's current rules, one behaviour per rule, citing the files. A judge then mapped each rule against the study's private list of the owner's intent: it agrees with a requirement in force, contradicts one, states a retired one, or matches nothing ([the reader's instructions](https://github.com/jszmajda/lid/blob/main/docs/research/cost-eval/harness/prompts/intent-from-tests.md), [the judge's](https://github.com/jszmajda/lid/blob/main/docs/research/cost-eval/harness/prompts/intent-match.md)). Reader and judge were both Claude Sonnet 5.5 at medium effort. LID's requirement IDs were stripped from every input, so its cross-references couldn't give the answers away.

**What counts.** We counted only the requirements each build actually meets, so the measure is how well the files record what was built. A requirement counts as recovered when some rule agrees with it, in whole or in part. A strong model guesses a lot from a brief, so most results are given as points above a reader who saw only the brief, scored on the same requirements. Each input was read twice on BenchTime and three times on ReleaseDesk.

**The projects.**

- **BenchTime**, a small reservation service, read at change 10, with three builds per approach.
- **ReleaseDesk**, a small release-approval tool grown from its brief through twenty changes, once per approach. Six of changes 11 to 20 changed direction: they retired or reversed a rule the owner had set earlier, changed how far one reached, or overturned a choice the owner had left to the agent.

**Stale files, and the next change.** A blind reader checked every test and document that a change of direction touched, or should have touched, for anything contradicting current intent. LID's own vocabulary was stripped first, so LID's files read like anyone's. Then, for each change of direction, an ordinary request in the same area that never mentions the rule ran three times, from snapshots two or three changes later, with the simulated owner on hand as in every other run. Its right answer differs under the current rule and the retired one, the version the change of direction replaced.

**Checking the instrument.** Before any approach ran, we planted stale tests in a correct build, and readers caught 83% of them at change 20. That build wrote a single test file, so the planted tests outnumbered its own, an easier case than a real suite ([log](https://github.com/jszmajda/lid/blob/main/docs/research/cost-eval/log-archive/2026-11.md?plain=1#L148-L157)).

## What a reader recovered

### BenchTime

| Requirements each build met that the reader recovered | Bare agent | Cheap discipline | LID Full |
|---|---|---|---|
| From its tests | 83% | 89% | 93% |
| From its tests, names and comments replaced | 76% | 82% | 84% |
| From its documents | 80% | 87% | 94% |

A reader given only the brief recovered 28%. LID's figure was highest in every row, but its three builds overlapped cheap discipline's: from the tests, 89% to 97% against 87% to 92%. The bare agent's only document was its README, and a reader still recovered 80% from it, so on a project this small most of what the owner asked for shows in almost anything the agent writes down. Replacing names and comments cost every approach's tests 7 to 9 points, LID's the most.

### ReleaseDesk

Points above a reader given only the brief, at change 10 and then change 20:

| | Bare agent | Checklist | LID Full |
|---|---|---|---|
| From its tests | +1, then +10 | +1, then +6 | +27, then +35 |
| From its tests, names and comments replaced | +3, then +9 | +4, then −2 | +24, then +33 |
| From its documents | not read | +34, then +42 | +31, then +36 |
| Size at change 20, tests and documents | 8,700 tokens and none | 9,700 and 13,300 tokens | 90,400 and 54,200 tokens |

ReleaseDesk's brief states most of its rules, so the brief alone recovered about half of what each build met (48% to 51% at change 20). The bare agent's only document was a README, and the trial reads documents only from builds with some other Markdown file ([the rule](https://github.com/jszmajda/lid/blob/main/docs/research/cost-eval/harness/growth_checkpoint.py#L284-L285)), so there is no ReleaseDesk figure for it.

Each approach ran once, and readings of the same files differed by up to 14 points (the bare agent's tests), 7 for the checklist's spec and 5 for LID's documents. So the checklist's 6-point lead over LID's documents is about the size of that spread. At change 10, LID's documents had the higher raw recall, 87% against 85%; the checklist leads only once each build's own brief baseline is taken off. LID's 25-point lead over the bare agent's tests is well outside the spread.

The study predicted that the bare agent's tests would lose ground as changes of direction piled up ([design](https://github.com/jszmajda/lid/blob/main/docs/research/cost-eval/design.md?plain=1#L213)). Through change 20 they gained, and so did every other source except the checklist's tests with names replaced.

## Retired rules and stale files

By change 20 the owner had retired seven rules. Readers of LID's documents stated two of them as current in all three readings, and so did readers of LID's tests. Readers of the bare agent's tests stated one or two per reading, and readers of the checklist's spec one, in one reading of three. One of LID's two was stated from every approach's tests, so it may say more about that rule, or the judge, than about any approach. The other came from LID's files alone.

The audit of stale files points the same way:

| At change 20 | Bare agent | Checklist | LID Full |
|---|---|---|---|
| Files judged stale on the main line, of files checked | 1 of 12 | 0 of 13 | 4 of 64 |
| Reruns of a change of direction that left a stale file | 4 of 18 | 1 of 18 | 12 of 18 |
| Files judged stale in those reruns, of files checked | 6 of 34 | 1 of 41 | 18 of 186 |

LID keeps many more files, so it has more places to go stale. As a share of the files checked, its rate was below the bare agent's and above the checklist's. In every rerun of every approach, the new rule worked and the retired one no longer did.

## Did stale files mislead the next change?

No. All 54 later requests, 18 per approach, followed the current rule, including three of the bare agent's runs and one of LID's that read a file the audit had judged stale. The audit judged files as they stood at change 20, which can be several changes after a run's snapshot, so a file judged stale wasn't necessarily stale when that run read it.

The simulated owner was present in these runs, and it holds the current rule. LID's runs averaged about six turns with it each, against 1.3 for the bare agent's and 2.1 for the checklist's ([records](https://github.com/jszmajda/lid-research-records/blob/main/cost-eval/intent-recovery/releasedesk-m2e.md)). So for LID, following the current rule can't separate files that didn't mislead from an owner who corrected the agent.

That doesn't show stale intent is harmless. A second model reviewing the study suggested that agents read the code, which is current, so tests may not be an agent's main record of intent ([log](https://github.com/jszmajda/lid/blob/main/docs/research/cost-eval/log-archive/2026-11.md?plain=1#L82)). At change 20 the bare agent's whole service was five source files and one test file, small enough to read in full at every change ([log](https://github.com/jszmajda/lid/blob/main/docs/research/cost-eval/log-archive/2026-11.md?plain=1#L67-L76)). That's why the study stopped this test at change 20 instead of running the forty changes it had planned ([decisions](https://github.com/jszmajda/lid/blob/main/docs/research/cost-eval/decisions.md?plain=1#L106)).

## What LID's documents did for an agent that doesn't follow LID

Clowder, a game project LID's maintainer built with LID, gives a different angle, because its repository holds the documents LID produced over the game's life. In a pilot, three approaches each made the same twelve changes at a 1M-token and a 200,000-token context window, one run per cell (each approach at each window): a bare agent on a stripped copy, with no documents, no agent instruction files, no requirement references and its tests thinned to about what a bare agent writes for itself; a bare agent on the full repository; and LID Full.

The bare agent on the full repository had no LID plugin, but it kept the repository's own instruction file, which tells agents to follow LID's workflow ([how the copies were made](https://github.com/jszmajda/lid/blob/main/docs/research/cost-eval/harness/clowder_variants.py#L12-L20)). So this is an agent without LID's tools, not one that had never heard of LID.

| | Bare agent, stripped copy | Bare agent, full repository | LID Full |
|---|---|---|---|
| Graded requirements met, 1M window | 79% | 88% | 97% |
| Graded requirements met, 200k window | 85% | 91% | 84% (27 of 32: one requirement couldn't be graded) |
| Agent cost against bare on the stripped copy, 1M and 200k | 1× | 2.9× and 3.4× | 4.3× and 3.9× |
| Changes that updated LID's documents, at each window | none: it had none | 10 of 12 | 10 of 12 |
| Largest context in any session, 1M and 200k | 98k and 76k tokens | 193k and 166k tokens | 255k and 166k tokens |

LID's 200k context figure covers 10 of its 12 changes: two were rerun after an instrument fix, and the reruns have no context record.

With LID's documents and the fuller test suite in reach, the bare agent met two or three more requirements than on the stripped copy, read more, and cost about three times as much. It edited LID's documents in as many changes as the LID agent did. With one run per cell, a single requirement moves a share by 3 points, so none of these differences separates the approaches or the windows.

This is why the study tested stale intent on a project each approach grew itself: in a repository LID built, a bare agent imitates LID's documents, and the comparison becomes one of workflows over shared documents ([design](https://github.com/jszmajda/lid/blob/main/docs/research/cost-eval/design.md?plain=1#L154), [decisions](https://github.com/jszmajda/lid/blob/main/docs/research/cost-eval/decisions.md?plain=1#L100)). It also suggests LID's documents carry value of their own, apart from LID's plugin. The Clowder pilot ran on the same versions as every other run here.

## What this doesn't show

**Larger projects.** The checklist's spec file did as well as LID's documents or slightly better on a system small enough that the spec and its README came to about 13,000 tokens. On a larger system one file may not hold all the rules, and a reader may not read all of it. That's where LID's tree of linked documents is meant to help, and nothing here tested it.

**Rot.** The projects were too small for stale files to mislead anyone, so these runs say nothing about what stale intent costs over a project's life.

**A newcomer with more to go on.** Our reader saw one source. A real newcomer would read the code as well, and could ask someone.

## How sure we are

**Few runs, and few retired rules.** ReleaseDesk had one run per approach, and most differences between approaches there are about the size of the spread between readings of the same files. It had seven retired rules by change 20, and BenchTime two by change 10.

**Partial matches count.** Counting only requirements that a single rule states in full gives much lower figures: 8% to 30% on BenchTime, and 3% to 14% on ReleaseDesk at change 20, where the brief-only reader did better, at 42% to 44%, probably because the brief and the requirements are both in the owner's words. Readers were told to write one behaviour per rule, which splits a long requirement into parts, so the stricter count likely undercounts every approach. Still, "recovered" often means "partly recovered".

**Size.** On ReleaseDesk, LID's test suite was about ten times the size of the others', and its documents four times the checklist's. We didn't separate what an approach writes from how much it writes.

**Grading versions.** The ReleaseDesk readings take the list of requirements each build met from an earlier version of the grading. The current version credits LID's build with one more, which those readings leave out.

**One model, and nothing fixed in advance.** Claude Sonnet 5.5 made every change and did all the reading and judging described here, and we didn't fix these analyses before running them ([hypotheses](https://github.com/jszmajda/lid/blob/main/docs/research/cost-eval/hypotheses.md?plain=1#L3)).

## Open questions

- **Does a single spec file still hand on intent when a system outgrows it, and does stale intent mislead a change on a project too big to read in full?** Both need the realistically sized, long-lived project the first report calls for.
- **Why did one retired rule outlive its retirement in LID's files?** Reading which documents still state it would show whether LID's cascade missed a file.
- **How much of what LID's tests carry comes from their size?** A bare agent told to name its tests after its rules would be a cheap comparison.

## Where the details are

The aggregate tables behind every number here are in [the study's records](https://github.com/jszmajda/lid-research-records/tree/main/cost-eval/intent-recovery): the reader's results on both projects, ReleaseDesk's full results at changes 10 and 20, the stale-file and reliance counts, and the Clowder pilot's structural numbers. The study's notebook, with its design, decisions, log and code, is [`docs/research/cost-eval/`](https://github.com/jszmajda/lid/tree/main/docs/research/cost-eval) in the LID repository. The projects' private material, including the owner's requirements and every transcript, stays private, because later comparisons will reuse it.
