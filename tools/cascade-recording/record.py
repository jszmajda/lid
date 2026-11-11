#!/usr/bin/env python3
"""Make a take of the home page's cascade recording.

    python3 tools/cascade-recording/record.py [options]
    python3 tools/cascade-recording/record.py --retime <take folder> [timing options]

A take copies the trial project to a fresh folder, records a clean terminal
with asciinema inside tmux, and drives a live Claude Code session through the
home page's change of mind. It types the commands and the request, watches the
screen for each stop for review, and types a reply. Afterward it writes a
second copy of the recording with the agent's working stretches shortened.
The tool never uploads a recording.

See docs/intent/cascade-recording/cascade-recording-design.md.
"""

from __future__ import annotations

import argparse
import datetime
import json
import math
import os
import random
import re
import shlex
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent
TRIAL_APP = HERE / "trial-app"
SHELL_DIR = HERE / "shell"
PLUGIN = REPO_ROOT / "plugins" / "linked-intent-dev"

# @spec CASCADE-REC-003
REQUEST = "End trials at midnight in each user's own time zone."

# @spec CASCADE-REC-014, CASCADE-REC-023
# Each command follows a comment saying what it shows.
OPENING = [("This app has LID set up. Its trial design says when a free trial ends:",
            'grep -A2 "## When the trial ends" docs/intent/trial/trial-design.md'),
           ("Requirement TRIAL-003 says the same, and the test and code that build it cite its ID:",
            "grep -rn TRIAL-003 docs src tests"),
           ("The tests pass:", "npm test")]
CLAUDE_INTRO = "Next, you ask Claude Code, with LID installed, to change when trials end."
CLOSING = [("The change reached every level: the design, the requirements, the tests, and the code.", "git diff --stat"),
           ("TRIAL-003 still leads to everything built from it:", "grep -rn TRIAL-003 docs src tests"),
           ("And every test passes:", "npm test")]

# Commands whose output pushes their comment off the screen: the comment holds
# before the command runs instead of after its output.
LONG_OUTPUT = {"npm test"}

# @spec CASCADE-REC-044
# The asides typed into Claude Code's input box, by what the stop shows.
ASIDES = {
    "recommendation": "(The HLD and its tenet still hold. Claude asks which midnight you mean, and recommends the one that never shortens a trial.)",
    "hld": "(The HLD and its tenet still hold, so Claude moves on to the trial's design.)",
    "design": "(Claude rewrote the trial's design: a trial now ends at the first local midnight after 720 hours.)",
    "design_other": "(Claude rewrote the trial's design and waits for your review.)",
    "tokyo": "(Claude added the Tokyo signup to the design as a worked example.)",
    "revised": "(Claude revised the design and waits for your review.)",
    "specs_other": "(Claude rewrote the requirements to match the design.)",
    "review": "(Claude waits for your review.)",
    "questions": "(Claude has follow-up questions and recommends an answer to each.)",
}

# @spec CASCADE-REC-019, CASCADE-REC-020, CASCADE-REC-021, CASCADE-REC-041
REPLIES = {
    "recommendation": "Go with your recommendation.",
    "recommendations": "Approved. Go with your recommendations.",
    "correction": "Looks right. Add the Tokyo signup from the test as a worked example, so anyone can check the rule.",
    "approved": "Approved.",
    "handoff": "Looks good. Take it from here on your own: update the test and the code, and show me when the tests pass.",
}

TITLE = "LID cascade: end trials at local midnight"
DEFAULT_MODEL, DEFAULT_EFFORT = "claude-opus-5-5", "medium"
COLS, ROWS = 100, 30
TMUX_SOCKET, TMUX_SESSION = "lid-cascade", "take"
PROGRAMS = ["tmux", "asciinema", "git", "npm", "claude"]
ENV_KEYS = ["HOME", "USER", "LOGNAME", "PATH", "TERM", "LANG", "TMPDIR"]
TOUR_RECORD = "Has met the LID tour: declined"
TAKE_MARK = Path(".git") / "cascade-take"

# The four files a complete change touches, by the name the replies use.
FILES = {"design": "docs/intent/trial/trial-design.md",
         "specs": "docs/intent/trial/trial-specs.md",
         "test": "tests/trial.test.ts",
         "code": "src/trial.ts"}

