#!/bin/bash
# THE UPDATE, WITH A SECOND TRY AND THE LAST GOOD CODE BEHIND IT (ops/run.sh; 22 September 2026, collection 306).
#
# Anthony, 22 September 2026: "we need the automatic updating process to always be flawless no matter what version of the
# tool is live. IT NEEDS TO ALWAYS WORK PROPERLY".
#
#   1. runs the live tool's own entry (ops/tool.json "entry"; today run_cloud.sh: update, build, site), with a time limit;
#   2. if that fails, puts the site's files back as they were published, waits half a minute and runs it once more (a
#      publisher's server error, a network blip) - but not after a time-out: a hang does not clear in thirty seconds;
#   3. if that fails too and the code has changed since the last run that published (ops/state/last_good.json), it puts
#      back that run's version - its code (*.py, *.sh, requirements.txt) and every file a person changed since (the version
#      file, the page template), never data the runs write - and runs once more, so the
#      site keeps updating with the last good version while the new one is fixed. If the last good version reaches a
#      different verdict (standing) from the one the new version published, nothing is published: a call must never flip
#      because a version broke. The next workflow step (ops/lastgood.py swap-out) puts the new code back before anything
#      is committed, so the repository keeps the new version.
# Writes ops/out/run_result.json (what happened, for the notification) and run.log. Exits 0 when an attempt succeeded.
#   OPS_SIMULATE=fail_first | fail_primary   (tests only: make the first attempt, or both primary attempts, fail)
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
mkdir -p ops/out
BASE="${OPS_BASE:-$(git rev-parse HEAD)}"
cfg () { python3 -c "import json,sys;t=json.load(open('ops/tool.json'));v=t.get(sys.argv[1],sys.argv[2]);print(' '.join(v) if isinstance(v,list) else v)" "$1" "$2" 2>/dev/null || echo "$2"; }
ENTRY="$(cfg entry run_cloud.sh)"
STATE="$(cfg state data/105_bristow_hall_system_2026-09-08/site/public/bhs_state.json)"
RESTORE="$(cfg restore_before_retry 'data/105_bristow_hall_system_2026-09-08/site data/105_bristow_hall_system_2026-09-08/bhs_state.json')"
LIMIT="${OPS_ATTEMPT_SECONDS:-900}"
: > run.log
attempt () {                    # $1 = which attempt; $2 = simulate a failure (yes/no)
  echo "=== ops: $1, $(date -u +%FT%TZ) ===" | tee -a run.log
  if [ "${2:-no}" = "yes" ]; then echo "ops: simulated failure (OPS_SIMULATE=${OPS_SIMULATE:-})" | tee -a run.log; return 97; fi
  timeout --kill-after=30 "$LIMIT" bash "$ENTRY" 2>&1 | tee -a run.log
  local rc=${PIPESTATUS[0]}
  [ "$rc" = "124" ] && echo "ops: $1 stopped after $LIMIT seconds (a hung fetch?)" | tee -a run.log
  return "$rc"
}
# the site's files as they were published, before another attempt reads them as "the state last published"
restore_site () { for p in $RESTORE; do git checkout -q "$BASE" -- "$p" 2>/dev/null; git clean -fdq -- "$p" 2>/dev/null; done; true; }
# the last three lines of the log, the last (the error itself) first
tail_err () { grep -v -e '^\s*$' -e 'DeprecationWarning' -e 'warnings.warn' -e '^=== ops:' -e '^ops: ' run.log | tail -n 3 | awk '{a[NR]=$0} END {for (i=NR; i>0; i--) print substr(a[i], 1, 200)}' | paste -sd'|' - ; }
SIM1=no; SIM2=no
case "${OPS_SIMULATE:-}" in fail_first) SIM1=yes;; fail_primary) SIM1=yes; SIM2=yes;; esac

TRIES=1
FIRST_ERR=""
attempt "attempt 1" "$SIM1"; RC=$?
if [ "$RC" -ne 0 ]; then
  FIRST_ERR="$(tail_err)"
  if [ "$RC" -ne 124 ]; then
    restore_site
    sleep "${OPS_RETRY_WAIT:-30}"
    TRIES=2
    attempt "attempt 2 (the same code)" "$SIM2"; RC=$?
  else
    echo "ops: no second try of the same code after a time-out" | tee -a run.log
  fi
