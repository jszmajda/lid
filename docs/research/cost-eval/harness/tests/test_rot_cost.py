"""Tests for the working-around-rot measure (costeval/rot_cost.py, rot_cost.py): what each reliance and course fork's
agent spent, the files it read, and which of them the stale-intent audit flagged for its course change.

Run from the harness folder: python3.12 -m unittest discover -s tests
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from costeval import rot_cost  # noqa: E402


def write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(obj if isinstance(obj, str) else json.dumps(obj))


def usage(inp=1, read=100, write_=10):
    return {"input_tokens": inp, "cache_read_input_tokens": read, "cache_creation_input_tokens": write_, "output_tokens": 5}


def assistant(msg_id, blocks):
    return {"type": "assistant", "message": {"id": msg_id, "role": "assistant", "content": blocks, "usage": usage(),
                                             "context_management": None}, "parent_tool_use_id": None, "session_id": "s1"}


def tool_use(tid, name, inp):
    return {"type": "tool_use", "id": tid, "name": name, "input": inp}


def tool_result(tid, content, extra=None):
    e = {"type": "user", "message": {"role": "user", "content": [{"type": "tool_result", "tool_use_id": tid,
                                                                  "content": content, "is_error": False}]},
         "parent_tool_use_id": None, "session_id": "s1"}
    if extra is not None:
        e["tool_use_result"] = extra
    return e


def read(tid, path):
    return [assistant(f"m-{tid}", [tool_use(tid, "Read", {"file_path": path})]),
            tool_result(tid, "1\tx", {"type": "text", "file": {"filePath": path, "content": "x", "startLine": 1,
                                                                "numLines": 1, "totalLines": 1}})]


def bash(tid, cmd):
    return [assistant(f"m-{tid}", [tool_use(tid, "Bash", {"command": cmd})]),
            tool_result(tid, "out", {"stdout": "out", "stderr": ""})]


def stream(*events) -> str:
    init = {"type": "system", "subtype": "init", "cwd": "/work", "session_id": "s1"}
    return "\n".join(json.dumps(e) for e in (init, *events)) + "\n"


def turn_record(name, inp, cache_read):
    return {"stream": name, "usage": {"models": {"m": {"input": inp, "output": 5, "cache_read": cache_read,
                                                        "cache_write_5m": 0, "cache_write_1h": 7}},
                                      "reported_cost_usd": 0.1}}


def reliance_fork(runs: Path, tid: str, course: int, k: int, *, at: int, cost: float, streams: list[str],
                  rounds=None) -> Path:
    fork = runs / tid / "course-forks" / f"c{course:02d}-reliance-{k}"
    write(fork / "trajectory.json", {"id": f"{tid}/course-forks/{fork.name}", "kind": "reliance", "course": course,
                                     "change": at, "at": at, "lag": at - course, "changes": {"reliance": {
                                         "rounds": rounds or len(streams), "agent_cost_usd": cost, "minutes": 2.5}}})
    cdir = fork / "change-reliance"
    for i, s in enumerate(streams):
        write(cdir / f"turn-{i:02d}.stream.jsonl", s)
    write(cdir / "change.json", {"turns": [turn_record(f"turn-{i:02d}.stream.jsonl", 3 + i, 1000 * (i + 1))
                                           for i in range(len(streams))]})
    return fork


def course_fork(runs: Path, tid: str, course: int, k: int, *, cost: float, streams: list[str], audit: dict) -> Path:
    fork = runs / tid / "course-forks" / f"c{course:02d}-course-{k}"
    write(fork / "trajectory.json", {"id": f"{tid}/course-forks/{fork.name}", "kind": "course", "course": course,
                                     "change": course, "at": None, "lag": None, "changes": {str(course): {
                                         "rounds": len(streams), "agent_cost_usd": cost, "minutes": 9.0}}})
    cdir = fork / f"change-{course:02d}"
    for i, s in enumerate(streams):
        write(cdir / f"turn-{i:02d}.stream.jsonl", s)
    write(cdir / "change.json", {"turns": [turn_record(f"turn-{i:02d}.stream.jsonl", 2, 500) for i in range(len(streams))]})
    write(fork / "growth" / "stale-audit.json", audit)
    return fork


def audit_of(named=None, **verdicts):
    """One course change's audit result: file -> verdict (README_md for README.md, docs__a_md for docs/a.md)."""
    files = {p.replace("__", "/").replace("_md", ".md").replace("_py", ".py"): {"verdict": v} for p, v in verdicts.items()}
    files |= {p: {"verdict": v} for p, v in (named or {}).items()}
    count = lambda v: sum(f["verdict"] == v for f in files.values())  # noqa: E731
    return {"kind": "reversal", "files": files, "current": count("current"), "stale": count("stale"),
            "mixed": count("mixed"), "unrelated": count("unrelated"), "no_ruling": 0}


