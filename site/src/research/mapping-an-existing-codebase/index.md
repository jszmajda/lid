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

Every number here comes from four pilot runs of LID's `/map-codebase` skill on one project, openGym, in Claude Code 2.1.323 on Claude Sonnet 5.5 at medium effort, with nobody in the owner's seat. We call each run a draw: one session mapping the whole project from the same prompt. We set the first aside, so most results rest on three maps: enough to see a pattern worth studying, not to say how often it happens. We're publishing it as a thread to pick up later.

## Why we looked

Most of what we know about LID comes from projects it built, but many people would first meet it in an existing codebase, through `/map-codebase`, the part of LID we've studied least. Our [first report](https://linked-intent.dev/research/first-results/) started LID's runs on openGym from these maps and counted them as a one-time cost; this report looks at the maps themselves.

## What the skill asks for

[The skill](https://github.com/jszmajda/lid/blob/main/plugins/arrow-maintenance/skills/map-codebase/SKILL.md) has the agent read every file in scope, "Not a sample", usually through parallel workers that each write a survey of their share. From the survey it proposes several ways to divide the code; the owner picks one, then a level of detail, then approves the segments. Only then does it write LID's documents, a high-level design and each segment's design doc and requirements, stopping after each segment for the owner. Every session here handed each segment's writing to a subagent, which we call a writer. A longer [reference](https://github.com/jszmajda/lid/blob/main/plugins/arrow-maintenance/skills/map-codebase/references/brownfield-bootstrap.md) expands on each step.

## How we ran it

openGym is an open-source fitness app with a Node API, a React app that's also the phone app, native shells, watch apps and an MCP server, created after the model's training cutoff. At the commit we pinned, it has 936 source files by our count: non-test files in its six programming languages, outside its exercise catalogue.

Each map was one session with both LID plugins loaded, GitHub blocked and web tools off. The prompt was `/map-codebase` plus one instruction: no owner is available, so wherever the skill would ask the owner, choose the most reasonable answer, note the question and the choice, and carry on ([the harness](https://github.com/jszmajda/lid/blob/main/docs/research/cost-eval/harness/opengym_map.py)).

**Why the first draw was set aside.** For that draw, the harness, the study's code that sets up each run, left openGym's exercise media out of the agent's copy, believing no test needed them. One test suite does, and the map recorded the missing media as a fact about openGym, in one requirement and five other lines: a setting of ours had leaked into the map, so it no longer showed what a real adopter would get. The next three draws ran on the whole tree, one for each set of LID's runs on openGym, so that no single map decided every LID run ([decisions](https://github.com/jszmajda/lid/blob/main/docs/research/cost-eval/decisions.md)). Our first report counts only these three, which is why it says we ran the skill three times.

Afterwards we counted what each map wrote and which source files it named, and checked whether it recorded 13 dependencies between components that we mined beforehand: rules one component holds and another relies on. The mapping sessions never saw the list, and we don't publish it, because later runs reuse it.

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
| Source files named nowhere in the map, of 936 | 26 to 130 | 332 to 472 | 187 to 355 |
| Dependencies, of 13, with both sides recorded and linked | 1 | 1 | 1 |
| Recorded on one side only | 10 | 8 | 7 |
| Recorded another way | 1 | 0 | 1 |
| Not recorded | 1 | 4 | 4 |

About nine in ten tokens were cache reads. "Recorded another way" is one side noted with its logic said to exist twice (draw 2), and both sides joined only by a shared term (draw 4). The [records](https://github.com/jszmajda/lid-research-records/tree/main/cost-eval/map-codebase-opengym) give every row for all four draws.

**The same prompt on the same tree gave quite different maps.** Cost varied twofold, tokens two and a half times, and requirements by about half.

**None read its own survey in full before choosing segments.** One session only counted the lines in its survey files, one printed about 45 lines from four of its reports, and one a short section of each. In the set-aside draw, the session opened none at all.

**Each set its own cap on requirements.** The skill gives no number, so each session gave its writers a range, and in two of three the writers went past it. In the set-aside draw, every spec file stopped at 58 to 60 whatever the segment's size, and at least six writers deleted drafted requirements to fit. So a map's count of requirements says as much about its cap as about the code.

**Workers skimmed in every draw, and only one session went back in earnest.** The skill makes sampling the owner's call, but in each draw survey workers' closing messages said they had read some code files only by headers, imports and exports, an outline or a skim: 10 of 11 workers in the set-aside draw (one reported "No source file was read end to end"), and 7 of 31, 17 of 44 and 16 of 24 in the others, not counting statements only about tests or data. Draw 2 sent 11 more workers to fill gaps or read deeper, and draw 3 sent one, but draw 2 still told its writers the survey had been partly skimmed. Otherwise the sessions noted the thin reports and carried on; two logged that they had.

**Coverage of the source files varied most.** Naming a file is a crude test, so each draw gets two rough figures, neither a bound: the higher counts a file as named only when its full file name appears in the map, and the lower also accepts the name without its extension. Both over-credit, because 129 of the 936 files share a name with another, and the lower also matches ordinary words; both under-credit a file covered only by a folder or pattern. Draw 2 named far more files because, after drafting, it checked its coverage, found 339 files no segment claimed, and assigned them. Draw 3 chose to leave five areas of the app unmapped, and said so. The skill asks for neither: it has no coverage check, and no step for leaving areas out of a whole-project mapping. A file no segment names gives the next change no design doc to find.

**The maps recorded rules inside components, and rarely the ties between them.** Each draw linked both sides of just one of the 13 dependencies, and recorded seven to ten on one side only, with nothing pointing to the other. Our first report found that LID's documents helped an agent keep a dependency when they linked the two parts, and hurt when they didn't: on another project, LID agents stopped searching at the edge of their segment when nothing pointed across ([#135](https://github.com/jszmajda/lid/issues/135)). That didn't happen on openGym, because each map put a feature's API and app code in one segment.

## What the review found in the skill itself

Before the first draw was set aside, another model, Claude Fable, reviewed it against the skill's text and the run's records, without seeing the list of dependencies, and ended with eleven places where the skill's documents contradict each other or leave a gap. Those come from reading the skill's files side by side, so they don't depend on the leak, and the behaviour they explain, from the unread survey to the invented cap, recurred in the three draws on the whole tree.

We rechecked each against LID 1.4.6, whose skill text is unchanged on `main`. Ten hold:

- **The main file and its reference describe different maps** in six places: whether to add `@spec` comments, LID's links from code to requirements (no draw added any), whether the high-level design is a skeleton or a full synthesis, which design-doc template to use, the order the documents are written in, a segment's starting status, and what the `[D]` status marker means (a deliberate non-feature in one, deferred work in the other). The reference calls the main file canonical, but an agent reads both. In the set-aside draw, writing segment documents before the high-level design left eight lines saying it didn't exist.
- **Reading the survey is asked for at the end of Phase 1** (the survey), and Phase 2 (proposing ways to divide the code) doesn't repeat it.
- **"Aborting at any STOP leaves nothing written to disk" isn't true.** The survey files, and each document in Phase 5, are written before the stop that follows them.
- **A worker whose share doesn't fit has no way out.** Its template says "Read every file. Do not skip." and gives no way to stop and report, and the main agent has no instruction for a worker that says it sampled.
- **Nothing says how many requirements a segment should have,** the gap each session filled with its own cap.

These are filed as [#133](https://github.com/jszmajda/lid/issues/133) and [#134](https://github.com/jszmajda/lid/issues/134). The eleventh finding doesn't hold: the two links in the main file that the review took for broken resolve correctly.

## What it suggests

- **The steps that take the most reading got cut.** Every draw thinned the survey, the reading of it, or both, and where the skill was loose or contradicted itself, each draw went its own way.
- **One map is a sample.** Expect a second run on the same tree to differ as much as these did.
- **A coverage check may help.** It worked in draw 2, but that was also the costliest draw, the check's own cost can't be separated out, and it's one draw.

## What we don't know

- **What an owner changes.** An owner would probably have made the agent build real proposals, with clusters and file counts, pushing it toward its survey, and one who knows the code might name the ties between parts. Neither is tested.
- **Other models and settings.** A stronger model or higher effort may follow the steps more closely.
- **Other codebases.** openGym's agent instructions and architecture notes are unusually thorough for an existing project; a less documented codebase may map differently.
- **Whether a better map changes the outcome.** In the openGym change we looked at most closely, the agent's own search found the right code, not the map. We didn't vary the maps' quality.
- **How good the requirements are.** We counted them but didn't check a sample against the code.
- **What a map is worth over a project's life,** which nothing here tests.

## What a deeper study would test

- **With an owner and without,** measuring whether the survey gets read, how many files go unnamed, and how many ties get linked.
- **Across models and effort levels,** several draws each, to separate the skill from the model.
- **On more codebases,** with dependencies mined before mapping.
- **Before and after [#133](https://github.com/jszmajda/lid/issues/133) and [#134](https://github.com/jszmajda/lid/issues/134) are fixed.**
- **A better yardstick:** which segment owns each file, read from the map's index, and a sample of requirements checked against the code.
- **Whether a map's quality reaches the changes made from it,** starting the same changes from maps that do and don't link a dependency's two sides.
- **With the analysis fixed in advance,** so the results count as more than a pilot.

## How sure we are

This is pilot evidence: three usable maps of one project, from one model, with measures we chose after seeing them. A model session wrote the dependency verdicts, reading each map for each dependency. The skill review was one model's reading, wrong on one of eleven points. The file counts rest on a crude name match. Dollar figures are what the tokens would cost at Anthropic's published API prices; the runs used a subscription.

## Where the details are

The [records](https://github.com/jszmajda/lid-research-records/tree/main/cost-eval/map-codebase-opengym) hold the counts, the review's findings set against the skill's text, and the counting script. The maps stay private: they're derived from openGym's AGPL-licensed code, and the study keeps everything derived from it local. The study's [notebook](https://github.com/jszmajda/lid/tree/main/docs/research/cost-eval) has the decisions, the dated log and the harness.
