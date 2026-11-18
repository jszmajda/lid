"""Context telemetry: how close each session came to its context window, and how much of the repository it read.

    python3.12 context_telemetry.py --ids s3b-bare-1 s3b-bare-2 s3b-lid-full-1 --summary
    python3.12 context_telemetry.py --ids s2-bare-1 --no-repo --window 1000000

Reads each trajectory's `trajectory.json`, each change's `change.json`, and its turns' stream-json transcripts. Writes
`runs/<id>/context-telemetry.json` and prints one table per trajectory, a row per change; `--summary` adds per-arm
means. It makes no model calls. The one outside step is listing the repository at each change's commit with
`git ls-tree` in the trajectory's workspace volume (one container per trajectory); `--no-repo` skips it.

What it measures, per turn and rolled up per change (a change is one session; its turns resume it):

- Context occupancy: for each API call of the main thread, the context it sent (uncached input + cache read + cache
  write tokens). Claude Code emits one stream event per content block, each repeating the call's usage, so calls are
  counted by message id. Subagents have their own contexts and are reported apart. The share is of `--window`; the
  window the session itself reported (`modelUsage.contextWindow`) is recorded beside it.
- Compaction: system events whose subtype names compaction (`compact_boundary`), non-null `context_management` on an
  assistant message (context editing), and, as a cross-check, any drop of the main thread's context between
  consecutive calls of more than 30% and 20k tokens.
- Reading: Read calls, unique files read, the characters Read returned to the model, and the exact lines Read covered;
  Grep and Glob calls; Bash calls that read files (cat, nl, less, more, tac, head, tail, sed -n), search (grep, rg,
  git grep) or list (ls, find, tree, git ls-files, wc, du), parsed from the command (heredoc bodies dropped, simple
  `for` loops and braces expanded, cwd tracked); the characters those reading calls returned, by class of file read (a
  call that reads several classes splits its output evenly across the files it names); and skill bodies loaded.
- Repository size at the change's commit (and at the commit before it): blob sizes from `git ls-tree -r -l`, split into
  docs (*.md), tests (by path), and code (everything else), with tokens estimated as bytes / 4.
- Coverage: the share of the repository's bytes that Read covered (exact, by line); an estimate that adds whole files
  catted in full by Bash (a piped cat, head, tail and sed -n count as partial and add nothing; a cat whose output was
  persisted counts only if the persisted file was then Read); and a touched share, the bytes of every repository file
  any read form reached, which bounds coverage from above. Blob sizes are bytes, so Read coverage is measured in UTF-8
  bytes too; characters returned are measured in characters.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import posixpath
import re
import shlex
import statistics as st
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNS = HERE.parent / "runs"
DEFAULT_IMAGE = "lid-cost-eval-executor:2.1.323"
DEFAULT_ROOT = "/work"
DEFAULT_WINDOW = 200_000
DROP_RATIO = 0.7  # a call whose context is below 70% of the one before it ...
DROP_MIN = 20_000  # ... and at least this many tokens smaller is flagged as a drop
SKILL_PREFIX = "Base directory for this skill:"
OUTPUT_NAME = "context-telemetry.json"


# --- Context ---------------------------------------------------------------------------------------------------


def context_size(usage: dict) -> int:
    """The context one API call sent: uncached input plus cache read plus cache write tokens."""
    return sum(int(usage.get(k) or 0) for k in ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"))


def context_drops(contexts: list[int]) -> list[dict]:
    return [{"from": a, "to": b} for a, b in zip(contexts, contexts[1:]) if b < DROP_RATIO * a and a - b >= DROP_MIN]


# --- Paths ------------------------------------------------------------------------------------------------------

TEST_DIRS = {"tests", "test", "__tests__", "spec"}


def classify_path(rel: str) -> str:
    """docs (*.md), tests (by directory or file name), or code (everything else) for a repository-relative path."""
    p = rel.lower()
    name = p.rsplit("/", 1)[-1]
    if name.endswith((".md", ".markdown")):
        return "docs"
    if any(part in TEST_DIRS for part in p.split("/")[:-1]):
        return "tests"
    if (name.startswith("test_") or name in ("conftest.py", "tests.py", "test.py")
            or re.search(r"_test\.\w+$", name) or re.search(r"\.(test|spec)\.\w+$", name)):
        return "tests"
    return "code"


def repo_rel(path: str, root: str) -> str | None:
    """The path relative to the repository root, or None if it lies outside it."""
    path = posixpath.normpath(path)
    root = root.rstrip("/")
    if path.startswith(root + "/"):
        return path[len(root) + 1:]
    return None


def classify_target(path: str, root: str) -> str:
    """The class of a file an agent read: a repository class, plugin, harness (persisted output, task files), or other."""
    rel = repo_rel(path, root)
    if rel is not None:
        return classify_path(rel)
    if "/tool-results/" in path or path.startswith(("/tmp/", "/cfg/projects/")):
        return "harness"
    if path.startswith("/cfg/"):
        return "plugin"
    return "other"


GLOB_CHARS = set("*?[")


def expand_pattern(path: str, root: str, files: set[str]) -> list[str]:
    """Repository-relative files a read argument names: itself, or the listed files a glob matches segment by segment."""
    rel = repo_rel(path, root)
    if rel is None:
        return []
    if not GLOB_CHARS & set(rel):
        return [rel]
    parts = rel.split("/")
    return sorted(f for f in files if len(f.split("/")) == len(parts)
                  and all(fnmatch.fnmatchcase(a, b) for a, b in zip(f.split("/"), parts)))


# --- Bash -------------------------------------------------------------------------------------------------------


@dataclass
class BashParse:
    reads: list = field(default_factory=list)  # (absolute path or glob, "full" | "partial")
    searches: int = 0
    lists: int = 0
    unresolved: int = 0  # read arguments that could not be resolved to a path ($vars, substitutions)
    read_segments: int = 0
    cwd: str = DEFAULT_ROOT  # the cwd the next Bash call starts in


HEREDOC = re.compile(r"(?<!<)<<(?!<)(-?)\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\2")
FOR_LOOP = re.compile(r"\bfor\s+([A-Za-z_]\w*)\s+in\s+([^;]*?)\s*;\s*do\s(.*?);?\s*\bdone\b", re.S)
PUNCT = set("();<>|&")
KEYWORDS = {"if", "then", "else", "elif", "do", "while", "until", "!", "time", "sudo", "exec", "command", "nohup",
            "{", "}", "fi", "done", "esac", "env"}
FULL_READERS = {"cat", "nl", "less", "more", "bat", "tac"}
PART_READERS = {"head", "tail"}
SEARCHERS = {"grep", "egrep", "fgrep", "rg", "ag", "ack", "zgrep"}
LISTERS = {"ls", "find", "tree", "fd", "du", "wc", "stat"}
GREP_VALUE_OPTS = {"-e", "-f", "-m", "-A", "-B", "-C", "-g", "-t", "-T", "-M", "-d", "-D", "--include", "--exclude",
                   "--glob", "--type", "--max-count", "--context", "--after-context", "--before-context", "--regexp"}
SUBST = "\x00SUBST\x00"


def strip_heredocs(cmd: str) -> str:
    out, pending = [], []
    for line in cmd.split("\n"):
        if pending:
            if line.strip() == pending[0]:
                pending.pop(0)
            continue
        out.append(line)
        pending.extend(m.group(3) for m in HEREDOC.finditer(line))
    return "\n".join(out)


def extract_substitutions(cmd: str) -> tuple[str, list[str]]:
    """Replace each $( ... ) and `...` with a placeholder; return the outer text and the inner commands."""
    inner, out, i = [], [], 0
    while i < len(cmd):
        if cmd.startswith("$(", i):
            depth, j = 1, i + 2
            while j < len(cmd) and depth:
                depth += {"(": 1, ")": -1}.get(cmd[j], 0)
                j += 1
            inner.append(cmd[i + 2:j - 1] if depth == 0 else cmd[i + 2:])
            out.append(SUBST)
            i = j
        elif cmd[i] == "`":
            j = cmd.find("`", i + 1)
            if j < 0:
                out.append(cmd[i:])
                break
            inner.append(cmd[i + 1:j])
            out.append(SUBST)
            i = j + 1
        else:
            out.append(cmd[i])
            i += 1
    return "".join(out), inner


def expand_for_loops(cmd: str) -> str:
    def repl(m):
        var, items, body = m.group(1), m.group(2), m.group(3)
        if SUBST in items or "$" in items:
            return m.group(0)
        try:
            words = shlex.split(items)
        except ValueError:
            return m.group(0)
        pat = re.compile(r"\$\{" + var + r"\}|\$" + var + r"\b")
        return " ; ".join(pat.sub(lambda _: w, body) for w in words)
    for _ in range(5):
        new = FOR_LOOP.sub(repl, cmd)
        if new == cmd:
            break
        cmd = new
    return cmd


def expand_braces(word: str) -> list[str]:
    m = re.search(r"\{([^{}]*,[^{}]*)\}", word)
    if not m:
        return [word]
    out = []
    for alt in m.group(1).split(","):
        out.extend(expand_braces(word[:m.start()] + alt + word[m.end():]))
    return out[:200]


def tokenize(cmd: str) -> list[str]:
    lex = shlex.shlex(cmd, posix=True, punctuation_chars=True)
    lex.whitespace_split = True
    lex.commenters = ""
    try:
        return list(lex)
    except ValueError:  # an unbalanced quote: fall back to a plain split
        return [t.strip("'\"") for t in re.findall(r"[;&|()<>]+|[^\s;&|()<>]+", cmd)]


def segments(tokens: list[str]) -> list[dict]:
    """Split tokens into simple commands, dropping redirections and noting pipes and input files."""
    segs, cur = [], {"words": [], "piped_in": False, "piped_out": False, "inputs": [], "heredoc": False}
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok and set(tok) <= PUNCT:
            if "<" in tok or ">" in tok:
                if cur["words"] and cur["words"][-1].isdigit() and len(cur["words"]) > 1:
                    cur["words"].pop()  # a file descriptor: the 2 of 2>&1
                target = tokens[i + 1] if i + 1 < len(tokens) and not set(tokens[i + 1]) <= PUNCT else None
                if tok in ("<<", "<<-"):
                    cur["heredoc"] = True
                elif tok == "<" and target:
                    cur["inputs"].append(target)
                i += 2 if target is not None else 1
                continue
            pipe = "|" in tok and "||" not in tok
            cur["piped_out"] = pipe
            segs.append(cur)
            cur = {"words": [], "piped_in": pipe, "piped_out": False, "inputs": [], "heredoc": False}
            i += 1
            continue
        cur["words"].append(tok)
        i += 1
    segs.append(cur)
    return [s for s in segs if s["words"] or s["inputs"]]


def _resolve(cwd: str, arg: str) -> str:
    return posixpath.normpath(arg if arg.startswith("/") else posixpath.join(cwd, arg))


def _head_tail_files(args: list[str]) -> list[str]:
    files, i = [], 0
    while i < len(args):
        a = args[i]
        if a in ("-n", "-c", "--lines", "--bytes"):
            i += 2
            continue
        if a.startswith("-") and a != "-" or a.startswith("+"):
            i += 1
            continue
        files.append(a)
        i += 1
    return files


def _sed_files(args: list[str]) -> tuple[bool, list[str]]:
    """(quiet and not in place, file arguments) for a sed invocation."""
    quiet = in_place = False
    script_given = False
    rest, i = [], 0
    while i < len(args):
        a = args[i]
        if a in ("-e", "-f", "--expression", "--file"):
            script_given = True
            i += 2
            continue
        if a.startswith("--"):
            quiet |= a in ("--quiet", "--silent")
            in_place |= a.startswith("--in-place")
        elif a.startswith("-") and len(a) > 1:
            quiet |= "n" in a[1:]
            in_place |= "i" in a[1:]
        else:
            rest.append(a)
        i += 1
    files = rest if script_given else rest[1:]
    return quiet and not in_place, files


def _grep_files(args: list[str]) -> list[str]:
    pattern_given = False
    rest, i = [], 0
    while i < len(args):
        a = args[i]
        if a in GREP_VALUE_OPTS:
            pattern_given |= a in ("-e", "-f", "--regexp")
            i += 2
            continue
        if a.startswith("-") and len(a) > 1:
            i += 1
            continue
        rest.append(a)
        i += 1
    return rest if pattern_given else rest[1:]


def bash_reads(command: str, cwd: str = DEFAULT_ROOT, root: str = DEFAULT_ROOT) -> BashParse:
    """The file reads, searches and listings in one Bash command, starting from cwd."""
    out = BashParse(cwd=cwd)
    text = strip_heredocs(command)
    text = re.sub(r"\\\n", " ", text)
    text = "\n".join(line for line in text.split("\n") if not line.lstrip().startswith("#"))
    text, inner = extract_substitutions(text)
    text = expand_for_loops(text.replace("\n", " ; "))
    for sub in inner:  # commands inside substitutions run too; they count, but cannot change our cwd
        b = bash_reads(sub, cwd=cwd, root=root)
        out.reads += b.reads
        out.searches += b.searches
        out.lists += b.lists
        out.unresolved += b.unresolved
        out.read_segments += b.read_segments
    cur = cwd
    for seg in segments(tokenize(text)):
        words = list(seg["words"])
        for k, w in enumerate(words):
            if w.startswith("#"):
                words = words[:k]
                break
        while words and (words[0] in KEYWORDS or re.match(r"^[A-Za-z_]\w*=", words[0])):
            words.pop(0)
        if not words or words[0] in ("for", "case", "select", "function"):
            continue
        from_stdin = False
        if posixpath.basename(words[0]) == "xargs":
            words.pop(0)
            while words and words[0].startswith("-"):
                words.pop(0)
            from_stdin = True
            if not words:
                continue
        verb, args = posixpath.basename(words[0]), words[1:]
        if verb == "cd":
            target = args[0] if args else root
            if not ({"$", "~"} & set(target) or SUBST in target or target == "-"):
                cur = _resolve(cur, target)
            continue
        if verb == "git":
            sub = next((a for a in args if not a.startswith("-")), "")
            if sub == "grep":
                out.searches += 1
            elif sub in ("ls-files", "ls-tree"):
                out.lists += 1
            continue
        files = None
        mode = "partial"
        if verb in FULL_READERS:
            files = [a for a in args if not (a.startswith("-") and a != "-")]
            mode = "partial" if seg["piped_out"] else "full"
        elif verb in PART_READERS:
            files = _head_tail_files(args)
        elif verb == "sed":
            quiet, f = _sed_files(args)
            files = f if quiet else None
        elif verb in SEARCHERS:
            if seg["piped_in"] and not _grep_files(args) and not from_stdin:
                continue  # filtering another command's output
            out.searches += 1
            continue
        elif verb in LISTERS:
            if seg["piped_in"] and not [a for a in args if not a.startswith("-")]:
                continue  # | wc -l
            out.lists += 1
            continue
        if files is None:
            continue
        files = [f for f in files if f != "-"] + seg["inputs"]
        if not files and not from_stdin:
            continue  # reading stdin: a pipe or a heredoc
        out.read_segments += 1
        if from_stdin and not files:
            out.unresolved += 1
        for f in files:
            if {"$", "~", "`"} & set(f) or SUBST in f:
                out.unresolved += 1
                continue
            for g in expand_braces(f):
                out.reads.append((_resolve(cur, g), mode))
    out.cwd = cur if cur == root or repo_rel(cur, root) is not None else root
    return out


# --- Streams ----------------------------------------------------------------------------------------------------


def _events(source):
    if isinstance(source, (str, Path)):
        with open(source, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line.startswith("{"):
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue
    else:
        yield from source


def _text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")
    return ""


NUMBERED = re.compile(r"^\s*(\d+)[\t→](.*)$")
PERSISTED = re.compile(r"saved to: (\S+)")


def new_turn(root: str) -> dict:
    return {
        "root": root, "api_calls": 0, "contexts": [], "subagent_api_calls": 0, "subagent_contexts": [], "subagents": set(),
        "compactions": [], "context_edits": 0, "reported_context_window": None, "tool_calls": Counter(),
        "read_calls": 0, "read_errors": 0, "read_chars": 0, "read_chars_by_class": Counter(), "read_files": set(),
        "read_lines": {}, "grep_calls": 0, "glob_calls": 0,
        "bash_calls": 0, "bash_read_calls": 0, "bash_search_calls": 0, "bash_list_calls": 0, "bash_read_chars": 0,
        "bash_read_chars_by_class": Counter(), "bash_read_chars_split": 0, "bash_reads": [], "bash_unresolved": 0,
        "bash_persisted": 0,
        "bash_persisted_bytes": 0, "skill_calls": 0, "skill_chars": 0,
    }


def parse_stream(source, root: str | None = None) -> dict:
    """One turn's measurements from its stream-json transcript (a path or an iterable of events)."""
    t = new_turn(root or DEFAULT_ROOT)
    seen: dict = {}  # thread -> message ids already counted
    cwd: dict = {}  # thread -> Bash cwd
    pending: dict = {}  # tool_use id -> (name, payload)
    for e in _events(source):
        typ = e.get("type")
        if typ == "system":
            sub = e.get("subtype") or ""
            if sub == "init" and e.get("cwd") and root is None:
                t["root"] = e["cwd"]
            if "compact" in sub:
                meta = e.get("compact_metadata") or {}
                t["compactions"].append({"subtype": sub, "trigger": meta.get("trigger"), "pre_tokens": meta.get("pre_tokens")})
        elif typ == "result":
            for mu in (e.get("modelUsage") or {}).values():
                w = mu.get("contextWindow")
                if w:
                    t["reported_context_window"] = max(t["reported_context_window"] or 0, w)
        elif typ == "assistant":
            msg = e.get("message") or {}
            thread = e.get("parent_tool_use_id")
            mid = msg.get("id") or e.get("uuid")
            ids = seen.setdefault(thread, set())
            if mid not in ids:
                ids.add(mid)
                size = context_size(msg.get("usage") or {})
                if thread is None:
                    t["api_calls"] += 1
                    t["contexts"].append(size)
                else:
                    t["subagent_api_calls"] += 1
                    t["subagent_contexts"].append(size)
                    t["subagents"].add(e.get("agent_id") or thread)
                if msg.get("context_management"):
                    t["context_edits"] += 1
            for b in msg.get("content") or []:
                if not isinstance(b, dict) or b.get("type") != "tool_use" or b.get("id") in pending:
                    continue
                name, inp = b.get("name"), b.get("input") or {}
                t["tool_calls"][name] += 1
                if name == "Read":
                    t["read_calls"] += 1
                    pending[b["id"]] = ("Read", inp)
                elif name == "Grep":
                    t["grep_calls"] += 1
                elif name == "Glob":
                    t["glob_calls"] += 1
                elif name == "Skill":
                    t["skill_calls"] += 1
                elif name == "Bash":
                    bp = bash_reads(inp.get("command") or "", cwd=cwd.get(thread, t["root"]), root=t["root"])
                    cwd[thread] = bp.cwd
                    t["bash_calls"] += 1
                    t["bash_search_calls"] += bp.searches > 0
                    t["bash_list_calls"] += bp.lists > 0
                    t["bash_unresolved"] += bp.unresolved
                    reads = [{"path": p, "mode": m, "persisted": None} for p, m in bp.reads]
                    if bp.read_segments:
                        t["bash_read_calls"] += 1
                        t["bash_reads"].extend(reads)
                    pending[b["id"]] = ("Bash", (bp, reads))
        elif typ == "user":
            content = (e.get("message") or {}).get("content")
            if not isinstance(content, list):
                continue
            results = [b for b in content if isinstance(b, dict) and b.get("type") == "tool_result"]
            extra = e.get("tool_use_result") if len(results) == 1 else None
            for b in content:
                if not isinstance(b, dict):
                    continue
                if b.get("type") == "text" and b.get("text", "").startswith(SKILL_PREFIX):
                    t["skill_chars"] += len(b["text"])
                if b.get("type") != "tool_result" or b.get("tool_use_id") not in pending:
                    continue
                name, payload = pending.pop(b["tool_use_id"])
                text = _text(b.get("content"))
                if name == "Read":
                    _read_result(t, payload, text, extra, bool(b.get("is_error")))
                elif name == "Bash":
                    _bash_result(t, payload, text, extra)
    c = t["contexts"]
    t["peak_context"] = max(c, default=0)
    t["first_context"] = c[0] if c else None
    t["subagent_peak_context"] = max(t["subagent_contexts"], default=0)
    t["context_drops"] = context_drops(c)
    return t


