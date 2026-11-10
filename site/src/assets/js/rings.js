// The rings drawing: every program that would satisfy a request is a dot, and each level of
// design is a ring around the programs it still allows. One module serves both uses. At build
// time, src/_data/rings.js calls renderStatic() for the hero and for each explainer's fallback;
// in the browser, mount() animates the explainers as the reader scrolls. Both draw through the
// same draw(), so the static and the animated drawing cannot drift apart.
// @spec MKT-SITE-111, MKT-SITE-113, MKT-SITE-114, MKT-SITE-115, MKT-SITE-117, MKT-SITE-118, MKT-SITE-119, MKT-SITE-120, MKT-SITE-121, MKT-SITE-122, MKT-SITE-123, MKT-SITE-124

export const W = 640;
export const H = 420;

// Geometry, in viewBox units. Every ring is a rounded rectangle.
export const HLD = { x: 52, y: 34, w: 536, h: 352 };
export const TENET = { x: 52, y: 34, w: 150, h: 352 };
export const TENET_EDGE = TENET.x + TENET.w;
export const LLD = {
  L0: { x: 224, y: 90, w: 304, h: 240 },
  L1: { x: 244, y: 98, w: 300, h: 226 },
  PROBE: { x: 184, y: 94, w: 304, h: 236 },
};
// TRIAL-001 and TRIAL-002 are wide rings that hold whatever the trial's end does;
// TRIAL-003 is the small ring that picks the program, and the only one that moves.
export const E1 = { x: 272, y: 168, w: 210, h: 84 };
export const E2 = { x: 332, y: 122, w: 92, h: 176 };
export const PROGRAMS = [{ x: 354, y: 194 }, { x: 394, y: 226 }];
export function e3For(p) {
  return { x: p.x - 26, y: p.y - 22, w: 52, h: 44 };
}
// The two programs TRIAL-003 closes on, plus two more inside each of its positions,
// so a few programs fit the requirements until a test picks one.
const FIXED = [...PROGRAMS, { x: 369, y: 203 }, { x: 340, y: 206 }, { x: 409, y: 235 }, { x: 380, y: 238 }];

