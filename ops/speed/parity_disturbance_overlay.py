#!/usr/bin/env python3
"""PARITY AND REPLAY OF THE DISTURBANCE SERIES' PUBLISHER OVERLAY (speed program 1052, 17 Nov 2026). No AI. Runs on GitHub Actions.

1. parity: for each series s2/disturbance/fred_refresh.py can take from its publisher on a release day (INDPRO: the G.17 file; PAYEMS,
   UNRATE: the BLS; GDPC1, W875RX1: the BEA), the publisher's series now must equal FRED's current fredgraph file on every month FRED
   carries (same months, same values) - the overlay then writes what the FRED path writes once FRED has posted.
2. replay of 17 Nov 2026 (the G.17 at 9:15 ET): FRED's INDPRO as it stood the day before (ALFRED, realtime 2026-11-16) is the file the
   9:16 release run downloaded; the overlay applied to it (the release day forced) must give FRED's file after its post, value for value.
Exit 1 on any difference."""
import os, sys, io, json, shutil, tempfile, urllib.request, urllib.parse
import pandas as pd
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WS = os.path.join(ROOT, 'data', '105_bristow_hall_system_2026-09-08', 'workspace')
sys.path.insert(0, os.path.join(WS, 's2')); sys.path.insert(0, os.path.join(WS, 's2', 'disturbance'))
import publisher_first as pf
import fred_refresh as fr
KEY = os.environ.get('FRED_API_KEY', '')


def fredgraph(s):
    for i in range(4):
        try:
            t = urllib.request.urlopen('https://fred.stlouisfed.org/graph/fredgraph.csv?id=' + s, timeout=60).read().decode(); break
        except Exception:
            if i == 3: raise
            import time; time.sleep(10 * (i + 1))
    d = pd.read_csv(io.StringIO(t)); d.columns = ['date', 'v']; d['v'] = pd.to_numeric(d.v, errors='coerce'); d = d.dropna()
    return pd.Series(d.v.values, index=pd.to_datetime(d.date))


def read(f):
    d = pd.read_csv(f); d.columns = ['date', 'v']; d['v'] = pd.to_numeric(d.v, errors='coerce'); d = d.dropna()
    return pd.Series(d.v.values, index=pd.to_datetime(d.date))


def main():
    out = {'parity': {}, 'ok': True}
    for s in fr.OVERLAY:
        try:
            pub = (pf.bea_series('T20600', '36', 'M') if s == 'W875RX1' else pf.publisher([s], full=True)[s]).dropna()
            f = fredgraph(s); pub = pub[pub.index >= f.index[0]]
            ix = f.index.union(pub.index)
            diff = [str(x.date()) for x in ix if not (x in f.index and x in pub.index and f[x] == pub[x])]
            out['parity'][s] = dict(fred_months=len(f), publisher_months=len(pub), differing=diff[:12], equal=not diff)
        except Exception as e:
            out['parity'][s] = dict(error=str(e)[:200], equal=False)
        out['ok'] &= out['parity'][s]['equal']
        print('%-8s %s' % (s, out['parity'][s]))
    # the replay of 17 Nov 2026
    q = urllib.parse.urlencode(dict(series_id='INDPRO', api_key=KEY, file_type='json', realtime_start='2026-11-16', realtime_end='2026-11-16'))
    obs = json.load(urllib.request.urlopen('https://api.stlouisfed.org/fred/series/observations?' + q, timeout=60))['observations']
    tmp = tempfile.mkdtemp(); f = os.path.join(tmp, 'INDPRO.csv')
    open(f, 'w').write('observation_date,INDPRO\n' + ''.join('%s,%s\n' % (o['date'], o['value']) for o in obs if o['value'] != '.'))
    before = read(f)
    for k in list(fr.OVERLAY):
        if k != 'INDPRO': fr.OVERLAY.pop(k)
    real = pf.release_days; pf.release_days = lambda g, extra=None: real(g) | {pf.ny_day()}   # the release day forced
    fr.publisher_overlay(tmp)
    after = read(f); now = fredgraph('INDPRO')
    ix = after.index.union(now.index)
    d = [str(x.date()) for x in ix if not (x in after.index and x in now.index and after[x] == now[x])]
    out['replay_17nov'] = dict(fred_day_before_through=str(before.index[-1].date()), sep_day_before=float(before.get(pd.Timestamp('2026-09-01'), float('nan'))),
                               overlay_through=str(after.index[-1].date()), sep_overlay=float(after.get(pd.Timestamp('2026-09-01'), float('nan'))),
                               oct_overlay=float(after.get(pd.Timestamp('2026-10-01'), float('nan'))), fred_now_through=str(now.index[-1].date()),
                               differing_from_fred_now=d[:12], equal=not d)
    out['ok'] &= not d
    print('replay 17 Nov:', out['replay_17nov'])
    os.makedirs(os.path.join(ROOT, 'ops', 'speed', 'out'), exist_ok=True)
    json.dump(out, open(os.path.join(ROOT, 'ops', 'speed', 'out', 'parity_disturbance_overlay.json'), 'w'), indent=1)
    print('OVERLAY PARITY', 'PASS' if out['ok'] else 'FAIL'); sys.exit(0 if out['ok'] else 1)


if __name__ == '__main__':
    main()