def _read_result(t: dict, inp: dict, text: str, extra, is_error: bool) -> None:
    f = extra.get("file") if isinstance(extra, dict) and isinstance(extra.get("file"), dict) else None
    path = posixpath.normpath((f or {}).get("filePath") or inp.get("file_path") or "?")
    t["read_chars"] += len(text)
    t["read_chars_by_class"][classify_target(path, t["root"])] += len(text)
    if is_error or text.startswith("<tool_use_error>"):
        t["read_errors"] += 1
        return
    t["read_files"].add(path)
    lines = t["read_lines"].setdefault(path, {})
    if f is not None and isinstance(f.get("content"), str):
        start = int(f.get("startLine") or 1)
        for k, line in enumerate(f["content"].split("\n")):
            lines[start + k] = max(lines.get(start + k, 0), len(line.encode()) + 1)
    else:
        for line in text.split("\n"):
            m = NUMBERED.match(line)
            if m:
                n = int(m.group(1))
                lines[n] = max(lines.get(n, 0), len(m.group(2).encode()) + 1)


def _bash_result(t: dict, payload, text: str, extra) -> None:
    bp, reads = payload
    persisted = None
    if isinstance(extra, dict) and extra.get("persistedOutputPath"):
        persisted = extra["persistedOutputPath"]
        t["bash_persisted_bytes"] += int(extra.get("persistedOutputSize") or 0)
    elif "<persisted-output>" in text:
        m = PERSISTED.search(text)
        persisted = m.group(1) if m else "?"
    if persisted:
        t["bash_persisted"] += 1
        for r in reads:
            r["persisted"] = persisted
    if not bp.read_segments:
        return
    t["bash_read_chars"] += len(text)
    targets = [classify_target(p, t["root"]) for p, _ in bp.reads] + ["unresolved"] * bp.unresolved
    if len(set(targets)) > 1:  # split evenly across the files named, remainder to the first
        t["bash_read_chars_split"] += len(text)
    base, extra_chars = divmod(len(text), len(targets) or 1)
    for k, cls in enumerate(targets or ["unresolved"]):
        t["bash_read_chars_by_class"][cls] += base + (k < extra_chars)


