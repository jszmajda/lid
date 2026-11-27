---
title: "Mapping a codebase LID didn't build: a first look"
date: 2026-11-27
status: pilot
summary: "Pilot runs of LID's /map-codebase on openGym, one model, no owner. Three usable maps cost $27 to $54 and wrote 815 to 1,195 requirements each, but none read its own survey in full, and each linked both sides of only 1 of 13 known ties between components. A lead to study, not a measurement."
tested:
  lid: "1.4.6, linked-intent-dev and arrow-maintenance plugins"
  agent: "Claude Code 2.1.323"
  model: "Claude Sonnet 5.5, medium effort, 1M-token context window"
records: "https://github.com/jszmajda/lid-research-records/tree/main/cost-eval/map-codebase-opengym"
---

Every number here comes from four pilot runs of LID's `/map-codebase` skill on one project, openGym, in Claude Code 2.1.323 on Claude Sonnet 5.5 at medium effort, with nobody in the owner's seat. We set the first run aside, so most results rest on three maps. That's enough to see a pattern worth studying, and not enough to say how often it happens, or whether it happens with other models or with an owner present. We're publishing it as a thread to pick up later.

## Why we looked

Most of what we know about LID comes from projects it built from the start. Many people would first meet it in a codebase that already exists, and `/map-codebase`, the part of LID for that, is the part we've studied least. It reads the code and writes LID's documents for it: a high-level design, then a design doc and requirements for each segment of the system.

