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

Every number here comes from one experiment, B10, run on 2 and 3 August 2026 on one segment of one project: the 24 requirements behind the Google Sheets view of portfolio-tracker, a personal-finance tool LID's maintainer built with LID. The headline auditor was Claude Sonnet; no Claude model's version was recorded. The audit ran as a harness written for the experiment, not as the skill LID ships, and the two differ in ways that matter. "Counted" means the analysis was fixed before any audit ran, not that the numbers are precise; we label what came after. Only the documents' own dates show when that was, since the design was first committed together with the results.

## The question

LID's case for lighter review is that once intent is written down as requirements and linked to the code by annotations, comments beside the code that name the requirement it meets, a reviewer can stop reading every line and check instead that what landed traces back to what was meant. That holds only if the checking catches what a careful reader would.

The bidirectional differential audits one requirement from both ends. In the A direction, a fresh session writes code from the requirement's text alone. In the B direction, a fresh session reads only the code, stripped of documents and requirement IDs, and writes the requirement it enforces. A classifier compares each with the real thing and lists the gaps.

On Threadkeeper, the maintainer's private app, this two-way version judged five of six requirements out of step with their code in [B9](https://github.com/jszmajda/lid/blob/main/docs/research/experiments/b9-bidirectional-differential-filter/RESULTS.md), and the one-way differentials [B1](https://github.com/jszmajda/lid/blob/main/docs/research/experiments/b1-differential-thr-det-021/RESULTS.md) and [B2](https://github.com/jszmajda/lid/blob/main/docs/research/experiments/b2-differential-llds-ears-primary/RESULTS.md) found other real gaps. With no answer key, they showed that the method finds things, not how much it misses. B10 planted gaps with the answers written down in advance, eight of each of three kinds:

- **Unstated intent.** The code and its tests gain a behaviour no requirement states, such as trimming and upper-casing a stock symbol before looking it up.
- **Phantom requirements.** A requirement gains a claim nothing in the code enforces.
- **Hollow tests.** The code quietly stops meeting a requirement, and its tests are changed to pin the narrower behaviour, so every check stays green. Sonnet had done this to its own code in earlier LID experiments, so B10 cared most about this kind, and we predicted it would be the hardest to catch.

## The short answer

| | What we saw |
|---|---|
| Planted gaps caught by fresh Sonnet auditors | 23 of 24 (95% interval about 0.80 to 0.99), against a pre-registered bar of 0.70. |
| By kind | Hollow tests 8 of 8, phantom requirements 8 of 8, unstated intent 7 of 8. Hollow tests, predicted hardest, were easiest. |
| The one miss | In code no annotation reached, so no auditor saw it. |
| More independent auditors | Bought nothing measurable: on 8 of the seeds, self-audit, Opus, GPT-5.6 Terra and GPT-5.6 Luna each caught 7, on an exam too easy to separate them. |
| A cheaper model | Haiku caught 5 of 8. |
| The label per requirement | Carried no signal: all 48 of Sonnet's audits, seeded or not, were labelled drifting. |
| False alarms on untouched requirements | 0% to 7.5% of findings per auditor, as a judge model ruled, but Sonnet still raised about five findings per untouched requirement. |
| Cost | About 343,000 Claude tokens per requirement audited. |
| The skill LID ships | Differs from what we tested in what it reads, reports and says it costs. |

## How we tested

