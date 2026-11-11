#!/usr/bin/env python3
"""Tests for record.py and the trial project. Run from the repository root:

    python3 tools/cascade-recording/test_record.py

The trial project's checks read its files and the home page's source. A take
is driven against a fake terminal on a fake clock, so no tmux, asciinema, or
Claude Code session runs. The recorded shell's startup files run in a real
zsh, with a stand-in `claude` on the path. Running the trial project's own
tests needs its dependencies (`npm ci` in tools/cascade-recording/trial-app/);
that test is skipped without them.
"""

# @spec CASCADE-REC-001, CASCADE-REC-002, CASCADE-REC-003, CASCADE-REC-004, CASCADE-REC-005, CASCADE-REC-006, CASCADE-REC-007
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent
TRIAL_APP = HERE / "trial-app"
sys.path.insert(0, str(HERE))
import record as rec  # noqa: E402


def page_source():
    return (REPO_ROOT / "site" / "src" / "index.njk").read_text()


def section(src, name):
    start = src.index('id="%s"' % name)
    return src[start:src.index("<!-- /section:%s -->" % name, start)]


def page_quotes():
    """The lines each narrowing card quotes, by the file path its caption shows."""
    quotes = {}
    pattern = r'<figure class="file"><figcaption>([^<]+)</figcaption>\s*<pre>(.*?)</pre></figure>'
    for path, pre in re.findall(pattern, section(page_source(), "narrowing"), re.S):
        text = html.unescape(re.sub(r"<[^>]+>", "", pre))
        quotes.setdefault(path, []).extend(line.strip() for line in text.splitlines() if line.strip())
    return quotes


def plain_lines(text):
    """A Markdown file's lines without status markers or bold, as the page renders them."""
    text = re.sub(r"`\[[ xD]\]` ", "", text).replace("**", "")
    return {line.strip() for line in text.splitlines()}


class TrialProject(unittest.TestCase):
    # @spec CASCADE-REC-001
    def test_holds_the_files_the_cards_show(self):
        for name in ["docs/high-level-design.md", "docs/intent/trial/trial-design.md",
                     "docs/intent/trial/trial-specs.md", "tests/trial.test.ts", "src/trial.ts",
                     "AGENTS.md", "CLAUDE.md", ".claude/settings.json", "package.json", "package-lock.json"]:
            self.assertTrue((TRIAL_APP / name).exists(), name)

    # @spec CASCADE-REC-002
    def test_every_quoted_line_appears_in_the_project(self):
        quotes = page_quotes()
        self.assertEqual(set(quotes), {"docs/high-level-design.md", "docs/intent/trial/trial-design.md",
                                       "docs/intent/trial/trial-specs.md", "tests/trial.test.ts"})
        for path, lines in quotes.items():
            have = plain_lines((TRIAL_APP / path).read_text())
            for line in lines:
                self.assertIn(line, have, "%s: %s" % (path, line))

    # @spec CASCADE-REC-003
    def test_types_the_change_the_page_shows(self):
        bubble = re.search(r'<div class="bubble"><span class="who">[^<]*</span><p>(.*?)</p>',
                           section(page_source(), "change"), re.S)
        self.assertEqual(rec.REQUEST, html.unescape(bubble.group(1)))

    # @spec CASCADE-REC-004
    def test_sets_up_lid_at_the_shipped_version(self):
        agents = (TRIAL_APP / "AGENTS.md").read_text()
        block = agents[agents.index("## LID\n"):].split("\n\n")[0]
        self.assertIn("- Mode: Full", block)
        shipped = json.loads((REPO_ROOT / "plugins/linked-intent-dev/.claude-plugin/plugin.json").read_text())["version"]
        self.assertIn("- Version: %s" % shipped, block)
        self.assertTrue((TRIAL_APP / "CLAUDE.md").is_symlink())
        self.assertEqual(os.readlink(TRIAL_APP / "CLAUDE.md"), "AGENTS.md")

    # @spec CASCADE-REC-005
    def test_tests_run_with_vitest_and_pass(self):
        package = json.loads((TRIAL_APP / "package.json").read_text())
        self.assertIn("vitest", package["scripts"]["test"])
        self.assertIn("vitest", package["devDependencies"])
        if not (TRIAL_APP / "node_modules").exists():
            self.skipTest("run `npm ci` in tools/cascade-recording/trial-app/ to run its tests")
        run = subprocess.run(["npm", "test", "--silent"], cwd=TRIAL_APP, capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)

    # @spec CASCADE-REC-006
    def test_code_and_tests_cite_the_requirements(self):
        defined = set(re.findall(r"\*\*(TRIAL-\d{3})\*\*", (TRIAL_APP / "docs/intent/trial/trial-specs.md").read_text()))
        self.assertEqual(defined, {"TRIAL-001", "TRIAL-002", "TRIAL-003"})
        for name in ["src/trial.ts", "tests/trial.test.ts"]:
            cited = set()
            for line in re.findall(r"@spec ([^\n]+)", (TRIAL_APP / name).read_text()):
                cited |= set(re.findall(r"TRIAL-\d{3}", line))
            self.assertEqual(cited, defined, name)

    # @spec CASCADE-REC-007
    def test_allows_the_commands_a_take_runs(self):
        allow = json.loads((TRIAL_APP / ".claude/settings.json").read_text())["permissions"]["allow"]
        for command in ["npm test", "grep", "git diff"]:
            self.assertTrue(any(rule.startswith("Bash(%s" % command) for rule in allow), command)