def turn_summary(t: dict) -> dict:
    c = t["contexts"]
    return {
        "api_calls": t["api_calls"], "peak_context": max(c, default=0), "first_context": c[0] if c else None,
        "last_context": c[-1] if c else None, "subagent_api_calls": t["subagent_api_calls"],
        "subagent_peak_context": max(t["subagent_contexts"], default=0), "compactions": t["compactions"],
        "context_edits": t["context_edits"], "context_drops": context_drops(c), "read_calls": t["read_calls"],
        "read_chars": t["read_chars"], "bash_calls": t["bash_calls"], "bash_read_calls": t["bash_read_calls"],
        "bash_read_chars": t["bash_read_chars"], "skill_calls": t["skill_calls"],
    }


# --- Repository -------------------------------------------------------------------------------------------------


class RepoUnavailable(RuntimeError):
    pass


def parse_ls_tree(text: str) -> list[tuple[str, int]]:
    """(path, size) for each blob in `git ls-tree -r -l` output; submodules (size '-') are skipped."""
    out = []
    for line in text.splitlines():
        meta, sep, path = line.partition("\t")
        parts = meta.split()
        if not sep or len(parts) < 4 or parts[1] != "blob" or not parts[3].isdigit():
            continue
        if len(path) > 1 and path[0] == path[-1] == '"':
            path = path[1:-1].encode("latin-1", "backslashreplace").decode("unicode_escape").encode("latin-1").decode("utf-8", "replace")
        out.append((path, int(parts[3])))
    return out


