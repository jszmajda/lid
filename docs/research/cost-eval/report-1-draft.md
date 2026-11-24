# What LID costs, and what it buys: first results

**Draft, 2026-11-24.** Every number here comes from pilot runs. None of the analyses were fixed in advance, the samples are small, and one model did all the work. The results show which way each difference points; they are too small to measure how big it is.

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
| Agent cost | LID cost 3.3 to 5.5 times as much as a bare agent per change, and the gap didn't narrow as a project aged. On a codebase LID didn't build, mapping it first raised that to about 16 times. |
| Owner's reading | LID showed the owner 5 to 11 times as many words, and on one single run of a large project about 25 times. |
| Building what was asked | LID was ahead on two projects, behind on one project's stated requirements, and level on one. |
| Requirements the owner never stated | On the one project with room to show it, the LID agent caught more of them, mostly because it asked. |
| Not breaking another part of the system | No overall difference. LID's documents helped when they linked the two parts, and hurt on changes where they didn't. |
| Fixing the bare agent's misses afterwards | Much cheaper in agent cost than LID's extra cost, once each miss was reported. Some misses survived the repair. |

## How we tested

**The executor.** Claude Sonnet 5.5 at medium reasoning effort made every change, whichever way of working it followed. Opus 5.5 ran only in two checks of how well a bare agent could do at its best. The runs on the last two projects used LID 1.4.6. The notebook records the versions for every run.

**The owner.** A real person can't sit through hundreds of runs, so a model plays the owner. The study wrote the owner's real intent down in advance as a list of requirements. The owner states some of them in its request. It shares others only when the agent asks, and objects to others only when the agent proposes something that contradicts them. The owner is an imperfect reader on purpose: it misses more as it reads more, and something the agent shows it can remind it of a requirement it forgot to mention. The settings for that come from published research on attention and memory ([owner-model-research.md](owner-model-research.md)). The owner never reads code.

**The projects.**

- **BenchTime**, a small reservation service, built from a short brief and then changed ten times.
- **ReleaseDesk**, a small release-approval tool, grown the same way through twenty changes.
- **Clowder**, a Rust terminal game with about 270,000 tokens of non-test source, which the maintainer built with LID. Each change was asked of one half of the code but had to respect a rule in the other half.
- **openGym**, an open-source fitness app with a Node API, a React app, watch apps and an MCP server. Its first commit came after the model's training cutoff, and LID didn't build it. Its changes were chosen the same way as Clowder's.

On the last two projects, each change was made three times by each way of working, each time from the same starting code.

**Grading.** Each requirement has one or more probes: small tests written against the build being graded. A model runs them in a container, and a second model judges the result. Before counting anything on the last two projects, we checked the grading both ways: the untouched code had to fail every new requirement, and a correct build of every change had to pass every one.

**Cost.** The agents ran on a Claude subscription. Dollar figures are what the same tokens would cost at list API prices. The study's real out-of-pocket spend was about $18, paid to other model families that drafted and reviewed the test material.

## What it costs

### Agent cost

| Project | Bare agent | LID Full | Ratio |
|---|---|---|---|
| BenchTime, the build and ten changes | $2.53 | $11.17 | 4.4× |
| ReleaseDesk, per change to change 20 | $0.29 | $1.59 | 5.5× |
| Clowder, per change | $0.14 | $0.51 | 3.6× |
| openGym, per change | $0.28 | $0.91 | 3.3× |
| openGym, per change with the one-time mapping spread over twelve changes | $0.28 | about $4.40 | about 16× |

The checklist on ReleaseDesk cost $0.34 per change, and cheap discipline on BenchTime $4.54 for the build and ten changes.

On BenchTime we also made the same small request after changes 0, 3, 6 and 9. LID's extra cost for it stayed the same as the project aged. We had expected LID's written intent to make later changes cheaper; on projects this size, later changes cost LID as much as early ones.

Tests and code take 43% of LID's spend on BenchTime and 48% on ReleaseDesk. The design, requirement and review phases take most of the rest, along with the stops where it shows the owner its work.

### The owner's reading

| Project | Bare agent | LID Full |
|---|---|---|
| BenchTime, the build and ten changes | 5,200 words | 53,400 words |
| ReleaseDesk, to change 20 | 8,200 words | 94,900 words |
| Clowder, per change, median (mean) | 312 (570) words | 1,639 (16,253) words |
| openGym, per change, median (mean) | 2,336 (9,903) words | 13,117 (24,016) words |

ReleaseDesk's LID total is about 6.6 hours of reading. In the first Clowder run, one run of twelve changes per approach, LID showed the owner about 195,000 words against the bare agent's 7,700.

These counts assume the owner reads everything LID shows, and most people don't read every requirement and test. On BenchTime, an owner who read only the conversation would read about half as much, and one who also read the design documents about four-fifths as much. We estimated those; we didn't run them, and every result here comes from an owner who reads everything. LID has an experimental option for an owner who reviews only the design.

