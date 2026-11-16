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
say() { echo "$(date -u '+%F %T')Z $*" | tee -a "$L"; }
STOP=""
step() { local name="$1"; shift; say "-- $name"; "$@" >> "$L" 2>&1; local rc=$?; say "   $name rc=$rc"; return $rc; }
cd "$C"
if [ "${MODE:-full}" != "parity" ]; then
  step "BLS API series" $PY "$OPS/bls_api_1052.py" || say "BLS API refresh returned non-zero (held files kept)"
  step "State inputs" $PY code/state_inputs_refresh_1052.py || say "state input refresh returned non-zero (held files kept)"
  step "QCEW county" $PY code/qcew_county_refresh_1052.py || say "QCEW county refresh returned non-zero (held files kept)"
  step "DOL State claims" $PY code/dol_refresh_1052.py || say "DOL refresh returned non-zero (held files kept)"
  # 15 Nov 2026: the State page's other inputs (CPI, NSA State series, weekly State claims and monthly insured rate from ETA 539, permits, CPS, SQINC4) and the
  # stress map's disturbance register (from the repo copy the cloud update rebuilds); add-only, see the script's first lines
  step "State page other inputs" $PY code/state_extra_refresh_1052.py || say "other State inputs refresh returned non-zero (held files kept)"
fi
step "1032 routine step 2" $PY code/state_v4_rebuild_1052.py || STOP="1032 routine step 2 (six scripts or a check) failed"
[ -z "$STOP" ] && { step "State page render" $PY code/page_check_1052.py state "$P/1032_state_recession_indicator_all_states_dc_2026-11-09/web/state-onset/index.html" || STOP="State page render check failed"; }
[ -z "$STOP" ] && { step "stress map v3.1" $PY "$OPS/stress_map_cached.py" --all --procs "$(nproc)" || STOP="stress map v3.1 build failed"; }
[ -z "$STOP" ] && { step "stress map gate" $PY - "$C" <<'EOF'
import json, sys, os
C = sys.argv[1]; s = json.load(open(os.path.join(C, 'out/stress_map_v3_1_tests_state_1052.json')))['results']; c = json.load(open(os.path.join(C, 'out/stress_map_v3_1_tests_1052.json')))
bad = [k for k, v in s.items() if not v and k != 'P1'] + [k for k in ('q2', 'q3', 'q4') if not c[k]]
print('stress map gate: state', s, 'county q2-q4', [c['q2'], c['q3'], c['q4']], 'thru', c['thru'], 'FAILED' if bad else 'ok', bad); sys.exit(1 if bad else 0)
EOF
} || { [ -z "$STOP" ] && STOP="stress map tests failed (beyond the known limits P1, Q1)"; }
[ -z "$STOP" ] && { step "stress map render" $PY code/page_check_1052.py stress "$C/web/stress-map/index.html" || STOP="stress map render check failed"; }
SH=ok
if [ "${MODE:-full}" != "parity" ]; then
  cd "$P"
  step "shadow feeds (824)" $PY -B 824_feeds_refresh_ender_plateau_2026-10-23/code/refresh_feeds_824.py || SH="824 feed refresh failed"
  # live_union_823 publishes by git push to main; here the push is switched off (the workflow commits the page after this script)
  [ "$SH" = ok ] && { BH_2024=v34 GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=remote.origin.pushurl GIT_CONFIG_VALUE_0=/dev/null/no-push-here \
      step "shadow (823)" $PY -B 823_live_release_readiness_2026-10-23/code/live_union_823.py || SH="live_union_823 failed"; }
else
  cd "$P"; BH_2024=v34 GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=remote.origin.pushurl GIT_CONFIG_VALUE_0=/dev/null/no-push-here \
      step "shadow (823), parity" $PY -B 823_live_release_readiness_2026-10-23/code/live_union_823.py || SH="live_union_823 failed"
fi
$PY - "$LT_OUT/status.json" "$STOP" "$SH" <<'EOF'
import json, sys, time
json.dump(dict(at=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), state_stress_ok=not sys.argv[2], stopped_at=sys.argv[2] or None, shadow_ok=sys.argv[3] == 'ok', shadow_note=sys.argv[3]), open(sys.argv[1], 'w'), indent=1)
EOF
say "done: state/stress ${STOP:-ok}; shadow $SH"
exit 0
