#!/bin/bash
# The update, the build and the site, run anywhere.
#
# The rule's chain has the collection's path written into it in many places, as ~/Projects/Onset Detector Data or
# ~/mnt/Onset Detector Data. Rather than edit dozens of files and risk changing what the rule reads, the runner
# puts the bundle where the chain already looks: one symlink, and every hardcoded path resolves.
#
# The Mac's bhs_run.sh also deploys with wrangler and writes the forward ledger; this does neither. Publishing here
# is committing the built site, which Cloudflare Pages picks up, so no Cloudflare credential lives in a runner.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$HOME/Projects" "$HOME/mnt"
ln -sfn "$HERE/data" "$HOME/Projects/Onset Detector Data"
ln -sfn "$HERE/data" "$HOME/mnt/Onset Detector Data"
# Directories the update WRITES to. They are not in the freeze, which lists what the rule READS, so the bundle
# does not carry them and the first cloud run died on a missing one. Created here rather than committed, because
# an empty directory is not something git can carry anyway.
for d in 25_fred_daily_weekly/fred_weekly 25_fred_daily_weekly/fred_daily \
         24_bristow_rule_lab/workspace/lab/data/fred_weekly 24_bristow_rule_lab/workspace/lab/rt/vint \
         186_realtime_channels_2026-09-15/data 186_realtime_channels_2026-09-15/data_highfreq \
         186_realtime_channels_2026-09-15/vintages 45_dol_first_prints_2026-09 \
         109_home_tiles_2026-09-11 191_standing_collector_2026-09-16/warehouse; do
  mkdir -p "$HERE/data/$d"
done

cd "$HERE/data/105_bristow_hall_system_2026-09-08/workspace"
mkdir -p out cache cache/surveys cache/closers ../live ../site/public
# THE GATE'S REFERENCE (20 September 2026, site-UI chat; collection 274). s2/deploy_gate.py decides by comparing this
# build with the state LAST PUBLISHED, which it reads from cache/last_deployed_state.json - a file only the Mac's
# bhs_run.sh ever wrote. On this runner it was whatever copy the bundle carried (v3.56, built 18 September), so from
# v3.57 every run read "standing changed" and a failed page check could never hold a build: the gate was off without
# saying so. The state this runner last published is the one the previous run committed, ../site/public/bhs_state.json,
# read here before this run's build replaces it - the same file, for the same reason, as the call alert below.
[ -f ../site/public/bhs_state.json ] && cp ../site/public/bhs_state.json cache/last_deployed_state.json || true
MODE="${BHS_MODE:-full}"    # full | build | site (20 September 2026; Anthony: "make these processes as fast as possible")
# THE RELEASE CALENDAR, ONCE A MONTH (21 September 2026, collection 278). bhs_calendar_fetch.py reads FRED's calendars for
# the jobs report, JOLTS, housing starts and the weekly claims. The Mac ran it at the first run of each month and this
# runner never did, so the cloud went by the calendar the bundle carried (fetched 14 September) and the usual-timing
# guesses beyond it. The mark is committed with the data, so this runs once a month; a failure leaves the calendar in hand.
# EVERY DAY, NOT EVERY MONTH (22 September 2026, collection 306; Anthony: "always know when the next data is available/
# coming so it automatically updates the schedule"). An agency that moves a release (the autumn 2025 shutdown moved a
# season of them) is on FRED's calendar within a day, and a month was too long to find out. Four calls to FRED, once a day.
MARK="cache/calendar_fetched_on"
# v3.73 (23 September 2026, collection 333): the grade reads GDP and GDPNow; a schedule without their rows is re-fetched today whatever the mark says
grep -q "^GDPC1," cache/release_schedule.csv 2>/dev/null || rm -f "$MARK"
if [ "$MODE" != "site" ] && [ "$(cat "$MARK" 2>/dev/null)" != "$(date +%F)" ]; then
  if python3 bhs_calendar_fetch.py > out/calendar_fetch.out 2>&1; then date +%F > "$MARK"; echo "calendar: $(head -1 out/calendar_fetch.out)"
  else echo "calendar fetch failed; the calendar in hand stands: $(tail -1 out/calendar_fetch.out)"; fi
fi
if [ "$MODE" = "site" ]; then
  # re-render the pages from the state the previous run committed; nothing is fetched or built
  cp ../site/public/bhs_state.json out/bhs_state.json
  echo "site mode: pages re-rendered from the committed state built $(python3 -c "import json;print(json.load(open('out/bhs_state.json'))['built_at'])")"
