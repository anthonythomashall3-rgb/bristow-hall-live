#!/usr/bin/env python3
"""Every transmission channel ever collected, priced as an armed leg in the episode form.

THE QUESTION THIS ANSWERS. Collection 183 priced 48 transmission series and found 19 admissible, and
only three of them -- H, D and O -- have ever been put into a walk. The other sixteen were never tested,
and they were priced as single objects rather than as conjunctions, and as point events rather than as
episodes. Three separate reasons the earlier answer was incomplete.

This prices all of them the same way, on the form that `leg_K_state.py` established works: a cause-side
proposer conjoined with a demand or housing confirmer, each held open for a window, and the day each
episode of the conjoined state opens taken as one leg proposal. That is the form a walk can inject and
it is the form leg K survived.

Every series in collections 182, 183 and 186 is offered as a proposer. Six confirmers are fixed in
advance, chosen because each is causally distinct from the cause side and each reaches far back:
housing starts and permits (construction), factory hours and industrial production (production), initial
claims (labour), the term spread (money).

The bar is this programme's standing one and is not relaxed here: **zero quiet firings**, at least one
call inside [-92, -1], and the July 1965 - June 1968 credit crunch scored like any other stretch rather
than excluded. Where first prints exist they are used and dated by their actual publication day; where
they do not, the current file is read with the frequency's publication lag charged, and the `p_read`
column says which, so a result that depends on revised data can be told from one that does not.
"""
import os, json, itertools, warnings, numpy as np, pandas as pd
warnings.filterwarnings('ignore')
_C = [os.path.expanduser('~/Projects/Onset Detector Data'), os.path.expanduser('~/mnt/Onset Detector Data')]
ROOT = next((c for c in _C if os.path.isdir(os.path.join(c, '186_realtime_channels_2026-09-15'))), _C[0])
HERE = os.path.join(ROOT, '186_realtime_channels_2026-09-15')
VDIR, OUT = os.path.join(HERE, 'vintages'), os.path.join(HERE, 'out')
BADFILES = []
FOLDERS = [os.path.join(ROOT, '186_realtime_channels_2026-09-15', 'data'),
           os.path.join(ROOT, '186_realtime_channels_2026-09-15', 'data_highfreq'),
           os.path.join(ROOT, '183_transmission_channels_2026-09-15', 'data'),
           os.path.join(ROOT, '182_channel_coverage_2026-09-15', 'data')]
NBER = [('1948-11','1949-10'),('1953-07','1954-05'),('1957-08','1958-04'),('1960-04','1961-02'),
        ('1969-12','1970-11'),('1973-11','1975-03'),('1980-01','1980-07'),('1981-07','1982-11'),
        ('1990-07','1991-03'),('2001-03','2001-11'),('2007-12','2009-06'),('2020-02','2020-04'),
        ('2024-04','2024-08')]
def me(y): return pd.Timestamp(y + '-01') + pd.offsets.MonthEnd(0)
PK = [me(p) for p, _ in NBER]; TR = [me(t) for _, t in NBER]
def inside(t): return any(p <= t <= r for p, r in zip(PK, TR))
CRUNCH = (pd.Timestamp('1965-07-01'), pd.Timestamp('1968-06-30'))

def rd_any(sid):
    # Tolerant by design. The first run of this sweep crashed on a CSV that a fetch script was still
    # writing when the sweep read it -- a race of my own making. A malformed or half-written file is
    # skipped and recorded rather than stopping a run that takes an hour.
    for f in FOLDERS:
        p = os.path.join(f, sid + '.csv')
        if os.path.exists(p):
            try:
                q = pd.read_csv(p)
            except Exception:
                BADFILES.append(p); return None
            c = list(q.columns)
            if len(c) < 2: BADFILES.append(p); return None
            try:
                s = pd.Series(pd.to_numeric(q[c[1]], errors='coerce').values,
                              index=pd.to_datetime(q[c[0]], errors='coerce')).dropna().sort_index()
            except Exception:
                BADFILES.append(p); return None
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
def spacing(s):
    return float(np.median(np.diff(s.index.values).astype('timedelta64[D]').astype(int))) if len(s) > 8 else 30.0
def lag_for(sp): return 1 if sp <= 3 else (12 if sp <= 10 else (40 if sp <= 45 else 120))

def as_of(sid, fn):
    s, pb = fp(sid)
    if s is not None and len(s) > 60:
        sp = spacing(s); k = max(1, int(round(182.0 / max(sp, 1))))
        x = fn(s, k).replace([np.inf, -np.inf], np.nan).dropna()
        idx, vals = [], []
        for t, v in x.items():
            a = pb.get(t)
            if a is None or pd.isna(a): continue
            idx.append(pd.Timestamp(a)); vals.append(v)
        if len(idx) > 60:
            y = pd.Series(vals, index=idx).sort_index()
            return y[~y.index.duplicated(keep='first')], max(1, int(round(365.0 / max(sp, 1)))), 'firstprint'
    s = rd_any(sid)
    if s is None or len(s) < 60: return None, None, None
    sp = spacing(s); k = max(1, int(round(182.0 / max(sp, 1))))
    x = fn(s, k).replace([np.inf, -np.inf], np.nan).dropna()
    if len(x) < 60: return None, None, None
    x.index = x.index + pd.Timedelta(days=lag_for(sp))
    return x, max(1, int(round(365.0 / max(sp, 1)))), 'current+lag'

