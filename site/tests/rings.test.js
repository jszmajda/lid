// Checks the rings drawing's module: its card states, its pacing, and its static drawing.
// Run from the repository root:
//   node --test site/tests/rings.test.js
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { fileURLToPath } from "node:url";
import {
  NARROWING,
  CHANGE,
  BEFORE,
  activeCard,
  plan,
  createPlayer,
  finalState,
  labelsFor,
  ringsFor,
  radius,
  classify,
  makeDots,
  renderStatic,
} from "../src/assets/js/rings.js";

const moduleSource = readFileSync(join(dirname(fileURLToPath(import.meta.url)), "../src/assets/js/rings.js"), "utf8");
const steps = (card) => card.map(([, state]) => state);

describe("pacing", () => {
  // @spec MKT-SITE-113
  it("follows the last card whose top has passed the line", () => {
    assert.equal(activeCard([900, 1200, 1500], 500), -1, "no card has reached the line");
    assert.equal(activeCard([300, 700, 1100], 500), 0);
    assert.equal(activeCard([-400, 100, 450, 800], 500), 2);
    assert.deepEqual(BEFORE.narrowing, NARROWING[0][0][1], "before the first card, the narrowing explainer shows the empty field");
    assert.deepEqual(BEFORE.change, finalState(NARROWING[NARROWING.length - 1]), "the change explainer starts where narrowing ends");
  });

  // @spec MKT-SITE-114
  it("plays a card's steps once and cancels what's left when the card changes", () => {
    const pending = new Map();
    let next = 0;
    const applied = [];
    const player = createPlayer(
      (state) => applied.push(state),
      (fn, delay) => { const id = next++; pending.set(id, { fn, delay }); return id; },
      (id) => pending.delete(id),
    );
    player.play(CHANGE[2]);
    assert.equal(pending.size, CHANGE[2].length, "every step is scheduled once");
    pending.get(0).fn();
    player.play(CHANGE[3]);
    assert.equal(pending.size, CHANGE[3].length, "the earlier card's unplayed steps are cancelled");
    assert.deepEqual(applied, [CHANGE[2][0][1]]);
  });

  // @spec MKT-SITE-115
  it("goes straight to each card's final state under reduced motion", () => {
    for (const card of [...NARROWING, ...CHANGE]) {
      const p = plan(card, true);
      assert.equal(p.length, 1);
      assert.equal(p[0][0], 0);
      assert.deepEqual(p[0][1], finalState(card));
    }
    assert.deepEqual(plan(CHANGE[3], false), CHANGE[3]);
  });

  // @spec MKT-SITE-118
  it("listens only to scrolling and stores nothing", () => {
    const events = [...moduleSource.matchAll(/addEventListener\(\s*["'](\w+)["']/g)].map((m) => m[1]);
    assert.ok(events.length > 0);
    for (const event of events) assert.ok(["scroll", "resize", "DOMContentLoaded"].includes(event), `listens to ${event}`);
    assert.doesNotMatch(moduleSource, /localStorage|sessionStorage|document\.cookie|indexedDB|fetch\(/);
  });
});

describe("what each card shows", () => {
  // @spec MKT-SITE-119
  it("rounds every ring by a fifth of its shorter side", () => {
    for (const card of [...NARROWING, ...CHANGE]) {
      for (const state of steps(card)) {
        for (const ring of ringsFor(state)) {
          assert.equal(radius(ring), Math.min(ring.w, ring.h) / 5);
        }
      }
    }
  });

  // @spec MKT-SITE-120
  it("names each level only once its card has", () => {
    const shown = NARROWING.map((card) => labelsFor(finalState(card)));
    assert.deepEqual(shown[0], []);
    assert.deepEqual(shown[1], ["HLD"]);
    assert.deepEqual(shown[2], ["HLD", "tenet"]);
    assert.deepEqual(shown[3], ["HLD", "tenet", "LLD"]);
    assert.deepEqual(shown[4], ["HLD", "tenet", "LLD", "TRIAL-003"]);
    const drafts = steps(CHANGE[2]).map(labelsFor).flat().filter((label) => label.startsWith("draft"));
    assert.deepEqual([...new Set(drafts)], ["draft 1", "draft 2"]);
  });

  // @spec MKT-SITE-121
  it("stops ruling programs out while a level is in question", () => {
    const loose = finalState(CHANGE[0]);
    assert.deepEqual(loose.recheck, ["lld", "e1", "e2", "e3"]);
    assert.equal(loose.code, 1, "the code turns hollow");
    assert.ok(!loose.test, "the test target lifts");
    const dots = makeDots();
    const settled = classify(finalState(NARROWING[5]), dots);
    const open = classify(loose, dots);
    const reopened = dots.filter((_, i) => settled[i] > 0 && open[i] === 0);
    assert.ok(reopened.length > 10, "programs inside the re-checked rings brighten again");
  });

  // @spec MKT-SITE-122
  it("checks each level that holds and crosses out draft 1", () => {
    const end = finalState(CHANGE[3]);
    assert.deepEqual([...end.checked].sort(), ["e1", "e2", "e3", "hld", "lld", "tenet"]);
    const draft1 = steps(CHANGE[2]).filter((s) => s.lldName === "draft 1");
    assert.ok(draft1.some((s) => s.reject), "draft 1 gets an ✗");
    assert.ok(steps(CHANGE[2]).filter((s) => s.lldName === "draft 2").every((s) => !s.reject));
    assert.ok(finalState(CHANGE[2]).checked.includes("lld"), "the approved design is checked");
  });

  // @spec MKT-SITE-123
  it("follows the @spec link before TRIAL-003 moves, then fails, then passes", () => {
    const seq = steps(CHANGE[3]);
    const lit = seq.findIndex((s) => s.thread === 2);
    const moved = seq.findIndex((s) => s.target === 1);
    const failing = seq.findIndex((s) => s.target === 1 && s.test === 1);
    const passing = seq.findIndex((s) => s.codeAt === 1 && s.test === 2);
    assert.ok(lit >= 0 && lit < moved && moved <= failing && failing < passing);
    assert.equal(seq[lit].target ?? 0, 0);
  });

  // @spec MKT-SITE-124
  it("leaves one program once the test holds", () => {
    const dots = makeDots();
    const before = classify(finalState(NARROWING[4]), dots);
    const after = classify(finalState(NARROWING[5]), dots);
    assert.ok(before.filter((level) => level === 0).length >= 3, "a few programs fit the requirements");
    assert.equal(after.filter((level) => level === 0).length, 1, "the test picks one");
  });
});

describe("the static drawing", () => {
  // @spec MKT-SITE-111, MKT-SITE-117
  it("renders a described SVG, with or without labels", () => {
    const state = finalState(NARROWING[5]);
    const unlabeled = renderStatic(state, { labels: false, uid: "t1", title: "Rings", desc: "A field of programs." });
    assert.match(unlabeled, /^<svg[^>]*role="img"/);
    assert.match(unlabeled, /<title[^>]*>Rings<\/title>/);
    assert.match(unlabeled, /<desc[^>]*>A field of programs\.<\/desc>/);
    assert.doesNotMatch(unlabeled, />(HLD|LLD|tenet|TRIAL-003)</);
    const labeled = renderStatic(state, { labels: true, uid: "t2", title: "Rings", desc: "x" });
    assert.match(labeled, />HLD</);
    assert.match(labeled, />TRIAL-003</);
  });
});
