#!/bin/sh
# Clowder with cross-crate changes (plan.md, M2f; decisions.md, 2026-11-21/22): changes 13-24 of the M2f change set,
# each forked from snapshot 86db995 and graded right after it runs.
#
#   variants   the variant sets: v2 (full, lid, stripped) and v2-dose (the same with the renaming dose for changes
#              14, 15 and 19), both drawn and thinned with the pilot's seed (v1), with M2f's held-out test functions
#              taken out of every variant (clowder_variants.py); then each set's graded targets, the dependency probes
#              and held-out test copies built from the snapshot outside the arms' view (m2f_graded_targets.py)
#   null       the null-arm check: the untouched v2 snapshot (the full variant, no agent) graded at every change, then
#              m2f_null_check.py: every new row not met, every dependency probe and held-out test passing
#   main       bare on the stripped variant against LID Full on the full variant, three forks a change at the 1M
#              window; fork k of every change and both arms shares the owner's replicate m2f-rk
#   dose       the same pairs on v2-dose, for changes 14, 15 and 19 only
#   repairs    a repair fork for every miss of every graded fork (run_clowder_repairs.py): run, graded, recorded,
#              then each fork's volumes released once all its misses are repaired
#   all        main, dose, then repairs
#
# Every fork is isolated (GitHub's hosts blocked, web tools denied) with the bounded owner. Resumable: a fork whose
# change is recorded isn't run again, nor a grading with a summary, nor a recorded repair; a fork that stopped partway
# is moved aside (<id>.stopped-<time>) and run again. JOBS (default 2) at a time; logs go to runs/clowder-m2f/.
# Run from harness/ with the token set: ../plumbing/with-token.sh sh run_clowder_m2f.sh main
# DRY=1 prints what would run instead of running it. Before each job, pace.sh waits while the subscription's weekly
# usage is at or above USAGE_PAUSE (90%) until it falls below USAGE_RESUME (50%).
PY=${PY:-python3.12}
RUNS=${RUNS:-../runs}
HIDDEN=${HIDDEN:-../seeds/clowder/hidden}
FILES=${FILES:-$HIDDEN/m2f}
REPO=${REPO:-/Users/jess/src/clowder}
LOG=$RUNS/clowder-m2f
export PACE_LOG=${PACE_LOG:-$LOG/pacing.log} PACE_MARK=${PACE_MARK:-$LOG/.pacing-unread}
JOBS=${JOBS:-2}
POLICY=${POLICY:-bounded}
WINDOW=1m
CHANGES="13 14 15 16 17 18 19 20 21 22 23 24"
DOSE_CHANGES="14 15 19"
REPEATS="1 2 3"
PAIRS="stripped:bare full:lid-full"
SEED_FLAGS="--oracle $FILES/oracle.md --change-script $FILES/change-script.md --owner-items $FILES/owner-items.json"
GRADE_FLAGS="--oracle $FILES/oracle.md --change-script $FILES/change-script.md --probes $HIDDEN/m2f-probes.md"

usage() {
  echo "usage: sh run_clowder_m2f.sh variants | null | main | dose | repairs | all" >&2
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

recorded() {  # a fork's trajectory.json records a commit for some change: <fork id>
  [ -f "$RUNS/$1/trajectory.json" ] && $PY -c "import json, sys; sys.exit(0 if any(c.get('commit') for c in json.load(open(sys.argv[1])).get('changes', {}).values()) else 1)" "$RUNS/$1/trajectory.json"
}

one() {  # one fork and its grading: <variant set> <variant> <arm> <change> <repeat>
  set=$1; variant=$2; arm=$3; n=$4; k=$5
  nn=$(printf %02d "$n")
  case "$set" in v2) pre=m2f ;; v2-dose) pre=m2f-dose ;; *) echo "unknown set $set" >&2; return 2 ;; esac
  if [ "$arm" = null ]; then fid=$pre-null-c$nn; else fid=$pre-$variant-$arm-c$nn-r$k; fi
  if ! recorded "$fid"; then
    [ -d "$RUNS/$fid" ] && run "mv $RUNS/$fid $RUNS/$fid.stopped-$(date +%Y%m%d-%H%M%S)"
    if [ "$arm" = null ]; then who="--null"; else who="--arm $arm --policy $POLICY"; fi
    pace
    run "$PY run_fork.py --variants $RUNS/clowder-variants/$set --variant $variant $who --change $n --repeat $k --replicate m2f-r$k --window $WINDOW $SEED_FLAGS --id $fid --runs $RUNS > $LOG/$fid.fork.log 2>&1" || return 1
  fi
  [ -f "$RUNS/$fid/grading/change-$nn/summary.json" ] && return 0
  pace
  run "$PY grade_rust.py --id $fid --runs $RUNS $GRADE_FLAGS > $LOG/$fid.grade.log 2>&1"
}

