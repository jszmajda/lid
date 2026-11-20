"""The instrument gate (design.md, "The trial, and its gate"), as the seed's reference-builds.md specifies it: R+ (arm
ref-correct), told every row in force at each change; a stale fork S_C (arm ref-stale) per course change; their
reliance forks; the spec's gradings (instrument.py); and the gate report."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from costeval import grading, growth, reference, simulator as sm, trajectory as tj  # noqa: E402

ORACLE = """# Oracle

## Owner narrative

### What the owner knows from the start

We publish letters.

### Learned at change 3: embargoes lift

Embargoed letters show once their date passes.

### Learned at change 4: exports

Exports list titles.

### Learned at change 5: search

Search ignores case.

## Item table

| ID | Checkable behavior | Disclosure kind | In force | Retired | External check sketch |
|---|---|---|---|---|---|
| RD-01 | A letter records its title. | Stated at start | Start | — | Sketch. |
| RD-02 | Embargoed letters never show. | Askable | Start | Change 3 | Sketch. |
| RD-03 | Embargoed letters show once their date passes. | Stated in change 3 | Change 3 | — | Sketch. |
| RD-04 | Exports list titles. See RD-01. | Stated in change 4 | Change 4 | — | Sketch. |
| RD-05 | Search ignores case. | Realized on symptom | Change 5 | — | Sketch. |
"""

RELIANCE = """### Reliance request

**Lag:** 2
**Setup:** S0
**Scenario:** Export after the date.
**Current-rule outcome:** The letter is listed.
**Displaced-rule outcome:** The letter is left out.

> Can I get this week's export?
"""

SCRIPT = f"""# Change script

## Change 1 — Titles

### Owner request

> Record titles.

**Introduces:** RD-01.

## Change 2 — Tidy

### Owner request

> Tidy up.

## Change 3 — Lift embargoes

### Owner request

> Show embargoed letters once their date passes.

**Introduces:** RD-03.
**Retires:** RD-02.
**Course change:** reversal of change 0 (distance 3)

{RELIANCE}
## Change 4 — Exports

### Owner request

> Add exports.

**Introduces:** RD-04.

## Change 5 — Search is fussy

### Owner symptom report

> Searching "harbour" misses "Harbour".

**Introduces:** RD-05.

## Change 6 — More

### Owner request

