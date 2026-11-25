---
title: "What LID costs, and what it buys: first results"
date: 2026-11-24
status: pilot
summary: "Pilot runs on four projects: LID cost 3.3 to 5.8 times as much per change as a bare agent and showed the owner 5 to 12 times as many words. It was ahead on building what was asked, level on not breaking other parts of a system, and untested over a project's long life."
tested:
  lid: "1.4.6"
  agent: "Claude Code 2.1.323"
  model: "Claude Sonnet 5.5, medium effort"
records: "https://github.com/jszmajda/lid/tree/main/docs/research/cost-eval"
---

Every number here comes from pilot runs of LID 1.4.6, in Claude Code 2.1.323 on Claude Sonnet 5.5. The cost ratios came out much the same on every project. The differences in what each approach built show which way things point, but they rest on three runs or fewer per comparison, so none of them is a precise measurement.

## The question

People who try LID usually ask two things first. How much more does it cost than just asking an agent to make the change? And does it get them software that does what they meant more often than the plain agent would?

LID makes the agent write a design, then requirements, then tests, before it writes code. In its full workflow, which we call LID Full, it stops after each of those steps to show the owner what it wrote. All of that costs tokens and the owner's reading time. We wanted to know what that buys.

We compared a bare agent, which gets the owner's request and nothing else, with the same agent following LID Full. On two projects we also tried a cheaper middle ground:

- **On BenchTime,** "cheap discipline": the agent plans before it codes, writes tests, and keeps a notes file.
- **On ReleaseDesk,** a "checklist": a few lines in the agent's instruction file asking it to keep a list of the system's requirements and to ask the owner about anything unsettled.

We haven't yet compared LID with the other spec-driven systems people ask about, such as OpenSpec, Spec Kit or BMAD.

## The short answer

| | What we saw |
|---|---|
| Agent cost | LID cost 3.3 to 5.8 times as much as a bare agent per change, on every project, and the gap didn't narrow as a project aged. On a codebase LID didn't build, mapping it first is a one-time cost of about $27 to $54 at list prices. |
| Owner's reading | In a typical change, and across whole small projects, LID showed the owner 5 to 12 times as many words, assuming the owner reads all of it. |
| Building what was asked | LID was ahead on openGym (36 of 36 changes fully built, against 33) and on BenchTime, level on Clowder, and behind on ReleaseDesk's stated requirements. |
| Requirements the owner never stated | On ReleaseDesk, the one project with room to show it, LID met all 9 and the bare agent 6, mostly because LID asked. |
| Not breaking another part of the system | No overall difference. LID's documents helped when they linked the two parts, and hurt when they didn't. |
| Fixing the bare agent's misses afterwards | Much cheaper in agent cost than LID's extra cost, once each miss was reported. Some misses survived the repair. |
| Whether LID pays off over a project's life | Not tested. The projects here are small, or were changed from a single snapshot. |

## What the results add up to

**LID's clearest benefit is getting what the owner meant.** The LID agent asked about what the owner left unsaid, and it caught misreadings of a request before writing code. That showed up on every project with room for it, and it's the benefit the evidence supports best.

**Linking intent across the parts of a system matters, in both directions.** Where LID's documents said which other part of the system relied on a rule, the LID agent kept that part working. Where they didn't, LID's boundaries between parts told the agent its work was done, and it did worse than the bare agent. That points at something specific in LID to fix, more than at the method as a whole.

**The owner's reading is the cost that matters most.** LID's extra agent cost was about $0.40 to $0.90 per change at list prices, which is small next to a person's time. Five to twelve times as much to read is not small, and our simulated owner caught far fewer problems in long documents than in short messages.

**Whether LID pays for itself over a project's life is still open.** The benefit people usually describe builds up over months, and nothing here tested that.

## Who this suggests should try LID

On this evidence, LID is most worth trying when your requests leave a lot unsaid and you're willing to read designs and answer questions, because that's where it helped. It hasn't yet been shown to pay on small projects where every requirement is stated up front, or to protect one part of a system from changes made in another. If you try it, how much you read is the biggest cost you control: the conversation and the design documents carry most of what you'd want to check.

## One change, from both sides

