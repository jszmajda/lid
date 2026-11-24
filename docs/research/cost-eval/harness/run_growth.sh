#!/bin/sh
# The growth test on ReleaseDesk (design.md, "The growth test"; plan.md, M2d): each arm grows the project from its brief
# through the change script, under the bounded owner at its central constants, one fresh session per change.
#
#   trial   bare-1 and lid-full-1 through change 20, their course-change forks, and checkpoints at 10 and 20
#   full    bare-1..5, the drift floor (g-bare-drift, on bare-1's replicate seed), lid-full-1..5 and
#           bare-one-line-1..3 through change 40, the course-change forks, and checkpoints at 10, 20, 30 and 40
#   m2e     the checklist arm (plan.md, M2e; landscape.md, "The checklist arm"): checklist-1 on replicate g-r1
#           through change 20, with the trial's replicate-1 forks and its checkpoints at 10 and 20
#   repairs repair forks (plan.md, M2e; run_repair_forks.py): for each latent item a checkpoint's grading of
#           REPAIR_IDS (bare-1, lid-full-1, checklist-1) has as not met, at REPAIR_CHECKPOINTS (10 and 20), one fork
#           from that checkpoint's snapshot opened by the owner's repair report, then regraded in full
#   instrument  the instrument gate (design.md, "The trial, and its gate"), as the seed's reference-builds.md says
#           it (costeval/reference.py; arms ref-correct and ref-stale, never study arms): R+ (g-ref-correct) through
#           change 40; a stale fork S_C (g-ref-stale-cNN) per course change, from R+ after C-1 through C+lag; each
#           one's reliance fork; the spec's gradings (instrument.py); the positive control planted in R+'s tests at 20
#           and 40 and read by the intent readers; then the gate report (report.py --instrument, runs/growth/instrument.md)
#
# Replicate k's trajectories share the replicate seed g-rk; a trajectory runs in batches ending at each checkpoint. Each
# course change's reliance request runs only as a fork, from the trajectory's snapshot after its lag: one from every
# trajectory, and three (FORKS) from the first replicate of each arm (FORK_REPLICATES). That first replicate also forks
# every course change three times from the snapshot before it. The checkpoint that follows grades each fork (the
# reliance outcome, or flips and the stale-intent audit) and discards it.
# Isolation: every session (trajectories, R+ and its stale forks, course and reliance forks) runs with GitHub's hosts
# blocked and web search and fetch denied (--isolate), and so do the graders that have tools.
# Pacing (pace.sh): before each batch, fork, and grading with work left (pending.py), the job waits while the
# subscription's weekly usage is at or above USAGE_PAUSE (90%) until it falls below USAGE_RESUME (50%); a job with
# nothing left is skipped without waiting, and a running job is never interrupted. Resumable: run_trajectory skips recorded changes (a trial trajectory carries on to
# change 40 in the full run), a recorded fork is left alone, and a checkpoint skips the steps it has recorded.
# Concurrency is kept low for a 2-CPU Docker VM (JOBS, default 2). Logs go under runs/growth/.
# Run from harness/ with the token set: ../plumbing/with-token.sh sh run_growth.sh trial
# DRY=1 prints what would run instead of running it.
PY=${PY:-$(command -v python3.12 || echo /Users/jess/.local/share/uv/python/cpython-3.12-macos-aarch64-none/bin/python3.12)}  # a fresh shell may lack python3.12 on PATH
RUNS=${RUNS:-../runs}
SEED=${SEED:-releasedesk-growth}  # assembled by assemble_growth_seed.py
SEED_DIR=${SEED_DIR:-../seeds/$SEED}
JOBS=${JOBS:-2}
FORKS=${FORKS:-3}
FORK_REPLICATES=${FORK_REPLICATES:-1}
LOG=$RUNS/growth
REPAIR_IDS=${REPAIR_IDS:-"g-bare-1 g-lid-full-1 g-checklist-1"}
REPAIR_CHECKPOINTS=${REPAIR_CHECKPOINTS:-"10 20"}
export PACE_LOG=${PACE_LOG:-$LOG/pacing.log} PACE_MARK=${PACE_MARK:-$LOG/.pacing-unread}
PACE="sh pace.sh"

usage() {
  echo "usage: sh run_growth.sh trial | m2e | repairs | full | instrument" >&2
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
  id=$1; arm=$2; rep=$3; upto=$4; policy=${5:-bounded}
  from=0; out=""
  for end in 10 20 30 40; do
    [ "$end" -gt "$upto" ] && break
    list=$from; i=$from
    while [ $i -lt $end ]; do i=$((i + 1)); list="$list,$i"; done
    cmd="if $PY pending.py batch --id $id --changes $list; then $PACE && $PY run_trajectory.py --arm $arm --seed $SEED --id $id --replicate $rep --policy $policy --owner-model-config central --isolate --changes $list >> $LOG/$id.log 2>&1; fi"
    out="${out:+$out && }$cmd"
    from=$((end + 1))
  done
  echo "$out"
}

