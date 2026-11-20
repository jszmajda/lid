#!/bin/sh
# The growth test on ReleaseDesk (design.md, "The growth test"; plan.md, M2d): each arm grows the project from its brief
# through the change script, under the bounded owner at its central constants, one fresh session per change.
#
#   trial   bare-1 and lid-full-1 through change 20, their course-change forks, and checkpoints at 10 and 20
#   full    bare-1..5, the drift floor (g-bare-drift, on bare-1's replicate seed), lid-full-1..5 and
#           bare-one-line-1..3 through change 40, the course-change forks, and checkpoints at 10, 20, 30 and 40
#
# Replicate k's trajectories share the replicate seed g-rk; a trajectory runs in batches ending at each checkpoint. Each
# course change's reliance request runs only as a fork, from the trajectory's snapshot after its lag: one from every
# trajectory, and three (FORKS) from the first replicate of each arm (FORK_REPLICATES). That first replicate also forks
# every course change three times from the snapshot before it. The checkpoint that follows grades each fork (the
# reliance outcome, or flips and the stale-intent audit) and discards it.
# Pacing (pace.sh): before each batch, fork, and grading with work left (pending.py), the job waits while the
# subscription's weekly usage is at or above USAGE_PAUSE (90%) until it falls below USAGE_RESUME (50%); a job with
# nothing left is skipped without waiting, and a running job is never interrupted. Resumable: run_trajectory skips recorded changes (a trial trajectory carries on to
# change 40 in the full run), a recorded fork is left alone, and a checkpoint skips the steps it has recorded.
# Concurrency is kept low for a 2-CPU Docker VM (JOBS, default 2). Logs go under runs/growth/.
# Run from harness/ with the token set: ../plumbing/with-token.sh sh run_growth.sh trial
# DRY=1 prints what would run instead of running it.
PY=${PY:-python3.12}
RUNS=${RUNS:-../runs}
SEED=${SEED:-releasedesk}
SEED_DIR=${SEED_DIR:-../seeds/$SEED}
JOBS=${JOBS:-2}
FORKS=${FORKS:-3}
FORK_REPLICATES=${FORK_REPLICATES:-1}
LOG=$RUNS/growth
export PACE_LOG=${PACE_LOG:-$LOG/pacing.log} PACE_MARK=${PACE_MARK:-$LOG/.pacing-unread}
PACE="sh pace.sh"

usage() {
  echo "usage: sh run_growth.sh trial | full" >&2
  exit 2
}

run_queue() {  # run the commands on stdin, $1 at a time (-S: macOS xargs limits a replaced line to 255 bytes otherwise)
  if [ -n "$DRY" ]; then cat; else xargs -P "$1" -S 4096 -I CMD sh -c CMD; fi
}

changes_to() {  # 0,1,...,N
  i=0; out=0
  while [ $i -lt "$1" ]; do i=$((i + 1)); out="$out,$i"; done
  echo "$out"
}

course_changes() {  # the course changes at or before $1
  $PY -c "
import sys; sys.path.insert(0, '.')
from costeval import simulator
s = simulator.parse_change_script(open('$SEED_DIR/hidden/change-script.md').read())
print(' '.join(str(n) for n, c in sorted(s.items()) if c.course_change and n <= $1))"
}

reliance_courses() {  # the course changes whose reliance request (at course + lag) is at or before $1
  $PY -c "
import sys; sys.path.insert(0, '.')
from costeval import growth, simulator
s = simulator.parse_change_script(open('$SEED_DIR/hidden/change-script.md').read())
print(' '.join(str(c) for c, lag in growth.reliance_requests(s, upto=$1)))"
}

batches() {  # a trajectory's changes in batches ending at each checkpoint, with the pacing gate before each
  id=$1; arm=$2; rep=$3; upto=$4
  from=0; out=""
  for end in 10 20 30 40; do
    [ "$end" -gt "$upto" ] && break
    list=$from; i=$from
    while [ $i -lt $end ]; do i=$((i + 1)); list="$list,$i"; done
    cmd="if $PY pending.py batch --id $id --changes $list; then $PACE && $PY run_trajectory.py --arm $arm --seed $SEED --id $id --replicate $rep --policy bounded --owner-model-config central --changes $list >> $LOG/$id.log 2>&1; fi"
    out="${out:+$out && }$cmd"
    from=$((end + 1))
  done
  echo "$out"
}

trajectories() {  # id arm replicate, one per line, for a phase
  case "$1" in
    trial) printf '%s\n' "g-bare-1 bare g-r1" "g-lid-full-1 lid-full g-r1" ;;
    full)
      for k in 1 2 3 4 5; do echo "g-bare-$k bare g-r$k"; done
      echo "g-bare-drift bare g-r1"
      for k in 1 2 3 4 5; do echo "g-lid-full-$k lid-full g-r$k"; done
      for k in 1 2 3; do echo "g-bare-one-line-$k bare-one-line g-r$k"; done ;;
  esac
}

grow() {  # phase, last change, checkpoints
  phase=$1; upto=$2; checkpoints=$3
  mkdir -p "$LOG"
  rm -f "$PACE_MARK"  # this run logs a missing usage reading afresh
  trajectories "$phase" | while read -r id arm rep; do
    batches "$id" "$arm" "$rep" "$upto"
  done | run_queue "$JOBS"
  courses=$(course_changes "$upto")
  reliances=$(reliance_courses "$upto")
  trajectories "$phase" | while read -r id arm rep; do
    k=${id##*-}
    case " $FORK_REPLICATES " in *" $k "*) first=yes ;; *) first=no ;; esac
    if [ $first = yes ]; then
      for c in $courses; do  # course forks: the course change, from the snapshot just before it
        f=1
        while [ $f -le "$FORKS" ]; do
          echo "if $PY pending.py fork --id $id --kind course --course $c --fork $f; then $PACE && $PY run_course_forks.py --id $id --kind course --course $c --fork $f > $LOG/$id-course$c-$f.log 2>&1; fi"
          f=$((f + 1))
        done
      done
    fi
    for c in $reliances; do  # reliance forks: one per course change from every trajectory, more from a first replicate
      n=1; [ $first = yes ] && n=$FORKS
      f=1
      while [ $f -le "$n" ]; do
        echo "if $PY pending.py fork --id $id --kind reliance --course $c --fork $f; then $PACE && $PY run_course_forks.py --id $id --kind reliance --course $c --fork $f > $LOG/$id-reliance$c-$f.log 2>&1; fi"
        f=$((f + 1))
      done
    done
  done | run_queue "$JOBS"
  trajectories "$phase" | while read -r id arm rep; do
    for c in $checkpoints; do
      echo "if $PY pending.py checkpoint --id $id --change $c; then $PACE && $PY growth_checkpoint.py --id $id --change $c > $LOG/$id-checkpoint-$c.log 2>&1; fi"
    done
  done | run_queue "$JOBS"
}

case "$1" in
  trial) grow trial 20 "10 20"; echo "trial done" ;;
  full) grow full 40 "10 20 30 40"; echo "full run done" ;;
  *) usage ;;
esac