# What the screen shows: Claude Code's hint while the agent works, its folder
# trust prompt, the footer of a menu of options, the footer of any other
# prompt (such as a permission prompt), and a numbered option in a menu.
HINT = "esc to interrupt"
TRUST = re.compile(r"trust this folder|one you trust")
MENU = re.compile(r"to navigate")
DIALOG = re.compile(r"Esc to cancel")
OPTION = re.compile(r"^\s*(❯\s*)?(\d+)\.\s+(.+)$")
MIDNIGHT_720 = re.compile(r"^(?=.*midnight)(?=.*\b720\b).*$", re.I | re.M)
RECOMMENDS = re.compile(r"recommend|suggest|propos|\bI'd\b", re.I)
CLOCK_CHANGE = re.compile(r"clock|daylight", re.I)
SPEC_LINE = re.compile(r"\*\*(TRIAL-\d{3})\*\*:?[ \t]*([^\n]*)")
ANSI = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")
KEEPS_720 = re.compile(r"\b(after|at least|past|beyond) (the )?720(th)? ?(h\b|hours?|hrs?\b)", re.I)

# The site's dark ink on the recording frame's brown-black.
# Colors as lowercase #rrggbb, the only form the player's upload accepts.
THEME = {"fg": "#f4ede8", "bg": "#1a0f0a",
         "palette": ":".join(["#352b25", "#e07a6a", "#8ec07c", "#e3b27a", "#8fbbda", "#c79ad6", "#7fc4bd", "#b8aba3",
                              "#6b5f58", "#ff7a4f", "#a9d494", "#f0c896", "#a9cde6", "#d9b3e4", "#9fd8d1", "#f4ede8"])}


@dataclass
class Options:
    model: str = DEFAULT_MODEL
    effort: str = DEFAULT_EFFORT
    take_dir: str = "/tmp/trial-app"
    reading_pause: float = 4.0
    stop_limit: int = 8
    time_limit: float = 1800.0
    stretch_limit: float = 6.0
    typing_speed: float = 1.6
    pause_cap: float = 1.5
    max_length: float = 180.0
    per_output_line: float = 0.5
    clear_hold: float = 3.0
    output_cap: float = 4.0
    typing_delay: float = 0.035
    hold_base: float = 1.0
    read_rate: float = 40.0
    seed: int = None
    settle: float = 2.0
    hint_wait: float = 30.0
    poll: float = 0.1


class TakeFailed(Exception):
    pass


# ── Before recording ──────────────────────────────────────────────────────

# @spec CASCADE-REC-008
def missing_programs(which=shutil.which):
    return [name for name in PROGRAMS if not which(name)]


def mark_take_folder(folder):
    mark = Path(folder) / TAKE_MARK
    mark.parent.mkdir(parents=True, exist_ok=True)
    mark.write_text("Made by tools/cascade-recording/record.py\n")


# @spec CASCADE-REC-009
def prepare_take_folder(src, dest, install):
    """Copy the trial project to `dest`, install it, and commit the starting state."""
    src, dest = Path(src), Path(dest)
    if dest.is_symlink() or (dest.exists() and any(dest.iterdir()) and not (dest / TAKE_MARK).exists()):
        raise TakeFailed("%s holds something no take made; choose another take folder with --take-dir." % dest)
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest, symlinks=True, ignore=shutil.ignore_patterns("node_modules"))
    install(dest)
    git = ["git", "-c", "user.name=Trial App", "-c", "user.email=trial-app@example.com", "-c", "commit.gpgsign=false"]
    for args in (["init", "-q", "-b", "main"], ["add", "-A"], ["commit", "-q", "-m", "Start the trial app"]):
        subprocess.run(git + args, cwd=dest, check=True, capture_output=True)
    mark_take_folder(dest)


def npm_ci(folder):
    subprocess.run(["npm", "ci", "--no-audit", "--no-fund", "--silent"], cwd=folder, check=True)


def memory_folder(take_dir, home):
    """Claude Code's memory folder for a project folder."""
    return Path(home) / ".claude" / "projects" / re.sub(r"[^A-Za-z0-9]", "-", str(Path(take_dir).resolve())) / "memory"