> More.
"""

OWNER_ITEMS = {"RD-02": {"tier": "medium", "recall": "Embargoed letters stay hidden."},
               "RD-05": {"tier": "low", "recall": "Search shouldn't care about capitals."}}


def parsed():
    return sm.parse_oracle(ORACLE), sm.parse_change_script(SCRIPT)


TEXT = {"RD-01": "A letter records its title.", "RD-02": "Embargoed letters never show.",
        "RD-03": "Embargoed letters show once their date passes.", "RD-04": "Exports list titles.",
        "RD-05": "Search ignores case."}
SPEC = {
    "owner_text": TEXT,
    "correct": {**{str(n): ["RD-01", "RD-02"] for n in range(3)}, "3": ["RD-01", "RD-03"], "4": ["RD-01", "RD-03", "RD-04"],
                "5": ["RD-01", "RD-03", "RD-04", "RD-05"], "6": ["RD-01", "RD-03", "RD-04", "RD-05"]},
    "stale": {
        "3": {"kind": "reversal", "fork_from": 2, "lag": 2, "decline": "skip", "stand_in": None, "drops": ["RD-03"],
              "keeps": ["RD-02"], "hold": {"3": ["RD-01", "RD-02"], "4": ["RD-01", "RD-02", "RD-04"],
                                           "5": ["RD-01", "RD-02", "RD-04", "RD-05"]}},
        "4": {"kind": "emerging", "fork_from": 3, "lag": 2, "decline": "stand-in", "stand_in": "Exports list nothing.",
              "drops": ["RD-04"], "keeps": [], "hold": {"4": ["RD-01", "RD-03"], "5": ["RD-01", "RD-03", "RD-05"],
                                                       "6": ["RD-01", "RD-03", "RD-05"]}}},
    "checks": {"3": {"flip_old": ["P-RD02-flip03"], "flip_new": ["P-RD03-flip03"], "rr": ["P-RR03-current", "P-RR03-displaced"]},
               "4": {"flip_old": [], "flip_new": [], "rr": ["P-RR04-current", "P-RR04-displaced"]}},
}


class ReferenceSpecTest(unittest.TestCase):
    """reference-builds.json, as the drafter's build_reference.py writes it, drives both references."""

    def test_each_opening_message_states_every_held_row_in_its_owner_text(self):
        text = reference.statement(SPEC, 3)
        self.assertTrue(text.startswith(reference.INTRO))
        self.assertEqual(text.split("\n\n", 1)[1], "- A letter records its title.\n- Embargoed letters show once their date passes.")
        stale = reference.statement(SPEC, 4, stale_of=3)  # S_3 at change 4: RD-03 dropped, RD-02 kept
        self.assertIn("- Embargoed letters never show.", stale)
        self.assertNotIn("date passes", stale)
        self.assertTrue(reference.statement(SPEC, 5, stale_of=4).endswith("- Exports list nothing."))  # the stand-in rule

    def test_the_owner_holds_exactly_the_spec_rows_all_stated_with_no_narrative(self):
        o, _ = parsed()
        view = reference.owner_view(o, SPEC)
        for n in range(7):
            self.assertEqual([i.id for i in sm.released_items(view, n)], SPEC["correct"][str(n)], n)
        self.assertTrue(all(i.share == "Stated" for i in view.items))  # nothing latent: no recall, nothing withheld
        self.assertEqual(view.narrative, {})
        self.assertEqual(sm.recall_eligible(view), [])
        stale = reference.owner_view(o, SPEC, stale_of=3)
        for n in (3, 4, 5):
            self.assertEqual([i.id for i in sm.released_items(stale, n)], SPEC["stale"]["3"]["hold"][str(n)], n)
        stand = reference.owner_view(o, SPEC, stale_of=4)
        self.assertEqual([i.id for i in sm.released_items(stand, 5)], ["RD-01", "RD-03", "RD-05", "SI-04"])
        self.assertEqual(next(i for i in stand.items if i.id == "SI-04").behavior, "Exports list nothing.")
        self.assertEqual(next(i for i in view.items if i.id == "RD-04").behavior, "Exports list titles.")  # the spec's text

    def test_what_each_reference_runs_at_a_change(self):
        _, s = parsed()
        self.assertEqual(reference.plan_change(SPEC, s, 4), ("run", s[4]))
        kind, ch = reference.plan_change(SPEC, s, 5)  # a symptom-only change: its report, whatever a diagnostic says
        self.assertEqual((kind, ch.symptom is not None), ("run", True))
        self.assertEqual(reference.plan_change(SPEC, s, 3, stale_of=3), ("skip", None))  # declined: no session
        kind, ch = reference.plan_change(SPEC, s, 4, stale_of=4)
        self.assertEqual((kind, ch.request), ("run", "Please make sure of this: Exports list nothing."))
        self.assertEqual((ch.introduces, ch.course_change), ((), None))
        self.assertEqual(reference.plan_change(SPEC, s, 5, stale_of=3), ("run", s[5]))  # then the main line's changes
        import dataclasses
        with_redirect = dataclasses.replace(s[4], redirect="a change of mind")
        self.assertIsNone(reference.plan_change(SPEC, {**s, 4: with_redirect}, 4)[1].redirect)  # no redirects

    def test_the_stale_forks_and_their_checks(self):
        self.assertEqual(reference.stale_forks(SPEC), [(3, 2), (4, 2)])

    def test_the_reference_arms_are_bare_agents_marked_as_references(self):
        for kind in reference.KINDS:
            arm = tj.load_arm(f"ref-{kind}")
            self.assertEqual((arm.reference, arm.plugins, arm.workspace_files, arm.lid_release), (kind, (), {}, None))
        self.assertIsNone(tj.load_arm("bare").reference)

    def test_the_rules_go_to_the_agents_prompt_not_the_owners_request(self):
        arm = tj.load_arm("ref-correct")
        _, s = parsed()
        p = tj.change_prompt(arm, s[4], "Add exports.", rules="These are all the rules ...")
        self.assertTrue(p.startswith("Add exports.\n\nThese are all the rules ..."))
        self.assertTrue(p.rstrip().endswith(tj.NEUTRAL_SENTENCE))
        self.assertEqual(tj.change_prompt(arm, s[4], "Add exports."), f"Add exports.\n\n{tj.NEUTRAL_SENTENCE}")

    def test_a_reference_owner_holds_rows_by_their_lifetime(self):
        o, s = parsed()
        owner = sm.Owner(oracle=reference.owner_view(o, SPEC), brief="b", policy="diligent", replicate="g-ref",
                         ask=lambda p: {}, touch=lambda p: {"touches": []}, owner_items={}, full_oracle=True)
        tj.restore_owner_state(owner, {"record": [], "requests": [], "seen": {}, "disclosed": []})
        owner.start_change(s[6])
        self.assertIsNone(owner.realized)
        self.assertIn("[RD-05]", owner._prompt("Done.", [], None))

    def test_the_drafters_spec_matches_the_assembled_seed(self):
        seed = Path(__file__).resolve().parent.parent.parent / "seeds" / "releasedesk-growth"
        if not (seed / "hidden" / "reference-builds.json").exists():
            self.skipTest("no assembled growth seed")
        spec = reference.load_spec(seed)
        o = sm.parse_oracle((seed / "hidden" / "oracle.md").read_text())
        view = reference.owner_view(o, spec)
        for n in range(41):
            self.assertEqual([i.id for i in sm.released_items(view, n)], spec["correct"][str(n)], n)
        for c, entry in spec["stale"].items():
            v = reference.owner_view(o, spec, stale_of=int(c))
            for n, rows in entry["hold"].items():
                si = [f"SI-{int(c):02d}"] if entry["stand_in"] else []
                self.assertEqual([i.id for i in sm.released_items(v, int(n))], rows + si, (c, n))


