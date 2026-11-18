"""Build the falsification test's repository variants from one Clowder commit (design.md, "Later seeds and variants").

    python3.12 clowder_variants.py --repo /Users/jess/src/clowder --commit 86db995 --seed v1 \\
        --out ../runs/clowder-variants/v1 --volumes --cargo-test

Each variant is a single-commit git repository with fresh history, so no arm can recover what was removed from
`git log`. Three are built:

- **held-out slice** (removed from all three): a seeded random share (15%) of the test files under crates/*/tests/,
  drawn per directory, saved aside under `held-out/` for grading keeping. A removed module's `mod` line goes from its
  directory's `main.rs`, so the build stays green.
- **full**: everything else, docs and agent instruction files included.
- **lid**: the same files as full. The LID arm's plugin is installed by the arm's own setup, as for other seeds; the
  repository's AGENTS.md already carries its LID directives. Full and lid are loaded as colocated jj repositories,
  since the project's instructions ask for jj; stripped stays plain git.
- **stripped**: no docs/, no agent instruction files (AGENTS.md, CLAUDE.md, GEMINI.md, .claude/), no LID tooling
  (a script outside crates/ that reads `@spec` annotations or docs/intent), no README paragraph about LID or linking
  into docs/, no `@spec` annotations and no other citation of a spec ID (the IDs' prefixes are read from the specs),
  and tests thinned at random, whole files, per directory, until test lines are about `--ratio` (0.6) times the
  non-test source lines.

Writes, under --out: `<variant>/` (each repository), `held-out/` (the removed test files at their paths, and the
original helper modules they use), and `manifest.json` (what was removed and stripped, sizes in bytes and estimated
tokens by class, each variant's commit and volume, and with --cargo-test each variant's build and test results).
--volumes loads each repository into a Docker volume (`ce-cv-<seed>-<variant>`) for fork runs.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
IMAGE = "lid-cost-eval-executor-rust:2.1.323"
IDENTITY = ("Lab Owner", "owner@example.invalid")  # the workspaces' neutral git identity (trajectory.GIT_IDENTITY)
DATE = "2026-01-01T00:00:00+00:00"  # a fixed date, so a variant's commit hash depends only on its files
HELD_OUT_SHARE = 0.15
RATIO = 0.6
AGENT_FILES = ("AGENTS.md", "CLAUDE.md", "GEMINI.md")
LID_MARKERS = ("@spec", "docs/intent")


# --------------------------------------------------------------------------------------------- the source tree


@dataclass
class Tree:
    commit: str
    files: dict[str, bytes]
    symlinks: dict[str, str] = field(default_factory=dict)
    executables: set[str] = field(default_factory=set)


@dataclass
class Variant:
    name: str
    files: dict[str, bytes]
    symlinks: dict[str, str]
    executables: set[str]
    report: dict = field(default_factory=dict)
    vcs: str = "git"  # "jj": loaded as a colocated jj repository, as the project's own instructions expect


def _git(repo: Path, *args: str, stdin: bytes | None = None) -> bytes:
    return subprocess.run(["git", "-C", str(repo), *args], input=stdin, check=True, capture_output=True).stdout


def read_tree(repo: Path | str, commit: str) -> Tree:
    """Every tracked file at the commit: regular files, symlinks (as their targets), and which are executable."""
    repo = Path(repo)
    commit = _git(repo, "rev-parse", commit).decode().strip()
    entries = []
    for rec in _git(repo, "ls-tree", "-r", "-z", commit).split(b"\0"):
        if not rec:
            continue
        meta, path = rec.split(b"\t", 1)
        mode, kind, sha = meta.decode().split()
        if kind == "blob":
            entries.append((mode, sha, path.decode()))
    out = _git(repo, "cat-file", "--batch", stdin="".join(f"{sha}\n" for _, sha, _ in entries).encode())
    tree, i = Tree(commit=commit, files={}), 0
    for mode, sha, path in entries:
        nl = out.index(b"\n", i)
        size = int(out[i:nl].split()[2])
        data = out[nl + 1:nl + 1 + size]
        i = nl + 1 + size + 1
        if mode == "120000":
            tree.symlinks[path] = data.decode()
        else:
            tree.files[path] = data
            if mode == "100755":
                tree.executables.add(path)
    return tree


def _text(data: bytes) -> str | None:
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return None


def _lines(data: bytes) -> int:
    return data.count(b"\n") + (1 if data and not data.endswith(b"\n") else 0)


# ------------------------------------------------------------------------------------------------- spec IDs


def spec_id_pattern(tree: Tree) -> re.Pattern:
    """Spec IDs as the project's specs write them (**PREFIX-NNN**): their prefixes, then three or more digits and an
    optional letter."""
    prefixes = set()
    for path, data in tree.files.items():
        if path.endswith("-specs.md") and (text := _text(data)):
            prefixes |= {m.group(1) for m in re.finditer(r"\*\*([A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*?)-\d{3,}[a-z]?\*\*", text)}
    if not prefixes:
        return re.compile(r"(?!)")
    alt = "|".join(re.escape(p) for p in sorted(prefixes, key=lambda p: (-len(p), p)))
    return re.compile(rf"\b(?:{alt})-\d{{3,}}[a-z]?\b")


_COMMENT = ("//", "/*", "*")


def strip_spec_ids(text: str, pattern: re.Pattern) -> tuple[str, dict[str, int]]:
    """Remove `@spec` annotations and every other citation of a spec ID, keeping the prose around them.

    A line that is only an annotation goes. An annotation at the end of prose or code goes, and the rest stays. A
    citation goes with what only frames it: parentheses around it ("(X-001)", "(X-001 amended)"), a lead-in ("see",
    "per"), a label colon ("X-001: ..."); "X-001's rule" becomes "the rule". A comment left with no words goes."""
    ident = pattern.pattern
    lst = rf"(?:{ident})(?:\s*(?:,|\band\b|&|/)\s*(?:{ident}))*"
    counts = {"annotation lines": 0, "lines changed": 0, "lines dropped": 0}
    out = []
    for line in text.splitlines(keepends=True):
        if "@spec" not in line and not pattern.search(line):
            out.append(line)
            continue
        body, nl = (line[:-1], "\n") if line.endswith("\n") else (line, "")
        stripped = body.strip()
        if re.match(r"^(?:///|//!|//)\s*@spec\b", stripped):
            counts["annotation lines"] += 1
            continue
        new = re.sub(rf"\s*@spec\s+{lst}", "", body)
        new = re.sub(r"\s*@spec\b\s*$", "", new)  # its IDs wrapped to the next line, which goes as a citation

        def paren(m: re.Match) -> str:
            rest = re.sub(r"[^\w\s]", " ", m.group("rest") or "").split()
            return "" if len(rest) <= 2 else m.group(0).replace(m.group("ids"), "").replace("( ", "(")

        new = re.sub(rf"\s*\(\s*(?:see\s+|per\s+|cf\.?\s+)?(?P<ids>{lst})(?P<rest>[^()]*)\)", paren, new)
        new = re.sub(rf"{lst}'s\b", "the", new)
        new = re.sub(rf"{lst}\s*:\s*", "", new)
        new = re.sub(rf"\b(?:[Ss]ee|[Pp]er|cf\.?|as in|under)\s+{lst}", "", new)
        new = re.sub(lst, "", new)
        lead = len(new) - len(new.lstrip())
        rest = re.sub(r" {2,}", " ", new[lead:])
        rest = re.sub(r" +([,.;:)])", r"\1", rest).replace("()", "").replace("( )", "")
        new = (new[:lead] + rest).rstrip()
        is_comment = stripped.startswith(_COMMENT)
        if is_comment:
            m = re.match(r"^(\s*(?:///|//!|//|/\*|\*))\s*(.*)$", new)
            head, words = m.group(1), m.group(2)
            words = re.sub(r"[\s\u2014\u2013:;,]+$", "", re.sub(r"^[\s\u2014\u2013:;,.]+", "", words))
            if not re.search(r"\w", words):
                counts["lines dropped"] += 1
                continue
            new = f"{head} {words}"
        if not is_comment:
            new = re.sub(r"\s*//[!/]?\s*[.,;:]*\s*$", "", new)  # a trailing comment left empty
            if not new.strip() and stripped:
                counts["lines dropped"] += 1
                continue
        counts["lines changed"] += 1
        out.append(new + nl)
    return "".join(out), counts


# ------------------------------------------------------------------------------------------------ test files


def cfg_test_lines(text: str) -> int:
    """Lines of `#[cfg(test)]` items in a source file: from the attribute to the item's end (its closing brace, or
    its semicolon), skipping braces inside strings, character literals, and comments."""
    total, i = 0, 0
    while (k := text.find("#[cfg(test)]", i)) >= 0:
        end = _item_end(text, k + len("#[cfg(test)]"))
        total += text.count("\n", k, end) + 1
        i = end
    return total


def _item_end(text: str, i: int) -> int:
    depth, n = 0, len(text)
    while i < n:
        c = text[i]
        if text.startswith("//", i):
            i = text.find("\n", i)
            i = n if i < 0 else i
            continue
        if text.startswith("/*", i):
            j = text.find("*/", i + 2)
            i = n if j < 0 else j + 2
            continue
        m = re.match(r'b?r(#*)"', text[i:i + 12])
        if m:
            close = '"' + m.group(1)
            j = text.find(close, i + len(m.group(0)))
            i = n if j < 0 else j + len(close)
            continue
        if c == '"' or text.startswith('b"', i):
            j = i + (2 if c == "b" else 1)
            while j < n and text[j] != '"':
                j += 2 if text[j] == "\\" else 1
            i = j + 1
            continue
        if c == "'":
            if text.startswith("'\\", i):
                j = text.find("'", i + 2)
                i = n if j < 0 else j + 1
                continue
            if i + 2 < n and text[i + 2] == "'":
                i += 3
                continue
            i += 1  # a lifetime
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i
        elif c == ";" and depth == 0:
            return i
        i += 1
    return n


def _is_test_file(path: str) -> bool:
    return bool(re.fullmatch(r"crates/[^/]+/tests/[^/]+\.rs", path)
                or re.fullmatch(r"crates/[^/]+/tests/[^/]+/(?!main\.rs$)[^/]+\.rs", path))


def test_files(files) -> list[str]:
    """Test files that can be removed whole: a test target of its own under crates/*/tests/, or a module directly in
    one of its directories (not that directory's main.rs, and not a helper module's own folder, such as common/)."""
    return sorted(p for p in files if _is_test_file(p))


def _stratum(path: str) -> str:
    return path.rsplit("/", 1)[0]


def _by_stratum(paths) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for p in sorted(paths):
        out.setdefault(_stratum(p), []).append(p)
    return out


READS_DOCS = re.compile(r'(?:include_(?:str|bytes)!|read_to_string)\s*\(\s*"[^"]*\bdocs/')


def reads_docs(text: str) -> bool:
    """A test that reads the project's docs (checking a design table against the code, say) can't build without them."""
    return bool(READS_DOCS.search(text))


def choose_held_out(tree: Tree, *, share: float = HELD_OUT_SHARE, seed: str) -> list[str]:
    """A seeded random share of each directory's test files, rounded half up. Files that read the docs are never
    held out: they would fail to build against the stripped variant for want of the docs, not of the behaviour."""
    held = []
    eligible = [p for p in test_files(tree.files) if not reads_docs(tree.files[p].decode(errors="replace"))]
    for stratum, paths in _by_stratum(eligible).items():
        k = int(share * len(paths) + 0.5)
        held += random.Random(f"{seed}|held-out|{stratum}").sample(paths, k)
    return sorted(held)


def _drop_modules(files: dict[str, bytes], removed: list[str]) -> None:
    """Take each removed module's `mod` line (and attributes just above it) out of its directory's main.rs."""
    for path in removed:
        if not re.fullmatch(r"crates/[^/]+/tests/[^/]+/[^/]+\.rs", path):
            continue  # a test target of its own: nothing declares it
        main = f"{_stratum(path)}/main.rs"
        if main not in files:
            continue
        stem = Path(path).stem
        lines = files[main].decode().splitlines(keepends=True)
        for k, line in enumerate(lines):
            if re.fullmatch(rf"\s*(?:pub\s+)?mod\s+{re.escape(stem)}\s*;\s*", line.rstrip("\n")):
                j = k
                while j > 0 and lines[j - 1].strip().startswith("#["):
                    j -= 1
                del lines[j:k + 1]
                break
        files[main] = "".join(lines).encode()


def drop_doc_tests(files: dict[str, bytes]) -> list[str]:
    """Remove the tests that read the docs: whole test files, and single `#[test]` functions in source files (with
    their doc comments and attributes). Returns what went, as paths or path::function."""
    gone = []
    for p in test_files(files):
        if reads_docs(files[p].decode(errors="replace")):
            gone.append(p)
            del files[p]
    _drop_modules(files, list(gone))
    for p in sorted(files):
        if not p.endswith(".rs") or not p.startswith("crates/"):
            continue
        text = files[p].decode(errors="replace")
        while (m := READS_DOCS.search(text)):
            attr = text.rfind("#[test]", 0, m.start())
            fn = re.compile(r"\bfn\s+(\w+)").search(text, attr) if attr >= 0 else None
            if fn is None or fn.start() > m.start():
                raise ValueError(f"{p}: reads the docs outside a test function")
            end = _item_end(text, fn.end())
            start = text.rfind("\n", 0, attr) + 1
            while start > 0:  # the item's doc comments and other attributes above it
                prev = text.rfind("\n", 0, start - 1) + 1
                if not text[prev:start].strip().startswith(("///", "#[", "//")):
                    break
                start = prev
            stop = text.find("\n", end)
            text = text[:start] + text[(len(text) if stop < 0 else stop + 1):]
            gone.append(f"{p}::{fn.group(1)}")
        files[p] = text.encode()
    return sorted(gone)


def _source_lines(files: dict[str, bytes]) -> int:
    n = 0
    for p, d in files.items():
        if p.endswith(".rs") and "/tests/" not in p and p.startswith("crates/"):
            n += _lines(d) - cfg_test_lines(d.decode(errors="replace"))
    return n


def _test_lines(files: dict[str, bytes]) -> int:
    n = sum(_lines(d) for p, d in files.items() if p.endswith(".rs") and "/tests/" in p and p.startswith("crates/"))
    return n + sum(cfg_test_lines(d.decode(errors="replace")) for p, d in files.items()
                   if p.endswith(".rs") and "/tests/" not in p and p.startswith("crates/"))


def thin_tests(files: dict[str, bytes], *, ratio: float, seed: str) -> list[str]:
    """Test files to remove so test lines come to about `ratio` times the non-test source lines. Each directory's
    test files get a share of the budget in proportion to their lines, and are taken in a seeded random order, each
    kept if it brings the directory closer to its share."""
    candidates = test_files(files)
    fixed = _test_lines(files) - sum(_lines(files[p]) for p in candidates)
    budget = max(0.0, ratio * _source_lines(files) - fixed)
    total = sum(_lines(files[p]) for p in candidates) or 1
    removed = []
    for stratum, paths in _by_stratum(candidates).items():
        share = budget * sum(_lines(files[p]) for p in paths) / total
        order = list(paths)
        random.Random(f"{seed}|thin|{stratum}").shuffle(order)
        kept = 0
        for p in order:
            n = _lines(files[p])
            if abs(kept + n - share) < abs(kept - share):
                kept += n
            else:
                removed.append(p)
    return sorted(removed)


# ---------------------------------------------------------------------------------------------- the variants


README_LID = re.compile(r"Linked-Intent|linked-intent|\bLID\b|jszmajda/lid|@spec|docs/intent|\]\(docs/|AGENTS\.md|CLAUDE\.md"
                        r"|spec-test-coverage|\barrow\b(?!\s+keys?\b)", re.I)


def _readme(text: str) -> tuple[str, int]:
    """The README without what describes LID: each paragraph that mentions it, LID, its specs, the docs, or the agent
    instruction files, and each such line of a code block; then any heading left with nothing under it. A section
    named for the arrow keeps its remaining content under "Testing"."""
    blocks = [b for b in re.split(r"\n\s*\n", text.strip("\n"))]
    kept, dropped = [], 0
    for b in blocks:
        if b.startswith("```"):
            lines = b.split("\n")
            inner = [l for l in lines[1:-1] if not README_LID.search(l)]
            dropped += len(lines) - 2 - len(inner)
            if inner:
                kept.append("\n".join([lines[0], *inner, lines[-1]]))
        elif b.startswith("#"):
            kept.append("## Testing" if README_LID.search(b) and b.startswith("## ") else b)
        elif re.match(r"\s*(?:[-*+]|\d+\.)\s", b):
            # a list: each item on its own, with any lines that continue it
            items = re.split(r"\n(?=\s*(?:[-*+]|\d+\.)\s)", b)
            left = [i for i in items if not README_LID.search(i)]
            dropped += len(items) - len(left)
            if left:
                kept.append("\n".join(left))
        elif README_LID.search(b):
            dropped += 1
        else:
            kept.append(b)
    out = []
    for k, b in enumerate(kept):
        level = len(b) - len(b.lstrip("#")) if b.startswith("#") else 0
        nxt = kept[k + 1] if k + 1 < len(kept) else None
        nxt_level = len(nxt) - len(nxt.lstrip("#")) if nxt and nxt.startswith("#") else 0
        if level and (nxt is None or (nxt_level and nxt_level <= level)):
            continue  # a heading with nothing left under it
        out.append(b)
    return "\n\n".join(out) + "\n", dropped


def plan_variants(tree: Tree, *, held_out: list[str], seed: str, ratio: float = RATIO) -> dict[str, Variant]:
    base = {p: d for p, d in tree.files.items() if p not in held_out}
    _drop_modules(base, held_out)
    full = Variant("full", dict(base), dict(tree.symlinks), set(tree.executables) - set(held_out),
                   {"held_out": sorted(held_out)}, vcs="jj")
    lid = Variant("lid", dict(base), dict(tree.symlinks), set(full.executables), dict(full.report), vcs="jj")

    files = dict(base)
    gone = {"docs": [], "agent files": [], "lid tooling": []}
    for p in list(files):
        top = p.split("/", 1)[0]
        if top == "docs":
            gone["docs"].append(p)
        elif p in AGENT_FILES or top == ".claude":
            gone["agent files"].append(p)
        elif not p.startswith("crates/") and not p.endswith(".md") and (t := _text(files[p])) and any(m in t for m in LID_MARKERS):
            gone["lid tooling"].append(p)
        else:
            continue
        del files[p]
    symlinks = {}
    for p, target in tree.symlinks.items():
        resolved = os.path.normpath(os.path.join(os.path.dirname(p), target))
        if p in AGENT_FILES or resolved in AGENT_FILES or resolved.split("/", 1)[0] in ("docs", ".claude"):
            gone["agent files"].append(p)
        else:
            symlinks[p] = target
    pattern = spec_id_pattern(tree)
    stripped_counts = {"annotation lines": 0, "lines changed": 0, "lines dropped": 0, "files": 0}
    readme_paragraphs = 0
    for p, d in list(files.items()):
        t = _text(d)
        if t is None:
            continue
        if p == "README.md":
            t, readme_paragraphs = _readme(t)
        new, counts = strip_spec_ids(t, pattern)
        if new != _text(d):
            stripped_counts["files"] += 1
            for k, v in counts.items():
                stripped_counts[k] += v
            files[p] = new.encode()
    reading_docs = drop_doc_tests(files)
    thinned = thin_tests(files, ratio=ratio, seed=seed)
    for p in thinned:
        del files[p]
    _drop_modules(files, thinned)
    stripped = Variant("stripped", files, symlinks, set(tree.executables) & set(files),
                       {"held_out": sorted(held_out), "removed": {k: sorted(v) for k, v in gone.items()},
                        "readme_paragraphs_removed": readme_paragraphs, "spec_ids": stripped_counts,
                        "spec_id_pattern": pattern.pattern, "tests_reading_docs": reading_docs, "tests_thinned": thinned,
                        "source_lines": _source_lines(files), "test_lines": _test_lines(files), "ratio_target": ratio})
    stripped.report["ratio"] = round(stripped.report["test_lines"] / max(1, stripped.report["source_lines"]), 3)
    for v in (full, lid):
        v.report.update(source_lines=_source_lines(v.files), test_lines=_test_lines(v.files))
        v.report["ratio"] = round(v.report["test_lines"] / max(1, v.report["source_lines"]), 3)
    return {"full": full, "lid": lid, "stripped": stripped}


def _class(path: str) -> str:
    if "/tests/" in f"/{path}":
        return "tests"
    if path.endswith(".md") or path.startswith("docs/"):
        return "docs"
    if path.endswith(".rs"):
        return "source"
    return "other"


def variant_sizes(v: Variant) -> dict[str, dict]:
    """Bytes, lines, files, and tokens (estimated as bytes / 4, as context telemetry does) by class: source (Rust
    outside tests/), tests (anything under a tests/ directory), docs (Markdown and docs/), and other."""
    out = {k: {"bytes": 0, "lines": 0, "files": 0} for k in ("source", "tests", "docs", "other")}
    for p, d in v.files.items():
        c = out[_class(p)]
        c["bytes"] += len(d)
        c["lines"] += _lines(d)
        c["files"] += 1
    for c in out.values():
        c["tokens_est"] = c["bytes"] // 4
    return out


def write_repo(v: Variant, out: Path) -> str:
    """Write the variant as a one-commit git repository at `out`; returns the commit. The same files give the same
    commit."""
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    for p, d in v.files.items():
        f = out / p
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(d)
        if p in v.executables:
            f.chmod(0o755)
    for p, target in v.symlinks.items():
        (out / p).parent.mkdir(parents=True, exist_ok=True)
        os.symlink(target, out / p)
    env = {**os.environ, "GIT_AUTHOR_NAME": IDENTITY[0], "GIT_AUTHOR_EMAIL": IDENTITY[1], "GIT_COMMITTER_NAME": IDENTITY[0],
           "GIT_COMMITTER_EMAIL": IDENTITY[1], "GIT_AUTHOR_DATE": DATE, "GIT_COMMITTER_DATE": DATE}
    git = lambda *a: subprocess.run(["git", "-C", str(out), "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null", *a],  # noqa: E731
                                    check=True, capture_output=True, env=env, text=True).stdout.strip()
    git("init", "-q", "-b", "main")
    git("add", "-A")
    git("commit", "-q", "-m", "Start")
    return git("rev-parse", "HEAD")


def held_out_helpers(tree: Tree, held_out: list[str]) -> dict[str, bytes]:
    """The held-out files and, beside them, each test directory's helper modules as they were (main.rs's other
    modules, such as common/), so grading can build them against the original helpers."""
    out = {p: tree.files[p] for p in held_out}
    dirs = {_stratum(p) for p in held_out}
    for p, d in tree.files.items():
        if any(p.startswith(d_ + "/") for d_ in dirs) and p not in test_files(tree.files):
            out[p] = d
    return out


# -------------------------------------------------------------------------------------------- docker and cargo


def load_volume(repo_dir: Path, volume: str, image: str = IMAGE, *, jj: bool = False, runner=subprocess.run) -> None:
    """Replace the volume's contents with the repository (its working tree and .git), owned by the image's user. With
    jj, the repository becomes a colocated jj repository, made by the image's own jj."""
    tar = subprocess.run(["tar", "-C", str(repo_dir), "-cf", "-", "."], check=True, capture_output=True).stdout
    script = "find /work -mindepth 1 -delete && tar -x -C /work"
    if jj:
        script += " && cd /work && jj git init --colocate >/dev/null 2>&1"
    runner(["docker", "run", "--rm", "-i", "-v", f"{volume}:/work", image, "sh", "-c", script],
           input=tar, check=True, capture_output=True)


TEST_RESULT = re.compile(r"test result: (\w+)\. (\d+) passed; (\d+) failed; (\d+) ignored")


def parse_cargo_test(output: str, exit_code: int) -> dict:
    """Totals from `cargo test` output, the failing tests' names, and whether anything failed to compile."""
    passed = failed = ignored = 0
    for m in TEST_RESULT.finditer(output):
        passed, failed, ignored = passed + int(m.group(2)), failed + int(m.group(3)), ignored + int(m.group(4))
    failing = sorted(set(re.findall(r"(?m)^test (\S+) \.\.\. FAILED$", output)))
    compile_errors = re.findall(r"(?m)^error(?:\[E\d+\])?: .*$", output)
    compile_failed = bool(re.search(r"(?m)^error: could not compile", output))
    targets = len(TEST_RESULT.findall(output))
    return {"ok": exit_code == 0 and failed == 0 and targets > 0, "exit_code": exit_code, "passed": passed,
            "failed": failed, "ignored": ignored, "failing": failing, "compile_failed": compile_failed,
            "compile_errors": compile_errors[:20], "targets": targets}


def cargo_test(volume: str, *, image: str = IMAGE, target_volume: str = "ce-cv-target", runner=subprocess.run,
               args: str = "--workspace") -> tuple[dict, str]:
    """Run the variant's tests in a copy of the volume (so no target/ lands in it), with no network. The build output
    goes to a target volume shared across variants, handed to the image's user first (Docker creates it root-owned)."""
    runner(["docker", "run", "--rm", "--user", "root", "-v", f"{target_volume}:/target", image, "chown", "agent:agent",
            "/target"], capture_output=True, text=True)
    script = (f"cp -a /src /tmp/w && cd /tmp/w && CARGO_TARGET_DIR=/target timeout 3000 cargo test --offline {args} 2>&1; "
              "echo EXIT=$?")
    p = runner(["docker", "run", "--rm", "--network", "none", "-v", f"{volume}:/src:ro", "-v", f"{target_volume}:/target",
                image, "sh", "-c", script], capture_output=True, text=True)
    out = p.stdout + p.stderr
    m = re.search(r"EXIT=(\d+)\s*$", out)
    return parse_cargo_test(out, int(m.group(1)) if m else p.returncode), out


# ------------------------------------------------------------------------------------------------------ main


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", type=Path, required=True)
    ap.add_argument("--commit", default="HEAD")
    ap.add_argument("--seed", required=True, help="the seed for the held-out draw and the thinning; names the volumes")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--held-out-share", type=float, default=HELD_OUT_SHARE)
    ap.add_argument("--ratio", type=float, default=RATIO)
    ap.add_argument("--volumes", action="store_true", help="load each variant into a Docker volume")
    ap.add_argument("--cargo-test", action="store_true", help="run each variant's tests in the Rust image")
    ap.add_argument("--image", default=IMAGE)
    args = ap.parse_args(argv)
    tree = read_tree(args.repo, args.commit)
    held = choose_held_out(tree, share=args.held_out_share, seed=args.seed)
    variants = plan_variants(tree, held_out=held, seed=args.seed, ratio=args.ratio)
    args.out.mkdir(parents=True, exist_ok=True)
    hdir = args.out / "held-out"
    shutil.rmtree(hdir, ignore_errors=True)
    for p, d in held_out_helpers(tree, held).items():
        (hdir / p).parent.mkdir(parents=True, exist_ok=True)
        (hdir / p).write_bytes(d)
    manifest = {"source_commit": tree.commit, "seed": args.seed, "held_out_share": args.held_out_share,
                "held_out": held, "variants": {}}
    for name, v in variants.items():
        head = write_repo(v, args.out / name)
        entry = {"commit": head, "vcs": v.vcs, "report": v.report, "sizes": variant_sizes(v), "files": len(v.files)}
        if args.volumes or args.cargo_test:
            entry["volume"] = f"ce-cv-{args.seed}-{name}"
            load_volume(args.out / name, entry["volume"], args.image, jj=v.vcs == "jj")
        if args.cargo_test:
            result, log = cargo_test(entry["volume"], image=args.image)
            (args.out / f"cargo-test-{name}.log").write_text(log)
            entry["cargo_test"] = result
            print(f"{name}: {result['passed']} passed, {result['failed']} failed, compile failed {result['compile_failed']}",
                  flush=True)
        manifest["variants"][name] = entry
    if args.cargo_test:
        subprocess.run(["docker", "volume", "rm", "-f", "ce-cv-target"], capture_output=True)
    (args.out / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")
    for name, e in manifest["variants"].items():
        s = e["sizes"]
        print(f"{name}: {e['commit'][:12]} files {e['files']}, tokens source {s['source']['tokens_est']:,} tests "
              f"{s['tests']['tokens_est']:,} docs {s['docs']['tokens_est']:,}, test/source lines {e['report']['ratio']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