# @spec CASCADE-REC-010
def seed_memory(take_dir, home):
    """Leave only the tour's record in Claude Code's memory for the take folder."""
    folders = {memory_folder(take_dir, home),
               Path(home) / ".claude" / "projects" / re.sub(r"[^A-Za-z0-9]", "-", os.path.abspath(take_dir)) / "memory"}
    for folder in folders:
        if folder.exists():
            shutil.rmtree(folder)
        folder.mkdir(parents=True)
        (folder / "lid_tour.md").write_text(
            "---\nname: lid-tour\ndescription: Whether this person has met the LID newcomer tour\n"
            "metadata:\n  type: user\n---\n\n%s\n" % TOUR_RECORD)
        (folder / "MEMORY.md").write_text("- [LID tour](lid_tour.md) — %s\n" % TOUR_RECORD)


# ── The recorded terminal ─────────────────────────────────────────────────

# @spec CASCADE-REC-012, CASCADE-REC-013
def take_env(base, model, effort):
    """The recorded shell's whole environment."""
    env = {key: base[key] for key in ENV_KEYS if key in base}
    env["TERM"] = "xterm-256color"
    env.update(ZDOTDIR=str(SHELL_DIR), LID_PLUGIN=str(PLUGIN), LID_MODEL=model, LID_EFFORT=effort,
               CLAUDE_CODE_ENABLE_PROMPT_SUGGESTION="false")
    return env


# @spec CASCADE-REC-011
def tmux_argv(take_dir, raw_cast, env):
    assignments = " ".join(shlex.quote("%s=%s" % item) for item in env.items())
    inner = "cd %s && exec env -i %s asciinema rec --quiet --overwrite --command 'zsh -i' %s" % (
        shlex.quote(str(take_dir)), assignments, shlex.quote(str(raw_cast)))
    return ["tmux", "-L", TMUX_SOCKET, "-f", str(SHELL_DIR / "tmux.conf"), "new-session", "-d",
            "-s", TMUX_SESSION, "-x", str(COLS), "-y", str(ROWS), inner]


class TmuxTerm:
    """The recorded tmux pane: read what it shows, type into it."""

    def tmux(self, *args):
        return subprocess.run(["tmux", "-L", TMUX_SOCKET] + list(args), capture_output=True, text=True)

    def screen(self):
        return "\n".join(line.rstrip() for line in self.tmux("capture-pane", "-p", "-t", TMUX_SESSION).stdout.splitlines())

    def type(self, char):
        self.tmux("send-keys", "-t", TMUX_SESSION, "-l", char)

    def key(self, name):
        self.tmux("send-keys", "-t", TMUX_SESSION, name)

    def running(self):
        return self.tmux("has-session", "-t", TMUX_SESSION).returncode == 0


class TakeProject:
    """The take folder, read from outside the recording."""

    def __init__(self, folder):
        self.folder = Path(folder)
        self.passed = None

    def read(self, path):
        file = self.folder / path
        return file.read_text() if file.exists() else ""

    def at_start(self, path):
        return subprocess.run(["git", "show", "HEAD:" + path], cwd=self.folder, capture_output=True, text=True).stdout

    def facts(self):
        hld = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", "docs/high-level-design.md"], cwd=self.folder)
        return {"hld_changed": bool(hld.returncode), "design": self.read(FILES["design"]),
                "specs_before": self.at_start(FILES["specs"]), "specs_after": self.read(FILES["specs"]),
                "tests_passed": self.passed}

    def changed(self):
        return {key for key, path in FILES.items()
                if subprocess.run(["git", "diff", "--quiet", "HEAD", "--", path], cwd=self.folder).returncode}

    def tests_pass(self):
        run = subprocess.run(["npm", "test", "--silent"], cwd=self.folder, capture_output=True, text=True, timeout=300)
        found = re.search(r"Tests\s+(\d+) passed", ANSI.sub("", run.stdout + run.stderr))
        self.passed = int(found.group(1)) if found and run.returncode == 0 else None
        return run.returncode == 0

    def done(self):
        return self.changed() == set(FILES) and self.tests_pass()


# ── The script ────────────────────────────────────────────────────────────

def last_line(screen):
    lines = [line.rstrip() for line in screen.splitlines() if line.strip()]
    return lines[-1] if lines else ""


def at_prompt(screen):
    return last_line(screen) == "$"


