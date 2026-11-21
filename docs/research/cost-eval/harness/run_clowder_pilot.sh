#!/bin/sh
# The Clowder pilot (design.md, "Later seeds and variants"): forks of the Clowder change script, each graded right
# after it runs. Every fork shares replicate cp-r1, so the owner's draws match across arms and windows.
#
#   phase0 <changes> [repeat]  the null-arm recheck: the stripped variant with no agent, at the changes given
#                              (comma-separated, e.g. 1,12), as fork repeat <repeat> (default 2)
#   phase1                     the ceiling check: bare on the stripped variant at the 1M window, all twelve changes
#   phase2                     bare on stripped, bare on full, and LID Full on full, at the 1m and 200k windows, all
#                              twelve changes each (phase 1's forks are among them, and skipped once done)
#   all                        phase1, then phase2
#   regrade <changes> [tag]    grade again, under the current probes.md, the changes given for all six cells and the
#                              null arm (no forking): each earlier grading moves to grading-<tag>/ (default v3); one
#                              already graded under the current probes.md's hash is skipped
#   rekeep <fork ids...>       run the held-out keeping step alone again for these forks (grade_rust --keeping-only),
#                              once each: the earlier keeping stays beside it as keeping.before-rerun
#
# Resumable: a fork whose change is recorded isn't run again, nor a grading with a summary; a fork that stopped
# partway is moved aside (<id>.stopped-<time>) and run again. Concurrency is kept low for a 2-CPU Docker VM (JOBS,
# default 2). Logs go to runs/clowder-pilot/<id>.fork.log and <id>.grade.log.
# Run from harness/ with the token set: ../plumbing/with-token.sh sh run_clowder_pilot.sh phase1
# DRY=1 prints what would run instead of running it. Before each job, pace.sh waits while the subscription's weekly
# usage is at or above USAGE_PAUSE (90%) until it falls below USAGE_RESUME (50%).
PY=${PY:-python3.12}
RUNS=${RUNS:-../runs}
VARIANTS=${VARIANTS:-$RUNS/clowder-variants/v1}
SEED=${SEED:-../seeds/clowder}
LOG=$RUNS/clowder-pilot
export PACE_LOG=${PACE_LOG:-$LOG/pacing.log} PACE_MARK=${PACE_MARK:-$LOG/.pacing-unread}
JOBS=${JOBS:-2}
REPLICATE=cp-r1
# The bounded owner, the realistic setting BenchTime's latest run used; diligent would favour arms that show the owner more.
POLICY=${POLICY:-bounded}
CHANGES="1 2 3 4 5 6 7 8 9 10 11 12"

usage() {
  echo "usage: sh run_clowder_pilot.sh phase0 <changes> [repeat] | phase1 | phase2 | all | regrade <changes> [tag] | rekeep <fork ids...>" >&2
  exit 2
}

run() {  # run a command, or print it when dry
  if [ -n "$DRY" ]; then echo "$*"; else sh -c "$*"; fi
}

pace() {  # the pacing gate before each job (pace.sh); never when dry
  [ -n "$DRY" ] || sh pace.sh
}

run_queue() {  # run the commands on stdin, $1 at a time (-S: macOS xargs limits a replaced line to 255 bytes otherwise)
  xargs -P "$1" -S 4096 -I CMD sh -c CMD
}

one() {  # one fork and its grading: <variant> <arm> <window> <change> <repeat>
  variant=$1; arm=$2; window=$3; n=$4; repeat=$5
  nn=$(printf %02d "$n")
  fid=cf-$variant-$arm-$window-c$nn-r$repeat
  rec=$RUNS/$fid/trajectory.json
  fork=yes
  if [ -f "$rec" ]; then
    if $PY -c "import json, sys; sys.exit(0 if json.load(open(sys.argv[1])).get('changes', {}).get(sys.argv[2], {}).get('commit') else 1)" "$rec" "$n"; then
      fork=no
    else  # stopped partway: keep its record aside and run it again
      run "mv $RUNS/$fid $RUNS/$fid.stopped-$(date +%Y%m%d-%H%M%S)"
    fi
  fi
  if [ $fork = yes ]; then
    if [ "$arm" = null ]; then who="--null"; else who="--arm $arm --policy $POLICY"; fi
    pace
    run "$PY run_fork.py --variants $VARIANTS --variant $variant $who --change $n --repeat $repeat --replicate $REPLICATE --window $window --runs $RUNS > $LOG/$fid.fork.log 2>&1" || return 1
  fi
  [ -f "$RUNS/$fid/grading/change-$nn/summary.json" ] && return 0
  pace
  run "$PY grade_rust.py --id $fid --runs $RUNS > $LOG/$fid.grade.log 2>&1"
}

