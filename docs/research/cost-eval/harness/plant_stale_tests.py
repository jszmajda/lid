"""The positive control for intent from tests (design.md, "The growth test"): copy one build's tests and plant stale
tests derived from retired items, so the measure can be checked to catch them. Two kinds, reported apart:

- names: the retired rule only in a test's name, docstring, and comment, with an empty assertion. The reader with names
  and comments replaced shouldn't catch these, which checks that that variant works;
- assertions: a test whose assertions encode the retired behaviour, written by a model (Sonnet, through claude -p at
  medium effort) from the rule and a sample of the build's tests, for their style.

    ../plumbing/with-token.sh python3.12 plant_stale_tests.py --id g-bare-1 --change 20 --items RD-12,RD-19

Planted tests are written in the build's own test language and layout, with nothing that marks them as planted, and
are only read, never run. Each kind's copy goes to a Docker volume of its own (ce-pc-<id>-cNN-<kind>, the tests under
/work/app), and which file came from which item to ../runs/<id>/growth/positive-control-cNN/<kind>/index.json, apart
from the copy. A plan for intent_from_tests.py, both kinds as written and with names replaced, goes to
../runs/intent-from-tests/pc-<id>-cNN/plan.json.
"""

from __future__ import annotations

import argparse
import json
import random
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from costeval import simulator, stale_audit  # noqa: E402

IMAGE = "lid-cost-eval-executor:2.1.323"


def _language(tests: dict[str, str]) -> str:
    kinds = Counter()
    for p in tests:
        if re.search(r"\.(test|spec)\.(js|jsx|mjs)$", p):
            kinds["js"] += 1
        elif re.search(r"\.(test|spec)\.(ts|tsx)$", p):
            kinds["ts"] += 1
        elif p.endswith("_test.go"):
            kinds["go"] += 1
        elif p.endswith(".rs"):
            kinds["rust"] += 1
        elif p.endswith(".py"):
            kinds["python"] += 1
    return kinds.most_common(1)[0][0] if kinds else "python"


def _slug(text: str, words: int = 7) -> str:
    return "_".join(re.findall(r"[a-z0-9]+", text.lower())[:words]) or "rule"


NEUTRAL_STEMS = ("checks", "cases", "behaviour", "regressions", "scenarios", "rules", "edge_cases", "more", "extra",
                 "followups", "coverage", "examples")


def neutral_stem(seed: str, item: str) -> str:
    """A file name stem that says nothing of the rule: the readers see file names whatever variant they read."""
    r = random.Random(f"{seed}|{item}|name")
    return f"{r.choice(NEUTRAL_STEMS)}_{r.randrange(100, 1000)}"


def _test_file(lang: str, behavior: str, stem: str = "checks") -> tuple[str, str]:
    """(file name, text) of a stale test for one retired rule: the rule in the test's name, docstring and comment
    only, never in its file name or a string literal, so a reader with names, comments and docstrings replaced sees
    nothing of it."""
    slug, rule = _slug(behavior), behavior.strip().rstrip(".")
    if lang in ("js", "ts"):  # the test's name is its string argument: JS has no other place for one
        name = f"{stem.replace('_', '-')}.test.{lang}"
        return name, (f"test('{rule.replace(chr(39), chr(92) + chr(39))}', () => {{\n"
                      f"  // {rule}.\n  expect(true).toBe(true);\n}});\n")
    if lang == "go":
        camel = "".join(w.capitalize() for w in slug.split("_"))
        return f"{stem}_test.go", (f"package main\n\nimport \"testing\"\n\n// {rule}.\nfunc Test{camel}(t *testing.T) {{\n"
                                    f"\t_ = t\n}}\n")
    if lang == "rust":
        return f"{stem}.rs", f"/// {rule}.\n#[test]\nfn {slug}() {{\n    assert!(true);\n}}\n"
    return f"test_{stem}.py", f'def test_{slug}():\n    """{rule}."""\n    assert True\n'


def plant(tests: dict[str, str], retired: dict[str, str], *, seed: str) -> tuple[dict[str, str], dict]:
    """The build's tests with one stale test per retired item added beside them, and the index of what was planted."""
    lang = _language(tests)
    dirs = Counter(str(Path(p).parent) for p in tests if p.endswith((".py", ".js", ".ts", ".go", ".rs", ".jsx", ".tsx")))
    where = dirs.most_common(1)[0][0] if dirs else "tests"
    out, index = dict(tests), {"kind": "names", "seed": seed, "language": lang, "planted": {}}
    for item in sorted(retired, key=lambda i: random.Random(f"{seed}|{i}").random()):
        name, text = _test_file(lang, retired[item], neutral_stem(seed, item))
        path = f"{where}/{name}" if where != "." else name
        k = 2
        while path in out:
            stem, dot, ext = name.partition(".")
            path = f"{where}/{stem}_{k}{dot}{ext}"
            k += 1
        out[path] = text
        index["planted"][path] = {"item": item, "behavior": retired[item]}
    return out, index


