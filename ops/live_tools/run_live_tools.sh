#!/bin/bash
# LIVE TOOLS ON GITHUB (collection 1052, 15 Nov 2026; Anthony 08:21 PT: "make it not on the mac but on the github and make sure ALL live tools
# are updated by the github so the mac doesnt need to be on and running"). No AI. Run by .github/workflows/live-tools.yml after state.py restore.
# The Mac job com.bristowhall.stressmap1052 (1052 code/stress_map_live_job_1052.sh), step by step, with the same scripts at the same paths
# (the mirror of the Mac's folders under /Users/anthonyhall):
#   1. inputs: State coincident indexes, State unemployment rates and payrolls (state_inputs_refresh_1052.py: FRED, else the BLS series),
#      QCEW county (qcew_county_refresh_1052.py), the BLS series kept by bls_api_1052.py, the DOL State claims files (dol_refresh_1052.py);
#   2. 1032 routine step 2 (six scripts, checks a185 and a187) + a render of all 50 States;
#   3. stress map v3.1 (stress_map_v2_1052.py --all), its gate (every State test but P1, county Q2-Q4) + a render of the built page;
#   then the shadow tool (refresh_feeds_824.py, live_union_823.py; its own git push is switched off: the workflow commits).
# MODE=parity: no input refresh (the inputs exactly as restored), for the Mac-vs-runner comparison.
# Writes $LT_OUT/status.json: {state_stress_ok, stopped_at, shadow_ok}. Exit 0 (the workflow reads status.json).
set -o pipefail
export HOME=/Users/anthonyhall
C="$HOME/Projects/Onset Detector Data/1052_stress_map_fix_parse_collect_2026-11-12"; P="$HOME/Projects/Onset Detector Data"
PY=${PY:-python3}; OPS="$GITHUB_WORKSPACE/ops/live_tools"; L="$LT_OUT/run.log"; mkdir -p "$LT_OUT" "$C/logs" "$C/out" "$C/data"
# 1167 (25 Nov 2026; Anthony: "under 3 minutes of data releases"): every Python process below loads ops/live_tools/pyboot/sitecustomize.py:
# the peak-to-trough arithmetic of damage_dimensions_live_v376 in one pass on the arrays, and pandas' date-array indexing without its runtime
# Union - bit-identical, each only when the code it replaces is the code read that day (LT_PYBOOT=0 runs without it)
[ "${LT_PYBOOT:-1}" = "1" ] && export PYTHONPATH="$OPS/pyboot${PYTHONPATH:+:$PYTHONPATH}"
say() { echo "$(date -u '+%F %T')Z $*" | tee -a "$L"; }
STOP=""
step() { local name="$1"; shift; say "-- $name"; "$@" >> "$L" 2>&1; local rc=$?; say "   $name rc=$rc"; return $rc; }
cd "$C"
if [ "${MODE:-full}" != "parity" ]; then
  step "BLS API series" $PY "$OPS/bls_api_1052.py" || say "BLS API refresh returned non-zero (held files kept)"
  # 1052 speed (16 Nov 2026): the two State refreshes run unchanged through ops/live_tools/state_fast.py (their FRED series from the BLS API
  # in one pass, FRED where the BLS lacks a series) and side by side; the other inputs need the DOL file first, as before
  export SF_BUNDLE="$LT_OUT/bls_state_bundle.json"; step "BLS State bundle" $PY "$OPS/state_fast.py" bundle || say "BLS State bundle not read (FRED serves)"
  ( step "State inputs" $PY "$OPS/state_fast.py" inputs || say "state input refresh returned non-zero (held files kept)" ) &
  SI=$!
  step "QCEW county" $PY code/qcew_county_refresh_1052.py || say "QCEW county refresh returned non-zero (held files kept)"
  step "DOL State claims" $PY code/dol_refresh_1052.py || say "DOL refresh returned non-zero (held files kept)"
  # 15 Nov 2026: the State page's other inputs (CPI, NSA State series, weekly State claims and monthly insured rate from ETA 539, permits, CPS, SQINC4) and the
  # stress map's disturbance register (from the repo copy the cloud update rebuilds); add-only, see the script's first lines
  step "State page other inputs" $PY "$OPS/state_fast.py" extra || say "other State inputs refresh returned non-zero (held files kept)"
  wait $SI
  # 1161 (21 Nov 2026): "State payrolls by industry, as first published" was never refreshed, so the day after each State release the
  # source gate held every full build; the newest month is appended from the BLS series bls_api_1052.py already keeps (add-only)
  step "State industry first prints" $PY "$OPS/state_industry_first_prints_1161.py" || say "State industry first prints returned non-zero (held file kept)"
