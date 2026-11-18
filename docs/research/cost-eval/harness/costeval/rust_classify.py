"""The pre-registered classification of held-out tests that fail against an arm's code.

A held-out test checks behaviour the project had before the change, and the arm never saw it. Where the change adds
state, a test that compares state whole can fail on the new state alone: a migrated save that now carries
`"nickname": null`. That is not a failure to keep the old behaviour. So each failing held-out test is classified:

- **new state only:** the only difference the failure reports is state the change itself adds, at its empty value.
  Logged and reported, not counted against keeping.
- **keeping failure:** anything else.

The judge model rules (prompts/keeping-classify-rust.md), from the change request and, for each failing test, its
failure output, the source of the test, of the failure site when that is elsewhere, and of the helpers the failing
statement calls (from the target's own files), and, where the output compares two JSON values, the key-by-key
difference the harness computes first. Each ruling gives a reason and cites evidence lines, which are checked; a
ruling that fails the check is asked again, and a test still without a valid ruling counts as a keeping failure.

Two cases need no ruling and are keeping failures: a test that reached a wildcard arm the adaptation added (a
variant the arm added arrived where the test handles only the old ones), and a failing test with no failure output.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Callable

from . import grading, rust_adapt

CLASSES = ("new state only", "keeping failure")
MAX_OUTPUT = 12000  # characters of one failure's output the judge sees
MAX_DIFFERENCES = 80
MAX_TEST_LINES = 150
MAX_HELPERS = 4
MAX_HELPER_LINES = 60
SITE_CONTEXT = 12
BATCH = 5
ATTEMPTS = 3

SCHEMA = {
    "type": "object", "additionalProperties": False, "required": ["rulings"],
    "properties": {"rulings": {"type": "array", "items": {
        "type": "object", "additionalProperties": False, "required": ["test", "classification", "reason", "evidence"],
        "properties": {
            "test": {"type": "string"}, "classification": {"type": "string", "enum": list(CLASSES)},
            "reason": {"type": "string"},
            "evidence": {"type": "array", "items": {
                "type": "object", "additionalProperties": False, "required": ["seq", "lines"],
                "properties": {"seq": {"type": "integer"}, "lines": {"type": "array", "items": {"type": "integer"}}}}}}}}},
}


# ---------------------------------------------------------------------------------------------- failure output


def failure_sections(log: str) -> dict[str, str]:
    """Each failing test's own output in a cargo test log, without the backtrace hint."""
    out = {}
    for m in re.finditer(r"(?ms)^---- (\S+) stdout ----\n(.*?)(?=^---- \S+ stdout ----|^failures:\s*$|\Z)", log):
        text = "\n".join(l for l in m.group(2).splitlines() if not l.startswith("note: run with `RUST_BACKTRACE"))
        out[m.group(1)] = text.strip("\n") + "\n"
    return out


def panic_site(output: str) -> tuple[str, int] | None:
    m = re.search(r"panicked at (\S+?):(\d+):\d+:", output)
    return (m.group(1), int(m.group(2))) if m else None


def _message(output: str) -> str:
    """The panic message: what follows the "panicked at" line."""
    m = re.search(r"panicked at \S+:\n", output)
    return output[m.end():] if m else output


_DEC = json.JSONDecoder()


def _from_value_debug(text: str) -> Any:
    """serde_json::Value's Debug form (`Object {"a": Number(1)}`) as the value it shows."""
    out, i, n = [], 0, len(text)
    while i < n:
        if text.startswith("Object {", i):
            out.append("{"); i += 8
        elif text.startswith("Array [", i):
            out.append("["); i += 7
        elif text.startswith("Number(", i) or text.startswith("Bool(", i):
            j = text.index(")", i)
            out.append(text[text.index("(", i) + 1:j]); i = j + 1
        elif text.startswith("Null", i):
            out.append("null"); i += 4
        elif text.startswith("String(", i):
            v, j = _DEC.raw_decode(text, i + 7)
            out.append(json.dumps(v)); i = j + 1
        elif text[i] == '"':
            v, j = _DEC.raw_decode(text, i)
            out.append(json.dumps(v)); i = j
        else:
            out.append(text[i]); i += 1
    return json.loads("".join(out))