def repo_size(entries: list[tuple[str, int]]) -> dict:
    r = {"files": len(entries), "bytes": 0, "tests": 0, "code": 0, "docs": 0}
    for path, size in entries:
        r[classify_path(path)] += size
        r["bytes"] += size
    r["tokens_est"] = round(r["bytes"] / 4)
    return r


def fetch_listings(volume: str, commits, image: str = DEFAULT_IMAGE, run=subprocess.run) -> dict[str, str]:
    """`git ls-tree -r -l` for each commit in the workspace volume, in one container. Raises RepoUnavailable."""
    commits = list(dict.fromkeys(c for c in commits if c))
    probe = run(["docker", "volume", "inspect", volume], capture_output=True, text=True)
    if probe.returncode != 0:  # docker run would silently create an empty volume
        raise RepoUnavailable(f"no volume {volume}")
    script = ("cd /w && git config --global --add safe.directory /w && for c in " + " ".join(shlex.quote(c) for c in commits)
              + '; do echo "@@@ $c"; git ls-tree -r -l "$c" || echo "@@@ERROR $c"; done')
    cmd = ["docker", "run", "--rm", "--entrypoint", "sh", "-v", f"{volume}:/w:ro", image, "-c", script]
    p = run(cmd, capture_output=True, text=True, timeout=600)
    if p.returncode != 0:
        raise RepoUnavailable(f"docker run failed for {volume}: {(p.stderr or '').strip()[:300]}")
    out: dict[str, list[str]] = {}
    failed, cur = set(), None
    for line in p.stdout.splitlines():
        if line.startswith("@@@ERROR "):
            failed.add(line[9:].strip())
        elif line.startswith("@@@ "):
            cur = line[4:].strip()
            out[cur] = []
        elif cur is not None:
            out[cur].append(line)
    return {c: "".join(x + "\n" for x in lines) for c, lines in out.items() if c not in failed}