else
  if [ "$MODE" = "full" ]; then python3 bhs_update.py --no-build; else echo "build mode: no update; the data as committed"; fi
  # THE BACKSTOP OPENER'S CALLS (20 September 2026, collection 256): before the build, so bhs_build.py can read them; never fails the run
  python3 s2/backstop.py || true
  # THE ACTIVITY OPENER (v3.60, Core v6, 21 September 2026, collection 278): its calls and reading, before the build; never fails the run
  python3 s2/activity_opener.py || true
  # v3.72 (22 September 2026, collection 311; E31): THE SECOND OPENER's states - the 51 first prints and the breadth - before the build; never fails the run
  python3 s2/state_breadth.py || true
  # v3.73 (23 September 2026, collection 333; collection 331): the committee watch, once a day; a dating the chronology file lacks raises a flag, moves nothing; never fails the run
  if [ "$(cat cache/chronology_watch_on 2>/dev/null)" != "$(date +%F)" ]; then python3 s2/chronology_watch.py && date +%F > cache/chronology_watch_on || true; fi
  python3 bhs_build.py
fi
# THE CALL ALERT (20 September 2026, collection 257; ask 42): a build whose standing differs from the LAST PUBLISHED state
# (../site/public/bhs_state.json, committed by the previous run) is the event the system exists for; alerted here, on every
# channel, before the gate or the deploy can hold it. BHS_DRILL=yes sends a fire-drill alert through the same path.
[ "$MODE" = "site" ] || python3 - <<'STANDING' || true
import json, os, subprocess
new = json.load(open('out/bhs_state.json')).get('standing') or {}
old = {}
for cand in ('../site/public/bhs_state.json', '../bhs_state.json'):
    try: old = json.load(open(cand)).get('standing') or {}; break
    except Exception: continue
if old and (new.get('state'), new.get('since')) != (old.get('state'), old.get('since')):   # v3.64: the state and its day, not the dict (the branch names changed its keys)
    msg = "THE RULE'S STANDING CHANGED: %s since %s (%s) -> %s since %s (%s), dated %s. Built %s." % (old.get('state'), old.get('since'), old.get('branch') or old.get('leg'), new.get('state'), new.get('since'), new.get('branch') or new.get('leg'), new.get('dated'), json.load(open('out/bhs_state.json')).get('built_at'))
    print(msg); subprocess.run(['bash', 's2/alert.sh', 'THE RULE CALLED' if new.get('state') == 'open' else 'THE RULE CLOSED', msg], timeout=90)
else: print('standing unchanged:', new)
STANDING
# v3.59 (20 September 2026): the leg-proposal alert (257 part 2) is gone with the leg tier; the call alert above stands.
if [ "${BHS_DRILL:-no}" = "yes" ]; then bash s2/alert.sh "FIRE DRILL" "A drill from the cloud runner (run ${GITHUB_RUN_ID:-local}, $(date -u +%FT%TZ)): the call-alert path works if this reached the phone and a GitHub issue."; fi
# The build writes the state to out/. The site reads it from ../site/. On the Mac, bhs_run.sh copies between the
# two, and this runner did not: the first green cloud run rebuilt everything and then published the stale copy
# the bundle happened to carry. A run that succeeds while publishing yesterday is worse than one that fails.
cp out/bhs_state.json ../site/bhs_state.json
cp out/bhs_state.json ../bhs_state.json
python3 bhs_site.py
# THE RUN SLOTS (21 September 2026, collection 278): the release times at which the Cloudflare Worker and the Mac start the
# next runs, published with the site (site/public/run_slots.json); never fails the run
python3 s2/run_slots.py || true
# THE WATCHDOG (v3.67, 22 September 2026, collection 295): a stale channel, an opener that did not run, a late breadth month or
# an FOMC calendar about to end is alerted (s2/alert.sh), once in three days while it lasts; never fails the run
[ "$MODE" = "site" ] || python3 s2/watchdog.py || true
# THE BACKSTOP TIER (20 September 2026, collection 249): three outside zero-false-alarm rules run as a SHADOW tier beside
# the rule - they never open, move or close an episode. Writes out/backstop_state.json and site/public/backstop/. A
# failure here never fails the run.
[ "$MODE" = "site" ] || python3 s2/backstop.py || true
# collection 335 (23 September 2026; plan L5, L7, item 18): the shadow scoreboard after the tier; on the first run of a new year the expansion ledger; never fail the run
[ "$MODE" = "site" ] || python3 s2/scoreboard.py || true
[ "$MODE" = "site" ] || python3 s2/data_census.py || true   # collection 337: the data census
if [ "$MODE" != "site" ] && [ "$(cat cache/expansion_ledger_year 2>/dev/null)" != "$(date +%Y)" ]; then python3 s2/expansion_ledger.py && date +%Y > cache/expansion_ledger_year || true; fi

# and prove it: the published state must be the one this run built, not the one the bundle carried
python3 - <<'CHECK'
import json, sys
a = json.load(open('out/bhs_state.json'))['built_at']
b = json.load(open('../site/public/bhs_state.json'))['built_at']
print('built_at: built %s, published %s' % (a, b))
if a != b:
    sys.exit('the site published a state this run did not build')
CHECK
