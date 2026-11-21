"""LID's spend by phase (plan.md, M2e): from data already collected, no model calls.

    python3.12 analysis_phase_spend.py                    # g-lid-full-1 and s3b-lid-full-1..3
    python3.12 analysis_phase_spend.py --ids g-lid-full-1

Splits a LID Full trajectory's agent tokens and cost by LID phase (HLD, LLD, EARS specs, edge audit, tests, code)
plus owner-facing stops, per change and overall.

Where the numbers come from:

- Calls. Each change's turn streams (runs/<id>/change-*/turn-*.stream.jsonl) list the main thread's API calls in
  order, by message ID, with their text and tool calls. That content is what the phase is inferred from.
- Tokens. A stream records each call's usage as the call began, so its output tokens are understated. Each call's
  final usage comes from the session transcript in the arm's configuration volume (read-only), matched by message
  ID; a subagent's tokens come from its own transcript, joined to the main-thread call that launched it through the
  transcript's meta file. A call missing from the transcripts keeps its stream usage, with the change's missing
  output tokens spread over such calls by the length of what they wrote. Per change, the tokens found this way are
  checked against the session's result records (each turn's result less the one before); a shortfall is reported as
  "unattributed".
- Dollars. Prices per token class are fitted, exactly, from the result records' own `costUSD` against their token
  counts (list prices, as Claude Code records them), and each call is priced from its tokens.

The attribution rule (primary, "as announced"):

1. The last call of each turn, whose text is the message the owner reads at the stop, goes to "stops". The phase
   it closes is kept separately ("stops by phase").
2. Every other call (a working call) goes to a phase, turn by turn:
   a. A turn whose working calls announce no phase, but whose stop message says which phase it closes, goes wholly
      to that phase, forward or back. Only explicit statements count: "This is the Phase 1 stop", "Phase 3 is
      drafted", "the Phase 4 audit", "I'm in Phase 1", a line or heading that starts with "Phase N" ("**Phase 4
      (edge audit):**"); "Phases 1 and 2" counts as the later one. Failing those, one before the phase the stop
      first looks ahead to ("If this reads right, I'll move to Phase 3" closes Phase 2). A passing reference
      ("matches the Phase 4 edits", "(Phase 2)") is no evidence. So an edge audit that edits specs without
      announcing itself is edge audit.
   b. Otherwise the current phase is set as the calls go by. A phase announcement in a working call's text sets
      it, forward or back: the last "Phase N" in the text that isn't retrospective ("Phase 1 is done", "deferred in
      Phase 5", "in line with the Phase 4 edits"). A call without one that writes or edits files moves it forward
      to the latest phase they belong to, never back, and never past the phase the turn's stop closes:
      docs/high-level-design.md is HLD (1); a design doc (*-design.md) or decision doc is LLD (2); a spec file
      (*-specs.md) is EARS specs (3); a test file is tests (5); other source is code (6). Writes are read from
      Write and Edit calls and from shell commands (redirections, tee, sed -i, cp/mv targets, and path literals in
      inline Python that writes files, relative paths resolved against any `cd` before them). Other files (README,
      AGENTS.md, arrow docs) are no evidence. So Phase 6 fixing a test or ticking a spec stays code, and a stub
      module written in a turn that closes Phase 5 stays tests.
   c. Calls in a turn before its first evidence take the phase that evidence sets (reading comes before writing);
      a turn with no evidence keeps the phase from before it.
3. Subagents take the phase of the call that launched them.
4. Calls before any evidence in their change go to "no phase": first-turn triage questions asked before any phase
   is named, and changes LID handled outside the phases (a README-only change).

A sensitivity variant ("as written") gives each call that writes phase files the phase of what it writes (split
equally across phases when it writes several), and otherwise follows the primary rule.
"""

from __future__ import annotations

import argparse
import io
import json
import re
import shlex
import subprocess
import sys
import tarfile
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
IMAGE = "lid-cost-eval-executor-rust:2.1.323"

PHASES = {1: "hld", 2: "lld", 3: "ears", 4: "edge_audit", 5: "tests", 6: "code"}
BUCKETS = ("hld", "lld", "ears", "edge_audit", "tests", "code", "stops", "no_phase", "unattributed")
LABELS = {"hld": "HLD", "lld": "LLD", "ears": "EARS specs", "edge_audit": "Edge audit", "tests": "Tests",
          "code": "Code", "stops": "Owner-facing stops", "no_phase": "No phase", "unattributed": "Unattributed"}
CLASSES = ("input", "output", "cache_read", "cache_write_5m", "cache_write_1h")
DEFAULT_IDS = ["g-lid-full-1", "s3b-lid-full-1", "s3b-lid-full-2", "s3b-lid-full-3"]

# ------------------------------------------------------------------------------------------- files and phases

_CODE_SUFFIXES = (".py", ".js", ".ts", ".rs", ".go", ".java", ".rb", ".sql")