# --- Rollup -----------------------------------------------------------------------------------------------------

REPO_CLASSES = ("docs", "tests", "code")


def _share(a, b):
    return a / b if b else None


def rollup_change(turns: list[dict], entries, window: int, root: str | None = None) -> dict:
    """One change's measurements from its turns, with coverage when the repository listing is given."""
    root = root or (turns[0]["root"] if turns else DEFAULT_ROOT)
    contexts = [c for t in turns for c in t["contexts"]]
    peak = max(contexts, default=0)
    peak_turn = next((i for i, t in enumerate(turns) if peak and peak in t["contexts"]), None)
    read_files = set().union(*(t["read_files"] for t in turns)) if turns else set()
    read_lines: dict[str, dict[int, int]] = {}
    for t in turns:
        for p, lines in t["read_lines"].items():
            d = read_lines.setdefault(p, {})
            for n, b in lines.items():
                d[n] = max(d.get(n, 0), b)
    bash_reads = [r for t in turns for r in t["bash_reads"]]
    compactions = [dict(c, turn=i) for i, t in enumerate(turns) for c in t["compactions"]]
    sums = lambda k: sum(t[k] for t in turns)  # noqa: E731
    counters = lambda k: dict(sum((t[k] for t in turns), Counter()))  # noqa: E731
    windows = [t["reported_context_window"] for t in turns if t["reported_context_window"]]
    read_repo = sorted({rel for p in read_files if (rel := repo_rel(p, root)) is not None})
    out = {
        "turns": [turn_summary(t) for t in turns],
        "api_calls": sums("api_calls"), "peak_context": peak, "peak_turn": peak_turn, "peak_share": peak / window,
        "first_context": contexts[0] if contexts else None,
        "reported_context_window": max(windows) if windows else None,
        "subagents": len(set().union(*(t["subagents"] for t in turns))) if turns else 0,
        "subagent_api_calls": sums("subagent_api_calls"),
        "subagent_peak_context": max((c for t in turns for c in t["subagent_contexts"]), default=0),
        "compactions": len(compactions), "compaction_events": compactions, "context_edits": sums("context_edits"),
        "context_drops": context_drops(contexts),
        "tool_calls": counters("tool_calls"),
        "read_calls": sums("read_calls"), "read_errors": sums("read_errors"), "read_unique_files": len(read_files),
        "read_unique_repo_files": len(read_repo), "read_chars": sums("read_chars"),
        "read_chars_by_class": counters("read_chars_by_class"),
        "grep_calls": sums("grep_calls"), "glob_calls": sums("glob_calls"),
        "bash_calls": sums("bash_calls"), "bash_read_calls": sums("bash_read_calls"),
        "bash_search_calls": sums("bash_search_calls"), "bash_list_calls": sums("bash_list_calls"),
        "bash_read_chars": sums("bash_read_chars"), "bash_read_chars_by_class": counters("bash_read_chars_by_class"),
        "bash_read_chars_split": sums("bash_read_chars_split"),
        "bash_unresolved_args": sums("bash_unresolved"), "bash_persisted": sums("bash_persisted"),
        "bash_persisted_bytes": sums("bash_persisted_bytes"),
        "skill_calls": sums("skill_calls"), "skill_chars": sums("skill_chars"),
        "read_files": read_repo + sorted(p for p in read_files if repo_rel(p, root) is None),
    }
    reading = Counter(out["read_chars_by_class"]) + Counter(out["bash_read_chars_by_class"])
    reading["skill"] += out["skill_chars"]
    out["reading_chars_by_class"] = dict(reading)
    repo_reading = sum(reading[k] for k in REPO_CLASSES)
    out["reading_docs_share"] = _share(reading["docs"], repo_reading)
    out["method_chars"] = reading["skill"] + reading.get("plugin", 0)  # the method's own text: skill bodies and plugin files
    out["reading_tokens_est"] = round((out["read_chars"] + out["bash_read_chars"] + out["skill_chars"]) / 4)

    sizes = dict(entries) if entries is not None else {}
    listed = set(sizes)
    bash_files: dict[str, str] = {}  # rel path -> best mode credited
    any_files = set(read_repo)
    for r in bash_reads:
        for rel in expand_pattern(r["path"], root, listed):
            any_files.add(rel)
            seen_whole = r["mode"] == "full" and (r["persisted"] is None or r["persisted"] in read_files)
            if seen_whole or rel not in bash_files:
                bash_files[rel] = "full" if seen_whole else bash_files.get(rel, "partial")
    out["files_read_any"] = len(any_files)
    out["bash_read_files"] = sorted(bash_files)
    if entries is None:
        out["repo"] = None
        out["coverage"] = None
        return out
    repo = repo_size(entries)
    repo["window_share"] = repo["tokens_est"] / window
    out["repo"] = repo
    read_cov = {}
    for p, lines in read_lines.items():
        rel = repo_rel(p, root)
        if rel in sizes:
            read_cov[rel] = min(sum(lines.values()), sizes[rel])
    est = dict(read_cov)
    for rel, mode in bash_files.items():
        if mode == "full" and rel in sizes:
            est[rel] = sizes[rel]
    touched = {rel for rel in any_files if rel in sizes}
    est_by_class = Counter()
    for rel, b in est.items():
        est_by_class[classify_path(rel)] += b
    read_repo_chars = sum(out["read_chars_by_class"].get(k, 0) for k in REPO_CLASSES)
    out["coverage"] = {
        "read_tool_bytes": sum(read_cov.values()), "read_tool_share": _share(sum(read_cov.values()), repo["bytes"]),
        "read_tool_gross_share": _share(read_repo_chars, repo["bytes"]),
        "est_bytes": sum(est.values()), "est_share": _share(sum(est.values()), repo["bytes"]),
        "est_share_by_class": {k: _share(est_by_class[k], repo[k]) for k in REPO_CLASSES},
        "touched_bytes": sum(sizes[r] for r in touched), "touched_share": _share(sum(sizes[r] for r in touched), repo["bytes"]),
        "touched_files": len(touched),
        "reading_volume_share": _share(repo_reading, repo["bytes"]),
    }
    return out


