# Research log

Newest entries first. Each entry says what was done, what was decided, and who decided it.

Older entries move to [log-archive/](log-archive/) when this file passes about 2,000 words, and 'Earlier, in brief' at the bottom summarizes them.

## 2026-11-13 (later): Seed materials accepted; the log gets compacted

**Decided by the maintainer.**

- **BenchTime's materials are accepted** as reasonable, including the three edits marked for review: moving the cancellation-reason item to change 7, adding the one-hold-per-person item, and replacing the probe with the slot finder. Their hashes are recorded as version 1 in [seeds/benchtime/README.md](seeds/benchtime/README.md).
- **The log shouldn't grow without limit.** A subagent should move older entries into an archive and summarize them from time to time. Haiku is enough for the job.

**Decided by the main session**, which the maintainer left to it:

- **When:** once `log.md` passes about 2,000 words. At the pace so far, that means every two or three working sessions.
- **What stays:** the newest entries, up to about 1,000 words. Everything older moves word for word into `log-archive/YYYY-MM.md`.
- **The summary:** an "Earlier, in brief" section of up to about 400 words keeps the arc and the decisions that still stand, each with who decided it.
- **Where it lives:** the procedure is in [upkeep/compact-log.md](upkeep/compact-log.md). The README tells whoever updates the log to check the word count, so nobody has to remember.
- **The first run:**
  - Haiku moved the four oldest entries word for word into [log-archive/2026-11.md](log-archive/2026-11.md), and the main session checked every entry against a saved copy.
  - The summary Haiku wrote held a list of standing decisions that would grow without limit. The list moved into a ledger, [decisions.md](decisions.md), one line per decision with its date and who made it, and the summary's cap became about 300 words.
  - Two decisions the log didn't attribute were the main session's: the editing rules and keeping hidden materials private.
  - The log went from 2,800 words to about 1,100.

## 2026-11-13: A grading protocol

**The gap the maintainer found.** The design said how graders would be calibrated and spot-checked, but not what a verdict is, how one is reached, or how verdicts are scored and reported. The oracle's grading sketches also leave room for interpretation.

**Done.** [design.md](design.md) now has a "Grading protocol" section:

- **Verdicts.** Each item in force gets a verdict at each checkpoint: met, not met, or couldn't exercise.
- **Probes.** Each item gets one or more probes, written before any counted run. A probe is a scenario plus an expected observation, in terms of operations. An item is met only if all its probes pass.
- **Separate execution and judgment.**
  - Execution records every request, response, and clock setting in a log, without deciding anything.
  - A separate judgment session compares each expected observation with the log and cites its evidence.
  - A verdict can therefore be judged again or checked by another model without running the software again.
- **Checks on the graders:**
  - seeded violations, which give known answers;
  - labelled pairs;
  - test-retest at both steps;
  - cross-family judging of logs;
  - maintainer spot checks that over-represent "not met", "couldn't exercise", and latent items.

  Graders are trusted at about 90% agreement and under 5% flips.
- **Disagreements.** The maintainer's verdict stands, and a pattern of disagreement on one item leads to a new version of its probes and a re-judgment of every log.
- **Scoring.** Verdicts are rows. Fidelity is met divided by met plus not met. "Couldn't exercise" is reported separately and, as a sensitivity check, also counted as not met. Breakdowns are by disclosure kind, new against preserved items, and change type. Regressions are reported with the change that caused them and how long they survived.

Probes and the seeded-violation calibration set were added to M1 in [plan.md](plan.md). The plumbing test now also checks whether a Haiku grader can work from an extraction reference.

## 2026-11-12 (night): Each arm designs its own interface

**The problem the maintainer raised.** The first brief held a 1,500-word API contract alongside the owner's rules. That has three costs:
- no real owner hands over a contract like that;
- it leaves the processes little to do, because turning loose intent into a design is where they are supposed to earn their cost;
- it makes a ceiling more likely.

**Decided by the maintainer.** Each arm defines its own interface. A step before grading extracts the interface for the grader.

**What that changed in [design.md](design.md):**
- **The brief.** It is in the owner's words and fixes only the stack, one start command documented in the README, one data location, and reading the current time from the system clock.
- **Interface extraction.** A new step reads each checkpoint's repository and running software and writes a neutral reference to the interface. It follows a fixed template, says how to call things but never what they should do, and isn't charged to the arm.
- **A third verdict.** Graders can now return "couldn't exercise", so an awkward API doesn't count as lost intent.
- **Clock and reset.** The harness controls the clock from outside (for example with `libfaketime`, to be confirmed in the plumbing test) and resets state by starting from an empty data location. The brief needs no test hooks.

**Done.**

- **Sol revised the oracle and change script** for this ([prompts/03-revise-without-interface.md](seeds/benchtime/prompts/03-revise-without-interface.md)), keeping the main session's earlier edits. Rules that had lived in each change's interface additions became owner wording or new items (BT-44 to BT-55), and pure API shape was dropped.
- **Argon wrote an owner-voice brief** ([prompts/04-owner-brief.md](seeds/benchtime/prompts/04-owner-brief.md)).
- **The main session made six more edits** (E10 to E15, logged privately):
  - dropped two items that were only API validation limits;
  - reclassified one item as stated;
  - stopped one item from marking an arm down for adding a feature;
  - reworded a stated item so it doesn't give away an askable one;
  - rewrote the brief in the lab manager's voice, about 550 words against 2,300 before.
- **The fixed-interface versions stay** in `hidden/fixed-interface-v1/` as a fallback, in case graders can't work through interfaces they discover.

The revision cost about $0.25.

## Earlier, in brief

**The arc so far.** The moved entries cover 2026-11-11 to 2026-11-12, in the order they happened. On 11-11, three separate takes on the design converged on one core design: fresh sessions per change, hidden behaviour tests at a fixed interface, the slope of cost per change as the measure, a user simulator, and pinned versions. Checking old transcripts showed they could not answer the question, so mining them was dropped. On 11-12, the maintainer settled that graders are models. Fifteen candidate projects came back from GPT-6.1 Sol, Gemini 4 Argon, and a fresh Claude Opus 5.5 session, and Claude Fable reviewed the plan. Later that day, BenchTime was chosen as the pilot seed and ReleaseDesk as the second, every point in the plan review was adopted, and the cost constraints were set. In the evening, Sol drafted the interface, oracle, and change script, and Argon drafted the brief. The main session edited both, marked three edits for the maintainer's review, and kept the drafts unedited.

**Decisions.** Every decision that still stands, with its date and who made it, is in [decisions.md](decisions.md).

**Archive.**

- [2026-11.md](log-archive/2026-11.md): entries from 2026-11-11 and 2026-11-12 (four entries)
