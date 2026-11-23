#!/bin/sh
# The disk gate before each fork (plan.md, M2h): wait while Docker's free disk is under MIN_FREE_GB (default 20) until
# it isn't, checking every DISK_SLEEP seconds (default 300). Each fork copies about 910 MB, and a fork with a miss to
# repair keeps its volumes until the repair is recorded, so a full queue could fill the VM's disk. Free space is read
# inside a container (its overlay root reports the Docker disk's free space); DISK_CMD, a script printing whole GB,
# stands in for it in tests. With no reading, log it and carry on. Waits go to DISK_LOG.
MIN_FREE_GB=${MIN_FREE_GB:-20}
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

while :; do
  g=$(free_gb 2>/dev/null)
  case "$g" in
    '' | *[!0-9]*) echo "$(date '+%F %T') no disk reading; going on" >> "$DISK_LOG"; exit 0 ;;
  esac
  [ "$g" -ge "$MIN_FREE_GB" ] && exit 0
  echo "$(date '+%F %T') Docker has $g GB free, under $MIN_FREE_GB; waiting ${DISK_SLEEP}s" >> "$DISK_LOG"
  sleep "$DISK_SLEEP"
done