TEMPLATE = HERE / "prompts" / "plant-stale-test.md"
SCHEMA = {"type": "object", "additionalProperties": False, "required": ["file_name", "text"],
          "properties": {"file_name": {"type": "string"}, "text": {"type": "string"}}}
TEST_MARK = {"python": r"\bdef test_\w*\s*\(", "js": r"\b(test|it)\s*\(", "ts": r"\b(test|it)\s*\(",
             "go": r"\bfunc Test\w*\s*\(", "rust": r"#\[test\]"}
GIVEAWAYS = re.compile(r"\bplant(ed)?\b|\bstale\b|\bretired\b|\b[A-Z]{1,4}-\d+\b", re.I)


def _sample(tests: dict[str, str], seed: str, files: int = 3, chars: int = 4000) -> str:
    picks = sorted(tests, key=lambda p: random.Random(f"{seed}|{p}").random())[:files]
    return "\n\n".join(f"--- {p}\n{tests[p][:chars]}" for p in sorted(picks))


def check_written(answer, lang: str) -> list[str]:
    if not isinstance(answer, dict) or not (answer.get("text") or "").strip():
        return ["no test written"]
    problems = []
    if not re.search(TEST_MARK.get(lang, TEST_MARK["python"]), answer["text"]):
        problems.append(f"no {lang} test in it")
    if GIVEAWAYS.search(answer["text"]) or GIVEAWAYS.search(answer.get("file_name") or ""):
        problems.append("it names an item or gives the plant away")
    if "/" in (answer.get("file_name") or "") or not (answer.get("file_name") or "").strip():
        problems.append("a file name with a folder, or none")
    return problems


def plant_assertions(tests: dict[str, str], retired: dict[str, str], *, seed: str, write, attempts: int = 3) -> tuple[dict, dict]:
    """The build's tests with a model-written test per retired item beside them, whose assertions encode the retired
    behaviour; write(prompt) -> (structured answer, cost). An item with no valid answer is left out and recorded."""
    lang = _language(tests)
    dirs = Counter(str(Path(p).parent) for p in tests)
    where = dirs.most_common(1)[0][0] if dirs else "tests"
    sample = _sample(tests, seed)
    out, index = dict(tests), {"kind": "assertions", "seed": seed, "language": lang, "planted": {}, "failed": [], "cost_usd": 0.0}
    for item in sorted(retired, key=lambda i: random.Random(f"{seed}|{i}").random()):
        text = TEMPLATE.read_text(encoding="utf-8").replace("{SAMPLE}", sample).replace("{RULE}", retired[item].strip())
        answer = None
        for _ in range(attempts):
            got, cost = write(text)
            index["cost_usd"] += cost or 0.0
            if not check_written(got, lang):
                answer = got
                break
        if answer is None:
            index["failed"].append(item)
            continue
        # the file name the model chose may name the rule; readers see file names in every variant, so it is replaced
        ext = Path(answer["file_name"]).suffix or ".py"
        lead = "test_" if Path(answer["file_name"]).name.startswith("test_") else ""
        fname = f"{lead}{neutral_stem(seed, item)}{'.test' if answer['file_name'].endswith(('.test' + ext,)) else ''}{ext}"
        path = f"{where}/{fname}" if where != "." else fname
        k = 2
        while path in out:
            stem, dot, rest = fname.partition(".")
            path = f"{where}/{stem}_{k}{dot}{rest}"
            k += 1
        out[path] = answer["text"]
        index["planted"][path] = {"item": item, "behavior": retired[item]}
    index["cost_usd"] = round(index["cost_usd"], 4)
    return out, index


def retired_by(oracle: simulator.Oracle, change: int) -> list[str]:
    """Every row retired at or before this change: what `--items retired` plants."""
    return [i.id for i in oracle.items if i.retired is not None and i.retired <= change]


