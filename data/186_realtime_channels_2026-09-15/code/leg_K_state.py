#!/usr/bin/env python3
"""Leg K, second attempt: take the conjunction's EPISODES as the leg's proposals.

WHY THE FIRST ATTEMPT FAILED, AND WHY THIS IS NOT THE SAME MISTAKE TWICE. `cost_channel.py` measured
the cost channel as a conjunction -- two booleans each held open for a window and intersected -- and it
scored well: five calls in eighty years, 1969 at -20, 1973 at -50, 1981 at -20, no false alarm, silent
through 1966, 1987, 2011 and 2022. `leg_K_priced.py` then rebuilt it as a point event -- a locked-out
proposal with the gate asked on the publication day -- and it collapsed to one firing.

The conclusion drawn from that was that a conjunction is a state and a leg is a point event, so the
channel could only be used by changing the core. **That conclusion was too quick.** A leg is a list of
(published, dated) proposals, and a conjunction PRODUCES such a list: the day each episode of the
conjoined state opens is a date, and there are five of them. The leg does not have to be a point event
just because the legs built so far happen to be.

So this takes `episodes(P & C)` -- the same function, the same held windows, the same lines -- and
treats each episode opening as one proposal. The scoring is then identical to every other leg's, and
the numbers are comparable with leg Y's and with legs A, M, H, D and O.

What is being tested is whether the channel survives the translation when the translation is done
properly. If it does, the cost channel is usable as an armed leg after all and the earlier conclusion
was wrong. If it does not, the earlier conclusion holds and stands on two independent tests instead of
one.
"""
import os, json, itertools, warnings, numpy as np, pandas as pd
warnings.filterwarnings('ignore')
_C = [os.path.expanduser('~/Projects/Onset Detector Data'), os.path.expanduser('~/mnt/Onset Detector Data')]
ROOT = next((c for c in _C if os.path.isdir(os.path.join(c, '186_realtime_channels_2026-09-15'))), _C[0])
HERE = os.path.join(ROOT, '186_realtime_channels_2026-09-15')
DATA, VDIR, OUT = os.path.join(HERE, 'data'), os.path.join(HERE, 'vintages'), os.path.join(HERE, 'out')
S182 = os.path.join(ROOT, '182_channel_coverage_2026-09-15', 'data')
NBER = [('1948-11','1949-10'),('1953-07','1954-05'),('1957-08','1958-04'),('1960-04','1961-02'),
        ('1969-12','1970-11'),('1973-11','1975-03'),('1980-01','1980-07'),('1981-07','1982-11'),
        ('1990-07','1991-03'),('2001-03','2001-11'),('2007-12','2009-06'),('2020-02','2020-04'),
        ('2024-04','2024-08')]
def me(y): return pd.Timestamp(y + '-01') + pd.offsets.MonthEnd(0)
PK = [me(p) for p, _ in NBER]; TR = [me(t) for _, t in NBER]
def inside(t): return any(p <= t <= r for p, r in zip(PK, TR))
CRUNCH = (pd.Timestamp('1965-07-01'), pd.Timestamp('1968-06-30'))

def rd(sid):
    for f in (DATA, S182):
        p = os.path.join(f, sid + '.csv')
        if os.path.exists(p):
            q = pd.read_csv(p); c = list(q.columns)
            s = pd.Series(pd.to_numeric(q[c[1]], errors='coerce').values,
                          index=pd.to_datetime(q[c[0]], errors='coerce')).dropna().sort_index()
            return s[~s.index.duplicated(keep='last')]
    return None
def fp(sid):
    p = os.path.join(VDIR, sid + '_firstprint.csv')
    if not os.path.exists(p): return None, None
    q = pd.read_csv(p)
    d = pd.to_datetime(q['date'], errors='coerce'); pb = pd.to_datetime(q['published'], errors='coerce')
    v = pd.to_numeric(q['value'], errors='coerce'); k = d.notna() & pb.notna() & v.notna()
    s = pd.Series(v[k].values, index=d[k]).sort_index(); b = pd.Series(pb[k].values, index=d[k]).sort_index()
    return s[~s.index.duplicated(keep='first')], b[~b.index.duplicated(keep='first')]
def steps(s, days):
    sp = float(np.median(np.diff(s.index.values).astype('timedelta64[D]').astype(int))) if len(s) > 8 else 30.0
    return max(1, int(round(days / max(sp, 1)))), sp
def lag_for(sp): return 1 if sp <= 3 else (12 if sp <= 10 else (40 if sp <= 45 else 120))

def series_on_pub(sid, fn):
    """Prefer first prints dated by their actual publication day; fall back to the current file with
    the frequency's publication lag charged, and say which was used."""
    s, pb = fp(sid)
    if s is not None and len(s) > 60:
        k, sp = steps(s, 182)
        x = fn(s, k).replace([np.inf, -np.inf], np.nan).dropna()
        idx = [pd.Timestamp(pb.get(t)) for t in x.index if pd.notna(pb.get(t))]
        x = pd.Series(x.values[:len(idx)], index=idx).sort_index()
        return x[~x.index.duplicated(keep='first')], max(1, int(round(365.0 / max(sp, 1)))), 'firstprint'
    s = rd(sid)
    if s is None or len(s) < 60: return None, None, None
    k, sp = steps(s, 182)
    x = fn(s, k).replace([np.inf, -np.inf], np.nan).dropna()
    x.index = x.index + pd.Timedelta(days=lag_for(sp))
    return x, max(1, int(round(365.0 / max(sp, 1)))), 'current+lag'