# --- Trajectories -----------------------------------------------------------------------------------------------


def _turn_paths(cdir: Path) -> list[Path]:
    cj = cdir / "change.json"
    if cj.exists():
        names = [t.get("stream") for t in json.loads(cj.read_text()).get("turns", []) if t.get("stream")]
        paths = [cdir / n for n in names if (cdir / n).exists()]
        if paths:
            return paths
    return sorted(cdir.glob("turn-*.stream.jsonl"))


def trajectory_telemetry(run: Path, window: int = DEFAULT_WINDOW, fetch=fetch_listings, image: str | None = None,
                         log=lambda msg: print(msg, file=sys.stderr)) -> dict:
    """Every change of one trajectory. fetch(volume, commits, image) lists the repository; None skips it."""
    run = Path(run)
    tj = json.loads((run / "trajectory.json").read_text())
    changes = sorted(((int(k), v) for k, v in tj.get("changes", {}).items()), key=lambda kv: kv[0])
    before, prev = {}, tj.get("start_commit")
    for n, ch in changes:
        before[n] = prev
        prev = ch.get("commit") or prev
    listings: dict[str, str] = {}
    volume = (tj.get("volumes") or {}).get("workspace")
    repo_note = "skipped (--no-repo)" if fetch is None else None
    if fetch is not None:
        if not volume:
            repo_note = "no workspace volume recorded"
        else:
            commits = [c for n, ch in changes for c in (ch.get("commit"), before[n]) if c]
            try:
                listings = fetch(volume, commits, image or tj.get("image") or DEFAULT_IMAGE)
                repo_note = f"listed {len(listings)} commits from {volume}"
            except (RepoUnavailable, OSError, subprocess.SubprocessError) as exc:
                repo_note = f"unavailable: {exc}"
                log(f"{tj.get('id', run.name)}: repository {repo_note}")
    out_changes, skipped = [], []
    for n, ch in changes:
        cdir = run / f"change-{n:02d}"
        paths = _turn_paths(cdir) if cdir.is_dir() else []
        if not paths:
            skipped.append({"change": n, "title": ch.get("title"),
                            "reason": ch.get("symptom") or ch.get("error") or "no transcripts"})
            continue
        turns = [parse_stream(p) for p in paths]
        commit = ch.get("commit")
        entries = parse_ls_tree(listings[commit]) if commit in listings else None
        c = rollup_change(turns, entries, window, turns[0]["root"])
        start = before[n]
        c = {"change": n, "title": ch.get("title"), "commit": commit, "start_commit": start, **c,
             "repo_start": repo_size(parse_ls_tree(listings[start])) if start in listings else None}
        for i, (t, p) in enumerate(zip(c["turns"], paths)):
            t["stream"] = p.name
        out_changes.append(c)
    windows = [c["reported_context_window"] for c in out_changes if c["reported_context_window"]]
    return {
        "id": tj.get("id", run.name), "arm": tj.get("arm"), "seed": tj.get("seed"), "model": tj.get("model"),
        "claude_code": tj.get("claude_code"), "window": window,
        "reported_context_window": max(windows) if windows else None, "repo": repo_note,
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "changes": out_changes, "skipped": skipped,
    }