def path_phase(path: str) -> int | None:
    """The LID phase a written file belongs to, or None when it is no evidence."""
    p = path.strip().strip("'\"").lower()
    for prefix in ("/work/", "./"):
        if p.startswith(prefix):
            p = p[len(prefix):]
    parts = p.split("/")
    base = parts[-1]
    if base == "high-level-design.md":
        return 1
    if base.endswith("-specs.md"):
        return 3
    if base.endswith("-design.md") or ("decisions" in parts[:-1] and base.endswith(".md")):
        return 2
    if base.endswith(_CODE_SUFFIXES):
        if (any(seg in ("tests", "test") for seg in parts[:-1]) or base.startswith("test_")
                or base.endswith("_test.py") or base == "conftest.py"):
            return 5
        return 6
    return None


_PATHLIKE = re.compile(r"""['"]([\w./*\-]+\.(?:md|py|js|ts|rs|go|sql))['"]""")
_REDIRECT = re.compile(r"(?<![<>&0-9])>>?\s*([^\s;&|<>()'\"]+)")
_TEE = re.compile(r"\btee\s+(?:-a\s+)?([^\s;&|<>()]+)")
_PY_WRITES = re.compile(r"open\([^)]*['\"][wa]\+?['\"]|\.write\(|write_text\(|\.writelines\(")
_SEP = re.compile(r"&&|\|\||;|\|")
_HEREDOC = re.compile(r"<<-?\s*(['\"]?)([\w.-]+)\1")
_SCRATCH = ("/dev/", "/tmp/", "&")


def _strip_quoted(s: str) -> str:
    return re.sub(r"'[^']*'|\"[^\"]*\"", " ", s)


def _join(cwd: str | None, path: str) -> str:
    if cwd is None or path.startswith("/"):
        return path
    parts = cwd.rstrip("/").split("/")
    for p in path.split("/"):
        if p == "..":
            parts = parts[:-1] or [""]
        elif p and p != ".":
            parts.append(p)
    return "/".join(parts)


def bash_writes(command: str) -> list[str]:
    """The files a shell command writes or edits, as far as its text shows: redirections, tee, sed -i, cp and mv
    targets, and path literals in inline Python that writes files; relative paths are resolved against any `cd`
    before them. Heredoc bodies are file content or scripts, not shell."""
    out: list[str] = []
    lines = command.split("\n")
    cwd: str | None = None
    i = 0
    while i < len(lines):
        line = lines[i]
        body = ""
        m = _HEREDOC.search(line)
        if m:
            term, j, collected = m.group(2), i + 1, []
            while j < len(lines) and lines[j].strip() != term:
                collected.append(lines[j])
                j += 1
            body, i = "\n".join(collected), j
        segs = _SEP.split(line)
        for k, seg in enumerate(segs):
            seg = seg.strip()
            try:
                toks = shlex.split(_HEREDOC.sub(" ", seg))
            except ValueError:
                toks = _HEREDOC.sub(" ", seg).split()
            if not toks:
                continue
            if toks[0] == "cd" and len(toks) > 1:
                cwd = _join(cwd, toks[1])
                continue
            script = seg + ("\n" + body if k == len(segs) - 1 else "")
            if re.search(r"\bpython[\d.]*\b", seg) and _PY_WRITES.search(script):
                out += [_join(cwd, p) for p in _PATHLIKE.findall(script)]
            shell = _strip_quoted(_HEREDOC.sub(" ", seg))
            out += [_join(cwd, t) for t in _REDIRECT.findall(shell) if not t.startswith(_SCRATCH)]
            out += [_join(cwd, t) for t in _TEE.findall(shell) if not t.startswith(_SCRATCH + ("-",))]
            if toks[0] == "sed" and any(t.startswith("-i") for t in toks[1:]):
                args, scripted, skip = [], False, False
                for t in toks[1:]:
                    if skip:
                        skip = False
                    elif t in ("-e", "-f", "--expression", "--file"):
                        scripted, skip = True, True
                    elif not t.startswith("-"):
                        args.append(t)
                if not scripted:  # the first non-option argument is the script unless -e or -f gave it
                    args = args[1:]
                out += [_join(cwd, a) for a in args if ("." in a or "/" in a) and not a.startswith(_SCRATCH)]
            elif toks[0] in ("cp", "mv") and len(toks) >= 3 and not toks[-1].startswith(_SCRATCH):
                out.append(_join(cwd, toks[-1]))
        i += 1
    return out


def call_writes(blocks: list[dict]) -> list[str]:
    paths: list[str] = []
    for b in blocks:
        if b.get("type") != "tool_use":
            continue
        name, inp = b.get("name", ""), b.get("input") or {}
        if name in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
            p = inp.get("file_path") or inp.get("notebook_path")
            if p:
                paths.append(p)
        elif name.lower() == "bash":
            paths += bash_writes(inp.get("command") or "")
    return paths


