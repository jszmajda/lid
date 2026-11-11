---
parent: high-level-design
prefix: CASCADE-REC
---

# Cascade Recording

## Context and Design Philosophy

The home page follows one 30-day free trial from a request to code, and then follows a change of mind about it, "End trials at midnight in each user's own time zone.", through every level (marketing-site § Page: Home). Right after those cards, the page plays a terminal recording of Claude Code making that same change with LID installed (MKT-SITE-003, MKT-SITE-110). The recording is the cards' claim happening in a real session, so it has to show the same project, the same files, and the same change.

A recording made by hand carries whatever the maintainer's terminal carries: shell startup messages, a themed prompt, typing mistakes, and the agent's full working time, which runs several minutes for a change through four levels. It also leaves the project changed, so the next take starts somewhere else. This tool makes every take the same way. It copies the same starting project, opens a clean terminal of a fixed size, types the same request, gives the same reply at each review stop, and afterward shortens the stretches where the agent is working, so the finished recording runs two to three minutes. Along the way it narrates in the terminal, one sentence at each step, because a viewer meeting LID for the first time can't tell what a command shows or read what Claude Code wrote in the seconds a recording gives them.

The tool lives at `tools/cascade-recording/`. It is ordinary code: it walks the standard arrow (`HLD → LLD → EARS → tests → code`) and carries `@spec` annotations. It ships in no plugin and is never installed into a user's project. Its output is a recording file; uploading it to asciinema.org and pointing the home page at it stay the maintainer's steps.

Four principles shape it:

- **Record the real screen.** A take is a live Claude Code session in a terminal, recorded as Claude Code draws it. The tool types and waits like a person at the keyboard and never draws anything itself, so what the viewer sees is what a user of Claude Code would see. Its narration is typed into the same terminal, the way a person would type a note, not laid over the picture.
- **Change the timing, never the frames.** After a take, the tool changes only the delays between frames. It shortens the agent's working stretches and long pauses, and every review stop plays at full speed. No frame is removed or altered, and the page says the waiting is sped up.
- **Start every take from the same place.** The starting project is committed in this repository, and every take runs on a fresh copy of it.
- **A person picks the take.** The agent's wording and choices vary from run to run. The tool makes takes cheaply and records what happened in each, and a maintainer watches them and picks one. The tool never uploads or publishes.

## The trial project

`tools/cascade-recording/trial-app/` is a small TypeScript project with LID set up in Full mode. It holds the files the home page's cards show, and each file contains the lines the cards quote, word for word:

- **`docs/high-level-design.md`**: why the app has a trial, with the goal "New users can try the app free for 30 days before they pay." and the tenet "Customer delight over perfect cost management. When a choice could go either way, we lean toward the customer."
- **`docs/intent/trial/trial-design.md`**: how the trial works, with the section "When the trial ends" saying "The trial ends 720 hours after signup.", plus when the trial starts and what an active trial allows.
- **`docs/intent/trial/trial-specs.md`**: the three requirements `TRIAL-001`, `TRIAL-002`, and `TRIAL-003`, as the page shows them.
- **`tests/trial.test.ts`**: a test for each requirement, including the page's `TRIAL-003` test of a Tokyo signup at 11 p.m. on March 1st.
- **`src/trial.ts`**: the code, with `@spec` comments citing the requirements it implements.
- **`AGENTS.md`**, with `CLAUDE.md` as an alias: the LID directives the `update-lid` skill writes, with `Mode: Full` and the version of `linked-intent-dev` this repository ships.
- **`.claude/settings.json`**: permission to run the commands a take uses (the tests, `grep`, and `git diff`), so no permission prompt interrupts a take.

The tests run with Vitest, because its `it` and `expect` form is what the page's test excerpt shows. The project's tests pass at its starting state.

The page and the project describe one project, so a change to the text a card quotes changes the trial project in the same change, and a test in this segment checks that every line a card quotes from these files appears in them.

## A take

A take runs in seven steps.