export function rng(seed) {
  let a = seed;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// The field of programs. Seeded, so it is the same on every load and at build time.
export function makeDots(seed = 37) {
  const r = rng(seed);
  const out = FIXED.map((p) => ({ x: p.x, y: p.y }));
  for (let n = 0; out.length < 160 && n < 9000; n++) {
    const x = 14 + r() * (W - 28);
    const y = 14 + r() * (H - 28);
    if (out.every((p) => (p.x - x) ** 2 + (p.y - y) ** 2 >= 17 * 17)) out.push({ x, y });
  }
  return out;
}

export function radius(g) {
  return Math.min(g.w, g.h) / 5;
}

export function inside(p, g, pad = 0) {
  const x0 = g.x + pad, y0 = g.y + pad, x1 = g.x + g.w - pad, y1 = g.y + g.h - pad;
  if (p.x < x0 || p.x > x1 || p.y < y0 || p.y > y1) return false;
  const r = Math.max(0, radius(g) - pad);
  const cx = Math.min(Math.max(p.x, x0 + r), x1 - r);
  const cy = Math.min(Math.max(p.y, y0 + r), y1 - r);
  return (p.x - cx) ** 2 + (p.y - cy) ** 2 <= r * r;
}

const n = (v) => (Math.round(v * 100) / 100).toString();

// A rounded rectangle as a path. Small filled shapes stay paths, not <rect>s,
// because of a Firefox Android paint bug with small filled rects.
export function roundedPath(x, y, w, h, r) {
  r = Math.min(r, w / 2, h / 2);
  return `M${n(x + r)} ${n(y)}H${n(x + w - r)}A${n(r)} ${n(r)} 0 0 1 ${n(x + w)} ${n(y + r)}V${n(y + h - r)}A${n(r)} ${n(r)} 0 0 1 ${n(x + w - r)} ${n(y + h)}H${n(x + r)}A${n(r)} ${n(r)} 0 0 1 ${n(x)} ${n(y + h - r)}V${n(y + r)}A${n(r)} ${n(r)} 0 0 1 ${n(x + r)} ${n(y)}Z`;
}

// ── Card states ─────────────────────────────────────────────────────────────
// A state names which levels show, where the LLD sits and what its label says, which program
// TRIAL-003 closes on, whether a test aims (1) or holds (2), whether the code is in doubt (1)
// or built (2), whether the @spec link shows (1) or is being followed (2), which rings are being
// re-checked, which hold, and whether the draft on show is ruled out.
const NARROW = { hld: 1, tenet: 1, lld: 1, ears: 1 };
const DONE = { ...NARROW, test: 2, code: 2, thread: 1 };
const ALL_LEVELS = ["hld", "tenet", "lld", "e1", "e2", "e3"];

export const NARROWING = [
  [[0, {}]],
  [[0, { hld: 1 }]],
  [[0, { hld: 1, tenet: 1 }]],
  [[0, { hld: 1, tenet: 1, lld: 1 }]],
  [[0, NARROW]],
  [[0, { ...NARROW, test: 1 }], [1500, DONE]],
];

const RECHECK = { ...NARROW, code: 1, thread: 1, recheck: ["lld", "e1", "e2", "e3"] };
const HOLDS = { ...RECHECK, checked: ["hld", "tenet"] };
const FOUND = { ...HOLDS, lldGeo: "L1", recheck: ["e1", "e2", "e3"], checked: ["hld", "tenet", "lld"], phase: "d2ok" };
const KEPT = { ...NARROW, code: 1, thread: 1, lldGeo: "L1", recheck: ["e3"], checked: ["hld", "tenet", "lld", "e1", "e2"] };

export const CHANGE = [
  [[0, RECHECK]],
  [[0, HOLDS]],
  [
    [0, { ...HOLDS, lldGeo: "PROBE", lldName: "draft 1", phase: "d1" }],
    [800, { ...HOLDS, lldGeo: "PROBE", lldName: "draft 1", hit: 1, reject: 1, phase: "d1x" }],
    [2300, { ...HOLDS, lldGeo: "L1", lldName: "draft 2", phase: "d2" }],
    [3300, FOUND],
  ],
  [
    [0, KEPT],
    [800, { ...KEPT, thread: 2 }],
    [1500, { ...KEPT, thread: 2, target: 1 }],
    [2400, { ...KEPT, thread: 2, target: 1, recheck: [], checked: ALL_LEVELS, test: 1, testAt: 1 }],
    [3400, { ...DONE, lldGeo: "L1", target: 1, testAt: 1, codeAt: 1, checked: ALL_LEVELS }],
  ],
];

export const HERO = DONE;
export const BEFORE = { narrowing: NARROWING[0][0][1], change: DONE };

export function finalState(card) {
  return card[card.length - 1][1];
}

// The rings a state shows, in drawing order.
export function ringsFor(state) {
  const rings = [];
  if (state.hld) rings.push(HLD);
  if (state.lld) rings.push(LLD[state.lldGeo || "L0"]);
  if (state.ears) rings.push(E1, E2, e3For(PROGRAMS[state.target || 0]));
  return rings;
}

// The labels a state shows, in drawing order. A label arrives with the card that names its level.
export function labelsFor(state) {
  const labels = [];
  if (state.hld) labels.push("HLD");
  if (state.tenet) labels.push("tenet");
  if (state.lld) labels.push(state.lldName || "LLD");
  if (state.ears) labels.push("TRIAL-003");
  return labels;
}

// How far each program fades: 0 is a program still allowed; each constraint it breaks adds one.
// A ring being re-checked rules nothing out. Once a test holds, it leaves only the program it aims at.
export function classify(state, dots) {
  const recheck = new Set(state.recheck || []);
  const lld = LLD[state.lldGeo || "L0"];
  const ears = [["e1", E1], ["e2", E2], ["e3", e3For(PROGRAMS[state.target || 0])]];
  const tested = state.test === 2 ? dots[state.testAt || 0] : null;
  return dots.map((p) => {
    let v = 0;
    if (state.hld && !inside(p, HLD, 4)) v++;
    if (state.tenet && p.x <= TENET_EDGE + 3) v++;
    if (state.lld && !recheck.has("lld") && !inside(p, lld, 3)) v++;
    if (state.ears) for (const [key, g] of ears) if (!recheck.has(key) && !inside(p, g, 3)) v++;
    let level = Math.min(3, v);
    if (tested && level === 0 && p !== tested) level = 1;
    return level;
  });
}

// ── Drawing ────────────────────────────────────────────────────────────────
const FADE = [0.85, 0.24, 0.13, 0.07];
const RING_KEYS = ["hld", "lld", "e1", "e2", "e3"];
const NAMES = { hld: "HLD", lld: "LLD", e3: "TRIAL-003" };

// The model is what draw() paints: ring geometry and opacities, label text, mark positions,
// and each dot's opacity. targetModel() turns a state into the model it settles on.
export function targetModel(state, dots) {
  const levels = classify(state, dots);
  const recheck = new Set(state.recheck || []);
  const checked = new Set(state.checked || []);
  const geo = { hld: HLD, lld: LLD[state.lldGeo || "L0"], e1: E1, e2: E2, e3: e3For(PROGRAMS[state.target || 0]) };
  const shown = { hld: state.hld, lld: state.lld, e1: state.ears, e2: state.ears, e3: state.ears };
  const rings = {};
  for (const key of RING_KEYS) {
    rings[key] = {
      g: { ...geo[key] },
      op: shown[key] ? 1 : 0,
      chk: checked.has(key) ? 1 : 0,
      x: key === "lld" && state.reject ? 1 : 0,
      loose: recheck.has(key),
      name: key === "lld" ? state.lldName || "LLD" : NAMES[key] || null,
    };
  }
  const codeAt = dots[state.codeAt || 0];
  const testAt = dots[state.testAt || 0];
  return {
    rings,
    tenet: { op: state.tenet ? 1 : 0, chk: checked.has("tenet") ? 1 : 0, hit: !!state.hit },
    ret: { x: testAt.x, y: testAt.y, op: state.test ? 1 : 0, aim: state.test === 1 },
    code: { x: codeAt.x, y: codeAt.y, op: state.code ? 1 : 0, hollow: state.code === 1, at: state.codeAt || 0 },
    thread: { op: state.thread ? 1 : 0, lit: state.thread === 2 },
    dots: levels.map((level, i) => (state.code && i === (state.codeAt || 0) ? 0 : FADE[level])),
  };
}

function tab(key, g, name) {
  const small = key === "e3";
  const R = radius(g);
  const w = small ? name.length * 7.4 + 12 : name.length * 9.2 + 16;
  const h = small ? 18 : 22;
  return { x: g.x + R + 2, y: g.y - h / 2, w, h, small };
}

function badge(x, y, scale, opacity, cross) {
  if (opacity < 0.01) return "";
  const mark = cross ? "M-3.4 -3.4L3.4 3.4M3.4 -3.4L-3.4 3.4" : "M-4 0.2L-1.1 3.1L4.2-2.9";
  return `<g class="${cross ? "xbadge" : "badge"}" opacity="${n(opacity)}" transform="translate(${n(x)} ${n(y)}) scale(${n(scale)})"><circle r="9"/><path d="${mark}"/></g>`;
}

// Paints a model. With labels off, it leaves out every label, badge, and the @spec link.
export function draw(model, { labels, uid }) {
  const parts = [];
  parts.push(
    `<defs><pattern id="${uid}-hatch" width="10" height="10" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line class="hatch-line" x1="2" y1="0" x2="2" y2="10"/></pattern>` +
      `<clipPath id="${uid}-clip"><path d="${roundedPath(HLD.x, HLD.y, HLD.w, HLD.h, radius(HLD))}"/></clipPath></defs>`,
  );
  parts.push(`<g class="dots">${model.dots.map((o, i) => `<circle class="dot" cx="${n(model.dotsAt[i].x)}" cy="${n(model.dotsAt[i].y)}" r="3.6" opacity="${n(o)}"/>`).join("")}</g>`);

  const t = model.tenet;
  if (t.op > 0.01) {
    let tenet = `<g class="tenet${t.hit ? " hit" : ""}" opacity="${n(t.op)}"><g clip-path="url(#${uid}-clip)"><path fill="url(#${uid}-hatch)" d="M${TENET.x} ${TENET.y}H${TENET_EDGE}V${TENET.y + TENET.h}H${TENET.x}Z"/><path class="tenet-edge" d="M${TENET_EDGE} ${TENET.y}V${TENET.y + TENET.h}"/></g>`;
    if (labels) {
      const tw = 5 * 9.2 + 16, tx = TENET.x + 30, ty = TENET.y + 46;
      tenet += `<path class="ring-tab" d="${roundedPath(tx, ty - 11, tw, 22, 6)}"/><text class="ring-label" x="${n(tx + 8)}" y="${n(ty + 5.5)}">tenet</text>`;
      tenet += badge(tx + tw + 13, ty, 1, t.chk, false);
    }
    parts.push(tenet + "</g>");
  }

  for (const key of RING_KEYS) {
    const r = model.rings[key];
    if (r.op < 0.01) continue;
    const ear = key.startsWith("e");
    const grow = (1 - r.op) * (ear ? 14 : 30);
    const g = { x: r.g.x - grow, y: r.g.y - grow, w: r.g.w + 2 * grow, h: r.g.h + 2 * grow };
    const cls = `ring ring-${key}${ear ? " ear" : ""}${r.loose ? " loose" : ""}`;
    let ring = `<g class="${cls}" opacity="${n(r.op)}"><path class="ring-line" d="${roundedPath(g.x, g.y, g.w, g.h, radius(g))}"/>`;
    if (labels) {
      const scale = ear ? 0.8 : 1;
      let bx = g.x + g.w - radius(g) - 12;
      if (r.name) {
        const b = tab(key, g, r.name);
        ring += `<path class="ring-tab" d="${roundedPath(b.x, b.y, b.w, b.h, b.small ? 5 : 6)}"/><text class="ring-label${b.small ? " small" : ""}" x="${n(b.x + (b.small ? 6 : 8))}" y="${n(g.y + (b.small ? 4.3 : 5.5))}">${r.name}</text>`;
        bx = b.x + b.w + (b.small ? 11 : 13);
        r.tabEnd = { x: b.x + b.w, y: g.y };
      }
      ring += badge(bx, g.y, scale * (0.6 + 0.4 * r.chk), r.chk * (1 - r.x), false);
      ring += badge(bx, g.y, scale * (0.6 + 0.4 * r.x), r.x, true);
    }
    parts.push(ring + "</g>");
  }

  const e3 = model.rings.e3;
  const c = model.code;
  if (labels && e3.tabEnd && model.thread.op > 0.01) {
    const op = model.thread.op * Math.min(c.op, e3.op);
    if (op > 0.01) {
      const sx = c.x + 12, sy = c.y + 4, ex = e3.tabEnd.x + 2, ey = e3.tabEnd.y + 6;
      parts.push(
        `<g class="thread${model.thread.lit ? " lit" : ""}" opacity="${n(op)}"><path d="M${n(sx)} ${n(sy)}C${n(sx + 40)} ${n(sy + 6)} ${n(ex + 34)} ${n(ey + 4)} ${n(ex)} ${n(ey)}"/><text class="spec-tag" x="${n(sx + 30)}" y="${n(sy + 20)}">@spec</text></g>`,
      );
    }
  }
  const ret = model.ret;
  if (ret.op > 0.01) {
    parts.push(
      `<g class="reticle${ret.aim ? " aim" : ""}" opacity="${n(ret.op)}" transform="translate(${n(ret.x)} ${n(ret.y)})"><circle r="10"/><path d="M0 -7V-15M0 7V15M-7 0H-15M7 0H15"/></g>`,
    );
  }
  if (c.op > 0.01) {
    parts.push(
      `<g class="code${c.hollow ? " hollow" : ""}" opacity="${n(c.op)}" transform="translate(${n(c.x)} ${n(c.y)})"><circle class="code-halo" r="11"/><circle class="code-core" r="5.5"/></g>`,
    );
  }
  return parts.join("");
}

// A finished drawing as static SVG, for the hero and for the explainers without JavaScript.
export function renderStatic(state, { labels = true, uid = "rings", title = "", desc = "" } = {}) {
  const dots = makeDots();
  const model = { ...targetModel(state, dots), dotsAt: dots };
  return (
    `<svg class="rings-svg" viewBox="-24 -22 688 464" role="img" aria-labelledby="${uid}-title ${uid}-desc" id="${uid}">` +
    `<title id="${uid}-title">${title}</title><desc id="${uid}-desc">${desc}</desc>` +
    `<g class="rings-layer">${draw(model, { labels, uid })}</g></svg>`
  );
}

// ── Pacing ─────────────────────────────────────────────────────────────────
// The active card is the last one whose top has passed the line; -1 when none has.
export function activeCard(tops, line) {
  let active = -1;
  tops.forEach((top, i) => {
    if (top < line) active = i;
  });
  return active;
}

// The steps to play for a card: all of them, or under reduced motion only the last.
export function plan(card, reduce) {
  return reduce ? [[0, finalState(card)]] : card;
}

// Plays a card's steps once; playing another card cancels whatever is left of the last one.
export function createPlayer(apply, schedule = (fn, ms) => setTimeout(fn, ms), cancel = (id) => clearTimeout(id)) {
  let timers = [];
  return {
    play(steps) {
      timers.forEach(cancel);
      timers = steps.map(([delay, state]) => schedule(() => apply(state), delay));
    },
  };
}

// ── Browser ────────────────────────────────────────────────────────────────
function ease(cur, target, k) {
  const d = target - cur;
  return Math.abs(d) < 0.004 ? target : cur + d * k;
}

class Animator {
  constructor(svg, uid, reduce) {
    this.layer = svg.querySelector(".rings-layer");
    this.uid = uid;
    this.reduce = reduce;
    this.dots = makeDots();
    this.model = null;
    this.target = null;
    this.running = false;
  }
  set(state) {
    this.target = targetModel(state, this.dots);
    if (!this.model || this.reduce) this.model = structuredClone(this.target);
    this.start();
  }
  snap(state) {
    this.target = targetModel(state, this.dots);
    this.model = structuredClone(this.target);
    this.paint();
  }
  start() {
    if (this.running) return;
    this.running = true;
    const tick = () => {
      const moving = this.step();
      this.paint();
      if (moving) requestAnimationFrame(tick);
      else this.running = false;
    };
    requestAnimationFrame(tick);
  }
  step() {
    const m = this.model, t = this.target;
    let moving = false;
    const go = (o, key, tgt, k) => {
      const v = ease(o[key], tgt, k);
      if (v !== tgt) moving = true;
      o[key] = v;
    };
    for (const key of RING_KEYS) {
      const r = m.rings[key], q = t.rings[key];
      for (const side of ["x", "y", "w", "h"]) go(r.g, side, q.g[side], 0.1);
      go(r, "op", q.op, 0.09);
      go(r, "chk", q.chk, 0.09);
      go(r, "x", q.x, 0.09);
      r.loose = q.loose;
      r.name = q.name;
    }
    go(m.tenet, "op", t.tenet.op, 0.09);
    go(m.tenet, "chk", t.tenet.chk, 0.09);
    m.tenet.hit = t.tenet.hit;
    for (const mark of ["ret", "code"]) {
      go(m[mark], "x", t[mark].x, 0.11);
      go(m[mark], "y", t[mark].y, 0.11);
      go(m[mark], "op", t[mark].op, 0.09);
    }
    m.ret.aim = t.ret.aim;
    m.code.hollow = t.code.hollow;
    go(m.thread, "op", t.thread.op, 0.09);
    m.thread.lit = t.thread.lit;
    m.dots.forEach((o, i) => go(m.dots, i, t.dots[i], 0.12));
    return moving;
  }
  paint() {
    this.layer.innerHTML = draw({ ...this.model, dotsAt: this.dots }, { labels: true, uid: this.uid });
  }
}

export function mount(doc = document, win = window) {
  const reduce = !!(win.matchMedia && win.matchMedia("(prefers-reduced-motion: reduce)").matches);
  const wide = win.matchMedia ? win.matchMedia("(min-width: 900px)") : { matches: true };
  const explainers = [];
  for (const figure of doc.querySelectorAll("[data-rings]")) {
    const kind = figure.dataset.rings;
    const cards = kind === "change" ? CHANGE : NARROWING;
    const list = doc.querySelector(`[data-scene="${kind}"]`);
    const svg = figure.querySelector("svg.rings-svg");
    if (!list || !svg) continue;
    const steps = [...list.querySelectorAll(".step")];
    const animator = new Animator(svg, svg.id, reduce);
    let current = null;
    const player = createPlayer((state) => {
      animator.set(state);
      const card = steps[current];
      if (!card) return;
      if (state.phase) card.dataset.phase = state.phase;
      else delete card.dataset.phase;
    });
    list.closest(".scrolly")?.classList.add("live");
    explainers.push(() => {
      const line = win.innerHeight * (wide.matches ? 0.58 : 0.74);
      const next = activeCard(steps.map((el) => el.getBoundingClientRect().top), line);
      if (next === current) return;
      const first = current === null;
      current = next;
      steps.forEach((el, i) => {
        el.classList.toggle("on", i === Math.max(next, 0));
        delete el.dataset.phase;
      });
      const seq = next < 0 ? [[0, BEFORE[kind]]] : plan(cards[next], reduce);
      if (first) {
        animator.snap(finalState(seq));
        const card = steps[current];
        const phase = finalState(seq).phase;
        if (card && phase) card.dataset.phase = phase;
      } else {
        player.play(seq);
      }
    });
  }
  if (!explainers.length) return;
  let ticking = false;
  const update = () => {
    ticking = false;
    explainers.forEach((fn) => fn());
  };
  win.addEventListener("scroll", () => {
    if (!ticking) {
      ticking = true;
      win.requestAnimationFrame(update);
    }
  }, { passive: true });
  win.addEventListener("resize", update);
  update();
}

if (typeof window !== "undefined" && typeof document !== "undefined") {
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", () => mount());
  else mount();
}
