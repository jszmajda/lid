#!/bin/sh
# Pilot stage 2, second part (2026-11-15). Cheap-discipline trajectories 1 to 3 ran with Claude Code's scheduling
# tools available; in plan mode the agent scheduled wakeups while waiting for approval, which kept turns alive
# (one timed out). Those tools are now denied in every executor session, and cheap discipline runs again as
# trajectories 4 to 6. Then probe forks for them, then grading for every valid stage 2 trajectory.
# Run from harness/ with the token set: PY=... ../plumbing/with-token.sh sh run_stage2b.sh
PY=${PY:-python3.12}
LOG=../runs/stage2
mkdir -p $LOG
CHANGES=0,1,2,3,4,5,6,7,8,9,10
run_queue() { xargs -P "$1" -I CMD sh -c CMD; }

for k in 4 5 6; do
  echo "$PY run_trajectory.py --arm cheap-discipline --id s2-cheap-discipline-$k --changes $CHANGES > $LOG/s2-cheap-discipline-$k.log 2>&1"
done | run_queue 3

while pgrep -f run_probe.py > /dev/null; do sleep 30; done
for k in 4 5 6; do
  for at in 0 3 6 9; do
    [ -f ../runs/s2-cheap-discipline-$k-probe0$at-1/trajectory.json ] && continue
    echo "$PY run_probe.py --id s2-cheap-discipline-$k --at $at --fork 1 > $LOG/probe-s2-cheap-discipline-$k-$at.log 2>&1"
  done
done | run_queue 3

{
  for t in s2-bare-1 s2-bare-2 s2-bare-3 s2-lid-full-1 s2-lid-full-2 s2-lid-full-3 s2-cheap-discipline-4 s2-cheap-discipline-5 s2-cheap-discipline-6; do
    for c in 2 6 10; do
      [ -f ../runs/$t/grading/change-$(printf %02d $c)/verdicts.json ] && continue
      echo "$PY grade_checkpoint.py --id $t --change $c --workers 2 > $LOG/grade-$t-$c.log 2>&1"
    done
  done
  for t in s2-bare-aa-1 s2-bare-aa-2 s2-bare-aa-3 s2-positive-control-1 s2-positive-control-2 s2-positive-control-3; do
    [ -f ../runs/$t/grading/change-10/verdicts.json ] && continue
    echo "$PY grade_checkpoint.py --id $t --change 10 --workers 2 > $LOG/grade-$t-10.log 2>&1"
  done
} | run_queue 2
echo "stage 2b done"
