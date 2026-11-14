# Eval design (working draft)

**Status: working draft.** This file always shows the current design. The reasons for changes go in [log.md](log.md). Items marked "Open" still need a decision.

## The shape of a claim

The research aims at claims like this one:

> On executor E (a harness, model, and reasoning effort), with project size S and user policy U, arm A's cost per change is k times arm B's when the project is new, and k′ times after N changes, at fidelity F. The cumulative cost curves cross at about change N\* (with a confidence interval), or don't cross within the range tested.

Every published claim carries its scope: the versions of every system involved, the executor, the user policy, the size tier, the date of the runs, and an evidence grade (see "Statistics"). Cost always appears next to fidelity, because a cheap change that breaks earlier behaviour isn't cheap once someone has to fix it.

Terms used in claims:

- **Cost per change** is the full cost of one change: the agent's tokens, plus the human attention it asked for, reported side by side.
- **Fidelity at a change** is the share of requirements in force that the software meets after that change. A requirement is in force from the point where the arm could know it until a later change retires it (see "When the owner knows what they want").
- **An accepted change** is one where the software meets every requirement in force that the owner has stated or disclosed so far. Missing a requirement the owner never disclosed doesn't block acceptance. It counts against fidelity and is reported separately. Acceptance matters once repairs are added (see "Repairs"); the pilot reports cost and fidelity without repairs.

There are two ways to measure break-even, and we keep them separate. One is by project size, which is what #75 asks about. The other is by number of changes, which is what the maintenance hypothesis predicts.

## Arms

An arm is one way of working with the agent. Each arm is a self-contained configuration: its install steps, the instruction files it adds to the project, the prompt template for each change, and a mapping from each point where the arm expects a person (an approval, a question, a persona conversation) to the user simulator. Keeping arms self-contained lets another system's maintainers write or correct their own arm (see "Fairness").

**Pilot arms:**

- **Bare agent.** The harness's defaults and the product brief, and nothing else, apart from the isolation that applies to every arm (see "Sessions and isolation").
- **Cheap discipline.** Plan mode, plus a short AGENTS.md that tells the agent to write tests for each behaviour and to keep a NOTES.md recording decisions and the reasons for them. Nobody brands this way of working, but it is probably the most widely used real alternative to an SDD system, so it is the rival that matters most.
- **LID Full.** The `linked-intent-dev` plugin in Full mode.

**Later arms, in order:**

1. **LID Scoped, and LID with and without the arrow-maintenance overlay.** These ablations answer #75's "proportional cost" question directly. They compare LID only with itself, so there's no conflict of interest in running them. They come before the competitors.
2. **OpenSpec 2.x.** It keeps living capability specs plus an archive of per-change folders. It is the competitor most focused on changes after the first build.
3. **Spec Kit, using its living-spec model.** Spec Kit documents four ways to keep specs after delivery and makes none of them the default. In the living-spec model, `spec.md` is the contract and the plan and tasks are regenerated from it. That is the model closest to LID's spec-anchored design, so it is the strongest Spec Kit competitor. Flow-back, where any artifact may be updated, is the alternative if Spec Kit's maintainers prefer it.
4. **cc-sdd, as the Kiro-shaped arm.** cc-sdd is open source and Kiro-compatible: EARS requirements, then a design, then tasks, with phase gates. It runs in Claude Code and Codex. Using it means we don't have to build a Kiro imitation of our own.
5. **BMAD,** once version 7 is stable. Comparing against version 6 just before it is replaced would date the result immediately.
6. **Superpowers,** possibly, as a branded version of discipline without a living spec.

**Kiro itself is out.** It runs only in its own harness and needs a paid API key, so a Kiro arm would measure the product rather than the method.

Each competitor arm runs at a pinned version, installed by its official quickstart and driven by its documented workflow. [landscape.md](landscape.md) records the configuration chosen for each system and the reason for it.

## Executors

An executor is a harness, a model, and a reasoning effort, treated as one unit. Harness and model family change together (Claude runs only through `claude -p`, and other families run through opencode), so claims are made per executor. Arms are compared within an executor. Across executors we check only whether the ranking of the arms holds.

| Family | Top tier | Mid tier | Harness |
|---|---|---|---|
| Anthropic | Opus 5.5 | Sonnet 5.5 | `claude -p`, medium effort |
| OpenAI | GPT-6.1 Sol | GPT-6.1 Terra | opencode over OpenRouter, medium effort |
| Third (Open) | Gemini 4 Carbon or Argon, or the latest DeepSeek | | opencode over OpenRouter |

