#!/bin/bash
# THE BRISTOW HALL SYSTEM — one refresh, on the Mac, with no one in the loop. Pulls the releases the rule reads,
# rebuilds the series and the page when something new arrived, deploys to Cloudflare. Run by launchd right after
# each release (bhs_schedule.py writes the job; two later attempts catch a late posting) or by hand:
#     bash bhs_run.sh manual
# Once a month it also refreshes the release calendar from FRED (bhs_calendar_fetch.py) and rewrites the job.
# Writes to live/runs.log. Needs python3 with pandas, numpy and xlrd, curl, and (for the deploy) wrangler.
set -u
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"
# Where the collection is. Resolved from this script's own location, so the system keeps working if the
# ~/mnt symlink that used to be hardcoded here is ever moved or removed. The old path is the fallback.
_SELF="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
COL="$(cd "$_SELF/.." && pwd)"
[ -d "$COL/workspace" ] || COL="$HOME/mnt/Onset Detector Data/105_bristow_hall_system_2026-09-08"
LOG="$COL/live/runs.log"
LABEL="${1:-manual}"
cd "$COL/workspace" || { echo "no workspace at $COL/workspace"; exit 1; }
mkdir -p out cache "$COL/live"
STAMP="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
# one run at a time: a scheduled firing while a run is under way (or two attempts folded together on wake) would
# rewrite the same files; the lock is a directory (atomic), stale after twenty minutes
LOCK="cache/run.lock"
if ! mkdir "$LOCK" 2>/dev/null; then
  if [ -n "$(find "$LOCK" -maxdepth 0 -mmin +20 2>/dev/null)" ]; then rmdir "$LOCK" 2>/dev/null; mkdir "$LOCK" 2>/dev/null || { echo "=== $STAMP $LABEL: lock held; skipped" >> "$LOG"; exit 0; }
  else echo "=== $STAMP $LABEL: another run under way; skipped" >> "$LOG"; exit 0; fi
fi
trap 'rmdir "$LOCK" 2>/dev/null' EXIT
# the network: a run launched the moment the Mac wakes has none for a few seconds (17 September 2026: "curl failed for ICSA"); wait up to two minutes
for _i in $(seq 1 12); do curl -sS -m 10 -o /dev/null https://api.stlouisfed.org/ && break; sleep 10; done
# the release calendar, once a month (FRED lists the year ahead as soon as the agencies publish it)
MARK="cache/calendar_fetched_$(date +%Y-%m)"
if [ ! -f "$MARK" ]; then
  if python3 bhs_calendar_fetch.py > out/calendar_fetch.out 2>&1; then touch "$MARK"; echo "=== $STAMP calendar: $(head -1 out/calendar_fetch.out)" >> "$LOG"; python3 bhs_schedule.py --install >> "$LOG" 2>&1
  else echo "=== $STAMP calendar fetch failed: $(tail -1 out/calendar_fetch.out)" >> "$LOG"; fi
fi
WHY="$(python3 bhs_schedule.py --why)"; RC=$?
# a build the gate held, or a deploy that failed, is owed: the next firing builds and publishes even when nothing new
# has arrived (17 September 2026, collection 201)
PENDING=no; if [ -f cache/deploy_pending ]; then PENDING=yes; fi
if [ "$LABEL" = "scheduled" ] && [ $RC -ne 0 ] && [ "$PENDING" = "no" ]; then echo "=== $STAMP scheduled: $WHY; nothing to do" >> "$LOG"; exit 0; fi
if [ "$PENDING" = "yes" ]; then WHY="$WHY; a held or failed publish is owed"; fi
echo "=== $STAMP run: $LABEL ($WHY)" >> "$LOG"
# THE ARITHMETIC THIS RUN WILL USE. pandas and numpy are the rule's arithmetic; if they move under us the tool
# computes something slightly different from the tool that was tested, and nothing would say so. The run stops
# here rather than publishing it. Changing versions is then a decision, taken with the walk re-run to prove the
# record is unmoved.
VCK="$(python3 s2/versions.py 2>&1)"; VRC=$?
if [ $VRC -ne 0 ]; then
  echo "$VCK" >> "$LOG"
  bash s2/alert.sh "THE ARITHMETIC MOVED" "$(printf '%s' "$VCK" | tr '\n' ' ')"
  exit 1
fi