_PHASE = re.compile(r"\bPhase\s+([1-6])\b(?!\s*[-–]\s*[1-6])")
_RETRO_AFTER = re.compile(
    r"^(?:'s\b[^.\n]{0,40}?\b(?:are|is|were|was)\s+|\s+(?:is|are|was|has been|have been)\s+(?:now\s+|all\s+)?)"
    r"(?:done|complete|completed|finished|drafted|landed|over|approved|in place|half done|closed)", re.I)
_RETRO_BEFORE = re.compile(r"(?:\bdeferred (?:in|to|until)|\bin line with(?: the)?|\bfrom(?: the)?|\bduring(?: the)?|"
                           r"\bafter(?: the)?|\bsince(?: the)?|\bback in|\bearlier in|\bin(?: the)?)\s+$", re.I)


def announcement(text: str) -> int | None:
    """The phase a working call's text announces: its last non-retrospective "Phase N"."""
    last = None
    for m in _PHASE.finditer(text):
        if text[max(0, m.start() - 1):m.start()].isalpha():
            continue
        before = text[max(0, m.start() - 30):m.start()]
        after = text[m.end():m.end() + 60]
        if _RETRO_AFTER.search(after) or _RETRO_BEFORE.search(before):
            continue
        last = int(m.group(1))
    return last


_PAIR = re.compile(r"\bPhases?\s+[1-6]\s*(?:and|&|,|to|-|–|/)\s*([1-6])\b")
_N = r"Phase\s+([1-6])\b"
_CLOSING = [re.compile(p, re.I | re.M) for p in (
    r"\bThis is (?:the |my )?(?:first |second |third |final |last )?" + _N,
    _N + r"(?:\s*\([^)\n]{0,40}\))?,?\s*(?:is|are|was)\s+(?:now\s+)?(?:done|drafted|complete|completed|ready|written|"
         r"finished|in place|half done|landed|run)",
    r"\b(?:at|for|in) the " + _N + r"\s+(?:stop|review|boundary)",
    r"\bat the Phase\s+([1-6])/[1-6]\s+boundary",
    _N + r"\s+(?:stop|review|audit|output|results|draft)\b",
    # a line or heading that starts with "Phase N" ("**Phase 1 (HLD check):**", "## Phase 4 output"), not looking ahead
    r"^[\W_]*" + _N + r"(?!(?:\s*\([^)\n]{0,40}\))?\s+(?:would|will|is next|comes next))",
    r"\b(?:I'm|I am|we're|still) (?:now )?(?:in|at) (?:the )?" + _N,
    r"\bI(?:'ve| have) (?:\w+ )?(?:drafted|written|run|done|finished|completed|updated) the " + _N,
)]
_FORWARD = [re.compile(p, re.I) for p in (
    r"\b(?:start|begin|move (?:on )?to|go (?:on )?to|proceed (?:to|with)|run|write|on to)\s+(?:with\s+)?(?:the\s+)?" + _N,
    r"\bbefore (?:I |we )?(?:start |begin |move to |go to |go on to )?(?:on )?(?:the )?" + _N,
    r"\bNext (?:is|comes|up:?)\s+" + _N,
    r"\bThen (?:comes )?" + _N,
    r"\bAfter that comes " + _N,
    _N + r"(?:\s*\([^)\n]{0,40}\))?\s+(?:would|will|is next|comes next)",
)]


def stop_announcement(text: str) -> int | None:
    """The phase a stop message closes, from explicit statements only: "This is the Phase 1 stop", "Phase 3 is
    drafted", "the Phase 4 audit", "I'm in Phase 1", a line starting with "Phase N". "Phases 1 and 2" counts as its
    later phase. Failing those, one before the phase it first looks ahead to ("If this reads right, I'll move to Phase
    3" closes Phase 2). A passing reference ("matches the Phase 4 edits", "(Phase 2)") is no evidence."""
    t = _PAIR.sub(lambda m: f"Phase {m.group(1)}", text)
    hits = [(m.start(), int(m.group(1))) for p in _CLOSING for m in p.finditer(t)]
    if hits:
        return min(hits)[1]
    ahead = [(m.start(), int(m.group(1))) for p in _FORWARD for m in p.finditer(t)]
    if ahead:
        n = min(ahead)[1]
        return n - 1 if n > 1 else None
    return None


# ------------------------------------------------------------------------------------------------ the record


@dataclass
class Call:
    msg_id: str
    blocks: list[dict]
    turn: int
    final: bool = False
    tokens: dict[str, int] = field(default_factory=dict)
    usage_source: str = "stream"
    phase: str = "no_phase"  # primary rule
    phase_written: dict[str, float] = field(default_factory=dict)  # sensitivity variant: bucket -> weight
    stop_phase: str | None = None
    announce: int | None = None
    writes: list[str] = field(default_factory=list)
    write_phases: list[int] = field(default_factory=list)
    spawns: list[str] = field(default_factory=list)  # Agent/Task tool_use ids

    @property
    def text(self) -> str:
        return "\n".join(b.get("text", "") for b in self.blocks if b.get("type") == "text")

    @property
    def visible_chars(self) -> int:
        n = 0
        for b in self.blocks:
            if b.get("type") == "text":
                n += len(b.get("text", ""))
            elif b.get("type") == "tool_use":
                n += len(json.dumps(b.get("input") or {}))
        return max(n, 1)