The pilot starts on Sonnet 5.5 and adds Opus 5.5 once the instrument works (see [plan.md](plan.md)). Sonnet 5.5 may be too strong to stand in for the cheap models in the studies behind H5, so a Haiku 5.5 tier is a candidate for testing H5.

## Sessions and isolation

Each change runs in a fresh session. The agent continues in its own workspace, the repository as the previous change left it, and nothing from earlier sessions carries over except what is in that repository. This is how the maintenance hypothesis works in practice: an agent that comes to change 6 without remembering changes 1 to 5 has to find the intent it needs.

- **Each session runs in a container, with its arm's own configuration.** Every executor session runs in a Linux container from one pinned executor image, as a non-root user with a neutral git identity. The container is the permission boundary, so the agent runs with permissions bypassed, and every harness (Claude Code or opencode) is isolated the same way. Each arm's configuration lives in its own volume, holding only that arm's plugins, skills, settings, and session transcripts, with no global instruction file and no memory. The machine running the eval has LID's plugins installed for everyday use, and its account details would otherwise reach the agent, so nothing from that machine enters the container except the arm's workspace and a subscription token. Every session's start-up record is checked for the plugins and skills it loaded, and a session that loaded anything outside its arm's list is invalid.
- **Auto-memory is off in every arm,** because it would carry intent between sessions outside the repository.
- **Versions are pinned.** The Claude Code version and the model snapshot are pinned and recorded with every run.
- **Every arm hears that someone can answer questions.** Every arm's first prompt for a change includes the same neutral sentence saying the product owner is available to answer questions.
- **Turns that wait for an answer are recognised.** In headless mode, a turn can end because the agent is done or because it is waiting for the person. The harness tells the two apart with an explicit rule, and checks that rule against labelled transcripts.
- **Pacing happens only between changes.** Pausing in the middle of a change would let the prompt cache expire between turns, which would penalise arms that stop often.

**Ablations, run and reported in a later stage:** every change in one long session, which favours the bare arm because the context window then holds the intent; and auto-memory left on.

## Seed projects

**Greenfield from a brief comes first.** Every arm starts from the same product brief, so no arm starts with an advantage and nobody has to map an existing codebase's intent first.

**The brief is in the owner's own words:** what they need, and the rules they state up front. It doesn't fix an interface, so each arm designs its own API. Turning loose intent into a design is part of the work being compared. A brief that settled the design would leave the processes little to do, and would make a ceiling more likely.

**The brief fixes only what the harness needs to run every arm the same way:**

- the language and stack, to cut variance (Python 3.12, FastAPI, and SQLite for BenchTime);
- one command, documented in the README, that starts the software;
- one data location that the start command uses, so the harness can reset state by starting from an empty location;
- reading the current time from the system clock. The harness controls that clock from outside, with `libfaketime` in the Linux container the software runs in, so time-dependent rules can be graded reproducibly without the arm building a clock of its own. The container runs in UTC; the lab's time zone is setup data.

**The chosen seeds.** All fifteen candidates and the reasons for the choice are in [seed-proposals/](seed-proposals/README.md).

- **Pilot: BenchTime**, from GPT-6.1 Sol's proposals. It is a reservation service for shared lab instruments, with cleaning buffers, qualifications that must cover the whole booking, inspection before an instrument is available again, and maintenance closures. Its rules mix time, state, and qualifications, so date arithmetic doesn't dominate. Its domain was the top pick of two model families working separately.
- **Second seed: ReleaseDesk**, also from Sol. It is an embargoed archive where restricted records must stay invisible in every surface: search, counts, file names, and download bundles. It tests a different kind of rule, one that every new feature must respect, and it depends much less on dates.

**What makes seed data interesting:** rules that aren't obvious from the code, at least three components with contracts between them that nobody wrote down, and requirements that later conflict with each other.

**Size tiers** are set by the size of the code relative to the executor's context window, not by lines of code: well under the window, near it, and several times larger. LID's claim about cheap navigation depends on the window, so a medium tier comes before the competitor arms, and the largest tier will have to be brownfield.

**Authorship.** Models from families other than Claude draft the brief, the hidden oracle, and the change script, without knowledge of the arms. The oracle is narrative product prose. It is never written as EARS requirements, because an oracle shaped like LID's specs would line up with LID's tests by construction.

The main session then edits the drafts for quality before the maintainer reviews them. The main session knows the arms, so its edits could tilt the materials toward LID, and three rules guard against that:

