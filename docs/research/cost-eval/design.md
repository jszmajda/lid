# Eval design (working draft)

**Status: working draft.** This file always shows the current design. The reasons for changes go in [log.md](log.md). Sections marked "Open" still need a decision.

## The shape of a claim

The research aims at claims like this one:

> On executor E (a harness, model, and reasoning effort), with project size S and user policy U, arm A's cost per accepted change is k times arm B's when the project is new, and k′ times after N changes. The cumulative cost curves cross at about change N\* (with a confidence interval), or don't cross within the range tested.

Every published claim carries its scope: the versions of every system involved, the executor, the user policy, the size tier, the date of the runs, and an evidence grade (see "Statistics" below). Cost always appears next to fidelity, because a cheap change that breaks earlier behaviour isn't cheap once someone has to fix it.

There are two ways to measure break-even, and we keep them separate. One is by project size, which is what #75 asks about. The other is by number of changes, which is what the maintenance hypothesis predicts.

## Arms

An arm is one way of working with the agent. Each arm is a self-contained configuration: its install steps, the instruction files it adds to the project, the prompt template for each change, and a mapping from each point where the arm expects a person (an approval, a question, a persona conversation) to the user simulator. Keeping arms self-contained lets another system's maintainers write or correct their own arm (see "Fairness" below).

**Pilot arms:**

- **Bare agent.** The harness's defaults and the product brief, and nothing else.
- **Cheap discipline.** Plan mode, plus a short AGENTS.md that tells the agent to write tests for each behaviour and to keep a NOTES.md recording decisions and the reasons for them. Nobody brands this way of working, but it is probably the most widely used real alternative to an SDD system, so it is the rival that matters most.
- **LID Full.** The `linked-intent-dev` plugin in Full mode.

**Later arms:**

- **LID Scoped, and LID with and without the arrow-maintenance overlay.** These ablations answer #75's "proportional cost" question directly. They also compare LID only with itself, so there's no conflict of interest in running them.
- **OpenSpec 2.x.** It keeps living capability specs plus an archive of per-change folders. It is the competitor most focused on changes after the first build.
- **Spec Kit, using its living-spec model.** Spec Kit documents four ways to keep specs after delivery and makes none of them the default. In the living-spec model, `spec.md` is the contract and the plan and tasks are regenerated from it. That is the model closest to LID's spec-anchored design, so it is the strongest Spec Kit competitor. Flow-back, where any artifact may be updated, is the alternative if Spec Kit's maintainers prefer it.
- **cc-sdd, as the Kiro-shaped arm.** cc-sdd is open source and Kiro-compatible: EARS requirements, then a design, then tasks, with phase gates. It runs in Claude Code and Codex. Using it means we don't have to build a Kiro imitation of our own.
- **BMAD,** once version 7 is stable. Version 7 was due in mid-November 2026, and comparing against version 6 just before it is replaced would date the result immediately.
- **Superpowers,** possibly, as a branded version of discipline without a living spec.
- **Kiro itself is out.** It runs only in its own harness and needs a paid API key, so a Kiro arm would measure the product rather than the method.

Each competitor arm runs at a pinned version, installed by its official quickstart and driven by its documented workflow. [landscape.md](landscape.md) records the configuration chosen for each system and the reason for it.

## Executors

An executor is a harness, a model, and a reasoning effort, treated as one unit. Harness and model family change together (Claude runs only through `claude -p`, and other families run through opencode), so claims are made per executor. Arms are compared within an executor. Across executors we check only whether the ranking of the arms holds.

| Family | Top tier | Mid tier | Harness |
|---|---|---|---|
| Anthropic | Opus 5.5 | Sonnet 5.5 | `claude -p`, medium effort |
| OpenAI | GPT-6.1 Sol | GPT-6.1 Terra | opencode over OpenRouter, medium effort |
| Third (Open) | Gemini 4 Carbon or Argon, or the latest DeepSeek | | opencode over OpenRouter |

Both tiers run from the pilot onward, because published evidence suggests process overhead pays off more on mid-tier models (H5 in [hypotheses.md](hypotheses.md)).

## Sessions