PROPS = {
 'cpi_yoy':         ('CPIAUCSL',    lambda s, k: s.pct_change(2 * k) * 100),
 'prime_rise6m':    ('DPRIME',      lambda s, k: s.diff(k)),
 'fedfunds_rise6m': ('DFF',         lambda s, k: s.diff(k)),
 'mortgage_rise6m': ('MORTGAGE30US',lambda s, k: s.diff(k)),
 'oil_yoy':         ('WTISPLC',     lambda s, k: s.pct_change(2 * k) * 100),
 'ppi_yoy':         ('PPIACO',      lambda s, k: s.pct_change(2 * k) * 100),
}
CONFS = {
 'starts_falling':  ('HOUST',   lambda s, k: -s.pct_change(2 * k) * 100),
 'permits_falling': ('PERMIT',  lambda s, k: -s.pct_change(2 * k) * 100),
 'hours_falling':   ('AWHMAN',  lambda s, k: -s.diff(k)),
 'ip_falling':      ('INDPRO',  lambda s, k: -s.pct_change(k) * 100),
}
P = {}; C = {}
for n, (sid, fn) in PROPS.items():
    x, ny, how = series_on_pub(sid, fn)
    if x is not None: P[n] = (x, ny, how)
for n, (sid, fn) in CONFS.items():
    x, ny, how = series_on_pub(sid, fn)
    if x is not None: C[n] = (x, ny, how)
print('proposers :', {k: (v[2], str(v[0].index.min().date())) for k, v in P.items()})
print('confirmers:', {k: (v[2], str(v[0].index.min().date())) for k, v in C.items()})

IDX = pd.date_range('1946-01-31', '2026-09-30', freq='D')
def daily(b): return b.reindex(IDX.union(b.index)).ffill().reindex(IDX).fillna(False).astype(bool)
def hold(b, d): return b.rolling(d, min_periods=1).max().astype(bool)
def over_q(x, q, win):
    ln = x.shift(1).rolling(win, min_periods=max(10, win // 2)).quantile(q / 100.0)
    return (x > ln) & ln.notna()
def episodes(fire, minexp=9):
    calls, armed, last = [], True, None
    for t, f in fire.items():
        if armed and f: calls.append(t); armed = False; last = t
        elif not armed and last is not None and (t - last).days >= minexp * 30 and not f: armed = True
    return calls
def score(calls):
    used, leads = set(), {}
    for p in PK:
        c = [t for t in calls if 0 <= (p - t).days <= 400]
        if c: t = max(c); leads[p.strftime('%Y-%m')] = (t - p).days; used.add(t)
    quiet = [t for t in calls if t not in used and not inside(t)]
    crunch = [t for t in quiet if CRUNCH[0] <= t <= CRUNCH[1]]
    return len(calls), len(leads), len({k: v for k, v in leads.items() if -92 <= v <= -1}), len(quiet), \
           len(crunch), json.dumps({k: v for k, v in leads.items() if -92 <= v <= -1}), json.dumps(leads), \
           json.dumps([t.strftime('%Y-%m') for t in quiet][:8])
rows = []
for pn, (px, pny, phow) in P.items():
    for pq, pwy, phold in itertools.product((90, 95, 97), (10, 20), (180, 270)):
        Pb = hold(daily(over_q(px, pq, max(12, int(pwy * pny)))), phold)
        for cn, (cx, cny, chow) in C.items():
            for cq, cwy, chold in itertools.product((90, 95), (10, 20), (270,)):
                Cb = hold(daily(over_q(cx, cq, max(12, int(cwy * cny)))), chold)
                n, nh, ni, nq, nc, iw, al, qz = score(episodes(Pb & Cb))
                rows.append(dict(proposer=pn, p_read=phow, p_q=pq, p_win=pwy, p_hold=phold,
                                 confirmer=cn, c_read=chow, c_q=cq, c_win=cwy,
                                 n_fire=n, n_peak=nh, n_in=ni, n_quiet=nq, n_crunch=nc,
                                 inwindow=iw, all_leads=al, quiet=qz))
D = pd.DataFrame(rows); D.to_csv(os.path.join(OUT, 'leg_K_state.csv'), index=False)
pd.set_option('display.width', 260)
COL = ['proposer','p_read','p_q','p_win','p_hold','confirmer','c_read','c_q','c_win','n_fire','n_peak','n_in','n_quiet','n_crunch','inwindow']
print('\nconfigurations: %d' % len(D))
z = D[(D.n_quiet == 0) & (D.n_in > 0)]
print('ZERO quiet firings and at least one call inside [-92,-1]: %d' % len(z))
if len(z):
    print(z.sort_values(['n_in','n_peak','n_fire'], ascending=[False,False,True])[COL].head(20).to_string(index=False))
    zz = z[(z.p_read == 'firstprint') & (z.c_read == 'firstprint')]
    print('\n  of those, read entirely on first prints: %d' % len(zz))
    if len(zz): print(zz.sort_values(['n_in','n_peak'], ascending=False)[COL].head(10).to_string(index=False))
print('\nconfigurations firing in the 1965-68 credit crunch: %d of %d' % (int((D.n_crunch > 0).sum()), len(D)))