- **Edits may fix:**
  - inconsistencies between the documents;
  - items that can't be graded through the interface;
  - names or values a grader needs that no disclosure contains;
  - disclosure kinds a real owner wouldn't plausibly have;
  - unclear wording;
  - scope that would make the first build too large.
- **Edits may not** change the mix of change types, add or remove changes, or move items between disclosure kinds in order to favour a predicted direction.
- **Every edit is logged with its reason, and the drafts are kept unedited** beside the edited versions.

**Hidden materials stay private until their runs finish.** The oracle and the change script, with the drafts and edit log, stay out of the public repository until every counted run that uses them is done, because an agent under test could otherwise find them. Their hashes are recorded publicly before any counted run. The brief and the authoring prompts are public.

**Later seeds and variants:**

- **Relayed briefs.** An intermediary model plays a product manager who writes the brief and change requests from the owner's notes. That loses and reinterprets some intent along the way, as real requirements do when they pass through a business group.
- **Brownfield.** A common pre-built codebase that every arm onboards through its own documented process, with the onboarding cost metered as the cost of adopting the system.
- **History replay.** An open-source project at an early commit, with its next real issues as the change requests and the tests those changes added as hidden tests.
- **SlopCodeBench as-is.** Running a benchmark that someone else designed, with a LID arm added, checks our results against a test we didn't shape. SlopCodeBench gives each agent a Jinja system-prompt template. Whether it can load a Claude Code plugin or a project AGENTS.md hasn't been checked yet.

The maintainer's own public LID projects already contain LID's docs, which would give LID an unfair advantage, so they aren't used as comparison seeds.

## The change script

Each seed has a scripted sequence of changes, written in plain product language. Every change has a type, and before any run we record whether that type should favour LID, disfavour it, or neither:

| Change type | Example | Predicted direction |
|---|---|---|
| Rule across the whole system | "All money amounts round with banker's rounding" | Favours LID |
| Reversal of an earlier decision | "Drop the 30-day grace period we added earlier" | Favours LID |
| Needs the reason behind an earlier tradeoff | "Speed up the export, keeping the guarantee it was built around" | Favours LID |
| Bug report describing only a symptom | "Customers in Sydney are charged a day early" | Favours LID |
| Ordinary local feature, such as adding a field | "Add a CSV export of invoices" | Neither |
| Copy or config change | "Rename the 'Overdue' label to 'Past due'" | Disfavours LID |
| Dependency bump or pure refactor | "Upgrade the date library" | Disfavours LID |
| Change that touches many areas | "Add multi-currency support" | Unclear: LID cascades through every area, which costs, and finds every area, which saves |

**The mix of change types decides any pooled number,** and LID's maintainer would otherwise be choosing it. So results are always reported per change type. Any pooled figure weights the types by a mix taken from real commit histories and fixed before the runs. We also publish the break-even mix, in the form "LID costs less overall when at least x% of changes depend on earlier intent", so readers can apply their own mix.

**Probe changes measure the slope.** A probe is one request that makes sense at any age of the project, for example "add an export of all bookings in a date range". It is forked from the snapshots after changes 0, 3, 6, and 9, run several times from each, and the forks are then thrown away so they don't change the trajectory. Running the same request at each age keeps the age of the project separate from how hard a particular change happens to be.

**Every requirement has a lifetime.** Each requirement records the change that introduced it and the change that retired it, if any. Graders check a requirement only while it is in force, so a reversal or a redirect doesn't leave the arm graded against intent the owner has dropped.

## When the owner knows what they want

Real owners don't know everything at the start. Some intent is clear, some comes out only when someone asks the right question, some is noticed only on seeing a wrong proposal, and some isn't realised until weeks later. A product manager can also forget to pass something on. Each item in the oracle therefore has a disclosure point, set when the seed is written and the same for every arm:

| Disclosure | What the owner does | Example (BenchTime) | In force from |
|---|---|---|---|
| Stated | Puts it in the brief or a change request | "Bookings for one instrument can't overlap" | The change that states it |
| Askable | Knows it and gives it when asked about that topic | Asked whether a cleaning buffer counts toward a person's booking limit: "No, only the reserved time does" | The start |
| Recognised on sight | Can't put it into words, but rejects a proposal that gets it wrong | Shown a plan where a returned instrument is available at once: "No, it has to pass inspection first" | The start |
| Emerging at change k | Doesn't know yet. Before change k, answers "no preference, use your judgment". At change k, brings it up unprompted as part of the work | At change 7: "I've realised a person's qualification has to be valid for the whole booking, not just when they book" | Change k |
| Realised on a symptom | Notices only when the software does it wrong | At change 9, if the software lets an uninspected instrument be booked, the owner reports what they saw. If it doesn't, nothing is reported | The report |