def _tokens_from_usage(u: dict) -> dict[str, int]:
    split = u.get("cache_creation") or {}
    w = u.get("cache_creation_input_tokens", 0) or 0
    w5, w1 = split.get("ephemeral_5m_input_tokens"), split.get("ephemeral_1h_input_tokens")
    if w5 is None and w1 is None:
        w5, w1 = w, 0
    return {"input": u.get("input_tokens", 0) or 0, "output": u.get("output_tokens", 0) or 0,
            "cache_read": u.get("cache_read_input_tokens", 0) or 0, "cache_write_5m": w5 or 0, "cache_write_1h": w1 or 0}


def _tokens_from_model_usage(mu: dict) -> dict[str, int]:
    out = {c: 0 for c in CLASSES}
    for v in (mu or {}).values():
        w5, w1 = v.get("cacheCreationEphemeral5mInputTokens"), v.get("cacheCreationEphemeral1hInputTokens")
        if w5 is None and w1 is None:
            w5, w1 = v.get("cacheCreationInputTokens", 0), 0
        out["input"] += v.get("inputTokens", 0)
        out["output"] += v.get("outputTokens", 0)
        out["cache_read"] += v.get("cacheReadInputTokens", 0)
        out["cache_write_5m"] += w5 or 0
        out["cache_write_1h"] += w1 or 0
    return out


def _add(a: dict, b: dict, k: float = 1.0) -> dict:
    return {c: a.get(c, 0) + k * b.get(c, 0) for c in set(a) | set(b)}


def total_tokens(t: dict) -> float:
    return sum(t.get(c, 0) for c in CLASSES)


def read_stream(path: Path) -> tuple[str | None, list[tuple[str, list[dict], dict]], dict | None]:
    """(session id, main-thread calls in order as (message id, content blocks, stream usage), last result)."""
    session, result = None, None
    order: list[str] = []
    blocks: dict[str, list[dict]] = {}
    usage: dict[str, dict] = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            session = r.get("session_id", session)
            if r.get("type") == "result":
                result = r
            if r.get("type") != "assistant" or r.get("parent_tool_use_id"):
                continue
            m = r.get("message") or {}
            mid = m.get("id")
            if not mid:
                continue
            if mid not in blocks:
                order.append(mid)
                blocks[mid] = []
            blocks[mid].extend(m.get("content") or [])
            if m.get("usage"):
                usage[mid] = m["usage"]
    return session, [(mid, blocks[mid], usage.get(mid, {})) for mid in order], result


# ------------------------------------------------------------------------------------------------ transcripts


@dataclass
class Transcripts:
    """Per message ID usage for main threads, and per launching tool_use ID usage for subagents."""
    messages: dict[str, dict[str, int]] = field(default_factory=dict)
    subagents: dict[str, dict[str, int]] = field(default_factory=dict)  # toolUseId -> tokens
    subagent_parents: dict[str, str] = field(default_factory=dict)  # subagent's own agent id -> launching toolUseId
    unlinked_subagents: dict[str, int] = field(default_factory=dict)  # file -> total tokens, no toolUseId


def _jsonl_messages(lines) -> dict[str, dict[str, int]]:
    seen: dict[str, dict[str, int]] = {}
    for line in lines:
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        m = r.get("message") or {}
        if r.get("type") != "assistant" or not m.get("id") or not m.get("usage"):
            continue
        seen[m["id"]] = _tokens_from_usage(m["usage"])
    return seen


def transcripts_from_files(files: dict[str, bytes]) -> Transcripts:
    """Transcripts from a projects folder's files (path -> bytes)."""
    t = Transcripts()
    metas = {p: json.loads(b) for p, b in files.items() if p.endswith(".meta.json")}
    for p, data in files.items():
        if not p.endswith(".jsonl"):
            continue
        lines = data.decode("utf-8", errors="replace").splitlines()
        msgs = _jsonl_messages(lines)
        if "/subagents/" in p:
            meta = metas.get(p[:-len(".jsonl")] + ".meta.json") or {}
            tok = {c: 0 for c in CLASSES}
            for v in msgs.values():
                tok = _add(tok, v)
            tid = meta.get("toolUseId")
            if tid:
                t.subagents[tid] = _add(t.subagents.get(tid, {c: 0 for c in CLASSES}), tok)
            else:
                t.unlinked_subagents[p] = int(total_tokens(tok))
        else:
            t.messages.update(msgs)
    return t


