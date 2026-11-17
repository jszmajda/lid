#!/bin/sh
# BenchTime under the rebuilt owner (design.md, "Attention and recall"): bare, cheap discipline, and LID Full on
# Sonnet 5.5, three trajectories each, the bounded policy at the central owner model. The three arms of replicate k
# share the replicate seed s3b-rk, so their draws match. Then probe forks after changes 0, 3, 6 and 9, then grading
# at checkpoints 2, 6 and 10 with the current probes.
# Resumable: each step skips work already recorded. Concurrency is kept low for a small Docker VM.
# Run from harness/ with the token set: ../plumbing/with-token.sh sh run_stage3b.sh
PY=${PY:-python3.12}
LOG=../runs/stage3b
mkdir -p $LOG
CHANGES=0,1,2,3,4,5,6,7,8,9,10
ARMS="bare cheap-discipline lid-full"

run_queue() {  # run the commands on stdin, $1 at a time (-S: macOS xargs limits a replaced line to 255 bytes otherwise)
  xargs -P "$1" -S 4096 -I CMD sh -c CMD
}

{
  for k in 1 2 3; do
    for arm in $ARMS; do
      echo "$PY run_trajectory.py --arm $arm --seed benchtime --id s3b-$arm-$k --replicate s3b-r$k --policy bounded --changes $CHANGES > $LOG/s3b-$arm-$k.log 2>&1"
    done
  done
} | run_queue 3

{
  for arm in $ARMS; do
    for k in 1 2 3; do
      for at in 0 3 6 9; do
        [ -f ../runs/s3b-$arm-$k-probe0$at-1/trajectory.json ] && continue
        echo "$PY run_probe.py --id s3b-$arm-$k --at $at --fork 1 > $LOG/probe-s3b-$arm-$k-$at.log 2>&1"
      done
    done
  done
} | run_queue 3

{
  for arm in $ARMS; do
    for k in 1 2 3; do
      for c in 2 6 10; do
        [ -f ../runs/s3b-$arm-$k/grading/change-$(printf %02d $c)/verdicts.json ] && continue
        echo "$PY grade_checkpoint.py --id s3b-$arm-$k --seed benchtime --change $c --workers 2 > $LOG/grade-s3b-$arm-$k-$c.log 2>&1"
      done
    done
  done
} | run_queue 2
echo "stage 3b done"