Emerging intent tests the maintenance hypothesis directly. Arms that asked about an emerging item early were told "no preference" and made a choice. When the owner's realisation arrives, an arm has to find where that choice was made and change it. An arm that recorded the choice should find it cheaply.

Requirements disclosed as askable or recognised on sight are graded from the start, because an arm could have found them. They are reported separately from stated ones, as latent intent.

## Redirects

In some changes, the owner changes direction partway through. There are two kinds:

- **Change of mind:** the owner wanted one thing and now wants another, for example "actually, a safety closure should cancel existing bookings too".
- **Clarification:** the intent was unclear and the agent guessed, and the owner now says what they meant. If the arm asked first, so there was nothing to clarify, the redirect is recorded as pre-empted. That counts as an outcome, not as missing data.

Each redirect is delivered at one of three times:

- **Early:** at the first plan or spec the arm shows the owner.
- **Late:** after code has been written.
- **Interrupt:** at a fixed fraction of the arm's usual spend for that change. This timing doesn't depend on the arm's stopping points, so it also works for a bare agent, which has no early stop of its own. A real user of a bare agent can interrupt it too.

**Redirect cost is marginal.** From the same snapshot, the change runs twice: once with the redirect, and once with the final intent stated from the start. The redirect's cost is the difference. This keeps the ordinary work an arm still has to do after a redirect out of the redirect's cost.

**Stale intent.** After the change, every artifact (code, tests, comments, and docs, for every arm) is checked for statements of the abandoned intent. We report the count, plus a behavioural check of whether the software still acts on the abandoned intent. More artifacts mean more places to go stale, so the count is reported next to how much each arm keeps.

In the pilot, redirects test the plumbing only. There are too few to measure.

## The user simulator

Every arm expects a person at different points: LID's phase stops, BMAD's persona conversations, Spec Kit's clarify step and review gates. A model plays that person for every arm, using the same model and the same prompt throughout. It holds the hidden oracle and its disclosure schedule.

- **It keeps a record of its answers.** Every answer is kept for the whole trajectory and given back to the simulator each time, so an owner at change 6 can't contradict what it said at change 2.
- **Broad questions get narrow answers.** Asked something broad, such as "any other edge cases?", it gives only askable items that concern the current change.
- **Silence gets a neutral answer.** Asked about something the oracle doesn't cover, it says "no preference, use your judgment", and the exchange is logged.
- **It never volunteers.** It offers nothing it wasn't asked for, except emerging items at their scheduled change. Transcripts are audited for leaks.

It runs under three policies:

- **Diligent:** reads everything the arm shows it and rejects anything that contradicts the oracle.
- **Bounded attention:** catches a contradiction with a probability that falls as the document gets longer. The curve is calibrated from trajectories in which the maintainer plays the owner.
- **Rubber-stamp:** approves everything and answers only direct questions.

The diligent policy alone would act as a perfect proofreader, which rewards whichever arm shows the most text. Results are therefore reported under all three policies, and as a function of how likely the owner is to catch a contradiction. The bare arm never stops for review, so it runs under one policy only.

To check that the simulator behaves like a person, the maintainer plays the owner on a few trajectories, and those results are compared with the simulator's.

## Human cost

Human attention is a headline measure, reported next to token cost and not converted into dollars by us. Each reader can apply their own exchange rate.

**The unit is one request.** A turn that asks three things is three requests. Each request is sorted by what it asks of the person, judged from the request and the oracle and never from the simulator's reply, so its kind doesn't depend on the user policy:

| Kind | What the person does | Rule | Example |
|---|---|---|---|
| Acknowledgement | Nothing to decide | No decision is requested | "Here's the plan. Proceed?" |
| Lookup | States something they know | The answer is a stated or askable item | "Which time zone does the lab use?" |
| Judgment | Chooses between options the agent sets out | The answer is latent, and the agent offered it as one of the options | "Should the cleaning buffer count toward the booking limit, or not?" |
| Origination | Works out intent nobody has stated | The answer is latent and wasn't offered, or the oracle doesn't cover it | "What should happen to bookings when an instrument's model is retired?" |
| Bug report | Notices a problem and reports it | The owner reports a symptom | "The instrument shows as free, but booking it fails" |
| End-of-change review | Reviews the finished change | Every arm, at the end of every change | — |