Our [first report](https://linked-intent.dev/research/first-results/) started LID's runs on openGym from these maps and counted them as a one-time cost. This report looks at the maps themselves.

## What the skill asks for

[The skill](https://github.com/jszmajda/lid/blob/main/plugins/arrow-maintenance/skills/map-codebase/SKILL.md) has the agent read every file in scope, "Not a sample", usually through parallel workers that each write a survey of their share. From that survey it proposes several ways to divide the code, and the owner picks one, then a level of detail, then approves the segments. Only then does it write each segment's documents, stopping after each for the owner. It's built around an owner who reads and steers at every stop. A longer [reference](https://github.com/jszmajda/lid/blob/main/plugins/arrow-maintenance/skills/map-codebase/references/brownfield-bootstrap.md) expands on each step.

## How we ran it

openGym is an open-source fitness app with a Node API, a React app that's also the phone app, native shells, watch apps and an MCP server. It was created after the model's training cutoff, and LID didn't build it. We pinned one commit, which by our count has 936 source files that aren't tests.

Each map was one session with both of LID's plugins loaded, GitHub blocked and web tools turned off. The prompt was `/map-codebase` plus one instruction: no owner is available, so wherever the skill would ask the owner, choose the most reasonable answer, note the question and the choice, and carry on ([the harness](https://github.com/jszmajda/lid/blob/main/docs/research/cost-eval/harness/opengym_map.py)).

**Why the first draw was set aside.** For the first draw, the harness, the study's code that sets up each run, left openGym's exercise media out of the copy the agent mapped, believing no test needed them. One of the project's test suites does, and the map wrote the missing media down as a fact about openGym, in one requirement and five other lines. A setting of ours had leaked into the map, so it no longer showed what a real adopter would get. The next three draws ran on the whole tree, one for each set of LID runs, so that no single map decided every LID run ([decisions](https://github.com/jszmajda/lid/blob/main/docs/research/cost-eval/decisions.md)).

Afterwards we counted what each map wrote and which source files it named, and checked whether it recorded 13 dependencies between components that the study had mined beforehand: rules that one component holds and another relies on. The mapping sessions never saw that list, and we don't publish it, because later runs reuse it.

## What we saw

| | Draw 2 | Draw 3 | Draw 4 |
|---|---|---|---|
| Time | 19.6 min | 20.7 min | 12.0 min |
| Cost at list prices | $53.64 | $45.37 | $26.53 |
| Tokens | 152.5M | 128.8M | 58.9M |
| Subagents it started | 50 | 58 | 46 |
| Segments | 19 | 14 | 22 |
| Requirements written | 1,195 | 815 | 878 |
| Requirements per segment, median | 61 | 59 | 40 |
| Range it told its writers to aim for | 25 to 60 | 25 to 60 | 15 to 40 |
| Read its own survey before choosing segments | no | in part | in part |
| Source files named nowhere in the map, of 936 | 26 to 112 | 332 to 445 | 184 to 342 |
| Dependencies, of 13, with both sides recorded and linked | 1 | 1 | 1 |
| Recorded on one side only | 10 | 8 | 7 |
| Not recorded | 1 | 4 | 4 |

About nine in ten tokens were cache reads. Draw 2 also recorded one dependency on one side while noting that its logic exists twice, and draw 4 recorded both sides of one more, joined only by a shared term. The [records](https://github.com/jszmajda/lid-research-records/tree/main/cost-eval/map-codebase-opengym) give every row for all four draws.

**The same prompt on the same tree gave quite different maps.** Cost varied by a factor of two, tokens by two and a half, and requirements by about half.

**None read its own survey in full before choosing segments.** Before choosing, one session ran only a line count of its survey files, one printed about 45 lines from four of its reports, and one printed a short section of each. In the set-aside draw, the session opened no survey file at all.

**Each set its own cap on requirements, which the skill doesn't set.** The skill gives no number, so each session gave its writers a range, and in two of the three the writers went past it. In the set-aside draw, every spec file stopped at 58 to 60 whatever the segment's size, and at least six writers deleted requirements they had drafted, to fit. A map's count of requirements says as much about its cap as about the code.

**Workers skimmed, and the sessions let it pass.** The skill says to read every file, and makes sampling the owner's call. In the set-aside draw, most workers read only the headers, imports and exports of large files, and one reported "No source file was read end to end". The session noted each case and carried on. The other three sessions also accepted sampled reading, and two of them logged that they had.

**No draw added `@spec` comments,** LID's links from code to the requirement it implements. The skill's main file has no step for them, and its reference has one.

**Coverage of the source files varied most.** Naming a file is a crude test, so each draw gets a range: the higher figure needs a file's full name to appear in the map, and the lower one also accepts its name without the extension, which ordinary words sometimes match. Draw 2 named nearly every file, because the session checked its own coverage after drafting, found 339 files that no segment claimed, and assigned them. Draw 3 chose to leave five areas of the app unmapped, and said so. The skill asks for neither. A file that no segment names gives the next change no design doc to find.

**The maps recorded rules inside components, and rarely the ties between them.** Each draw recorded both sides of exactly one of the 13 dependencies with a line linking them, and seven to ten on one side only, with nothing pointing to the other. Our first report found that LID's documents helped an agent keep a dependency when they linked the two parts, and hurt when they didn't ([#135](https://github.com/jszmajda/lid/issues/135)). On openGym that didn't show up as stops at segment boundaries, because each map put a feature's API and app code in the same segment.

## What the review found in the skill itself

Before the first draw was set aside, another model, Claude Fable, reviewed it closely against the skill's text and the run's records, without seeing the list of dependencies. The review's last section is about the skill itself: eleven places where the skill's own documents contradict each other or leave a gap. Those come from reading the skill's files side by side, and the run only showed where they bite, so they don't depend on the leak. The run's own behaviour, from the unread survey to the invented cap, turned up again in the three draws on the whole tree.

We rechecked each finding against LID 1.4.6, whose skill text is unchanged on `main`. Ten hold:

- **The main file and its reference describe different maps** in six places: whether to add `@spec` comments, whether the high-level design is a skeleton or a full synthesis, which design-doc template to use, the order the documents are written in, a segment's starting status, and what the `[D]` marker means. The reference calls the main file canonical, but an agent reads both. In the set-aside draw, writing the segment documents before the high-level design left eight lines saying it didn't exist.
- **Reading the survey is stated at the end of Phase 1,** and Phase 2, where the segments are chosen, doesn't repeat it.
- **"Aborting at any STOP leaves nothing written to disk" isn't true.** The survey files, and each document in Phase 5, are written before the stop that follows them.
- **A worker whose share doesn't fit has no way out.** Its template says "Read every file. Do not skip." and gives it no way to stop and report, and the main agent has no instruction for a worker that says it sampled.
- **Nothing says how many requirements a segment should have,** the gap each session filled with its own cap.

These are filed as [#133](https://github.com/jszmajda/lid/issues/133) and [#134](https://github.com/jszmajda/lid/issues/134). The eleventh finding, two links in the main file the review took for broken, doesn't hold: they resolve correctly.

## What it suggests

These are directions from three maps of one project.

- **The steps that take the most reading are the ones that got cut.** Every draw thinned the survey, the reading of it, or both. Where the skill was loose or contradicted itself, each draw went its own way.
- **One map is a sample.** Three draws on the same tree differed twofold in cost and by hundreds of files in what they named. A study that starts from one map, or a person judging one, should expect a second run to differ.
- **A coverage check may be cheap and effective.** The one session that checked which files it had missed went on to name nearly all of them. That's a single draw.

## What we don't know

- **What an owner changes.** Nobody read or steered these maps. An owner would at least have made the agent build real proposals, with clusters and file counts, which forces it to read its survey, and one who knows the code might name the ties between parts. We haven't tested either.
- **Other models and settings.** A stronger model, or a higher effort, may follow the steps more closely.
- **Other codebases.** openGym's own agent instructions and architecture notes are unusually thorough for an existing project, and a less documented codebase may map differently.
- **Whether a better map changes the outcome.** In the openGym change we looked at most closely, the agent's own search found the right code, not the map. We didn't vary the maps' quality.
- **How good the requirements are.** We counted them, but didn't check a sample against the code.
- **What a map is worth over a project's life.** Nothing here tests that.

## What a deeper study would test

- **With an owner and without,** measuring whether the survey gets read, how many files go unnamed, and how many ties get linked.
- **Across models and effort levels,** with several draws each, to separate what the skill does from what the model does.
- **On more codebases,** of different sizes and documentation, with dependencies mined before mapping as here.
- **Before and after [#133](https://github.com/jszmajda/lid/issues/133) and [#134](https://github.com/jszmajda/lid/issues/134) are fixed,** to see whether a consistent skill is followed more closely.
- **A better yardstick for a map:** which segment owns each file, read from the map's index rather than matched by name, and a sample of requirements checked against the code.
- **Whether a map's quality reaches the changes made from it:** the same changes, started from maps that do and don't link a dependency's two sides.
- **With the analysis fixed in advance,** so the results count as more than a pilot.

## How sure we are

This is pilot evidence: three usable maps and one set aside, from one model on one project, with measures we chose after seeing the maps. We judged each dependency by reading each map for it. The review of the skill was one model's reading, which we rechecked once, and it was wrong on one of eleven points. The source-file counts rest on a crude name match. Dollar figures are what the tokens would cost at Anthropic's published API prices; the runs used a subscription.

## Where the details are

The [records](https://github.com/jszmajda/lid-research-records/tree/main/cost-eval/map-codebase-opengym) hold a counts-only table of all four draws, the review's findings set against the skill's text, and the script that counted source files. The maps stay private, because they're derived from openGym's AGPL-licensed code and the study keeps everything derived from it local. The study's [notebook](https://github.com/jszmajda/lid/tree/main/docs/research/cost-eval) has the decisions, the dated log and the harness.
