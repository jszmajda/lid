# Research log

Newest entries first. Each entry says what was done, what was decided, and who decided it.

Older entries move to [log-archive/](log-archive/) when this file passes about 2,000 words, and 'Earlier, in brief' at the bottom summarizes them.

## 2026-11-14: The simulated owner, drafted and reviewed

**Decided by the maintainer:** once the simulator is drafted, the main session runs the rest of the pilot on its own judgment, bringing the maintainer only decisions that are really theirs.

**Done.**
- **The owner's prompt template** ([harness/prompts/simulator.md](harness/prompts/simulator.md)) and **`costeval/simulator.py`**. The code parses the oracle and change script, releases the narrative and items by change, and builds the prompt under one of three policies. The owner returns structured output: whether the change is finished, its reply, whether it delivered or dropped a redirect, and an entry for each question it answered. The tests use a made-up oracle. On the real seed, the release gives the right sets at every change.
- **`costeval/executor.py` runs harness roles** (the simulator, extraction, graders) in the container, with only the tools they name. 48 tests pass.
- **Live tests:** six scenarios on Sonnet 5.5, about $0.03 a call, over three rounds of fixes. The first round found a rubber-stamp owner rejecting plans, a diligent owner withholding a correction because it overlapped a pending clarification, a redirect delivered too early, and an owner volunteering rules. Later rounds mostly behaved as designed.

**Claude Fable reviewed the simulator in the maintainer's place,** and found it not ready for counted runs: 4 blockers, 11 major, and 8 minor problems. The review quotes hidden items, so it is kept privately in `seeds/benchtime/hidden/fable-simulator-review.md`. Its main points:
- what the owner is shown is undefined, such as documents the agent asks the owner to read, or plan files;
- the end-of-change review rewarded long reports, and wasn't specified for the bare arm;
- bounded attention, done as a word cut-off, cuts off the question and isn't the design's probability model;
- volunteering still happens on plan review;
- a change of mind's settled view was released before the redirect delivered it;
- the owner has no word-for-word memory of the current change;
- redirect text should be inserted word for word by the harness, and leaks need logging and an independent judge.

**Decided by the main session,** under the maintainer's delegation:
- The end of every change is a review stop, so the bare arm runs under all three policies too. [design.md](design.md) ("The user simulator") now says so.
- Bounded attention drops each correction with a probability that falls as the words shown grow, as the design defines it. The curve is a placeholder until the maintainer-played trajectories calibrate it.
- An open question on a recognized-on-sight topic gets "Show me what you have in mind and I'll tell you if it's wrong."
- The harness inserts redirect text word for word; the owner only decides when.
- Every other fix the review proposed is adopted.

**Next:** fix the simulator, then run each live scenario at least ten times and set a leak-rate threshold before counted runs.

## 2026-11-13 (late night): The harness begins

**Decided by the maintainer:** grading replays the previous checkpoint's calls without a model, as proposed in the night entry, now archived.

**Decided by the main session:** the harness has three parts (trajectories, grading, and reports) that hand records to each other, under the principles in [design.md](design.md) ("The harness").

**Done.** The first two harness modules, written test-first, are in [harness/](harness/README.md). All 30 tests pass.
- **`costeval/usage.py`** reads a session's tokens by model and token class from its result record. It takes each turn's share as the difference between consecutive results, and falls back to summing the transcripts on disk when a run left no result. On the plumbing test's real sessions, the two sources agree to the token, and the twelve turns of the LID walk sum exactly to its final total.
- **`costeval/executor.py`** runs one `claude -p` turn in the executor container, with the arm's two volumes and the token passed by name. It checks the session's start-up record against the arm's plugins, the pinned model and Claude Code version, and memory being off. A live turn worked, and so did a resume from a new container, because the transcript lives in the arm's configuration volume.

**Plan mode works headless,** which closes a plumbing item. A turn in plan mode writes only a plan file, in the configuration volume rather than the repository, and ends by presenting the plan. Resuming with "Approved." in the normal mode builds it. So the cheap-discipline arm opens each change in plan mode, the simulator reviews the plan, and the rest of the change runs normally.

**Next:** the arm configurations, the user simulator, and the trajectory loop that ties them together.

## Earlier, in brief

**The arc so far.** The moved entries cover 2026-11-11 to 2026-11-13, in the order they happened. On 11-11, three separate takes on the design converged on one core design, and a check of old transcripts showed they could not answer the question, so mining them was dropped. On 11-12, the maintainer settled that graders are models. Fifteen candidate projects came back from GPT-6.1 Sol, Gemini 4 Argon, and a fresh Claude Opus 5.5 session, and BenchTime was chosen as the pilot seed and ReleaseDesk as the second. Sol and Argon drafted BenchTime's materials, the main session edited them, and the maintainer decided that each arm defines its own interface. On 11-13, a grading protocol was written into design.md, and the maintainer accepted BenchTime's materials. In the afternoon, about 25 throwaway sessions on Sonnet 5.5 showed that LID's phase stops work headless, and checked isolation, cost accounting, and the fake clock. In the evening, a bare BenchTime build, interface extraction, and grading ran in a Linux container, and the judge caught a seeded mutant on two probes. That night, the maintainer made the container the standard recipe for every executor session. Sol drafted 88 probes, and Claude Fable reviewed them in the maintainer's place, which brought them to 92 and the oracle to version 2. Grading turned out to be the study's biggest cost, so replay was proposed, and the maintainer decided that the harness stays outside LID's arrow.

**Decisions.** Every decision that still stands, with its date and who made it, is in [decisions.md](decisions.md).

**Archive.**

- [2026-11.md](log-archive/2026-11.md): entries from 2026-11-11 to 2026-11-13 (ten entries)