def claude_ready(screen):
    return "❯" in screen and HINT not in screen


# @spec CASCADE-REC-042
def output_lines(screen, command):
    """How many non-blank lines `command` printed, from the screen after it ran."""
    lines = screen.splitlines()
    runs = [i for i, line in enumerate(lines) if line.rstrip() == "$ " + command]
    if not runs:
        return 0
    return sum(1 for line in lines[runs[-1] + 1:] if line.strip() and line.rstrip() != "$")


def input_empty(screen):
    inputs = [line.strip() for line in screen.splitlines() if line.lstrip().startswith("❯")]
    return not inputs or inputs[-1] == "❯"


# @spec CASCADE-REC-015
def keystroke_delay(char, base, rng):
    """How long a person waits after typing `char`."""
    delay = base * rng.uniform(0.5, 2.0)
    if char == " ":
        delay += rng.uniform(0.03, 0.12)
    elif char in ".,:;?!)":
        delay += rng.uniform(0.12, 0.3)
    if rng.random() < 0.03:
        delay += rng.uniform(0.2, 0.45)
    return delay


def spec_texts(text):
    return dict(SPEC_LINE.findall(text))


def join_ids(ids):
    numbers = [int(i.rsplit("-", 1)[1]) for i in ids]
    if len(ids) >= 3 and numbers == list(range(numbers[0], numbers[0] + len(ids))):
        return "%s to %s" % (ids[0], ids[-1])
    if len(ids) <= 2:
        return " and ".join(ids)
    return ", ".join(ids[:-1]) + ", and " + ids[-1]


# @spec CASCADE-REC-044
def aside(reply, facts):
    """The one sentence typed before a reply, from what the tool can check."""
    changed, given = facts["changed"], facts["given"]
    if reply == "recommendation":
        return ASIDES["recommendation"]
    if reply == "correction":
        return ASIDES["design"] if MIDNIGHT_720.search(facts["design"]) else ASIDES["design_other"]
    if reply == "handoff":
        before, after = spec_texts(facts["specs_before"]), spec_texts(facts["specs_after"])
        rewritten = sorted(i for i in after if i in before and after[i] != before[i])
        added = sorted(i for i in after if i not in before)
        if not rewritten and not added:
            return ASIDES["specs_other"]
        parts = (["rewrote " + join_ids(rewritten)] if rewritten else []) + (["added " + join_ids(added)] if added else [])
        sentence = "(Claude " + " and ".join(parts)
        if not added:
            sentence += " to match the design"
        elif any(CLOCK_CHANGE.search(after[i]) for i in added):
            sentence += ", for cases such as daylight saving"
        return sentence + ".)"
    if reply == "exit":
        if facts.get("tests_passed"):
            return "(Claude updated the tests and the code, and all %d tests pass.)" % facts["tests_passed"]
        return "(Claude updated the tests and the code, and the tests pass.)"
    if reply in ("approved", "recommendations"):
        if reply == "approved" and not changed and not facts["hld_changed"] and not given & {"correction", "handoff"}:
            return ASIDES["hld"]
        if facts.get("last") == "correction":
            said = ASIDES["tokyo"] if "tokyo" in facts["design"].lower() else ASIDES["revised"]
            if reply == "recommendations":
                said = said[:-2] + ", and recommends answers to its follow-up questions.)"
            return said
        if reply == "recommendations":
            return ASIDES["questions"]
    return ASIDES["review"]


# @spec CASCADE-REC-019, CASCADE-REC-020, CASCADE-REC-021, CASCADE-REC-041
def choose_reply(changed, given, screen=""):
    if "specs" in changed and "handoff" not in given:
        return "handoff"
    if not changed and "recommend" in screen.lower() and "recommendation" not in given:
        return "recommendation"
    if "design" in changed and not given & {"correction", "handoff"}:
        return "correction"
    if RECOMMENDS.search(screen):
        return "recommendations"
    return "approved"