The extra reading has a cost beyond time. Our owner, like a real one, misses more as it reads more. On BenchTime, each run had about four places where what the agent showed the owner contradicted one of the owner's requirements. The owner objected to 2.7 of 4.3 of them in the bare agent's short messages, and to 0.3 of 4.0 in LID's long documents.

## What it buys

### Small projects built from scratch

On BenchTime, every approach met most of the owner's requirements, so there wasn't much room to separate them. These are the shares met after ten changes, with three runs each:

| | Bare agent | Cheap discipline | LID Full |
|---|---|---|---|
| An owner who catches every contradiction | 92% | 89% | 96% |
| The imperfect owner | 95% | 93% | 97% |

LID's runs scored highest both times, but their range overlapped the bare agent's. The first row was graded before we fixed a way the owner could leak requirements while correcting the agent. Counting those leaks as misses doesn't change the order, and the two rows used different versions of the probes, so they shouldn't be compared with each other.

ReleaseDesk had more room, because more of its requirements were left unstated. We ran one sequence of twenty changes per approach:

| At change 20 | Bare agent | Checklist | LID Full |
|---|---|---|---|
| Stated requirements met | 98% | 98% | 93% |
| Unstated requirements met | 67% | 78% | 100% |
| Requirements met earlier and since lost | 0 of 49 | 0 of 48 | 2 of 48 |
| Owner's reading so far | 0.6 hours | 1.5 hours | 6.6 hours |

The LID agent met every unstated requirement, and the bare agent two in three. That's the largest gap in the study, but it's one run per approach, and LID's figure was 89% until we fixed a probe fault. Most of the gap comes from requirements that only the LID agent's owner disclosed, because the LID agent asked more questions. On requirements that every agent's owner had disclosed, every agent met all of them. The LID agent was behind on stated requirements.

### Large projects, where intent sits in another part of the code

| | Bare agent | LID Full |
|---|---|---|
| Clowder: new requirements met | 69 of 72 | 70 of 72 |
| openGym: built everything the owner asked for | 33 of 36 | 36 of 36 |
| openGym: new requirements met | 95 of 109 | 103 of 110 |

On openGym, the LID agent first mapped the codebase with LID's `/map-codebase` skill. The bare agent's misses there were mostly one kind. Asked for a join code that lets people sign up to the owner's gym for 90 days, two bare runs built admin sign-up invitations instead. Two LID runs made the same mistake, then corrected it while writing the design, before any code. With three runs per approach, that difference rests on two runs of one change.

In the first Clowder run, at a 1M-token context window, LID met 97% of the requirements and the bare agent 79%. At a 200k window they were level, at 84% and 85%. That was one run per cell.

### Not breaking another part of the system

Every change on Clowder and openGym was asked of one part of the code but had to respect a rule in another part. For example, the game's core decides how saved absence reports are kept, and the interface reads them to show a banner. A change to how reports are kept can quietly break the banner. We wanted to know whether LID's written intent helps an agent find and respect the other side.

| | Bare agent | LID Full |
|---|---|---|
| Clowder: the other part kept working | 18 of 24 | 19 of 24 |
| openGym: the other part broke, of runs that built the change | 7 of 33 | 6 of 35 |

Overall there was no difference, because LID's documents helped on some changes and hurt on others.

## When LID's documents helped, and when they hurt

**When the documents linked the two parts, the LID agent kept the dependency and the bare agent didn't.** On the absence-report change, LID's requirements said which part of the interface reads the saved reports. All three LID runs found it and kept the banner working. None of the three bare runs did. Part of LID's help came from a reference to that requirement in the interface code, which the bare agent's copy didn't have, because we removed every requirement reference from it. When we then told the bare agent about the miss, one of three repairs fixed it.

**When nothing linked them, LID's division of the project stopped the search.** LID divides a project's intent into segments. Inside a segment, the agent updates everything a change affects without asking; when a change would cross into another segment, it stops and asks the owner first. On three of Clowder's changes, the rule being changed was relied on by the interface's segment, and for two of them the interface's requirements restated the rule. Nothing on the core side pointed there. The LID agents read the design documents and the core code, concluded that the change stayed inside the segment they were editing, and stopped. They broke the interface in 5 of 9 runs. The bare agent, with no segments to respect, searched the whole codebase, found the interface's code, and broke it in 2 of 9. One LID run did notice the interface during its review and asked the owner, but the owner knew no code and said it had no preference, so the agent stayed out. This gap is being written up as an issue for LID.

**openGym's hardest dependency went the same way for both.** Only one of openGym's twelve changes had a dependency that a text search from the edited side wouldn't find. None of the three maps recorded it, and each approach kept it in one of three runs. On openGym the LID agents didn't stop at segment boundaries, because the maps grouped each feature's API and app code into one segment. Their misses came from reading too little inside a segment.

**The owner's reviews can't catch these misses.** The owner reviews designs and requirements and never reads code, so a dependency broken in code passes its review unless a document mentions it.

## Fixing misses afterwards

If the bare agent is cheaper and misses more, one plan is to use the bare agent and fix its misses when someone notices them. We tested that by reporting each miss to the agent as the owner would, then letting the agent repair the code.