from test_growth import EMPTY_STATE, subprocess_ok  # noqa: E402
from test_simulator import FakeAsk, out  # noqa: E402
from test_trajectory import FakeTurns, FakeWorkspace  # noqa: E402


PAIR_PROBES = """# Probes: Letters

## Setups

### S0: Example archive

Start with empty data.

## Probes

### RD-01

#### P-RD01-a
- **Applies:** from change 0
- **Setup:** S0
- **Needs:** none
- **Scenario:**
  1. Record a letter.
- **Expected observation:** It has its title.

### RD-02

#### P-RD02-flip03
- **Applies:** from change 0, until change 2
- **Setup:** S0
- **Needs:** none
- **Scenario:**
  1. Embargo a letter until yesterday and look for it.
- **Expected observation:** It isn't shown.

### RD-03

#### P-RD03-flip03
- **Applies:** from change 3
- **Setup:** S0
- **Needs:** none
- **Scenario:**
  1. Embargo a letter until yesterday and look for it.
- **Expected observation:** It is shown.

### RR-03

#### P-RR03-current
- **Applies:** from change 0
- **Setup:** S0
- **Needs:** none
- **Scenario:**
  1. Export after the date.
- **Expected observation:** The letter is listed.

#### P-RR03-displaced
- **Applies:** from change 0
- **Setup:** S0
- **Needs:** none
- **Scenario:**
  1. Export after the date.
- **Expected observation:** The letter is left out.
"""


def seed_dir(root: Path) -> Path:
    seed = root / "seeds" / "rd"
    (seed / "hidden").mkdir(parents=True)
    (seed / "brief.md").write_text("# Letters\n\nPublish letters.")
    (seed / "hidden" / "oracle.md").write_text(ORACLE)
    (seed / "hidden" / "change-script.md").write_text(SCRIPT)
    (seed / "hidden" / "owner-items.json").write_text(json.dumps(OWNER_ITEMS))
    (seed / "hidden" / "reference-builds.json").write_text(json.dumps(SPEC))
    (seed / "hidden" / "probes.md").write_text(PAIR_PROBES)
    return seed


def ref_meta(tid, kind, stale_of=None, changes=range(0, 7)):
    return {"id": tid, "arm": f"ref-{kind}", "seed": "rd", "model": "m", "effort": "medium", "policy": "diligent",
            "owner_model": "o", "replicate": "g-ref", "isolation": {"window": "1m"}, "round_cap": 6, "reference": kind,
            "stale_of": stale_of, "volumes": {"workspace": f"ce-{tid}-ws", "config": f"ce-{tid}-cfg"},
            "changes": {str(n): {"commit": f"{tid}-c{n}"} for n in changes}}


