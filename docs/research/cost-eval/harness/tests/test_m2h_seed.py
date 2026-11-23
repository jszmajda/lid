"""Tests for the M2h seed converter (build_m2h_seed.py, costeval/m2h_seed.py): openGym's M2h change set turned into the
harness's change script, oracle, owner items, repair reports, kept-behaviour record (with each change's searchability
tier, dependency precondition or comparison row, and joint-outcome notes) and guard rows.

The synthetic excerpt below follows m2h-changes.md's layout: two cross-component changes (one with a guard row, a
retired-test list with adjusted copies, a citation whose test title holds a semicolon; one with a conditional guard,
the conditional recall line, and a fixture-patch retired list with run-time test titles) and one control with its
comparison row. The last test converts the real file when it is reachable (M2H_HIDDEN, or the harness's own seeds).
"""

from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

HARNESS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HARNESS))

import build_m2h_seed  # noqa: E402
from costeval import m2h_seed as ms, repair, simulator as sm  # noqa: E402

M2H = """# openGym M2h changes (a three-change excerpt)

Sol's draft, with the edits in the edit log.

## Change 1 — One watch at a time

**Type:** api-change-app-depends
**Intent distance:** other part
**Edits part:** api
**Edits file:** api/watch-relay.js
**Intent lives in:** frontend/src/views/ZeppSettings.jsx
**Searchability tier:** hidden. No name or value search finds the dependent line.

### Owner request

> can we make it one Zepp watch per person? when someone pairs a replacement, i'd like it to take the place of the old one.

### New rows

| ID | Behaviour | Disclosure kind | Check |
|---|---|---|---|
| OGM-0101 | A successful pairing leaves only the newly paired watch linked to that profile. | Stated | Server routes: redeem two codes and read `/api/watch/links`. |
| OGM-0102 | The existing watch stays connected when a pairing starts, even if the attempt is abandoned. | Askable | Server routes: request a code without redeeming it. |

- **OGM-0102** recall: “If I get called away halfway, the old one should still work.”

**Guard row:** OGM-0102. The untouched code meets it by design, so it is graded apart from the new behaviour (`m2h-guard-rows.json`).

**Left to the developer:** How to record the replacement.

**For grading:** the dependency probe serves the settings screen through the server's watch-link functions.

### Behaviour to keep

| Behaviour | Established in | How a careless version breaks it | Check |
|---|---|---|---|
| Zepp settings notices a pairing at its next look at the list. | api/watch-relay.js#createWatchLink; api/server.js#POST /api/watch/redeem; frontend/src/views/ZeppSettings.jsx:53-66 | The screen still looks for a longer list. | Web app + server functions: seed links, redeem, advance the timers. |
| Retried updates queue once. | api/watch-relay.js:158-188; api/test/watch-relay.test.js::events queue in order, once each; the page acknowledges them out; CLAUDE.md | A special path bypasses acknowledgement. | Server functions: push the same event twice. |

**Dependency exercised only if** a second redemption leaves the profile one watch (the server replaces links). Otherwise the dependency is **not exercised** for that fork, never kept. The fork's joint outcome pairs this with whether the change's stated rows were met.

**Deliberate change:** `api/watch-relay.js#createWatchLink` keeps one watch link per profile instead of up to five.

### Retired tests

<!-- Set by Claude, not Sol. -->

- api/test/server-pairing.test.js::minting a pairing code asks the owner proof: a session alone gets none — update the old code-shape assertion, not the proof requirement.
- frontend/src/views/Home.queue.test.jsx::a managed pass counts your own day — ownership plays no part in the tally — update the wording only.

**For grading:** each test above is kept in grading through a grader-owned adjusted copy that changes only the wording or layout named. The copies are frozen before any run.

### Why the other part is needed

The server can replace the link without making the list longer.

### Repair reports

<!-- OGM-0102: rewritten by Claude, not Sol. -->

- **OGM-0101:** “I paired a second watch, but I didn't end up with just the new one paired.”
- **OGM-0102:** “I got a code for a replacement and never used it. My old watch stopped connecting.”
- **Dependency:** “I finished pairing and left the settings open. The code didn't clear.”

## Change 4 — A private cycle log

**Type:** client-change-api-depends
**Intent distance:** other part
**Edits part:** frontend
**Edits file:** frontend/src/store/useStore.js
**Intent lives in:** api/tokens.js
**Searchability tier:** one-step grep. From the documented sync twin, `grep dayForm api/` lands on the never-handed-out list.

### Owner request

> someone in the group asked for a little cycle log. that needs to be private, just for them.

### New rows

| ID | Behaviour | Disclosure kind | Check |
|---|---|---|---|
| OGM-0401 | A member can record period starts and see them after reopening the app. | Stated | Web app: record two dates and reload. |
| OGM-0402 | Today's cycle day counts from the latest start on or before today. | Stated | Web app: read day 1, then day 3. |
| OGM-0403 | Trainer and admin views still show none of the log. | Stated | Server routes: read the member as a trainer and as an admin. |
| OGM-0404 | Before a start is logged, the app does not guess a cycle day. | Askable | Web app: open the log with no starts. Exercised only if the log opens at all (at the pin it doesn't: not exercised). |
| OGM-0405 | No access token receives the log, whatever it is allowed to read. | Askable | Web app + server: read the document through the token route. |

- **OGM-0404** recall: “If they haven’t put a start in, just leave the day blank.”
- **OGM-0405** recall: “no, not their apps either. it's between them and the screen.”

**Guard row:** OGM-0403. The untouched code meets it by design.

**For grading:** OGM-0403 is a conditional guard: it runs only on a build that has the log (at the pin, not exercised). OGM-0405's recall line is given only in answer to a question about privacy. OGM-0405 is reported beside the dependency rate, not inside the new-row score: a web-app-only build that adds a new key fails both for one fault. The dependency rate over all forks is the primary figure; the rate over new-key builds describes a selected group.

**Left to the developer:** Where the log sits.

### Behaviour to keep

| Behaviour | Established in | How a careless version breaks it | Check |
|---|---|---|---|
| A plans-only token does not receive the log. | api/tokens.js#KEY_CATEGORY; api/tokens.js#scopedState; docs/API_TOKENS.md | A new field rides along as a setting. | Web app + server: read with a plans-only token. |
| Ordinary settings still ride along. | api/tokens.js:43-55 | A blanket filter strips units. | Server functions: scope a document to plans-only. |

**Dependency exercised only if** the build's own action logs a period start, the entry is in the member's own document, and a control field syncs to the server. Otherwise **not exercised**.

**Deliberate change:** None.

### Retired tests

The right build fails the 3 existing tests below: 1 in the API and 2 in 1 web-app files. A grader-owned patch, frozen before any run, adjusts them:
- **one default test** (marked "pins the old default") changes only its missing-choice expectation;
- **the other 2** keep every assertion, and their fixtures opt in.

**API (1):**

- api/test/wrapped.test.js::the summary is a few small facts whatever the state holds — pins the old default

**Web app (2):**

- frontend/src/views/settings-pages.test.jsx, the two scenario tests whose titles are made at run time from its `scenarios` (line 279): guest in a browser; signed in, browser without push — their fixtures leave Motivation unset; kept with the fixtures opted in

### Why the other part is needed

A frontend-only log under an unclassified key exposes it even to a narrow token.

### Repair reports

- **OGM-0401:** “I marked two period starts and reopened the app. I couldn't find both.”
- **OGM-0402:** “I logged a start today after an earlier one. I didn't get day 1.”
- **OGM-0403:** “I looked at what my trainer can see of me. Some of the log showed up.”
- **OGM-0404:** “I opened the log without a start and it gave me a cycle day.”
- **OGM-0405:** “I made a key for one of my apps, and it could read part of my log.”
- **Dependency:** “I checked what access just to my plans could read. It could read part of my log.”

## Change 9 — A join code good for 90 days

**Type:** control
**Intent distance:** other file, same part
**Edits part:** api
**Edits file:** api/trainers/dashboard-routes.js
**Intent lives in:** api/trainers/org-store.js
**Searchability tier:** one-step grep. The route calls `createCode` directly; its clamp is one step in.

### Owner request

> could the gym join code i pin up by the door be good for 90 days?

### New rows

| ID | Behaviour | Disclosure kind | Check |
|---|---|---|---|
| OGM-0901 | A normal gym-lead join code gets a 90-day expiry by default. | Stated | Server routes: issue a code without days. |
| OGM-0902 | The join code can be used near the end of those 90 days, and not after them. | Stated | Server routes: join at day 89 and at day 90 plus a minute. |
| OGM-0903 | A gym lead can still ask for a shorter-lived code. | Askable | Server routes: ask for seven days. |

- **OGM-0903** recall: “If it’s just for a short intake, I’d still like one that runs out sooner.”

**Guard row:** OGM-0903. The untouched code meets it by design.

**Left to the developer:** How to give gym codes their own lifetime rule.

### Behaviour to keep

| Behaviour | Established in | How a careless version breaks it | Check |
|---|---|---|---|
| A trainer’s invite code lasts at most 30 days. | api/trainers/org-store.js#createCode; api/trainers/routes.js#POST /api/trainer/codes | Raising the shared ceiling lengthens trainer invites. | Server routes: issue invites with no days, 30 and 90. |
| Only the lead of that gym can issue its join code. | api/trainers/dashboard-routes.js:334-341 | A shortcut skips the gym permission check. | Server routes: try as a trainer who isn't the lead. |

**Comparison row:** the first kept row (trainer codes stay within 30 days). It is the control's counterpart of a dependency row. It is **exercised only if** a gym join code lasts 90 days; otherwise **not exercised**, never kept. Baseline witness: at the pin, trainer codes asking for no days, 30 and 90 days get 7, 30 and 30.

**Deliberate change:** `api/trainers/org-store.js#createCode` allows the gym's join code 90 days.

### Retired tests

None found.

### Repair reports

- **OGM-0901:** “I made the usual join code, and it wasn't good for 90 days.”
- **OGM-0902:** “The code didn't work on day 89, or still worked just past day 90.”
- **OGM-0903:** “I asked for a gym code for a week, but it didn't get a one-week expiry.”

### Summary

| Change | Type | Intent distance | Edits part | Files: edit → intent |
|---|---|---|---|---|
| 1 | api-change-app-depends | other part | api | `api/watch-relay.js` → `frontend/src/views/ZeppSettings.jsx` |
| 4 | client-change-api-depends | other part | frontend | `frontend/src/store/useStore.js` → `api/tokens.js` |
| 9 | control | other file, same part | api | `api/trainers/dashboard-routes.js` → `api/trainers/org-store.js` |
"""