# --- Summary ----------------------------------------------------------------------------------------------------


def _mean(xs):
    xs = [x for x in xs if x is not None]
    return st.mean(xs) if xs else None


def trajectory_row(t: dict) -> dict:
    cs = t["changes"]
    cov = lambda k: [(c.get("coverage") or {}).get(k) for c in cs]  # noqa: E731
    c10 = next((c for c in cs if c["change"] == 10 and c.get("repo")), None)
    c10 = c10 or next((c for c in reversed(cs) if c.get("repo")), None)
    window = t.get("window") or DEFAULT_WINDOW
    peaks = [c["peak_context"] for c in cs]
    return {
        "id": t["id"], "arm": t.get("arm"), "changes": len(cs),
        "peak_context_mean": _mean(peaks), "peak_context_max": max(peaks, default=None),
        "peak_share_mean": _mean([p / window for p in peaks]), "peak_share_max": max(peaks, default=0) / window,
        "compactions": sum(c.get("compactions", 0) for c in cs),
        "read_files_mean": _mean([c.get("read_unique_repo_files") for c in cs]),
        "files_any_mean": _mean([c.get("files_read_any") for c in cs]),
        "bash_read_calls_mean": _mean([c.get("bash_read_calls") for c in cs]),
        "read_tool_share_mean": _mean(cov("read_tool_share")), "est_share_mean": _mean(cov("est_share")),
        "touched_share_mean": _mean(cov("touched_share")),
        "reading_docs_share_mean": _mean([c.get("reading_docs_share") for c in cs]),
        "method_chars_mean": _mean([c.get("method_chars") for c in cs]),
        "repo_change": c10["change"] if c10 else None,
        **{f"repo_{k}_c10": (c10["repo"][k] if c10 else None) for k in ("bytes", "tokens_est", "tests", "code", "docs")},
    }


def summarize(trajectories: list[dict]) -> dict:
    """Per-arm means over trajectories of each trajectory's per-change means (and of its max peak)."""
    rows = [trajectory_row(t) for t in trajectories]
    arms: dict[str, list[dict]] = {}
    for r in rows:
        arms.setdefault(r["arm"], []).append(r)
    out = {}
    for arm, rs in arms.items():
        keys = [k for k in rs[0] if k not in ("id", "arm", "repo_change")]
        m = {k: _mean([r[k] for r in rs]) for k in keys}
        m["peak_context_max"] = _mean([r["peak_context_max"] for r in rs])
        m["n"] = len(rs)
        m["ids"] = [r["id"] for r in rs]
        out[arm] = m
    return out