repair_one() {  # one repair fork, its grading and its record: <fork id> <item>
  fid=$1; item=$2; rid=$fid-fix-$item
  [ -f "$RUNS/$rid/repair.json" ] && return 0
  nn=$(echo "$fid" | sed 's/.*-c\([0-9][0-9]\)-r[0-9]*$/\1/')
  if ! recorded "$rid"; then
    pace
    run "$PY run_clowder_repairs.py run --of $fid --item $item --runs $RUNS --seed-files $FILES --isolate > $LOG/$rid.fork.log 2>&1" || return 1
  fi
  if [ ! -f "$RUNS/$rid/grading/change-$nn/summary.json" ]; then
    pace
    run "$PY grade_rust.py --id $rid --runs $RUNS $GRADE_FLAGS > $LOG/$rid.grade.log 2>&1" || return 1
  fi
  run "$PY run_clowder_repairs.py record --of $fid --item $item --runs $RUNS --seed-files $FILES >> $LOG/$rid.grade.log 2>&1"
}

variants() {  # the two variant sets and their graded targets (no model calls)
  for set in v2 v2-dose; do
    extra=""; [ "$set" = v2-dose ] && extra="--renames $HIDDEN/m2f-renaming/renames.json"
    run "$PY clowder_variants.py --repo $REPO --commit 86db995 --seed $set --draw-seed v1 --holdouts $HIDDEN/m2f-holdouts.json $extra --out $RUNS/clowder-variants/$set --volumes --cargo-test > $LOG/variants-$set.log 2>&1" || return 1
    run "$PY m2f_graded_targets.py --repo $REPO --commit 86db995 --probes $HIDDEN/m2f-dependency-probes --holdouts $HIDDEN/m2f-holdouts.json --out $RUNS/clowder-variants/$set/graded >> $LOG/variants-$set.log 2>&1" || return 1
  done
}

null() {
  for n in $CHANGES; do echo "sh $0 one v2 full null $n 1"; done | run_queue "$JOBS"
  run "$PY m2f_null_check.py --runs $RUNS --forks 'm2f-null-c*' --seed-files $FILES"
}

main_phase() {
  for n in $CHANGES; do for k in $REPEATS; do for pair in $PAIRS; do
    echo "sh $0 one v2 ${pair%%:*} ${pair#*:} $n $k"
  done; done; done | run_queue "$JOBS"
}

dose() {
  for n in $DOSE_CHANGES; do for k in $REPEATS; do for pair in $PAIRS; do
    echo "sh $0 one v2-dose ${pair%%:*} ${pair#*:} $n $k"
  done; done; done | run_queue "$JOBS"
}

repairs() {
  $PY run_clowder_repairs.py plan --forks 'm2f-*' --runs "$RUNS" --seed-files "$FILES" | while read -r fid item; do
    echo "sh $0 repair-one $fid $item"
  done | run_queue "$JOBS"
  run "$PY run_clowder_repairs.py release --forks 'm2f-*' --runs $RUNS --seed-files $FILES"
}

mkdir -p "$LOG"
case "$1" in *-one|one) ;; *) rm -f "$PACE_MARK" ;; esac  # a top-level run logs a missing usage reading afresh
case "$1" in
  one) shift; one "$@" ;;
  repair-one) shift; repair_one "$@" ;;
  variants) variants; echo "variants done" ;;
  null) null; echo "null check done" ;;
  main) main_phase; echo "main done" ;;
  dose) dose; echo "dose done" ;;
  repairs) repairs; echo "repairs done" ;;
  all) main_phase; dose; repairs; echo "M2f done" ;;
  *) usage ;;
esac
