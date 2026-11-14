# Research log

Newest entries first. Each entry says what was done, what was decided, and who decided it.

Older entries move to [log-archive/](log-archive/) when this file passes about 2,000 words, and 'Earlier, in brief' at the bottom summarizes them.

## 2026-11-14 (later): The simulator passes, the trajectory runner works, grading begins

Run by the main session on its own judgment, under the maintainer's handover.

**The simulator, reworked from Claude Fable's review.** Every finding was worked through. The main changes:
- **One model call per stop serves all three policies.** The model classifies the agent's message, answers its direct questions, and lists each contradiction tied to an oracle item. The harness then keeps every correction (diligent), none (rubber-stamp), or each one on a seeded draw against a placeholder curve over the words read in the change (bounded). It puts the reply together itself.
- **What the owner sees is one rule for every arm:** the final message, the plan from plan mode, and every prose file the message names, shown as its changes since the owner last read it.
- **Redirect timing and words belong to the harness.** A pending change of mind is withheld from the owner until it is delivered.
- **The seed's owner material changed** (oracle version 3, change script version 2, edits E48 to E51 and C1 in the private edit log). A study note and four passages that put recognized-on-sight rules or a graded boundary into the owner's own words came out of the narrative, and change 2's redirect now lists the items it brings in. No probe or graded behaviour changed.
- **A leak judge (Opus 5.5) and a trimming call.** The first ten-run sweep of 15 scenarios passed every structural check but one. The judge, though, found the owner restating whole rules, with their other clauses and exact boundaries, in up to 9 of 10 runs of a scenario. Prompt changes alone brought most scenarios down but not all. A separate trimming call, which sees only the agent's message and the owner's draft parts, cuts each part to what the question or the quoted wrong words need.
- **Result:** the final sweep (15 scenarios × 10 runs) passed every check, and the judge confirmed no leaks or inventions. Spot checks show the trimming keeps what corrections need. The threshold for counted runs (at most 5% of replies, and no scenario above 2 in 10) was set before this sweep. About $9 notional on the subscription across the sweeps.

**Arms and the trajectory runner.**
- The three pilot arms are data in [harness/arms/](harness/arms/). LID Full runs v1.4.6 from this repository and starts the first build with `/linked-intent-dev`.
- `run_trajectory.py` runs a change between the agent and the owner, commits at its end, records every turn and owner call in the git-ignored `runs/` folder, and runs symptom diagnostics before symptom changes. `audit_owner.py` runs the leak judge over a real trajectory's replies.
- 103 tests pass.

**Pilot stage 0 is running** (all three arms on Sonnet 5.5, the first build plus changes 1 and 2, the diligent owner).
- **A false start:** Claude Code 2.1.323 loads four built-in plugins in every session (two more than a day earlier, under the same version), which the start-up check counted as outside the arm. The runs were stopped after a few minutes and restarted. Built-ins now count as part of the harness and are recorded with every turn.
- **Bare and cheap discipline finished all three changes**, at $0.85 and $1.22 notional. LID Full's first build took 8 owner stops and $2.56, against $0.52 for bare and $0.70 for cheap discipline.
- **Plumbing checks:**
  - cheap discipline's plan mode, the owner reading plans and the files they name, and change 2's redirect firing at the first plan (bare got it with its completion report, after code);
  - the owner answering with no view where it had none;
  - the leak audit found nothing in the 12 replies of the finished arms.

**Grading is built and runs end to end.**
- A control server inside each app container starts the arm's service under libfaketime, forwards requests, sets the clock, restarts, restores named setups, runs only the setup commands the reference names, and writes the execution log itself. Graders reach it only through `gt`, from a container without the source.
- Extraction (Sonnet) writes the reference and a start spec, a setup session loads and snapshots each setup, Haiku executes probes in batches across parallel workers, and Haiku judges each batch's log.
- **A first try on four probes** found two setup problems, both fixed: the reference's examples used a different admin token from the instance's, and probes ran on empty setups. On the second try two probes were met. One came back "couldn't exercise" because the executor did one case's steps out of order, and the prompt now forbids that. In the other, a concurrent hold was refused for the wrong reason. libfaketime was checked under 16 concurrent threads and held, so the wrong reason is the arm's own behaviour. The judge's verdict there is kept as a calibration case.
- Probes needing prior-data are reported as not run until that's built.

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
