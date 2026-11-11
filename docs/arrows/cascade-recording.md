# Arrow: cascade-recording

The tool that makes the home page's terminal recording. It copies a small free-trial project whose files match the home page's cards, records a clean terminal with asciinema inside tmux, and drives a live Claude Code session through the cards' change of mind, "End trials at midnight in each user's own time zone." It types the request and a reply at each stop for review, then shortens the agent's working stretches in a second copy of the recording. A maintainer picks a take and publishes it.

## Status

**MAPPED**, a new leaf segment sampled 2026-11-11 and not yet audited. The tool, the trial project, and their tests are built, and all 47 `CASCADE-REC` specs are implemented; the first complete takes ran 2026-11-11. The home page embeds take 20261111-052857 (2:51), committed at `site/recordings/cascade.cast` with its log (`MKT-SITE-003`, `MKT-SITE-134`).

## References

### HLD
- `docs/high-level-design.md` § Key Design Decisions / *The arrow for LID itself* (content artifacts)

### LLD
- `docs/intent/cascade-recording/cascade-recording-design.md`

### EARS
- `docs/intent/cascade-recording/cascade-recording-specs.md` (prefix `CASCADE-REC-*`)

### Tests
- `tools/cascade-recording/test_record.py`: the trial project against the home page's quoted lines, the recorded shell's startup files in a real zsh with a stand-in `claude`, a take driven against a fake terminal on a fake clock, the retiming, and the take folder. Run: `python3 tools/cascade-recording/test_record.py`. The trial project's own tests run when its dependencies are installed (`npm ci` in `tools/cascade-recording/trial-app/`).

### Code
- `tools/cascade-recording/record.py`: the tool (Python 3.9+, standard library)
- `tools/cascade-recording/shell/`: the recorded shell's startup files and the tmux configuration
- `tools/cascade-recording/trial-app/`: the trial project

## Architecture

**Purpose:** Make the home page's recording the same way every time, so it can be made again whenever the skills change, and keep it short enough to watch.

**Key Components:**
1. **Trial project**: a TypeScript project with LID in Full mode, holding the HLD, trial design, specs, test, and code the home page's cards quote, tested with Vitest.
2. **Take folder**: a fresh, committed copy at `/tmp/trial-app`, with Claude Code's memory for it emptied and holding only the tour's record.
3. **Recorded terminal**: a 100×30 tmux pane without a status bar on its own socket, recorded by asciinema, running zsh with the tool's own startup files and a `claude` that loads the working tree's plugin without the maintainer's user settings.
4. **Driver**: types each command after a shell comment saying what it shows, types a parenthetical aside into Claude Code's input box at each stop and clears it unsent, types commands and replies with a person's uneven rhythm, finds each stop by Claude Code's `esc to interrupt` hint going away, picks the reply (a correction, a hand-off, or approval) by which files have changed, and ends the change when all four files have changed and the tests pass.
5. **Retiming**: changes only the delays between events, shortening working stretches to eight seconds at most, keeping reading pauses, and capping other gaps.