class ReferenceForkTest(unittest.TestCase):
    def test_each_references_reliance_fork_states_its_held_rows_and_its_owner_holds_them(self):
        import run_course_forks as rcf
        root = Path(tempfile.mkdtemp())
        seed = seed_dir(root)
        prompts = {}
        for tid, kind, stale_of in (("g-ref-correct", "correct", None), ("g-ref-stale-c03", "stale", 3)):
            base = root / "runs" / tid
            base.mkdir(parents=True)
            (base / "trajectory.json").write_text(json.dumps(ref_meta(tid, kind, stale_of)))
            (base / "owner-state-05.json").write_text(json.dumps(EMPTY_STATE))
            ws = FakeWorkspace()
            turns = FakeTurns(ws, ("Done: the export is ready.", None, ["src/app.py"]))
            ask = FakeAsk(out("completion"))
            deps = rcf.Deps(docker=lambda cmd, **kw: subprocess_ok(cmd), turn_for=lambda s: turns,
                            workspace_for=lambda image, vol: ws, ask=ask, touch=ask.touch, trim=None)
            rc = rcf.main(["--id", tid, "--kind", "reliance", "--course", "3", "--fork", "1", "--runs", str(root / "runs"),
                           "--seed-dir", str(seed)], deps=deps)
            self.assertEqual(rc, 0)
            prompts[kind] = turns.calls[0]["prompt"]
            self.assertTrue(rcf.LAST_OWNER.full_oracle)
            held = [i.id for i in sm.released_items(rcf.LAST_OWNER.oracle, 5)]
            self.assertEqual(held, SPEC["correct"]["5"] if kind == "correct" else SPEC["stale"]["3"]["hold"]["5"])
        self.assertIn("Can I get this week's export?", prompts["correct"])
        self.assertIn(reference.statement(SPEC, 5), prompts["correct"])
        self.assertIn(reference.statement(SPEC, 5, stale_of=3), prompts["stale"])
        self.assertNotIn("date passes", prompts["stale"])


import instrument  # noqa: E402


class RefRuns(unittest.TestCase):
    """R+ and two stale forks, each with a recorded reliance fork, on the synthetic seed."""

    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.seed = seed_dir(self.root)
        self.runs = self.root / "runs"
        for tid, kind, stale_of, changes in (("g-ref-correct", "correct", None, range(0, 7)),
                                             ("g-ref-stale-c03", "stale", 3, range(3, 6)),
                                             ("g-ref-stale-c04", "stale", 4, range(4, 7))):
            (self.runs / tid).mkdir(parents=True)
            (self.runs / tid / "trajectory.json").write_text(json.dumps(ref_meta(tid, kind, stale_of, changes)))
        for tid, c in (("g-ref-correct", 3), ("g-ref-stale-c03", 3), ("g-ref-correct", 4), ("g-ref-stale-c04", 4)):
            f = self.runs / tid / "course-forks" / f"c{c:02d}-reliance-1"
            f.mkdir(parents=True)
            (f / "trajectory.json").write_text(json.dumps({"kind": "reliance", "course": c, "at": c + 2,
                                                          "changes": {"reliance": {"commit": f"{tid}-rr{c}"}}}))
        self.commands = []

    def fake_run(self, cmd):
        self.commands.append(cmd)
        if "grade_checkpoint.py" in cmd:
            tid = cmd[cmd.index("--id") + 1]
            name = cmd[cmd.index("--out-name") + 1] if "--out-name" in cmd else f"change-{int(cmd[cmd.index('--change') + 1]):02d}"
            probes = cmd[cmd.index("--probes") + 1].split(",") if "--probes" in cmd else ["P-RD01-a"]
            g = self.runs / tid / "grading" / name
            g.mkdir(parents=True, exist_ok=True)
            (g / "verdicts.json").write_text(json.dumps({"probes": {p: "met" for p in probes}}))
        return 0

    def grade(self, *argv):
        return instrument.main([*argv, "--runs", str(self.runs), "--seed-dir", str(self.seed)], run=self.fake_run)