**The fixture.** portfolio-tracker is a Rust workspace that keeps an investment ledger and publishes read-only view tabs to Google Sheets. The segment that writes them was fully implemented at commit `ba94c01`, tagged [`lid-b10-baseline`](https://github.com/jszmajda/portfolio-tracker/tree/lid-b10-baseline), and its full check suite passed, including formal-verification stages and a check that a test cites each of the project's 365 requirements.

**The seeds.** A Sonnet session planted each gap in its own clone, one per requirement, drawing on gaps seen in real work: wire formats, exact constants, error handling, boundary behaviour and tie-breaking. Each seeded clone still passed the project's checks with every annotation resolving, so only the audit could find it. The controls are the same 24 requirements, untouched.

**The audit.** Each unit was one requirement: three A-direction runs, three B-direction runs and one classifier call. The B direction read the files that cite the requirement, tests included; the classifier read all six outputs and listed findings strongest first. The [prompts](https://github.com/jszmajda/lid/blob/main/docs/research/experiments/b10-differential-catch-rate/harness/audit-prompts.md) were frozen after a two-seed pilot.

**The arms.** Fresh Sonnet sessions ran all 48 units. A subset of 8 seeds and 8 controls was also audited by the seeding session itself, by fresh Opus, and by GPT-5.6 Terra, chosen as Sonnet's peer from another provider, with Claude Haiku and GPT-5.6 Luna as an exploratory arm.

**Scoring.** A seed was caught when any finding in its unit matched the key's direction and substance. A Claude Fable judge, not told which units were seeded, ruled each finding on an untouched requirement a real gap, a missing cross-reference (behaviour a sibling requirement states), or a false alarm. GPT-5.6 Sol re-judged a sample; if the two agreed on less than 85% of it, Jess Szmajda, LID's maintainer, would rule on every disagreement before any number was published.

## What we found

### Planted gaps caught

| Auditor | Unstated intent | Phantom requirement | Hollow test | Total |
|---|---|---|---|---|
| Sonnet, fresh, all seeds | 7 of 8 | 8 of 8 | 8 of 8 | 23 of 24 |
| On the subset of 8, each of: Sonnet auditing its own seeds; fresh Sonnet, Opus and GPT-5.6 Terra; GPT-5.6 Luna (exploratory) | 2 of 3 | 3 of 3 | 2 of 2 | 7 of 8 |
| Haiku, fresh, the subset (exploratory) | 1 of 3 | 3 of 3 | 1 of 2 | 5 of 8 |

An auditor that caught a seed usually led with it: the matching finding came first in 17 of Sonnet's 23 catches, and 42 of the 49 by fresh auditors.

### The one miss

Every auditor missed the seed that kept the last good quote date when a new one couldn't be read. Its file named no requirement ID, and the audit picks files to show by following those IDs, so no auditor saw it. Another seed in that file was shown, because its requirement's annotations reached there, and every auditor but Haiku caught it.

So the audit sees only what annotations reach, and the agent writing the code usually places them; nothing here tests whether that tempts it to leave some out. Setting the unseen seed aside, a view chosen after the results, every auditor caught all it could see, except Haiku at 5 of 7.

### Hollow tests were easiest, by construction

A hollow-test seed leaves the requirement alone, so the A direction rebuilds the original intent, the B direction the narrowed code, and the two collide, often on an exact value. One seed made a price conversion round ties up instead of to even, and the findings named the case: $1.005 became 101 cents, where the requirement's rule gives 100. That is also the result's limit: these hollow tests were visible by design. In real use, an agent may narrow the requirement along with the code, or the requirement may have been ambiguous from the start.

### Independence, and a cheaper model

The tie at 7 of 8 doesn't show that independence is worthless: every seed was either visible and caught by all those auditors or hidden from all of them, so a more independent one had nothing left to find. Whether related models share blind spots is neither confirmed nor ruled out.

Haiku, a cheaper model, gave way: it also missed a hollow test, and found another seed's planted mechanism but called it harmless, which counted as a miss. Luna, also cheap, didn't.

### The label per requirement carried no signal

The audit labels whether, and which way, each requirement and its code have drifted apart. All 48 of Sonnet's units and all 16 of Opus's were labelled drifting. That's partly real, since the untouched requirements had genuine gaps, but the label couldn't tell planted gaps from that background, and it wasn't stable: 3 of the 24 untouched units changed label between the Sonnet arm's two executions. The findings list, matched against the key, was what separated seeds from controls.

### Findings on untouched requirements

| Auditor | Findings | Real gaps | Missing cross-references | False alarms |
|---|---|---|---|---|
| Sonnet, 24 requirements | 120 | 54 | 57 | 9 (7.5%) |
| Opus, 8 | 77 | 44 | 31 | 2 (2.6%) |
| GPT-5.6 Terra, 8 | 42 | 22 | 20 | 0 |
| GPT-5.6 Luna, 8 | 43 | 20 | 22 | 1 (2.3%) |
| Haiku, 8 | 18 | 6 | 11 | 1 (5.6%) |

Around half the findings were missing cross-references. The real gaps are discoveries in portfolio-tracker; the most serious is that a requirement says leftover rows must be cleared from a view tab, and only the test doubles do it, not the production Sheets code.

### The judges disagreed enough to call in the human

Fable and Sol agreed on 112 of 134 sampled verdicts, 83.6%, below the trigger; Sol finished 10 of its 15 planned groups before the OpenAI credits ran out. On 3 August Jess ruled on all 22 disagreements, siding with Fable 12 times and Sol 10, on principles not fixed in advance: a sibling may state an exception to a universal requirement, which makes a missing cross-reference, not drift; silence on a question nobody has settled isn't drift; and a finding that calls a planted gap harmless doesn't catch it. That last moved Haiku from 6 of 8 to 5 of 8, the only recall figure that changed.

### Stability and cost

Sonnet's three A-direction runs agreed closely on 30 of its 48 units and poorly on 2; its B-direction runs agreed closely on 45. Haiku's A-direction runs agreed poorly on 8 of 16.

Claude calls, seeding and pilot included, used about 46.1 million tokens, and judging about 5.5 million more, recorded as tokens, not dollars. 16.6 million of that came from the Sonnet arm running twice after a workflow resume; the second execution was scored and the first kept as superseded. OpenAI calls were priced: Terra cost $3.94 for 16 units, Luna $0.43, and Sol's cross-checks about $2.33.

## What the shipped skill does differently

LID ships this audit as the experimental [bidirectional-differential skill](https://github.com/jszmajda/lid/tree/main/plugins/lid-experimental/skills/bidirectional-differential), which differs from B10's harness:

- **It leaves tests out by default.** B10's B direction read test files and was asked for behaviour pinned only by tests; the skill omits them unless the user opts in ([audit-protocol.md](https://github.com/jszmajda/lid/blob/main/plugins/lid-experimental/skills/bidirectional-differential/references/audit-protocol.md)). No B10 arm ran without them, so we don't know how much the result depended on them.
- **It leads with the label B10 found carries no signal.** The label heads each audit record, and the summary leads with label counts. With no key or judge, a user sees every finding, with nothing sorting real gaps from missing cross-references and false alarms.
- **It describes a different cost.** The [design](https://github.com/jszmajda/lid/blob/main/docs/intent/lid-experimental/bidirectional-differential/bidirectional-differential-design.md) puts an audit at about six short calls costing "a few cents" at Sonnet rates. B10's took seven calls (a separate classifier, where the skill classifies in its own session) and about 343,000 tokens, and Terra, Sonnet's peer, cost about 25 cents a unit. With no Claude price, we can't check the design's figure directly.

The prompts differ too: B10's A direction listed every assumption it invented; the skill's asks for code alone. Open questions for LID:

- Should the skill's B direction read tests?
- Should its report lead with ranked findings, not the label?
- Could a judging step, or a check for sibling requirements, cut the cross-reference noise before a person reads it?
- Since the audit sees only annotated code, should LID measure how much of a change its annotations reach?
- Should the design state a measured cost?

## What this doesn't show

**That audits can replace reading code.** B10 had no comparison: no person reading the code, no ordinary reviewer prompt, no one-direction audit. It set a bar for the audit, not a rule for choosing between auditing and reading. It supports something narrower: on annotated code, the audit can take some of the checking that requirements and code agree off a reviewer.

**Anything a requirement doesn't say.** Maintainability, security, architecture, and choices that are each reasonable but add up badly are mostly in no requirement or test, and no catch rate here bears on them.

**Real gaps, found unprompted.** The seeds were synthetic, written by a Sonnet session that knew the audit existed, so they may sit close to what it expects; gaps recovered from real bug fixes would settle that. Every auditor also knew it was auditing; real drift arrives unannounced.

**Other codebases.** Everything was measured on one segment of the maintainer's own code, built with LID from its first commit.

## How sure we are

**The exam was too easy.** Clearing the bar widely, with every auditor but one tied, is what a saturated exam looks like. B10 is best read as a calibration pilot: the harness works, and the next exam needs to be harder. 23 of 24 has a wide interval, and on a Wilson interval 8 of 8 in a kind is consistent with a true rate as low as about 0.68.

**What was fixed in advance.** The hypothesis, the 0.70 bar, the readouts and the 85% trigger are in the [design](https://github.com/jszmajda/lid/blob/main/docs/research/experiments/b10-differential-catch-rate/DESIGN.md), with an amendment dated before seeding and adjustments dated after the pilot but before the main runs. The view without the unseen seed, and the human pass's principles, came later.

**Blinding was partial.** Judges of untouched-requirement findings could compare seeded code with the baseline, and at least two verdicts mention "the planted change". File paths given to the B direction and the classifier named the baseline or the seed's ID, so an auditor could tell untouched code from planted, though not what was planted. Haiku's sessions ran in the folder holding the sealed key; their prompts said to read nothing else, and no output shows one opening it. We can't measure what any of this changed.

**Who judged.** A Claude model judged mostly Claude auditors, hence Sol's cross-check, and there was one human judge. The GPT arms got file contents in their prompts; Claude arms read files.

**What survives.** Kept: Sonnet's untouched units from both runs, the Opus and Haiku arms, and the pilot's judging files. Not kept: Sonnet's seeded units, the Terra and Luna outputs, and the main judging outputs, so 23 of 24 rests on the scoring files' tallies, not on outputs anyone can re-read.

**The critique.** After the results, eight model reviewer set-ups attacked the design and its reading, in twelve Claude-family reviews over two rounds and two on GPT-5.6 Sol ([CRITIQUE.md](https://github.com/jszmajda/lid/blob/main/docs/research/experiments/b10-differential-catch-rate/CRITIQUE.md)). They read a prose summary, not the records, and only the two Sol reviews raised the missing comparison. That review shapes this report, but it was models reviewing a model-run study.

## Where the details are

The study's notebook, [`docs/research/experiments/b10-differential-catch-rate/`](https://github.com/jszmajda/lid/tree/main/docs/research/experiments/b10-differential-catch-rate) in the LID repository, holds the design, the [pilot](https://github.com/jszmajda/lid/blob/main/docs/research/experiments/b10-differential-catch-rate/PILOT.md), the [results](https://github.com/jszmajda/lid/blob/main/docs/research/experiments/b10-differential-catch-rate/RESULTS.md) as written at the time, the critique, the [final scoring](https://github.com/jszmajda/lid/blob/main/docs/research/experiments/b10-differential-catch-rate/scoring-final.json), the [answer key](https://github.com/jszmajda/lid/tree/main/docs/research/experiments/b10-differential-catch-rate/answer-key) with each seed's patch and the [human rulings](https://github.com/jszmajda/lid/blob/main/docs/research/experiments/b10-differential-catch-rate/answer-key/human-adjudication.md), and the [harness](https://github.com/jszmajda/lid/tree/main/docs/research/experiments/b10-differential-catch-rate/harness). The raw outputs that were kept are in the [study's records](https://github.com/jszmajda/lid-research-records/tree/main/b10-differential-catch-rate).