BRIEF = """# openGym

I coach a small strength group. We use openGym to keep track of what we lifted.

I didn’t build openGym. I can tell you what I’d like to happen, but how to get there is up to you.
"""

GUARDS = {"note": "Keep-it-as-it-was rows.", "rows": {
    "OGM-0102": {"change": 1, "why": "the existing watch stays connected", "checkable_on_snapshot": True},
    "OGM-0403": {"change": 4, "why": "trainer and admin views still show none of the log", "checkable_on_snapshot": False,
                 "uncheckable_why": "a conditional guard: it runs only on a build that has the cycle log"},
    "OGM-0903": {"change": 9, "why": "a gym lead can still ask for a shorter-lived code", "checkable_on_snapshot": True}}}

PLAN = """# M2h: the drafting plan

**Searchability tiers, for reading results** (recorded in each change's line).

| Change | Tier | Why |
|---|---|---|
| 1 | hidden | no name or value hit; two hops by route. Signpost: `docs/ZEPP_OS.md:64` names the screen ("pair, list, unpair"), not the length comparison |
| 4 | one-step grep | the documented sync twin leads into `api/` |
| 9 | one-step grep | the edited code calls the module that holds the rule |

**Tier count:** cross-component changes: 0 documented, 1 one-step (4), 1 hidden (1). Controls: 1 one-step (9).
"""