_T0=$SECONDS   # each stage's seconds go on the run's last line (17 September 2026: "as fast as possible, as safe as possible")
python3 bhs_update.py --no-build > out/bhs_update.out 2>&1; RC=$?
_TU=$((SECONDS-_T0)); _T0=$SECONDS
cp out/bhs_update_timing.txt "out/timing_update_$LABEL.txt" 2>/dev/null   # the last run of each kind keeps its stage times (scheduled runs are not read by hand)
grep -vE " obs\)$" out/bhs_update.out >> "$LOG"
if [ $RC -ne 0 ]; then echo "update failed (exit $RC)" >> "$LOG"; bash s2/alert.sh "UPDATE FAILED" "bhs_update.py exit $RC, run $STAMP ($LABEL): $(tail -1 out/bhs_update.out | cut -c1-160)"; exit 1; fi
NEW="$(python3 - <<'EOF'
import re
new=False
for line in open('out/bhs_update.out'):
    if re.search(r'appended|extended|corrected|CHANGED',line): new=True
    m=re.search(r'^(\S+)\s+(\d{4}-\d{2}-\d{2})\s+->\s+(\d{4}-\d{2}-\d{2})',line)
    if m and m.group(2)!=m.group(3): new=True
print('yes' if new else 'no')
EOF
)"
if [ "$LABEL" = "scheduled" ] && [ "$NEW" = "no" ] && [ "$PENDING" = "no" ]; then echo "nothing new yet; no rebuild | update ${_TU}s" >> "$LOG"; python3 bhs_schedule.py --mark-done; exit 0; fi
if ! python3 bhs_build.py > out/bhs_build.out 2>&1; then echo "build failed:" >> "$LOG"; tail -5 out/bhs_build.out >> "$LOG"; bash s2/alert.sh "BUILD FAILED" "bhs_build.py, run $STAMP ($LABEL): $(tail -1 out/bhs_build.out | cut -c1-160)"; exit 1; fi
_TB=$((SECONDS-_T0)); _T0=$SECONDS
cp out/bhs_build_timing.txt "out/timing_build_$LABEL.txt" 2>/dev/null
grep -E "^standing|^daily series|^episodes|^closers memo|^opening scores|^daily readings" out/bhs_build.out | cut -c1-160 >> "$LOG"
cp out/bhs_state.json ../site/bhs_state.json && cp out/bhs_state.json ../bhs_state.json
if ! python3 bhs_site.py >> "$LOG" 2>&1; then echo "site failed" >> "$LOG"; bash s2/alert.sh "SITE BUILD FAILED" "bhs_site.py, run $STAMP ($LABEL); see live/runs.log"; exit 1; fi
# THE SHAPE OF WHAT ARRIVED, not only that it arrived. A publisher switching a series from thousands to millions,
# or weekly to monthly, or dropping twenty years in a revision, produces a file that downloads and parses
# perfectly and is wrong by a factor of a thousand. Checked against the remembered shape of all 67 feeds before
# the gate. It warns rather than halting, because a real redefinition must still be publishable once accepted.
SHP="$(python3 s2/shape_guard.py 2>&1)"; SRC=$?
if [ $SRC -ne 0 ]; then
  echo "$SHP" >> "$LOG"
  bash s2/alert.sh "A SOURCE CHANGED SHAPE" "$(printf '%s' "$SHP" | tail -n +2 | head -4 | tr '\n' ' ')"
fi

_TS=$((SECONDS-_T0)); _T0=$SECONDS
# every printed number recomputed from its own source file; a failure is logged, never hidden
rm -f out/q41_data_check.txt out/q41_data_check.json   # a check that crashes must not leave the last run's results standing
if ! PYTHONPATH=. python3 s2/q41_data_check.py > out/q41_data_check.out 2>&1; then
  if [ -f out/q41_data_check.txt ]; then
    echo "DATA CHECK FAILED: $(grep -c '^FAIL' out/q41_data_check.txt) of $(wc -l < out/q41_data_check.txt | tr -d ' ') checks" >> "$LOG"
    grep '^FAIL' out/q41_data_check.txt >> "$LOG"
  else echo "DATA CHECK DID NOT COMPLETE: $(tail -1 out/q41_data_check.out | cut -c1-200)" >> "$LOG"; fi