The last two kinds apply to every arm, so a bare agent that never asks anything still shows the attention its user spends finding problems and reviewing changes.

**Reading is reported separately from deciding.** For each touchpoint we count the words presented, counting only words that changed since the person last saw that document, and report them apart from the decisions requested.

**Labels are checked before they're trusted.** A model sorts requests into kinds. Two people label a sample of about 100 requests, and the target is agreement of kappa 0.7 or better between the people and between the people and the model. If four decision kinds can't reach that, they collapse to two: decision and no decision.

**Yield.** Each request records whether its answer brought out intent that a later graded requirement checks. Relevance alone doesn't show that asking prevented a failure, so the comparison is counterfactual: how often trajectories that never asked about a requirement go on to meet it, against how often trajectories that did ask go on to meet it.

**Time.** Only active time is recorded. Wall-clock time means little when runs are paced to fit a subscription quota.

## Intent fidelity

Fidelity is measured at three levels. Not every arm has all three.

1. **Behaviour against the oracle (every arm).** A grader checks each requirement in force against the running software, through the interface the arm built, using the reference that interface extraction writes (see "Graders"). The grader can make requests, and the harness sets the clock and resets state on its behalf. It never sees the source, the docs, or anything else that would identify the arm or persuade it that a behaviour exists because a spec says so. Graders are models because what's being graded is meaning: each arm designs its own interface and chooses its own names, messages, and structure, and a deterministic test can't tell when two different outputs mean the same thing.
2. **Artifacts against code and against the oracle (arms that keep artifacts).** A cold reader, a fresh agent with the whole repository and a fixed token budget, answers questions about how the system behaves and points to where each behaviour is implemented and tested. We score its answers against the oracle and against what the running software does, and record what each answer cost. This generalises the idea behind LID's bidirectional-differential skill, a naive reader working intent out again, so it can apply to any arm. Some arms may not produce artifacts for which this measure makes sense. If so, that is a finding, and we report it.
3. **Design levels against each other (LID only).** No instrument today checks that LID's HLD, LLDs, and EARS agree with each other. The bidirectional-differential skill covers only EARS against code. Measuring this level may lead to a separate change to LID, either extending that skill or adding a new one. That change would be its own issue and arrow walk.

Level 3 is never folded into any score that compares arms. LID's own instruments aren't used as metrics when comparing arms, because that would measure LID on its own terms. Their methods can be adapted into neutral measures, as level 2 does.

## Graders

**Graders run on the maintainer's Claude subscription,** through `claude -p`, to keep costs down. Haiku 5.5 is the first choice, and Sonnet 5.5 is used if Haiku fails calibration. Execution (see "Grading protocol") runs in batches of a few probes per session, because each probe takes a dozen or more calls and a session's cost grows with its length. Judgment reads each batch's execution log in one session.

**Grading Claude with Claude risks a family bias,** so four safeguards apply:

- At level 1 the grader sees only the software's behaviour, not code or documents a Claude model wrote.
- Graders don't know which arm they are grading.
- Calibration includes checking for bias.
- A small sample of checkpoints is also graded by a model from another family (GPT-6.1 Terra), which costs a few dollars and measures any self-preference directly.

When a later stage runs executors from other families, a Claude grader is already from a different family.

**Interface extraction comes before grading.** Before each checkpoint is graded, a separate session reads the arm's repository and its running software. It writes a neutral reference covering:

- how to start the software and where its data lives;
- how to load the lab's setup data;
- every operation, with its inputs and outputs.

The extraction session works as follows:

- **It describes calls, not behaviour.** The reference follows a fixed template and says only how to call the software, never what it is meant to do, so an arm's specs and docs can't reach the grader.
- **It starts from the generated description when there is one.** It begins from FastAPI's OpenAPI description where that is available.
- **It isn't charged to the arm.** Extraction is evaluation overhead.
- **It is checked like grading.** The maintainer spot-checks references against the code.

A requirement the grader can't find a way to exercise gets a third verdict, "couldn't exercise", reported separately from "not met". An awkward API therefore shows up as itself rather than as lost intent.

## Grading protocol

### What a verdict is

Graders give one verdict for each item in force, at each checkpoint, in each trajectory. Items that aren't in force at a checkpoint get no verdict. A verdict is one of:

- **met**;
- **not met**;
- **couldn't exercise:** the grader couldn't find a way, through the interface reference, to perform what the check needs.

### Probes turn each item into concrete checks

The oracle's grading sketches leave room for interpretation. Before any counted run, each item therefore gets one or more probes. A probe is a scenario and an expected observation, both in terms of operations:

