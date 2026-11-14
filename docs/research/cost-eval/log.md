# Research log

Newest entries first. Each entry says what was done, what was decided, and who decided it.

Older entries move to [log-archive/](log-archive/) when this file passes about 2,000 words, and 'Earlier, in brief' at the bottom summarizes them.

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