class InstrumentGradingTest(RefRuns):
    """instrument.py: the spec's grading table, run through grade_checkpoint.py."""

    def test_a_course_change_is_graded_at_each_point_the_spec_names(self):
        self.assertTrue(instrument.pending_course(self.runs, SPEC, 3))
        self.assertEqual(self.grade("course", "--course", "3"), 0)
        cmds = [" ".join(c) for c in self.commands]
        graded = [c for c in cmds if "grade_checkpoint.py" in c]
        want = [("g-ref-correct", 2, "pair-c03-before", "P-RD02-flip03,P-RD03-flip03", None),
                ("g-ref-correct", 3, "pair-c03-after", "P-RD02-flip03,P-RD03-flip03", None),
                ("g-ref-stale-c03", 5, "pair-c03", "P-RD02-flip03,P-RD03-flip03", None),
                ("g-ref-correct/course-forks/c03-reliance-1", 5, "reliance", "P-RR03-current,P-RR03-displaced", "g-ref-correct-rr3"),
                ("g-ref-stale-c03/course-forks/c03-reliance-1", 5, "reliance", "P-RR03-current,P-RR03-displaced",
                 "g-ref-stale-c03-rr3")]
        for tid, n, name, probes, commit in want:
            self.assertTrue(any(f"--id {tid} --change {n} --seed rd" in c and f"--out-name {name}" in c and f"--probes {probes}" in c
                                and (commit is None or f"--commit {commit}" in c) for c in graded), (tid, name))
        self.assertEqual(len(graded), 5)
        self.assertTrue(any("run_course_forks.py --id g-ref-correct --kind reliance --course 3 --fork 1 --discard" in c for c in cmds))
        self.assertTrue(any("run_course_forks.py --id g-ref-stale-c03 --kind reliance --course 3 --fork 1 --discard" in c for c in cmds))
        self.assertFalse(instrument.pending_course(self.runs, SPEC, 3))
        self.commands.clear()
        self.grade("course", "--course", "3")
        self.assertFalse(any("grade_checkpoint.py" in " ".join(c) for c in self.commands))  # graded already

    def test_an_emerging_change_has_only_its_follow_up_pair(self):
        self.grade("course", "--course", "4")
        graded = [" ".join(c) for c in self.commands if "grade_checkpoint.py" in " ".join(c)]
        self.assertEqual(len(graded), 2)
        self.assertTrue(all("--out-name reliance" in c and "--probes P-RR04-current,P-RR04-displaced" in c for c in graded))

    def test_a_checkpoint_grades_every_probe_that_applies_to_r_plus(self):
        self.assertTrue(instrument.pending_checkpoint(self.runs, 6))
        self.grade("checkpoint", "--change", "6")
        (cmd,) = [" ".join(c) for c in self.commands]
        self.assertIn("grade_checkpoint.py --id g-ref-correct --change 6 --seed rd", cmd)
        self.assertNotIn("--probes", cmd)
        self.assertFalse(instrument.pending_checkpoint(self.runs, 6))

    def test_the_gate_gradings_have_work_until_each_is_recorded(self):
        import pending
        left = lambda *a: pending.main(["gate", *a, "--runs", str(self.runs), "--seed-dir", str(self.seed)]) == 0  # noqa: E731
        self.assertTrue(left("--course", "3"))
        self.assertTrue(left("--change", "6"))
        self.grade("course", "--course", "3")
        self.grade("checkpoint", "--change", "6")
        self.assertFalse(left("--course", "3"))
        self.assertFalse(left("--change", "6"))

    def test_the_positive_control_has_work_until_the_readers_summary_exists(self):
        import pending
        self.assertEqual(pending.main(["control", "--id", "g-ref-correct", "--change", "20", "--runs", str(self.runs)]), 0)
        d = self.runs / "intent-from-tests" / "pc-g-ref-correct-c20"
        d.mkdir(parents=True)
        (d / "summary.json").write_text("{}")
        self.assertEqual(pending.main(["control", "--id", "g-ref-correct", "--change", "20", "--runs", str(self.runs)]), 1)


