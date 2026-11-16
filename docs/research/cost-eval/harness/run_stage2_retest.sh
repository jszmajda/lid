#!/bin/sh
# Judge three stage 2 change-10 checkpoints twice more under the current judge rules and the probe text their logs
# were executed under (version 4), to measure test-retest flips. Run from harness/ with the token set.
PY=${PY:-python3.12}
for id in s2-bare-1 s2-cheap-discipline-4 s2-lid-full-1; do
  for name in retest-a retest-b; do
    echo "$PY rejudge.py --id $id --change 10 --model claude-sonnet-5-5 --name $name --probes archive/probes-v4.md > ../runs/stage2/$name-$id.log 2>&1"
  done
done | xargs -P 2 -I CMD sh -c CMD
echo "retest done"