def parse_menu(screen):
    """The menu at the bottom of the screen: the highlighted option's number,
    and each option's number and text (its label and the lines under it)."""
    lines = screen.splitlines()
    heads = [(i, OPTION.match(line)) for i, line in enumerate(lines) if OPTION.match(line)]
    starts = [k for k, (_, m) in enumerate(heads) if m.group(2) == "1"]
    if not starts:
        return 1, []
    heads = heads[starts[-1]:]
    menu = [heads[0]]
    for i, m in heads[1:]:
        if int(m.group(2)) != int(menu[-1][1].group(2)) + 1:
            break
        menu.append((i, m))
    cursor, options = 1, []
    for k, (i, m) in enumerate(menu):
        end = menu[k + 1][0] if k + 1 < len(menu) else len(lines)
        under = [line.strip() for line in lines[i + 1:end]
                 if line.strip() and not line.strip().startswith("─") and not DIALOG.search(line)]
        options.append((int(m.group(2)), " ".join([m.group(3).strip()] + under)))
        if m.group(1):
            cursor = int(m.group(2))
    return cursor, options


# @spec CASCADE-REC-040
def choose_option(options):
    for number, text in options:
        if "(Recommended)" in text:
            return number
    for number, text in options:
        if KEEPS_720.search(text):
            return number
    for number, text in options:
        if text.startswith("Submit"):
            return number
    return None


