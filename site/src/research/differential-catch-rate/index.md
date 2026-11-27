---
title: "Does the bidirectional differential catch planted gaps?"
date: 2026-11-27
status: counted
summary: "On one 24-requirement segment of one project, fresh Claude Sonnet auditors caught 23 of 24 planted gaps, past a pre-registered bar of 0.70. The exam was too easy to tell auditors apart, the one miss sat in code no annotation reached, and the skill LID ships differs from what we tested."
tested:
  lid: "1.3.0 (lid-experimental 0.2.0), run as a standalone harness, not the shipped skill"
  agent: "Claude Code's Workflow tool, version not recorded; OpenAI Responses API for the GPT-5.6 arms"
  model: "Claude Sonnet (headline arm), also Claude Opus and Claude Haiku, versions and effort not recorded; gpt-5.6-terra and gpt-5.6-luna, effort not set"
records: "https://github.com/jszmajda/lid-research-records/tree/main/b10-differential-catch-rate"
---

Every number here comes from one experiment, B10, run on 2 and 3 August 2026 on one segment of one project: the 24 requirements behind the Google Sheets view of portfolio-tracker, a personal-finance tool that LID's maintainer built with LID. The headline auditor was Claude Sonnet, with smaller runs on Claude Opus, Claude Haiku and two GPT-5.6 models; the exact Claude versions weren't recorded. The audit ran as a harness written for the experiment, not as the skill LID ships, and the two differ in ways that matter, set out below. The hypothesis, pass mark and readouts were written down before any audit ran, and we label what came afterwards. Only the documents' own dates show when that was, since the design was first committed together with the results.

## The question

LID's case for lighter review is that once intent is written down as requirements and linked to the code, a reviewer can stop reading every line and check instead that what landed traces back to what was meant. That holds only if the checking catches what a careful reader would.

One such instrument is the bidirectional differential, which audits one requirement from both ends. In the A direction, a fresh session gets only the requirement's text and writes code for it. In the B direction, a fresh session gets only the code, with documents and requirement IDs stripped out, and writes down the requirement it enforces. A classifier compares each with the real thing and lists the gaps.

Earlier experiments ran this audit on Threadkeeper, the maintainer's private app, and found real gaps: [B9](https://github.com/jszmajda/lid/blob/main/docs/research/experiments/b9-bidirectional-differential-filter/RESULTS.md), for one, judged five of six requirements out of step with their code, and [B1](https://github.com/jszmajda/lid/blob/main/docs/research/experiments/b1-differential-thr-det-021/RESULTS.md) and [B2](https://github.com/jszmajda/lid/blob/main/docs/research/experiments/b2-differential-llds-ears-primary/RESULTS.md) found others. None had an answer key, so they showed that the method finds things, not how much it misses. B10 planted gaps with the answers written down in advance, eight of each of three kinds:

- **Unstated intent.** The code and its tests gain a behaviour no requirement states. One seed made the code trim and upper-case a stock symbol before looking it up.
- **Phantom requirements.** A requirement gains a claim nothing in the code enforces.
- **Hollow tests.** The code quietly stops meeting a requirement, and its tests are changed to pin the narrower behaviour, so every check stays green. Sonnet had done this to its own code in earlier LID experiments, so this was the case B10 cared most about. We predicted it would be the hardest to catch.

## The short answer

| | What we saw |
|---|---|
| Planted gaps caught by fresh Sonnet auditors | 23 of 24, against a pre-registered bar of 0.70. The 95% interval runs from about 0.80 to 0.99. |
| By kind | Hollow tests 8 of 8, phantom requirements 8 of 8, unstated intent 7 of 8. Hollow tests were the easiest, not the hardest. |
| The one miss | In code no requirement annotation reached, so no auditor was shown it. |
| More independent auditors | Bought nothing we could measure. On 8 of the seeds, self-audit, Opus, GPT-5.6 Terra and GPT-5.6 Luna each caught 7. The exam was too easy to separate them. |
| A cheaper model | Haiku caught 5 of 8. |
| The verdict per requirement | Told planted gaps from untouched code not at all: all 48 of Sonnet's units were labelled as drifting. |
| False alarms on untouched requirements | 0% to 7.5% of findings per auditor, after a judge model ruled on each. Sonnet still raised about five findings per untouched requirement. |
| Cost | About 343,000 Claude tokens per requirement audited. |
| The skill LID ships | Differs from what we tested in what it reads, what it reports, and what it says it costs. |