class InstrumentReportTest(RefRuns):
    """report.py --instrument: each course change's verdicts at every point against the spec's expectations, R+'s
    unmet probes at the checkpoints, and the positive control's catch rate."""

    GIVEN = {  # what each grading found: S_3 also meets the new rule, a mismatch for probe review
        ("g-ref-correct", "pair-c03-before"): {"P-RD02-flip03": "met", "P-RD03-flip03": "not met"},
        ("g-ref-correct", "pair-c03-after"): {"P-RD02-flip03": "not met", "P-RD03-flip03": "met"},
        ("g-ref-stale-c03", "pair-c03"): {"P-RD02-flip03": "met", "P-RD03-flip03": "met"},
        ("g-ref-correct/course-forks/c03-reliance-1", "reliance"): {"P-RR03-current": "met", "P-RR03-displaced": "not met"},
        ("g-ref-stale-c03/course-forks/c03-reliance-1", "reliance"): {"P-RR03-current": "not met", "P-RR03-displaced": "met"},
        ("g-ref-correct/course-forks/c04-reliance-1", "reliance"): {"P-RR04-current": "met", "P-RR04-displaced": "not met"},
        ("g-ref-stale-c04/course-forks/c04-reliance-1", "reliance"): {"P-RR04-current": "not met", "P-RR04-displaced": "met"},
        ("g-ref-correct", "change-06"): {"P-RD01-a": "met", "P-RD03-flip03": "couldn't exercise"},
    }

    def fake_run(self, cmd):
        self.commands.append(cmd)
        if "grade_checkpoint.py" in cmd:
            tid = cmd[cmd.index("--id") + 1]
            name = cmd[cmd.index("--out-name") + 1] if "--out-name" in cmd else f"change-{int(cmd[cmd.index('--change') + 1]):02d}"
            g = self.runs / tid / "grading" / name
            g.mkdir(parents=True, exist_ok=True)
            (g / "verdicts.json").write_text(json.dumps({"probes": {p: {"verdict": v} for p, v in self.GIVEN[tid, name].items()}}))
        return 0

    def control(self):
        base = self.runs / "g-ref-correct" / "growth" / "positive-control-c20"
        for kind, planted in (("names", {"tests/a.py": {"item": "RD-02"}, "tests/b.py": {"item": "RD-09"}}),
                              ("assertions", {"tests/c.py": {"item": "RD-02"}})):
            (base / kind).mkdir(parents=True)
            (base / kind / "index.json").write_text(json.dumps({"kind": kind, "planted": planted}))
        res = self.runs / "intent-from-tests" / "pc-g-ref-correct-c20"
        for label, reps in (("pc-names", [["RD-02"], ["RD-02", "RD-09"]]), ("pc-names-neutral", [[], []]),
                            ("pc-assertions", [["RD-02"], ["RD-02"]]), ("pc-assertions-neutral", [["RD-02"], []])):
            (res / label).mkdir(parents=True)
            (res / label / "result.json").write_text(json.dumps({"label": label, "repeats": [{"stale_items": r} for r in reps]}))

    def test_the_gate_report(self):
        import report
        for c in (3, 4):
            self.grade("course", "--course", str(c))
        self.grade("checkpoint", "--change", "6")
        self.control()
        r = report.instrument_report(self.runs, self.seed, checkpoints=[6], controls=[20])
        c3, c4 = r["courses"]
        self.assertEqual((c3["course"], c3["separates"], c4["separates"]), (3, False, True))
        self.assertEqual([p["point"] for p in c3["points"]], ["R+ after C-1", "R+ after C", "S_C after C+L", "R+ reliance fork",
                                                              "S_C reliance fork"])
        self.assertEqual([p["point"] for p in c4["points"]], ["R+ reliance fork", "S_C reliance fork"])  # emerging: no flips
        self.assertEqual(r["mismatches"], [{"course": 3, "point": "S_C after C+L", "probe": "P-RD03-flip03",
                                            "expected": "not met", "verdict": "met"}])
        self.assertEqual(r["checkpoints"], [{"change": 6, "graded": 2, "unmet": {"P-RD03-flip03": "couldn't exercise"}}])
        ctl = {(x["kind"], x["neutral"]): x for x in r["control"]}
        self.assertEqual(ctl["names", False]["catch"], 0.75)  # 1/2, then 2/2
        self.assertEqual(ctl["names", True]["catch"], 0.0)
        self.assertEqual(ctl["assertions", False]["catch"], 1.0)
        self.assertEqual(ctl["assertions", True]["catch"], 0.5)
        text = report.render_instrument(r)
        for line in ("Separating: 1 of 2 course changes", "| 3 | S_C after C+L | P-RD03-flip03 | not met | met |",
                     "| 6 | 2 | P-RD03-flip03 (couldn't exercise) |", "| 20 | assertions | as written | 1 | 100% |"):
            self.assertIn(line, text)

    def test_a_grading_not_yet_recorded_leaves_the_course_undecided(self):
        import report
        self.grade("course", "--course", "4")
        r = report.instrument_report(self.runs, self.seed, checkpoints=[], controls=[])
        self.assertIsNone(r["courses"][0]["separates"])  # course 3 hasn't been graded
        self.assertTrue(r["courses"][1]["separates"])