def _as_json(text: str) -> Any:
    """A printed value as JSON: JSON itself, a Debug string holding JSON, or serde_json::Value's Debug form."""
    text = text.strip()
    for parse in (json.loads, _from_value_debug):
        try:
            v = parse(text)
        except (ValueError, IndexError):
            continue
        if isinstance(v, str) and v[:1] in "{[":
            try:
                v = json.loads(v)
            except ValueError:
                return None
        return v if isinstance(v, (dict, list)) else None
    return None


def json_values(text: str) -> list:
    """The JSON objects and arrays written in a text, and those held in Debug-printed strings, in order."""
    out, i = [], 0
    while i < len(text):
        c = text[i]
        if c in "{[":
            try:
                v, j = _DEC.raw_decode(text, i)
            except ValueError:
                i += 1
                continue
            if isinstance(v, (dict, list)):
                out.append(v)
            i = j
        elif c == '"':
            try:
                v, j = _DEC.raw_decode(text, i)
            except ValueError:
                i += 1
                continue
            if isinstance(v, str) and (inner := _as_json(v)) is not None:
                out.append(inner)
            i = j
        else:
            i += 1
    return out


def compared_json(output: str) -> tuple[str, str, Any, Any] | None:
    """The two JSON values a failure compares, with what the output calls them: an assert_eq's left and right, or
    else the only two values its message holds, first and second."""
    msg = _message(output)
    m = re.search(r"(?m)^\s*left: (.*)\n\s*right: (.*)$", msg)
    if m:
        a, b = _as_json(m.group(1)), _as_json(m.group(2))
        if a is not None and b is not None:
            return "left", "right", a, b
    values = json_values(msg)
    if len(values) == 2:
        return "first", "second", values[0], values[1]
    return None


def _short(v: Any) -> str:
    s = json.dumps(v, separators=(",", ":"), ensure_ascii=False)
    return s if len(s) <= 160 else s[:160] + "…"


def json_difference(a: Any, b: Any, *, labels: tuple[str, str] = ("first", "second"),
                    limit: int = MAX_DIFFERENCES) -> list[str]:
    """Key by key: what only one value has, and where both have something that differs."""
    l1, l2 = labels
    out: list[str] = []

    def walk(x: Any, y: Any, path: str) -> None:
        at = path or "(top)"
        if isinstance(x, dict) and isinstance(y, dict):
            for k in x:
                p = f"{path}.{k}" if path else k
                if k not in y:
                    out.append(f"{p}: only in {l1}: {_short(x[k])}")
                else:
                    walk(x[k], y[k], p)
            for k in y:
                if k not in x:
                    out.append(f"{path + '.' if path else ''}{k}: only in {l2}: {_short(y[k])}")
        elif isinstance(x, list) and isinstance(y, list):
            if len(x) != len(y):
                out.append(f"{at}: {len(x)} item{'' if len(x) == 1 else 's'} in {l1}, {len(y)} in {l2}")
            for i in range(min(len(x), len(y))):
                walk(x[i], y[i], f"{path}[{i}]")
            for i in range(len(y), len(x)):
                out.append(f"{path}[{i}]: only in {l1}: {_short(x[i])}")
            for i in range(len(x), len(y)):
                out.append(f"{path}[{i}]: only in {l2}: {_short(y[i])}")
        elif x != y or type(x) is not type(y):
            out.append(f"{at}: {l1} {_short(x)}, {l2} {_short(y)}")
    walk(a, b, "")
    if not out:
        return ["no difference between the two values"]
    if len(out) > limit:
        out = out[:limit] + [f"…and {len(out) - limit} more differences"]
    return out


# ---------------------------------------------------------------------------------------------------- source


_KEYWORDS = {"if", "match", "while", "for", "return", "loop", "in", "as", "move", "let", "fn", "else", "unsafe"}