def transcripts_from_volume(volume: str, image: str = IMAGE) -> Transcripts:
    proc = subprocess.run(["docker", "run", "--rm", "-v", f"{volume}:/cfg:ro", "--entrypoint", "tar", image,
                           "-C", "/cfg/projects", "-c", "."], capture_output=True, timeout=600)
    if proc.returncode != 0:
        raise RuntimeError(f"reading {volume}: {proc.stderr.decode(errors='replace')[-300:]}")
    files: dict[str, bytes] = {}
    with tarfile.open(fileobj=io.BytesIO(proc.stdout), mode="r:*") as tf:
        for m in tf.getmembers():
            if m.isfile() and (m.name.endswith(".jsonl") or m.name.endswith(".meta.json")):
                f = tf.extractfile(m)
                if f is not None:
                    files[m.name] = f.read()
    return transcripts_from_files(files)


# ------------------------------------------------------------------------------------------------ attribution


def classify_calls(turns: list[list[Call]]) -> None:
    """Apply the attribution rule to one change's calls, turn by turn, in place."""
    state: int | None = None
    for calls in turns:
        if not calls:
            continue
        last, working = calls[-1], calls[:-1]
        last.final = True
        closing = stop_announcement(last.text)
        for c in working:
            c.announce = announcement(c.text)
            c.writes = call_writes(c.blocks)
            c.write_phases = sorted({p for p in (path_phase(w) for w in c.writes) if p is not None})
            c.spawns = [b.get("id") for b in c.blocks
                        if b.get("type") == "tool_use" and b.get("name") in ("Agent", "Task") and b.get("id")]
        if closing is not None and all(c.announce is None for c in working):
            state = closing  # 2d: no announcement in the turn, so its stop says which phase its work was
            for c in working:
                c.phase = PHASES[state]
        else:
            pending: list[Call] = []
            seen_evidence = False
            for c in working:
                evidence = False
                if c.announce is not None:  # 2a
                    state, evidence = c.announce, True
                elif c.write_phases:  # 2b: forward only, and not past the phase the stop closes
                    evidence = True
                    target = max(c.write_phases) if closing is None else min(max(c.write_phases), closing)
                    if state is None or target > state:
                        state = target
                current = PHASES[state] if state is not None else "no_phase"
                if evidence and not seen_evidence:  # 2c: earlier calls in the turn take this phase
                    seen_evidence = True
                    for p in pending:
                        p.phase = current
                    pending = []
                if seen_evidence:
                    c.phase = current
                else:
                    pending.append(c)
            for p in pending:  # no evidence at all: the phase from before the turn
                p.phase = PHASES[state] if state is not None else "no_phase"
        last.phase = "stops"
        stop = closing if closing is not None else state
        last.stop_phase = PHASES[stop] if stop is not None else "no_phase"
        last.writes = call_writes(last.blocks)
        for c in calls:
            if c.final:
                c.phase_written = {"stops": 1.0}
            elif c.write_phases:
                w = 1.0 / len(c.write_phases)
                c.phase_written = {PHASES[p]: w for p in c.write_phases}
            else:
                c.phase_written = {c.phase: 1.0}


def fit_prices(records: list[dict]) -> dict[str, float]:
    """Dollars per token for each class, fitted by least squares to result records' (tokens, costUSD) pairs. Classes
    that never occur get a price of 0."""
    rows = []
    for r in records:
        for v in (r.get("modelUsage") or {}).values():
            t = _tokens_from_model_usage({"m": v})
            if v.get("costUSD") is not None:
                rows.append(([t[c] / 1e6 for c in CLASSES], v["costUSD"]))
    used = [i for i in range(len(CLASSES)) if any(x[i] for x, _ in rows)]
    n = len(used)
    if not n:
        return {c: 0.0 for c in CLASSES}
    if len(rows) < 2 * n:
        raise ValueError(f"{len(rows)} cost records are too few to fit {n} prices")
    a = [[0.0] * (n + 1) for _ in range(n)]
    for x, y in rows:
        xs = [x[i] for i in used]
        for i in range(n):
            a[i][n] += xs[i] * y
            for j in range(n):
                a[i][j] += xs[i] * xs[j]
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(a[r][col]))
        a[col], a[piv] = a[piv], a[col]
        if abs(a[col][col]) < 1e-12:
            continue
        for r in range(n):
            if r != col:
                f = a[r][col] / a[col][col]
                a[r] = [u - f * v for u, v in zip(a[r], a[col])]
    per_m = {CLASSES[used[i]]: (a[i][n] / a[i][i] if abs(a[i][i]) > 1e-12 else 0.0) for i in range(n)}
    prices = {c: per_m.get(c, 0.0) / 1e6 for c in CLASSES}
    worst = max(abs(sum(x[i] * per_m.get(CLASSES[i], 0.0) for i in range(len(CLASSES))) - y) for x, y in rows)
    if worst > 1e-6 + 1e-6 * max(y for _, y in rows):
        raise ValueError(f"the fitted prices miss a cost record by ${worst:.6f}: costs aren't linear in tokens")
    return prices


def price(tokens: dict, prices: dict[str, float]) -> float:
    return sum(tokens.get(c, 0) * prices[c] for c in CLASSES)


