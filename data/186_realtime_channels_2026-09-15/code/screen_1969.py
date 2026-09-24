#!/usr/bin/env python3
"""The 1969 screen: the same method, with confirmers that can actually form a line by 1969.

WHY RE-RUN IT. The first screen ran over 573 channels because that is all the collection held at the
time. It now holds **5,939**: the whole remaining FRED weekly and daily catalogue, the NBER
Macrohistory series, and the two datasets fetched specifically for the mechanisms the first screen
found blind -- EIA Monthly Energy Review electricity generation back to **1949**, where the daily grid
data only reached 2015, and NOAA billion-dollar disaster **costs** back to 1980, where FEMA gave only a
count. A screen that named grid and climate as blind spots while holding neither of those series was
answering a question about the data it had, not about the world.

IDENTICAL ARITHMETIC. Each channel is scored against a fixed confirmer set by a fixed function; no
channel's result depends on another's. The computation is a pure map, so splitting it across processes
changes only the order rows arrive in, and the output is sorted before it is written.

The bar is unchanged and is not relaxed for the larger pool: zero quiet firings, at least one call
inside [-92, -1], every firing over the whole 1946-2026 span counted, and the July 1965 - June 1968
credit crunch scored like any other stretch rather than excluded.

RECESSION INDICATORS ARE EXCLUDED HERE, not merely downstream. The first screen admitted USRECDP,
USRECDM and a recession probability into the candidate pool, and they were only caught at the
selection step. A channel that IS the recession indicator predicts recessions perfectly and means
nothing, so it is refused at the point of entry.
"""
import os, re, json, itertools, warnings, numpy as np, pandas as pd
import multiprocessing as mp
warnings.filterwarnings('ignore')
_C = [os.path.expanduser('~/Projects/Onset Detector Data'), os.path.expanduser('~/mnt/Onset Detector Data')]
ROOT = next((c for c in _C if os.path.isdir(os.path.join(c, '186_realtime_channels_2026-09-15'))), _C[0])
HERE = os.path.join(ROOT, '186_realtime_channels_2026-09-15')
VDIR, OUT = os.path.join(HERE, 'vintages'), os.path.join(HERE, 'out')
FOLDERS = [os.path.join(HERE, 'data'), os.path.join(HERE, 'data_highfreq'), os.path.join(HERE, 'data_nber'),
           os.path.join(ROOT, '183_transmission_channels_2026-09-15', 'data'),
           os.path.join(ROOT, '182_channel_coverage_2026-09-15', 'data')]
LEAK = re.compile(r'^(USREC|RECPRO|JHDUSRGDPBR|USARECD|NBERREC|CANREC|.*RECD[MPQ]$)', re.I)
NBER = [('1948-11','1949-10'),('1953-07','1954-05'),('1957-08','1958-04'),('1960-04','1961-02'),
        ('1969-12','1970-11'),('1973-11','1975-03'),('1980-01','1980-07'),('1981-07','1982-11'),
        ('1990-07','1991-03'),('2001-03','2001-11'),('2007-12','2009-06'),('2020-02','2020-04'),
        ('2024-04','2024-08')]
def me(y): return pd.Timestamp(y + '-01') + pd.offsets.MonthEnd(0)
PK = [me(p) for p, _ in NBER]; TR = [me(t) for _, t in NBER]
def inside(t): return any(p <= t <= r for p, r in zip(PK, TR))
CRUNCH = (pd.Timestamp('1965-07-01'), pd.Timestamp('1968-06-30'))
IDX = pd.date_range('1946-01-31', '2026-09-30', freq='D')

def rd_any(sid):
    for f in FOLDERS:
        p = os.path.join(f, sid + '.csv')
        if os.path.exists(p):
            try: q = pd.read_csv(p)
            except Exception: return None
            c = list(q.columns)
            if len(c) < 2: return None
            try:
                s = pd.Series(pd.to_numeric(q[c[1]], errors='coerce').values,
                              index=pd.to_datetime(q[c[0]], errors='coerce')).dropna().sort_index()
            except Exception: return None
            return s[~s.index.duplicated(keep='last')]
    return None
