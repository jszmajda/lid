# Brainstorm by Claude Fable (2026-11-11)

One of the three independent design takes collected at kickoff. A Claude Fable session got the maintainer's proposal (paraphrased), the HLD, issue #75, and the alternate-model eval design. It didn't see the main session's ideas. Its facts about competitors came from memory and were checked afterwards by the landscape survey ([landscape.md](../landscape.md)). The text below is its report, unedited apart from formatting.

The other two takes were a brainstorm in the main session and a survey of the landscape and literature. The survey's findings are in [landscape.md](../landscape.md) and [sources.md](../sources.md). The main session's points were merged directly into [design.md](../design.md).

## The five ideas that matter most

- **[TOP 1] The proposal answers a different question than #75 asks.** #75 wants "walking the arrow vs not walking it" and a break-even by project size. None of its four acceptance criteria needs a competitor. The first comparison should be LID vs a bare agent vs a cheap discipline baseline ("good AGENTS.md, write tests, keep a NOTES.md"). That last one is the dangerous rival, not BMAD.
- **[TOP 2] The hypothesis is about a slope, so measure the slope.** "LID shines later" means the marginal cost of an accepted change grows more slowly with system age. Apply the same class of probe change at ages 0, 5 and 15, per arm. Totals over one trajectory cannot show this.
- **[TOP 3] Use forked checkpoints, not only full trajectories.** Build each arm's trajectory, snapshot it at checkpoints, then run each change N times from the same snapshot. That separates per-change variance from trajectory variance and stops one bad build poisoning 20 data points.
- **[TOP 4] The simulated user is the experiment.** LID's mechanism is the human resolving ambiguity. A headless run with "take the default" removes the treatment and measures only the overhead. You need an oracle user holding hidden intent, with attention metered, under at least two user policies.
- **[TOP 5] Expect a ceiling effect, and decide now to publish it.** At affordable sizes a frontier model with no SDD will pass most hidden tests. The likely result is "LID costs k× more with no measurable fidelity gain at sizes we could afford". That is a legitimate answer to #75's "honest about where LID is not worth it".

## 1. The question itself