class StaleForkStartTest(unittest.TestCase):
    def test_s_c_starts_from_r_plus_after_c_minus_1_with_its_owner_state(self):
        import run_trajectory as rt
        runs = Path(tempfile.mkdtemp())
        (runs / "g-ref-correct").mkdir()
        (runs / "g-ref-correct" / "trajectory.json").write_text(json.dumps(ref_meta("g-ref-correct", "correct")))
        (runs / "g-ref-correct" / "owner-state-02.json").write_text(json.dumps({**EMPTY_STATE, "disclosed": ["RD-01"]}))
        commit, state, volume = rt.fork_start(runs, "g-ref-correct", 3)
        self.assertEqual((commit, state["disclosed"], volume), ("g-ref-correct-c2", ["RD-01"], "ce-g-ref-correct-ws"))
        with self.assertRaisesRegex(RuntimeError, "after change 9"):
            rt.fork_start(runs, "g-ref-correct", 10)
        cmd = " ".join(tj.clone_command("ce-src", "ce-dest", "abc123"))
        self.assertIn("-v ce-src:/src:ro -v ce-dest:/work", cmd)
        self.assertIn("git checkout -q -B main abc123", cmd)


class FollowUpProbesTest(unittest.TestCase):
    def test_a_checkpoint_never_runs_the_follow_up_pairs_which_belong_to_reliance_forks(self):
        import grade_checkpoint as gck
        ps = grading.parse_probes(PAIR_PROBES)
        self.assertEqual([p.id for p in gck.applicable(ps, 6, set())], ["P-RD01-a", "P-RD03-flip03"])
        self.assertEqual([p.id for p in gck.applicable(ps, 6, {"P-RR03-current"})], ["P-RR03-current"])  # when named


class GrowthOwnerItemsTest(unittest.TestCase):
    """assemble_growth_seed.py: block 1's owner items with the growth salience rounds merged in, and the gaps."""

    def rounds(self, root: Path) -> Path:
        sal = root / "salience"
        for d, tiers, lines in ((sal, {"RD-06": "low"}, {"RD-06": "Exports stay quiet."}),                    # current
                                (sal / "round2", {"RD-04": "medium", "RD-06": "high"}, {"RD-04": "Old line.", "RD-06": "Old."}),
                                (sal / "round1", {"RD-05": "high", "RD-07": "low"}, {"RD-05": "Case never matters."})):
            d.mkdir(parents=True, exist_ok=True)
            (d / "ratings.json").write_text(json.dumps({"tier": tiers}))
            (d / "recall-lines.json").write_text(json.dumps({"lines": lines, "missing": []}))
        return sal

    def test_the_rounds_merge_by_precedence_and_round_2_gives_only_its_named_row(self):
        import assemble_growth_seed as ags
        sal = self.rounds(Path(tempfile.mkdtemp()))
        base = {"_note": "block 1", "items": {"RD-02": {"tier": "medium", "recall": "Embargoes hold."}}}
        merged = ags.merge_owner_items(base, sal, round2_only={"RD-04"})
        self.assertEqual(merged["_note"], "block 1")
        self.assertEqual(merged["items"], {
            "RD-02": {"tier": "medium", "recall": "Embargoes hold."},
            "RD-06": {"tier": "low", "recall": "Exports stay quiet."},     # the current round wins over round 2
            "RD-04": {"tier": "medium", "recall": "Old line."},
            "RD-05": {"tier": "high", "recall": "Case never matters."},
            "RD-07": {"tier": "low"}})                                       # rated, but no recall line: left as it is
        self.assertIn("growth salience", merged["_growth"])

    def test_every_recall_eligible_row_without_a_tier_or_recall_line_is_a_gap(self):
        import assemble_growth_seed as ags
        o = sm.parse_oracle(ORACLE.replace("| RD-04 | Exports list titles. See RD-01. | Stated in change 4 |",
                                           "| RD-04 | Exports list titles. See RD-01. | Askable |"))
        items = {"RD-02": {"tier": "medium", "recall": "Embargoes hold."}, "RD-05": {"tier": "high"}}
        self.assertEqual(ags.owner_item_gaps(o, items), ["RD-04: no tier or recall line", "RD-05: no recall line"])


class PlantRetiredTest(unittest.TestCase):
    def test_the_control_plants_every_row_retired_by_the_change(self):
        import plant_stale_tests as pst
        o, s = parsed()
        self.assertEqual(pst.retired_by(o, 2), [])
        self.assertEqual(pst.retired_by(o, 3), ["RD-02"])


if __name__ == "__main__":
    unittest.main()