TEST_INDEX = {
    "api/test/server-pairing.test.js": ["minting a pairing code asks the owner proof: a session alone gets none"],
    "frontend/src/views/Home.queue.test.jsx": ["a managed pass counts your own day — ownership plays no part in the tally"],
    "api/test/watch-relay.test.js": ["events queue in order, once each; the page acknowledges them out"],
    "api/test/wrapped.test.js": ["the summary is a few small facts whatever the state holds"],
    "frontend/src/views/settings-pages.test.jsx": ["${name}: every row on a page is in the search"],
}

PATHS = {"api/watch-relay.js", "api/server.js", "frontend/src/views/ZeppSettings.jsx", "api/test/watch-relay.test.js",
         "CLAUDE.md", "api/tokens.js", "docs/API_TOKENS.md", "api/trainers/org-store.js", "api/trainers/routes.js",
         "api/trainers/dashboard-routes.js", *TEST_INDEX}

BRIEFS = {"changes": [
    {"n": 1, "type": "api-change-app-depends",
     "dependency_row": {"cites": ["api/watch-relay.js#createWatchLink", "api/server.js#POST /api/watch/redeem",
                                  "frontend/src/views/ZeppSettings.jsx:53-66"]},
     "known_retired": ["api/test/server-pairing.test.js::minting a pairing code asks the owner proof: a session alone gets none"]},
    {"n": 4, "type": "client-change-api-depends",
     "dependency_row": {"cites": ["api/tokens.js#KEY_CATEGORY", "api/tokens.js#scopedState", "docs/API_TOKENS.md"]},
     "known_retired": []},
    {"n": 9, "type": "control",
     "kept_row": {"cites": ["api/trainers/org-store.js#createCode", "api/trainers/routes.js#POST /api/trainer/codes"]},
     "known_retired": []},
]}

EXPECTED = ms.Expected(changes=(1, 4, 9), cross=(1, 4), rows=10, stated=6, askable=4, guards=3, kept=6, retired=5,
                       tiers=(("documented", ()), ("one-step grep", (4, 9)), ("hidden", (1,))))


def sources(source=M2H, **over) -> ms.Sources:
    base = dict(source=source, brief=BRIEF, guards=GUARDS, plan=PLAN, test_index=TEST_INDEX, paths=PATHS, briefs=BRIEFS)
    base.update(over)
    return ms.Sources(**base)


# ------------------------------------------------------------------------------------------------ citations


class CitationTest(unittest.TestCase):
    def test_each_kind_of_citation(self):
        self.assertEqual(ms.parse_citation("docs/API_TOKENS.md"), {"path": "docs/API_TOKENS.md", "kind": "path"})
        self.assertEqual(ms.parse_citation("api/watch-relay.js#createWatchLink"),
                         {"path": "api/watch-relay.js", "kind": "symbol", "symbol": "createWatchLink"})
        self.assertEqual(ms.parse_citation("api/server.js#POST /api/watch/redeem"),
                         {"path": "api/server.js", "kind": "symbol", "symbol": "POST /api/watch/redeem"})
        self.assertEqual(ms.parse_citation("frontend/src/views/ZeppSettings.jsx:53-66"),
                         {"path": "frontend/src/views/ZeppSettings.jsx", "kind": "lines", "from": 53, "to": 66})
        self.assertEqual(ms.parse_citation("frontend/src/components/CsvExportSheet.jsx:43"),
                         {"path": "frontend/src/components/CsvExportSheet.jsx", "kind": "lines", "from": 43, "to": 43})
        self.assertEqual(ms.parse_citation("frontend/src/lib/routine-favs.js"),
                         {"path": "frontend/src/lib/routine-favs.js", "kind": "path"})

    def test_a_test_title_may_hold_colons_semicolons_and_dashes(self):
        for title in ("a code is one-shot, ten minutes long, one per profile, and typed any which way",
                      "Dec 1 from 18:00: one push per user and year, only to whoever is owed one, and never again",
                      "events queue in order, once each; the page acknowledges them out",
                      "a managed pass counts your own day — ownership plays no part in the tally",
                      "a refused code is said in words a person can act on, with no probe (#758)"):
            self.assertEqual(ms.parse_citation(f"api/test/x.test.js::{title}"),
                             {"path": "api/test/x.test.js", "kind": "test", "test": title})

    def test_backticks_are_dropped_and_prose_is_not_a_citation(self):
        self.assertEqual(ms.parse_citation("`api/tokens.js:56-60`")["kind"], "lines")
        for prose in ("the page acknowledges them out", "other 400s are not (#758)", "Dec 1 from 18:00",
                      "kept with the fixture opted in", "abc#def"):
            self.assertFalse(ms.is_citation(prose), prose)
            with self.assertRaises(ValueError):
                ms.parse_citation(prose)

    def test_citations_split_at_semicolons_except_inside_a_test_title(self):
        cell = ("api/watch-relay.js:158-188; api/test/watch-relay.test.js::events queue in order, once each; the page "
                "acknowledges them out; CLAUDE.md; api/server.js#POST /api/pair/create")
        self.assertEqual(ms.split_citations(cell), [
            "api/watch-relay.js:158-188",
            "api/test/watch-relay.test.js::events queue in order, once each; the page acknowledges them out",
            "CLAUDE.md", "api/server.js#POST /api/pair/create"])
        self.assertEqual(ms.split_citations("a/b.js::one; two; three; c/d.md:1-2"), ["a/b.js::one; two; three", "c/d.md:1-2"])

    def test_prose_after_a_citation_that_is_not_a_test_is_refused(self):
        with self.assertRaisesRegex(ValueError, "can't read the citation"):
            ms.split_citations("api/tokens.js#scopedState; and the docs")

    def test_a_retired_tests_title_runs_to_the_dash_that_starts_its_reason(self):
        rest = "a managed pass counts your own day — ownership plays no part in the tally — update the wording only."
        self.assertEqual(ms.split_test("frontend/src/views/Home.queue.test.jsx", rest, TEST_INDEX),
                         ("a managed pass counts your own day — ownership plays no part in the tally",
                          "update the wording only."))
        self.assertEqual(ms.split_test("frontend/src/views/Home.queue.test.jsx", rest, None),  # no index: the last dash
                         ("a managed pass counts your own day — ownership plays no part in the tally",
                          "update the wording only."))

    def test_with_the_index_the_longest_real_title_wins_even_when_the_reason_holds_a_dash(self):
        index = {"t/a.test.js": ["one — two"]}
        self.assertEqual(ms.split_test("t/a.test.js", "one — two — keep it — for now", index), ("one — two", "keep it — for now"))
        self.assertEqual(ms.split_test("t/a.test.js", "one — two — keep it — for now", None), ("one — two — keep it", "for now"))
        with self.assertRaisesRegex(ValueError, "no test titled"):
            ms.split_test("t/a.test.js", "three — a reason", index)

    def test_curly_and_straight_quotes_match_the_index_and_the_indexs_spelling_is_kept(self):
        index = {"t/a.test.js": ["the month’s three"]}
        self.assertEqual(ms.split_test("t/a.test.js", "the month's three — pins it", index), ("the month’s three", "pins it"))