regrade_one() {  # one fork graded again under the current probes: <fork id> <change> <tag>
  fid=$1; n=$2; tag=$3
  nn=$(printf %02d "$n")
  g=$RUNS/$fid/grading/change-$nn
  now=$($PY -c "import hashlib, sys; print(hashlib.sha256(open(sys.argv[1], 'rb').read()).hexdigest())" "$SEED/hidden/probes.md")
  if [ -f "$g/summary.json" ]; then
    was=$($PY -c "import json, sys; print((json.load(open(sys.argv[1])).get('seed_files') or {}).get('probes_sha256') or '')" "$g/summary.json")
    [ "$was" = "$now" ] && return 0
  fi
  if [ -d "$g" ] && [ ! -d "$RUNS/$fid/grading-$tag/change-$nn" ]; then
    run "mkdir -p $RUNS/$fid/grading-$tag && mv $g $RUNS/$fid/grading-$tag/change-$nn"
  elif [ -d "$g" ]; then  # a regrade that stopped partway: the earlier grading is already kept
    run "rm -rf $g"
  fi
  pace
  run "$PY grade_rust.py --id $fid --runs $RUNS > $LOG/$fid.regrade-$tag.log 2>&1"
}

regrade() {
  [ -n "$1" ] || usage
  tag=${2:-v3}
  for n in $(echo "$1" | tr ',' ' '); do
    nn=$(printf %02d "$n")
    for window in 1m 200k; do
      for pair in stripped:bare full:bare full:lid-full; do
        echo "sh $0 regrade-one cf-${pair%%:*}-${pair#*:}-$window-c$nn-r1 $n $tag"
      done
    done
    echo "sh $0 regrade-one cf-stripped-null-200k-c$nn-r1 $n $tag"
  done | run_queue "$JOBS"
}

rekeep_one() {  # <fork id>
  fid=$1
  nn=$(echo "$fid" | sed 's/.*-c\([0-9][0-9]\)-r[0-9]*$/\1/')
  [ -f "$RUNS/$fid/grading/change-$nn/keeping.before-rerun.json" ] && return 0
  pace
  run "$PY grade_rust.py --id $fid --runs $RUNS --keeping-only > $LOG/$fid.rekeep.log 2>&1"
}

rekeep() {
  [ -n "$1" ] || usage
  for fid in "$@"; do echo "sh $0 rekeep-one $fid"; done | run_queue "$JOBS"
}

phase0() {
  [ -n "$1" ] || usage
  repeat=${2:-2}
  for n in $(echo "$1" | tr ',' ' '); do
    echo "sh $0 one stripped null 200k $n $repeat"
  done | run_queue "$JOBS"
}

phase1() {
  for n in $CHANGES; do
    echo "sh $0 one stripped bare 1m $n 1"
  done | run_queue "$JOBS"
}

phase2() {
  for window in 1m 200k; do
    for pair in stripped:bare full:bare full:lid-full; do
      for n in $CHANGES; do
        echo "sh $0 one ${pair%%:*} ${pair#*:} $window $n 1"
      done
    done
  done | run_queue "$JOBS"
}

mkdir -p "$LOG"
case "$1" in *-one) ;; *) rm -f "$PACE_MARK" ;; esac  # a top-level run logs a missing usage reading afresh
case "$1" in
  one) shift; one "$@" ;;
  regrade-one) shift; regrade_one "$@" ;;
  regrade) shift; regrade "$@"; echo "regrade done" ;;
  rekeep-one) shift; rekeep_one "$@" ;;
  rekeep) shift; rekeep "$@"; echo "rekeep done" ;;
  phase0) shift; phase0 "$@"; echo "phase 0 done" ;;
  phase1) phase1; echo "phase 1 done" ;;
  phase2) phase2; echo "phase 2 done" ;;
  all) phase1; phase2; echo "pilot done" ;;
  *) usage ;;
esac
