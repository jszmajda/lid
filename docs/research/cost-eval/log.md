# Research log

Newest entries first. Each entry says what was done, what was decided, and who decided it.

Older entries move to [log-archive/](log-archive/) when this file passes about 2,000 words, and 'Earlier, in brief' at the bottom summarizes them.

## 2026-11-13 (night): The container recipe is standard; probes drafted and reviewed

**Decided by the maintainer.**
- Every executor session runs in a Linux container from the pinned executor image, with each arm's configuration in its own volume and the maintainer's subscription token. [design.md](design.md) ("Sessions and isolation") now says so.
- No force-pushes to the pull request branch, because they could disturb a collaborator's checkout. A pushed commit named the private file holding the token and had the maintainer's home-directory paths. The next commit moved those into a git-ignored local file, and the earlier commit stays in the history.

**Done.** GPT-6.1 Sol was asked to draft probes for every graded BenchTime item ([prompts/05-probes.md](seeds/benchtime/prompts/05-probes.md)). The prompt asks for:
- scenarios that name every inspection without hinting at the answer, because the executor never sees the expected observations;
- named starting setups, so the harness can prepare each once and restore it;
- the change each probe applies from and until;
- what each probe needs beyond the clock, reset, requests, and setup commands, such as concurrent requests, a restart on existing data, or data from an earlier checkpoint.

**Sol's draft** came back with 88 probes for all 53 graded items, in 8 named setups, for $0.37. It was careful in places: it swaps one race probe for another at change 8, when one live hold per person arrives, and it found the right instants for the offset-transition cases. The main session made 14 edits (E16 to E29, logged privately). Most apply one rule: **a probe for one item mustn't fail because of another item's answer.** Otherwise an arm that settled an askable rule its own way would lose points on stated items too, and one decision would be graded twice. Two boundaries kept leaking into other items' probes: the end of the cleaning allowance (BT-15) and the exact instant a hold expires (BT-17). Two probes also couldn't have run as drafted, because they gave Maya four upcoming bookings before testing the waiting list. The judge prompt now says that reasons in expected observations needn't appear in responses.

**Claude Fable reviewed the probes in the maintainer's place,** at the maintainer's request, because checking 88 probes line by line is beyond a useful human review.
- **First pass:** Fable reviewed them cold against the oracle, recomputing every time and boundary, then read the edit log. It found 1 blocker, 7 major, and 12 minor problems. The blocker was a setup step that an arm honoring one askable rule would refuse, so the probe could never pass for a careful arm.
- **The main lesson:** the main session's edits had swept for leaks from two askable items only. The same leak ran through five more, so other items' probes would have failed arms for answers they were entitled to give differently.
- **An oracle fix:** one item stated in a change carried a clause that belongs to an askable item, so an arm could fail a stated item whatever the probes did. The clause moved to the askable item, as an earlier accepted edit did for a similar case. The oracle is now version 2.
- **A reversal:** one earlier edit had treated a rule as askable, but a redirect in the change script states it, so the case went back in.
- **Second pass:** the main session adopted every blocker and major fix and most minor ones (E30 to E47, logged privately). Fable then checked the fixes and found no remaining or new blockers or majors.
- **Result:** 92 probes, recorded as version 1 with the oracle's version 2 in [seeds/benchtime/README.md](seeds/benchtime/README.md).

**The harness stays outside LID's arrow. Decided by the maintainer.** This is a research spike, and the harness serves this study. A walk of the arrow had started; the main session pointed out that the alternate-model runner earns its segment because its results become shipped plugin content, and that the cost harness's results back nothing LID ships yet. The harness lives beside the notebook in `harness/`, its design is in [design.md](design.md) under "The harness", and it moves into the arrow as a segment if its results come to back a shipped claim.

**Grading is the study's biggest cost.** A trajectory grades 627 probe-runs across its 11 checkpoints. At the plumbing test's rate, that is about 18,500 calls and $130 at Haiku's list price, or about 7,300 calls and $50 with snapshots of each setup. An executor trajectory probably costs $10 to $30. Most of those runs repeat a probe that passed at the previous checkpoint against an unchanged interface.

**Proposed by the main session, for the harness:** replay instead of re-running. At each checkpoint, the harness replays the previous checkpoint's calls for each probe without a model, matching identifiers by position, and compares the responses. A model executes a probe only when it is new, or when the replay fails because the interface changed. The judge sees only probes whose responses changed, and the others keep their verdicts. A sample of carried-over verdicts is judged again, to check that replay doesn't hide regressions.

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