TWO_TURNS = [
    stream(*read("t1", "/work/docs/intent/catalog.md"), *read("t2", "/home/agent/.claude/skills/x/SKILL.md"),
           assistant("m-g", [tool_use("t3", "Grep", {"pattern": "live", "path": "/work/tests/test_api.py"})]),
           tool_result("t3", "tests/test_api.py:3: live")),
    stream(*bash("t4", "cat tests/test_versions.py | head -20; sed -n 1,5p README.md"), *read("t5", "/work/docs/intent/catalog.md")),
]


class MeasuresTest(unittest.TestCase):
    def test_a_forks_cost_turns_time_tokens_and_the_distinct_repository_files_it_read(self):
        runs = Path(tempfile.mkdtemp()) / "runs"
        fork = reliance_fork(runs, "g-bare-1", 2, 1, at=4, cost=0.42, streams=TWO_TURNS)
        m = rot_cost.measures(fork)
        self.assertEqual((m["kind"], m["course"], m["at"], m["lag"]), ("reliance", 2, 4, 2))
        self.assertEqual((m["agent_cost_usd"], m["turns"], m["minutes"]), (0.42, 2, 2.5))
        self.assertEqual((m["input_tokens"], m["cache_read_tokens"], m["cache_write_tokens"]), (3 + 4, 1000 + 2000, 14))
        self.assertEqual(m["model_calls"], 5)  # main-thread API calls over both turns
        # Read and Bash reads of a named file, inside the repository, once each; a search doesn't count as reading
        self.assertEqual(m["files_read"], ["README.md", "docs/intent/catalog.md", "tests/test_versions.py"])

    def test_the_record_is_written_once_beside_the_fork_and_read_back(self):
        runs = Path(tempfile.mkdtemp()) / "runs"
        fork = reliance_fork(runs, "g-bare-1", 2, 1, at=4, cost=0.42, streams=TWO_TURNS)
        written = rot_cost.measures(fork, write=True)
        self.assertEqual(json.loads((fork / rot_cost.MEASURES).read_text()), written)
        (fork / "change-reliance" / "turn-00.stream.jsonl").unlink()  # the record stands once written
        self.assertEqual(rot_cost.measures(fork), written)

    def test_a_fork_with_no_recorded_change_has_no_measures(self):
        runs = Path(tempfile.mkdtemp()) / "runs"
        fork = runs / "g-bare-1" / "course-forks" / "c02-reliance-1"
        write(fork / "trajectory.json", {"kind": "reliance", "course": 2, "at": 4, "lag": 2, "changes": {}})
        self.assertIsNone(rot_cost.measures(fork))