# --- Printing ---------------------------------------------------------------------------------------------------


def _k(n):
    return "-" if n is None else (f"{n / 1000:.1f}k" if n >= 1000 else str(round(n)))


def _pct(x):
    return "-" if x is None else f"{100 * x:.1f}%"


def _kb(n):
    return "-" if n is None else f"{n / 1024:.0f}"


def format_trajectory(t: dict) -> str:
    head = (f"{t['id']}  arm={t['arm']}  window={t['window']:,} (session reports {t['reported_context_window'] or '?':,})"
            if isinstance(t["reported_context_window"], int) else f"{t['id']}  arm={t['arm']}  window={t['window']:,}")
    cols = ("ch", "turns", "calls", "peak", "%win", "base", "cmpct", "Read", "files", "readKB", "Bash", "bRead", "bGrep",
            "bReadKB", "pers", "anyFiles", "repoKB t/c/d", "Read%", "est%", "touch%", "docs%rd", "methodKB")
    rows = []
    for c in t["changes"]:
        r, cov = c.get("repo"), c.get("coverage") or {}
        repo = f"{_kb(r['bytes'])} {_kb(r['tests'])}/{_kb(r['code'])}/{_kb(r['docs'])}" if r else "-"
        rows.append((c["change"], len(c["turns"]), c["api_calls"], _k(c["peak_context"]), _pct(c["peak_share"]),
                     _k(c["first_context"]), c["compactions"], c["read_calls"], c["read_unique_repo_files"],
                     _kb(c["read_chars"]), c["bash_calls"], c["bash_read_calls"], c["bash_search_calls"],
                     _kb(c["bash_read_chars"]), c["bash_persisted"], c["files_read_any"], repo,
                     _pct(cov.get("read_tool_share")), _pct(cov.get("est_share")), _pct(cov.get("touched_share")),
                     _pct(c.get("reading_docs_share")), _kb(c.get("method_chars"))))
    lines = [head, _table(cols, rows)]
    if t["skipped"]:
        lines.append("not run: " + "; ".join(f"{s['change']} ({s['reason']})" for s in t["skipped"]))
    lines.append(f"repository: {t['repo']}")
    return "\n".join(lines)


def format_summary(summary: dict, window: int) -> str:
    cols = ("arm", "n", "peak mean", "peak max", "%win mean", "%win max", "compactions", "Read files/chg",
            "any files/chg", "bash reads/chg", "Read%", "est%", "touch%", "docs%rd", "methodKB/chg", "repo@c10 KB",
            "tok", "t/c/d KB")
    rows = []
    for arm, m in summary.items():
        rows.append((arm, m["n"], _k(m["peak_context_mean"]), _k(m["peak_context_max"]), _pct(m["peak_share_mean"]),
                     _pct(m["peak_context_max"] / window if m["peak_context_max"] is not None else None),
                     f"{m['compactions']:.1f}", f"{m['read_files_mean']:.1f}", f"{m['files_any_mean']:.1f}",
                     f"{m['bash_read_calls_mean']:.1f}", _pct(m["read_tool_share_mean"]), _pct(m["est_share_mean"]),
                     _pct(m["touched_share_mean"]), _pct(m["reading_docs_share_mean"]), _kb(m["method_chars_mean"]),
                     _kb(m["repo_bytes_c10"]),
                     _k(m["repo_tokens_est_c10"]),
                     f"{_kb(m['repo_tests_c10'])}/{_kb(m['repo_code_c10'])}/{_kb(m['repo_docs_c10'])}"))
    return _table(cols, rows)


def _table(cols, rows) -> str:
    rows = [tuple(str(x) for x in r) for r in rows]
    widths = [max(len(c), *(len(r[i]) for r in rows)) if rows else len(c) for i, c in enumerate(cols)]
    fmt = lambda r: "  ".join(x.rjust(w) for x, w in zip(r, widths))  # noqa: E731
    return "\n".join([fmt(cols), fmt(["-" * w for w in widths])] + [fmt(r) for r in rows])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ids", nargs="+", required=True, help="trajectory ids under the runs folder")
    ap.add_argument("--window", type=int, default=DEFAULT_WINDOW, help="context window for shares (default %(default)s)")
    ap.add_argument("--no-repo", action="store_true", help="skip listing the repository in the workspace volumes")
    ap.add_argument("--summary", action="store_true", help="print per-arm means across the trajectories")
    ap.add_argument("--runs", type=Path, default=RUNS)
    ap.add_argument("--image", help="executor image (default: the trajectory's own)")
    args = ap.parse_args(argv)
    done = []
    for tid in args.ids:
        run = args.runs / tid
        if not (run / "trajectory.json").exists():
            print(f"{tid}: no trajectory.json under {args.runs}", file=sys.stderr)
            return 2
        t = trajectory_telemetry(run, args.window, fetch=None if args.no_repo else fetch_listings, image=args.image)
        (run / OUTPUT_NAME).write_text(json.dumps(t, indent=1) + "\n")
        print(format_trajectory(t))
        print()
        done.append(t)
    if args.summary:
        print(f"Per-arm means (window {args.window:,}; peak = per-change peak, averaged over changes then trajectories; "
              "peak max = each trajectory's largest change, averaged)")
        print(format_summary(summarize(done), args.window))
    return 0


if __name__ == "__main__":
    sys.exit(main())
