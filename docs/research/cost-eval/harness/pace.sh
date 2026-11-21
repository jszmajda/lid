#!/bin/sh
# Pacing gate, run before each job a runner starts (a batch of a trajectory's changes, a fork, a grading): while the
# subscription's weekly usage is at or above USAGE_PAUSE (default 90), wait in PACE_SLEEP steps (default 900 s, 15
# minutes) until it falls below USAGE_RESUME (default 50, after the weekly reset), then go on. A job already running is
# never interrupted. Usage comes from USAGE_CMD (default ../plumbing/local/usage.sh), which prints an integer percentage,
# or nothing if it can't read it; with no reading, the gate logs that once (PACE_MARK, which each runner clears when it
# starts) and lets every job through.
USAGE_CMD=${USAGE_CMD:-$(dirname "$0")/../plumbing/local/usage.sh}
USAGE_PAUSE=${USAGE_PAUSE:-90}
USAGE_RESUME=${USAGE_RESUME:-50}
PACE_SLEEP=${PACE_SLEEP:-900}
PACE_LOG=${PACE_LOG:-/dev/stderr}
PACE_MARK=${PACE_MARK:-${TMPDIR:-/tmp}/lid-cost-eval-pacing-unread}

reading() {
  [ -f "$USAGE_CMD" ] || return 0
  sh "$USAGE_CMD" 2>/dev/null | head -1 | tr -dc '0-9'
}

u=$(reading)
if [ -z "$u" ]; then
  if [ ! -f "$PACE_MARK" ]; then
    echo "$(date '+%Y-%m-%d %H:%M') pacing: no usage reading from $USAGE_CMD; running without the gate" >> "$PACE_LOG"
    : > "$PACE_MARK"
  fi
  exit 0
fi
[ "$u" -lt "$USAGE_PAUSE" ] && exit 0
echo "$(date '+%Y-%m-%d %H:%M') pacing: weekly usage ${u}% is at or above ${USAGE_PAUSE}%; waiting until it is below ${USAGE_RESUME}%" >> "$PACE_LOG"
while :; do
  sleep "$PACE_SLEEP"
  u=$(reading)
  if [ -z "$u" ]; then
    echo "$(date '+%Y-%m-%d %H:%M') pacing: the usage reading stopped; going on" >> "$PACE_LOG"
    exit 0
  fi
  if [ "$u" -lt "$USAGE_RESUME" ]; then
    echo "$(date '+%Y-%m-%d %H:%M') pacing: resuming at ${u}%" >> "$PACE_LOG"
    exit 0
  fi
done