1. **A fresh copy.** The tool copies the trial project to the take folder, `/tmp/trial-app` by default, because Claude Code prints the folder's path in its banner and a short path reads cleanly. It replaces a folder an earlier take left there, and refuses to replace a folder it didn't make, so a mistyped path can't delete someone's work. It installs the project's dependencies and commits the starting state to a new git repository there, so the diff at the end shows only what the take changed.
2. **A clean terminal.** The tool opens a tmux session 100 columns by 30 rows with tmux's status bar off, and records it with asciinema. The shell inside reads its startup files from the tool's own folder rather than the maintainer's, which gives it a plain `$ ` prompt and no startup messages. The environment carries only what Claude Code needs to find the maintainer's login (home, user, path, terminal, and locale).
3. **Claude Code configured by the take, not by the maintainer's settings.** In the recorded shell, `claude` runs Claude Code with the `linked-intent-dev` plugin loaded from this repository's working tree and the maintainer's user settings left out, so their other plugins, hooks, and status line stay out of the picture. The model and effort are set by the take, the current Opus at medium effort by default. The session runs in Claude Code's auto mode, which approves the agent's routine edits and commands without a prompt and still asks before a risky one, which fails the take. Claude Code's suggested next reply, which it shows in grey in the input box, is turned off, so the only reply on screen is the one the take types. The viewer sees the command typed as `claude`.
4. **No first-run prompts on screen.** Claude Code asks once whether to trust a folder it hasn't seen before, and remembers the answer by path. If that prompt appears during a take, the tool stops the take and tells the maintainer to run `claude` once in the take folder and answer it. LID's skill offers its newcomer tour when nothing in Claude Code's memory shows the person has met LID; the recording shows a person who has, so before starting, the tool empties Claude Code's memory for the take folder and writes the tour's record, `Has met the LID tour: declined`, into it. Emptying it first also keeps anything the agent remembered during an earlier take out of the next one.
5. **Before the change.** The tool runs three commands, each after a shell comment saying what it shows (see *Narration*): it shows the "When the trial ends" section of `trial-design.md`, searches for `TRIAL-003` across the docs, tests, and code, and runs the tests, which pass. Then it clears the screen and types one more comment introducing Claude Code.
6. **The change.** The tool starts `claude` and types the request, "End trials at midnight in each user's own time zone.", exactly as the page's card shows it. Then it watches the screen. While the agent works, Claude Code shows the hint "esc to interrupt"; when the hint goes away and the screen stays still, the agent has stopped for review. At each stop, the tool types an aside into Claude Code's input box saying in one sentence what the agent just did, holds it while the viewer reads, clears it without sending it, and then answers. At a menu, which has no input box, it skips the aside and waits a few seconds before choosing. The answers show the ways a person steers at a stop: choosing among the agent's options, a small correction, and a hand-off. The tool picks each one from what the screen shows and from which files in the take folder have changed, checked from outside the recording:
   - **A choice**, when the agent asks with a menu of options, as Claude Code does for a question with a few answers. The tool chooses the option the agent marked as recommended, as it does when the agent asks in prose; when none is marked, it chooses the option that ends the trial at the first local midnight after 720 hours, the draft the page's card approves. When the menu asks to submit answers already chosen, the tool submits them. A take whose menu offers none of these fails.
   - **"Go with your recommendation."**, when the agent has asked in its message and recommended an answer before changing any of the four files.
   - **A small correction**, at the first stop after `trial-design.md` changes: "Looks right. Add the Tokyo signup from the test as a worked example, so anyone can check the rule." The agent revises the design and stops again.
   - **A hand-off**, at the first stop after `trial-specs.md` changes: "Looks good. Take it from here on your own: update the test and the code, and show me when the tests pass." The agent writes the test and the code without stopping again.
   - **"Approved."** at any other stop, or **"Approved. Go with your recommendations."** when the agent's message recommends or suggests answers to questions it is asking, so the reply settles them instead of leaving the agent to ask what "Approved" meant.

   The change is complete when `trial-design.md`, `trial-specs.md`, the test file, and `src/trial.ts` have all changed and the tests pass. The tool then types a last aside and `/exit`.
7. **After the change.** The tool clears the screen and runs three more commands, each after a comment: the diff's file summary, the `TRIAL-003` search again, and the tests, which pass.