class BeforeRecording(unittest.TestCase):
    # @spec CASCADE-REC-008
    def test_names_each_missing_program(self):
        present = {"git", "npm", "claude"}
        missing = rec.missing_programs(lambda name: "/bin/" + name if name in present else None)
        self.assertEqual(missing, ["tmux", "asciinema"])
        self.assertEqual(rec.missing_programs(lambda name: "/bin/" + name), [])

    # @spec CASCADE-REC-009
    def test_starts_from_a_fresh_committed_copy(self):
        with tempfile.TemporaryDirectory() as tmp:
            src, dest = Path(tmp, "src"), Path(tmp, "take")
            (src / "docs").mkdir(parents=True)
            (src / "docs" / "a.md").write_text("a\n")
            (src / ".gitignore").write_text("node_modules/\n")
            (src / "node_modules").mkdir()
            (src / "node_modules" / "junk.js").write_text("")
            os.symlink("docs/a.md", src / "link.md")
            dest.mkdir()
            (dest / "left-over.txt").write_text("from an earlier take")
            with self.assertRaises(rec.TakeFailed):
                rec.prepare_take_folder(src, dest, install=lambda folder: None)
            self.assertTrue((dest / "left-over.txt").exists(), "a folder no take made is left alone")
            rec.mark_take_folder(dest)
            installed = []
            rec.prepare_take_folder(src, dest, install=installed.append)
            self.assertEqual(installed, [dest])
            self.assertFalse((dest / "left-over.txt").exists())
            self.assertFalse((dest / "node_modules").exists())
            self.assertTrue((dest / "link.md").is_symlink())
            log = subprocess.run(["git", "log", "--oneline"], cwd=dest, capture_output=True, text=True).stdout
            self.assertEqual(len(log.splitlines()), 1)
            status = subprocess.run(["git", "status", "--porcelain"], cwd=dest, capture_output=True, text=True).stdout
            self.assertEqual(status, "")

    # @spec CASCADE-REC-010
    def test_leaves_only_the_tour_record_in_memory(self):
        with tempfile.TemporaryDirectory() as tmp:
            home, take = Path(tmp, "home"), Path(tmp, "trial-app")
            take.mkdir()
            folder = rec.memory_folder(take, home)
            self.assertEqual(folder.parent.parent, home / ".claude" / "projects")
            self.assertEqual(folder.parent.name, re.sub(r"[^A-Za-z0-9]", "-", str(take.resolve())))
            folder.mkdir(parents=True)
            (folder / "user_prefers_tabs.md").write_text("from an earlier take")
            rec.seed_memory(take, home)
            files = sorted(p.name for p in folder.iterdir())
            self.assertEqual(files, ["MEMORY.md", "lid_tour.md"])
            self.assertIn("Has met the LID tour: declined", (folder / "MEMORY.md").read_text())
            self.assertIn("Has met the LID tour: declined", (folder / "lid_tour.md").read_text())


def zsh(env_extra, command, path):
    env = rec.take_env({"HOME": os.environ["HOME"], "USER": "u", "LOGNAME": "u", "PATH": path,
                        "LANG": "en_US.UTF-8", "TMPDIR": tempfile.gettempdir(), "SECRET": "x"},
                       model="claude-opus-5-5", effort="medium")
    env.update(env_extra)
    return subprocess.run(["zsh", "-i", "-c", command], env=env, capture_output=True, text=True, cwd=tempfile.gettempdir())


@unittest.skipUnless(shutil.which("zsh"), "zsh is not installed")
class RecordedTerminal(unittest.TestCase):
    # @spec CASCADE-REC-011
    def test_records_a_fixed_size_session_without_a_status_bar(self):
        argv = rec.tmux_argv("/tmp/trial-app", Path("/tmp/raw.cast"), {"HOME": "/h"})
        self.assertEqual(argv[:3], ["tmux", "-L", rec.TMUX_SOCKET])
        self.assertEqual(argv[argv.index("-x") + 1], "100")
        self.assertEqual(argv[argv.index("-y") + 1], "30")
        self.assertIn("asciinema rec", argv[-1])
        self.assertIn("/tmp/raw.cast", argv[-1])
        conf = Path(argv[argv.index("-f") + 1]).read_text()
        self.assertRegex(conf, r"(?m)^set -g status off$")

    # @spec CASCADE-REC-012
    def test_shell_shows_a_plain_prompt_and_prints_nothing_first(self):
        env = rec.take_env({"HOME": "/h", "USER": "u", "LOGNAME": "u", "PATH": "/bin", "LANG": "C",
                            "TMPDIR": "/t", "SECRET": "x", "TERM": "screen"}, model="m", effort="e")
        self.assertEqual(env["CLAUDE_CODE_ENABLE_PROMPT_SUGGESTION"], "false")
        self.assertEqual(set(env) - {"ZDOTDIR", "LID_PLUGIN", "LID_MODEL", "LID_EFFORT", "CLAUDE_CODE_ENABLE_PROMPT_SUGGESTION"},
                         {"HOME", "USER", "LOGNAME", "PATH", "TERM", "LANG", "TMPDIR"})
        self.assertEqual(Path(env["ZDOTDIR"]), HERE / "shell")
        quiet = zsh({}, "true", "/usr/bin:/bin")
        self.assertEqual((quiet.stdout, quiet.stderr), ("", ""))
        self.assertEqual(zsh({}, 'print -r -- "[$PROMPT]"', "/usr/bin:/bin").stdout, "[$ ]\n")
        env = rec.take_env({"HOME": os.environ["HOME"], "PATH": "/usr/bin:/bin"}, model="m", effort="e")
        typed = subprocess.run(["zsh", "-i"], input="# a comment typed at the prompt\nprint ok\nexit\n",
                               env=env, capture_output=True, text=True, cwd=tempfile.gettempdir())
        self.assertNotIn("command not found", typed.stdout + typed.stderr)
        self.assertIn("ok", typed.stdout + typed.stderr)

    # @spec CASCADE-REC-013
    def test_claude_runs_with_the_working_tree_plugin_and_no_user_settings(self):
        with tempfile.TemporaryDirectory() as tmp:
            stub = Path(tmp, "claude")
            stub.write_text("#!/bin/sh\nprintf '%s\\n' \"$@\"\n")
            stub.chmod(0o755)
            args = zsh({}, "claude", "%s:/usr/bin:/bin" % tmp).stdout.splitlines()
        self.assertEqual(args, ["--plugin-dir", str(REPO_ROOT / "plugins" / "linked-intent-dev"),
                                "--setting-sources", "project", "--model", "claude-opus-5-5",
                                "--effort", "medium", "--permission-mode", "auto"])
        self.assertEqual((rec.DEFAULT_MODEL, rec.DEFAULT_EFFORT), ("claude-opus-5-5", "medium"))