def change_spend(cdir: Path, tr: Transcripts | None) -> dict:
    """One change's calls with tokens and phases, its result totals and its reconciliation."""
    turns: list[list[Call]] = []
    results: list[dict] = []
    stream_usage: dict[str, dict] = {}
    for k, f in enumerate(sorted(cdir.glob("turn-[0-9][0-9].stream.jsonl"))):
        _, calls, result = read_stream(f)
        turns.append([Call(mid, blocks, k) for mid, blocks, _ in calls])
        stream_usage.update({mid: u for mid, _, u in calls})
        if result is not None:
            results.append(result)
    classify_calls(turns)
    # result totals: cumulative within the session, so the last result's totals are the change's
    recorded = _tokens_from_model_usage(results[-1].get("modelUsage")) if results else {c: 0 for c in CLASSES}
    recorded_cost = results[-1].get("total_cost_usd") if results else None
    calls = [c for t in turns for c in t]
    fallback = []
    for c in calls:
        if tr is not None and c.msg_id in tr.messages:
            c.tokens, c.usage_source = dict(tr.messages[c.msg_id]), "transcript"
        else:
            c.tokens, c.usage_source = _tokens_from_usage(stream_usage.get(c.msg_id, {})), "stream"
            fallback.append(c)
    sub: list[tuple[Call, dict]] = []
    for c in calls:
        for tid in c.spawns:
            if tr is not None and tid in tr.subagents:
                sub.append((c, tr.subagents[tid]))
    found = {cl: 0 for cl in CLASSES}
    for c in calls:
        found = _add(found, c.tokens)
    for _, t in sub:
        found = _add(found, t)
    if fallback:  # spread the missing output over calls without final usage, by what they wrote
        missing = int(round(recorded["output"] - found["output"]))
        if missing > 0:
            weight = sum(c.visible_chars for c in fallback)
            shares = [missing * c.visible_chars / weight for c in fallback]
            extra = [int(x) for x in shares]
            for i in sorted(range(len(fallback)), key=lambda i: extra[i] - shares[i])[:missing - sum(extra)]:
                extra[i] += 1  # largest remainders, so the parts add up exactly
            for c, e in zip(fallback, extra):
                c.tokens["output"] += e
                found["output"] += e
    residual = {cl: recorded[cl] - found[cl] for cl in CLASSES}
    return {"turns": turns, "calls": calls, "subagents": sub, "recorded": recorded, "recorded_cost": recorded_cost,
            "residual": residual, "results": results, "fallback_calls": len(fallback)}


def run_spend(run: Path, tr: Transcripts | None, prices: dict[str, float] | None = None) -> dict:
    traj = json.loads((run / "trajectory.json").read_text())
    changes = {}
    for cdir in sorted(run.glob("change-[0-9][0-9]")):
        if not list(cdir.glob("turn-*.stream.jsonl")):
            continue
        changes[int(cdir.name.split("-")[1])] = change_spend(cdir, tr)
    if prices is None:
        prices = fit_prices([r for ch in changes.values() for r in ch["results"]])
    out_changes = {}
    tot = {"primary": {b: {"tokens": 0.0, "cost": 0.0, "calls": 0} for b in BUCKETS},
           "written": {b: {"tokens": 0.0, "cost": 0.0} for b in BUCKETS},
           "by_class": {b: {c: 0.0 for c in CLASSES} for b in BUCKETS}, "subagent_cost": 0.0}
    stops_by_phase: dict[str, dict[str, float]] = {}
    recon = []
    for n, ch in changes.items():
        prim = {b: {"tokens": 0.0, "cost": 0.0, "calls": 0} for b in BUCKETS}
        wrt = {b: {"tokens": 0.0, "cost": 0.0} for b in BUCKETS}
        for c in ch["calls"]:
            tt, cc = total_tokens(c.tokens), price(c.tokens, prices)
            for cl in CLASSES:
                tot["by_class"][c.phase][cl] += c.tokens.get(cl, 0) * prices[cl]
            prim[c.phase]["tokens"] += tt
            prim[c.phase]["cost"] += cc
            prim[c.phase]["calls"] += 1
            for b, w in c.phase_written.items():
                wrt[b]["tokens"] += w * tt
                wrt[b]["cost"] += w * cc
            if c.final:
                s = stops_by_phase.setdefault(c.stop_phase, {"tokens": 0.0, "cost": 0.0, "stops": 0})
                s["tokens"] += tt
                s["cost"] += cc
                s["stops"] += 1
        for parent, t in ch["subagents"]:
            tt, cc = total_tokens(t), price(t, prices)
            tot["subagent_cost"] += cc
            for cl in CLASSES:
                tot["by_class"][parent.phase][cl] += t.get(cl, 0) * prices[cl]
            prim[parent.phase]["tokens"] += tt
            prim[parent.phase]["cost"] += cc
            for b, w in parent.phase_written.items():
                wrt[b]["tokens"] += w * tt
                wrt[b]["cost"] += w * cc
        res = {c: max(v, 0) for c, v in ch["residual"].items()}
        for d in (prim, wrt):
            d["unattributed"]["tokens"] += total_tokens(res)
            d["unattributed"]["cost"] += price(res, prices)
        for b in BUCKETS:
            for k in ("tokens", "cost"):
                tot["primary"][b][k] += prim[b][k]
                tot["written"][b][k] += wrt[b][k]
            tot["primary"][b]["calls"] += prim[b]["calls"]
        found_tokens = total_tokens(ch["recorded"]) - total_tokens(ch["residual"])
        recon.append({"change": n, "recorded_tokens": int(total_tokens(ch["recorded"])), "found_tokens": int(found_tokens),
                      "residual": {k: int(v) for k, v in ch["residual"].items() if v},
                      "recorded_cost": ch["recorded_cost"], "priced_cost": round(price(ch["recorded"], prices), 6),
                      "fallback_calls": ch["fallback_calls"], "calls": len(ch["calls"]), "subagents": len(ch["subagents"])})
        out_changes[str(n)] = {"primary": prim, "written": wrt,
                               "turns": [[{"msg": c.msg_id, "phase": c.phase, "announce": c.announce,
                                           "write_phases": c.write_phases, "final": c.final, "stop_phase": c.stop_phase,
                                           "tokens": int(total_tokens(c.tokens)), "usage": c.usage_source}
                                          for c in t] for t in ch["turns"]]}
    return {"id": traj.get("id", run.name), "arm": traj.get("arm"), "seed": traj.get("seed"),
            "prices_per_mtok": {c: round(p * 1e6, 4) for c, p in prices.items()},
            "changes": out_changes, "total": tot, "stops_by_phase": stops_by_phase, "reconciliation": recon}


