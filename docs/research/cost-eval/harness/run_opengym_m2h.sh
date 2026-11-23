#!/bin/sh
# The openGym brownfield test (plan.md, M2h; seeds/opengym/hidden/m2h-plan.md and m2h-harness-needs.md): changes 1-12,
# each forked from a pristine start (copied, never run in) and graded right after it runs.
#
#   null       the untouched starts (NULL_STARTS: the bare start and each replicate's map) graded at every change, as
#              null forks, then m2h_check.py --mode null: every dependency probe not exercised, every non-guard new row
#              not met or not exercised
#   right      the instrument's positive control: each change's right build (m2h-validation/builds.mjs, written as a
#              patch by m2h_right_builds.py) committed after the bare start as a null fork's result and graded exactly
#              as a fork is, then m2h_check.py --mode right: every row met, every dependency probe kept
#   main       bare from the shared start against LID Full from each replicate's map (r1 ogmap-2, r2 ogmap-3, r3
#              ogmap-4; runs/opengym-m2h/starts.json), three forks a change at the 1M window; fork k of every change
#              and both arms shares the owner's replicate m2h-rk
#   repairs    a repair fork for every miss of every graded fork (run_clowder_repairs.py): run, graded, recorded, then
#              each fork's volumes released once all its misses are repaired
#   report     the joint-outcome report (m2h_report.py): implemented against the dependency, per fork, change and tier
#   all        main, repairs, then report
#
# Every fork is isolated (GitHub's hosts blocked, web tools denied) with the bounded owner, in the Node executor image
# the starts file names; npm stays reachable (NPM_NETWORK, recorded). Disk: each fork copies about 910 MB, so before
# each one disk_gate.sh waits while Docker's free disk is under MIN_FREE_GB (20), and a graded fork's volumes go at once
# unless it has a miss to repair (null and right forks never do); those go once their repairs are recorded. Resumable: a fork whose change is recorded isn't
# run again, nor a grading with a summary, nor a recorded repair; a fork that stopped partway is moved aside
# (<id>.stopped-<time>) and run again. JOBS (default 2) at a time; logs go to runs/opengym-m2h/.
# Run from harness/ with the token set: ../plumbing/with-token.sh sh run_opengym_m2h.sh main
# DRY=1 prints what would run instead of running it. Before each job, pace.sh waits while the subscription's weekly
# usage is at or above USAGE_PAUSE (90%) until it falls below USAGE_RESUME (50%).
PY=${PY:-python3.12}
RUNS=${RUNS:-../runs}
MAIN=${MAIN:-/Users/jess/src/lid-cost-eval/docs/research/cost-eval}  # git-ignored seed material lives here
SEED=${SEED:-$MAIN/seeds/opengym}
HIDDEN=$SEED/hidden
FILES=${FILES:-$HIDDEN/m2h}
LOG=$RUNS/opengym-m2h
STARTS=${STARTS:-$LOG/starts.json}
export PACE_LOG=${PACE_LOG:-$LOG/pacing.log} PACE_MARK=${PACE_MARK:-$LOG/.pacing-unread} DISK_LOG=${DISK_LOG:-$LOG/disk.log}
JOBS=${JOBS:-2}
POLICY=${POLICY:-bounded}
NPM_NETWORK=${NPM_NETWORK:-on}
WINDOW=1m
CHANGES="1 2 3 4 5 6 7 8 9 10 11 12"
REPEATS="1 2 3"
NULL_STARTS=${NULL_STARTS:-"bare lid-r1"}  # the maps change no code: one map is enough to catch docs misleading graders
RIGHT=$LOG/right
SEED_FLAGS="--seed-dir $SEED --oracle $FILES/oracle.md --change-script $FILES/change-script.md --owner-items $FILES/owner-items.json --brief $SEED/brief.md"
GRADE_FLAGS="--seed-dir $SEED --probes $HIDDEN/m2h-probes.md --guard-rows $HIDDEN/m2h-guard-rows.json"

usage() {
  echo "usage: sh run_opengym_m2h.sh null | right | main | repairs | report | all" >&2
  exit 2
}

run() {  # run a command, or print it when dry
  if [ -n "$DRY" ]; then echo "$*"; else sh -c "$*"; fi
}

pace() {  # the pacing gate before each job (pace.sh); never when dry
  [ -n "$DRY" ] || sh pace.sh
}

disk() {  # the disk gate before each fork (disk_gate.sh: Docker's free disk under MIN_FREE_GB, default 20); never when dry
  [ -n "$DRY" ] || sh disk_gate.sh
}

release() {  # a graded fork's volumes go now unless it has a miss to repair (run_clowder_repairs.py release): <fork id>
  run "$PY run_clowder_repairs.py release --forks '$1' --runs $RUNS --seed-files $FILES >> $LOG/$1.grade.log 2>&1"
}

run_queue() {  # run the commands on stdin, $1 at a time (-S: macOS xargs limits a replaced line to 255 bytes otherwise)
  xargs -P "$1" -S 4096 -I CMD sh -c CMD
}

recorded() {  # a fork's trajectory.json records a commit for some change: <fork id>
  [ -f "$RUNS/$1/trajectory.json" ] && $PY -c "import json, sys; sys.exit(0 if any(c.get('commit') for c in json.load(open(sys.argv[1])).get('changes', {}).values()) else 1)" "$RUNS/$1/trajectory.json"
}