fi
PRIMARY_RC=$RC
PRIMARY_ERR=""
[ "$RC" -ne 0 ] && PRIMARY_ERR="$(tail_err)"
FB_TRIED=0; FB_RC=""; FB_SHA=""; FB_FILES=0; GUARD=""
if [ "$RC" -ne 0 ]; then
  FB_SHA="$(python3 ops/lastgood.py sha 2>/dev/null || true)"
  if [ -n "$FB_SHA" ] && [ "$FB_SHA" != "$BASE" ]; then
    # the site's files first: the swap may put back files in the site folder (the last good version's page template)
    restore_site
    FB_FILES="$(OPS_BASE="$BASE" python3 ops/lastgood.py swap-in "$FB_SHA" 2>>run.log | tail -n 1)"
    if [ -n "$FB_FILES" ] && [ "$FB_FILES" -gt 0 ] 2>/dev/null; then
      FB_TRIED=1
      echo "ops: the code changed in $FB_FILES file(s) since the last good run ($FB_SHA); running that version once more" | tee -a run.log
      pip install --quiet --retries 5 -r requirements.txt >/dev/null 2>&1 || true
      TRIES=$((TRIES + 1))
      attempt "fallback: the last good code ($FB_SHA)" no; FB_RC=$?
      RC=$FB_RC
      if [ "$RC" -eq 0 ]; then
        # THE VERDICT GUARD: a different version that reaches a different standing is not published
        GUARD="$(python3 - "$BASE" "$STATE" <<'PY'
import json, subprocess, sys
base, state = sys.argv[1], sys.argv[2]
try:
    old = json.loads(subprocess.run(['git', 'show', '%s:%s' % (base, state)], capture_output=True, timeout=60).stdout or b'{}')
    new = json.load(open(state))
except Exception:
    print(''); sys.exit(0)
k = lambda s: ((s.get('standing') or {}).get('state'), (s.get('standing') or {}).get('since'))
if old.get('version') != new.get('version') and k(old) != k(new):
    print('the last good version (%s) reaches %s since %s where the published version (%s) stands %s since %s' % (
        new.get('version'), k(new)[0], k(new)[1], old.get('version'), k(old)[0], k(old)[1]))
PY
)"
        if [ -n "$GUARD" ]; then echo "ops: NOT PUBLISHED - $GUARD" | tee -a run.log; RC=11; fi
      fi
    else
      echo "ops: no code has changed since the last good run; nothing to fall back to (the failure is in a source or the data)" | tee -a run.log
    fi
  fi
fi
python3 - "$TRIES" "$RC" "$PRIMARY_RC" "$FB_TRIED" "${FB_RC:-}" "$FB_SHA" "$FB_FILES" "$PRIMARY_ERR" "$(tail_err)" "$FIRST_ERR" "$GUARD" "$BASE" <<'PY'
import json, sys, os
t, rc, prc, fbt, fbrc, sha, files, perr, err, ferr, guard, base = sys.argv[1:13]
lg = {}
try: lg = json.load(open('ops/state/last_good.json'))
except Exception: pass
res = {'attempts': int(t), 'rc': int(rc), 'primary_rc': int(prc), 'error': '' if int(rc) == 0 else (('Verdict guard: ' + guard) if guard else err),
       'first_error': ferr, 'verdict_guard': guard or None,
       'fallback': {'tried': fbt == '1', 'used': fbt == '1' and fbrc == '0' and not guard, 'rc': int(fbrc) if fbrc else None,
                    'sha': sha or None, 'version': lg.get('version') if sha else None, 'files': int(files) if str(files).isdigit() else 0,
                    'primary_error': perr, 'failed_version': base[:7] or None}}
json.dump(res, open('ops/out/run_result.json', 'w'), indent=1)
print('ops: %d attempt(s); %s%s' % (res['attempts'], 'published code ran' if res['rc'] == 0 else 'FAILED',
      (' (with the last good code %s)' % sha[:7]) if res['fallback']['used'] else ''))
PY
exit "$RC"