class Take:
    """Drives one take through a terminal, logging times since the recording began."""

    def __init__(self, term, project, clock, sleep, opts, t0):
        self.term, self.project, self.clock, self.sleep, self.opts, self.t0 = term, project, clock, sleep, opts, t0
        seed = opts.seed if opts.seed is not None else random.randrange(1 << 30)
        self.rng = random.Random(seed)
        self.log = {"stretches": [], "pauses": [], "typing": [], "stops": [], "seed": seed}
        self.given = set()
        self.last = None

    def now(self):
        return self.clock() - self.t0

    # @spec CASCADE-REC-014, CASCADE-REC-023, CASCADE-REC-045
    def run(self):
        self.watch(at_prompt, 0.5)
        for comment, command in OPENING:
            self.narrated(comment, command)
        self.wait(self.opts.clear_hold)
        self.clear_screen()
        self.narrate(CLAUDE_INTRO)
        self.type_line("claude")
        self.watch(claude_ready, self.opts.settle)
        self.type_line(REQUEST)
        self.log["request_typed"] = round(self.now(), 3)
        self.converse()
        self.watch(at_prompt, 0.5)
        self.clear_screen()
        for comment, command in CLOSING:
            self.narrated(comment, command)

    def clear_screen(self):
        self.term.key("C-l")
        self.watch(at_prompt, 0.5)

    def narrate(self, comment):
        """Type a shell comment, then hold it for the viewer to read."""
        line = "# " + comment
        self.shell(line)
        self.hold(line)

    # @spec CASCADE-REC-042
    def narrated(self, comment, command):
        """A comment and its command. A short output holds after it, so the
        viewer reads the comment and the output together; a long one holds
        after the comment, before the output pushes it off the screen."""
        if command in LONG_OUTPUT:
            self.narrate(comment)
            self.shell(command)
            return
        line = "# " + comment
        self.shell(line)
        screen = self.shell(command)
        self.hold(line, min(self.opts.output_cap, self.opts.per_output_line * output_lines(screen, command)))

    # @spec CASCADE-REC-042
    def hold(self, text, extra=0.0):
        start = self.now()
        self.sleep(self.opts.hold_base + len(text) / self.opts.read_rate + extra)
        self.log["pauses"].append([round(start, 3), round(self.now(), 3)])

    # @spec CASCADE-REC-043
    def say(self, text):
        """Type an aside into Claude Code's input box, hold it, and clear it unsent."""
        self.type_text(text)
        self.hold(text)
        for _ in range(8):
            self.term.key("C-u")
            self.sleep(0.15)
            if input_empty(self.term.screen()):
                break

    # @spec CASCADE-REC-024, CASCADE-REC-025, CASCADE-REC-026
    def check(self, screen):
        if TRUST.search(screen):
            raise TakeFailed("Claude Code asked whether to trust the folder; run `claude` once in %s, "
                             "answer it, and make the take again." % self.opts.take_dir)
        if DIALOG.search(screen) and not MENU.search(screen):
            tail = "\n".join(screen.splitlines()[-8:])
            raise TakeFailed("Claude Code showed a prompt a typed reply can't answer:\n%s" % tail)
        if self.now() > self.opts.time_limit:
            raise TakeFailed("The take ran past its time limit of %g minutes." % (self.opts.time_limit / 60))

    def watch(self, ready, stable):
        """Wait until the screen is ready and has not changed for `stable` seconds."""
        last, since = None, self.clock()
        while True:
            screen = self.term.screen()
            self.check(screen)
            if screen != last:
                last, since = screen, self.clock()
            if ready(screen) and self.clock() - since >= stable:
                return screen
            self.sleep(self.opts.poll)

    # @spec CASCADE-REC-015
    # @spec CASCADE-REC-028
    def type_text(self, text):
        start = self.now()
        for char in text:
            self.term.type(char)
            self.sleep(keystroke_delay(char, self.opts.typing_delay, self.rng))
        self.log["typing"].append([round(start, 3), round(self.now(), 3)])

    def type_line(self, text):
        self.type_text(text)
        self.term.key("Enter")

    def shell(self, command):
        self.type_line(command)
        return self.watch(at_prompt, 0.5)

    # @spec CASCADE-REC-017, CASCADE-REC-028
    def await_stop(self):
        """Wait for the agent to work and then stop; log the working stretch."""
        began = self.clock()
        start = end = None
        last, since = None, self.clock()
        while True:
            screen = self.term.screen()
            self.check(screen)
            now = self.clock()
            if screen != last:
                last, since = screen, now
            if HINT in screen:
                start = now if start is None else start
                end = None
            elif start is not None and end is None:
                end = now
            settled = now - since >= self.opts.settle
            if end is not None and settled:
                break
            if start is None and now - began >= self.opts.hint_wait and settled:
                break
            self.sleep(self.opts.poll)
        if start is not None:
            self.log["stretches"].append([round(start - self.t0, 3), round(end - self.t0, 3)])
        return screen

    # @spec CASCADE-REC-018, CASCADE-REC-030
    def reading_pause(self):
        self.wait(self.opts.reading_pause)

    # @spec CASCADE-REC-045
    def wait(self, seconds):
        """Hold the screen still, logged as a reading pause so retiming keeps it."""
        start = self.now()
        self.sleep(seconds)
        self.log["pauses"].append([round(start, 3), round(self.now(), 3)])

    # @spec CASCADE-REC-016, CASCADE-REC-022, CASCADE-REC-026
    def converse(self):
        stops = 0
        while True:
            screen = self.await_stop()
            stops += 1
            if stops > self.opts.stop_limit:
                raise TakeFailed("Claude Code stopped for review more than %d times." % self.opts.stop_limit)
            done = self.project.done()
            if MENU.search(screen) and not done:
                self.choose(screen)
                continue
            reply = "exit" if done else choose_reply(self.project.changed(), self.given, screen)
            facts = dict(self.project.facts(), changed=self.project.changed(), given=set(self.given), last=self.last)
            said = aside(reply, facts)
            self.say(said)
            self.log["stops"].append({"at": round(self.now(), 2), "reply": reply, "aside": said})
            if done:
                self.type_line("/exit")
                return
            self.type_line(REPLIES[reply])
            self.given.add(reply)
            self.last = reply


    # @spec CASCADE-REC-040
    def choose(self, screen):
        """Answer a menu of options with the arrow keys and Enter."""
        cursor, options = parse_menu(screen)
        target = choose_option(options)
        if target is None:
            raise TakeFailed("Claude Code asked a question with no option that keeps 720 hours, is recommended, "
                             "or submits:\n%s" % "\n".join("%d. %s" % o for o in options))
        self.reading_pause()
        self.log["stops"].append({"at": round(self.now(), 2), "reply": "choice", "option": dict(options)[target]})
        for _ in range(abs(target - cursor)):
            self.term.key("Down" if target > cursor else "Up")
            self.sleep(self.opts.typing_delay * 5)
        self.term.key("Enter")


# ── Timing ────────────────────────────────────────────────────────────────

def read_cast(path):
    lines = Path(path).read_text().splitlines()
    return json.loads(lines[0]), [json.loads(line) for line in lines[1:] if line.strip()]


def write_cast(path, header, events):
    with open(path, "w") as f:
        f.write(json.dumps(header, ensure_ascii=False) + "\n")
        for event in events:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")


def total(events):
    return sum(event[0] for event in events)


