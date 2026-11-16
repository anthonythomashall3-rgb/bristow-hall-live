#!/usr/bin/env python3
"""RELEASE TO LIVE, MEASURED (speed program 1052). No AI. Reads the repository's own history after a release day:
every run that publishes commits the built site right after its Cloudflare deploy, so the commit time of the first build whose
published state carries the new period is an UPPER bound on the moment the figure went live (the deploy is about a minute before).
The publisher's time is the scheduled release time given on the command line (or --pub-time measured from the publisher).

    python3 ops/speed/measure_release_to_live.py --day 2026-11-17 --release 09:15 --series INDPRO
    python3 ops/speed/measure_release_to_live.py --day 2026-11-19 --release 08:30 --series ICSA,CCSA,CCNSA
    python3 ops/speed/measure_release_to_live.py --day 2026-11-20 --release 10:00 --page state-onset/index.html,stress-map/index.html

--series: detector readings (bhs_state.json "readings", by the source gate's object prefixes); --page: any published file, measured
as the first commit after the release that changed it. Prints one line per series/page: release, live (upper bound), minutes."""
import os, re, sys, json, argparse, subprocess, datetime as dt
from zoneinfo import ZoneInfo
ET, UTC = ZoneInfo('America/New_York'), dt.timezone.utc
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PUB = 'data/105_bristow_hall_system_2026-09-08/site/public/'
OBJ = {'INDPRO': 'route: industrial production', 'PAYEMS': 'route: payrolls', 'UNRATE': 'route: unemployment rate',
       'UNEMPLOY': "count door: the unemployed count", 'LNS13023621': 'job-losers door: unemployed job losers',
       'JTSJOL': 'route: job openings', 'ICSA': 'count door: initial or insured claims', 'CCNSA': 'route: insured unemployment',
       'CCSA': 'E22 leg A: insured unemployment', 'FEDFUNDS': 'fed-shock door', 'BAA': "route: Moody's Baa", 'SP500': 'route: S&P 500'}


def git(*a): return subprocess.run(['git', '-C', ROOT] + list(a), capture_output=True, text=True).stdout


def commits(path, since, until):
    out = []
    for ln in git('log', 'origin/main', '--first-parent', '--format=%H %cI', '--since', since.isoformat(), '--until', until.isoformat(), '--', PUB + path).splitlines():
        h, t = ln.split(' ', 1); out.append((dt.datetime.fromisoformat(t).astimezone(UTC), h))
    return sorted(out)


def through(h, sid):
    try: S = json.loads(git('show', '%s:%sbhs_state.json' % (h, PUB)))
    except Exception: return None
    for r in S.get('readings') or []:
        if (r.get('object') or '').startswith(OBJ[sid]): return r.get('through')
    return None


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--day', required=True); ap.add_argument('--release', required=True)
    ap.add_argument('--series', default=''); ap.add_argument('--page', default=''); a = ap.parse_args()
    subprocess.run(['git', '-C', ROOT, 'fetch', '-q', 'origin', 'main'])
    rel = dt.datetime.strptime(a.day + ' ' + a.release, '%Y-%m-%d %H:%M').replace(tzinfo=ET)
    lo, hi = rel - dt.timedelta(hours=18), rel + dt.timedelta(hours=14)
    rows = []
    for sid in [s for s in a.series.split(',') if s]:
        cs = commits('bhs_state.json', lo, hi); before = [h for t, h in cs if t < rel]
        base = through(before[-1], sid) if before else None
        hit = next(((t, h, through(h, sid)) for t, h in cs if t >= rel and (through(h, sid) or '') > (base or '')), None)
        rows.append((sid, base, hit))
    for p in [s for s in a.page.split(',') if s]:
        cs = commits(p, rel, hi); rows.append((p, None, (cs[0][0], cs[0][1], 'changed') if cs else None))
    for name, base, hit in rows:
        if not hit: print('%-28s release %s ET | not live by %s ET (through %s)' % (name, a.release, hi.astimezone(ET).strftime('%m-%d %H:%M'), base)); continue
        t, h, th = hit; m = (t - rel).total_seconds() / 60
        print('%-28s release %s ET | live by %s ET (commit %s; %s -> %s) | %.1f min %s' % (name, a.release, t.astimezone(ET).strftime('%H:%M:%S'), h[:8], base, th, m, 'OK' if m <= 5 else 'OVER 5'))


if __name__ == '__main__':
    main()