Each change runs in a fresh session. The agent continues in its own workspace, the repository as the previous change left it, and nothing from earlier sessions carries over except what is in that repository. This is how the maintenance hypothesis works in practice: an agent that comes to change 6 without remembering changes 1 to 5 has to find the intent it needs.

Claude Code's auto-memory is turned off in every arm, because it would carry intent between sessions outside the repository. Running every change in one long session is a possible ablation. It favours the bare arm, because the context window then holds the intent.

## Seed projects

**Greenfield from a brief comes first.** Every arm starts from the same product brief, so no arm starts with an advantage and nobody has to map an existing codebase's intent first. The brief fixes an external interface, either a CLI or an HTTP API, including every name, path, and output format the hidden tests use. Everything behind that interface is the arm's own choice.

**Interesting seed data** means domains with rules that aren't obvious from the code: billing with exceptions, scheduling across time zones, permissions, and state machines. A good seed has at least three components with contracts between them that nobody wrote down, and requirements that later conflict with each other. The free-trial question ("when exactly does day 30 end, and in whose time zone?") is the kind of rule a seed should contain.

**Size tiers** are set by the size of the code relative to the executor's context window, not by lines of code: well under the window, near it, and several times larger. LID's claim about cheap navigation depends on the window, and the largest tier will have to be brownfield.

**Oracle authorship.** Each seed has a hidden oracle, a fuller description of what the product owner wants than the brief gives. A model from a different family (GPT-6.1 Sol or Gemini 4) writes the oracle as narrative product prose, and the maintainer reviews it. It is never written as EARS requirements, because an oracle shaped like LID's specs would line up with LID's tests by construction.

**Later seeds:**

- **Brownfield.** A common pre-built codebase that every arm onboards through its own documented process, with the onboarding cost metered as the cost of adopting the system.
- **History replay.** An open-source project at an early commit, with its next real issues as the change requests and the tests those changes added as hidden tests.
- **SlopCodeBench as-is.** Running a benchmark that someone else designed, with a LID arm added, checks our results against a test we didn't shape. SlopCodeBench gives each agent a Jinja system-prompt template. Whether it can load a Claude Code plugin or a project AGENTS.md hasn't been checked yet.

The maintainer's own public LID projects already contain LID's docs, which would give LID an unfair advantage, so they aren't used as comparison seeds.

## The change script

Each seed has a scripted sequence of changes, written in plain product language by a model from another family. Every change has a type, and before any run we record whether that type should favour LID, disfavour it, or neither:

| Change type | Example | Predicted direction |
|---|---|---|
| Rule across the whole system | "All money amounts round with banker's rounding" | Favours LID |
| Reversal of an earlier decision | "Drop the 30-day grace period we added earlier" | Favours LID |
| Needs the reason behind an earlier tradeoff | "Speed up the export, keeping the guarantee it was built around" | Favours LID |
| Bug report describing only a symptom | "Customers in Sydney are charged a day early" | Favours LID |
| Ordinary local feature | "Add a CSV export of invoices" | Neither |
| Copy or config change | "Rename the 'Overdue' label to 'Past due'" | Disfavours LID |
| Dependency bump or pure refactor | "Upgrade the date library" | Disfavours LID |
| Change that touches many areas | "Add multi-currency support" | Unclear: LID cascades through every area, which costs, and finds every area, which saves |

**Probe changes measure the slope.** The same type of change appears when the project is new, again after about 5 changes, and again after about 15. Comparing what each instance costs shows how cost per change grows with age, which a total across the whole sequence can't show.

**Redirects.** In some changes, the user simulator changes direction partway through. There are two kinds, crossed with two timings:

- **Change of mind:** the person wanted one thing and now wants another, for example "actually, refunds should be pro-rated, not full."
- **Clarification:** the intent was unclear and the agent guessed, and the person now says what they meant.
- **Early:** at the first plan or spec the arm shows the person.
- **Late:** after code has been written.

For each redirect we measure the cost from the redirect to an accepted change, how much the person had to say to get the change of direction across, and whether any artifact still states the abandoned intent afterwards.