- "Cheaper than X under Y" is the wrong first claim shape. It turns the work into a leaderboard, which the HLD rejects ("LID is not in the SDD methodology category competing for the same slot"). A maintainer-run leaderboard also gets disputed rather than believed.
- A better claim shape: "at fidelity bar F, on an executor of class E, LID's cost per accepted change is k× baseline at age 0 and k′× at age N; the curves cross at about N* (CI), or do not cross within the range tested."
- Cost without fidelity is meaningless. The unit is **cost to an accepted change**: tokens plus metered human attention until the hidden acceptance suite passes, with all earlier changes still passing. Report the (cost, fidelity) pair, never a scalar.
- "Not a quality eval yet" does not hold. Once cost is conditioned on fidelity, it is a quality eval, so design the fidelity measure first.
- Break-even, operationally: the change index where cumulative cost-to-fidelity curves cross, per size tier. It depends on the price of human attention, so report it as a function of $/human-minute. "No crossing observed" is a valid result.
- There are two break-even axes, project size (#75) and change count (the proposal). Do not collapse them.
- "Nobody compares because the approaches differ" is half the reason. The other half is that the results are expensive and likely unflattering. Differing approaches are an argument for black-box outcome measures, not for skipping comparison.

## 2. The change sequence

- Pre-register a taxonomy with a predicted direction per class before any run.
- Changes that should favor LID:
  - a change that silently contradicts a decision made 10 changes earlier and not visible in code;
  - a non-local invariant ("all money rounding is banker's");
  - a bug that is really an intent divergence;
  - a change that needs the "why" of an earlier tradeoff.
- Changes that should disfavor LID:
  - a typo, copy change or config flip;
  - a dependency bump;
  - a pure refactor;
  - visual polish;
  - a throwaway spike;
  - a reversal (add a feature, then remove it, so the docs must be torn down too);
  - a cross-cutting change that fans out over many segments and pauses at each.
- Neutral: an ordinary local feature.
- Honesty mechanisms:
  - set the class mix from the empirical distribution in real commit histories, not by hand;
  - have someone who does not know LID's internals author the changes, or an agent given only a neutral brief;
  - report per class, never only pooled.
- Fresh session per change should be the default. It is the HLD's own premise ("each session brings a new capable programmer"). Same-session is an ablation, and it favors the bare arm.
- Claude Code auto-memory leaks intent across "fresh" sessions. Disable it in all arms, or declare it part of the baseline.
- Turning failure into cost:
  - a failing hidden test becomes a templated user bug report that describes behavior, not the test;
  - a new session handles it, capped at K rounds, with all cost summed;
  - still failing at the cap is censored, reported separately, with a sensitivity analysis.
- Re-run the full hidden suite after every change. Charge an escaped regression when it is detected, and report its dwell time (how many changes it survived).

## 3. Measuring intent fidelity

- Primary: hidden black-box acceptance tests at a fixed external interface (CLI or HTTP), written from an oracle intent document. The interface contract goes to every arm.
- Latent-intent probes: requirements stated once, early or only on asking, never restated in the change prompt. This is the gap LID claims to close, so it is the fidelity signal that matters.
- Artifact truthfulness, system-neutral: a cold agent gets only the arm's artifacts (bare arm: code plus README) and answers "what does the system do when…". Score against the oracle. This measures doc rot without privileging any format.
- LLM judge for the residue only, from a different provider than the executor, blind to arm. Validate it against a human-labeled sample first.
- Do not use LID's own instruments (differential audit, arrow audit) as metrics. That is home-field measurement.
- Risk: the LID arm writes tests from EARS, and the hidden tests come from an oracle a LID-minded author wrote in EARS-like form. Have the oracle written as narrative product prose by someone else.

## 4. "Testable in CI"

- This conflates structural checkability (links exist) with semantic checkability (behavior matches intent). Only executable tests are semantic and mechanical. A `@spec` tag can lie.
- A naive "does it ship a validator" metric favors OpenSpec-style tools and penalizes LID, whose Non-Goals reject linters and CI gates. It also rewards structure over truth.
- System-neutral operationalization by mutation, in two tiers:
  - **Tier A (model-free):** inject intent violations into each arm's final repo (code violates a stated requirement; a spec changes without the code). Run only deterministic checks: the project's tests plus any validator the system ships. Score is detection rate, effectively a requirement-level mutation score against the oracle's requirement list.
  - **Tier B (cheap agent):** a cold small model with a fixed token budget is asked "does this repo match its stated intent?". Score is detection rate, false-positive rate and tokens per detection. This is where attestation should pay off if it is real.
- Traceability cost: for a sampled oracle requirement, tokens and accuracy for a cold agent to find its tests and implementation.

## 5. Human-in-the-loop simulation

- Oracle user: an LLM holding the hidden intent document. It answers truthfully only what is asked, never volunteers, and approves or rejects against the oracle. Use the same simulator model and prompt for every arm.
- Run two policies to bracket reality:
  - **Diligent:** reads everything and catches oracle-contradicting artifacts with probability p.
  - **Rubber-stamp:** approves everything and answers only direct questions.
- Real users sit between the two. If LID only wins under Diligent, say so.
- Attention accounting: count interrupts, questions asked, and words presented for review. Convert at a stated reading rate and report minutes separately from tokens. The exchange rate is the reader's to choose.
- At realistic rates, human attention likely dominates token dollars. A tokens-only eval measures the cheap resource, and LID spends attention deliberately ("Lean toward the human's attention").
- Tooling gap: the alt-model runner supports one scripted `follow_up`. A multi-turn simulator loop is new work on both harnesses (`claude -p --resume`, `opencode --continue`).
- Validate the simulator by having a human play user on a few trajectories and comparing outcomes.

## 6. Fairness to the competitors

- Each system at a pinned version, installed by its official quickstart, driven by its documented flow. No custom prompts unless that system's docs prescribe them.
- Send the configuration to each competitor's maintainers before running. Accept their PRs and publish their objections alongside results.
- Pre-register seeds, change sets, primary metric, primary contrast, exclusion rules and the censoring cap. Commit the registration hash before the first run.
- Publish everything: transcripts, repos at every checkpoint, the oracle after the run, and the harness.
- Conflict of interest: "intent fidelity" is LID's frame, and Spec Kit and BMAD optimize other things. State the outcome neutrally as "behavioral correctness against requirements stated over time".
- Include LID ablations (Full vs Scoped, with and without arrow-maintenance, review-depth). They answer #75's "proportional cost" directly and carry no conflict-of-interest problem.

## 7. Confounds

- **Model family is perfectly confounded with harness** (Claude only via `claude -p`, everything else via opencode). Within-executor comparisons across systems are clean; cross-executor comparisons are not. Treat (harness, model, effort) as one executor and make claims per executor. "2-3 families" then shows robustness of the ranking, not model effects.
- Each system integrates differently per harness (skills vs slash commands vs rule files). A system can lose because its opencode port is weak. Record integration quality per cell.
- Caching: cache hits depend on pacing and parallelism. Report raw token classes (input, cache-write, cache-read, output, reasoning), then price at a dated list-price table. The subscription being "sunk" is irrelevant to the published number.
- **The existing runner drops `timeout` and `harness_error` from results. In a cost eval that biases toward heavy systems**, which time out more. Timeouts must count as outcomes with their spend. The 10-minute default is also too short for builds.
- Version drift: SDD tools ship often, and OpenRouter can re-route providers. Pin the provider and date-stamp every claim. Results have a shelf life of months.
- Training-data familiarity: models have seen far more Spec Kit than LID, and may have memorized any OSS seed.
- Seeds that already carry LID docs: keeping them gives home advantage, stripping them is a handicap. See section 8.
- Compaction and context limits differ by harness. Log compaction events.
- Medium effort is fine as a pin, but it is one point. If a competitor documents a recommended effort, note the mismatch.

## 8. Seed projects

- Greenfield synthetic apps with an authored oracle are the control: uncontaminated, with latent intent by design. The weakness is that agent-built large apps are unreliable and costly, so greenfield tops out at the medium tier.
- For brownfield, use a common pre-built codebase for all arms. Each system bootstraps its own intent artifacts by its own onboarding flow, and that cost is metered as "adoption cost", which users want to know. This removes build variance.
- Real history replay: an OSS repo at commit C0, the next N real issues as change requests, the tests those PRs added as hidden tests. It has the highest realism and an honest change mix. The weaknesses are contamination and under-specified issues.
- The maintainer's own LID projects are the worst seeds for comparison (home field) and the best for descriptive cost accounting (section 10, Stage 0).
- "Interesting" means decisions invisible in code, non-local invariants, and domain rules with exceptions (pricing, permissions, time, state machines). It also means at least three components with implicit contracts, and requirements that later conflict.
- Size tiers should be defined by ratio to the executor's context window (code tokens well under, near, or several times the window), not by lines of code. LID's navigation claim is keyed to the window. With large-context models the "several times" tier is big and must be brownfield.

## 9. Statistics and precision labeling

- The unit of analysis is the trajectory, not the change, because changes within a trajectory are correlated. Use a cluster bootstrap or a hierarchical model. The effective N will be small, and the report should say so.
- Pair on (seed, change, executor). Report ratios with bootstrap CIs.
- Agent costs are heavy-tailed. Report median, mean and P90, and never the mean alone.
- Estimate variance in the pilot, then set repetitions by power. Do not pick N in advance.
- Pick one pre-registered primary contrast. Everything else is labeled exploratory, because the matrix invites forking paths.
- A possible evidence-grade scheme:
  - **A:** pre-registered, at least 2 executors, at least 2 seeds, CI excludes 1, externally reproduced.
  - **B:** pre-registered, one executor or one seed, CI excludes 1.
  - **C:** directional, CI includes 1 or post hoc.
  - **D:** single trajectory or anecdote.
- Every published claim carries its scope: system versions, executor, effort, user policy, size tier, date.

## 10. Budget and staging

- **Stage 0 (near-free, do first):** descriptive cost accounting. If past Claude Code session transcripts for real LID projects are retained, mine token usage by phase. This partly answers "what does walking the arrow cost" before any experiment and shows which phases dominate.
- **Stage 1 pilot:**
  - one small-to-medium seed;
  - three arms: bare, cheap-discipline baseline, LID Full;
  - one executor: `claude -p` on a mid-tier Claude model at medium effort (quota, paced);
  - 8-10 changes including three same-class probes at different ages;
  - 3 trajectories per arm, and 3 repetitions per change from forked checkpoints;
  - both user policies.
- The pilot's purpose is to learn whether the fidelity metric discriminates at all (the ceiling check), the variance, whether the simulator is viable, and real cost per trajectory. If the bare arm is at ceiling, make the seed harder before spending more.
- **Stage 2:** add one competitor (the most change-centric one), and LID Scoped.
- **Stage 3:** a second executor through opencode, for real dollars. Set a hard cap from the pilot's measured tokens per trajectory, and use a per-batch low-limit key.
- **Stage 4:** the brownfield large tier and history replay.
- Spend on repetitions before breadth. Three model families at N=1 teach less than one family at N=5.

## 11. What is missing, and how this could mislead

- The regime where LID is hypothesized to win (large, long-lived, several humans, months of forgetting) is the one the eval cannot afford. Twenty changes in a day is not two years, and human forgetting is unmeasured. The eval samples the regime where LID should lose, and readers will generalize from it.
- A perfect, patient oracle user flatters any elicitation-heavy system. A rubber-stamp user makes the stops pure overhead. Without both, the user policy is a hidden parameter that decides the answer.
- Value that tokens and tests do not capture: human comprehension of the system, reviewability, onboarding. State these as unmeasured. Do not let them be implied by the numbers or dismissed by them.
- Wall-clock time and human waiting time are costs users feel. Record them.
- The harness is the durable product. Results go stale with each model and tool release, so design for cheap re-runs and publish dated runs.
- Goal 5 says site claims must trace to the arrow. A cost claim is intent, so the eval's design, registration and results need a home in the tree before the site cites them.
- If the result is bad for LID, #75's scope says acting on it is downstream. Agree in advance that an unflattering result gets published, or the pre-registration means nothing.