def main(argv=None) -> int:
    from costeval import rust_grading
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--id", required=True)
    ap.add_argument("--change", type=int, required=True)
    ap.add_argument("--items", required=True, help="the retired items to plant, comma-separated, or `retired` for "
                                                    "every row retired by the change")
    ap.add_argument("--runs", type=Path, default=HERE.parent / "runs")
    ap.add_argument("--seed", default="pc-1")
    ap.add_argument("--names-only", action="store_true", help="plant only the names kind (no model call)")
    args = ap.parse_args(argv)
    meta = json.loads((args.runs / args.id / "trajectory.json").read_text())
    oracle = simulator.parse_oracle((HERE.parent / "seeds" / meta["seed"] / "hidden" / "oracle.md").read_text(encoding="utf-8"))
    behaviors = {i.id: i.behavior for i in oracle.items}
    items = (retired_by(oracle, args.change) if args.items == "retired"
             else [i.strip() for i in args.items.split(",") if i.strip()])
    commit = meta["changes"][str(args.change)]["commit"]
    src = VolumeShell(meta["volumes"]["workspace"])
    listed = src.sh(f"cd /work && git ls-tree -r --name-only {commit}", check=False).split()
    tests = {p: src.sh(f"cd /work && git show {commit}:'{p}'", check=False) for p in listed
             if stale_audit.is_test_or_doc(p) and not p.endswith(".md")}
    rule = {i: behaviors[i] for i in items}
    copies = {"names": plant(tests, rule, seed=args.seed)}
    if not args.names_only:
        from costeval import executor
        from run_trajectory import CLAUDE_CODE, ROLES_VOLUME
        role = executor.RoleSession(image=IMAGE, config_volume=ROLES_VOLUME, model="claude-sonnet-5-5",
                                    claude_code_version=CLAUDE_CODE, effort="medium")

        def write(prompt):
            r = executor.run_role(role, prompt, json_schema=json.dumps(SCHEMA, separators=(",", ":")))
            return r.structured, r.usage.reported_cost_usd or 0.0
        copies["assertions"] = plant_assertions(tests, rule, seed=args.seed, write=write)
    base = args.runs / args.id / "growth" / f"positive-control-c{args.change:02d}"
    inputs = []
    for kind, (planted, index) in copies.items():
        vol = f"ce-pc-{args.id.replace('/', '-')}-c{args.change:02d}-{kind}"
        dest = VolumeShell(vol)
        dest.sh("rm -rf /work/app && mkdir -p /work/app")
        for d in sorted({str(Path(p).parent) for p in planted}):
            dest.sh(f"mkdir -p '/work/app/{d}'")
        rust_grading._write(dest, "/work/app", planted)
        (base / kind).mkdir(parents=True, exist_ok=True)
        (base / kind / "index.json").write_text(json.dumps({**index, "volume": vol, "root": "app", "commit": commit}, indent=1))
        oracle_ref = {"kind": "benchtime", "seed": meta["seed"], "change": args.change}
        for neutral in (False, True):
            inputs.append({"label": f"pc-{kind}" + ("-neutral" if neutral else ""), "group": f"positive control: {kind}",
                           "source": "tests", "neutral": neutral, "volume": vol, "root": "app", "oracle": oracle_ref,
                           "verdicts": f"runs/{args.id}/grading/change-{args.change:02d}", "baseline": "brief"})
        print(f"{kind}: {len(index['planted'])} stale tests planted among {len(tests)} in {vol}")
    inputs.append({"label": "brief", "group": "brief", "source": "brief", "brief": f"seeds/{meta['seed']}/brief.md",
                   "oracle": {"kind": "benchtime", "seed": meta["seed"], "change": args.change}})
    name = f"pc-{args.id.replace('/', '-')}-c{args.change:02d}"
    plan = args.runs / "intent-from-tests" / name / "plan.json"
    plan.parent.mkdir(parents=True, exist_ok=True)
    plan.write_text(json.dumps({"name": name, "inputs": inputs}, indent=1))
    print(f"plan for the readers: {plan}")
    return 0


class VolumeShell:
    """Commands in a container with a Docker volume at /work, as the grading checkpoints run them."""

    def __init__(self, volume: str, image: str = IMAGE):
        self.volume, self.image = volume, image

    def sh(self, script: str, stdin: str | None = None, check: bool = True) -> str:
        p = subprocess.run(["docker", "run", "--rm", "-i", "-v", f"{self.volume}:/work", "-w", "/work", self.image,
                            "sh", "-c", script], input=stdin, capture_output=True, text=True)
        if check and p.returncode != 0:
            raise RuntimeError(f"failed ({p.returncode}): {script[:120]}: {p.stderr[-300:]}")
        return p.stdout


if __name__ == "__main__":
    sys.exit(main())
