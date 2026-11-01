# Cascade Recording Specs

**LLD**: docs/intent/cascade-recording/cascade-recording-design.md
**Implementing artifacts**:
- tools/cascade-recording/record.py
- tools/cascade-recording/test_record.py
- tools/cascade-recording/shell/.zshrc
- tools/cascade-recording/trial-app/

Status markers: `[x]` implemented · `[ ]` active gap · `[D]` deferred

## The Trial Project

- `[x]` **CASCADE-REC-001**: The repository SHALL hold a starting project at `tools/cascade-recording/trial-app/` containing `docs/high-level-design.md`, `docs/intent/trial/trial-design.md`, `docs/intent/trial/trial-specs.md`, `tests/trial.test.ts`, `src/trial.ts`, `AGENTS.md`, `CLAUDE.md`, `.claude/settings.json`, `package.json`, and `package-lock.json`.
- `[x]` **CASCADE-REC-002**: Every line that the home page's narrowing explainer quotes from `docs/high-level-design.md`, `docs/intent/trial/trial-design.md`, `docs/intent/trial/trial-specs.md`, or `tests/trial.test.ts` SHALL appear in the trial project's file at that path.
- `[x]` **CASCADE-REC-003**: The change request a take types SHALL be the request the home page's change explainer shows.
- `[x]` **CASCADE-REC-004**: The trial project's `AGENTS.md` SHALL carry a `## LID` block with `- Mode: Full` and `- Version:` set to the version in `plugins/linked-intent-dev/.claude-plugin/plugin.json`, and its `CLAUDE.md` SHALL be a symbolic link to `AGENTS.md`.
- `[x]` **CASCADE-REC-005**: The trial project's tests SHALL run with Vitest through `npm test` and SHALL pass at the project's starting state.
- `[x]` **CASCADE-REC-006**: The trial project's `src/trial.ts` and `tests/trial.test.ts` SHALL carry `@spec` comments citing `TRIAL-001`, `TRIAL-002`, and `TRIAL-003`, and every `TRIAL-` ID they cite SHALL be defined in its `trial-specs.md`.
- `[x]` **CASCADE-REC-007**: The trial project's `.claude/settings.json` SHALL allow the project's tests, `grep`, and `git diff` to run without a permission prompt.

## Before Recording

- `[x]` **CASCADE-REC-008**: When a take starts, the tool SHALL check that `tmux`, `asciinema`, `git`, `npm`, and `claude` can be run, and SHALL stop before recording, naming each one that can't.
- `[x]` **CASCADE-REC-009**: The tool SHALL copy the trial project to the take folder, `/tmp/trial-app` by default, replacing a folder that an earlier take made there and refusing, before changing anything, to replace a folder that no take made; SHALL install the project's dependencies; and SHALL commit the starting state to a new git repository in the take folder.
- `[x]` **CASCADE-REC-010**: Before recording, the tool SHALL replace the contents of Claude Code's memory folder for the take folder with a single memory holding the record `Has met the LID tour: declined`.

## The Recorded Terminal

- `[x]` **CASCADE-REC-011**: The tool SHALL record, with asciinema, a tmux session 100 columns wide and 30 rows tall with tmux's status bar turned off.
- `[x]` **CASCADE-REC-012**: The recorded shell SHALL read its startup files from `tools/cascade-recording/shell/`, SHALL show the prompt `$ `, SHALL print nothing before its first prompt, and SHALL accept `#` comments typed at the prompt. Its environment SHALL hold only `HOME`, `USER`, `LOGNAME`, `PATH`, `TERM`, `LANG`, `TMPDIR`, and the variables the tool sets for the take.
- `[x]` **CASCADE-REC-013**: In the recorded shell, the command `claude` SHALL run Claude Code with the `linked-intent-dev` plugin loaded from this repository's `plugins/linked-intent-dev/`, with `--setting-sources project`, with the take's model and effort (by default `claude-opus-5-5` at `medium`), and with permission mode `auto`. The recorded shell's environment SHALL set `CLAUDE_CODE_ENABLE_PROMPT_SUGGESTION=false`, so Claude Code shows no suggested reply in its input box.

## The Script