# @spec CASCADE-REC-029, CASCADE-REC-030, CASCADE-REC-031, CASCADE-REC-032, CASCADE-REC-033
def retime(header, events, log, opts):
    """Change only the delays between events: shorten working stretches, keep
    reading pauses, and cap every other gap."""
    stretches = [(a, b, min(1.0, opts.stretch_limit / (b - a)) if b > a else 1.0) for a, b in log["stretches"]]
    # @spec CASCADE-REC-046
    stretches += [(a, b, 1.0 / opts.typing_speed) for a, b in log.get("typing", [])]
    pauses = [(a, b) for a, b in log["pauses"]]
    bounds = sorted({x for a, b, _ in stretches for x in (a, b)} | {x for p in pauses for x in p})
    out, t = [], 0.0
    for delay, kind, data in events:
        a, b = t, t + delay
        t = b
        cuts = [a] + [x for x in bounds if a < x < b] + [b]
        kept, other = 0.0, 0.0
        for x0, x1 in zip(cuts, cuts[1:]):
            mid = (x0 + x1) / 2
            if any(p0 <= mid <= p1 for p0, p1 in pauses):
                kept += x1 - x0
                continue
            factor = next((k for s0, s1, k in stretches if s0 <= mid <= s1), None)
            if factor is None:
                other += x1 - x0
            else:
                kept += (x1 - x0) * factor
        out.append([round(kept + min(other, opts.pause_cap), 6), kind, data])
    term = header.get("term", {})
    new_term = {"cols": term.get("cols", COLS), "rows": term.get("rows", ROWS)}
    if term.get("type"):
        new_term["type"] = term["type"]
    new_term["theme"] = THEME
    new_header = {"version": header.get("version", 3), "term": new_term, "title": TITLE}
    if header.get("timestamp"):
        new_header["timestamp"] = header["timestamp"]
    return new_header, out


