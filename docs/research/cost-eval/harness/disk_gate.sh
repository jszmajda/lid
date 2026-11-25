#!/bin/sh
# The disk gate before each fork (plan.md, M2h): wait while Docker's free disk is under MIN_FREE_GB (default 20), or
# the Mac's own free space (/System/Volumes/Data, where Colima's disk image lives) is under HOST_MIN_FREE_GB (default
# 25), trimming the VM's disk (trim.sh) before each wait, until neither is, checking every DISK_SLEEP seconds (default 300). Each fork copies about 910 MB, and a fork with a miss to
# repair keeps its volumes until the repair is recorded, so a full queue could fill the VM's disk. Free space is read
# inside a container (its overlay root reports the Docker disk's free space); DISK_CMD, a script printing whole GB,
# stands in for it in tests, as HOST_DF_CMD does for the Mac's and TRIM_CMD for the trim. With no reading, log it and
# carry on. Waits go to DISK_LOG.
MIN_FREE_GB=${MIN_FREE_GB:-20}
HOST_MIN_FREE_GB=${HOST_MIN_FREE_GB:-25}
DISK_SLEEP=${DISK_SLEEP:-300}
DISK_LOG=${DISK_LOG:-/dev/null}
DISK_IMAGE=${DISK_IMAGE:-lid-cost-eval-executor-node:2.1.323}

free_gb() {
  if [ -n "$DISK_CMD" ]; then
    sh "$DISK_CMD"
  else
    docker run --rm --entrypoint df "$DISK_IMAGE" -Pk / | awk 'NR == 2 { printf "%d\n", $4 / 1048576 }'
  fi
}

host_gb() {  # the Mac's own free space, where Colima's disk image lives
  if [ -n "$HOST_DF_CMD" ]; then
    sh "$HOST_DF_CMD"
  else
    df -Pk /System/Volumes/Data 2>/dev/null | awk 'NR == 2 { printf "%d\n", $4 / 1048576 }'
  fi
}

while :; do
  low=""
  g=$(free_gb 2>/dev/null)
  case "$g" in
    '' | *[!0-9]*) echo "$(date '+%F %T') no Docker disk reading; going on" >> "$DISK_LOG"; g="" ;;
  esac
  [ -n "$g" ] && [ "$g" -lt "$MIN_FREE_GB" ] && low="Docker has $g GB free, under $MIN_FREE_GB"
  h=$(host_gb 2>/dev/null)
  case "$h" in
    '' | *[!0-9]*) h="" ;;
  esac
  [ -n "$h" ] && [ "$h" -lt "$HOST_MIN_FREE_GB" ] && low="${low:+$low; }the Mac has $h GB free, under $HOST_MIN_FREE_GB"
  [ -z "$low" ] && exit 0
  sh "$(dirname "$0")/trim.sh"  # released volumes give their space back to the Mac only once trimmed
  echo "$(date '+%F %T') $low; trimmed, waiting ${DISK_SLEEP}s" >> "$DISK_LOG"
  sleep "$DISK_SLEEP"
done