fi
# 19 Nov 2026 (collection 1149, Anthony: "do all three"): the tool code changed that day is carried in the repo (ops/live_tools/overlay) and laid over the
# restored state before the tools run: the State page's last column is the fall against trend; the stress map starts each period where the State page does.
for d in 1032_state_recession_indicator_all_states_dc_2026-11-09:1032 1052_stress_map_fix_parse_collect_2026-11-12:1052 823_live_release_readiness_2026-10-23:823; do   # 823 since 1153: the shadow page's 2024 row is Paper 1's, not the NBER's
  ( cd "$OPS/overlay/${d##*:}" && find . -type f ! -name '*.md' | sed 's#^\./##' ) | while read -r f; do
    cmp -s "$OPS/overlay/${d##*:}/$f" "$P/${d%%:*}/$f" || { mkdir -p "$(dirname "$P/${d%%:*}/$f")" && cp "$OPS/overlay/${d##*:}/$f" "$P/${d%%:*}/$f" && say "overlay: $f"; }
  done
done
# 1167 (24 Nov 2026, limit 3 of Paper 3): the State grade's third dimension, production. The State production index is refreshed (its inputs from 2019 on,
# rebuilt by the collection's own scripts in 1032 data/spi/work, carried in the overlay) and replaced only if its checks hold; never stops the run
if [ "${MODE:-full}" != "parity" ]; then
  step "State production index (1167)" $PY "$OPS/spi_refresh_1167.py" || say "State production index refresh returned non-zero (held file kept)"
fi
# 1150 (19 Nov 2026): county jobs by industry (QCEW) for the stress map's county panel, kept to the newest quarter; never stops the run
# (in a parity run only when none is held yet: the first run reads 1990 on from the BLS files)
if [ "${MODE:-full}" != "parity" ] || ! ls "$P/1032_state_recession_indicator_all_states_dc_2026-11-09/data/qcew_industry_county/"*.csv.gz >/dev/null 2>&1; then
  step "QCEW county by industry" $PY code/qcew_county_ind_refresh_1150.py || say "QCEW county by industry refresh returned non-zero (held files kept)"
fi
# 1167b (25 Nov 2026; Anthony: "under 3 minutes of data releases"): THE SHADOW TOOL BESIDE THE REBUILD. The shadow feeds and page (824, 823)
# read neither the State page nor the stress map and write nothing either reads; they ran after both (about 9 s). They now run in the
# background from here, with their own log (appended to run.log at the end) and the same result in status.json.
( L="$LT_OUT/run_shadow.log"; : > "$L"; SH=ok; cd "$P"
  if [ "${MODE:-full}" != "parity" ]; then
    step "shadow feeds (824)" $PY -B 824_feeds_refresh_ender_plateau_2026-10-23/code/refresh_feeds_824.py || SH="824 feed refresh failed"
    # live_union_823 publishes by git push to main; here the push is switched off (the workflow commits the page after this script)
    [ "$SH" = ok ] && { BH_2024=v34 GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=remote.origin.pushurl GIT_CONFIG_VALUE_0=/dev/null/no-push-here \
        step "shadow (823)" $PY -B 823_live_release_readiness_2026-10-23/code/live_union_823.py || SH="live_union_823 failed"; }
  else
    BH_2024=v34 GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=remote.origin.pushurl GIT_CONFIG_VALUE_0=/dev/null/no-push-here \
        step "shadow (823), parity" $PY -B 823_live_release_readiness_2026-10-23/code/live_union_823.py || SH="live_union_823 failed"
  fi
  echo "$SH" > "$LT_OUT/shadow.status" ) &
