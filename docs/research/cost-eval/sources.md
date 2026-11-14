# Sources

Each source says how closely it was read. Labels, from closest to least close:

- **raw**: the full text was read as raw text, for example through the GitHub API.
- **partly verbatim**: part of the text was read verbatim and the rest through a fetch tool's summary.
- **summary**: a fetch tool read the whole page and returned a model-written summary. Check any number or quote against the original before using it publicly.
- **skim**: only the abstract or part of the page was read.
- **snippet**: only a search-result snippet was seen.

All sources were gathered on 2026-11-11 unless marked otherwise.

## Measured comparisons of SDD systems

- **Uvik Software, SDD benchmark** (vendor blog; runs 2026-10-15, updated 2026-11-02). [uvik.net](https://uvik.net/blog/spec-driven-development-benchmark/), summary.
  - Setup: 50 brownfield Python tickets from five private client repositories; Spec Kit 1.0, Kiro, BMAD 6, OpenSpec, and a control with no spec; one model (claude-sonnet-5); a blind reviewer judged whether each change would merge; no hidden tests.
  - Results: merge rates of 84% for OpenSpec, 82% for Kiro and BMAD, 80% for Spec Kit, and 72% for no spec. Cost per merged ticket was $2.35 to $4.23, with no spec at $2.43. The no-spec arm used the most tokens while building.
  - The authors' noise band was ±10 points, so they didn't rank the arms. The summary also reported internal inconsistencies in the drift figures.
  - They wrote that "long-term value of a living spec across many changes was not measured." That untested question is our main hypothesis.
- **Jain, "Are Harnesses Worth the Cost?"** (martinfowler.com, 2026-10-13). [link](https://martinfowler.com/articles/are-harnesses-worth-the-cost.html), summary.
  - Setup: a harness of contract specs, examples, and executable checks, against no harness; one greenfield Java service; 10 paired runs per model; 178 hidden functional checks.
  - On the flagship GPT model, the harness cost about 10 times the tokens, with 10/10 acceptance either way.
  - On the cheap model, the harness raised acceptance from 3/10 to 10/10, and the harnessed cheap model cost less than the unharnessed flagship.
  - No spread was reported. This is evidence for H5.
- **Böckeler, "TDD inside the agent loop"** (martinfowler.com, 2026-08-10). [link](https://martinfowler.com/articles/exploring-gen-ai/tdd-in-the-agent-loop.html), summary.
  - Test-driven runs used 3 to 8.5 times the tokens, with no quality gain on a strong model.
  - Agents often skipped or faked the step where a test should fail first.
  - Token counts included cache reads.
- **Edwards-Alexander, "The Economic Benefit of Refactoring"** (martinfowler.com, 2026-07-30). [link](https://martinfowler.com/articles/exploring-gen-ai/refactoring-economic-benefit.html), summary.
  - The same change was replayed after each of 15 refactoring steps, and input tokens fell 83%.
  - Evidence that the structure of the code, not only the spec, drives what later changes cost.
  - One run per step; tokens estimated as characters divided by 4.
- **"Evaluating AGENTS.md"** (arXiv 2602.11988, 2026-02). [link](https://arxiv.org/abs/2602.11988), snippet. Context files gave no gain in success and about 20 to 23% higher inference cost.
- **"Citation Discipline in SDD" (traceSDD)** (arXiv 2606.30689, 2026-06). [link](https://arxiv.org/html/2606.30689v1), summary.
  - Per-line requirement citations made runs less deterministic, but caught 86 to 88% of injected scope creep with no false positives.
  - Relevant to what LID's `@spec` annotations buy.
  - The author promotes their own framework.

## Anecdotes and single runs

- **Scott Logic, on Spec Kit** (2025-11-26). [link](https://blog.scottlogic.com/2025/11/26/putting-spec-kit-through-its-paces-radical-idea-or-reinvented-waterfall.html), summary. One feature took 33.5 minutes of agent time and 3.5 hours of review with Spec Kit. With iterative prompting it took 8 minutes and 15 minutes.
- **OpenSpec against Spec Kit token test** (Medium). [link](https://medium.com/it-chronicles/is-your-safe-choice-burning-your-budget-1cfddf8782e4), snippet. OpenSpec used about half the tokens of Spec Kit in two tests.
- **The "Reenbit" and "Hashrocket" comparisons** were seen only second-hand, and no primary source was found. Not used.

## Qualitative comparisons

- **Böckeler, "Understanding Spec-Driven-Development: Kiro, spec-kit, and Tessl"** (martinfowler.com, 2025-10-15). [link](https://martinfowler.com/articles/exploring-gen-ai/sdd-3-tools.html), summary.
  - Introduced the spec-first, spec-anchored, and spec-as-source levels.
  - Found the tools effectively spec-first, with maintenance "left vague or totally open."
- **"SDD as Prescribed and as Practiced"** (arXiv 2608.25202, 2026). [link](https://arxiv.org/abs/2608.25202), skim. Practitioners check specs against code mostly when a change is finished, not continuously.
- **A taxonomy of SDD systems** (arXiv 2606.04967, 2026-06). [link](https://arxiv.org/abs/2606.04967), skim. A rubric-only comparison that notes "the absence of full-process benchmarks."

## Benchmarks of changes over time

- **SlopCodeBench** (arXiv 2603.24755, v2 2026-05). [paper](https://arxiv.org/abs/2603.24755), partly verbatim; [repository](https://github.com/SprocketLab/slop-code-bench), raw README, MIT license; [site](https://www.scbench.ai/).
  - Setup: 36 problems with 196 checkpoints in Python. Each checkpoint updates the spec in prose covering only observable behaviour, with hidden tests split into core, error, functionality, and regression. The agent carries its own workspace forward into a fresh container, in its native harness.
  - Cost per checkpoint grew about 2.2 times from first to last.
  - Code erosion predicted the next checkpoint's cost.
  - Prompting for quality reduced the initial mess but not the rate of decline.
  - Agents get a Jinja system-prompt template. Plugin and project instruction-file support is unverified.
  - A full run cost roughly $40 to $620 depending on the model.
  - The closest template for our design.
- **SWE-CI** (arXiv 2603.03823, 2026-03). [link](https://arxiv.org/html/2603.03823v2), summary.
  - Up to 20 iterations of incremental requirements, written by an architect agent.
  - Its EvoScore weights later iterations more heavily, which rewards code that is easy to keep changing.
- **EvoClaw** (arXiv 2603.13428, 2026). [link](https://arxiv.org/abs/2603.13428), summary.
  - Agents succeeded on more than 80% of tasks run on their own, but at most 38% when the same tasks ran continuously.
  - It scores new behaviour and preserved behaviour separately.
- **SLUMP** (arXiv 2603.17104, 2026-03). [link](https://arxiv.org/abs/2603.17104), skim.
  - Specs revealed bit by bit were followed less faithfully than specs given all at once.
  - An external project-state layer recovered 90% of the gap. This is the closest published evidence that keeping spec state helps across a sequence of changes.
- **SWE-EVO, SWE-Chain, and RoadmapBench** (2026). skim or snippet. Multi-step evolution benchmarks built from release notes, chains of changes, or version upgrades.

## Grading validity

- **"What the Specification Did Not Say: Specification-Oracle Gaps in Test-Graded Coding-Agent Benchmarks"** (arXiv 2610.30635, 2026-10-22). [link](https://arxiv.org/abs/2610.30635), partly verbatim.
  - The grader is an executable test suite taken from a reference solution, not an LLM judge.
  - A gap is a name, path, or literal value that a test needs and the task neither states nor lets the agent infer.
  - Example: a server-sent-events task needed a constant named `valueSSE`. Of 34 analysed runs, 32 built the behaviour, but the 23 that named the constant something else (most often `valueEventStream`) passed none of the 84 tests.
  - Units with a gap failed in 80.6% of runs, against 48.4% for comparable units without one.
  - The paper's fix is to state the names the tests need, or to exclude tests that reach into internals.
  - The lesson for us is narrow: a deterministic test can't grade output whose names the agent chooses. That is one reason our graders are models.
- **DeepSWE** (arXiv 2607.07946, 2026-07). [link](https://arxiv.org/abs/2607.07946), skim. Hand-written verifiers disagreed with an LLM judge 1.4% of the time, against 32.4% for tests inherited from upstream repositories.

## Measuring cost

- **"Token Reduction Is Not Cost Reduction"** (arXiv 2607.12161, 2026). [link](https://arxiv.org/abs/2607.12161), skim.
  - Cutting tokens and cutting cost correlated at only r = 0.15, and one token cut raised the bill.
  - It recommends cost per successful task.
- **Prompt caching across providers** (arXiv 2601.06007, 2026-01). [link](https://arxiv.org/abs/2601.06007), skim. Caching cut cost by 41 to 80%.
- **Anthropic, "Infrastructure noise"** (2026-02-05). [link](https://www.anthropic.com/engineering/infrastructure-noise), summary.
  - Container resource limits moved benchmark scores by 6 points.
  - Recommends running at several times and on several days.
- **Claude Code cost and headless docs.** [costs](https://code.claude.com/docs/en/costs), [headless](https://code.claude.com/docs/en/headless), summary. JSON output includes `total_cost_usd`, which is a client-side estimate at list price.
- **Tessl, reading evaluation results.** [link](https://docs.tessl.io/improving-your-skills/reading-evaluation-results.md), summary. "Start with at least three repeats," and "a missing measurement is different from a measured zero."