# A fake terminal on a fake clock. Each Enter moves the screen to the next
# scene; a scene is a list of (seconds, screen) frames shown in turn, and the
# last frame stays on screen. Typed text isn't echoed; the terminal records
# each line sent with Enter, each line cleared with Ctrl+U (an aside), and
# every other key, in one list of events.

PROMPT = "$ grep TRIAL-003\nresults\n$"
BUSY = "$ npm test\n running"
READY = "Claude Code v2.1\n────\n❯ \n────\n  ⏵⏵ auto mode on"
WORKING = "Claude Code v2.1\n✻ Thinking…\n────\n❯ \n────\n  ⏵⏵ auto mode on · esc to interrupt"


MENU = """Claude Code v2.1
☐ Trial end

Which midnight should end the trial?

❯ 1. A: midnight starting day 31
     Between 30 and 31 days; daylight saving can make it an hour short of 720 hours.
  2. B: midnight ending day 30
     Late signups lose up to a day, which works against the tenet.
  3. C: first local midnight after 720 hours (Recommended)
     Never under 720 hours.
  4. Type something.
────
  5. Chat about this

Enter to select · ↑/↓ to navigate · Esc to cancel"""


def stopped(text):
    return "Claude Code v2.1\n⏺ %s\n────\n❯ \n────\n  ⏵⏵ auto mode on" % text


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


class FakeTerm:
    def __init__(self, clock, scenes):
        self.clock, self.scenes, self.scene, self.since = clock, scenes, 0, clock()
        self.events, self.line, self.line_screen = [], "", None

    def screen(self):
        elapsed, frames = self.clock() - self.since, self.scenes[min(self.scene, len(self.scenes) - 1)]
        for seconds, screen in frames:
            if elapsed < seconds:
                return screen
            elapsed -= seconds
        return frames[-1][1]

    def type(self, char):
        if not self.line:
            self.line_screen = self.screen()
        self.line += char

    def key(self, name):
        assert name in ("Enter", "Down", "Up", "C-u", "C-l"), name
        if name == "C-u":
            if self.line:
                self.events.append(("aside", self.line, self.clock(), self.line_screen))
            self.line = ""
            return
        if name != "Enter":
            self.events.append(("key", name, self.clock(), None))
            return
        self.events.append(("line", self.line, self.clock(), self.line_screen))
        self.line = ""
        self.scene += 1
        self.since = self.clock()

    def lines(self):
        return [text for kind, text, _, _ in self.events if kind == "line"]

    def asides(self):
        return [text for kind, text, _, _ in self.events if kind == "aside"]


class FakeProject:
    """Answers, at each stop, which files have changed and whether the tests pass."""

    def __init__(self, states, facts=None):
        self.states, self.asked, self.current = states, 0, states[0]
        self.extra = facts or {}

    def done(self):
        """Called once per stop; moves to that stop's state."""
        self.current = self.states[min(self.asked, len(self.states) - 1)]
        self.asked += 1
        changed, passing = self.current
        return set(changed) == {"design", "specs", "test", "code"} and passing

    def changed(self):
        return set(self.current[0])

    def facts(self):
        facts = {"hld_changed": False, "design": "", "specs_before": "", "specs_after": "", "tests_passed": None}
        facts.update(self.extra)
        return facts


def shell_scene():
    return [(0.5, BUSY), (0, PROMPT)]


def comment_scene():
    return [(0, PROMPT)]


FIRST_STOP = 2 * 3 + 3  # the first prompt, three comment-and-command pairs, the comment before claude, claude


def full_take_scenes(stops):
    """A take from the shell's first prompt to the last closing command."""
    scenes = [[(0, PROMPT)]]
    for _ in rec.OPENING:
        scenes += [comment_scene(), shell_scene()]
    scenes.append(comment_scene())
    scenes.append([(1.0, "$ claude"), (0, READY)])
    for working in stops:
        scenes.append([(0.3, READY), (working, WORKING), (0, stopped("Here is the draft."))])
    scenes.append([(1.0, "Resume this session with: claude --resume x"), (0, PROMPT)])
    for _ in rec.CLOSING:
        scenes += [comment_scene(), shell_scene()]
    return scenes


ALL = ["design", "specs", "test", "code"]


def run_take(scenes, states, facts=None, **options):
    clock = Clock()
    term = FakeTerm(clock, scenes)
    opts = rec.Options(seed=7, **options)
    take = rec.Take(term, FakeProject(states, facts), clock, clock.sleep, opts, clock())
    error = None
    try:
        take.run()
    except rec.TakeFailed as e:
        error = e
    return take, term, error