# ------------------------------------------------------------------------------------------------- reporting


def _share(d: dict, key: str) -> dict[str, float]:
    total = sum(v[key] for v in d.values())
    return {b: (d[b][key] / total if total else 0.0) for b in d}


def report(results: list[dict]) -> str:
    lines = ["# LID's spend by phase", "",
             "Agent tokens (all classes: input, output, cache reads and writes) and dollars at list prices fitted from "
             "the runs' own cost records, split by LID phase. Read the attribution rule at the end before the numbers.",
             ""]
    lines += ["## Overall shares (primary rule, as announced)", "",
              "| Trajectory | Total cost | " + " | ".join(LABELS[b] for b in BUCKETS) + " |",
              "|---|---|" + "---|" * len(BUCKETS)]
    for r in results:
        p = r["total"]["primary"]
        cs, ts = _share(p, "cost"), _share(p, "tokens")
        total_cost = sum(v["cost"] for v in p.values())
        lines.append(f"| {r['id']} | ${total_cost:.2f} | " + " | ".join(
            f"{100 * cs[b]:.0f}% ({100 * ts[b]:.0f}%)" for b in BUCKETS) + " |")
    lines += ["", "Each cell is the share of cost, with the share of tokens in brackets.", ""]
    s3b = [r for r in results if r["id"].startswith("s3b-")]
    if s3b:
        pooled = {b: {"cost": sum(r["total"]["primary"][b]["cost"] for r in s3b),
                      "tokens": sum(r["total"]["primary"][b]["tokens"] for r in s3b)} for b in BUCKETS}
        cs, ts = _share(pooled, "cost"), _share(pooled, "tokens")
        lines += [f"BenchTime stage 3b pooled ({len(s3b)} trajectories): " + "; ".join(
            f"{LABELS[b]} {100 * cs[b]:.0f}% ({100 * ts[b]:.0f}%)" for b in BUCKETS if pooled[b]["cost"]) + ".", ""]
    lines += ["## What each bucket's dollars paid for (all four trajectories pooled)", "",
              "Share of each bucket's cost by token class. Every change opens a fresh session, so its first calls write "
              "the system prompt, the skill and the first reads to the cache; those writes land in the phase the change "
              "starts in, usually HLD.", "",
              "| Bucket | Cost | Output | Cache writes | Cache reads | Uncached input |", "|---|---|---|---|---|---|"]
    for b in BUCKETS:
        bc = {cl: sum(r["total"]["by_class"][b][cl] for r in results) for cl in CLASSES}
        tc = sum(bc.values())
        if not tc:
            continue
        w = bc["cache_write_5m"] + bc["cache_write_1h"]
        lines.append(f"| {LABELS[b]} | ${tc:.2f} | {100 * bc['output'] / tc:.0f}% | {100 * w / tc:.0f}% | "
                     f"{100 * bc['cache_read'] / tc:.0f}% | {100 * bc['input'] / tc:.0f}% |")
    sub = sum(r["total"]["subagent_cost"] for r in results)
    allc = sum(sum(v["cost"] for v in r["total"]["primary"].values()) for r in results)
    lines += ["", f"Subagents account for ${sub:.2f} of ${allc:.2f} ({100 * sub / allc:.0f}%), each counted in the "
              "phase of the call that launched it.", ""]
    lines += ["## Sensitivity: as written", "",
              "Calls that write phase files take the phase of what they write; the rest as the primary rule.", "",
              "| Trajectory | " + " | ".join(LABELS[b] for b in BUCKETS) + " |", "|---|" + "---|" * len(BUCKETS)]
    for r in results:
        cs = _share(r["total"]["written"], "cost")
        lines.append(f"| {r['id']} | " + " | ".join(f"{100 * cs[b]:.0f}%" for b in BUCKETS) + " |")
    lines += ["", "## Stops by the phase they close (share of all stop cost)", ""]
    for r in results:
        sp = r["stops_by_phase"]
        tot = sum(v["cost"] for v in sp.values())
        lines.append(f"- {r['id']}: " + "; ".join(
            f"{LABELS.get(k, k)} {v['stops']} stops, {100 * v['cost'] / tot:.0f}%" for k, v in
            sorted(sp.items(), key=lambda kv: BUCKETS.index(kv[0]) if kv[0] in BUCKETS else 99)) + ".")
    for r in results:
        lines += ["", f"## {r['id']}: cost by phase and change (primary rule)", "",
                  "| Change | Cost | " + " | ".join(LABELS[b] for b in BUCKETS) + " |", "|---|---|" + "---|" * len(BUCKETS)]
        for n, ch in sorted(r["changes"].items(), key=lambda kv: int(kv[0])):
            p = ch["primary"]
            total = sum(v["cost"] for v in p.values())
            lines.append(f"| {n} | ${total:.2f} | " + " | ".join(
                (f"{100 * p[b]['cost'] / total:.0f}%" if total and p[b]["cost"] else "–") for b in BUCKETS) + " |")
    lines += ["", "## Reconciliation", "",
              "Tokens found (transcripts, matched by message ID, plus subagent transcripts) against the session's "
              "result totals; dollars priced from the fitted prices against Claude Code's recorded cost.", ""]
    for r in results:
        rec = r["reconciliation"]
        rt = sum(x["recorded_tokens"] for x in rec)
        ft = sum(x["found_tokens"] for x in rec)
        rc = sum(x["recorded_cost"] or 0 for x in rec)
        pc = sum(x["priced_cost"] for x in rec)
        fb = sum(x["fallback_calls"] for x in rec)
        calls = sum(x["calls"] for x in rec)
        off = [f"change {x['change']}: {x['residual']}" for x in rec if x["residual"]]
        lines.append(f"- {r['id']}: {ft:,} of {rt:,} recorded tokens found ({100 * ft / rt:.2f}%); recorded cost "
                     f"${rc:.2f}, priced ${pc:.2f}; {fb} of {calls} calls without transcript usage. Prices per million "
                     f"tokens: " + ", ".join(f"{k} ${v}" for k, v in r["prices_per_mtok"].items())
                     + (". Residuals: " + "; ".join(off[:6]) if off else "") + ".")
    lines += ["", "## The attribution rule", "", __doc__.split("The attribution rule (primary, \"as announced\"):", 1)[1]
              .split("A sensitivity variant", 1)[0].strip(), "",
              "A sensitivity variant (\"as written\") gives each call that writes phase files the phase of what it "
              "writes, split equally when it writes several, and otherwise follows the primary rule."]
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ids", nargs="+", default=DEFAULT_IDS)
    ap.add_argument("--runs", type=Path, default=HERE.parent / "runs")
    ap.add_argument("--out", type=Path, default=None, help="output folder (default: <runs>/analysis)")
    ap.add_argument("--no-transcripts", action="store_true", help="use stream usage only (output tokens estimated)")
    args = ap.parse_args(argv)
    out = args.out or args.runs / "analysis"
    runs = []
    for tid in args.ids:
        run = args.runs / tid
        if not (run / "trajectory.json").exists():
            print(f"{tid}: no trajectory.json, skipped", file=sys.stderr)
            continue
        traj = json.loads((run / "trajectory.json").read_text())
        tr = None
        if not args.no_transcripts:
            try:
                tr = transcripts_from_volume(traj["volumes"]["config"])
            except Exception as e:  # noqa: BLE001
                print(f"{tid}: transcripts unreadable ({e}); stream usage only", file=sys.stderr)
        runs.append((run, tr))
    # one price table for all runs, fitted from every result record they hold
    records = []
    for run, _ in runs:
        for f in sorted(run.glob("change-[0-9][0-9]/turn-*.stream.jsonl")):
            r = read_stream(f)[2]
            if r is not None:
                records.append(r)
    prices = fit_prices(records)
    results = [run_spend(run, tr, prices) for run, tr in runs]
    out.mkdir(parents=True, exist_ok=True)
    (out / "phase_spend.json").write_text(json.dumps(results, indent=1))
    (out / "phase_spend.md").write_text(report(results))
    for r in results:
        cs = _share(r["total"]["primary"], "cost")
        print(f"{r['id']}: " + ", ".join(f"{b} {100 * cs[b]:.0f}%" for b in BUCKETS if cs[b]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
