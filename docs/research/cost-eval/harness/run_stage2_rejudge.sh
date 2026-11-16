#!/bin/sh
# Judge every stage 2 checkpoint's logs again under probes version 4 and the rule on inspections a build doesn't
# offer, then grade the two checkpoints whose app didn't start. Run from harness/ with the token set.
PY=${PY:-python3.12}
for d in ../runs/s2-*/grading/change-*; do
  t=$(echo $d | cut -d/ -f3); c=$(echo $d | sed 's/.*change-0*//'); [ -z "$c" ] && c=0
  [ -f $d/verdicts.json ] || continue
  [ -f $d/rejudge-v4.json ] && continue
  echo "$PY rejudge.py --id $t --change $c --model claude-sonnet-5-5 --name v4 > ../runs/stage2/rejudge-$t-$c.log 2>&1"
done | xargs -P 2 -I CMD sh -c CMD


echo "rejudge done"
