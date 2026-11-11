import { expect, it } from "vitest";
import { hasFullAccess, hoursAfter, startTrial, trialEnded } from "../src/trial";

// @spec TRIAL-001
it("starts a trial when a new user signs up", () => {
  const signedUpAt = new Date("2026-03-01T14:00:00Z");
  const trial = startTrial({ signedUpAt, timeZone: "Asia/Tokyo" });
  expect(trial.startedAt).toEqual(signedUpAt);
});

// @spec TRIAL-002
it("gives full access while the trial is active", () => {
  const signup = new Date("2026-03-01T14:00:00Z");
  expect(hasFullAccess(signup, hoursAfter(signup, 719))).toBe(true);
});

// @spec TRIAL-003
it("ends the trial 720 hours after signup", () => {
  // 11 p.m. on March 1st, in Tokyo
  const signup = new Date("2026-03-01T14:00:00Z");
  const end = hoursAfter(signup, 720);
  expect(trialEnded(signup, end)).toBe(true);
});