## How we tested

**The fixture.** portfolio-tracker is a Rust workspace that keeps an investment ledger and publishes read-only view tabs to a Google Sheets workbook. We used the segment that writes those tabs: 24 requirements, all implemented, at commit `ba94c01`, published as the tag [`lid-b10-baseline`](https://github.com/jszmajda/portfolio-tracker/tree/lid-b10-baseline). Before the runs its full check suite passed, including formal-verification stages and a check that every one of the project's 365 requirements is cited by a test.

**The seeds.** A Sonnet session planted each gap in its own clone, one per requirement, using kinds of gap seen in real work: wire formats, exact constants, error handling, boundary behaviour and tie-breaking. Every seeded clone had to pass the project's checks with every annotation still resolving, so that only the audit could find it. The answer key came before any audit. The segment has exactly 24 requirements, so the controls are the same 24 on untouched code.

**The audit.** Each unit was one requirement: three A-direction runs, three B-direction runs and one classifier call. The B direction read the files that cite the requirement, test files included. The classifier read the real requirement and code and the six outputs, and listed findings strongest first. The [prompts](https://github.com/jszmajda/lid/blob/main/docs/research/experiments/b10-differential-catch-rate/harness/audit-prompts.md) were frozen after a two-seed pilot.

**The arms.** Fresh Sonnet sessions, started by Claude Code's Workflow tool, ran all 48 units. A subset of 8 seeds and 8 controls also ran with the seeding session auditing its own work, with fresh Opus, and with GPT-5.6 Terra, chosen as Sonnet's peer from another provider. Haiku and GPT-5.6 Luna ran the subset as an exploratory arm.

**Scoring.** A seed counted as caught when any finding in its unit's one list matched the key's direction and substance. A Claude Fable judge, not told which units were seeded, ruled on each finding about an untouched requirement: a real gap, a missing cross-reference (behaviour a sibling requirement states), or a false alarm. GPT-5.6 Sol re-judged a sample. If the two agreed on less than 85% of it, Jess Szmajda, LID's maintainer, would rule on every disagreement before any number was published.

## What we found

### Planted gaps caught

| Auditor | Unstated intent | Phantom requirement | Hollow test | Total |
|---|---|---|---|---|
| Sonnet, fresh, all seeds | 7 of 8 | 8 of 8 | 8 of 8 | 23 of 24 |
| Sonnet, auditing its own seeds | 2 of 3 | 3 of 3 | 2 of 2 | 7 of 8 |
| Sonnet, fresh, the same 8 | 2 of 3 | 3 of 3 | 2 of 2 | 7 of 8 |
| Opus, fresh | 2 of 3 | 3 of 3 | 2 of 2 | 7 of 8 |
| GPT-5.6 Terra, fresh | 2 of 3 | 3 of 3 | 2 of 2 | 7 of 8 |
| GPT-5.6 Luna, fresh (exploratory) | 2 of 3 | 3 of 3 | 2 of 2 | 7 of 8 |
| Haiku, fresh (exploratory) | 1 of 3 | 3 of 3 | 1 of 2 | 5 of 8 |

An auditor that caught a seed usually led with it: in 17 of Sonnet's 23 catches, and 42 of the 49 by fresh auditors, the matching finding came first.

### The one miss

Every auditor missed the same seed, which kept the last good quote date when a new one couldn't be read. It sat in a file that mentioned no requirement ID, and the audit picks the files it shows by following those IDs, so no auditor saw it. Another seed in the same file was shown, because its requirement's annotations already reached there, and every auditor but Haiku caught it.

So the audit sees only what the annotations reach. The agent writing the code usually places them too, and nothing here tests whether that tempts it to leave some out. Leaving the unseen seed out, a view we chose after the results, every auditor caught everything it could see, except Haiku at 5 of 7.

### Hollow tests were easiest, by construction

A hollow-test seed leaves the requirement's text alone, so the A direction rebuilds the original intent while the B direction rebuilds the narrowed code, and the two collide, often on an exact value. One seed made a price conversion round every tie up instead of to even, and the findings named the case: $1.005 became 101 cents, where the requirement's rule gives 100. That is also the result's limit: these were hollow tests the audit can see by design. An agent that narrows code in real use may narrow the requirement too, or the requirement may have been ambiguous from the start.

### Independence, and a cheaper model

Self-audit, fresh Sonnet, Opus, Terra and Luna all caught the same 7 of 8. That doesn't show independence is worthless: every seed was either visible and caught by all of them or hidden from all of them, so a more independent auditor had nothing left to find. Whether related models share blind spots is neither confirmed nor ruled out.

Haiku is where a cheaper model gave way. It also missed one hollow test, and on another seed it found the planted mechanism but called it harmless, which the human pass ruled a miss. Luna caught 7 of 8, for $0.43 across its 16 units.

### The verdict per requirement carried no signal

The audit labels each requirement with a code saying whether, and in which direction, requirement and code have drifted apart. All 48 of Sonnet's units got a drifting label, the 24 untouched ones included, and so did all 16 of Opus's. That's partly real, because the untouched requirements had genuine gaps, but the label couldn't tell planted gaps from the background. It wasn't stable either: when the Sonnet arm accidentally ran twice, 3 of the 24 untouched units changed label. What separated seeds from controls was the list of findings, matched against the key.

### Findings on untouched requirements

| Auditor | Findings | Real gaps | Missing cross-references | False alarms |
|---|---|---|---|---|
| Sonnet, 24 requirements | 120 | 54 | 57 | 9 (7.5%) |
| Opus, 8 | 77 | 44 | 31 | 2 (2.6%) |
| GPT-5.6 Terra, 8 | 42 | 22 | 20 | 0 |
| GPT-5.6 Luna, 8 | 43 | 20 | 22 | 1 (2.3%) |
| Haiku, 8 | 18 | 6 | 11 | 1 (5.6%) |

Few findings were false alarms, but around half described behaviour a sibling requirement states. The real gaps are discoveries in portfolio-tracker; the most serious is that its production Sheets code never clears leftover rows from a view tab, as a requirement says it must, and only its test doubles do.

### The judges disagreed enough to call in the human

Fable and Sol agreed on 112 of 134 sampled verdicts, 83.6%, below the trigger. Sol finished 10 of its 15 planned groups before the OpenAI credits ran out. Jess ruled on all 22 disagreements on 3 August, siding with Fable 12 times and Sol 10. The principles behind her rulings weren't fixed in advance: a sibling may state an exception to a universal requirement, which makes a missing cross-reference, not drift; silence on a question nobody has settled isn't drift; and a finding that calls a planted gap harmless doesn't catch it. That last ruling moved Haiku from 6 of 8 to 5 of 8, the only recall figure that changed.

### Stability and cost

Sonnet's three A-direction runs agreed closely on 30 of its 48 units and poorly on 2; its B-direction runs agreed closely on 45. Haiku's A-direction runs agreed poorly on 8 of its 16.

Claude audit calls used about 46.1 million tokens, 16.6 million of them an accidental second run of the Sonnet arm, and judging about 5.5 million more. Each Sonnet unit took about 343,000. The Claude side was recorded as tokens per arm, not dollars. The OpenAI side was priced per call: Terra cost $3.94 for 16 units, Luna $0.43, and Sol's cross-checks about $2.33.

## What the shipped skill does differently

LID ships this audit as the experimental [bidirectional-differential skill](https://github.com/jszmajda/lid/tree/main/plugins/lid-experimental/skills/bidirectional-differential), which isn't what B10 measured:

- **It leaves tests out by default.** B10's B direction read test files and was asked for behaviour pinned only by tests. The skill omits test files unless the user opts in ([audit-protocol.md](https://github.com/jszmajda/lid/blob/main/plugins/lid-experimental/skills/bidirectional-differential/references/audit-protocol.md)). No B10 arm ran without them, so we don't know how much the result depended on them.
- **It leads with the label B10 found carries no signal.** Each audit record is headed by the per-requirement code, and the summary leads with counts of codes. With no answer key and no judge, a user sees every finding, about five per untouched requirement in B10, with nothing sorting real gaps from missing cross-references and false alarms.
- **It describes a different cost.** The design gives an audit as about six short calls costing "a few cents" at Sonnet rates ([design](https://github.com/jszmajda/lid/blob/main/docs/intent/lid-experimental/bidirectional-differential/bidirectional-differential-design.md)). B10's took seven calls and about 343,000 tokens, and Terra, Sonnet's peer, cost about 25 cents a unit. We didn't price the Claude side, so we can't check the design's figure directly.

The prompts differ too: B10's A direction listed every assumption it invented, where the skill's asks for code alone. That leaves questions for LID, none of them settled:

- Should the skill's B direction read tests, as B10's did?
- Should its report lead with ranked findings rather than the label?
- Could a judging step, or a check for sibling requirements, cut the cross-reference noise before a person reads it?
- Since the audit sees only annotated code, should LID measure how much of a change its annotations reach?
- Should the design state a measured cost?

## What this doesn't show

**That audits can replace reading code.** B10 had no comparison: no person reading the code, no ordinary reviewer prompt, no one-direction audit. It set a bar for the audit, not a rule for choosing between auditing and reading. What it supports is narrower: on annotated code, the audit can take some of the checking that requirements and code agree off a reviewer.

**Anything a requirement doesn't say.** Maintainability, security, architecture, and choices that are each reasonable but add up badly are mostly in no requirement or test, and no catch rate here bears on them.

**Real gaps, found unprompted.** The seeds were synthetic, written by a Sonnet session that knew the audit existed, so they may sit close to what it expects. Scoring it against gaps recovered from real bug fixes would settle that. Every auditor also knew it was auditing; drift in real use arrives unannounced.

**Other codebases.** Everything was measured on one segment of the maintainer's own code, built with LID from its first commit.

## How sure we are

**The exam was too easy.** The audit cleared its bar by a wide margin and every auditor but one tied, which is what a saturated exam looks like. B10 is best read as a calibration pilot: the harness works, and the next exam needs to be harder. 23 of 24 has a wide interval, and 8 of 8 in a kind is consistent with a true rate as low as about 0.68.

**What was fixed in advance.** The hypothesis, the 0.70 bar, the readouts and the 85% trigger are in the [design](https://github.com/jszmajda/lid/blob/main/docs/research/experiments/b10-differential-catch-rate/DESIGN.md), with an amendment dated before seeding and adjustments dated after the pilot but before the main runs. The view without the unseen seed, and the human pass's principles, came later.

**Blinding was partial.** The judges of untouched-requirement findings could compare seeded code with the baseline, and at least two verdicts mention "the planted change". The file paths given to the B direction and the classifier named their tree, the baseline or the seed's ID, so an auditor could tell untouched code from planted, though not what was planted. Haiku's sessions ran with the folder holding the sealed key as their working directory; their prompts said to read nothing else, and no output shows one opening it. We can't measure what any of this changed.

**Who judged.** A Claude model judged mostly Claude auditors, hence Sol's cross-check, and there was one human judge. The GPT arms got file contents in their prompts, where Claude arms read files.

**What survives.** Sonnet's untouched units from both runs, the Opus and Haiku arms, and the pilot's judging files were kept. Sonnet's seeded units, the Terra and Luna outputs and the main judging outputs weren't, so 23 of 24 rests on the scoring files' tallies, not on outputs anyone can re-read.

**The critique.** After the results, eight model reviewers, six Claude-family and two on GPT-5.6 Sol, attacked the design and its reading ([CRITIQUE.md](https://github.com/jszmajda/lid/blob/main/docs/research/experiments/b10-differential-catch-rate/CRITIQUE.md)). They read a prose summary, not the records, and only the Sol reviewers raised the missing comparison. That review shapes this report, but it was models reviewing a model-run study.

## Where the details are

The study's notebook is [`docs/research/experiments/b10-differential-catch-rate/`](https://github.com/jszmajda/lid/tree/main/docs/research/experiments/b10-differential-catch-rate) in the LID repository: the design, the [pilot](https://github.com/jszmajda/lid/blob/main/docs/research/experiments/b10-differential-catch-rate/PILOT.md), the [results](https://github.com/jszmajda/lid/blob/main/docs/research/experiments/b10-differential-catch-rate/RESULTS.md) as written at the time, the critique, the [final scoring](https://github.com/jszmajda/lid/blob/main/docs/research/experiments/b10-differential-catch-rate/scoring-final.json), the [answer key](https://github.com/jszmajda/lid/tree/main/docs/research/experiments/b10-differential-catch-rate/answer-key) with each seed's patch and the [human rulings](https://github.com/jszmajda/lid/blob/main/docs/research/experiments/b10-differential-catch-rate/answer-key/human-adjudication.md), and the [harness](https://github.com/jszmajda/lid/tree/main/docs/research/experiments/b10-differential-catch-rate/harness). The raw outputs that were kept are in the [study's records](https://github.com/jszmajda/lid-research-records/tree/main/b10-differential-catch-rate).