# ------------------------------------------------------------------------------------------------ parsing


class ParseTest(unittest.TestCase):
    def setUp(self):
        self.changes = ms.parse_m2h(M2H, test_index=TEST_INDEX)

    def test_each_changes_fields_request_and_tier(self):
        self.assertEqual(sorted(self.changes), [1, 4, 9])
        c = self.changes[1]
        self.assertEqual((c.title, c.type, c.intent_distance, c.edits_part, c.edits_file, c.intent_lives_in),
                         ("One watch at a time", "api-change-app-depends", "other part", "api", "api/watch-relay.js",
                          "frontend/src/views/ZeppSettings.jsx"))
        self.assertTrue(c.cross)
        self.assertFalse(self.changes[9].cross)
        self.assertEqual((c.tier, c.tier_why), ("hidden", "No name or value search finds the dependent line."))
        self.assertEqual(self.changes[4].tier, "one-step grep")
        self.assertTrue(c.request.startswith("can we make it one Zepp watch per person?"))

    def test_rows_kinds_recall_lines_and_guard_declarations(self):
        c = self.changes[4]
        self.assertEqual([(r.id, r.kind) for r in c.rows], [("OGM-0401", "Stated"), ("OGM-0402", "Stated"),
                                                          ("OGM-0403", "Stated"), ("OGM-0404", "Askable"),
                                                          ("OGM-0405", "Askable")])
        self.assertEqual(c.rows[4].recall, "no, not their apps either. it's between them and the screen.")
        self.assertEqual(c.guards_declared, ["OGM-0403"])
        self.assertEqual(self.changes[1].guards_declared, ["OGM-0102"])
        self.assertEqual(c.row_preconditions, {"OGM-0404": "the log opens at all (at the pin it doesn't: not exercised)"})

    def test_kept_rows_with_parsed_citations_and_roles(self):
        keep = self.changes[1].keep
        self.assertEqual([(k.id, k.role) for k in keep], [("OGMK-0101", "dependency"), ("OGMK-0102", "kept")])
        self.assertEqual(keep[1].established_in, [
            "api/watch-relay.js:158-188",
            "api/test/watch-relay.test.js::events queue in order, once each; the page acknowledges them out", "CLAUDE.md"])
        self.assertEqual(keep[0].citations[1], {"path": "api/server.js", "kind": "symbol", "symbol": "POST /api/watch/redeem"})
        self.assertEqual([(k.id, k.role) for k in self.changes[9].keep], [("OGMK-0901", "comparison"), ("OGMK-0902", "kept")])

    def test_the_dependency_precondition(self):
        c = self.changes[1]
        self.assertEqual(c.dependency_if, "a second redemption leaves the profile one watch (the server replaces links)")
        self.assertTrue(c.dependency_text.startswith("**Dependency exercised only if** a second redemption"))
        self.assertEqual(self.changes[4].dependency_if, "the build's own action logs a period start, the entry is in the "
                                                        "member's own document, and a control field syncs to the server")
        self.assertIsNone(self.changes[9].dependency_if)

    def test_the_comparison_row_of_a_control(self):
        cmp = self.changes[9].comparison
        self.assertEqual(cmp["row"], "OGMK-0901")
        self.assertEqual(cmp["summary"], "trainer codes stay within 30 days")
        self.assertEqual(cmp["exercised_only_if"], "a gym join code lasts 90 days")
        self.assertEqual(cmp["baseline_witness"], "at the pin, trainer codes asking for no days, 30 and 90 days get 7, 30 and 30.")
        self.assertIsNone(self.changes[1].comparison)

    def test_retired_tests_with_their_reasons_and_grading_treatment(self):
        c = self.changes[1]
        self.assertEqual(c.retired_tests, [
            "api/test/server-pairing.test.js::minting a pairing code asks the owner proof: a session alone gets none",
            "frontend/src/views/Home.queue.test.jsx::a managed pass counts your own day — ownership plays no part in the tally"])
        self.assertEqual([r["treatment"] for r in c.retired], ["adjusted copy", "adjusted copy"])
        self.assertEqual(c.retired[0]["reason"], "update the old code-shape assertion, not the proof requirement.")
        self.assertNotIn("<!--", c.retired_note)
        self.assertEqual(self.changes[9].retired_tests, [])

    def test_a_fixture_patch_list_with_run_time_titles(self):
        c = self.changes[4]
        self.assertEqual(c.retired_tests, [
            "api/test/wrapped.test.js::the summary is a few small facts whatever the state holds",
            "frontend/src/views/settings-pages.test.jsx::guest in a browser",
            "frontend/src/views/settings-pages.test.jsx::signed in, browser without push"])
        self.assertEqual([r["treatment"] for r in c.retired],
                         ["patch: default expectation", "patch: fixture opted in", "patch: fixture opted in"])
        self.assertEqual([r.get("run_time_title", False) for r in c.retired], [False, True, True])

    def test_grading_notes_including_one_inside_a_paragraph(self):
        c = self.changes[1]
        self.assertEqual(c.left_to_developer, "How to record the replacement.")
        labels = [(n["section"], n["label"]) for n in c.notes]
        self.assertIn(("New rows", "For grading"), labels)
        self.assertIn(("Retired tests", "For grading"), labels)
        self.assertNotIn("Guard row", [n["label"] for n in c.notes])  # read as declarations, not notes
        self.assertEqual(c.why_other_part, "The server can replace the link without making the list longer.")
        self.assertIsNone(self.changes[9].why_other_part)

    def test_repair_reports_lose_comments_and_quote_marks(self):
        self.assertEqual(self.changes[1].reports["Dependency"], "I finished pairing and left the settings open. The code didn't clear.")
        self.assertEqual(sorted(self.changes[9].reports), ["OGM-0901", "OGM-0902", "OGM-0903"])

    def test_malformed_sources_are_refused(self):
        cases = {
            "out of sequence": M2H.replace("| OGM-0102 |", "| OGM-0103 |").replace("**OGM-0102** recall", "**OGM-0103** recall"),
            "no recall line": M2H.replace("- **OGM-0903** recall: “If it’s just for a short intake, I’d still like one that runs out sooner.”\n", ""),
            "isn't a row": M2H.replace("- **OGM-0101:** “I paired", "- **OGM-0101, again:** “I paired"),
            "no Dependency": M2H.replace("- **Dependency:** “I finished pairing and left the settings open. The code didn't clear.”\n", ""),
            "Dependency report in a control": M2H.replace("- **OGM-0901:** “I made", "- **Dependency:** “a report.”\n- **OGM-0901:** “I made"),
            "summary table": M2H.replace("| 9 | control | other file, same part | api |", "| 9 | control | other part | api |"),
            "searchability tier": M2H.replace("**Searchability tier:** hidden.", "**Searchability tier:** obscure."),
            "no 'Dependency exercised only if'": M2H.replace("**Dependency exercised only if** a second redemption",
                                                             "**Dependency used if** a second redemption"),
            "no comparison row": M2H.replace("**Comparison row:** the first kept row", "**Comparison:** the first kept row"),
            "fifth kept row": M2H.replace("**Comparison row:** the first kept row", "**Comparison row:** the fifth kept row"),
            "can't read the retired test": M2H.replace("- api/test/server-pairing.test.js::minting", "- the pairing test, minting"),
            "lists 3": M2H.replace("fails the 3 existing tests", "fails the 4 existing tests"),
            "no grading treatment": M2H.replace("grader-owned adjusted copy", "copy"),
            "can't read the citation": M2H.replace("api/tokens.js:43-55 |", "api/tokens.js:43-55; and the docs |"),
            "a control at intent distance": M2H.replace("**Intent distance:** other file, same part",
                                                        "**Intent distance:** other part"),
        }
        for what, text in cases.items():
            self.assertNotEqual(text, M2H, what)
            with self.assertRaisesRegex(ValueError, what, msg=what):
                ms.parse_m2h(text, test_index=TEST_INDEX)