else echo "data check: $(tail -1 out/q41_data_check.out)" >> "$LOG"; fi
_TC=$((SECONDS-_T0)); _T0=$SECONDS
# THE DEPLOY GATE (17 September 2026, collection 201). Until today a failed check was logged and the build deployed
# anyway. s2/deploy_gate.py now decides: a garbage input or a corrupt state is never published; a page that disagrees
# with its own sources is held unless the rule's standing changed (a call is never held back by a page check);
# freshness and presentation failures are published and noted. A held build leaves the last published build live and
# is owed: the next firing builds and tries again. Every hold, every failure and every note raises an alert.
GATE="$(python3 s2/deploy_gate.py 2>&1)"; GRC=$?
echo "gate: $GATE" >> "$LOG"
if [ $GRC -ne 0 ]; then
  touch cache/deploy_pending; bash s2/alert.sh "PUBLISH HELD" "$GATE"
  echo "not deployed: the last published build stays live; the next run builds and tries again" >> "$LOG"
  python3 bhs_schedule.py --install >> "$LOG" 2>&1; python3 bhs_schedule.py --mark-done
  echo "held $(date -u +%H:%M:%SZ) | update ${_TU}s build ${_TB}s site ${_TS}s check ${_TC}s" >> "$LOG"; exit 0
fi
case "$GATE" in
  "DEPLOY all checks passed"*) ;;
  *) if [ "$GATE" != "$(cat cache/last_gate_note 2>/dev/null)" ]; then bash s2/alert.sh "PUBLISHED WITH NOTES" "$GATE"; fi;;
esac
echo "$GATE" > cache/last_gate_note
bash deploy.sh >> "$LOG" 2>&1; DRC=$?
if [ $DRC -ne 0 ]; then
  touch cache/deploy_pending; echo "DEPLOY FAILED (exit $DRC): the last published build stays live; the next run tries again" >> "$LOG"
  bash s2/alert.sh "DEPLOY FAILED" "deploy.sh exit $DRC, run $STAMP ($LABEL); the site is NOT updated; see live/runs.log"
else rm -f cache/deploy_pending; cp out/bhs_state.json cache/last_deployed_state.json; fi
_TD=$((SECONDS-_T0)); _T0=$SECONDS
# THE FORWARD LEDGER (18 September 2026, collection 202, register item 24). Every test on the past can be fitted to the
# past; the forward record cannot. Each published build appends one line - standing, reading, every through-date, every
# pending proposal, the state's sha256 - to live/FORWARD-LEDGER.jsonl, and the line is stamped through OpenTimestamps,
# which anchors its hash in the Bitcoin chain: no account, nobody's word, and the day the rule said it is provable
# afterwards to anyone. A failure here never fails the run; it is logged and alerted.
if [ $DRC -eq 0 ]; then
  LED="$(python3 s2/ledger.py 2>&1)"; LRC=$?
  echo "$LED" >> "$LOG"
  if [ $LRC -ne 0 ] || printf '%s' "$LED" | grep -q "timestamped NO"; then bash s2/alert.sh "FORWARD LEDGER" "$LED"; fi
fi
_TL=$((SECONDS-_T0)); _T0=$SECONDS

# THE PUBLISHED SITE, CHECKED AFTER EVERY PUBLISH (18 September 2026). The gate checks what is about to be
# published; nothing checked what actually arrived. Every page answers, carries no error text a reader can see,
# parses under a strict JSON parser, shows the same number the state file holds, and is current. The fast form
# skips the 57 external source links, which the watchdog checks once a day instead. A failure alerts and is
# logged; it never fails the run, because the publish has already happened and the alert is the point.
if [ $DRC -eq 0 ]; then
  sleep 8   # Cloudflare needs a moment to serve the new build
  AUD="$(python3 s2/audit_everything.py --fast --quiet 2>&1 | tail -20)"; ARC=$?
  echo "$AUD" >> "$LOG"
  [ $ARC -ne 0 ] && bash s2/alert.sh "THE PUBLISHED SITE FAILED ITS AUDIT" "$(printf '%s' "$AUD" | tail -6 | tr '\n' ' ')"
fi
_TA=$((SECONDS-_T0)); _T0=$SECONDS
python3 bhs_schedule.py --install >> "$LOG" 2>&1
# the time this run completed: the next scheduled firing runs if any slot has passed since (launchd folds the slots a
# sleeping Mac missed into one firing on wake, whatever the day or hour; bhs_schedule.py --why reads this mark)
python3 bhs_schedule.py --mark-done
echo "done $(date -u +%H:%M:%SZ) | update ${_TU}s build ${_TB}s site ${_TS}s check ${_TC}s deploy ${_TD}s ledger ${_TL}s audit ${_TA}s schedule $((SECONDS-_T0))s" >> "$LOG"
