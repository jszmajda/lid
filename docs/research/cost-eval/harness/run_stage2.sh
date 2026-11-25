#!/bin/sh
# Pilot stage 2 on BenchTime (see plan.md): three arms on Sonnet 5.5, three trajectories each, diligent owner,
# plus the A/A check (bare-aa) and the positive control, then probe forks after changes 0, 3, 6 and 9 for the nine
# main trajectories, then grading (checkpoints 2, 6 and 10 for the main trajectories; 10 for the others).
# Resumable: each step skips work already recorded. Concurrency is kept low for a small Docker VM.
# Run from harness/ with the token set: ../plumbing/with-token.sh sh run_stage2.sh
PY=${PY:-python3.12}
LOG=../runs/stage2
mkdir -p $LOG
CHANGES=0,1,2,3,4,5,6,7,8,9,10

run_queue() {  # run the commands on stdin, $1 at a time
  xargs -P "$1" -I CMD sh -c CMD
}

{
  for arm in bare cheap-discipline lid-full bare-aa positive-control; do
    for k in 1 2 3; do
      echo "$PY run_trajectory.py --arm $arm --id s2-$arm-$k --changes $CHANGES > $LOG/s2-$arm-$k.log 2>&1"
    done
  done
} | run_queue 3

{
  for arm in bare cheap-discipline lid-full; do
    for k in 1 2 3; do
      for at in 0 3 6 9; do
        [ -f ../runs/s2-$arm-$k-probe0$at-1/trajectory.json ] && continue
        echo "$PY run_probe.py --id s2-$arm-$k --at $at --fork 1 > $LOG/probe-s2-$arm-$k-$at.log 2>&1"
      done
    done
  done
} | run_queue 3

{
  for arm in bare cheap-discipline lid-full; do
    for k in 1 2 3; do
      for c in 2 6 10; do
        [ -f ../runs/s2-$arm-$k/grading/change-$(printf %02d $c)/verdicts.json ] && continue
        echo "$PY grade_checkpoint.py --id s2-$arm-$k --change $c --workers 2 > $LOG/grade-s2-$arm-$k-$c.log 2>&1"
      done
    done
  done
  for arm in bare-aa positive-control; do
    for k in 1 2 3; do
      [ -f ../runs/s2-$arm-$k/grading/change-10/verdicts.json ] && continue
      echo "$PY grade_checkpoint.py --id s2-$arm-$k --change 10 --workers 2 > $LOG/grade-s2-$arm-$k-10.log 2>&1"
    done
  done
} | run_queue 2
echo "stage 2 done"