class AuditTest(unittest.TestCase):
    def setUp(self):
        self.runs = Path(tempfile.mkdtemp()) / "runs"
        for cp, courses in ((10, {"2": audit_of(README_md="stale")}),
                            (20, {"2": audit_of(README_md="current"), "12": audit_of(docs__a_md="stale")})):
            write(self.runs / "g-bare-1" / "growth" / f"checkpoint-{cp:02d}" / "stale-audit.json",
                  {"checkpoint": cp, "courses": courses})

    def test_a_reliance_fork_takes_the_nearest_checkpoint_whose_audit_covers_its_course_change(self):
        run = self.runs / "g-bare-1"
        self.assertEqual(rot_cost.nearest_audit(run, 2, 4)[0], 10)
        self.assertEqual(rot_cost.nearest_audit(run, 12, 14)[0], 20)  # checkpoint 10 is nearer but came before it
        self.assertEqual(rot_cost.nearest_audit(run, 2, 15)[0], 10)  # a tie goes to the earlier checkpoint
        self.assertIsNone(rot_cost.nearest_audit(run, 31, 33))

    def test_flagged_files_read_are_those_the_audit_judged_stale_with_mixed_ones_apart(self):
        fork = reliance_fork(self.runs, "g-bare-1", 12, 1, at=14, cost=0.3, streams=[
            stream(*read("t1", "/work/docs/a.md"), *read("t2", "/work/docs/b.md"), *read("t3", "/work/src/app.py"))])
        write(self.runs / "g-bare-1" / "growth" / "checkpoint-20" / "stale-audit.json",
              {"checkpoint": 20, "courses": {"12": audit_of(docs__a_md="stale", docs__b_md="mixed", docs__c_md="stale")}})
        rec = rot_cost.record(fork)
        self.assertEqual(rec["audit"], {"source": "checkpoint 20", "distance": 6, "stale": 2, "mixed": 1})
        self.assertEqual((rec["flagged_read"], rec["mixed_read"]), (["docs/a.md"], ["docs/b.md"]))
        self.assertEqual(rec["files_read_count"], 3)

    def test_a_bash_glob_read_counts_the_audited_files_it_matches(self):
        # no listing of the fork's repository is kept, so a glob is matched against the files the audit names
        fork = reliance_fork(self.runs, "g-bare-1", 12, 1, at=14, cost=0.3, streams=[
            stream(*bash("t1", "cat docs/intent/x/*.md; head -3 tests/*.py"), *read("t2", "/work/docs/intent/x/x-design.md"))])
        write(self.runs / "g-bare-1" / "growth" / "checkpoint-20" / "stale-audit.json",
              {"checkpoint": 20, "courses": {"12": audit_of({"docs/intent/x/x-specs.md": "stale",
                                                              "docs/intent/x/x-design.md": "current",
                                                              "docs/intent/y/y-specs.md": "stale"})}})
        m = rot_cost.measures(fork)
        self.assertEqual((m["files_read"], m["globs_read"]), (["docs/intent/x/x-design.md"], ["docs/intent/x/*.md", "tests/*.py"]))
        rec = rot_cost.record(fork)
        self.assertEqual(rec["flagged_read"], ["docs/intent/x/x-specs.md"])
        self.assertEqual(rec["files_read_via_glob"], ["docs/intent/x/x-specs.md"])
        self.assertEqual(rec["files_read_count"], 2)

    def test_a_course_fork_uses_its_own_audit(self):
        fork = course_fork(self.runs, "g-bare-1", 2, 1, cost=2.0, streams=[stream(*read("t1", "/work/README.md"))],
                           audit=audit_of(README_md="stale", tests__test_api_py="current"))
        rec = rot_cost.record(fork)
        self.assertEqual(rec["audit"]["source"], "own")
        self.assertEqual(rec["flagged_read"], ["README.md"])

    def test_a_fork_with_no_audit_to_join_has_no_flagged_count(self):
        fork = reliance_fork(self.runs, "g-bare-1", 31, 1, at=33, cost=0.3, streams=[stream(*read("t1", "/work/README.md"))])
        rec = rot_cost.record(fork)
        self.assertIsNone(rec["audit"])
        self.assertIsNone(rec["flagged_read"])