def fp(sid):
    p = os.path.join(VDIR, sid + '_firstprint.csv')
    if not os.path.exists(p): return None, None
    try: q = pd.read_csv(p)
    except Exception: return None, None
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
def daily(b): return b.reindex(IDX.union(b.index)).ffill().reindex(IDX).fillna(False).astype(bool)
def hold(b, d): return b.rolling(d, min_periods=1).max().astype(bool)
def over_q(x, q, win):
    ln = x.shift(1).rolling(win, min_periods=max(10, win // 2)).quantile(q / 100.0)
    return (x > ln) & ln.notna()
def episodes(fire, minexp=9):
    out, armed, last = [], True, None
    for t, f in fire.items():
        if armed and f: out.append(t); armed = False; last = t
        elif not armed and last is not None and (t - last).days >= minexp * 30 and not f: armed = True
    return out
def score(calls):
    used, leads = set(), {}
    for p in PK:
        c = [t for t in calls if 0 <= (p - t).days <= 400]
        if c: t = max(c); leads[p.strftime('%Y-%m')] = (t - p).days; used.add(t)
    quiet = [t for t in calls if t not in used and not inside(t)]
    crunch = [t for t in quiet if CRUNCH[0] <= t <= CRUNCH[1]]
    return len(calls), len(leads), len({k: v for k, v in leads.items() if -92 <= v <= -1}), len(quiet), \
           len(crunch), json.dumps({k: v for k, v in leads.items() if -92 <= v <= -1}), json.dumps(leads)
DIRS = {'rise6m': lambda s, k: s.diff(k), 'fall6m': lambda s, k: -s.diff(k),
        'yoy_up': lambda s, k: s.pct_change(2 * k) * 100, 'yoy_down': lambda s, k: -s.pct_change(2 * k) * 100}
# WHY THIS SET AND THIS WINDOW. The main screen reported ZERO channels covering December 1969 and that
# looked like a real gap, because 1969 sits inside the data's range. It is not obviously real. That
# screen used a twenty-year confirmer window, and its confirmers begin in 1959 (housing starts), 1960
# (permits), 1967 (claims) and 1976 (the term spread) -- so at 1969 only two of the six could have a
# line at all. It is the same unreachability-by-construction that made the early-peaks sweep return
# zeros for 1948, 1953 and 1957 until it was rebuilt.
# So: confirmers that all reach back far enough, and a ten-year window so a line exists by 1969.
CONFS = {
 'ip_falling':      ('INDPRO', lambda s, k: -s.pct_change(k) * 100),          # 1919
 'hours_falling':   ('AWHMAN', lambda s, k: -s.diff(k)),                      # 1939
 'mfg_emp_falling': ('MANEMP', lambda s, k: -s.pct_change(k) * 100),          # 1939
 'unrate_rising':   ('UNRATE', lambda s, k: s.diff(k)),                       # 1948
 'metals_price_falling': ('WPU101', lambda s, k: -s.pct_change(k) * 100),     # 1926
 'starts_falling':  ('HOUST',  lambda s, k: -s.pct_change(2 * k) * 100),      # 1959
 'layoff_rate_rising': ('M0852BUSM497NNBR', lambda s, k: s.diff(k)),          # 1930
 'freight_cars_falling': ('M03002USM544NNBR', lambda s, k: -s.pct_change(2 * k) * 100),  # 1918
}
CB = None
def init():
    global CB
    CB = {}
    for cn, (sid, fn) in CONFS.items():
        x, ny, how = as_of(sid, fn)
        if x is None: continue
        for cq, cwy in itertools.product((90, 95), (10,)):
            CB[(cn, cq, cwy, how)] = hold(daily(over_q(x, cq, max(12, int(cwy * ny)))), 270)
def one(sid):
    out = []
    for dname, dfn in DIRS.items():
        x, ny, how = as_of(sid, dfn)
        if x is None: continue
        for pq, pwy, phold in itertools.product((95, 97), (10, 20), (180, 270)):
            Pb = hold(daily(over_q(x, pq, max(12, int(pwy * ny)))), phold)
            for (cn, cq, cwy, chow), Cb in CB.items():
                n, nh, ni, nq, nc, iw, al = score(episodes(Pb & Cb))
                if nq == 0 and ni > 0 and '1969-12' in iw:
                    out.append(dict(proposer=sid, direction=dname, p_read=how, p_q=pq, p_win=pwy,
                                    p_hold=phold, confirmer=cn, c_read=chow, c_q=cq, c_win=cwy,
                                    n_fire=n, n_peak=nh, n_in=ni, n_quiet=nq, n_crunch=nc,
                                    inwindow=iw, all_leads=al))
    return out
if __name__ == '__main__':
    import time
    conf_ids = {v[0] for v in CONFS.values()}
    seen, cand = set(), []
    for f in FOLDERS:
        if not os.path.isdir(f): continue
        for fn_ in sorted(os.listdir(f)):
            if not fn_.endswith('.csv'): continue
            sid = fn_[:-4]
            if sid in seen or sid in conf_ids or LEAK.match(sid): continue
            seen.add(sid); cand.append(sid)
    ncpu = max(1, (os.cpu_count() or 4) - 1)
    print('candidate channels %d, workers %d' % (len(cand), ncpu), flush=True)
    t0 = time.time(); rows = []
    with mp.Pool(ncpu, initializer=init) as pool:
        for i, res in enumerate(pool.imap_unordered(one, cand, chunksize=8)):
            rows += res
            if (i + 1) % 250 == 0:
                print('  %d/%d, %d admissible, %.1f min' % (i + 1, len(cand), len(rows),
                                                            (time.time() - t0) / 60), flush=True)
    D = pd.DataFrame(rows)
    if len(D): D = D.sort_values(['proposer','direction','p_q','p_win','p_hold','confirmer','c_q']).reset_index(drop=True)
    D.to_csv(os.path.join(OUT, 'screen_1969.csv'), index=False)
    print('\ncompleted in %.1f minutes' % ((time.time() - t0) / 60))
    print('ADMISSIBLE leg configurations: %d over %d distinct channels'
          % (len(D), D.proposer.nunique() if len(D) else 0))
