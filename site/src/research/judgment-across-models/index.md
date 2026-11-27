---
title: "Which judgments a model can be left to make: the first 29 configurations"
date: 2026-11-20
status: pilot
summary: "How LID measures which judgments a model misses, so it can bring them to the user. In pilot runs, 9 of 29 configurations missed one or both of the two judgments tested. Neither size nor release date sorted which, and every Claude model ran in a different harness from the rest."
tested:
  lid: "pre-release trees of 1.4.0 and 1.4.1 (1e7ef1a; 919c4b4, stripped)"
  agent: "Claude Code 2.1.296 or 2.1.310 (Claude models); opencode 1.18.32 via OpenRouter (others)"
  model: "29 configurations at medium effort (see the table)"
records: "https://github.com/jszmajda/lid-research-records/tree/main/capability-flags"
---

This is a snapshot, which won't be updated, of the first 29 model configurations LID tested for capability flags, run from 10 October to 20 November 2026 (UTC). The list's current rows are in [capability-flags.md](https://github.com/jszmajda/lid/blob/main/plugins/linked-intent-dev/skills/linked-intent-dev/references/capability-flags.md). Five things limit it:

- **These are pilot results, and much of the method came during the runs.** One of the two judgments, the tendency category, and the line for what counts as a miss were defined after the first 13 configurations ran. Two results sit exactly on that line.
- **Every Claude model ran in Claude Code, and every other model in opencode through OpenRouter,** so a difference between Claude and the rest may come from the harness as much as the model.
- **The grader was a Claude model, where we know.** No surviving record names the grader for 21 configurations, including 7 of the 9 flagged, and the first 13 had no planted checks on their grading.
- **The test projects are small** and state fairly plainly the conditions each judgment turns on, so a pass says a model makes the judgment when the documents make it visible.
- **Each result rests on 10 runs per project.**

## The question

LID stops after each phase of a change to show the person what it wrote, and many people let some of those checks go once they trust the agent. But some judgments depend on the model: one notices that a design works against the project's own principles, another reads straight past it. So LID keeps a list of **capability flags**: for each configuration it has tested, a model at a reasoning effort, the kinds of judgment it is known to miss. When a flag applies, the agent names that judgment at the phase's stop and asks the person to check it, even if they had let such checks go.

## The short answer

| | What we saw |
|---|---|
| Flags | 9 of the 29 configurations missed at least one of the two judgments tested: 4 missed both, 2 only the first, 3 only the second. The other 20 cleared the bar on both. |
| Size and release date | Neither sorted flagged models from unflagged ones, though small and older models were flagged more often. |
| How close the calls were | Mostly not close. Of the 87 results (two flags and the tendency, for each configuration), 5 would change if one run on one project had gone the other way. |
| What a pass hides | A flag needs misses on two projects, so a configuration that passes can still miss most of the time on one. Only 11 of the 29 scored above 70% on all eight projects. |
| Rewording the skill | Where we tried it on a flagged model, the miss stayed and another behaviour got worse. |

## What a flag is

Of the eleven kinds of judgment LID's workflow names, two have flags so far:

- **Tenet or goal conflict:** noticing that a design's mechanism works against one of the project's own tenets or goals, when the two share no wording.
- **Under-captured decision:** recognising when a settled choice will stay live for a later reader and deserves a fuller record. Most choices get a **row** in a design's Decisions table, naming the choice, the alternatives and why; a few deserve a **decision doc**, a standalone record of the options and what was given up. The flag covers offering a doc when the person settles such a choice and, in a review, flagging a record too thin to show a cold reader what was given up.

The list also records **tendencies**, leans in something the person already decides. The one so far is **offering decision docs too readily**, for choices a row would cover; a configuration with it says so once, when it offers a doc.

Every configuration ran at medium effort, the most common default; a model told it runs lower takes every flag. The list's *Covered* entries, untested models given a tested model's row on the maintainers' knowledge, rest on no runs and are left out here.

## How a flag is earned

**The test projects** are eight small ones from LID's own eval suites ([core](https://github.com/jszmajda/lid/blob/226b03185e1fa27a5438a31814ea8542fa8c4ff0/plugins/linked-intent-dev/skills/linked-intent-dev/evals/evals.json), [lid-coach](https://github.com/jszmajda/lid/blob/226b03185e1fa27a5438a31814ea8542fa8c4ff0/plugins/linked-intent-dev/skills/lid-coach/evals/evals.json)), with the same files and prompts for every configuration, each known by its eval number:

- *Tenet or goal conflict:* coach evals 15 (library holds) and 16 (home-visit openings), where LID's review skill reads a design whose mechanism works against a tenet, in different words.
- *Under-captured decision:* core evals 0 and 3, where the agent should offer a decision doc, and coach evals 10 and 11, where a review should flag a thin record as a finding of its own.
- *The tendency:* core evals 1 and 2, where the agent should hold back.

Each eval has several assertions. A configuration's **cell** on an eval is how many of its graded runs passed the one that tests the judgment: offering the doc, holding back, or raising the finding.

**The bar.** A flag or tendency enters the list only when all three hold:

1. **At least 10 runs** per configuration on each project. A run the host cuts short may say nothing about the model, so it's rerun unless no outcome could change the result; if the rerun is cut short too, the project is judged on the runs that finished.
2. **A gap larger than the noise.** In a noise study before the roster, the strongest configurations scored 9 or 10 of 10, so a pass rate of **70% or lower** (7 of 10) counts as a miss. That study ran only Claude models, at Claude Code's default thinking rather than medium, on earlier skill text and two review projects: eval 11 and an early version of eval 15. A configuration that truly passes 9 runs in 10 scores 7 or lower about 7% of the time, so by chance it misses both of two projects about 0.5% of the time, and two of four about 3%. An 80% line would raise those to about 7% and 29%.
3. **Misses on at least two projects**, so one awkward project can't flag a model.

A rerun that no longer clears the bar removes the flag.

### Which parts came first

Dates are when each commit landed, in UTC.

| Date | What was settled | Configurations already run |
|---|---|---|
| 25 Sep | The bar's three rules, and one flag: tenet or goal conflict, on evals 15 and 16 ([8f4b392](https://github.com/jszmajda/lid/commit/8f4b392e310fd7623b586063d002d1ff6afa205a)) | 0 |
| 29 Sep | Effort pinned at medium; flags keyed to a configuration and the harness it ran in ([fc18658](https://github.com/jszmajda/lid/commit/fc18658e6996d35478b976b46bdf22ff6438dfd7)) | 0 |
| 9 Oct | Core eval 3 added ([1e7ef1a](https://github.com/jszmajda/lid/commit/1e7ef1a4435a9140019eaa0bf3bf7792152d092e)) | 0 |
| 10 Oct | The under-captured-decision flag and the four evals that count for it; the tendency category and its two evals, scored on holding back ([1a1f219](https://github.com/jszmajda/lid/commit/1a1f219e2b35a494617a20fd4efdddf427d3bbed)) | 13 |
| 11 Oct | The harness dropped from the key, and kept as data ([8474f96](https://github.com/jszmajda/lid/commit/8474f961b3249659b1ff2713a6c218225e2c4948)) | 13 |
| 17 Oct | Evidence runs use a copy of the skills with the flag list removed ([919c4b4](https://github.com/jszmajda/lid/commit/919c4b4bae2de396603e0b52794ddbb6c52dcf6a)) | 13 |
| 19 Oct | Coach eval 11 scored for the under-captured flag by whether the thin record gets its own finding, not by its tenet assertion ([a355424](https://github.com/jszmajda/lid/commit/a3554249be054dfe3dec49c4af4f546c5eb7c80f)) | 15 |
| 21 Oct | The 70% line, and reruns of runs a host cuts short ([80a7679](https://github.com/jszmajda/lid/commit/80a7679049ce4010a9d34086af3deaa0b1630ece)) | 19 |
| 12 Nov | A rerun cut short again is judged on the runs that finished ([6454735](https://github.com/jszmajda/lid/commit/64547352e9256bf9488e03dc95d060011b87954e)) | 26 |

The under-captured flag and the tendency category were defined with the first 13 results in hand, and the harness left the key hours later. The commit that changed coach eval 11's scoring says no flag changed.

The 70% line came after 19 had run. At 60%, none of those 19 results would have changed; at 80%, three would have, flagging GPT-6 Luna and listing DeepSeek V4.1 Flash and GLM 5.3 for the tendency. Two later results sit exactly on the line: Claude Sonnet 5's tendency and Kimi K3.1 Pro's under-captured flag each rest on a cell of 7 of 10, and at 60% neither would be listed. The rule for reruns cut short again was written the day MiniMax M3.1 Flash needed it: its tendency cells came out at 7 of 8 and 5 of 8, so it isn't listed, where counting the unfinished runs as misses would have listed it.

## How we tested

**Two skill trees.** The first 13 configurations ran on tree A, the skills at `1e7ef1a` with the flag list present but empty. That list told an untested model to treat every flag as applying, and its template named the tenet-conflict flag, so the skill itself could prompt the model to look for the judgment being measured. A phrase search of the first round's replies finds 16 runs where the model said so, 13 from DeepSeek V4.1 Flash and GLM 5.3 Flash (the list's notes count 17 of about 1,000); leaving them out changes no result. The rest ran on tree B, a copy of `919c4b4` with the list and every passage mentioning it removed by hand, checked by a search and a diff before the runs. Both manifests say 1.4.0, but neither is a release: A is from the day before 1.4.0 shipped, B the first commit of the change that became 1.4.1.

**Two harnesses.** The Claude models ran headless in Claude Code (`claude -p`; 2.1.296 on 10 October and 2.1.310 on 24 October, versions from the list, not the run records) at `--effort medium` on the maintainer's machine, reading the skill as a file. The others ran in opencode 1.18.32 in a locked-down container, through OpenRouter at medium reasoning effort, loading the skill with opencode's skill tool. The prompts also differed slightly: Claude's called it a Claude Code skill and said to ignore instruction files in parent directories; opencode's called it an agent skill and said to make any file changes itself (the records' README gives both). Claude Code allowed 25 minutes per turn, opencode 10 minutes per run, or 30 on 20 November with a 10-minute limit on silence.

**Blind grading.** A model session graded each run against the eval's assertions, seeing the project, the run's replies and changes, and a random ID, never the model's name. From round 3, each blind batch also held earlier runs with a known grade on the cell; 190 of these 192 planted controls came back as expected, and the other two, one lenient and one strict, turned on the same borderline reading of coach eval 10 and would change no result. Rounds 1 and 2, grading the 13 tree-A configurations, had no controls; round 2 regraded 8 round-1 runs, and 7 agreed. A batch whose grader drifted from the agreed reading was regraded. **Claude Sonnet 5.5 graded rounds 6 to 8,** the last 8 configurations; no surviving record names the grader of the first five.

The records' de-blinded grades and script recompute all 232 evidence cells in the list exactly.

## The first 29 configurations

The last column lists every cell at 70% or lower, including single misses that don't earn a flag. MiniMax, MiMo and Gemini 3.8 Flash had some runs cut short, so fewer than 80 were graded.

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

Dates are from the run records; the list dates a few rows one or two days earlier.

## What the snapshot showed

**Neither size nor release date sorted flagged models from unflagged ones.** By the list's own tiers, 5 of 11 small configurations are flagged, 2 of 8 mid and 2 of 10 large, and both 2025 releases are flagged, but every group holds both kinds: Claude Haiku 5.5 (small, October 2026) and Claude Opus 4.8 (May 2026) carry no flag, while Nemotron 3 Ultra (large, June 2026) and Kimi K3.1 Pro (large, October 2026) are flagged. Within a vendor's line, newer and larger models did no worse on the flags: Claude Haiku 4.5 missed what Haiku 5.5 catches, and GPT-5.6 Terra what GPT-6.1 Terra catches. The tendency is the exception, as LID's design notes: Claude Sonnet 5 leans toward offering docs where the older Sonnet 4.6 doesn't. So the list is keyed to exact configurations, and a model with no row may take the row of an earlier release in its line or a smaller model of its generation, never a newer or larger one.

**A pass can hide a deep miss on one project.** Claude Sonnet 5 raised the library-holds conflict in 3 of 10 runs and passes that flag. GPT-6 Luna offered the doc on core eval 3 in 1 of 10 runs and passes, as do Claude Sonnet 4.6 (3 of 10) and Hy4 (5 of 10). The list records these single-project misses, but they don't reach the person as flags.

**Rewording the skill didn't close the gap where we tried it.** Before the roster, LID's review skill gained an explicit check of designs against the project's tenets. Claude Sonnet 4.5 stayed at 0 of 10 on library holds; on another project its tenet finding rose from 3 to 7 of 10, while its finding on the thin decision record fell from 5 to 1. Wording isn't irrelevant: Claude Opus 4.8 went from 6 of 10 on an early version of library holds to 10 of 10 after the change, though other settings changed too.

**Thinking can move a result as much as the choice of model.** On one review project in Claude Code, Sonnet 4.5 caught the tenet conflict in 7 of 10 runs with its default thinking on and 0 of 10 with it off. That's one model on one project, not a comparison of effort levels. Nor does asking for an effort guarantee reasoning: Gemini 4 Argon's provider passes medium on as low, and it reasoned in 14 of its 80 evidence runs, passing every project anyway.

**Some models didn't follow the workflow.** MiniMax M3.1 Flash often ran past the phase stop until the 10-minute limit cut it off: in 13 of its 40 core runs and 8 of 30 reruns. Hy4 stopped after a one-line progress message, before doing any work, in 11 of its 40 core runs by the records (12 by the list); all its core eval 3 misses were such stalls, and its stalls on core 1 and 2 count as holding back. Gemini 3.8 Flash ended its first turn with no reply in 4 core runs. Muse Glimmer 30B and Nemotron 3 Ultra never offered a decision doc in a first turn, so their perfect holding-back scores show they don't offer one, not restraint.

**Some configurations raise conflicts that aren't there.** The library-holds project holds a decoy, a mechanism that costs something toward a goal without contradicting a tenet, and eval 15's restraint assertion fails when a report names any mechanism but the real one as working against a tenet or goal. 15 of the 29 configurations failed it at least once, or 16 counting eval 16, though the list's notes name only 11 for eval 15; one failure was a Gemini 4 Carbon reply of garbage tokens. Claude Opus 5, Claude Haiku 5.5 and GPT-6.1 Terra failed it in 9 of 10 runs while finding the real conflict every time. LID records this as an observation, not a tendency, because an extra finding asks the person to look twice, which costs less than a missed one.

**Spending varied widely.** 26 of the 29 configurations had a median under 10,000 reasoning tokens per run, which providers bill as output; Hy4's was 36,301. The harnesses count differently, so figures compare only roughly across them, and the records reproduce every median but those of the three Gemini 4 models whose token counts were lost.

## How sure we are

**Harness and vendor move together.** The two harnesses differ in how the skill reaches the model, the prompt, how reasoning is requested, the time limits and where the run happens, so a gap between Claude and the rest could come from any of those. The Claude runs, on the maintainer's machine outside a container, could see the host's identity; one wrote the maintainer's name into a decision doc.

The one direct check ran Claude Sonnet 4.5 in both harnesses on 28 September, on earlier skill text and two review projects. On eval 11 it compared them with no reasoning on either side: Claude Code's thinking was off, and OpenRouter didn't make Sonnet 4.5 reason (even high effort gave a median of 84 reasoning tokens per run). There the two matched on five of six assertions and scored 3 against 5 of 10 on the sixth, but three of the five sat at 0 or 10 of 10 on both sides, so only three could show a difference. On the early library-holds project both scored 0 of 10, with Claude Code's thinking on and opencode at its default. The check also found the runner cutting long lines from the skill, fixed before the roster. Nothing compares the harnesses at medium effort, where every result here was measured.

**The grader may favour Claude.** Where recorded, it was Claude Sonnet 5.5, itself one of the configurations. Blind grading and the controls don't rule out a Claude grader reading Claude's style more kindly, and no grader from another vendor has rechecked these grades.

**The method and the text changed during the runs.** Besides the method (see *Which parts came first*), the first 13 configurations ran on different skill text from the other 16, and none has been rerun on tree B, so each result is a claim about the text it ran on.

**Some records were lost.** The three Gemini 4 models' 20 November runs were made in a checkout since deleted. Their replies, changes and grades survive in the copies made for blind grading, so their results reproduce; their timing, token counts and transcripts don't.

**The models weren't sampled.** The maintainer chose them, such as the untested models in one week's OpenRouter top 10 and the three untested Gemini 4 models.

**No run went without LID.** Every run followed the skill, so these results say which judgments a model makes while following LID, not what LID adds.

## Where the details are

- **The list at this snapshot:** [capability-flags.md at commit 226b031](https://github.com/jszmajda/lid/blob/226b03185e1fa27a5438a31814ea8542fa8c4ff0/plugins/linked-intent-dev/skills/linked-intent-dev/references/capability-flags.md), the last commit to change its evidence, with every row's evidence, the single-project misses, and notes on each configuration's behaviour. The current list is [on main](https://github.com/jszmajda/lid/blob/main/plugins/linked-intent-dev/skills/linked-intent-dev/references/capability-flags.md).
- **The design, at the same commit:** the *Capability Flags* section of the [linked-intent-dev design](https://github.com/jszmajda/lid/blob/226b03185e1fa27a5438a31814ea8542fa8c4ff0/docs/intent/linked-intent-dev/linked-intent-dev-design.md), whose decisions table says why the line is 70%; the [core workflow's design](https://github.com/jszmajda/lid/blob/226b03185e1fa27a5438a31814ea8542fa8c4ff0/docs/intent/linked-intent-dev/core/core-design.md), on what the agent does with a flag; and the [alternate-model eval design](https://github.com/jszmajda/lid/blob/226b03185e1fa27a5438a31814ea8542fa8c4ff0/docs/intent/alt-model-evals/alt-model-evals-design.md), on the opencode runner.
- **The records:** [lid-research-records/capability-flags](https://github.com/jszmajda/lid-research-records/tree/main/capability-flags) holds every graded run's replies, changes, timing and de-blinded grade, one index row per batch, the blind keys and grades with their controls, the diff that made the stripped tree, and the noise study and harness comparison. Its README lists what was left out and why.
