#!/bin/sh
# Classify the owner touchpoints and audit the owner replies of every stage 2 trajectory counted in the results
# (not the probe forks, and not cheap-discipline 1 to 3). Run from harness/ with the token set.
PY=${PY:-python3.12}
for t in bare-1 bare-2 bare-3 bare-aa-1 bare-aa-2 bare-aa-3 cheap-discipline-4 cheap-discipline-5 cheap-discipline-6 \
         lid-full-1 lid-full-2 lid-full-3 positive-control-1 positive-control-2 positive-control-3; do
  id=s2-$t
  [ -f ../runs/$id/touchpoints.json ] || $PY classify_touchpoints.py --id $id > ../runs/stage2/touchpoints-$id.log 2>&1
  [ -f ../runs/$id/owner-audit.json ] || $PY audit_owner.py --id $id > ../runs/stage2/audit-$id.log 2>&1
  echo "$id done"
done
echo "touchpoints and audits done"
