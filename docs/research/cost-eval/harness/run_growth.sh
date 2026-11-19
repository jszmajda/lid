#!/bin/sh
# The growth test on ReleaseDesk (design.md, "The growth test"; plan.md, M2d): each arm grows the project from its brief
# through the change script, under the bounded owner at its central constants, one fresh session per change.
#
#   trial   bare-1 and lid-full-1 through change 20, their course-change forks, and checkpoints at 10 and 20
#   full    bare-1..5, the drift floor (g-bare-drift, on bare-1's replicate seed), lid-full-1..5 and
#           bare-one-line-1..3 through change 40, the course-change forks, and checkpoints at 10, 20, 30 and 40
#
# Replicate k's trajectories share the replicate seed g-rk. Forks run from the first replicate of each arm
# (FORK_REPLICATES, default 1), three of each kind (FORKS), each one change long: course forks of each course change
# from the snapshot before it, and reliance forks of each reliance change from the trajectory's own snapshot before it.
# The checkpoint that follows grades them (flips and the stale-intent audit, or regression) and discards them. Resumable: run_trajectory skips recorded changes (a trial trajectory carries on to
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

reliance_changes() {  # the reliance changes at or before $1
  $PY -c "
import sys; sys.path.insert(0, '.')
from costeval import growth, simulator
s = simulator.parse_change_script(open('$SEED_DIR/hidden/change-script.md').read())
print(' '.join(str(r) for r in growth.reliance_changes(s, upto=$1)))"
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
  trajectories "$phase" | while read -r id arm rep; do
    echo "$PY run_trajectory.py --arm $arm --seed $SEED --id $id --replicate $rep --policy bounded --owner-model-config central --changes $(changes_to "$upto") > $LOG/$id.log 2>&1"
  done | run_queue "$JOBS"
  courses=$(course_changes "$upto")
  reliances=$(reliance_changes "$upto")
  trajectories "$phase" | while read -r id arm rep; do
    k=${id##*-}
    case " $FORK_REPLICATES " in *" $k "*) ;; *) continue ;; esac
    for c in $courses; do  # course forks: the course change, from the snapshot just before it
      f=1
      while [ $f -le "$FORKS" ]; do
        echo "$PY run_course_forks.py --id $id --kind course --course $c --fork $f > $LOG/$id-course$c-$f.log 2>&1"
        f=$((f + 1))
      done
    done
    for r in $reliances; do  # reliance forks: the reliance change, from the trajectory's own snapshot just before it
      f=1
      while [ $f -le "$FORKS" ]; do
        echo "$PY run_course_forks.py --id $id --kind reliance --reliance $r --fork $f > $LOG/$id-reliance$r-$f.log 2>&1"
        f=$((f + 1))
      done
    done
  done | run_queue "$JOBS"
  trajectories "$phase" | while read -r id arm rep; do
    for c in $checkpoints; do
      echo "$PY growth_checkpoint.py --id $id --change $c > $LOG/$id-checkpoint-$c.log 2>&1"
    done
  done | run_queue "$JOBS"
}

case "$1" in
  trial) grow trial 20 "10 20"; echo "trial done" ;;
  full) grow full 40 "10 20 30 40"; echo "full run done" ;;
  *) usage ;;
esac