# @spec CASCADE-REC-047
def poster(raw_events, retimed_events, log):
    """The first whole second after the request was sent, in the retimed recording, as npt:M:SS."""
    if log.get("request_typed") is None:
        return None
    t = rt = at = 0.0
    for (delay, _, _), (new_delay, _, _) in zip(raw_events, retimed_events):
        t += delay
        rt += new_delay
        if t > log["request_typed"]:
            break
        at = rt
    whole = int(math.ceil(round(at, 3)))
    return "npt:%d:%02d" % (whole // 60, whole % 60)


# @spec CASCADE-REC-034
def length_report(seconds):
    whole = int(round(seconds))
    report = "Retimed length %d:%02d (%d seconds)." % (whole // 60, whole % 60, whole)
    if seconds > Options.max_length:
        report += " That's over %d seconds: make another take, or change the timing options and retime this one." % Options.max_length
    return report


# ── What a take leaves ────────────────────────────────────────────────────

def takes_folder():
    return HERE / "takes"


def take_name():
    return datetime.datetime.now().strftime("%Y%m%d-%H%M%S")


def lid_version():
    return json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text())["version"]


# @spec CASCADE-REC-037
def take_log(opts, claude_version):
    return {"started": datetime.datetime.now().isoformat(timespec="seconds"),
            "claude_code_version": claude_version, "model": opts.model, "effort": opts.effort,
            "lid_version": lid_version(), "request": REQUEST, "take_dir": opts.take_dir}


# @spec CASCADE-REC-027, CASCADE-REC-036
def finish(folder, log, opts, diff):
    """Write the take's diff, retimed recording, and log; return the exit status."""
    folder = Path(folder)
    (folder / "diff.patch").write_text(diff)
    raw = folder / "raw.cast"
    if raw.exists():
        header, events = read_cast(raw)
        log["real_length"] = round(total(events), 2)
        new_header, new_events = retime(header, events, log, opts)
        write_cast(folder / "cascade.cast", new_header, new_events)
        log["retimed_length"] = round(total(new_events), 2)
        if poster(events, new_events, log):
            log["poster"] = poster(events, new_events, log)
        print(length_report(log["retimed_length"]))
    (folder / "take.json").write_text(json.dumps(log, indent=2, ensure_ascii=False) + "\n")
    outcome = log.get("outcome", {})
    if outcome.get("complete"):
        print("Take complete: %s" % folder)
        return 0
    print("Take failed: %s\n%s" % (folder, outcome.get("reason", "")))
    return 1


# @spec CASCADE-REC-035
def retime_take(folder, opts):
    folder = Path(folder)
    log = json.loads((folder / "take.json").read_text())
    header, events = read_cast(folder / "raw.cast")
    new_header, new_events = retime(header, events, log, opts)
    write_cast(folder / "cascade.cast", new_header, new_events)
    log["real_length"] = round(total(events), 2)
    log["retimed_length"] = round(total(new_events), 2)
    if poster(events, new_events, log):
        log["poster"] = poster(events, new_events, log)
    (folder / "take.json").write_text(json.dumps(log, indent=2, ensure_ascii=False) + "\n")
    print(length_report(log["retimed_length"]))
    return 0


def take_diff(take_dir):
    subprocess.run(["git", "add", "-A"], cwd=take_dir, capture_output=True)
    return subprocess.run(["git", "diff", "--cached", "HEAD"], cwd=take_dir, capture_output=True, text=True).stdout


def claude_version():
    return subprocess.run(["claude", "--version"], capture_output=True, text=True).stdout.strip()


def stop_recording(term):
    """End the recorded shell, which ends asciinema, then the tmux server."""
    if term.running():
        term.key("C-d")
        for _ in range(100):
            if not term.running():
                break
            time.sleep(0.1)
    term.tmux("kill-server")


# @spec CASCADE-REC-039
def record_take(opts):
    missing = missing_programs()
    if missing:
        print("Can't make a take; these programs can't be run: %s" % ", ".join(missing))
        return 2
    folder = takes_folder() / take_name()
    folder.mkdir(parents=True)
    print("Take folder: %s" % folder)
    log = take_log(opts, claude_version())
    log.update({"stretches": [], "pauses": [], "stops": []})
    take_dir = Path(opts.take_dir)
    try:
        prepare_take_folder(TRIAL_APP, take_dir, install=npm_ci)
    except TakeFailed as e:
        log["outcome"] = {"complete": False, "reason": str(e)}
        return finish(folder, log, opts, diff="")
    seed_memory(take_dir, Path.home())
    term = TmuxTerm()
    term.tmux("kill-server")
    subprocess.run(tmux_argv(take_dir, folder / "raw.cast", take_env(os.environ, opts.model, opts.effort)), check=True)
    take = Take(term, TakeProject(take_dir), time.monotonic, time.sleep, opts, time.monotonic())
    try:
        take.run()
        log["outcome"] = {"complete": True}
    except TakeFailed as e:
        log["outcome"] = {"complete": False, "reason": str(e)}
    except KeyboardInterrupt:
        log["outcome"] = {"complete": False, "reason": "Stopped by the maintainer."}
    finally:
        time.sleep(1.0)
        stop_recording(term)
    log.update(take.log)
    return finish(folder, log, opts, diff=take_diff(take_dir))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Make a take of the home page's cascade recording.")
    parser.add_argument("--retime", metavar="TAKE_FOLDER", help="retime an earlier take without recording")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--effort", default=DEFAULT_EFFORT)
    parser.add_argument("--take-dir", default=Options.take_dir)
    parser.add_argument("--reading-pause", type=float, default=Options.reading_pause, help="seconds")
    parser.add_argument("--stop-limit", type=int, default=Options.stop_limit)
    parser.add_argument("--time-limit", type=float, default=Options.time_limit / 60, help="minutes")
    parser.add_argument("--stretch-limit", type=float, default=Options.stretch_limit, help="seconds")
    parser.add_argument("--pause-cap", type=float, default=Options.pause_cap, help="seconds")
    parser.add_argument("--typing-speed", type=float, default=Options.typing_speed,
                        help="how many times faster typing plays when retimed")
    args = parser.parse_args(argv)
    opts = Options(model=args.model, effort=args.effort, take_dir=args.take_dir, reading_pause=args.reading_pause,
                   stop_limit=args.stop_limit, time_limit=args.time_limit * 60, stretch_limit=args.stretch_limit,
                   pause_cap=args.pause_cap, typing_speed=args.typing_speed)
    if args.retime:
        return retime_take(args.retime, opts)
    return record_take(opts)


if __name__ == "__main__":
    sys.exit(main())