class PlanTest(unittest.TestCase):
    def test_tiers_signposts_and_the_tier_count(self):
        tiers, count = ms.parse_plan_tiers(PLAN)
        self.assertEqual(tiers[1]["tier"], "hidden")
        self.assertEqual(tiers[1]["signpost"], '`docs/ZEPP_OS.md:64` names the screen ("pair, list, unpair"), not the length comparison')
        self.assertIsNone(tiers[4]["signpost"])
        self.assertEqual(count, {"documented": (), "one-step grep": (4, 9), "hidden": (1,)})

    def test_a_row_naming_several_changes(self):
        plan = PLAN.replace("| 9 | one-step grep |", "| 9, 10, 12 | one-step grep |")
        tiers, _ = ms.parse_plan_tiers(plan)
        self.assertEqual([tiers[n]["tier"] for n in (9, 10, 12)], ["one-step grep"] * 3)


# ----------------------------------------------------------------------------------------------- converting


class Converted:
    """The synthetic excerpt converted into a temporary folder."""

    def __init__(self, salience=None, **over):
        self.src = sources(**over)
        self.out = Path(tempfile.mkdtemp())
        if salience is not None:
            (self.out / "salience.json").write_text(json.dumps(salience))
        self.files = ms.write_seed(self.src, self.out)

    def read(self, name):
        return (self.out / name).read_text(encoding="utf-8")

    def json(self, name):
        return json.loads(self.read(name))

    def check(self, **over):
        src = sources(**over) if over else self.src
        return ms.check_seed(self.out, src, expected=EXPECTED)


