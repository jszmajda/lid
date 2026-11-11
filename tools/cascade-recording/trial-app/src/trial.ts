export const TRIAL_HOURS = 720;

export interface User {
  signedUpAt: Date;
  // An IANA time zone name, such as "Asia/Tokyo"
  timeZone: string;
}

export interface Trial {
  startedAt: Date;
}

export function hoursAfter(start: Date, hours: number): Date {
  return new Date(start.getTime() + hours * 60 * 60 * 1000);
}

// @spec TRIAL-001
export function startTrial(user: User): Trial {
  return { startedAt: user.signedUpAt };
}

// @spec TRIAL-002
export function hasFullAccess(signup: Date, now: Date): boolean {
  return !trialEnded(signup, now);
}

// @spec TRIAL-003
export function trialEnded(signup: Date, now: Date): boolean {
  return now.getTime() >= hoursAfter(signup, TRIAL_HOURS).getTime();
}
