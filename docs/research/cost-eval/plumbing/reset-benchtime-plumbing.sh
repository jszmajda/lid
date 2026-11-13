#!/bin/bash
# Plumbing example for the bare build of BenchTime: its start command and data location are hard-coded from its interface reference.
# Start (or restart) the service on empty data, with the clock at the last value gt set (default 2026-01-05 08:00:00 UTC).
CLOCK=$(cat "$GT_STATE/clock" 2>/dev/null || echo "2026-01-05 08:00:00")
docker rm -f $GT_CONTAINER >/dev/null 2>&1
docker run -d --name $GT_CONTAINER --tmpfs /clock:mode=1777 -e TZ=UTC ${GT_IMAGE:-bt-plumb-app:ckpt0} sh -c "echo '$CLOCK' > /clock/faketime; cd /home/agent/app && exec env LD_PRELOAD=/usr/lib/aarch64-linux-gnu/faketime/libfaketime.so.1 FAKETIME_DONT_FAKE_MONOTONIC=1 FAKETIME_NO_CACHE=1 FAKETIME_TIMESTAMP_FILE=/clock/faketime BENCHTIME_DATA_DIR=/home/agent/data .venv/bin/python -m benchtime" >/dev/null
for i in $(seq 1 50); do docker exec $GT_CONTAINER curl -s -o /dev/null http://localhost:$GT_PORT/docs && exit 0; sleep 0.2; done; exit 1