fork_and_grade() {  # <fork id> <change> <run_fork arguments...>: the fork unless recorded, then its grading unless done
  fid=$1; n=$2; shift 2
  nn=$(printf %02d "$n")
  if ! recorded "$fid"; then
    [ -d "$RUNS/$fid" ] && run "mv $RUNS/$fid $RUNS/$fid.stopped-$(date +%Y%m%d-%H%M%S)"
    disk && pace
    run "$PY run_fork.py --starts $STARTS $* --change $n --window $WINDOW --npm-network $NPM_NETWORK $SEED_FLAGS --id $fid --runs $RUNS > $LOG/$fid.fork.log 2>&1" || return 1
  fi
  if [ ! -f "$RUNS/$fid/grading/change-$nn/summary.json" ]; then
    pace
    run "$PY grade_node.py --id $fid --runs $RUNS $GRADE_FLAGS > $LOG/$fid.grade.log 2>&1" || return 1
  fi
  release "$fid"
}

one() {  # one fork of main: <arm: bare|lid> <change> <repeat>
  arm=$1; n=$2; k=$3; nn=$(printf %02d "$n")
  if [ "$arm" = bare ]; then who="--start bare --arm bare"; else who="--start lid-r$k --arm lid-full-arrows"; fi
  fork_and_grade "m2h-$arm-c$nn-r$k" "$n" "$who --policy $POLICY --repeat $k --replicate m2h-r$k"
}

null_one() {  # one untouched start graded at one change: <start> <change>
  s=$1; n=$2; nn=$(printf %02d "$n")
  fork_and_grade "m2h-null-$s-c$nn" "$n" "--start $s --null --repeat 1 --replicate m2h-r1"
}

right_one() {  # one right build, committed after the bare start as a null fork's result: <change>
  n=$1; nn=$(printf %02d "$n")
  fork_and_grade "m2h-right-c$nn" "$n" "--start bare --null --result-patch $RIGHT/change-$nn.diff --repeat 1 --replicate m2h-r1"
}

repair_one() {  # one repair fork, its grading and its record: <fork id> <item>
  fid=$1; item=$2; rid=$fid-fix-$item
  [ -f "$RUNS/$rid/repair.json" ] && return 0
  nn=$(echo "$fid" | sed 's/.*-c\([0-9][0-9]\)-r[0-9]*$/\1/')
  if ! recorded "$rid"; then
    disk && pace
    run "$PY run_clowder_repairs.py run --of $fid --item $item --runs $RUNS --seed-files $FILES --isolate > $LOG/$rid.fork.log 2>&1" || return 1
  fi
  if [ ! -f "$RUNS/$rid/grading/change-$nn/summary.json" ]; then
    pace
    run "$PY grade_node.py --id $rid --runs $RUNS $GRADE_FLAGS > $LOG/$rid.grade.log 2>&1" || return 1
  fi
  run "$PY run_clowder_repairs.py record --of $fid --item $item --runs $RUNS --seed-files $FILES >> $LOG/$rid.grade.log 2>&1"
}

null_phase() {
  for s in $NULL_STARTS; do for n in $CHANGES; do echo "sh $0 null-one $s $n"; done; done | run_queue "$JOBS"
  run "$PY m2h_check.py --mode null --runs $RUNS --forks 'm2h-null-*' --seed-files $FILES"
}

right_phase() {
  run "$PY m2h_right_builds.py --builds $HIDDEN/m2h-validation/builds.mjs --out $RIGHT > $LOG/right-builds.log 2>&1" || return 1
  for n in $($PY m2h_right_builds.py --builds "$HIDDEN/m2h-validation/builds.mjs" --list); do echo "sh $0 right-one $n"; done | run_queue "$JOBS"
  run "$PY m2h_check.py --mode right --runs $RUNS --forks 'm2h-right-c*' --seed-files $FILES"
}

main_phase() {
  for n in $CHANGES; do for k in $REPEATS; do for arm in bare lid; do
    echo "sh $0 one $arm $n $k"
  done; done; done | run_queue "$JOBS"
}

repairs() {
  $PY run_clowder_repairs.py plan --forks 'm2h-*' --runs "$RUNS" --seed-files "$FILES" | while read -r fid item; do
    echo "sh $0 repair-one $fid $item"
  done | run_queue "$JOBS"
  run "$PY run_clowder_repairs.py release --forks 'm2h-*' --runs $RUNS --seed-files $FILES"
}

report() {
  run "$PY m2h_report.py --runs $RUNS --forks 'm2h-*-r[0-9]' --seed-files $FILES --out $LOG/m2h.md"
}

mkdir -p "$LOG"
case "$1" in *-one|one) ;; *) rm -f "$PACE_MARK" ;; esac  # a top-level run logs a missing usage reading afresh
case "$1" in
  one) shift; one "$@" ;;
  null-one) shift; null_one "$@" ;;
  right-one) shift; right_one "$@" ;;
  repair-one) shift; repair_one "$@" ;;
  null) null_phase; echo "null check done" ;;
  right) right_phase; echo "right builds done" ;;
  main) main_phase; echo "main done" ;;
  repairs) repairs; echo "repairs done" ;;
  report) report; echo "report done" ;;
  all) main_phase; repairs; report; echo "M2h done" ;;
  *) usage ;;
esac