**Stating names (the oracle-gap rule).** A hidden test may depend on a name, path, or literal value only if the current change request, or an earlier change, states it. A published audit found that hidden tests that depend on unstated names fail mostly for that reason, not for wrong behaviour (see [sources.md](sources.md)). A requirement stated once in an earlier change and not repeated is fair to test, and testing it is exactly how we measure whether intent survives. A requirement never stated anywhere isn't fair to test. Each hidden test is audited against the whole change history, not just the current change.

Open: how to set the mix of change types. The pilot uses a hand-written mix. Later stages could match the mix to the frequencies seen in real commit histories.

## The user simulator

Every arm expects a person at different points: LID's phase stops, BMAD's persona conversations, Spec Kit's clarify step and review gates. A model plays that person for every arm, using the same model and the same prompt throughout. It holds the hidden oracle, answers only what it is asked, and doesn't volunteer anything.

It runs under two policies, because real users fall somewhere between them:

- **Diligent:** it reads everything the arm shows it and rejects anything that contradicts the oracle.
- **Rubber-stamp:** it approves everything and answers only direct questions.

If an arm wins only under the diligent policy, the published claim says so.

Redirects are scripted events in the change script, delivered by the simulator at the arm's first suitable stopping point for that timing.

To check that the simulator behaves like a person, the maintainer plays the user on a few trajectories, and those results are compared with the simulator's.

Open: whether the simulator's model should come from a different family from the executor's.

## Human cost

Human attention is a headline measure, reported next to token cost and not converted into dollars by us. Each reader can apply their own exchange rate.

Every point where the arm turns to the person is counted, along with the words it asks them to read, and is sorted into one of four kinds:

| Kind | What the person does | Example |
|---|---|---|
| Acknowledgement | Nothing to decide | "Here's the plan. Proceed?" when the plan matches what they asked for |
| Lookup | States a fact they already know | "Which currency do invoices use?" |
| Judgment | Chooses between options the agent sets out | "Should late fees apply to partial payments, or only to full ones?" |
| Origination | Works out intent nobody has stated yet | "What should happen to a subscription when its owner's account is merged with another account?" |

Each touchpoint also records its yield: whether the answer brought out intent that a later hidden test checks. That separates attention that was wasted from attention that prevented a failure.

A judge model sorts touchpoints into the four kinds using a rubric, and is checked against a sample sorted by people before its results are trusted. Wall-clock time and the time a person would spend waiting are recorded too.

## Intent fidelity

Fidelity is measured at three levels. Not every arm has all three.

1. **Behaviour against the oracle (every arm).** Hidden black-box tests run at the fixed external interface. They split into acceptance tests, for what the current change adds, and regression tests, for what earlier changes established. The full suite runs after every change. Some regression tests check latent intent: requirements stated once, early on, and never repeated.
2. **Artifacts against code and against the oracle (arms that keep artifacts).** A cold reader, a fresh agent that sees only the arm's artifacts (for the bare arm, the code and README), answers questions about how the system behaves. We score the answers against the oracle and against what the running code does. This generalizes the idea behind LID's bidirectional-differential skill, a naive reader working intent out again, so it can apply to any system. Some arms may not produce artifacts for which this measure makes sense. If so, that is a finding, and we report it.
3. **Design levels against each other (LID only).** No instrument today checks that LID's HLD, LLDs, and EARS agree with each other. The bidirectional-differential skill covers only EARS against code. Measuring this level here may lead to a separate change to LID, either extending that skill or adding a new one. That change would be its own issue and arrow walk.

LID's own instruments aren't used as the scoring metric when comparing arms, because that would measure LID on its own terms. Their methods can be adapted into neutral measures, as level 2 does.

**Judges** come from a different family from the executor and don't know which arm produced what they are judging. Before a judge is trusted, it is checked against labelled pairs in both directions: the same behaviour under different names (which should pass) and different behaviour under the same names (which should fail).

## Whether intent can be checked in CI

- **Requirement-level mutants, without a model.** Inject a violation of one oracle requirement into an arm's final code, for example changing "late fees start after 30 days" to 31 days. Then run only deterministic checks: the project's own tests and any validator the arm ships. The score is the share of violations that get caught.
- **A cheap cold agent.** A small model with a fixed token budget is asked whether the repository matches its stated intent. The scores are the detection rate, the false-positive rate, and the tokens spent per detection.
- **Cost to trace.** For a sample of oracle requirements, measure what it costs a cold agent, and how accurately it can do it, to find the tests and the code for each one.