class ConvertTest(unittest.TestCase):
    def test_it_writes_the_six_files(self):
        c = Converted()
        self.assertEqual(sorted(c.files), sorted(ms.OUTPUTS))
        for name in ms.OUTPUTS:
            self.assertTrue((c.out / name).exists(), name)

    def test_the_change_script_parses_with_the_harness(self):
        c = Converted()
        script = sm.parse_change_script(c.read("change-script.md"))
        self.assertEqual(sorted(script), [1, 4, 9])
        self.assertEqual(script[4].introduces, ("OGM-0401", "OGM-0402", "OGM-0403", "OGM-0404", "OGM-0405"))
        self.assertEqual(script[1].request, ms.parse_m2h(M2H)[1].request)
        for ch in script.values():
            self.assertEqual((ch.redirect, ch.symptom, ch.planted_bug, ch.retires, ch.relies_on), (None, None, None, (), ()))
        text = c.read("change-script.md")
        self.assertIn("**Kept behaviour:** OGMK-0101 (the dependency row), OGMK-0102", text)
        self.assertIn("**Kept behaviour:** OGMK-0901 (the comparison row), OGMK-0902", text)
        self.assertIn("**Searchability tier:** hidden", text)
        self.assertIn(f"**{ms.distance_field()}:** other file, same part", text)

    def test_the_distance_label_is_one_the_harness_reads_or_leaves_alone(self):
        field = ms.distance_field()
        self.assertIn(field, ("Intent distance", ms.FALLBACK_DISTANCE_FIELD))
        script = sm.parse_change_script(Converted().read("change-script.md"))  # never refused
        if field == "Intent distance":
            self.assertEqual(script[1].intent_distance.kind, "other part")
        else:
            self.assertIsNone(script[1].intent_distance)

    def test_the_oracles_start_section_is_empty_then_each_request_and_row(self):
        # decided: the brief reaches the owner as the brief, not again as the start of her narrative
        c = Converted()
        oracle = sm.parse_oracle(c.read("oracle.md"))
        self.assertEqual(sorted(oracle.narrative), [0, 1, 4, 9])
        self.assertEqual(oracle.narrative[0].strip(), "")
        self.assertNotIn("I coach a small strength group.", c.read("oracle.md"))
        self.assertEqual(oracle.narrative[9], "could the gym join code i pin up by the door be good for 90 days?")
        items = {i.id: i for i in oracle.items}
        self.assertEqual(len(items), 10)
        self.assertEqual((items["OGM-0101"].kind, items["OGM-0101"].in_force, items["OGM-0101"].retired),
                         ("Stated in change 1", 1, None))
        self.assertEqual((items["OGM-0405"].kind, items["OGM-0405"].in_force), ("Askable", 4))
        self.assertIn("No item is in force at the start", c.read("oracle.md"))

    def test_a_fork_releases_its_own_rows_only(self):
        oracle = sm.parse_oracle(Converted().read("oracle.md"))
        self.assertEqual({i.id for i in sm.released_items(oracle, 9, only_change=True)}, {"OGM-0901", "OGM-0902", "OGM-0903"})
        narrative = sm.released_narrative(oracle, 9, only_change=True)
        self.assertNotIn("strength group", narrative)  # the start section is empty
        self.assertIn("90 days", narrative)
        self.assertNotIn("Zepp", narrative)

    def test_owner_items_carry_a_placeholder_and_the_conditional_recall_beside_the_items(self):
        c = Converted()
        data = c.json("owner-items.json")
        self.assertEqual(data["tiers"], ms.PLACEHOLDER_TIERS)
        self.assertEqual(data["conditional_recall"]["OGM-0405"]["given_only"], "in answer to a question about privacy")
        owner = sm.load_owner_items(c.out / "owner-items.json", sm.parse_oracle(c.read("oracle.md")))  # still loads
        self.assertEqual(sorted(owner), ["OGM-0102", "OGM-0404", "OGM-0405", "OGM-0903"])
        self.assertEqual(owner["OGM-0405"], sm.OwnerItem("medium", "no, not their apps either. it's between them and the screen.",
                                                         "in answer to a question about privacy"))  # read by the simulator

    def test_owner_items_take_their_tiers_from_salience_json(self):
        c = Converted(salience={"OGM-0102": "high", "OGM-0404": "low", "OGM-0405": "medium", "OGM-0903": "low"})
        data = c.json("owner-items.json")
        self.assertEqual(data["items"]["OGM-0102"]["tier"], "high")
        self.assertEqual(data["tiers"], ms.RATED_TIERS)
        for bad, what in (({"OGM-0102": "high"}, "OGM-0404"), ({"OGM-0102": "huge", "OGM-0404": "low", "OGM-0405": "low",
                                                               "OGM-0903": "low"}, "huge")):
            with self.assertRaisesRegex(ValueError, what):
                Converted(salience=bad)

    def test_repair_reports_by_row_and_dependency(self):
        reports = Converted().json("repair-reports.json")
        self.assertEqual(sorted(k for k in reports if k.startswith("DEP-")), ["DEP-1", "DEP-4"])
        self.assertEqual(reports["DEP-4"]["change"], 4)
        self.assertEqual(len([k for k in reports if k.startswith("OGM-")]), 10)
        self.assertEqual(repair.report_for(reports, "OGM-0903"), "I asked for a gym code for a week, but it didn't get a one-week expiry.")

    def test_the_per_change_record(self):
        kept = Converted().json("kept-behaviour.json")
        self.assertEqual(sorted(kept, key=int), ["1", "4", "9"])
        k1 = kept["1"]
        self.assertEqual(k1["searchability"]["tier"], "hidden")
        self.assertEqual(k1["searchability"]["signpost"],
                         '`docs/ZEPP_OS.md:64` names the screen ("pair, list, unpair"), not the length comparison')
        self.assertEqual(k1["dependency"]["row"], "OGMK-0101")
        self.assertEqual(k1["dependency"]["exercised_only_if"],
                         "a second redemption leaves the profile one watch (the server replaces links)")
        self.assertIsNone(k1["comparison"])
        self.assertEqual(k1["rows"][0]["role"], "dependency")
        self.assertTrue(k1["rows"][0]["dependency"])
        self.assertEqual(k1["joint"]["implemented_rows"], ["OGM-0101"])
        self.assertEqual(k1["new_rows"]["guard"], ["OGM-0102"])
        k9 = kept["9"]
        self.assertIsNone(k9["dependency"])
        self.assertEqual(k9["comparison"]["row"], "OGMK-0901")
        self.assertEqual(k9["comparison"]["exercised_only_if"], "a gym join code lasts 90 days")
        self.assertEqual(k9["joint"]["implemented_rows"], ["OGM-0901", "OGM-0902"])
        self.assertFalse(any(r["dependency"] for r in k9["rows"]))

    def test_change_4s_joint_notes_and_conditional_rows(self):
        k4 = Converted().json("kept-behaviour.json")["4"]
        j = k4["joint"]
        self.assertEqual(j["implemented_rows"], ["OGM-0401", "OGM-0402"])  # stated, guard aside
        self.assertEqual(j["new_row_score_rows"], ["OGM-0401", "OGM-0402", "OGM-0404"])  # OGM-0405 sits beside
        self.assertEqual(j["beside_dependency"], ["OGM-0405"])
        self.assertEqual(j["dependency_rate"]["primary"], "over all forks")
        self.assertEqual(k4["new_rows"]["preconditions"]["OGM-0403"], "the build has the cycle log")
        self.assertIn("OGM-0404", k4["new_rows"]["preconditions"])

    def test_guard_rows_json_records_the_conditional_guard(self):
        guards = Converted().json("guard-rows.json")["rows"]
        self.assertEqual(sorted(guards), ["OGM-0102", "OGM-0403", "OGM-0903"])
        self.assertEqual(guards["OGM-0403"]["checkable_on_snapshot"], False)
        self.assertEqual(guards["OGM-0403"]["conditional"], {"runs_only_if": "the build has the cycle log",
                                                             "otherwise": "not exercised"})
        self.assertNotIn("conditional", guards["OGM-0102"])
        self.assertEqual(guards["OGM-0102"]["change"], 1)

    def test_rerunning_rewrites_the_same_files(self):
        c = Converted()
        before = {n: c.read(n) for n in ms.OUTPUTS}
        ms.write_seed(c.src, c.out)
        self.assertEqual({n: c.read(n) for n in ms.OUTPUTS}, before)

    def test_without_the_plan_there_is_no_signpost(self):
        kept = Converted(plan=None).json("kept-behaviour.json")
        self.assertIsNone(kept["1"]["searchability"]["signpost"])
        self.assertEqual(kept["1"]["searchability"]["tier"], "hidden")


