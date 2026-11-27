---
title: "Which judgments a model can be left to make: the first 29 configurations"
date: 2026-11-27
status: pilot
summary: "How LID measures which judgments a model misses, so it can bring them to the user. In pilot runs of 29 configurations, 9 missed one or both of the two judgments tested. Size and release date didn't predict which, and every Claude model ran in a different harness from every other model."
tested:
  lid: "1.4.0 (two skill trees; see How we tested)"
  agent: "Claude Code 2.1.296 or 2.1.310 (Claude models); opencode 1.18.32 via OpenRouter (others)"
  model: "29 configurations at medium effort (see the table)"
records: "https://github.com/jszmajda/lid-research-records/tree/main/capability-flags"
---

This is a snapshot of the first 29 model configurations LID tested for capability flags, run between 10 October and 20 November 2026 (UTC). The list gains rows as models are tested. Its current rows are in [capability-flags.md](https://github.com/jszmajda/lid/blob/main/plugins/linked-intent-dev/skills/linked-intent-dev/references/capability-flags.md), and this report won't be updated. Four things limit what it shows:

- **These are pilot results.** The line that decides what counts as a miss was set while the runs were under way, and two results sit exactly on it.
- **Every Claude model ran in Claude Code, and every other model ran in opencode through OpenRouter.** So any difference between Claude and the rest may come from the harness as much as from the model.
- **The test projects are small** and state the conditions each judgment turns on fairly plainly. A pass says a model makes the judgment when the documents make it visible.
- **Each result rests on 10 runs per project.**

## The question

LID stops at each phase of a change to show the person it works with what it wrote, and many people let some of those checks go once they trust the agent. But some judgments depend on the model: one notices that a design works against the project's own principles, and another reads straight past it. If someone lets that check go while running a model that misses it, nobody makes the judgment.

So LID keeps a list of **capability flags**. For each configuration it has tested, a model at a reasoning effort, the list says which kinds of judgment that configuration is known to miss. When a flag applies, the agent does its work as usual, then names the judgment at the phase's stop and asks the person to check it, even if they had let that kind of check go. This report covers how a configuration earns a flag, and what the first 29 showed.

## The short answer

| | What we saw |
|---|---|
| Flags | 9 of the 29 configurations missed at least one of the two judgments tested: 4 missed both, 2 only the first, 3 only the second. The other 20 cleared the bar on both. |
| What predicted a miss | Across vendors, neither size nor release date did. A small model (Claude Haiku 5.5) carries no flag, and a large one released in June 2026 (Nemotron 3 Ultra) carries both. |
| How close the calls were | Mostly not close. Of the 87 results (29 configurations, three tables), 5 would change if one run in one cell had gone the other way. |
| What a pass hides | A flag needs misses on two projects, so a configuration that passes can still miss most of the time on one. Only 11 of the 29 scored above 70% on all eight projects. |
| Rewording the skill | Where we tried it on a flagged model, the miss stayed and another behaviour got worse. |
| The harness | Confounded with the vendor. The one comparison of a model in both harnesses found little difference once reasoning was matched, but that was one model on two projects. |

## What a flag is

Of the eleven kinds of judgment LID's workflow names, two have flags so far:

- **Tenet or goal conflict:** noticing that a design's mechanism works against one of the project's own tenets or goals, when the two share no wording.
- **Under-captured decision:** recognising when a settled choice will stay live for a later reader and deserves a fuller record. That means offering a decision doc when the person settles such a choice, and, in a review, flagging a decision whose record doesn't let a cold reader see what was given up.

The list also records **tendencies**, leans in something the person already decides. The one so far is **offering decision docs too readily**, for choices a table row would cover, so a configuration with it just says so once, when it offers a doc.

Every configuration ran at medium effort, the most common default. A model told it runs at a lower effort takes every flag, whatever its row says.

## How a flag is earned

**The test projects** are eight small fixtures from LID's own eval suites ([core](https://github.com/jszmajda/lid/blob/main/plugins/linked-intent-dev/skills/linked-intent-dev/evals/evals.json), [lid-coach](https://github.com/jszmajda/lid/blob/main/plugins/linked-intent-dev/skills/lid-coach/evals/evals.json)), with the same files and prompts for every configuration:

- *Tenet or goal conflict:* coach evals 15 (library holds) and 16 (home-visit openings), where LID's review skill reads a design whose mechanism works against a tenet, in different words.
- *Under-captured decision:* core evals 0 and 3, where the agent should offer a decision doc, and coach evals 10 and 11, where a review should flag a thin record as a finding of its own.
- *The tendency:* core evals 1 and 2, where the agent should hold back.

Each fixture has several assertions. A run's **cell** counts the one that tests the judgment: whether the agent offered the doc, held back, or raised the finding.

**The bar.** A flag or tendency enters the list only when all three hold:

1. **At least 10 runs** per configuration on each project. A run the host cuts short says nothing about the model, so it's rerun unless no outcome of it could change the result. If the rerun is cut short again, the project is judged on the runs that finished.
2. **A gap larger than the noise.** In a noise study before the roster, the strongest configurations scored 9 or 10 of 10, so a pass rate of **70% or lower** (7 of 10) counts as a miss. A configuration that truly passes 9 runs in 10 scores 7 or lower about 7% of the time. By chance, then, it misses both of two projects about 0.5% of the time, and two of four about 3%. An 80% line would raise those to about 7% and 29%.
3. **Misses on at least two projects**, so one awkward fixture can't flag a model.

A rerun that no longer clears the bar removes the flag.

### Which parts came first

| Date | What was settled | Configurations already run |
|---|---|---|
| 25 Sep | 10 runs, a gap beyond the noise, two projects ([8f4b392](https://github.com/jszmajda/lid/commit/8f4b392e310fd7623b586063d002d1ff6afa205a)) | 0 |
| 28 Sep | Effort pinned at medium; flags keyed to a configuration, not a class of models ([fc18658](https://github.com/jszmajda/lid/commit/fc18658e6996d35478b976b46bdf22ff6438dfd7)) | 0 |
| 9 Oct | Core eval 3 added ([1e7ef1a](https://github.com/jszmajda/lid/commit/1e7ef1a4435a9140019eaa0bf3bf7792152d092e)) | 0 |
| 14 Oct | Evidence runs use a copy of the skills with the flag list removed ([919c4b4](https://github.com/jszmajda/lid/commit/919c4b4bae2de396603e0b52794ddbb6c52dcf6a)) | 13 |
| 21 Oct | The 70% line, and reruns of runs a host cuts short ([80a7679](https://github.com/jszmajda/lid/commit/80a7679049ce4010a9d34086af3deaa0b1630ece)) | 19 |
| 11 Nov | A rerun cut short again is judged on the runs that finished ([6454735](https://github.com/jszmajda/lid/commit/64547352e9256bf9488e03dc95d060011b87954e)) | 26 |

The core of the bar came before any run, but the 70% line was chosen after 19 configurations had run. A 60% line would have changed none of those 19 results. An 80% line would have changed three, flagging GPT-6 Luna and listing DeepSeek V4.1 Flash and GLM 5.3 for the tendency. Two later results sit exactly on the line: Claude Sonnet 5's tendency and Kimi K3.1 Pro's under-captured flag each depend on a cell of exactly 7 of 10, and at 60% neither would be listed. The rule for reruns cut short again was written the day MiniMax M3.1 Flash needed it. Its tendency cells came out at 7 of 8 and 5 of 8, so it isn't listed. Counting the unfinished runs as misses would have listed it.

## How we tested

**Two skill trees.** The first 13 configurations ran against the skills at commit `1e7ef1a`, with the flag list in place but empty. That mattered: the list's rule for an untested model is to treat every flag as applying, and in 17 of about 1,000 of those runs the model applied it and raised tenet checks, the very judgment being measured. The list's notes say leaving those runs out changes no result. We didn't re-derive the 17 from the records. The other 16 ran against a copy of commit `919c4b4` with the list, and every passage that mentions it, removed by hand. A search and a diff checked the copy before the runs, and the diff is in the records. Both trees' manifests say 1.4.0, but neither is a release: the first is from the day before 1.4.0 shipped, and the second is the first commit of the change that became 1.4.1.

**Two harnesses.** The Claude models ran headless in Claude Code (`claude -p`, version 2.1.296 on 10 October and 2.1.310 on 24 October) at `--effort medium`, on the maintainer's machine, reading the skill as a file. Every other model ran in opencode 1.18.32 in a locked-down container, reached through OpenRouter at medium reasoning effort, and loaded the skill through opencode's skill tool. The prompts matched apart from how to load the skill. Claude Code allowed 25 minutes per turn. opencode allowed 10 minutes per run, except on 20 November, when it allowed 30 minutes, with a 10-minute limit on silence. Claude Code's version isn't in the run records; it comes from the list.

**Blind grading.** A model session graded each finished run against the fixture's assertions, seeing the fixture, the run's replies and changes, and a random ID, never the model's name. From the third grading round on, each blind batch also held runs from earlier rounds with a known grade on the cell. Of those 192 planted controls, 190 came back as expected. Both exceptions turned on the same borderline reading of coach eval 10, one graded leniently and one strictly, and neither would change a result. A batch whose grader drifted from the agreed reading was regraded with that reading spelled out. **Rounds 6 to 8, which cover the last 8 configurations, were graded by Claude Sonnet 5.5.** No surviving record says which model graded the first five rounds.

All 232 evidence cells in the list can be recomputed exactly from the de-blinded grades in the records, which include a script that does it.

## The first 29 configurations

A cell is the number of runs that made the judgment, out of those graded; for core evals 1 and 2, that's the runs that held back. The last column lists every cell at 70% or lower, including single misses that don't earn a flag. Tree A is `1e7ef1a` with the empty list, and tree B the stripped copy of `919c4b4`. MiniMax, MiMo and Gemini 3.8 Flash had some runs cut short, so they had fewer than 80 graded.

| Configuration | Harness | Ran (UTC) | Tree | Runs graded | Flags | Tendency | Cells at 70% or lower |
|---|---|---|---|---|---|---|---|
| `claude-sonnet-4-5` | Claude Code 2.1.296 | 10 Oct | A | 80 | tenet or goal conflict; under-captured decision | — | core 0 4/10; core 3 0/10; coach 11 2/10; coach 15 0/10; coach 16 0/10 |
| `claude-haiku-4-5` | Claude Code 2.1.296 | 10 Oct | A | 80 | tenet or goal conflict; under-captured decision | — | core 0 2/10; core 3 0/10; coach 10 5/10; coach 11 1/10; coach 15 0/10; coach 16 0/10 |
| `meta/muse-glimmer-30b` | opencode 1.18.32 | 17 Oct | B | 80 | tenet or goal conflict; under-captured decision | — | core 0 0/10; core 3 0/10; coach 11 1/10; coach 15 0/10; coach 16 0/10 |
| `nvidia/nemotron-3-ultra-550b-a55b` | opencode 1.18.32 | 19 Oct | B | 80 | tenet or goal conflict; under-captured decision | — | core 0 0/10; core 3 0/10; coach 10 7/10; coach 11 2/10; coach 15 0/10; coach 16 0/10 |
| `z-ai/glm-5.3-flash` | opencode 1.18.32 | 10 Oct | A | 80 | tenet or goal conflict | offers decision docs too readily | coach 11 1/10; coach 15 1/10; coach 16 5/10; core 1 6/10; core 2 3/10 |
| `google/gemini-3.8-flash` | opencode 1.18.32 | 19 Oct | B | 76 | tenet or goal conflict | — | coach 15 0/10; coach 16 6/10; core 2 2/10 |
| `openai/gpt-5.6-terra` | opencode 1.18.32 | 10 Oct | A | 80 | under-captured decision | — | core 0 6/10; core 3 3/10; coach 11 3/10 |
| `moonshotai/kimi-k3.1-pro` | opencode 1.18.32 | 9 Nov | B | 80 | under-captured decision | — | core 0 7/10; core 3 1/10 |
| `minimax/minimax-m3.1-flash` | opencode 1.18.32 | 11 Nov | B | 72 | under-captured decision | — | core 3 3/6; coach 11 3/10; core 2 5/8 |
| `claude-opus-4-8` | Claude Code 2.1.296 | 10 Oct | A | 80 | none | offers decision docs too readily | core 1 3/10; core 2 4/10 |
| `claude-sonnet-5` | Claude Code 2.1.310 | 24 Oct | B | 80 | none | offers decision docs too readily | coach 15 3/10; core 1 7/10; core 2 2/10 |
| `claude-haiku-5-5` | Claude Code 2.1.296 | 10 Oct | A | 80 | none | — | coach 11 7/10 |
| `claude-opus-5-5` | Claude Code 2.1.296 | 10 Oct | A | 80 | none | — | none |
| `claude-sonnet-4-6` | Claude Code 2.1.296 | 10 Oct | A | 80 | none | — | core 3 3/10; coach 15 6/10 |
| `claude-sonnet-5-5` | Claude Code 2.1.296 | 10 Oct | A | 80 | none | — | none |
| `deepseek/deepseek-v4.1-flash` | opencode 1.18.32 | 10 Oct | A | 80 | none | — | core 1 6/10 |
| `openai/gpt-5.6-sol` | opencode 1.18.32 | 10 Oct | A | 80 | none | — | none |
| `openai/gpt-6.1-sol` | opencode 1.18.32 | 10 Oct | A | 80 | none | — | none |
| `z-ai/glm-5.3` | opencode 1.18.32 | 10 Oct | A | 80 | none | — | core 2 7/10 |
| `google/gemini-4-argon` | opencode 1.18.32 | 17 Oct | B | 80 | none | — | none |
| `openai/gpt-6-luna` | opencode 1.18.32 | 19 Oct | B | 80 | none | — | core 3 1/10; coach 15 7/10 |
| `xiaomi/mimo-v2.6-flash` | opencode 1.18.32 | 19–20 Oct | B | 74 | none | — | core 1 4/7 |
| `claude-opus-5` | Claude Code 2.1.310 | 24 Oct | B | 80 | none | — | none |
| `openai/gpt-6.1-terra` | opencode 1.18.32 | 11 Nov | B | 80 | none | — | none |
| `tencent/hy4` | opencode 1.18.32 | 11 Nov | B | 80 | none | — | core 3 5/10 |
| `deepseek/deepseek-v4.1-flash-1017` | opencode 1.18.32 | 11 Nov | B | 80 | none | — | none |
| `google/gemini-4-carbon` | opencode 1.18.32 | 20 Nov | B | 80 | none | — | none |
| `google/gemini-4-hydrogen` | opencode 1.18.32 | 20 Nov | B | 80 | none | — | none |
| `google/gemini-4-neon` | opencode 1.18.32 | 20 Nov | B | 80 | none | — | none |

Dates are from the run records. The list gives a few rows a date a day earlier.

## What the snapshot showed

**Size and release date didn't predict a miss.** Across vendors, Claude Haiku 5.5 (small) carries no flag, while Nemotron 3 Ultra (large, June 2026) and Kimi K3.1 Pro (large, October 2026) are flagged. Within each vendor's line, newer and larger models did no worse: Claude Haiku 4.5 missed what Haiku 5.5 catches, and GPT-5.6 Terra what GPT-6.1 Terra catches. That's why the list is keyed to exact configurations, and why a model with no row may take the row of an earlier release in its line or a smaller model of its generation, never a newer or larger one.

**A pass can hide a deep miss on one project.** Requiring two misses keeps one awkward fixture from flagging a model, but it also lets a single deep miss through. Claude Sonnet 5 raised the library-holds conflict in 3 of 10 runs and passes that flag. GPT-6 Luna offered the decision doc on core eval 3 in 1 of 10 runs and passes too, as do Claude Sonnet 4.6 (3 of 10) and Hy4 (5 of 10). The list records these single-project misses so a later run can confirm or clear them, but they don't reach the person as flags.

**Rewording the skill didn't close the gap where we tried it.** Before the roster, LID's review skill gained an explicit check of designs against the project's tenets. On Claude Sonnet 4.5 it left the library-holds conflict at 0 of 10. On another project it raised Sonnet 4.5's tenet finding from 3 to 7 of 10, while its finding on the thin decision record fell from 5 to 1: one finding replaced the other. Wording isn't irrelevant, though: Claude Opus 4.8 went from 6 of 10 on an early version of library holds to 10 of 10 after the change, though other settings changed too.

**Reasoning effort moves results as much as the model does.** On one review project in Claude Code, Sonnet 4.5 caught the tenet conflict in 7 of 10 runs with its default thinking on, and 0 of 10 with it off. Asking for an effort doesn't guarantee reasoning, either. Gemini 4 Argon's provider passes medium on as a low effort level, and it reasoned in 14 of its 80 evidence runs. It passed every project anyway.

**Some models didn't follow the workflow.** MiniMax M3.1 Flash often ran past the phase stop until the 10-minute limit stopped it: in 13 of its 40 core runs, and 8 of 30 reruns. Hy4 stopped after a one-line progress message, before doing any work, in 11 of its 40 core runs. All of its core eval 3 misses were stalls like that, and its stalls on core 1 and 2 count as holding back. Gemini 3.8 Flash ended its first turn with no reply at all in 4 core runs. Muse Glimmer 30B and Nemotron 3 Ultra never offered a decision doc in a first turn, so their perfect scores for holding back show that they don't offer one, not restraint.

**Some configurations raise conflicts that aren't there.** The library-holds project contains a decoy: a mechanism that costs something toward a goal without contradicting a tenet. 15 of the 29 configurations named a mechanism other than the real one as a conflict at least once. Claude Opus 5, Claude Haiku 5.5 and GPT-6.1 Terra did so in 9 of 10 runs, while finding the real conflict every time. LID records this as an observation, not a tendency, because an extra finding asks the person to look twice, which costs less than a missed one.

**Spending varied widely.** On these projects, 26 of the 29 configurations had a median under 10,000 reasoning tokens per run, which providers bill as output, and Hy4's median was 36,301. Each harness reports its provider's own counts, so figures compare only roughly across the two.

## How sure we are

**Harness and vendor move together.** No Claude model ran in opencode, and no other model in Claude Code. The two differ in how the skill reaches the model, how reasoning is requested, the time limits, and where the run happens, so a gap between Claude and the rest could come from any of those. The one direct check ran Claude Sonnet 4.5 in both, on 28 September, on earlier skill text and two review projects. On one, with Claude Code's thinking off, the harnesses scored within two runs of each other on every assertion; on the other, Sonnet 4.5 missed the conflict in every run in both. It also found the runner cutting long lines from the skill, fixed before the roster. One model on two projects doesn't show that the harness never matters.

**The grader is a Claude model.** At least the last three grading rounds used Claude Sonnet 5.5, itself one of the configurations. Grading was blind and checked against planted controls, but a Claude grader may still read Claude's style more kindly. No grader from another vendor has rechecked these grades.

**The rules and the text changed during the runs.** The 70% line came after 19 configurations had run, and two results depend on a cell of exactly 7 of 10. The first 13 configurations ran on different skill text from the other 16, and none of the 13 has been rerun on the stripped tree. Each result is a claim about the text it ran on.

**Some records were lost.** The 20 November runs of the three Gemini 4 models were made in a checkout that was later deleted. Their replies, changes and grades survive in the copies made for blind grading, and their results reproduce from those. Their timing, token counts and transcripts don't.

**The models weren't sampled.** The maintainer chose them, for example the untested models in one week's OpenRouter top 10, and the three untested Gemini 4 models.

**No run went without LID.** Every run followed the skill, so these results say which judgments a model makes while following LID, not what LID adds.

## Where the details are

- **The current list:** [capability-flags.md](https://github.com/jszmajda/lid/blob/main/plugins/linked-intent-dev/skills/linked-intent-dev/references/capability-flags.md), with every row's evidence, the single-project misses, and notes on each configuration's behaviour.
- **The design:** the *Capability Flags* section of the [linked-intent-dev design](https://github.com/jszmajda/lid/blob/main/docs/intent/linked-intent-dev/linked-intent-dev-design.md), whose decisions table says why the line is 70%; the [core workflow's design](https://github.com/jszmajda/lid/blob/main/docs/intent/linked-intent-dev/core/core-design.md), on what the agent does with a flag; and the [alternate-model eval design](https://github.com/jszmajda/lid/blob/main/docs/intent/alt-model-evals/alt-model-evals-design.md), on the opencode runner.
- **The records:** [lid-research-records/capability-flags](https://github.com/jszmajda/lid-research-records/tree/main/capability-flags) holds every graded run's replies, changes, timing and de-blinded grade, one index row per batch, the blind keys and grades with their controls, the diff that made the stripped tree, and the noise study and harness comparison. Its README lists what was left out and why.