def _fn_span(path: str, text: str, name: str) -> tuple[int, int] | None:
    """The 1-based first and last lines of a function's definition, with the attributes and doc comments above it."""
    masked = rust_adapt._mask_cached(text)
    for m in re.finditer(rf"(?m)^[ \t]*(?:pub(?:\s*\([^)]*\))?\s+)?(?:async\s+)?fn\s+{re.escape(name)}\b", masked):
        k = masked.find("(", m.end())
        if k < 0:
            continue
        depth = 0
        for j in range(k, len(masked)):
            depth += {"(": 1, ")": -1}.get(masked[j], 0)
            if depth == 0:
                break
        body = re.search(r"[{;]", masked[j:])
        if not body or body.group(0) == ";":
            continue
        close = rust_adapt._close(masked, j + body.start())
        if close is None:
            continue
        lines = text.splitlines()
        first = text.count("\n", 0, m.start()) + 1
        while first > 1 and re.match(r"\s*(#\[|///|//!)", lines[first - 2]):
            first -= 1
        return first, text.count("\n", 0, close) + 1
    return None


def _numbered(text: str, first: int, last: int) -> str:
    lines = text.splitlines()
    return "\n".join(f"{n:>5}  {lines[n - 1]}" for n in range(first, min(last, len(lines)) + 1))


def _statement_lines(text: str, line: int) -> tuple[int, int]:
    """The lines of the statement starting at this line: to where its first bracket closes."""
    masked = rust_adapt._mask_cached(text)
    starts = [0] + [m.end() for m in re.finditer("\n", masked)]
    if line > len(starts):
        return line, line
    k, depth, opened = starts[line - 1], 0, False
    while k < len(masked):
        c = masked[k]
        if c in "([{":
            depth, opened = depth + 1, True
        elif c in ")]}":
            depth -= 1
        if (opened and depth <= 0) or (not opened and c in ";\n" and k > starts[line - 1]):
            break
        k += 1
    return line, min(masked.count("\n", 0, k) + 1, line + 30)


def source_entries(files: dict[str, str], test: str, site: tuple[str, int] | None) -> list[dict]:
    """The test's source, the failure site's when it is outside the test, and the helpers in the target's own files
    that the failing statement calls, each with its file and lines (the file's own numbers)."""
    name, module = test.split("::")[-1], (test.split("::")[0] if "::" in test else None)
    entries: list[dict] = []
    ordered = sorted(files, key=lambda p: (Path(p).stem != module, p))
    test_at = None
    for path in ordered:
        span = _fn_span(path, files[path], name)
        if span:
            test_at = (path, *span)
            break
    if test_at:
        path, first, last = test_at
        if last - first + 1 > MAX_TEST_LINES:
            if site and site[0] == path and first <= site[1] <= last:
                first, last = max(first, site[1] - MAX_TEST_LINES + 20), min(last, site[1] + 20)
            else:
                last = first + MAX_TEST_LINES - 1
        entries.append({"kind": "test source", "file": path, "from": first, "to": last,
                        "text": _numbered(files[path], first, last)})
    statement = None
    if site and site[0] in files:
        path, line = site
        if not (test_at and test_at[0] == path and test_at[1] <= line <= test_at[2]):
            first, last = max(1, line - SITE_CONTEXT), line + SITE_CONTEXT
            last = min(last, files[path].count("\n") + 1)
            entries.append({"kind": "failure site", "file": path, "from": first, "to": last,
                            "text": _numbered(files[path], first, last)})
        a, b = _statement_lines(files[path], line)
        statement = "\n".join(rust_adapt._mask_cached(files[path]).splitlines()[a - 1:b])
    if statement:
        called = []
        for c in re.findall(r"(?<![\w.!:])([a-z_]\w*)\s*\(", statement):
            if c not in _KEYWORDS and c != name and c not in called:
                called.append(c)
        for c in called:
            if len([e for e in entries if e["kind"] == "helper source"]) >= MAX_HELPERS:
                break
            for path in ordered:
                span = _fn_span(path, files[path], c)
                if span:
                    first, last = span[0], min(span[1], span[0] + MAX_HELPER_LINES - 1)
                    entries.append({"kind": "helper source", "file": path, "from": first, "to": last,
                                    "text": _numbered(files[path], first, last)})
                    break
    return entries


