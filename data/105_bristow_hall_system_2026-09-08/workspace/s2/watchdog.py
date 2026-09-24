"""s2/watchdog.py - THE WATCHDOG (v3.67, 22 September 2026, collection 295; the live-ops audit's findings 3, 9 and 12).

Until now nothing told anyone when a channel the rule reads went stale, when the activity opener failed to run (the build
quietly reuses its last outputs), when a breadth month failed to publish, or when the FOMC calendar in the opener was about
to run out. This reads what the build just wrote and raises one alert per problem through s2/alert.sh (ntfy and a GitHub
issue), at most once every three days per problem while it persists. It never fails its caller.
    python3 s2/watchdog.py            (from the workspace, after bhs_build.py)"""
import json, os, re, subprocess, datetime
try:
    from zoneinfo import ZoneInfo
    TODAY = datetime.datetime.now(ZoneInfo('America/New_York')).date()
except Exception:
    TODAY = datetime.date.today()
SENT_F = os.path.join('cache', 'watchdog_sent.json')
EVERY_DAYS = 3

def load(p):
    try: return json.load(open(p))
    except Exception: return None

def main():
    st = load(os.path.join('out', 'bhs_state.json')) or {}
    ao = load(os.path.join('out', 'activity_opener_state.json')) or {}
    problems = []   # (key, level, message)
    for c in st.get('channels') or []:
        if c.get('status') != 'current':
            problems.append(('chan:' + c.get('channel', '?'), 'CHANNEL STALE', '%s: last %s, %s days old, limit %s days, status %s%s' % (
                c.get('channel'), c.get('last'), c.get('age_days'), c.get('limit_days'), c.get('status'),
                (', substitute ' + str(c['substitute'])) if c.get('substitute') else '')))
    for k, c in (ao.get('channels') or {}).items():
        if (c or {}).get('status') != 'current':
            problems.append(('aochan:' + k, 'CHANNEL STALE', 'activity opener %s: %s days old, limit %s days, status %s' % (k, c.get('age_days'), c.get('limit_days'), c.get('status'))))
    if ao.get('asof') != TODAY.isoformat():
        problems.append(('ao:asof', 'OPENER DID NOT RUN', 'the activity opener\'s reading is as of %s, not today (%s): the build reused its last outputs' % (ao.get('asof'), TODAY)))
    nb = ao.get('next_breadth_publication')
    if nb:
        try:
            late = (TODAY - datetime.date.fromisoformat(nb)).days
            if late > 10: problems.append(('ao:breadth', 'BREADTH MONTH OVERDUE', 'the breadth month due %s is %d days late: fewer than 45 states have every report week in the ETA 539 file' % (nb, late)))
        except Exception: pass
    if ao.get('next_fomc_estimated'):
        problems.append(('ao:fomc_est', 'FOMC DATE ESTIMATED', 'the next FOMC decision day (%s) is an estimate: add the Federal Reserve\'s calendar to FOMC in s2/activity_opener.py' % ao.get('next_fomc')))
    try:
        src = open(os.path.join('s2', 'activity_opener.py')).read()
        m = re.search(r"^FOMC = \[(.*?)\]", src, re.S | re.M)
        last = max(re.findall(r"'(\d{4}-\d{2}-\d{2})'", m.group(1))) if m else None
        if last and (datetime.date.fromisoformat(last) - TODAY).days <= 120:
            problems.append(('fomc:end', 'FOMC LIST ENDS', 'the FOMC decision days in s2/activity_opener.py end on %s: add the next year\'s from federalreserve.gov/monetarypolicy/fomccalendars.htm' % last))
    except Exception: pass
    sent = load(SENT_F) or {}
    now = TODAY.isoformat(); out = 0
    for key, level, msg in problems:
        prev = sent.get(key)
        if prev and (TODAY - datetime.date.fromisoformat(prev)).days < EVERY_DAYS: continue
        if os.environ.get('WATCHDOG_DRY'): print('DRY', level, msg); continue
        try: subprocess.run(['bash', os.path.join('s2', 'alert.sh'), level, msg], timeout=90)
        except Exception: pass
        sent[key] = now; out += 1
    for key in [k for k in sent if k not in {p[0] for p in problems}]: sent.pop(key)   # a problem that cleared can alert again later
    try: json.dump(sent, open(SENT_F, 'w'), indent=0)
    except Exception: pass
    print('watchdog: %d problem(s), %d alert(s) sent%s' % (len(problems), out, (': ' + '; '.join(p[1] + ' ' + p[2][:80] for p in problems)) if problems else ''))

if __name__ == '__main__':
    try: main()
    except Exception as e: print('watchdog: failed (%r); the run goes on' % (e,))