A take stops early, and is reported as failed, when the screen shows something the tool can't answer, such as a permission prompt; when the agent has stopped more times than the take allows (eight by default); or when the take has run longer than its time limit (thirty minutes by default). A failed take keeps its recording and log for the maintainer to look at.

## Narration

Every line of narration is one sentence a newcomer can read in a few seconds, saying what the screen shows in plain words.

**In the shell**, narration is a comment typed at the prompt, and the recorded shell accepts `#` comments. Each command follows its comment:

| Comment | Command |
|---|---|
| `# This app has LID set up. Its trial design says when a free trial ends:` | `grep -A2 "## When the trial ends" docs/intent/trial/trial-design.md` |
| `# Requirement TRIAL-003 says the same, and the test and code that build it cite its ID:` | `grep -rn TRIAL-003 docs src tests` |
| `# The tests pass:` | `npm test` |
| `# Next, you ask Claude Code, with LID installed, to change when trials end.` | `claude` |
| `# The change reached every level: the design, the requirements, the tests, and the code.` | `git diff --stat` |
| `# TRIAL-003 still leads to everything built from it:` | `grep -rn TRIAL-003 docs src tests` |
| `# And every test passes:` | `npm test` |

**In Claude Code**, which has no comment mode, narration is an aside in parentheses, typed into the input box, held, and cleared without being sent. The agent's wording differs from take to take, so an aside states only what the tool can check in the take folder, or what that stop always is, and the narration stays true for whichever take is published:

- **At the first stop, before any file changes**, the agent has checked the change against the HLD. When it recommends an answer: "(The HLD and its tenet still hold. Claude asks which midnight you mean, and recommends the one that never shortens a trial.)" Otherwise: "(The HLD and its tenet still hold, so Claude moves on to the trial's design.)"
- **At the new design**: "(Claude rewrote the trial's design: a trial now ends at the first local midnight after 720 hours.)", when the design now pairs midnight with 720 hours; otherwise "(Claude rewrote the trial's design and waits for your review.)"
- **At the revised design**, at the stop right after the correction: "(Claude added the Tokyo signup to the design as a worked example.)", when the design now mentions Tokyo; otherwise "(Claude revised the design and waits for your review.)" When the agent also recommends answers to questions there, the aside adds ", and recommends answers to its follow-up questions" before its closing period.
- **At a later stop where the agent recommends answers to its questions**: "(Claude has follow-up questions and recommends an answer to each.)"
- **At the new requirements**: which requirements the agent rewrote and which it added, from comparing `trial-specs.md` with its starting state, such as "(Claude rewrote TRIAL-003 and added TRIAL-004 to TRIAL-008, for cases such as daylight saving.)" The closing clause appears when an added requirement concerns a clock change.
- **At the end**: "(Claude updated the tests and the code, and all 14 tests pass.)", with the count from the tests the tool runs.
- **At any other stop**: "(Claude waits for your review.)"

**Holds.** The tool holds each line of narration on screen long enough to finish reading it: one second plus one second for every forty characters, so a longer line stays up longer. The viewer reads along while it is typed, and the hold lets them finish. A shell comment whose command prints only a few lines holds after that output, with half a second more for each line of it (up to four seconds more), so the viewer reads the comment and what it introduces together. `npm test` prints enough to push its comment off the screen, so its comment holds before the command runs, and so does the comment introducing Claude Code, whose screen replaces it. An aside holds in Claude Code's input box before it is cleared.

**Screen clears.** The tool clears the screen before the comment that introduces Claude Code and again after Claude Code exits, so each part starts on an empty screen. Before the first clear, the screen holds for three seconds, so the viewer sees the tests pass before the picture changes.

**Typing rhythm.** Each keystroke waits a random time between half and twice the base delay, a little longer after a space and longer still after punctuation, with an occasional short hesitation, so the typing reads as a person's.

## Timing

During a take, the tool writes down when each line it types starts and ends, when each hold and menu wait starts and ends, and when each of the agent's working stretches starts and ends, in the recording's own clock. After the take, it writes a second copy of the recording with new delays between frames:

- Inside each working stretch, delays shrink by one factor, so the stretch plays in at most six seconds. A stretch shorter than that plays at full speed.
- Inside the typing, delays shrink by the typing speed, 1.6 by default, so the typing reads as quick without looking pasted, and the pace can be changed without a new take; the rhythm between keystrokes keeps its shape.
- Outside the working stretches, any pause longer than a second and a half plays as a second and a half, except the hold after each comment and aside and the wait before choosing at a menu, which play at full length.
- Every frame stays, in order, with its content unchanged.

The tool reports the finished length. A take whose finished length is over three minutes is flagged for the maintainer, who can make another take or change the timing settings, such as the typing speed, and retime the same take without recording it again.

The finished recording's header carries the title "LID cascade: end trials at local midnight", the terminal size, and a fixed dark color theme, so a take looks the same whichever terminal the maintainer ran it from.

## What a take leaves

Each take writes a folder under `tools/cascade-recording/takes/`, which git ignores, holding:

- the raw recording and the retimed recording;
- a log with the Claude Code version, the model and effort, the `linked-intent-dev` version, each stop and the reply given, the take's real and finished lengths, whether it completed or why it stopped, and a poster frame: the first whole second after the request is sent to Claude Code, as a time in the finished recording, while the comment introducing Claude Code is still on screen, so an embed can open on the request instead of a frame from the middle of the session;
- the take folder's final diff.

The maintainer watches the retimed recordings, picks one, uploads it to asciinema.org, and copies it to `site/recordings/cascade.cast`, where it is committed beside its log so the published recording's origin stays in the repository. The home page then embeds the uploaded recording (marketing-site § Asciinema).

## Running it

`tools/cascade-recording/record.py` makes a take. Options set the model, the effort, the take folder, the reply at each stop, the limits on stops and time, and the timing settings. `record.py --retime <take folder>` writes the retimed recording again from a take's raw recording and log, so the timing can be adjusted without a new take.

The tool uses Python's standard library and calls tmux, asciinema, git, npm, and Claude Code, and it checks that each one is present before it starts.

## Cascade

- **The home page's example changes** (marketing-site): when a card's quoted file text or the change request changes, the trial project and the request a take types change in the same change, and the test that compares them keeps the two in step.
- **The LID skills change materially** (MKT-SITE-035): the maintainer makes new takes, picks one, uploads it, and updates the committed recording and the home page's embed.
- **Claude Code's screen changes**: the hint the tool watches for is the tool's one dependency on how Claude Code draws its screen. When it changes, the tool's stop detection follows, and a take that never sees the hint fails at its time limit rather than recording a broken session.

## Decisions & Alternatives