On openGym, the owner, a coach who runs their own copy of the app for a training group, asked for a join code that lets someone sign up to the gym and stays valid for 90 days. openGym already had two kinds of code: an admin invitation to the whole server, and a code a gym's lead shares with their members. The owner meant the second.

- **Two of the three bare runs searched for "invite",** found the admin invitation, and built that. They told the owner the change was done, and it was the wrong change. Each cost about $0.27 to $0.43 and showed the owner about 14,000 words. When we reported the miss, the repairs built the same wrong thing again. The third bare run searched for "join code", found the gym's code, and built it correctly.
- **Two of the three LID runs also read the request as the admin invitation at first.** LID's first step has the agent search the code again before it writes any design, and that search turned up the gym's code. One run told the owner, "My earlier answer was about the wrong code," and both built the right one. The third found the gym's code straight away. All three built the change correctly, at about $0.47 to $0.81 each, and showed the owner between 8,500 and 24,000 words.

In this case, LID's extra step bought a correct change for a few tens of cents more and several thousand more words to read. The map of the codebase wasn't what helped: one of the two maps didn't mention the gym's code at all. The agent's own search did.

## How we tested

**The executor.** Claude Sonnet 5.5 at medium reasoning effort made every change, whichever way of working it followed. Opus 5.5 ran only in two checks of how well a bare agent could do at its best. Every run that followed LID used LID 1.4.6, in Claude Code 2.1.323, and on openGym both of LID's plugins, because its map uses the second plugin's navigation files. The notebook records the versions for every run.