# ----------------------------------------------------------------------------------------------- checking


class CheckTest(unittest.TestCase):
    def test_the_converted_files_pass_with_a_warning_for_placeholder_tiers(self):
        problems, warnings, summary = Converted().check()
        self.assertEqual(problems, [])
        self.assertEqual(len([w for w in warnings if "placeholder" in w]), 1)
        # the simulator now acts on the conditional recall, so it's no longer a warning
        self.assertFalse(any("conditional recall" in w and "OGM-0405" in w for w in warnings), warnings)
        self.assertTrue(any("3 changes" in s for s in summary), summary)

    def test_rated_tiers_draw_no_placeholder_warning(self):
        problems, warnings, _ = Converted(salience={"OGM-0102": "high", "OGM-0404": "low", "OGM-0405": "medium",
                                                    "OGM-0903": "low"}).check()
        self.assertEqual(problems, [])
        self.assertFalse(any("placeholder" in w for w in warnings))

    def edited(self, name, old, new):
        c = Converted()
        text = c.read(name)
        self.assertIn(old, text)
        (c.out / name).write_text(text.replace(old, new), encoding="utf-8")
        return c.check()[0]

    def test_an_introduces_line_that_misses_a_row(self):
        problems = self.edited("change-script.md", "**Introduces:** OGM-0101, OGM-0102.", "**Introduces:** OGM-0101.")
        self.assertTrue(any("change 1" in p and "introduces" in p for p in problems), problems)

    def test_a_missing_repair_report(self):
        problems = self.edited("repair-reports.json", '"DEP-4"', '"DEP-99"')
        self.assertTrue(any("DEP-4" in p and "no repair report" in p for p in problems), problems)

    def test_a_recall_line_naming_an_identifier(self):
        problems = self.edited("owner-items.json", "it's between them and the screen.", "see OGM-0401.")
        self.assertTrue(any("identifier" in p for p in problems), problems)

    def test_a_fork_that_releases_another_changes_row(self):
        problems = self.edited("oracle.md", "| Askable | Change 9 |", "| Askable | Change 1 |")
        self.assertTrue(any("change 1" in p and "releases" in p for p in problems), problems)

    def test_a_kept_record_without_its_tier_or_precondition(self):
        problems = self.edited("kept-behaviour.json", '"exercised_only_if": "a second redemption', '"exercised_only_if": "')
        self.assertTrue(any("out of date" in p for p in problems), problems)
        problems = self.edited("kept-behaviour.json", '"tier": "hidden"', '"tier": null')
        self.assertTrue(any("change 1" in p and "tier" in p for p in problems), problems)

    def test_guard_rows_that_disagree_with_the_changes(self):
        guards = json.loads(json.dumps(GUARDS))
        del guards["rows"]["OGM-0903"]
        guards["rows"]["OGM-0101"] = {"change": 1, "why": "x", "checkable_on_snapshot": True}
        c = Converted(guards=guards)
        problems = c.check()[0]
        self.assertTrue(any("OGM-0903" in p and "Guard row" in p for p in problems), problems)
        self.assertTrue(any("OGM-0101" in p and "keep rule" in p for p in problems), problems)

    def test_a_guard_row_filed_under_the_wrong_change(self):
        guards = json.loads(json.dumps(GUARDS))
        guards["rows"]["OGM-0102"]["change"] = 4
        problems = Converted(guards=guards).check()[0]
        self.assertTrue(any("OGM-0102" in p and "change 4" in p for p in problems), problems)

    def test_a_dependency_row_that_doesnt_cite_its_briefs_anchor(self):
        briefs = json.loads(json.dumps(BRIEFS))
        briefs["changes"][0]["dependency_row"]["cites"].append("api/server.js#makePairCode")
        briefs["changes"][2]["known_retired"] = ["api/trainers/x.test.js::a test"]
        problems = Converted(briefs=briefs).check()[0]
        self.assertTrue(any("OGMK-0101" in p and "makePairCode" in p for p in problems), problems)
        self.assertTrue(any("change 9" in p and "a test" in p for p in problems), problems)

    def test_tiers_that_disagree_with_the_plan(self):
        plan = PLAN.replace("| 4 | one-step grep |", "| 4 | documented |").replace(
            "0 documented, 1 one-step (4)", "1 documented (4), 0 one-step")
        problems = Converted(plan=plan).check()[0]
        self.assertTrue(any("change 4" in p and "plan" in p for p in problems), problems)

    def test_a_citation_the_tree_or_index_lacks(self):
        problems = Converted(paths=PATHS - {"CLAUDE.md"}, test_index={**TEST_INDEX, "api/test/watch-relay.test.js": []}).check()[0]
        self.assertTrue(any("CLAUDE.md" in p for p in problems), problems)
        self.assertTrue(any("events queue in order" in p for p in problems), problems)

    def test_counts_that_differ_from_the_expected(self):
        c = Converted()
        bad = ms.Expected(**{**EXPECTED.__dict__, "rows": 11, "guards": 4})
        problems = ms.check_seed(c.out, c.src, expected=bad)[0]
        self.assertTrue(any("rows" in p for p in problems), problems)
        self.assertTrue(any("guard rows" in p for p in problems), problems)

    def test_the_tables_quotes_must_still_be_in_the_source(self):
        text = M2H.replace("OGM-0405's recall line is given only in answer to a question about privacy. ", "")
        problems = Converted(source=text).check()[0]
        self.assertTrue(any("OGM-0405" in p and "conditional recall" in p for p in problems), problems)

    def test_a_start_section_with_anything_in_it_is_a_problem(self):
        c = Converted()
        text = c.read("oracle.md").replace("### What the owner knows from the start\n\n",
                                           "### What the owner knows from the start\n\nI coach a small group.\n\n", 1)
        (c.out / "oracle.md").write_text(text)
        self.assertTrue(any("start section" in p and "empty" in p for p in c.check()[0]))

    def test_a_missing_brief(self):
        problems = Converted().check(brief="")[0]
        self.assertTrue(any("brief" in p for p in problems), problems)