# --------------------------------------------------------------------------------------------------- the judge


def change_text(change) -> str:
    """What the judge reads of the change: its title, the owner's request, and any redirect's words."""
    text = f"{change.title}\n\n{change.owner_request}"
    if getattr(change, "redirect", None):
        text += f"\n\nLater in the change, the owner said:\n\n{change.redirect.text}"
    return text


def evidence_entries(tests: list[str], outputs: dict[str, str], files: dict[str, str]) -> list[dict]:
    """The numbered entries the judge reads for these tests."""
    entries: list[dict] = []

    def add(test: str, kind: str, lines: list[str], *, first: int = 1, file: str | None = None, label: str = ""):
        e = {"seq": len(entries) + 1, "test": test, "kind": kind, "from": first, "to": first + len(lines) - 1,
             "lines": lines, "label": label}
        if file:
            e["file"] = file
        entries.append(e)
    for t in tests:
        out = outputs[t]
        if len(out) > MAX_OUTPUT:
            out = out[:MAX_OUTPUT] + f" ...[cut: {len(out) - MAX_OUTPUT} more characters]"
        add(t, "failure output", out.rstrip("\n").splitlines())
        compared = compared_json(outputs[t])
        if compared:
            l1, l2, a, b = compared
            add(t, "json difference", json_difference(a, b, labels=(l1, l2)), label=f"{l1} and {l2}")
        for s in source_entries(files, t, panic_site(outputs[t])):
            add(t, s["kind"], files[s["file"]].splitlines()[s["from"] - 1:s["to"]], first=s["from"], file=s["file"],
                label=f"{s['file']} lines {s['from']}-{s['to']}")
    return entries


def render(entries: list[dict]) -> str:
    blocks = []
    for e in entries:
        head = f"[seq {e['seq']}] test `{e['test']}`: {e['kind']}" + (f", {e['label']}" if e["label"] else "")
        body = "\n".join(f"{e['from'] + k:>5}  {line}" for k, line in enumerate(e["lines"]))
        blocks.append(f"{head}\n{body}")
    return "\n\n".join(blocks)


def prompt(change: str, entries: list[dict]) -> str:
    return grading._template("keeping-classify-rust.md", CHANGE=change, EVIDENCE=render(entries))


def check_rulings(structured: Any, tests: list[str], entries: list[dict]) -> list[tuple[str | None, str]]:
    """(test, problem) for each problem in the judge's answer; test is None for one about the answer as a whole."""
    rulings = (structured or {}).get("rulings") if isinstance(structured, dict) else None
    if not isinstance(rulings, list):
        return [(None, "no rulings")]
    by_seq = {e["seq"]: e for e in entries}
    problems: list[tuple[str | None, str]] = []
    seen = set()
    for r in rulings:
        t = r.get("test")
        if t not in tests:
            problems.append((None, f"a ruling for `{t}`, which isn't one of the tests"))
            continue
        if t in seen:
            problems.append((t, f"two rulings for `{t}`"))
        seen.add(t)
        if r.get("classification") not in CLASSES:
            problems.append((t, f"`{t}`: classification {r.get('classification')!r}"))
        if not r.get("evidence"):
            problems.append((t, f"`{t}` cites no evidence"))
        for ev in r.get("evidence") or []:
            e = by_seq.get(ev.get("seq"))
            if not e or e["test"] != t:
                problems.append((t, f"`{t}` cites entry {ev.get('seq')}, which isn't one of its own"))
                continue
            bad = [n for n in ev.get("lines") or [] if not e["from"] <= n <= e["to"]]
            if not ev.get("lines") or bad:
                problems.append((t, f"`{t}` cites lines {bad or '(none)'} of entry {e['seq']}, which has lines "
                                    f"{e['from']}-{e['to']}"))
    for t in tests:
        if t not in seen:
            problems.append((t, f"no ruling for `{t}`"))
    return problems


