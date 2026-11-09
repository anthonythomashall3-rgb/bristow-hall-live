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
    # C1021 (1022, 8 November 2026): the v3.76 starter's watch (activity opener, breadth month, FOMC list) is retired with it.
    # The C1021 starter's watch: did s2/c1021.py run today, and does any pillar read dark or stale.
    c1 = load(os.path.join('out', 'c1021_state.json')) or {}
    problems = []   # (key, level, message)
    for c in st.get('channels') or []:
        if c.get('status') != 'current':
            problems.append(('chan:' + c.get('channel', '?'), 'CHANNEL STALE', '%s: last %s, %s days old, limit %s days, status %s%s' % (
                c.get('channel'), c.get('last'), c.get('age_days'), c.get('limit_days'), c.get('status'),
                (', substitute ' + str(c['substitute'])) if c.get('substitute') else '')))
    _td = c1.get('today'); _td = _td.get('day') if isinstance(_td, dict) else _td
    if str(_td or '')[:10] != TODAY.isoformat():
        problems.append(('c1021:today', 'STARTER DID NOT RUN', 'the C1021 starter\'s reading is as of %s, not today (%s): the build reused its last outputs' % (_td, TODAY)))
    if st.get('version') != 'C1021+E22':
        problems.append(('c1021:version', 'VERSION', 'the published state says version %s, not C1021+E22' % st.get('version')))
    # E22 (1031): did the ender run today; are its three inputs fresh (insured unemployment week, the funds-rate month, the S&P day)
    e2 = load(os.path.join('out', 'e22_state.json')) or {}
    if str(e2.get('today') or '')[:10] != TODAY.isoformat():
        problems.append(('e22:today', 'ENDER DID NOT RUN', 'the E22 ender\'s state is as of %s, not today (%s)' % (e2.get('today'), TODAY)))
    _ev = e2.get('values') or {}
    for k, f, lim in (('iu4', 'week', 20), ('iu_nsa', 'week', 27), ('rate', 'month', 35), ('sp', 'day', 6)):   # iu_nsa: the NSA print the two-print rule reads (ALFRED's initial release, a week behind the SA print)
        thr = (_ev.get(k) or {}).get(f)
        if not thr: problems.append(('e22:' + k, 'ENDER INPUT DARK', 'E22 input %s has no %s' % (k, f))); continue
        try:
            t = str(thr)
            if len(t) == 7: y, m = int(t[:4]), int(t[5:]); t = (datetime.date(y + (m == 12), 1 if m == 12 else m + 1, 1) - datetime.timedelta(days=1))
            else: t = datetime.date.fromisoformat(t[:10])
            age = (TODAY - t).days
            if age > lim: problems.append(('e22:' + k, 'ENDER INPUT STALE', 'E22 input %s reads through %s, %d days old (limit %d)' % (k, thr, age, lim)))
        except Exception: pass
    # each pillar's newest datum and how old it may be (days from the week-ending day, the trading day or the month's end)
    _key = {'SY': ('sp_last_day', 6), 'I4': ('week', 20), 'HW': ('week', 13), 'CHI': ('ic_week', 13), 'IP': ('month', 50), 'BAA': ('month', 40),
            'HH': ('month', 40), 'P': ('month', 40), 'CNT': ('month', 40), 'FS': ('month', 35), 'JL': ('month', 75)}
    for k, (f, lim) in _key.items():
        v = (c1.get('values') or {}).get(k) or {}
        thr = v.get(f)
        if not thr: problems.append(('c1021:' + k, 'PILLAR DARK', 'C1021 pillar %s has no %s in the starter\'s state' % (k, f))); continue
        try:
            t = str(thr)
            if len(t) == 7: y, m = int(t[:4]), int(t[5:]); t = (datetime.date(y + (m == 12), 1 if m == 12 else m + 1, 1) - datetime.timedelta(days=1))
            else: t = datetime.date.fromisoformat(t[:10])
            age = (TODAY - t).days
            if age > lim: problems.append(('c1021:' + k, 'PILLAR STALE', 'C1021 pillar %s reads through %s, %d days old (limit %d)' % (k, thr, age, lim)))
        except Exception: pass
    if c1.get('live_calls'):
        problems.append(('c1021:live', 'LIVE CALL', 'the C1021 starter has made a live call: %s' % c1.get('live_calls')))
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