- the lab data to load and the clock settings;
- the operations to perform, in order;
- what should be observable afterwards.

For example, a probe for the brief's three-booking limit reads: "Maya makes three confirmed bookings, then asks for a fourth on another instrument. Then Leo asks for a booking. Expected: Maya's fourth booking is refused, and Leo's succeeds."

An item is met only if every one of its probes passes. The share of probes passed is reported as a secondary figure. Probes are written the same way as the rest of the seed: a model from another family drafts them, and the main session edits them under the same rules. A review by Claude Fable stands in for the maintainer's detailed review: it checks every probe against the oracle, recomputing times and boundaries, and the fixes are checked again. They are kept hidden with the oracle.

### Running and judging are separate steps

1. **Execution.** A grading session works through the probes against the running software, using the interface reference, and records every request, response, and clock setting in an execution log. It records what it observes and doesn't decide verdicts. The grader reaches the software only through a harness tool that sets the clock, resets state, and makes requests from inside the software's container, and the tool writes the execution log itself. Setup data that the software takes from a file or a command goes through the same tool, which never opens the source to the grader.
2. **Judgment.** A separate session compares each probe's expected observation with the log, and returns a verdict with a short justification that cites the log entries it relied on. A verdict that cites no evidence from the log is invalid.

Keeping the two steps apart means a verdict can be judged again, checked by another model, or corrected without running the software again.

### How the graders' work is checked