| | Bare agent | LID Full |
|---|---|---|
| ReleaseDesk: LID's extra agent cost by change 20 | | about $19 |
| ReleaseDesk: cost to repair every miss | $0.39 | none missed |
| Clowder: changes plus repairs of every real miss | about $6.70 | about $21 |
| openGym: changes plus repairs | $12.67 | $35.12, or $160.66 with the mapping |
| openGym: misses fixed by one repair | 10 of 14 | 7 of 7 |

In agent dollars, repairing the bare agent's misses cost far less than LID's extra cost on every project. That comparison leaves out three things:

- **Some misses weren't fixed.** The bare agent's join-code misses survived their repairs, and two of its three absence-report misses did.
- **Some repairs broke something else.** On ReleaseDesk, one of three bare repairs and one of two checklist repairs broke another rule, and on Clowder three bare repairs did.
- **Every miss had to be noticed first.** We reported each miss to the agent the moment it happened. A real owner has to notice the problem, which may take weeks, while the software is wrong in the meantime. We didn't price that, or the owner's time to report it.

Whether LID's extra cost pays for itself depends on those three things, which this study doesn't yet measure, and on the owner's reading time, which counts against LID.

## Adopting LID on an existing codebase

LID's way into a codebase it didn't build is `/map-codebase`, which surveys the code and writes LID's documents for it: a high-level design, a design for each part, and requirements. We ran it four times on openGym, with no owner answering its questions. We set the first run aside because of a fault in our setup, and each of the other three became the starting point for one of the three LID runs of every change.

- **Each map took 12 to 21 minutes** and 59 to 153 million tokens, about $27 to $54 at list prices, and wrote 815 to 1,195 requirements.
- **Each map recorded the rules inside each part of the app well,** but rarely recorded the ties between parts: one or two of the thirteen we had found by hand.
- **The agent making each map skipped steps the skill asks for.** It chose how to divide the codebase before reading its own survey, accepted survey workers that skimmed large files instead of reading them, and invented its own limit on requirements per file, then deleted requirements to fit. We've filed both problems against the skill (#133 and #134).

Spread over twelve changes, the mapping raises LID's cost from about $0.91 to about $4.40 per change. On a project with many more changes, it would spread further.

## How sure we are

**Evidence.** By the study's own scale, nothing here is better than grade C: each difference shows a direction, but the samples are too small to rule out no difference, and we didn't fix the analyses in advance (pre-register them). Several results are grade D, a single run.

**The grading had faults, and we found and fixed them before these numbers.** Most numbers were regraded at least once, and the original gradings are kept. The faults included:

- a cheaper judge model that changed 9% of its verdicts when asked again, so we moved to a stronger one;
- probes that asked for more than their requirement said;
- a simulated owner that sometimes leaked requirements while correcting the agent;
- probes whose timing made two events happen at once, which caused the LID agent's only unstated-requirement miss on ReleaseDesk;
- on Clowder, grading that discounted requirements an agent met by rightly leaving code alone, and one probe that checked an internal function instead of what the player sees;
- on openGym, probes that accepted only one way of building a feature, failures of the test setup read as results, repairs left ungraded, and every cross-component repair run twice into the same workspace.

**Spot checks.** A second Claude model re-judged a sample of verdicts without seeing which approach produced them. On Clowder it agreed with 9 of 12, below the study's 90% bar; all three disagreements came from the one faulty probe, and after the fix the grading agrees with it. On openGym it agreed with 14 of 15, and the one disagreement was also a probe fault since fixed. Both rechecks rescored the same verdicts rather than drawing new ones.

**Choices that favour LID.** On Clowder, the LID agent had all the documents LID had built over the game's life. The bare agent got a copy with those removed and with its tests thinned to the number a bare agent writes for itself. So the two started from different material as well as working differently. Clowder's own instruction file also tells agents to settle design reviews against the game's stated principles rather than ask the owner. The LID agent followed that, so it stopped less often than LID normally does.

**Could the model have known the code already?** Shown nothing, the model recalled 82% of the internals we asked about in one candidate project, Paperless-ngx, so we dropped it. On Clowder and openGym it recalled about a fifth, mostly values it could have guessed.

**One model.** Everything ran on Sonnet 5.5 at medium effort. Other models may follow a long workflow differently.

## What we haven't tested

- **The other spec-driven systems.** That's the comparison people ask for most, and it needs setups that their maintainers can check first.
- **Long projects.** Our projects are small or were changed a dozen times. Testing whether LID's written intent pays off as a project ages needs a larger project built from scratch and changed many more times. Our first attempt didn't grow enough to test it.
- **What a miss costs a real owner** to notice, report and live with.
- **Lighter ways of running LID,** such as an owner who reviews only the design, or LID applied to only part of a codebase (its Scoped mode).

## Where the details are

Everything behind this report is in the research notebook in [docs/research/cost-eval/](README.md): the design, the decisions and who made them, a dated log, and the code that ran the study. Each project's test material stays private, because later comparisons will reuse it.