def _resolve(evidence: list[dict], entries: list[dict]) -> list[dict]:
    by_seq = {e["seq"]: e for e in entries}
    out = []
    for ev in evidence:
        e = by_seq[ev["seq"]]
        out.append({"seq": e["seq"], "kind": e["kind"], **({"file": e["file"]} if "file" in e else {}),
                    "lines": ev["lines"], "text": [e["lines"][n - e["from"]] for n in ev["lines"]]})
    return out


def _harness(reason: str) -> dict:
    return {"classification": "keeping failure", "by": "harness", "reason": reason, "evidence": []}


def classify(result: dict, logs: dict[str, str], files: dict[str, dict[str, str]], change: str, *,
             ask: Callable[[str], tuple[Any, dict]], out: Path | None = None, attempts: int = ATTEMPTS,
             batch_size: int = BATCH) -> dict:
    """Classify every failing held-out test in a keeping result, in place: each target's "failures", and in total
    "new_state_only", "keeping_failures", "share_kept" (passed and new-state-only over tests run), "classified", and
    "classification_cost_usd". ask(prompt) -> (structured answer, usage)."""
    cost = 0.0
    for target, rec in result["targets"].items():
        failed = sorted(n for n, s in rec["tests"].items() if s == "FAILED")
        if not failed:
            continue
        outputs = failure_sections(logs.get(target, ""))
        records: dict[str, dict] = {}
        pending = []
        for t in failed:
            if t in rec.get("reached_adaptation", []):
                records[t] = _harness("The test reached a wildcard arm the adaptation added: a variant the arm added "
                                      "arrived where the test handles only the old ones.")
            elif t not in outputs:
                records[t] = _harness("No failure output to read.")
            else:
                pending.append(t)
        for k in range(0, len(pending), batch_size):
            batch = pending[k:k + batch_size]
            entries = evidence_entries(batch, outputs, files.get(target, {}))
            text = prompt(change, entries)
            tries = []
            for _ in range(attempts):
                structured, usage = ask(text)
                cost += (usage or {}).get("cost_usd") or 0.0
                problems = check_rulings(structured, batch, entries)
                tries.append({"structured": structured, "problems": [p for _, p in problems], "usage": usage})
                if not problems:
                    break
            answer = tries[-1]["structured"]
            listed = answer.get("rulings") if isinstance(answer, dict) else None
            rulings = {r.get("test"): r for r in listed} if isinstance(listed, list) else {}
            broken = {t for t, _ in problems if t is not None}
            for t in batch:
                if t in rulings and t not in broken:
                    r = rulings[t]
                    records[t] = {"classification": r["classification"], "by": "grader", "reason": r["reason"],
                                  "evidence": _resolve(r["evidence"], entries)}
                else:
                    records[t] = _harness("No valid ruling from the grader: " +
                                          "; ".join(p for b, p in problems if b in (t, None)))
                diff = next((e["lines"] for e in entries if e["test"] == t and e["kind"] == "json difference"), None)
                if diff is not None:
                    records[t]["json_difference"] = diff
            if out is not None:
                out.mkdir(parents=True, exist_ok=True)
                (out / f"{target}-b{k // batch_size + 1:02d}.json").write_text(
                    json.dumps({"prompt": text, "entries": entries, "tries": tries}, indent=1))
        rec["failures"] = {t: records[t] for t in failed}
    every = [f for r in result["targets"].values() for f in (r.get("failures") or {}).values()]
    nso = sum(f["classification"] == "new state only" for f in every)
    ran = result["passed"] + result["failed"]
    result.update({"classified": True, "new_state_only": nso, "keeping_failures": result["failed"] - nso,
                   "share_kept": (result["passed"] + nso) / ran if ran else None,
                   "classification_cost_usd": round(cost, 6)})
    return result