class Script(unittest.TestCase):
    def take(self):
        states = [(["design"], False), (["design"], False), (["design", "specs"], False), (ALL, True)]
        return run_take(full_take_scenes([20, 10, 15, 60]), states)

    # @spec CASCADE-REC-014, CASCADE-REC-023
    def test_narrates_and_runs_the_opening_and_closing_commands(self):
        self.assertEqual(rec.OPENING, [
            ("This app has LID set up. Its trial design says when a free trial ends:",
             'grep -A2 "## When the trial ends" docs/intent/trial/trial-design.md'),
            ("Requirement TRIAL-003 says the same, and the test and code that build it cite its ID:",
             "grep -rn TRIAL-003 docs src tests"),
            ("The tests pass:", "npm test")])
        self.assertEqual(rec.CLAUDE_INTRO, "Next, you ask Claude Code, with LID installed, to change when trials end.")
        self.assertEqual(rec.CLOSING, [
            ("The change reached every level: the design, the requirements, the tests, and the code.", "git diff --stat"),
            ("TRIAL-003 still leads to everything built from it:", "grep -rn TRIAL-003 docs src tests"),
            ("And every test passes:", "npm test")])
        take, term, error = self.take()
        self.assertIsNone(error)
        pairs = lambda script: [line for comment, command in script for line in ("# " + comment, command)]
        lines = term.lines()
        self.assertEqual(lines[:6], pairs(rec.OPENING))
        self.assertEqual(lines[6:8], ["# " + rec.CLAUDE_INTRO, "claude"])
        self.assertEqual(lines[-6:], pairs(rec.CLOSING))

    # @spec CASCADE-REC-015
    def test_types_shell_lines_only_at_a_prompt(self):
        take, term, error = self.take()
        shell = {line for comment, command in rec.OPENING + rec.CLOSING for line in ("# " + comment, command)}
        shell |= {"# " + rec.CLAUDE_INTRO, "claude"}
        for kind, text, _, screen in term.events:
            if kind == "line" and text in shell:
                self.assertEqual(screen.splitlines()[-1], "$", text)

    # @spec CASCADE-REC-015
    def test_types_with_a_human_rhythm(self):
        import random
        rng, base = random.Random(1), 0.035
        plain = [rec.keystroke_delay("a", base, rng) for _ in range(2000)]
        spaces = [rec.keystroke_delay(" ", base, rng) for _ in range(2000)]
        stops = [rec.keystroke_delay(".", base, rng) for _ in range(2000)]
        mean = lambda xs: sum(xs) / len(xs)
        self.assertGreaterEqual(min(plain), base * 0.5)
        self.assertLess(sorted(plain)[len(plain) // 2], base * 2)
        self.assertGreater(len({round(x, 4) for x in plain}), 100)
        self.assertGreater(mean(spaces), mean(plain) + 0.03)
        self.assertGreater(mean(stops), mean(spaces) + 0.05)
        self.assertLess(max(plain + spaces + stops), rec.Options().pause_cap)
        take, term, error = self.take()
        self.assertEqual(take.log["seed"], 7)

    # @spec CASCADE-REC-016
    def test_types_the_request_once_claude_is_ready(self):
        take, term, error = self.take()
        lines = [event for event in term.events if event[0] == "line"]
        at = [text for _, text, _, _ in lines].index("claude")
        self.assertEqual(lines[at + 1][1], rec.REQUEST)
        self.assertEqual(lines[at + 1][3], READY)

    # @spec CASCADE-REC-017, CASCADE-REC-028
    def test_finds_each_working_stretch_from_the_hint(self):
        take, term, error = self.take()
        stretches = take.log["stretches"]
        self.assertEqual(len(stretches), 4)
        for (start, end), working in zip(stretches, [20, 10, 15, 60]):
            self.assertAlmostEqual(end - start, working, delta=0.25)
        replies = [t - take.t0 for kind, text, t, _ in term.events
                   if kind == "line" and (text in rec.REPLIES.values() or text == "/exit")]
        for (start, end), replied in zip(stretches, replies):
            self.assertGreaterEqual(replied - end, rec.Options().settle)

    # @spec CASCADE-REC-028
    def test_logs_each_typed_line(self):
        take, term, error = self.take()
        typed = term.lines() + term.asides()
        spans = take.log["typing"]
        self.assertEqual(len(spans), len(typed))
        self.assertTrue(all(end > start for start, end in spans))
        self.assertEqual(spans, sorted(spans))

    # @spec CASCADE-REC-030, CASCADE-REC-042
    def test_holds_after_each_comment_and_aside(self):
        take, term, error = self.take()
        texts = ["# " + comment for comment, _ in rec.OPENING] + ["# " + rec.CLAUDE_INTRO]
        texts += term.asides() + ["# " + comment for comment, _ in rec.CLOSING]
        holds = [end - start for start, end in take.log["pauses"]]
        del holds[len(rec.OPENING)]  # the hold before the first screen clear
        self.assertEqual(len(holds), len(texts))
        for hold, text in zip(holds, texts):
            self.assertAlmostEqual(hold, 1 + len(text) / 40, delta=0.01, msg=text)
        self.assertEqual((rec.Options().hold_base, rec.Options().read_rate), (1.0, 40.0))

    # @spec CASCADE-REC-042
    def test_holds_after_a_short_output_and_before_npm_test(self):
        scenes = full_take_scenes([20, 10, 15, 60])
        first = rec.OPENING[0][1]
        scenes[2] = [(0.5, BUSY), (0, "$ # %s\n$ %s\n## When the trial ends\n\nThe trial ends 720 hours after signup.\n$"
                                     % (rec.OPENING[0][0], first))]
        states = [(["design"], False), (["design"], False), (["design", "specs"], False), (ALL, True)]
        take, term, error = run_take(scenes, states)
        self.assertIsNone(error)
        entered = {text: t - take.t0 for kind, text, t, _ in term.events if kind == "line"}
        pauses = take.log["pauses"]
        grep_hold, npm_hold, intro_hold = pauses[0], pauses[2], pauses[4]
        self.assertGreater(grep_hold[0], entered[first], "the grep's comment holds after the grep runs")
        self.assertAlmostEqual(grep_hold[1] - grep_hold[0], 1 + len("# " + rec.OPENING[0][0]) / 40 + 2 * 0.5, delta=0.01)
        self.assertLess(npm_hold[1], entered["npm test"], "npm test's comment holds before npm test runs")
        self.assertLess(intro_hold[1], entered["claude"], "the comment introducing Claude Code holds before it starts")

    # @spec CASCADE-REC-042
    def test_counts_the_lines_a_command_printed(self):
        command = rec.OPENING[0][1]
        screen = "$ # a comment\n$ %s\n## When the trial ends\n\nThe trial ends 720 hours after signup.\n$" % command
        self.assertEqual(rec.output_lines(screen, command), 2)
        self.assertEqual(rec.output_lines("$ " + command + "\nold\n$ " + command + "\nnew\n$", command), 1)
        self.assertEqual(rec.output_lines("lots of output\n$", command), 0)

    # @spec CASCADE-REC-043
    def test_types_an_aside_holds_and_clears_it_before_each_reply(self):
        take, term, error = self.take()
        self.assertEqual(len(term.asides()), 4)
        kinds = [(kind, text) for kind, text, _, _ in term.events if kind in ("aside", "line")]
        start = kinds.index(("line", rec.REQUEST))
        replies = [rec.REPLIES["correction"], rec.REPLIES["approved"], rec.REPLIES["handoff"], "/exit"]
        expected = []
        for reply in replies:
            expected += [("aside", None), ("line", reply)]
        got = [(kind, text if kind == "line" else None) for kind, text in kinds[start + 1:start + 9]]
        self.assertEqual(got, expected)
        for aside in term.asides():
            self.assertTrue(aside.startswith("(") and aside.endswith(")"), aside)

    # @spec CASCADE-REC-044
    def test_writes_each_aside_from_what_the_tool_can_check(self):
        before = ("- `[x]` **TRIAL-001**: When a new user signs up, the system shall start a trial.\n"
                  "- `[x]` **TRIAL-002**: While a trial is active, the system shall give the user full access.\n"
                  "- `[x]` **TRIAL-003**: When 720 hours have passed since signup, the system shall end the trial.\n")
        rewritten = before.replace("When 720 hours have passed since signup", "When the first local midnight after 720 hours arrives")
        added = rewritten + "".join("- `[ ]` **TRIAL-%03d**: %s\n" % (n, text) for n, text in [
            (4, "When a trial starts, the system shall store its end."),
            (5, "If a clock change skips local 00:00, the system shall end the trial at the start of that day."),
            (6, "If 00:00 occurs twice, the system shall end the trial at the later one."),
            (7, "The system shall use the time zone recorded at signup."),
            (8, "If the time zone is missing, the system shall use UTC.")])
        base = {"changed": set(), "given": set(), "last": None, "hld_changed": False, "design": "",
                "specs_before": before, "specs_after": before, "tests_passed": None}
        def aside(reply, **facts):
            return rec.aside(reply, dict(base, **facts))
        self.assertEqual(aside("recommendation"), "(The HLD and its tenet still hold. Claude asks which midnight you mean, and recommends the one that never shortens a trial.)")
        self.assertEqual(aside("approved"), "(The HLD and its tenet still hold, so Claude moves on to the trial's design.)")
        self.assertEqual(aside("approved", hld_changed=True), "(Claude waits for your review.)")
        design = "The trial ends at the first midnight in the user's time zone at or after 720 hours from signup."
        self.assertEqual(aside("correction", changed={"design"}, design=design),
                         "(Claude rewrote the trial's design: a trial now ends at the first local midnight after 720 hours.)")
        self.assertEqual(aside("correction", changed={"design"}, design="The trial ends at midnight."),
                         "(Claude rewrote the trial's design and waits for your review.)")
        tokyo = design + "\nA user in Tokyo signs up."
        self.assertEqual(aside("approved", changed={"design"}, given={"correction"}, last="correction", design=tokyo),
                         "(Claude added the Tokyo signup to the design as a worked example.)")
        self.assertEqual(aside("approved", changed={"design"}, given={"correction"}, last="correction", design=design),
                         "(Claude revised the design and waits for your review.)")
        self.assertEqual(aside("recommendations", changed={"design"}, given={"correction"}, last="correction", design=tokyo),
                         "(Claude added the Tokyo signup to the design as a worked example, and recommends answers to its follow-up questions.)")
        self.assertEqual(aside("recommendations", changed={"design"}, given={"correction", "recommendations"},
                               last="recommendations", design=tokyo),
                         "(Claude has follow-up questions and recommends an answer to each.)")
        self.assertEqual(aside("approved", changed={"design"}, given={"correction", "approved"}, last="approved", design=tokyo),
                         "(Claude waits for your review.)", "the Tokyo aside appears once")
        self.assertEqual(aside("handoff", changed={"design", "specs"}, specs_after=added),
                         "(Claude rewrote TRIAL-003 and added TRIAL-004 to TRIAL-008, for cases such as daylight saving.)")
        self.assertEqual(aside("handoff", changed={"design", "specs"}, specs_after=rewritten),
                         "(Claude rewrote TRIAL-003 to match the design.)")
        self.assertEqual(aside("handoff", changed={"design", "specs"}, specs_after=rewritten + "- `[ ]` **TRIAL-004**: The system shall store the end.\n- `[ ]` **TRIAL-005**: The system shall log it.\n"),
                         "(Claude rewrote TRIAL-003 and added TRIAL-004 and TRIAL-005.)")
        self.assertEqual(aside("handoff", changed={"design", "specs"}, specs_after="no ids here"),
                         "(Claude rewrote the requirements to match the design.)")
        self.assertEqual(aside("exit", tests_passed=14), "(Claude updated the tests and the code, and all 14 tests pass.)")
        self.assertEqual(aside("exit"), "(Claude updated the tests and the code, and the tests pass.)")
        self.assertEqual(aside("approved", changed=set(ALL), given={"correction", "handoff"}), "(Claude waits for your review.)")

    # @spec CASCADE-REC-045
    def test_clears_the_screen_before_and_after_claude_code(self):
        take, term, error = self.take()
        sequence = [(kind, text) for kind, text, _, _ in term.events if kind in ("key", "line")]
        clears = [i for i, event in enumerate(sequence) if event == ("key", "C-l")]
        self.assertEqual(len(clears), 2)
        self.assertEqual(sequence[clears[0] + 1], ("line", "# " + rec.CLAUDE_INTRO))
        self.assertEqual(sequence[clears[1] - 1], ("line", "/exit"))
        first_clear = next(t for kind, text, t, _ in term.events if (kind, text) == ("key", "C-l")) - take.t0
        before = take.log["pauses"][len(rec.OPENING)]
        self.assertAlmostEqual(before[1] - before[0], 3.0, places=2)
        self.assertAlmostEqual(before[1], first_clear, places=2)
        self.assertEqual(rec.Options().clear_hold, 3.0)

    # @spec CASCADE-REC-019, CASCADE-REC-020, CASCADE-REC-021, CASCADE-REC-022
    def test_corrects_then_approves_then_hands_off_then_exits(self):
        take, term, error = self.take()
        lines = term.lines()
        at = lines.index(rec.REQUEST)
        self.assertEqual(lines[at + 1:at + 5], [rec.REPLIES["correction"], rec.REPLIES["approved"],
                                                rec.REPLIES["handoff"], "/exit"])
        self.assertEqual([stop["reply"] for stop in take.log["stops"]], ["correction", "approved", "handoff", "exit"])
        self.assertEqual(rec.REPLIES["correction"], "Looks right. Add the Tokyo signup from the test as a worked example, so anyone can check the rule.")
        self.assertEqual(rec.REPLIES["handoff"], "Looks good. Take it from here on your own: update the test and the code, and show me when the tests pass.")
        self.assertEqual(rec.REPLIES["approved"], "Approved.")

    # @spec CASCADE-REC-019, CASCADE-REC-020, CASCADE-REC-021
    def test_picks_replies_by_what_changed(self):
        self.assertEqual(rec.choose_reply(set(), set()), "approved")
        self.assertEqual(rec.choose_reply({"design"}, set()), "correction")
        self.assertEqual(rec.choose_reply({"design"}, {"correction"}), "approved")
        self.assertEqual(rec.choose_reply({"design", "specs"}, set()), "handoff")
        self.assertEqual(rec.choose_reply({"design", "specs"}, {"correction"}), "handoff")
        self.assertEqual(rec.choose_reply({"design", "specs"}, {"handoff"}), "approved")
        self.assertEqual(rec.choose_reply({"design", "specs", "test"}, {"handoff"}), "approved")

    # @spec CASCADE-REC-022
    def test_does_not_exit_while_the_tests_fail(self):
        states = [(ALL, False), (ALL, True)]
        take, term, error = run_take(full_take_scenes([5, 5]), states)
        self.assertIsNone(error)
        self.assertEqual([stop["reply"] for stop in take.log["stops"]], ["handoff", "exit"])


class Answers(unittest.TestCase):
    # @spec CASCADE-REC-018, CASCADE-REC-040
    def test_chooses_the_option_that_keeps_720_hours(self):
        scenes = full_take_scenes([5, 5, 5])
        scenes[FIRST_STOP] = [(0.3, READY), (5, WORKING), (0, MENU)]
        states = [([], False), (["design", "specs"], False), (ALL, True)]
        take, term, error = run_take(scenes, states)
        self.assertIsNone(error)
        sequence = [(kind, text) for kind, text, _, _ in term.events]
        at = sequence.index(("line", rec.REQUEST))
        self.assertEqual(sequence[at + 1:at + 4], [("key", "Down"), ("key", "Down"), ("line", "")])
        self.assertEqual([stop["reply"] for stop in take.log["stops"]], ["choice", "handoff", "exit"])
        self.assertIn("first local midnight after 720 hours", take.log["stops"][0]["option"])
        menu_pause = take.log["pauses"][len(rec.OPENING) + 2]
        self.assertAlmostEqual(menu_pause[1] - menu_pause[0], 4.0, places=2)

    # @spec CASCADE-REC-040
    def test_reads_a_menu_and_submits_chosen_answers(self):
        cursor, options = rec.parse_menu(MENU)
        self.assertEqual(cursor, 1)
        self.assertEqual([number for number, _ in options], [1, 2, 3, 4, 5])
        self.assertEqual(rec.choose_option(options), 3)
        review = "Review your answers\n\n❯ 1. Submit answers\n  2. Cancel\n\nEnter to select · ↑/↓ to navigate · Esc to cancel"
        self.assertEqual(rec.choose_option(rec.parse_menu(review)[1]), 1)
        no_720 = MENU.replace("after 720 hours", "after day 30")
        self.assertEqual(rec.choose_option(rec.parse_menu(no_720)[1]), 3, "falls back to the recommended option")
        self.assertIsNone(rec.choose_option(rec.parse_menu(no_720.replace(" (Recommended)", ""))[1]))
        zones = [(1, "Signup zone (Recommended) Use the zone recorded at signup."),
                 (2, "Current zone Use whatever zone the profile has when we check."),
                 (3, "Later of the two Use whichever zone gives the later midnight.")]
        self.assertEqual(rec.choose_option(zones), 1)
        # Claude Code's own wording from a take: the label says "720h", and option A's text mentions 720h too.
        real = [(1, "A: midnight after day 30 Can be about an hour under 720h around daylight-saving changes."),
                (2, "C: midnight after 720h (Recommended) Ends at the first local midnight at least 720 hours after signup."),
                (3, "B: midnight ending day 30 Late signups get up to about a day less.")]
        self.assertEqual(rec.choose_option(real), 2)
        self.assertEqual(rec.choose_option([(1, "Fixed day 30"), (2, "Later end Ends after the 720th hour.")]), 2)
        fallback = [(1, "First UTC midnight End at the first UTC midnight at or after 720 hours."),
                    (2, "744 hours (Recommended) Always at least as long as any local rule.")]
        self.assertEqual(rec.choose_option(fallback), 2, "the agent's recommendation comes first")

    # @spec CASCADE-REC-040
    def test_fails_when_no_option_can_be_chosen(self):
        scenes = full_take_scenes([5])
        scenes[FIRST_STOP] = [(0.3, READY), (5, WORKING),
                              (0, MENU.replace("after 720 hours", "after day 30").replace(" (Recommended)", ""))]
        take, term, error = run_take(scenes, [([], False)])
        self.assertIsNotNone(error)
        self.assertIn("B: midnight ending day 30", str(error))

    # @spec CASCADE-REC-041
    def test_takes_the_agents_recommendation_before_any_file_changes(self):
        self.assertEqual(rec.REPLIES["recommendation"], "Go with your recommendation.")
        self.assertEqual(rec.choose_reply(set(), set(), "I recommend C, the first midnight."), "recommendation")
        self.assertEqual(rec.choose_reply(set(), {"recommendation"}, "I recommend C."), "recommendations")
        self.assertEqual(rec.REPLIES["recommendations"], "Approved. Go with your recommendations.")
        asked = "2. Invalid or missing time zone: I'd use UTC-12.\n  Do my suggestions work for all three?"
        self.assertEqual(rec.choose_reply({"design"}, {"correction"}, asked), "recommendations")
        self.assertEqual(rec.choose_reply({"design"}, {"correction"}, "Here is the revised draft."), "approved")
        self.assertEqual(rec.choose_reply({"design"}, set(), "I recommend C."), "correction")
        self.assertEqual(rec.choose_reply(set(), set(), "The HLD still holds."), "approved")


class FailedTakes(unittest.TestCase):
    # @spec CASCADE-REC-024
    def test_stops_at_the_trust_prompt(self):
        scenes = full_take_scenes([])[:FIRST_STOP - 1]
        scenes.append([(0, "Quick safety check: Is this a project you created or one you trust?\n"
                           "❯ 1. Yes, I trust this folder\n  2. No, exit\nEnter to confirm · Esc to cancel")])
        take, term, error = run_take(scenes, [([], False)])
        self.assertIsNotNone(error)
        self.assertIn("run `claude` once in", str(error))

    # @spec CASCADE-REC-025
    def test_stops_at_a_prompt_a_reply_cannot_answer(self):
        scenes = full_take_scenes([5])
        scenes[FIRST_STOP] = [(0.3, READY), (5, WORKING),
                              (0, "Bash command\n  rm -rf build\nDo you want to proceed?\n❯ 1. Yes\n  2. No\nEsc to cancel")]
        take, term, error = run_take(scenes, [([], False)])
        self.assertIsNotNone(error)
        self.assertIn("Do you want to proceed?", str(error))

    # @spec CASCADE-REC-026
    def test_stops_after_too_many_stops(self):
        take, term, error = run_take(full_take_scenes([2] * 5), [(["design"], False)], stop_limit=3)
        self.assertIn("more than 3 times", str(error))

    # @spec CASCADE-REC-026
    def test_stops_at_the_time_limit(self):
        take, term, error = run_take(full_take_scenes([10_000]), [([], False)], time_limit=120)
        self.assertIn("time limit", str(error))

    # @spec CASCADE-REC-027
    def test_a_failed_take_keeps_its_recording_and_log(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / "raw.cast").write_text(json.dumps({"version": 3, "term": {"cols": 100, "rows": 30}}) + "\n[0.5, \"o\", \"$ \"]\n")
            log = {"stretches": [], "pauses": [], "stops": [], "outcome": {"complete": False, "reason": "time limit"}}
            code = rec.finish(folder, log, rec.Options(), diff="")
            self.assertEqual(code, 1)
            self.assertTrue((folder / "raw.cast").exists())
            self.assertEqual(json.loads((folder / "take.json").read_text())["outcome"]["reason"], "time limit")


def cast(events, header=None):
    header = header or {"version": 3, "term": {"cols": 100, "rows": 30, "type": "xterm-256color"},
                        "timestamp": 1794267811, "idle_time_limit": 2.0, "command": "zsh -i"}
    return header, [list(e) for e in events]


def length(events):
    return sum(e[0] for e in events)


class Timing(unittest.TestCase):
    # @spec CASCADE-REC-029
    def test_shortens_long_working_stretches_only(self):
        _, events = cast([(1.0, "o", "x")] * 50)
        log = {"stretches": [[10.0, 50.0], [45.0, 45.0]], "pauses": []}
        _, out = rec.retime(*cast(events), log, rec.Options())
        inside = sum(e[0] for e, t in zip(out, range(1, 51)) if 10 < t <= 50)
        self.assertAlmostEqual(inside, 6.0, places=6)
        self.assertEqual(rec.Options().stretch_limit, 6.0)
        short = {"stretches": [[10.0, 15.0]], "pauses": []}
        _, out = rec.retime(*cast(events), short, rec.Options())
        self.assertAlmostEqual(sum(e[0] for e, t in zip(out, range(1, 51)) if 10 < t <= 15), 5.0, places=6)

    # @spec CASCADE-REC-046
    def test_speeds_up_typing_by_the_typing_speed(self):
        events = [(0.1, "o", "k")] * 40
        log = {"stretches": [], "pauses": [], "typing": [[1.0, 3.0]]}
        self.assertEqual(rec.Options().typing_speed, 1.6)
        _, same = rec.retime(*cast(events), log, rec.Options(typing_speed=1.0))
        self.assertAlmostEqual(length(same), 4.0, places=6)
        _, faster = rec.retime(*cast(events), log, rec.Options(typing_speed=2.0))
        self.assertAlmostEqual(length(faster), 3.0, places=6)
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            rec.write_cast(folder / "raw.cast", *cast(events))
            (folder / "take.json").write_text(json.dumps(dict(log, stops=[], outcome={"complete": True})))
            rec.main(["--retime", str(folder), "--typing-speed", "2"])
            self.assertAlmostEqual(length(rec.read_cast(folder / "cascade.cast")[1]), 3.0, places=4)

    # @spec CASCADE-REC-030, CASCADE-REC-031
    def test_keeps_reading_pauses_and_caps_other_gaps(self):
        _, events = cast([(1.0, "o", "a"), (10.0, "o", "b"), (6.0, "o", "c")])
        log = {"stretches": [], "pauses": [[12.0, 16.0]]}
        _, out = rec.retime(*cast(events), log, rec.Options())
        self.assertEqual([round(e[0], 6) for e in out], [1.0, 1.5, 4.0 + 1.5])

    # @spec CASCADE-REC-032
    def test_keeps_every_event_unchanged(self):
        events = [(0.5, "o", "a"), (3.0, "m", ""), (0.1, "r", "100x30"), (2.0, "o", "\u001b[1mb"), (0.0, "x", "0")]
        _, out = rec.retime(*cast(events), {"stretches": [[0.0, 4.0]], "pauses": []}, rec.Options())
        self.assertEqual([e[1:] for e in out], [list(e[1:]) for e in events])

    # @spec CASCADE-REC-033
    def test_writes_the_title_size_and_theme(self):
        header, _ = rec.retime(*cast([(1.0, "o", "a")]), {"stretches": [], "pauses": []}, rec.Options())
        self.assertEqual(header["title"], "LID cascade: end trials at local midnight")
        self.assertEqual((header["term"]["cols"], header["term"]["rows"]), (100, 30))
        theme = header["term"]["theme"]
        self.assertRegex(theme["fg"], r"^#[0-9a-f]{6}$")
        self.assertRegex(theme["bg"], r"^#[0-9a-f]{6}$")
        self.assertEqual(len(theme["palette"].split(":")), 16)
        for color in theme["palette"].split(":"):
            self.assertRegex(color, r"^#[0-9a-f]{6}$")
        self.assertNotIn("idle_time_limit", header)

    # @spec CASCADE-REC-034
    def test_flags_a_take_over_180_seconds(self):
        self.assertNotIn("over 180", rec.length_report(180.0))
        self.assertIn("over 180", rec.length_report(181.0))
        self.assertIn("3:01", rec.length_report(181.0))

    # @spec CASCADE-REC-035
    def test_retimes_a_take_again_without_recording(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            header, events = cast([(1.0, "o", "x")] * 40)
            rec.write_cast(folder / "raw.cast", header, events)
            (folder / "take.json").write_text(json.dumps({"stretches": [[5.0, 35.0]], "pauses": [],
                                                          "stops": [], "outcome": {"complete": True}}))
            self.assertEqual(rec.main(["--retime", str(folder), "--stretch-limit", "4"]), 0)
            _, out = rec.read_cast(folder / "cascade.cast")
            self.assertAlmostEqual(length(out), 10.0 + 4.0, places=4)
            self.assertAlmostEqual(json.loads((folder / "take.json").read_text())["retimed_length"], 14.0, places=2)


class WhatATakeLeaves(unittest.TestCase):
    # @spec CASCADE-REC-036
    def test_writes_the_take_folder(self):
        self.assertEqual(rec.takes_folder(), HERE / "takes")
        self.assertRegex(rec.take_name(), r"^\d{8}-\d{6}$")
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            header, events = cast([(1.0, "o", "x")] * 3)
            rec.write_cast(folder / "raw.cast", header, events)
            log = {"stretches": [], "pauses": [], "stops": [], "outcome": {"complete": True}}
            self.assertEqual(rec.finish(folder, log, rec.Options(), diff="diff --git a b\n"), 0)
            self.assertEqual(sorted(p.name for p in folder.iterdir()), ["cascade.cast", "diff.patch", "raw.cast", "take.json"])

    # @spec CASCADE-REC-037
    def test_logs_what_ran_and_what_happened(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            header, events = cast([(2.0, "o", "x")] * 3)
            rec.write_cast(folder / "raw.cast", header, events)
            log = rec.take_log(rec.Options(), claude_version="2.1.321 (Claude Code)")
            log.update({"stretches": [], "pauses": [], "stops": [{"at": 1.0, "reply": "approved"}],
                        "outcome": {"complete": False, "reason": "time limit"}})
            rec.finish(folder, log, rec.Options(), diff="")
            saved = json.loads((folder / "take.json").read_text())
        shipped = json.loads((REPO_ROOT / "plugins/linked-intent-dev/.claude-plugin/plugin.json").read_text())["version"]
        self.assertEqual(saved["claude_code_version"], "2.1.321 (Claude Code)")
        self.assertEqual((saved["model"], saved["effort"]), ("claude-opus-5-5", "medium"))
        self.assertEqual(saved["lid_version"], shipped)
        self.assertEqual(saved["stops"], [{"at": 1.0, "reply": "approved"}])
        self.assertAlmostEqual(saved["real_length"], 6.0)
        self.assertAlmostEqual(saved["retimed_length"], 4.5)
        self.assertEqual(saved["outcome"], {"complete": False, "reason": "time limit"})

    # @spec CASCADE-REC-047
    def test_names_a_poster_frame_after_the_request(self):
        take, term, error = Script().take()
        typed = next(t for kind, text, t, _ in term.events if kind == "line" and text == rec.REQUEST) - take.t0
        self.assertAlmostEqual(take.log["request_typed"], typed, delta=0.05)
        events = [(1.0, "o", "x")] * 30
        log = {"stretches": [[2.0, 22.0]], "pauses": [], "typing": [], "request_typed": 25.0}
        header, out = rec.retime(*cast(events), log, rec.Options())
        self.assertEqual(rec.poster(cast(events)[1], out, log), "npt:0:11")  # 2s, then 20s played as 6s, then 3s to 25s
        halves = [(0.5, "o", "x")] * 60
        self.assertEqual(rec.poster(halves, halves, {"request_typed": 10.6}), "npt:0:11", "10.5s, rounded up")
        self.assertIsNone(rec.poster(cast(events)[1], out, {"stretches": [], "pauses": []}))
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            rec.write_cast(folder / "raw.cast", *cast(events))
            rec.finish(folder, dict(log, stops=[], outcome={"complete": True}), rec.Options(), diff="")
            self.assertEqual(json.loads((folder / "take.json").read_text())["poster"], "npt:0:11")

    # @spec CASCADE-REC-038
    def test_git_ignores_takes_and_dependencies(self):
        for path in ["tools/cascade-recording/takes/20261111-120000/raw.cast",
                     "tools/cascade-recording/trial-app/node_modules/vitest/index.js"]:
            run = subprocess.run(["git", "check-ignore", "-q", path], cwd=REPO_ROOT)
            self.assertEqual(run.returncode, 0, path)

    # @spec CASCADE-REC-039
    def test_never_uploads(self):
        source = (HERE / "record.py").read_text()
        self.assertNotRegex(source, r"[\"']upload[\"']")
        self.assertNotIn("asciinema.org", source)


if __name__ == "__main__":
    unittest.main()