- `[x]` **CASCADE-REC-014**: Before starting Claude Code, the tool SHALL type each of these comments, each followed by its command, in order: `# This app has LID set up. Its trial design says when a free trial ends:` then `grep -A2 "## When the trial ends" docs/intent/trial/trial-design.md`; `# Requirement TRIAL-003 says the same, and the test and code that build it cite its ID:` then `grep -rn TRIAL-003 docs src tests`; `# The tests pass:` then `npm test`. It SHALL then clear the screen and type `# Next, you ask Claude Code, with LID installed, to change when trials end.`
- `[x]` **CASCADE-REC-015**: The tool SHALL type every comment, command, aside, and reply one character at a time, waiting after each character a random time between half and twice the base delay, plus a short extra wait after a space and a longer one after punctuation, and SHALL NOT type a shell command or comment until the shell's prompt has returned from the previous one.
- `[x]` **CASCADE-REC-016**: The tool SHALL start Claude Code with `claude`, wait for its input box, and type the change request.
- `[x]` **CASCADE-REC-017**: The tool SHALL treat the agent as working while the screen shows `esc to interrupt`, and as stopped for review once that hint is gone and the screen has not changed for two seconds.
- `[x]` **CASCADE-REC-018**: When the agent stops at a menu, the tool SHALL wait a reading pause, four seconds by default, before choosing.
- `[x]` **CASCADE-REC-040**: At a stop where the screen shows a menu of options (Claude Code's footer reads "to navigate"), the tool SHALL move to the first option whose text contains "(Recommended)", or, when none does, to the first option whose text says the trial lasts at least 720 hours (such as "after 720h", "at least 720 hours", or "after the 720th hour"), or, when none does, to the first option whose label begins "Submit", using the arrow keys, and SHALL press Enter. When the menu has none of these, the tool SHALL stop the take as failed, saying what the menu offered.
- `[x]` **CASCADE-REC-041**: At a stop without a menu where none of the four files differs from the starting state, the screen contains "recommend", and this reply has not been given, the tool SHALL type "Go with your recommendation."
- `[x]` **CASCADE-REC-019**: At a stop without a menu, when `trial-specs.md` differs from the starting state and the hand-off has not been given, the tool SHALL type the hand-off, "Looks good. Take it from here on your own: update the test and the code, and show me when the tests pass."
- `[x]` **CASCADE-REC-020**: At a stop without a menu where CASCADE-REC-019 and CASCADE-REC-041 do not apply, when `trial-design.md` differs from the starting state and neither the correction nor the hand-off has been given, the tool SHALL type the correction, "Looks right. Add the Tokyo signup from the test as a worked example, so anyone can check the rule."
- `[x]` **CASCADE-REC-021**: At a stop without a menu where none of CASCADE-REC-019, CASCADE-REC-020, and CASCADE-REC-041 applies, the tool SHALL type "Approved. Go with your recommendations." when the screen mentions a recommendation, suggestion, or proposal, and "Approved." otherwise.
- `[x]` **CASCADE-REC-022**: After each stop, the tool SHALL check the take folder from outside the recording, and when `trial-design.md`, `trial-specs.md`, `tests/trial.test.ts`, and `src/trial.ts` all differ from the starting state and the project's tests pass, the tool SHALL type the closing aside (CASCADE-REC-044), hold and clear it, and type `/exit` instead of a reply.
- `[x]` **CASCADE-REC-023**: After Claude Code exits, the tool SHALL clear the screen and type each of these comments, each followed by its command, in order: `# The change reached every level: the design, the requirements, the tests, and the code.` then `git diff --stat`; `# TRIAL-003 still leads to everything built from it:` then `grep -rn TRIAL-003 docs src tests`; `# And every test passes:` then `npm test`. It SHALL then end the recording.

## Narration

- `[x]` **CASCADE-REC-042**: After typing an aside, and after typing the shell comment before `npm test` or before `claude`, the tool SHALL hold for one second plus one second per forty characters of the line typed. After every other shell comment, the tool SHALL run the comment's command first and then hold for one second plus one second per forty characters of the comment, plus half a second per non-blank line the command printed, up to four seconds for the printed lines. The tool SHALL log each hold as a reading pause.
- `[x]` **CASCADE-REC-043**: At each stop without a menu, the tool SHALL type that stop's aside into Claude Code's input box, hold it, clear it by pressing Ctrl+U until the input box is empty, and then type the reply.
- `[x]` **CASCADE-REC-044**: Each aside SHALL be, by the reply that follows it: before "Go with your recommendation.", "(The HLD and its tenet still hold. Claude asks which midnight you mean, and recommends the one that never shortens a trial.)"; before "Approved." at a stop where none of the four files nor the HLD differs from the starting state, "(The HLD and its tenet still hold, so Claude moves on to the trial's design.)"; before the correction, "(Claude rewrote the trial's design: a trial now ends at the first local midnight after 720 hours.)" when `trial-design.md` has a line that mentions both midnight and 720 hours, else "(Claude rewrote the trial's design and waits for your review.)"; at the stop right after the correction, "(Claude added the Tokyo signup to the design as a worked example.)" when `trial-design.md` mentions Tokyo, else "(Claude revised the design and waits for your review.)", with ", and recommends answers to its follow-up questions" before the closing period when the reply is "Approved. Go with your recommendations."; before "Approved. Go with your recommendations." at any later stop, "(Claude has follow-up questions and recommends an answer to each.)"; before the hand-off, "(Claude rewrote … and added ….)" naming the `TRIAL-` requirements whose text differs from the starting state and those added since (three or more consecutive IDs as "TRIAL-004 to TRIAL-008"), ending ", for cases such as daylight saving" when an added requirement mentions a clock change or daylight saving and " to match the design" when none was added, or "(Claude rewrote the requirements to match the design.)" when none can be named; before `/exit`, "(Claude updated the tests and the code, and all N tests pass.)" with the number of passing tests, or "… and the tests pass.)" when the number can't be read; and before any other reply, "(Claude waits for your review.)"
- `[x]` **CASCADE-REC-045**: The tool SHALL clear the screen with Ctrl+L before typing the comment that introduces Claude Code and again after Claude Code exits. Before the first clear, the tool SHALL hold for three seconds after the last opening command's output, and SHALL log the hold as a reading pause.

## Failed Takes

- `[x]` **CASCADE-REC-024**: If the screen shows Claude Code's prompt asking whether to trust the folder, the tool SHALL stop the take as failed and SHALL say to run `claude` once in the take folder and answer it.
- `[x]` **CASCADE-REC-025**: If the screen shows a prompt that is neither a menu of options nor the folder-trust prompt, such as a permission prompt (Claude Code's footer reads "Esc to cancel" without "to navigate"), the tool SHALL stop the take as failed, saying what it saw.
- `[x]` **CASCADE-REC-026**: If the agent stops for review more times than the stop limit (eight by default), or the take runs longer than the time limit (thirty minutes by default), the tool SHALL stop the take as failed.
- `[x]` **CASCADE-REC-027**: A failed take SHALL keep its raw recording and its log, and the tool SHALL exit with a non-zero status.

## Timing

- `[x]` **CASCADE-REC-028**: During a take, the tool SHALL log, in seconds since the recording began, when each working stretch starts and ends, when each reading pause and hold starts and ends, and when the typing of each comment, command, aside, and reply starts and ends.
- `[x]` **CASCADE-REC-029**: Retiming SHALL scale the delays inside each working stretch by one factor so that the stretch plays in at most the stretch limit, six seconds by default, and SHALL leave a shorter stretch at full speed.
- `[x]` **CASCADE-REC-030**: Retiming SHALL keep the delays inside each reading pause and each hold at full length.
- `[x]` **CASCADE-REC-046**: Retiming SHALL divide the delays inside each logged typing span by the typing speed, 1.6 by default.
- `[x]` **CASCADE-REC-031**: Outside working stretches and reading pauses, retiming SHALL shorten any delay longer than the pause cap, one and a half seconds by default, to the pause cap.
- `[x]` **CASCADE-REC-032**: Retiming SHALL keep every event of the raw recording, in order, with its type and content unchanged.
- `[x]` **CASCADE-REC-033**: The retimed recording's header SHALL carry the title \"LID cascade: end trials at local midnight\", the recorded terminal size, a fixed dark color theme whose colors are written as lowercase `#rrggbb`, the form asciinema.org accepts, and no idle time limit.
- `[x]` **CASCADE-REC-034**: The tool SHALL report the retimed recording's length, and SHALL flag a take whose retimed length is over 180 seconds.
- `[x]` **CASCADE-REC-035**: When run as `record.py --retime <take folder>`, the tool SHALL write the take's retimed recording again from its raw recording and log, using the timing options given, without recording.

## What a Take Leaves

- `[x]` **CASCADE-REC-036**: Each take SHALL write a folder under `tools/cascade-recording/takes/`, named for the take's start time, holding the raw recording (`raw.cast`), the retimed recording (`cascade.cast`), the log (`take.json`), and the take folder's final diff (`diff.patch`).
- `[x]` **CASCADE-REC-037**: The log SHALL record the Claude Code version, the model and effort, the `linked-intent-dev` version, each stop with the reply given, the take's real and retimed lengths, and whether the take completed or why it stopped.
- `[x]` **CASCADE-REC-047**: The log SHALL name a poster frame, written as `npt:M:SS`, at the first whole second at or after the moment the request is sent to Claude Code, measured in the retimed recording.
- `[x]` **CASCADE-REC-038**: Git SHALL ignore `tools/cascade-recording/takes/` and the trial project's `node_modules/`.
- `[x]` **CASCADE-REC-039**: The tool SHALL NOT upload or publish a recording.