| Decision | Chosen | Alternatives Considered | Rationale |
|---|---|---|---|
| How a take is made | Drive a live Claude Code session in tmux and record it with asciinema | Record by hand from a written script; run Claude Code headless and redraw the session as a recording; a VHS tape | The page says the viewer is watching the change happen, so the recording shows Claude Code's real screen. By hand, every take differs in noise and length and leaves the project changed. A redrawn session looks unlike the Claude Code a user installs. A VHS tape types on fixed sleeps that can't follow an agent's variable working time, and it produces video rather than a recording the asciinema player can show. |
| Which project | A small free-trial project whose files match the home page's cards | The URL shortener in `lid-example`, with a URL length cap | The recording follows the cards directly, so showing the same files and the same change lets the viewer see the cards' claims in a real session. A second example would ask the viewer to learn a new project at the end of the page. |
| Where the trial project lives | In this repository, beside the tool | A separate repository | One change can update a card and the project together, and the test that compares them can read both. |
| How the tool knows the agent has stopped | Claude Code's "esc to interrupt" hint is gone and the screen is still | Fixed waits; reading Claude Code's session files | Fixed waits either cut the agent off or pad the take. Session files describe the model's turns, not what is on screen. The hint is the signal a person watching the screen uses. |
| Replies at each stop | Answer the agent's question about which midnight (by choosing the option that keeps every trial at least 720 hours, or by taking its recommendation), then a small correction to the new design, then "Approved.", then a hand-off once the requirements are written, each picked from the screen and the changed files | "Approved." at every stop; failing a take whose agent asks a question; a model choosing each reply; the maintainer typing the replies live | The request leaves open which midnight ends the trial, and the agent brings that question to the person, which is the moment the page's card draws. A viewer learns more from seeing a stop used: a choice among the agent's own options, a one-sentence correction that the agent carries into the design, and a hand-off that lets the agent finish the test and code alone. The correction asks for a worked example, the page's own Tokyo signup, because it changes the document visibly without opening another question. The agent drafts the options and checks them against the tenet itself; the tool only picks the option the card approves, and its typed replies never name a design. Approval alone would show the stops but never what they are for. A model choosing replies would make the take harder to repeat, and live typing brings back the noise and variation the tool removes. |
| How the tool finds the working stretches | Noted live from the screen during the take | Found afterward in the recording | Claude Code redraws only the parts of the screen that change, so the "esc to interrupt" hint seldom appears in the recorded frames. The screen during the take shows it whenever the agent is working. |
| Timing | Shorten working stretches and long pauses; play every review stop at full speed | Real time, which runs several minutes; cutting frames; one speed-up for the whole take | The stops are where LID shows its point, so they keep their length. Cutting frames would alter the session, and a single speed-up would rush the stops. |
| Keeping the maintainer's setup out | User settings left out, plugin loaded from the working tree, model and effort set by the take | A separate Claude Code configuration folder; Claude Code's minimal mode | A separate configuration folder loses the maintainer's login. Minimal mode needs an API key and leaves out the project's own instruction file. Leaving out user settings keeps the login and drops the plugins, hooks, and status line. |
| Permission mode | Claude Code's auto mode | Accepting edits and listing allowed commands in the trial project's settings; skipping permission checks | The agent reads and checks files with shell pipelines no allow list anticipates, and allowing a general shell command would allow anything. Skipping the checks would let the agent run anything on the maintainer's machine. Auto mode approves routine work and still stops for a risky command, which fails the take rather than running it. |
| Narration | Typed shell comments, and parenthetical asides in Claude Code's input box that are cleared without being sent, built from facts the tool checks in the take folder | No narration; captions on the page beside the player; a model summarizing each stop as it happens | A newcomer can't tell what a `grep` shows or read the agent's tables in a few seconds, and without narration the recording only shows that something happened. Captions on the page drift out of step with the player. A model's summary would match each take but can't be reviewed before a take and reads differently every time; facts the tool checks keep each aside true and its wording fixed. |
| Typing rhythm | Random delays per keystroke, longer after spaces and punctuation | A steady pace; pasting each line | A steady pace reads as a machine, and pasted lines appear all at once, faster than a viewer can follow. |
| The newcomer tour | The tour's record is written into Claude Code's memory for the take folder | Letting the tour card appear | The recording shows a change, not a first meeting, and the card would take up the first stop. |
| Test runner in the trial project | Vitest | Node's built-in test runner with `assert`; Bun | The page's test excerpt uses `it` and `expect`. Node's runner has no `expect`, and Bun is less familiar to a viewer reading the test output. |
| Tool language | Python with only the standard library | A shell script; Node | The repository's other tools are Python, and the timing work needs more structure than a shell script holds. |

## Open Questions & Future Decisions

### Resolved

1. ✅ The recording shows Claude Code's live screen, driven by a tool and recorded with asciinema.
2. ✅ The recording follows the home page's free-trial example in a small project whose files match the cards.
3. ✅ The finished recording changes only timing: working stretches are shortened, and review stops play at full speed.
4. ✅ The replies show a small correction and a hand-off as well as approval, so the viewer sees what a stop is for.

### Deferred

1. **Uploading from the tool.** Whether the tool uploads a chosen take to asciinema.org itself is decided once the upload step has been done by hand a few times.

## References

- `docs/high-level-design.md` § Key Design Decisions / *The arrow for LID itself* (content artifacts).
- `docs/intent/marketing-site/marketing-site-design.md` § Page: Home (the explainers and the recording), § Asciinema, and § Change management.
- `docs/intent/tour/tour-design.md`: the newcomer tour and its record in the agent's memory.
- `plugins/linked-intent-dev/skills/update-lid/references/agents-md-template.md`: the LID directives the trial project's instruction file carries.