SHP=$!
step "1032 routine step 2" $PY code/state_v4_rebuild_1052.py || STOP="1032 routine step 2 (six scripts or a check) failed"
# 1167 (25 Nov 2026; Anthony: "under 3 minutes of data releases"): the State page's render check (a headless Chrome over all 50 States, 33 s)
# runs beside the stress map instead of before it. It reads only the State page and writes nothing; the stress map does not read the
# check. Its result joins before the stress map's gate, and a failed check stops the run with the same message as before.
if [ -z "$STOP" ]; then
  ( L="$LT_OUT/run_state_render.log"; : > "$L"; step "State page render" $PY code/page_check_1052.py state "$P/1032_state_recession_indicator_all_states_dc_2026-11-09/web/state-onset/index.html"; echo $? > "$LT_OUT/state_render.rc" ) &
  RP=$!
  ( cd "$P/1032_state_recession_indicator_all_states_dc_2026-11-09" && step "probe (1167n, not for main): a198 as itself" $PY code/state_chronology_v4_growth_cycle_a198_1032.py ) || true
  ( cd "$P/1032_state_recession_indicator_all_states_dc_2026-11-09" && PYBOOT_STATS=1 step "probe (1167n, not for main): a198 rewritten" $PY "$OPS/pyboot/run_rewritten.py" code/state_chronology_v4_growth_cycle_a198_1032.py ) || true
  step "probe (1167n, not for main): county pool" $PY "$OPS/county_pool_probe.py" || true
  step "stress map v3.1" $PY "$OPS/stress_map_cached.py" --all --procs "$(nproc)" || STOP="stress map v3.1 build failed"
  wait $RP; cat "$LT_OUT/run_state_render.log" >> "$L"
  [ "$(cat "$LT_OUT/state_render.rc" 2>/dev/null)" = 0 ] || STOP="State page render check failed"
fi
[ -z "$STOP" ] && { step "stress map gate" $PY - "$C" <<'EOF'
import json, sys, os
C = sys.argv[1]; s = json.load(open(os.path.join(C, 'out/stress_map_v3_1_tests_state_1052.json')))['results']; c = json.load(open(os.path.join(C, 'out/stress_map_v3_1_tests_1052.json')))
bad = [k for k, v in s.items() if not v and k != 'P1'] + [k for k in ('q2', 'q3', 'q4') if not c[k]]
print('stress map gate: state', s, 'county q2-q4', [c['q2'], c['q3'], c['q4']], 'thru', c['thru'], 'FAILED' if bad else 'ok', bad); sys.exit(1 if bad else 0)
EOF
} || { [ -z "$STOP" ] && STOP="stress map tests failed (beyond the known limits P1, Q1)"; }
[ -z "$STOP" ] && { step "stress map render" $PY code/page_check_1052.py stress "$C/web/stress-map/index.html" || STOP="stress map render check failed"; }
# 1150: the factor files and county jobs by industry the page reads when a State or a county is opened
# 1167f (26 Nov 2026): through ops/live_tools/pyboot/run_rewritten.py (pyboot_detail.py: the same bytes; the county jobs by industry kept
# between runs while the QCEW files are unchanged; 25 s of the run before)
DET=code/stress_map_detail_1150.py; [ "${LT_PYBOOT:-1}" = "1" ] && DET="$OPS/pyboot/run_rewritten.py $DET"
[ -z "$STOP" ] && { step "stress map detail" $PY $DET || STOP="stress map detail files failed their checks"; }
[ -z "$STOP" ] && { step "county view check" $PY code/county_view_check_1150.py "$C" "$C/out/county_view_check_1150.json" || STOP="stress map county view check failed"; }
wait $SHP; cat "$LT_OUT/run_shadow.log" >> "$L"; SH=$(cat "$LT_OUT/shadow.status" 2>/dev/null); [ -n "$SH" ] || SH="the shadow tool did not finish"
$PY - "$LT_OUT/status.json" "$STOP" "$SH" <<'EOF'
import json, sys, time
json.dump(dict(at=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), state_stress_ok=not sys.argv[2], stopped_at=sys.argv[2] or None, shadow_ok=sys.argv[3] == 'ok', shadow_note=sys.argv[3]), open(sys.argv[1], 'w'), indent=1)
EOF
say "done: state/stress ${STOP:-ok}; shadow $SH"
exit 0
