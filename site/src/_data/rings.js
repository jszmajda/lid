// Static rings drawings, rendered at build time from the same module that animates them.
// The hero uses one with no labels; each explainer shows its finished state until its script runs.
// @spec MKT-SITE-111, MKT-SITE-116, MKT-SITE-117
import { CHANGE, HERO, NARROWING, finalState, renderStatic } from "../assets/js/rings.js";

export default {
  hero: renderStatic(HERO, {
    labels: false,
    uid: "rings-hero",
    title: "Narrowing to one program",
    desc: "A field of dots, each a program an agent could build from a short request. Nested rounded rings close in on them, a hatched strip rules out one region ahead of time, and one orange dot is left inside a target.",
  }),
  narrowing: renderStatic(finalState(NARROWING[NARROWING.length - 1]), {
    uid: "rings-narrowing",
    title: "Each level rules out programs",
    desc: "Dots for every program that would satisfy the free-trial request. The high-level design's ring, the tenet's hatched strip, the low-level design's ring, and three overlapping requirement rings close in until a test's target holds one orange dot, the code, linked to TRIAL-003 by an @spec link.",
  }),
  change: renderStatic(finalState(CHANGE[CHANGE.length - 1]), {
    uid: "rings-change",
    title: "One level changes",
    desc: "The same rings after the change: the low-level design's ring has moved and is checked, the rings for TRIAL-001 and TRIAL-002 have not moved, and TRIAL-003's ring, the test's target, and the code have moved to a new program. Every level is checked.",
  }),
};