## Failures become cost

When hidden tests fail after a change, the simulator files a bug report describing only the symptom, the way a user would, and that report becomes the next change, in a new session. Repair rounds are capped at K. A change still failing at the cap is counted as unresolved, reported separately, and handled in the analysis with a sensitivity check. A regression that slips past one change is charged when it is detected, and its dwell time (how many changes it survived) is recorded.

## Cost accounting

- **Token classes.** Every run records uncached input, cache writes, cache reads, and output tokens separately. Dollars come from a dated table of list prices. Claude Code's `total_cost_usd` is its own estimate, so it is recorded but not trusted on its own.
- **Failed runs count.** Timeouts and harness errors are outcomes, and their spend counts. This differs from the alternate-model runner, which leaves them out of its results. In a cost eval, leaving them out would favour heavy systems, which time out more.
- **Standing context.** Each arm's fixed per-session overhead (its instruction files and skills loaded every session) is measured separately from its per-change work.
- **Run scheduling.** Runs are spread across several days, because infrastructure noise and cache state vary over time. Re-pricing every run as if it had no cache hits gives a sensitivity check.

## Statistics

- **Units of analysis.** A trajectory is one build followed by its change sequence, and it is the unit of analysis, because changes within one trajectory are correlated.
- **Forked checkpoints.** Each trajectory is snapshotted after certain changes, and probe changes are run several times from the same snapshot. That separates the noise in a single change from the noise in a whole trajectory, and one bad build can't spoil every later data point.
- **Reporting.** Pairing is on (seed, change, executor). Cost ratios are reported with cluster-bootstrap confidence intervals, and as the median, mean, and 90th percentile, because agent costs have long tails.
- **Sizing.** The pilot measures variance, and the number of repetitions is chosen from that measurement.
- **Primary comparison.** One comparison is pre-registered as primary, and everything else is labelled exploratory.

**Evidence grades:**

| Grade | Meaning |
|---|---|
| A | Pre-registered; at least two executors and two seeds; the confidence interval excludes no difference; reproduced by someone else |
| B | Pre-registered; one executor or one seed; the confidence interval excludes no difference |
| C | Direction only: the interval includes no difference, or the analysis wasn't planned in advance |
| D | A single trajectory, or an anecdote |

## Fairness

- **Competitors run as intended.** Each runs at a pinned version, installed by its official quickstart and driven by its documented workflow, with no custom prompts beyond what its own docs prescribe. The configuration chosen for each one, and the reason, is recorded in [landscape.md](landscape.md).
- **Other maintainers can check our setup.** We publish a guide to running the eval on one's own system, and invite the maintainers of each compared system to review our configuration for their system, correct it, or run it themselves. If our configuration misuses their system, they can tell us. Their corrections are accepted, and their objections are published next to the results.
- **Everything is published.** That includes the harness, every transcript, the repository at every checkpoint, the oracle (after the runs), and the analysis.
- **Pre-registration.** Hypotheses, the primary comparison, and the analysis plan freeze before the first counted run.
- **Unfavourable results get published.** We commit to publishing results that don't favour LID.

## Known limits

- **The conditions where LID should help most are the hardest to test.** Those are large systems, long-lived ones, several people, and months of forgetting. Fresh sessions stand in for forgetting, but not for a team changing over time, and twenty changes in a day is not two years of maintenance. Published claims will state which conditions they cover.
- **Some value isn't measured.** That includes how well a person understands the system, how easy changes are to review, and how quickly a newcomer learns the system. We state that these aren't measured, rather than letting the numbers imply anything about them either way.
- **Results go out of date.** Every system compared here releases often, some of them every few days. Results are dated, and the harness is built so that re-running it is cheap.

## Open questions

- Where the harness code lives, and how much of the alternate-model runner it reuses.
- Which domain the pilot seed uses.
- Whether the simulator's model should come from a different family from the executor's.
- The repair cap K, and the time limits for builds and for changes.
- Whether to run a second cheap-discipline variant alongside plan mode.
- How to set the mix of change types after the pilot.