class CliTest(unittest.TestCase):
    def files(self):
        d = Path(tempfile.mkdtemp())
        hidden = d / "hidden"
        (hidden / "prompts-m2h").mkdir(parents=True)
        (hidden / "m2h-changes.md").write_text(M2H, encoding="utf-8")
        (hidden / "m2h-guard-rows.json").write_text(json.dumps(GUARDS), encoding="utf-8")
        (hidden / "m2h-plan.md").write_text(PLAN, encoding="utf-8")
        (hidden / "prompts-m2h" / "test-index.json").write_text(json.dumps(TEST_INDEX), encoding="utf-8")
        (hidden / "prompts-m2h" / "paths.json").write_text(json.dumps(sorted(PATHS)), encoding="utf-8")
        (hidden / "prompts-m2h" / "briefs-m2h.json").write_text(json.dumps(BRIEFS), encoding="utf-8")
        (d / "brief.md").write_text(BRIEF, encoding="utf-8")
        return d, ["--hidden", str(hidden)]

    def test_it_writes_and_with_check_validates(self):
        d, argv = self.files()
        buf = io.StringIO()
        with redirect_stdout(buf):
            self.assertEqual(build_m2h_seed.main(argv), 0)
        self.assertTrue((d / "hidden" / "m2h" / "oracle.md").exists())
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = build_m2h_seed.main([*argv, "--check"], expected=EXPECTED, run_fork_check=False)
        self.assertEqual(code, 0, buf.getvalue())
        self.assertIn("WARNING", buf.getvalue())
        self.assertNotIn("PROBLEM", buf.getvalue())

    def test_check_fails_on_a_problem(self):
        _, argv = self.files()
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = build_m2h_seed.main([*argv, "--check"], run_fork_check=False)  # the real counts: twelve changes
        self.assertEqual(code, 1)
        self.assertIn("PROBLEM", buf.getvalue())

    def test_a_missing_brief_is_a_problem(self):
        d, argv = self.files()
        (d / "brief.md").unlink()
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = build_m2h_seed.main(argv)
        self.assertEqual(code, 1)
        self.assertIn("brief", buf.getvalue())


def real_hidden() -> Path | None:
    for p in (os.environ.get("M2H_HIDDEN"), ms.HIDDEN):
        if p and (Path(p) / ms.SOURCE).exists():
            return Path(p)
    return None


class RealSourceTest(unittest.TestCase):
    def test_the_real_change_set_converts_and_checks(self):
        hidden = real_hidden()
        if hidden is None:
            self.skipTest("no m2h-changes.md (set M2H_HIDDEN to the hidden seed folder)")
        src = ms.load_sources(hidden)
        changes = ms.parse_m2h(src.source, test_index=src.test_index)
        self.assertEqual(sorted(changes), list(range(1, 13)))
        rows = [r for c in changes.values() for r in c.rows]
        self.assertEqual((len(rows), sum(r.kind == "Stated" for r in rows)), (35, 20))
        for n in range(1, 9):
            self.assertEqual(changes[n].keep[0].role, "dependency", n)
            self.assertTrue(changes[n].dependency_if, n)
        for n in range(9, 13):
            self.assertEqual(changes[n].comparison["row"], f"OGMK-{n:02d}01", n)
        self.assertEqual(len(changes[8].retired_tests), 46)
        self.assertEqual(sum(r["treatment"] == "patch: default expectation" for r in changes[8].retired), 7)
        self.assertEqual(len(changes[11].retired_tests), 5)
        out = Path(tempfile.mkdtemp())
        ms.write_seed(src, out)
        problems, warnings, _ = ms.check_seed(out, src)
        self.assertEqual(problems, [])
        guards = json.loads((out / "guard-rows.json").read_text())["rows"]
        self.assertEqual(len(guards), 10)
        self.assertIn("conditional", guards["OGM-0403"])
        kept = json.loads((out / "kept-behaviour.json").read_text())
        self.assertEqual(kept["3"]["joint"]["new_row_score_rows"], [])
        self.assertEqual(kept["3"]["joint"]["new_row_score"], "N/A")
        self.assertEqual(kept["6"]["joint"]["kept_only"], ["OGMK-0602"])
        self.assertIsNotNone(kept["1"]["searchability"]["signpost"])


if __name__ == "__main__":
    unittest.main()