- **Seeded violations.** Before the pilot, a few builds are checked by hand. Copies are then changed to break one item each, and the grader must return "not met" on the broken item and leave its other verdicts unchanged. This gives known answers in both directions, on interfaces that different arms designed.
- **Labelled pairs.** Judgment is also checked on pairs in both directions: the same behaviour under different names, which should pass, and different behaviour under the same names, which should fail.
- **Test-retest at both steps.** Judging the same logs again measures how consistent judgment is. Running the probes again on the same snapshot measures how consistent execution is. Concurrency probes are watched closely, because they may flip for reasons unrelated to grading.
- **Cross-family judging.** GPT-6.1 Terra judges a sample of logs again. It needs only the logs, not the running software, so this costs little.
- **Spot checks by the maintainer.** The maintainer reviews a sample of verdicts together with their evidence. The sample over-represents "not met" and "couldn't exercise" verdicts and latent items, where interpretation matters most. A starting point is about 10% of verdicts, and at least 30 per pilot stage, adjusted after the pilot. The same checks apply to the cold reader's scoring at fidelity level 2, which is sampled most heavily, because grading artifacts against code is the least well understood.
- **Thresholds.** Graders are trusted when they agree with the maintainer on at least about 90% of sampled verdicts, and fewer than about 5% of verdicts flip when judged again (the pilot's stage 2 thresholds in [plan.md](plan.md)). Agreement is reported with every result, as a percentage and as Cohen's kappa.

### Disagreements

When the maintainer and a grader disagree, the maintainer's verdict stands for that case, and both are recorded. If the disagreements on one item follow a pattern, its probes or wording are fixed in a new version, and every log for that item is judged again. Each verdict records the probe version it was judged against.

### Scoring and reporting

- **Every verdict is a row.** It records the trajectory, arm, executor, checkpoint, item, disclosure kind, whether the item is new or preserved at that checkpoint, the verdict, the share of probes passed, and pointers to its evidence and probe version.
- **Fidelity at a checkpoint** is the number of items met divided by the number met plus not met, over the items in force. "Couldn't exercise" verdicts are left out of that fraction and reported as their own rate per arm. As a sensitivity check, they are also counted as not met.
- **Breakdowns.** Fidelity is reported overall and broken down three ways:
  - by disclosure kind (stated, askable, recognised on sight, emerging, and realised on a symptom);
  - by new against preserved items;
  - by change type.
- **Regressions.** A regression is an item met at one checkpoint and not met at a later one. Each is reported with the change that caused it and how many changes it survived.
- **Publication.** All verdict rows, execution logs, probes, and judging prompts are published after the runs, together with the oracle.

## Whether intent can be checked in CI

- **Requirement-level mutants, without a model.** For each requirement an arm currently meets, a violation is injected into that arm's code, for example changing an inspection requirement so a returned instrument becomes available at once. A mutant counts only if the black-box grader confirms that the requirement now fails. Then only deterministic checks run: the project's own tests and any validator the arm ships. The score is the share of valid mutants caught, out of requirements the arm met.
- **A cheap cold agent.** A small model with a fixed token budget is asked whether the repository matches its stated intent. The scores are the detection rate, the false-positive rate, and the tokens spent per detection.

These scores are reported on their own and never folded into a combined score, because "checkable in CI" is closer to LID's framing than to some competitors'.

## Repairs

The pilot measures without repairing. Each change's cost and the fidelity after it are reported side by side, and broken requirements stay broken. A repair loop that fixed every break at once would act as a free, instant QA team for every arm, so no regression would survive a single change, and nobody would pay the cost of noticing one.

Repairs are added in a later stage, built to match how bugs reach people:

- A broken requirement is reported only after a delay, and only as a symptom.
- A report is filed only after a replayed reproduction confirms the break, so a grader's false failure can't trigger a real repair session.
- Each report counts as a bug-report touchpoint.
- Repair rounds are capped. A change still failing at the cap is counted as unresolved and reported separately.

The scheduled realised-on-a-symptom items in the oracle already work this way, because they fire only if the software actually misbehaves.

## Cost accounting

- **Token classes.** Every run records uncached input, cache writes, cache reads, and output tokens separately. Dollars come from a dated table of list prices, whoever actually paid. Claude Code's `total_cost_usd` is its own estimate, so it is recorded but not trusted on its own.
- **Subagents count.** A session's `modelUsage` and `total_cost_usd` include its subagents. After a resume they are cumulative for the session, so a turn's tokens are the difference between consecutive results. The `usage` field covers only the main thread, so it isn't used.
- **Failed runs count.** Timeouts and harness errors are outcomes, and their spend counts. This differs from the alternate-model runner, which leaves them out of its results. In a cost eval, leaving them out would favour heavy systems, which time out more.
- **Standing context.** Each arm's fixed per-session overhead (its instruction files and skills loaded every session) is measured separately from its per-change work.
- **Run scheduling.** Trajectories are spread across several days, because infrastructure noise varies over time. Re-pricing every run as if it had no cache hits gives a sensitivity check.

## Budget

The maintainer pays for this research, so the design keeps real spending small without weakening it.

- **Claude roles run on the subscription.** Executors, the simulator, graders, and the touchpoint classifier all run through `claude -p`. The subscription's quota is the constraint, so runs are paced between changes and never inside one.
- **OpenRouter costs real dollars, and is used only for:**
  - writing briefs, oracles, and change scripts with other families, at cents per document;
  - the cross-family grader sample, at a few dollars;
  - the stage that runs other families as executors, with a hard cap set from the pilot's measured tokens per trajectory.
- **The design itself saves cost:**
  - the pilot runs in stages with stopping criteria;
  - repetitions come before breadth;
  - one grader session covers a whole checkpoint;
  - the bare arm runs under one policy;
  - probe forks are thrown away rather than carried forward.

## Statistics

- **Units of analysis.** A trajectory is one build followed by its change sequence, and it is the unit of analysis, because changes within one trajectory are correlated.
- **Forked checkpoints.** Probe changes and redirect twins run several times from the same snapshot. That separates the noise in a single change from the noise in a whole trajectory, and one bad build can't spoil every later data point.
- **Reporting.** Pairing is on (seed, change, executor). Cost ratios are reported with cluster-bootstrap confidence intervals, and as the median, mean, and 90th percentile, because agent costs have long tails.
- **Checks on the instrument itself:**
  - An A/A check runs the bare arm against itself and must show no difference.
  - A positive control is a deliberately weakened arm, for example one that loses part of every change request, and the instrument must show it doing worse.
- **Sizing.** The pilot measures variance, and the number of repetitions is chosen from that measurement.
- **Primary comparison.** One comparison is pre-registered as primary, and everything else is labelled exploratory. The provisional choice is LID Full against cheap discipline, measured as the ratio of their slopes of cost per change against project age, on Sonnet 5.5, with fidelity on preserved requirements reported beside it. It freezes at pre-registration.
- **Equivalence margin.** A margin of practical equivalence is set before the freeze, for example a cost ratio between 0.9 and 1.1. This makes "no meaningful difference" a result that can earn an evidence grade, not only a failure to find one.

**Evidence grades:**

| Grade | Meaning |
|---|---|
| A | Pre-registered; at least two executors and two seeds; the confidence interval excludes no difference, or lies entirely inside the equivalence margin; reproduced by someone else |
| B | Pre-registered; one executor or one seed; the confidence interval excludes no difference, or lies entirely inside the equivalence margin |
| C | Direction only: the interval is too wide for either, or the analysis wasn't planned in advance |
| D | A single trajectory, or an anecdote |

## Fairness

- **Competitors run as intended.** Each runs at a pinned version, installed by its official quickstart and driven by its documented workflow, with no custom prompts beyond what its own docs prescribe. The configuration chosen for each one, and the reason, is recorded in [landscape.md](landscape.md).
- **Other maintainers can check our setup before it's frozen.** We publish a guide to running the eval on one's own system, and invite the maintainers of each compared system to review our configuration for their system, correct it, or run it themselves, before pre-registration rather than after. Their corrections are accepted, and their objections are published next to the results.
- **Seed materials are written blind.** Briefs, oracles, and change scripts are written by models from other families, without knowledge of the arms, and their hashes are recorded before any counted run. A second seed written by someone outside the project would answer the objection that LID's maintainer chose the test.
- **Ablations that might favour LID are run, not only listed.** These are the single-session and memory-on ablations.
- **Everything is published.** That includes the harness, every transcript, the repository at every checkpoint, the oracle (after the runs), and the analysis.
- **Pre-registration.** Hypotheses, the primary comparison, the analysis plan, the equivalence margin, and the exclusion rules freeze before the first counted run.
- **Unfavourable results get published.** We commit to publishing results that don't favour LID.

## The harness

The harness is the code that runs the eval. It serves this study, so it sits outside LID's arrow, beside the notebook in `harness/`. If its results come to back a claim LID ships, such as Goal 3's "proportional cost" or a line on the site, or the eval becomes a measurement repeated as LID changes, the harness moves into the arrow as its own segment, as the alternate-model runner is. Milestone M8 is the natural point to decide.

It has three parts, run in order, each handing its records to the next:

- **Trajectories.** Takes one arm through one seed's changes with one executor. Each change gets a fresh session in the executor container. The user simulator answers whenever a turn ends waiting for the person, redirects and symptom reports arrive as the change script says, and the harness commits whatever the arm leaves uncommitted at the end of each change. The part records every session's transcript, the simulator's exchanges and answer record, and the cost of every turn.
- **Grading.** For each checkpoint, it builds an image of the arm's last commit and extracts the interface reference. It prepares each named setup once and snapshots its data location, runs the probes through `gt`, and has the judge read the logs.
- **Reports.** Turns the records into the measures in "The shape of a claim": tokens and dollars per change, touchpoints by kind, fidelity at each checkpoint, and the statistics.

**Replay keeps grading affordable.** Each trajectory runs about 600 probes across its 11 checkpoints, and most of them repeat a probe that passed against an unchanged interface. So at each checkpoint after the first, the harness first replays the previous checkpoint's calls for each probe, without a model, substituting the identifiers and tokens the service returns this time.
- A model executes a probe only when the probe is new at this checkpoint, or when its replay fails because the interface changed.
- The judge sees only probes whose responses changed; the others keep their verdicts.
- A sample of carried-over verdicts is judged again, so replay can't hide a regression.

**Principles the three parts share:**
- **Raw records first.** Every part keeps complete transcripts, logs, and responses, and measures are computed from them afterwards, so a measure can change without a re-run.
- **One treatment for every arm.** Where a tool's usual setup clashes with the shared harness, every arm gets the same treatment, and the difference is documented under "Fairness".
- **Runnable by others.** Images and versions are pinned, and nothing depends on the maintainer's machine, so another system's maintainers can run their own arm.
- **Tests where a quiet bug would bias the results:** cost accounting, replay matching, the grading log, and the simulator's release of the owner narrative.

## Known limits

- **The conditions where LID should help most are the hardest to test.** Those are large systems, long-lived ones, several people, and months of forgetting. Fresh sessions stand in for forgetting, and emerging intent stands in for an owner who learns over time, but neither stands in for a team changing over time, and twenty changes in a day is not two years of maintenance. Published claims will state which conditions they cover.
- **Some value isn't measured.** That includes how well a person understands the system, how easy changes are to review, and how quickly a newcomer learns the system. We state that these aren't measured, rather than letting the numbers imply anything about them either way.
- **Results go out of date.** Every system compared here releases often, some of them every few days. Results are dated, and the harness is built so that re-running it is cheap.

## Open questions

- Where the harness code lives, and how much of the alternate-model runner it reuses.
- Which model family is third: Gemini 4, or the latest DeepSeek.
- Whether to add a Haiku 5.5 executor tier for H5.
- The time limits for builds and for changes, and the repair cap for later stages.
- Whether to run a second cheap-discipline variant alongside plan mode.
- The fraction of usual spend at which interrupt redirects fire.