class GroupsTest(unittest.TestCase):
    RECS = [{"agent_cost_usd": 1.0, "turns": 2, "model_calls": 10, "files_read_count": 4, "flagged_read": ["a"],
             "mixed_read": [], "outcome": "displaced", "r_plus_ratio": 4.0},
            {"agent_cost_usd": 3.0, "turns": 6, "model_calls": 30, "files_read_count": 8, "flagged_read": ["a", "b"],
             "mixed_read": ["c"], "outcome": "current", "r_plus_ratio": 6.0},
            {"agent_cost_usd": 2.0, "turns": 1, "model_calls": 5, "files_read_count": 1, "flagged_read": [],
             "mixed_read": ["c"], "outcome": "current", "r_plus_ratio": 1.0},
            {"agent_cost_usd": 4.0, "turns": 1, "model_calls": 4, "files_read_count": 1, "flagged_read": [],
             "mixed_read": [], "outcome": "neither", "r_plus_ratio": 2.0},
            {"agent_cost_usd": 5.0, "turns": 1, "model_calls": 7, "files_read_count": 1, "flagged_read": None,
             "mixed_read": None, "outcome": "both", "r_plus_ratio": None}]

    def test_forks_that_read_a_stale_file_against_forks_that_read_none(self):
        g = rot_cost.groups(self.RECS, rot_cost.RELIANCE_OUTCOMES)
        self.assertEqual(g["read flagged"]["n"], 2)
        self.assertEqual((g["read flagged"]["cost_mean"], g["read flagged"]["cost_median"]), (2.0, 2.0))
        self.assertEqual((g["read flagged"]["turns_mean"], g["read flagged"]["files_median"]), (4.0, 6.0))
        self.assertEqual((g["read flagged"]["calls_mean"], g["read flagged"]["calls_median"]), (20.0, 20.0))
        self.assertEqual(g["read flagged"]["r_plus_ratio_median"], 5.0)
        self.assertEqual(g["read flagged"]["outcomes"], {"current": 1, "displaced": 1, "neither": 0, "other": 0})
        self.assertEqual(g["read none"]["n"], 2)
        self.assertEqual(g["no audit"]["outcomes"]["other"], 1)  # "both": counted, apart from the three

    def test_the_stale_or_mixed_cut_counts_a_fork_that_read_only_a_mixed_file_as_flagged(self):
        g = rot_cost.groups(self.RECS, rot_cost.RELIANCE_OUTCOMES, cut="stale or mixed")
        self.assertEqual((g["read flagged"]["n"], g["read none"]["n"], g["no audit"]["n"]), (3, 1, 1))
        self.assertEqual(g["read none"]["outcomes"]["neither"], 1)
        self.assertEqual(rot_cost.CUTS, ("stale", "stale or mixed"))


class BackfillTest(unittest.TestCase):
    def test_backfill_writes_each_forks_record_and_the_joined_records_per_trajectory(self):
        import rot_cost as cli
        runs = Path(tempfile.mkdtemp()) / "runs"
        write(runs / "g-bare-1" / "growth" / "checkpoint-02" / "stale-audit.json",
              {"checkpoint": 2, "courses": {"2": audit_of(README_md="stale")}})
        fork = reliance_fork(runs, "g-bare-1", 2, 1, at=4, cost=0.6, streams=[stream(*read("t1", "/work/README.md"))])
        aside = runs / "g-bare-1" / "course-forks" / "c02-reliance-2.before-v2"  # set aside by a redo: left alone
        write(aside / "trajectory.json", {"kind": "reliance", "course": 2, "at": 4, "lag": 2,
                                          "changes": {"reliance": {"agent_cost_usd": 9.0, "rounds": 1}}})
        self.assertEqual(cli.main(["--runs", str(runs), "--ids", "g-bare-1"]), 0)
        self.assertTrue((fork / rot_cost.MEASURES).exists())
        self.assertFalse((aside / rot_cost.MEASURES).exists())
        joined = json.loads((runs / "g-bare-1" / "growth" / "rot-cost.json").read_text())
        self.assertEqual([(r["run"], r["flagged_read"]) for r in joined], [("g-bare-1/course-forks/c02-reliance-1", ["README.md"])])


if __name__ == "__main__":
    unittest.main()