# Two directions per series, because a channel can deteriorate by rising or by falling and which one it
# is is a property of the series, not something to be decided by looking at the answer. Both are offered
# and both are scored; the column says which.
DIRS = {'rise6m': lambda s, k: s.diff(k), 'fall6m': lambda s, k: -s.diff(k),
        'yoy_up': lambda s, k: s.pct_change(2 * k) * 100, 'yoy_down': lambda s, k: -s.pct_change(2 * k) * 100}
CONFS = {
 'starts_falling':  ('HOUST',  lambda s, k: -s.pct_change(2 * k) * 100),
 'permits_falling': ('PERMIT', lambda s, k: -s.pct_change(2 * k) * 100),
 'hours_falling':   ('AWHMAN', lambda s, k: -s.diff(k)),
 'ip_falling':      ('INDPRO', lambda s, k: -s.pct_change(k) * 100),
 'claims_up':       ('IC4WSA', lambda s, k: s.pct_change(2 * k) * 100),
 'term_spread_low': ('T10Y2Y', lambda s, k: -s),
}
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
           len(crunch), json.dumps({k: v for k, v in leads.items() if -92 <= v <= -1}), json.dumps(leads)

CB = {}
for cn, (sid, fn) in CONFS.items():
    x, ny, how = as_of(sid, fn)
    if x is None: continue
    for cq, cwy in itertools.product((90, 95), (20,)):
        CB[(cn, cq, cwy)] = (hold(daily(over_q(x, cq, max(12, int(cwy * ny)))), 270), how)
print('confirmers built:', sorted(set(k[0] for k in CB)))

CONF_SERIES = {v[0] for v in CONFS.values()}
seen, cand = set(), []
for f in FOLDERS:
    if not os.path.isdir(f): continue
    for fn_ in sorted(os.listdir(f)):
        if not fn_.endswith('.csv'): continue
        sid = fn_[:-4]
        if sid in seen or sid in CONF_SERIES: continue
        seen.add(sid); cand.append(sid)
print('candidate proposers: %d' % len(cand))

rows, done = [], 0
for sid in cand:
    for dname, dfn in DIRS.items():
        x, ny, how = as_of(sid, dfn)
        if x is None: continue
        for pq, pwy, phold in itertools.product((95, 97), (10, 20), (180, 270)):
            Pb = hold(daily(over_q(x, pq, max(12, int(pwy * ny)))), phold)
            for (cn, cq, cwy), (Cb, chow) in CB.items():
                n, nh, ni, nq, nc, iw, al = score(episodes(Pb & Cb))
                if nq == 0 and ni > 0:
                    rows.append(dict(proposer=sid, direction=dname, p_read=how, p_q=pq, p_win=pwy,
                                     p_hold=phold, confirmer=cn, c_read=chow, c_q=cq, c_win=cwy,
                                     n_fire=n, n_peak=nh, n_in=ni, n_quiet=nq, n_crunch=nc,
                                     inwindow=iw, all_leads=al))
    done += 1
    if done % 25 == 0: print('  %d/%d proposers, %d admissible so far' % (done, len(cand), len(rows)), flush=True)
D = pd.DataFrame(rows)
D.to_csv(os.path.join(OUT, 'all_channels_as_legs.csv'), index=False)
print('unreadable files skipped: %d %s' % (len(BADFILES), BADFILES[:5]))
pd.set_option('display.width', 270)
COL = ['proposer','direction','p_read','p_q','p_win','p_hold','confirmer','c_q','n_fire','n_peak','n_in','n_crunch','inwindow']
print('\nADMISSIBLE leg configurations (zero quiet firings, >=1 call inside [-92,-1]): %d' % len(D))
if len(D):
    print('\ndistinct proposer series that produce at least one admissible leg: %d' % D.proposer.nunique())
    print(D.sort_values(['n_in','n_peak','n_fire'], ascending=[False,False,True])[COL].head(30).to_string(index=False))
    print('\n-- best configuration per proposer series, ranked by calls inside the window --')
    b = D.sort_values(['n_in','n_peak','n_fire'], ascending=[False,False,True]).groupby('proposer').head(1)
    print(b.sort_values(['n_in','n_peak'], ascending=False)[COL].head(40).to_string(index=False))
    print('\n-- read entirely on first prints --')
    z = D[(D.p_read == 'firstprint')]
    print(z.sort_values(['n_in','n_peak'], ascending=False)[COL].head(15).to_string(index=False) if len(z) else '   none')