trajectories() {  # id arm replicate, one per line, for a phase
  case "$1" in
    trial) printf '%s\n' "g-bare-1 bare g-r1" "g-lid-full-1 lid-full g-r1" ;;
    m2e) echo "g-checklist-1 checklist g-r1" ;;
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
          echo "if $PY pending.py fork --id $id --kind course --course $c --fork $f; then $PACE && $PY run_course_forks.py --id $id --kind course --course $c --fork $f --isolate > $LOG/$id-course$c-$f.log 2>&1; fi"
          f=$((f + 1))
        done
      done
    fi
    for c in $reliances; do  # reliance forks: one per course change from every trajectory, more from a first replicate
      n=1; [ $first = yes ] && n=$FORKS
      f=1
      while [ $f -le "$n" ]; do
        echo "if $PY pending.py fork --id $id --kind reliance --course $c --fork $f; then $PACE && $PY run_course_forks.py --id $id --kind reliance --course $c --fork $f --isolate > $LOG/$id-reliance$c-$f.log 2>&1; fi"
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

repairs() {  # one repair fork per latent miss of each run at each checkpoint, run then regraded in the same job
  mkdir -p "$LOG"
  rm -f "$PACE_MARK"
  # shellcheck disable=SC2086
  $PY run_repair_forks.py plan --ids $REPAIR_IDS --checkpoints $REPAIR_CHECKPOINTS --runs "$RUNS" --seed-dir "$SEED_DIR" |
  while read -r id at item; do
    echo "if $PY pending.py repair --id $id --at $at --item $item; then $PACE && $PY run_repair_forks.py run --id $id --at $at --item $item --isolate > $LOG/$id-repair$at-$item.log 2>&1 && $PY run_repair_forks.py grade --id $id --at $at --item $item >> $LOG/$id-repair$at-$item.log 2>&1; fi"
  done | run_queue "$JOBS"
}

stale_forks() {  # "C lag" for each stale fork in the seed's reference spec
  $PY -c "
import json
for c, e in sorted(json.load(open('$SEED_DIR/hidden/reference-builds.json'))['stale'].items(), key=lambda kv: int(kv[0])):
    print(c, e['lag'])"
}

instrument() {  # R+, the stale forks, their reliance forks, the spec's gradings, the positive control, the report
  mkdir -p "$LOG"
  rm -f "$PACE_MARK"
  batches g-ref-correct ref-correct g-ref 40 diligent | run_queue 1
  forks=$(stale_forks | tr ' ' ':')
  for f in $forks; do  # S_C: from R+ after C-1, C (declined) through C+lag
    c=${f%%:*}; lag=${f##*:}
    id=g-ref-stale-c$(printf %02d "$c")
    list=$c; i=$c
    while [ $i -lt $((c + lag)) ]; do i=$((i + 1)); list="$list,$i"; done
    echo "if $PY pending.py batch --id $id --changes $list; then $PACE && $PY run_trajectory.py --arm ref-stale --seed $SEED --id $id --replicate g-ref --policy diligent --owner-model-config central --stale-of $c --fork-of g-ref-correct --isolate --changes $list >> $LOG/$id.log 2>&1; fi"
  done | run_queue "$JOBS"
  for f in $forks; do  # each reference's reliance fork after C+lag
    c=${f%%:*}
    for id in g-ref-correct g-ref-stale-c$(printf %02d "$c"); do
      echo "if $PY pending.py fork --id $id --kind reliance --course $c --fork 1; then $PACE && $PY run_course_forks.py --id $id --kind reliance --course $c --fork 1 --isolate > $LOG/$id-reliance$c-1.log 2>&1; fi"
    done
  done | run_queue "$JOBS"
  {
    for c in 10 20 30 40; do
      echo "if $PY pending.py gate --change $c; then $PACE && $PY instrument.py checkpoint --change $c > $LOG/gate-checkpoint-$c.log 2>&1; fi"
    done
    for f in $forks; do
      c=${f%%:*}
      echo "if $PY pending.py gate --course $c; then $PACE && $PY instrument.py course --course $c > $LOG/gate-course-$c.log 2>&1; fi"
    done
  } | run_queue "$JOBS"
  for c in 20 40; do  # the positive control: stale tests planted in ref-correct's own, read by the intent readers
    name=pc-g-ref-correct-c$c
    echo "if $PY pending.py control --id g-ref-correct --change $c; then $PACE && { { [ -f $RUNS/g-ref-correct/growth/positive-control-c$c/assertions/index.json ] || $PY plant_stale_tests.py --id g-ref-correct --change $c --items retired; } && $PY intent_from_tests.py batch --plan runs/intent-from-tests/$name/plan.json && $PY intent_from_tests.py summarize --name $name; } > $LOG/$name.log 2>&1; fi"
  done | run_queue 1
  if [ -n "$DRY" ]; then echo "$PY report.py --instrument --seed $SEED --out $LOG/instrument.md"
  else $PY report.py --instrument --seed "$SEED" --out "$LOG/instrument.md"; fi
}

case "$1" in
  trial) grow trial 20 "10 20"; echo "trial done" ;;
  m2e) grow m2e 20 "10 20"; echo "m2e done" ;;
  repairs) repairs; echo "repairs done" ;;
  instrument) instrument; echo "instrument done" ;;
  full) grow full 40 "10 20 30 40"; echo "full run done" ;;
  *) usage ;;
esac
