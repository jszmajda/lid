# Research log

Newest entries first. Each entry says what was done, what was decided, and who decided it.

Older entries move to [log-archive/](log-archive/) when this file passes about 2,000 words, and 'Earlier, in brief' at the bottom summarizes them.

## 2026-11-13 (evening): The plumbing test, second half

**The maintainer supplied** a long-lived subscription token (an OAuth token from `claude setup-token`, kept outside the repository), so executor sessions could be tried in a container. The whole plumbing test came to about 30 invocations and $4.15 at list price, all on the subscription.

**The container works.**
- `claude -p` runs on the subscription inside the executor image, as a non-root user with permissions bypassed.
- With the token login, the account email doesn't reach the session. The git user is the image's neutral identity, memory is off, and only Claude Code's built-in skills load.

**A bare build of BenchTime.** A bare Sonnet 5.5 session built BenchTime from the brief in the container. It took 4 minutes and $0.56, and produced one commit, 9 tests, and a README with the start command and the data location.
- It added logins nobody asked for: a manager token stored in the data location, and a token for each person.
- It asked no questions. It settled several askable points itself and listed them in its README under "Interpretations of the brief (please check these)". The plumbing prompt left out the neutral sentence saying the owner can answer questions, so this says nothing yet about whether bare arms ask.
- The simulator design has to decide whether a list like that counts as asking, so that the owner's end-of-change review answers it.

**Interface extraction.** A Sonnet session in its own container, working on a clone of the committed repository, wrote a 1,500-word reference from the draft template. It made every call once against the real service, for $0.42.
- It took 23 minutes, because it waited out a real ten-minute hold expiry. Extraction should run under the fake clock.
- It copied the template's instruction line into its heading.
- Real error messages carry some rule text, such as "at most 3 upcoming confirmed bookings". The template allows real responses, the grader sees the same messages at grading time anyway, and the judge never sees the reference.

**Grading.** The service ran from a checkpoint image under `libfaketime`, and a reset started a new container. A Haiku 5.5 session ran the four plumbing probes through `gt`, seeing only the reference and the probe scenarios. A second Haiku session judged the execution log against the expected observations.
- **Execution:** all four probes, 87 logged calls, 2 minutes, $0.62. It found that each reset issues a new manager token and re-read it every time. It recorded which identifier the service gave each fixture, and it never looked at the source.
- **Judgment:** all four met, citing the right log lines, in 10 seconds for $0.10. The cited hold shows creation at 08:00, expiry at 08:10, and confirmation at 08:09 on 2026-01-05, so the fake clock reached the arm's own code.
- **A seeded mutant** of the same build allowed a fourth upcoming booking and a checkout at the booking's exact end. Execution ran the same way ($0.68). The judge marked P-BT07-a and P-BT11-a not met, citing the two offending responses, and left the other two met ($0.11).

**What the harness needs from this.**
- **Probes in batches.** Each probe re-loaded the lab, about 13 calls, and the session took one turn per call, so a session's cost grows faster than its length. Execution should run a few probes per session. Because all data lives in one location, the harness can also snapshot that location after the first setup and restore it, instead of having the grader rebuild the lab.
- **A rough grading cost,** to be checked in calibration: about $0.15 per probe at list price on Haiku as run here. At roughly 80 probes per checkpoint, that's $10 to $15 of subscription quota per graded checkpoint before snapshots.
- **`gt`'s command operation can open the source.** Haiku used it only to read the manager token, but the harness has to limit it.
- **The checkpoint is the arm's last commit.** Extraction and grading used a clone, so uncommitted files didn't count. The harness should commit whatever an arm leaves uncommitted at the end of a change.

**Decided by the main session.** Grading execution runs in batches of a few probes per session. [design.md](design.md) now says so, and its answered open questions, about the clock and how the grader reaches the software, are folded into its text.

**Waiting on the maintainer.** Whether executor sessions run in the container as the standard recipe. The maintainer supplied the token for the trial.

## Earlier, in brief

**The arc so far.** The moved entries cover 2026-11-11 to 2026-11-13, in the order they happened. On 11-11, three separate takes on the design converged on one core design: fresh sessions per change, hidden behaviour tests at a fixed interface, the slope of cost per change as the measure, a user simulator, and pinned versions. Checking old transcripts showed they could not answer the question, so mining them was dropped. On 11-12, the maintainer settled that graders are models. Fifteen candidate projects came back from GPT-6.1 Sol, Gemini 4 Argon, and a fresh Claude Opus 5.5 session, and Claude Fable reviewed the plan. Later that day, BenchTime was chosen as the pilot seed and ReleaseDesk as the second, every point in the plan review was adopted, and the cost constraints were set. In the evening, Sol drafted the interface, oracle, and change script, and Argon drafted the brief. The main session edited both, marked three edits for the maintainer's review, and kept the drafts unedited. On the night of 11-12, the maintainer decided that each arm defines its own interface, with a step before grading that extracts it. Sol revised the oracle and change script, Argon wrote an owner-voice brief, and the main session made six more edits. On 11-13, a grading protocol was written into design.md. The maintainer accepted BenchTime's materials, and the log was compacted for the first time. The plumbing test ran in two halves. In the afternoon, about 25 throwaway sessions on Sonnet 5.5 showed that LID's phase stops work headless, and the main session proposed running every executor in a Linux container. In the evening, a bare BenchTime build, interface extraction, and grading ran in that container, and the judge caught a seeded mutant on two probes.

**Decisions.** Every decision that still stands, with its date and who made it, is in [decisions.md](decisions.md).

**Archive.**

- [2026-11.md](log-archive/2026-11.md): entries from 2026-11-11 to 2026-11-13 (eight entries)