**The owner.** A real person can't sit through hundreds of runs, so a model plays the owner. The study wrote the owner's real intent down in advance as a list of requirements. The owner states some of them in its request. It shares others only when the agent asks, and objects to others only when the agent proposes something that contradicts them. The owner is an imperfect reader on purpose: it misses more as it reads more, and something the agent shows it can remind it of a requirement it forgot to mention. The settings for that come from published research on attention and memory ([owner-model-research.md](https://github.com/jszmajda/lid/blob/main/docs/research/cost-eval/owner-model-research.md)). The owner never reads code.

**The projects.**

- **BenchTime**, a small reservation service, built from a short brief and then changed ten times, three times over for each approach.
- **ReleaseDesk**, a small release-approval tool, grown the same way through twenty changes, once for each approach.
- **Clowder**, a Rust terminal game with about 270,000 tokens of non-test source, which LID's maintainer built with LID. We ran two experiments on it. The first was a pilot, in which each approach made twelve changes once. The second made twelve different changes, three times each: eight were asked of one half of the code but had to respect a rule in the other half, and four stayed within one half.
- **openGym**, an open-source fitness app with a Node API, a React app, watch apps and an MCP server. Its first commit came after the model's training cutoff, and LID didn't build it. Each approach made twelve changes, three times each, chosen the same way as Clowder's second set.

On the last two projects, every run of a change started from the same code, so nothing built up from one change to the next.

**Grading.** Each requirement has one or more probes. A probe is a small test written against whatever the agent built: it sets up a situation and checks what happens. A model runs the probes in a container, and a second model judges the result. Before counting anything on the last two projects, we checked the grading both ways: the untouched code had to fail every new requirement, and a correct build of every change had to pass every one.

**Cost.** The agents ran on a Claude subscription. Dollar figures are what the same tokens would cost at Anthropic's published API prices. The study's real out-of-pocket spend was about $18, paid to other model families that drafted and reviewed the test material.

## What it costs

### Agent cost

| Project | Bare agent | LID Full | Ratio |
|---|---|---|---|
| BenchTime, the build and ten changes | $2.53 | $11.17 | 4.4× |
| ReleaseDesk, the build and twenty changes | $4.00 | $23.20 | 5.8× |
| Clowder, per change | $0.14 | $0.51 | 3.6× |
| openGym, per change | $0.28 | $0.91 | 3.3× |

The cheaper middle grounds cost little more than the bare agent: the checklist $4.58 on ReleaseDesk, and cheap discipline $4.54 on BenchTime.

On BenchTime we also made the same small request after changes 0, 3, 6 and 9. LID's extra cost for it stayed the same as the project aged. We had expected LID's written intent to make later changes cheaper; on projects this size, later changes cost LID as much as early ones.

**Mapping an existing codebase.** LID's way into a codebase it didn't build is `/map-codebase`, which surveys the code and writes LID's documents for it. We ran it three times on openGym, once for each set of LID runs. Each map took 12 to 21 minutes and 59 to 153 million tokens, about $27 to $54 at list prices, and wrote 815 to 1,195 requirements. That's a one-time cost. Spread over our twelve changes, it would add about $3.50 per change; over a project's life, it would spread much further.

### The owner's reading

| Project | Bare agent | LID Full |
|---|---|---|
| BenchTime, the build and ten changes | 5,200 words | 53,400 words |
| ReleaseDesk, the build and twenty changes | 8,200 words (0.6 hours) | 94,900 words (6.6 hours) |
| Clowder, per change, median (mean) | 312 (570) words | 1,639 (16,253) words |
| openGym, per change, median (mean) | 2,336 (9,903) words | 13,117 (24,016) words |

On Clowder and openGym the mean is far above the median, because some of LID's stops showed the owner whole design documents of tens of thousands of words. In the Clowder pilot, LID showed the owner about 195,000 words across twelve changes, against the bare agent's 7,700.

These counts assume the owner reads everything LID shows, and most people don't read every requirement and test. On BenchTime, an owner who read only the conversation would read about half as much, and one who also read the design documents about four-fifths as much. We estimated those; we didn't run them, and every result here comes from an owner who reads everything.

The extra reading has a cost beyond time. Our owner, like a real one, misses more as it reads more. On BenchTime, each run had about four places where what the agent showed the owner contradicted one of the owner's requirements. The owner objected to 2.7 of 4.3 of them in the bare agent's short messages, and to 0.3 of 4.0 in LID's long documents.

## What it buys

### Small projects built from scratch

On BenchTime, every approach met most of the owner's requirements, so there wasn't much room to separate them. With an owner that catches every contradiction, the shares met after ten changes were 92% for the bare agent, 89% for cheap discipline and 96% for LID. With the imperfect owner, they were 95%, 93% and 97%. LID scored highest both times, but its three runs overlapped the bare agent's. The two sets were graded with different versions of the probes, so they shouldn't be compared with each other.

ReleaseDesk had more room, because more of its requirements were left unstated. We grew it through twenty changes once per approach:

| At change 20 | Bare agent | Checklist | LID Full |
|---|---|---|---|
| Stated requirements met | 53 of 54 | 53 of 54 | 50 of 54 |
| Unstated requirements met | 6 of 9 | 7 of 9 | 9 of 9 |
| Requirements that worked earlier and broke by change 20 | 0 of 49 | 0 of 48 | 2 of 48 |

LID met every unstated requirement, and the bare agent two in three. That's the largest gap in the study, but it's one run per approach, and LID's figure was 8 of 9 until we fixed a fault in one probe. Most of the gap comes from requirements that only the LID agent's owner disclosed, because the LID agent asked more questions. When the owner had told an agent about a requirement, that agent met it, whichever approach it followed. LID was behind on stated requirements, and we haven't yet looked at why.

### Large projects

| | Bare agent | LID Full |
|---|---|---|
| Clowder: new requirements met | 69 of 72 | 70 of 72 |
| openGym: changes with every stated requirement met | 33 of 36 | 36 of 36 |
| openGym: new requirements met | 95 of 109 | 103 of 110 |

On openGym, one of the bare agent's requirements couldn't be judged, so its total is one lower. Most of the bare agent's misses were the join-code mix-up described above.

The Clowder pilot was a different experiment. At a 1M-token context window, LID met 97% of the requirements and the bare agent 79%. At a 200,000-token window they were level, at 84% and 85%. Each of those four figures comes from a single run.

### Not breaking another part of the system

Eight of the twelve changes in Clowder's second set, and eight on openGym, were asked of one part of the code but had to respect a rule in another part. For example, the game's core decides how saved absence reports are kept, and the interface reads them to show a banner. A change to how reports are kept can quietly break the banner. We wanted to know whether LID's written intent helps an agent find and respect the other side.

| | Bare agent | LID Full |
|---|---|---|
| Clowder: the other part kept working | 18 of 24 runs | 19 of 24 runs |
| openGym: runs that built the change but broke the other part | 7 of 33 | 6 of 35 |

The openGym totals count only runs that built the change and in which the other part was exercised. Overall there was no difference, because LID's documents helped on some changes and hurt on others.

## When LID's documents helped, and when they hurt

**When the documents linked the two parts, the LID agent kept the dependency.** On the absence-report change, LID's requirements said which part of the interface reads the saved reports. All three LID runs found it and kept the banner working; none of the three bare runs did. Part of LID's help came from a reference to that requirement in the interface code, which the bare agent's copy didn't have, because we removed every requirement reference from it. When we then reported the miss, one of the bare agent's three repairs fixed it.

**When nothing linked them, LID's boundaries ended the search.** LID divides a project's intent into segments, one for each part of the system. Inside a segment, the agent updates everything a change affects without asking; when a change would cross into another segment, it stops and asks the owner first. On three of Clowder's changes, the interface relied on the rule being changed, and for two of them the interface's requirements restated it. Nothing on the core side pointed there. The LID agents read the design documents and the core code, concluded that the change stayed inside the segment they were editing, and stopped. They broke the interface in 5 of 9 runs. The bare agent, with no segments to respect, searched the whole codebase, found the interface's code, and broke it in 2 of 9. One LID run did notice the interface during its review and asked the owner whether to change it, but the owner knew no code and said it had no preference, so the agent left it alone. We've filed this gap as an issue for LID ([#135](https://github.com/jszmajda/lid/issues/135)).

**openGym's hardest dependency went the same way for both.** Only one of openGym's changes had a dependency that a text search from the edited side wouldn't find. None of the three maps recorded it, and each approach kept it in one of three runs. On openGym the LID agents didn't stop at segment boundaries, because each map put a feature's API and app code in the same segment. Their misses came from reading only part of a segment.

**The owner's reviews can't catch these misses.** The owner reviews designs and requirements and never reads code, so a dependency broken in code passes its review unless a document mentions it.

## Fixing misses afterwards

If the bare agent is cheaper and misses more, one plan is to use the bare agent and fix its misses when someone notices them. We tested that by reporting each miss to the agent as the owner would, then letting the agent repair the code.

| | Bare agent | LID Full |
|---|---|---|
| ReleaseDesk: LID's extra agent cost by change 20 | | $19.20 |
| ReleaseDesk: cost to repair every miss | $0.39 | none missed |
| Clowder: changes plus repairs of every real miss | about $6.70 | about $21 |
| openGym: changes plus repairs | $12.67 | $35.12, plus the one-time mapping |
| openGym: misses fixed by one repair | 10 of 14 | 7 of 7 |

In agent dollars, repairing the bare agent's misses cost far less than LID's extra cost on every project. That comparison leaves out three things:

- **Some misses weren't fixed.** The bare agent's join-code misses survived their repairs, and two of its three absence-report misses did.
- **Some repairs broke something else.** On ReleaseDesk, one of three bare repairs and one of two checklist repairs broke another rule, and on Clowder three bare repairs did.
- **Every miss had to be noticed first.** We reported each miss to the agent the moment it happened. A real owner has to notice the problem, which may take weeks, while the software is wrong in the meantime. We didn't price that, or the owner's time to report it.

Whether LID's extra cost pays for itself depends on those three things, which this study doesn't yet measure, and on the owner's reading time, which counts against LID.

## What this doesn't show

**What happens over a project's life.** People who like LID, including its maintainer, usually describe a benefit that builds up over months. The written intent stays true as the project changes, so the hundredth change is still easy to make safely, and coming back after a break doesn't mean rediscovering why things are the way they are. Runs that each start from the same code can't show that, because nothing builds up between them. The one test we designed for it, growing a project through forty changes with planned changes of direction, stopped after twenty, because the project stayed small enough for a bare agent to read in full every time. So these results neither support nor contradict the long-horizon benefit; they leave it untested. One thing we did see may matter there: by change 20 on ReleaseDesk, the bare agent kept about 85% of its code in one file, while the LID agent's code was split across 16 modules.

**Whether LID helps the owner think.** Our owner's intent was fixed in advance. A real owner often works out what they want while writing and reading a design, so LID's stops may help the person think, and not only help the agent understand. Our simulated owner had nothing to work out, so the study can't see that effect, in either direction.

**What people's experience shows.** People's good experience with LID is real, but it can't show what a different method would have missed, and the care a method demands can make it feel more valuable. These runs can't settle that question either, because they measure only what they measure.

## What we'll look at changing in LID

These come from what we saw in the runs. None of them has shipped.

- **Links between segments that can be followed from either side** ([#135](https://github.com/jszmajda/lid/issues/135)), so an agent changing a rule can find the segments that rely on it.
- **Boundary questions the owner can answer.** When a change reaches into another segment, the agent could look at the other side itself and bring the owner a question about behaviour, not about segments.
- **Searching the code for the values and names a change touches,** alongside reading the design documents. Several of openGym's dependencies were easiest to find that way.
- **Shorter documents,** because long ones cost review quality as well as time.
- **A more reliable `/map-codebase`** that records the ties between parts of a codebase and follows its own steps ([#133](https://github.com/jszmajda/lid/issues/133), [#134](https://github.com/jszmajda/lid/issues/134)).

## Open questions

- **Study next: does LID pay off over a long life?** This needs a realistically sized project built in public, ideally an app with a backend, grown from scratch over fifty or more changes with real changes of direction, and growing beyond what a bare agent can read at once.
- **Study next: what do long-running real projects show?** A project that adopted LID partway through has a natural before and after in its own history: regressions, reverts and fixes that cross components, per change, in each period. Model improvements over the same months confound that comparison, but it's real use over months.
- **Study next: do the LID changes above help?** Rerunning the same Clowder changes after [#135](https://github.com/jszmajda/lid/issues/135) is addressed would show whether the boundary failure goes away.
- **Study next: how much reading can an owner skip,** and does LID help weaker models more or less than a strong one?
- **Study next: how does LID compare with the other spec-driven systems,** with setups their maintainers can check first?

## How sure we are

**The size of the evidence.** Every comparison here rests on three runs or fewer per approach, and we didn't fix the analyses before running them. So each result shows a direction, and none rules out that there is no real difference. Several rest on a single run.

**The grading.** We found faults in the grading many times: probes that asked for more than their requirement said, probes that accepted only one way of building a feature, a simulated owner that sometimes leaked requirements, and a judge model that wasn't consistent enough. We fixed each one and regraded before the numbers in this report, and the study's notebook lists every fault and keeps the original gradings. A second Claude model also re-judged a sample of verdicts without seeing which approach produced them. On Clowder it agreed with 9 of 12, and on openGym with 14 of 15. Every disagreement came from a probe fault, and after the fix the grading agrees with it. That recheck rescored the same sample of verdicts; we didn't draw a fresh sample, which would be the stronger check.

**Choices that favour LID.** On Clowder, the LID agent had all the documents LID had built over the game's life. The bare agent got a copy with those removed and with its tests thinned to the number a bare agent writes for itself. So the two started from different material as well as working differently. Clowder's own instruction file also tells agents to settle design reviews against the game's stated principles rather than ask the owner. The LID agent followed that, so it stopped less often than LID normally does.

**Whether the model already knew the code.** When we asked the model about one candidate project, Paperless-ngx, without showing it any code, it answered 82% of our questions about its internals correctly, so we dropped that project. For Clowder and openGym it answered about a fifth correctly, mostly values it could have guessed.

**One model.** Everything ran on Sonnet 5.5 at medium effort. Other models may follow a long workflow differently.

## Where the details are

Everything behind this report is in the study's research notebook, [`docs/research/cost-eval/`](https://github.com/jszmajda/lid/tree/main/docs/research/cost-eval) in the LID repository ([pull request #120](https://github.com/jszmajda/lid/pull/120)): the design, the decisions and who made them, a dated log, the observations behind the list of LID changes above, and the code that ran the study. Each project's test material stays private, because later comparisons will reuse it.
