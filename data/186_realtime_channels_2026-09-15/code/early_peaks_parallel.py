#!/usr/bin/env python3
"""The early-peaks sweep, across all cores. Identical arithmetic, identical output, one eighth the time.

WHY PARALLELISM CANNOT CHANGE THE ANSWER HERE. Each proposer is scored against a fixed set of
confirmers and a fixed scoring function. No proposer's result depends on any other's; nothing is
accumulated across them except a list of rows that is sorted at the end. The computation is a pure map
over proposers, so splitting it across processes changes the order rows arrive in and nothing else.
The output file is sorted before it is written, so even the order is identical.

The confirmers are built once per worker rather than once per proposer -- they are the expensive part,
twenty daily boolean series over eighty years -- and each worker keeps its own copy. That is memory
spent to avoid recomputation, not a shortcut.

Everything about the measurement is unchanged from `early_peaks_sweep.py`: the same ten confirmers,
five of which reach back to 1930 or earlier so that 1948, 1953 and 1957 are reachable; the same
rolling-quantile lines; the same 540-day-equivalent hold; the same bar of zero quiet firings and at
least one call inside [-92, -1]; and the 1965-68 credit crunch scored like any other stretch.
"""
import os, json, itertools, warnings, numpy as np, pandas as pd
import multiprocessing as mp
warnings.filterwarnings('ignore')
_C = [os.path.expanduser('~/Projects/Onset Detector Data'), os.path.expanduser('~/mnt/Onset Detector Data')]
ROOT = next((c for c in _C if os.path.isdir(os.path.join(c, '186_realtime_channels_2026-09-15'))), _C[0])
HERE = os.path.join(ROOT, '186_realtime_channels_2026-09-15')
NBERD, DATA, OUT = os.path.join(HERE, 'data_nber'), os.path.join(HERE, 'data'), os.path.join(HERE, 'out')
NBER = [('1948-11','1949-10'),('1953-07','1954-05'),('1957-08','1958-04'),('1960-04','1961-02'),
        ('1969-12','1970-11'),('1973-11','1975-03'),('1980-01','1980-07'),('1981-07','1982-11'),
        ('1990-07','1991-03'),('2001-03','2001-11'),('2007-12','2009-06'),('2020-02','2020-04'),
        ('2024-04','2024-08')]
def me(y): return pd.Timestamp(y + '-01') + pd.offsets.MonthEnd(0)
PK = [me(p) for p, _ in NBER]; TR = [me(t) for _, t in NBER]
EARLY = {'1948-11', '1953-07', '1957-08', '1960-04'}
def inside(t): return any(p <= t <= r for p, r in zip(PK, TR))
CRUNCH = (pd.Timestamp('1965-07-01'), pd.Timestamp('1968-06-30'))
LAG = 40
IDX = pd.date_range('1946-01-31', '2026-09-30', freq='D')

def rd(folder, sid):
    p = os.path.join(folder, sid + '.csv')
    if not os.path.exists(p): return None
    try: q = pd.read_csv(p)
    except Exception: return None
    c = list(q.columns)
    if len(c) < 2: return None
    s = pd.Series(pd.to_numeric(q[c[1]], errors='coerce').values,
                  index=pd.to_datetime(q[c[0]], errors='coerce')).dropna().sort_index()
    return s[~s.index.duplicated(keep='last')]
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
    inw = {k: v for k, v in leads.items() if -92 <= v <= -1}
    return len(calls), len(leads), len(inw), len(quiet), len(crunch), inw, leads

DIRS = {'fall6m':   lambda s: -s.pct_change(6) * 100,
        'fall12m':  lambda s: -s.pct_change(12) * 100,
        'rise6m':   lambda s: s.pct_change(6) * 100,
        'gap_high': lambda s: (1 - s / s.rolling(24, min_periods=8).max()) * 100}
CONFS = {
 'ip_falling':           (DATA,  'INDPRO', lambda s: -s.pct_change(6) * 100),
 'metals_price_falling': (DATA,  'WPU101', lambda s: -s.pct_change(6) * 100),
 'hours_falling':        (DATA,  'AWHMAN', lambda s: -s.diff(6)),
 'mfg_emp_falling':      (DATA,  'MANEMP', lambda s: -s.pct_change(6) * 100),
 'unrate_rising':        (DATA,  'UNRATE', lambda s: s.diff(6)),
 'layoff_rate_rising':   (NBERD, 'M0852BUSM497NNBR', lambda s: s.diff(6)),
 'separations_rising':   (NBERD, 'M0854BUSM497NNBR', lambda s: s.diff(6)),
 'accessions_falling':   (NBERD, 'M0855BUSM497NNBR', lambda s: -s.diff(6)),
 'freight_cars_falling': (NBERD, 'M03002USM544NNBR', lambda s: -s.pct_change(12) * 100),
 'business_activity_falling': (NBERD, 'M12003USM516NNBR', lambda s: -s.pct_change(6) * 100),
}
CB = None
def init():
    global CB
    CB = {}
    for cn, (fol, sid, fn) in CONFS.items():
        s = rd(fol, sid)
        if s is None or len(s) < 120: continue
        x = fn(s).replace([np.inf, -np.inf], np.nan).dropna()
        x.index = x.index + pd.Timedelta(days=LAG)
        for cq, cwin in itertools.product((90, 95), (120,)):
            CB[(cn, cq, cwin)] = hold(daily(over_q(x, cq, cwin)), 270)

def one(sid):
    s = rd(NBERD, sid)
    if s is None or len(s) < 120: return []
    out = []
    for dname, dfn in DIRS.items():
        x = dfn(s).replace([np.inf, -np.inf], np.nan).dropna()
        if len(x) < 120: continue
        x = x.copy(); x.index = x.index + pd.Timedelta(days=LAG)
        for pq, phold, pwin in itertools.product((95, 97), (270,), (120, 240)):
            Pb = hold(daily(over_q(x, pq, pwin)), phold)
            for (cn, cq, cwin), Cb in CB.items():
                n, nh, ni, nq, nc, inw, leads = score(episodes(Pb & Cb))
                if nq == 0 and ni > 0:
                    out.append(dict(proposer=sid, direction=dname, p_q=pq, p_win=pwin, p_hold=phold,
                                    confirmer=cn, c_q=cq, c_win=cwin, n_fire=n, n_peak=nh, n_in=ni,
                                    n_quiet=nq, n_crunch=nc,
                                    n_early_in=sum(1 for k in inw if k in EARLY),
                                    first=str(s.index.min().date()), last=str(s.index.max().date()),
                                    inwindow=json.dumps(inw), all_leads=json.dumps(leads)))
    return out

if __name__ == '__main__':
    import time
    files = sorted(f[:-4] for f in os.listdir(NBERD) if f.endswith('.csv'))
    ncpu = max(1, (os.cpu_count() or 4) - 1)
    print('proposers %d, workers %d' % (len(files), ncpu), flush=True)
    t0 = time.time(); rows = []
    with mp.Pool(ncpu, initializer=init) as pool:
        for i, res in enumerate(pool.imap_unordered(one, files, chunksize=4)):
            rows += res
            if (i + 1) % 50 == 0:
                print('  %d/%d, %d admissible, %.1f min' % (i + 1, len(files), len(rows),
                                                            (time.time() - t0) / 60), flush=True)
    D = pd.DataFrame(rows)
    if len(D): D = D.sort_values(['proposer', 'direction', 'p_q', 'p_win', 'confirmer', 'c_q']).reset_index(drop=True)
    D.to_csv(os.path.join(OUT, 'early_peaks_sweep2.csv'), index=False)
    pd.set_option('display.width', 270)
    COL = ['proposer','direction','p_q','p_win','confirmer','c_q','n_fire','n_peak','n_in','n_early_in','first','last','inwindow']
    print('\ncompleted in %.1f minutes' % ((time.time() - t0) / 60))
    print('ADMISSIBLE (zero quiet firings, >=1 call inside [-92,-1]): %d' % len(D))
    if len(D):
        print('distinct NBER series producing an admissible leg: %d' % D.proposer.nunique())
        print('\n-- ranked by how many of the FOUR EARLY PEAKS they call inside the window --')
        print(D.sort_values(['n_early_in','n_in','n_peak'], ascending=False)[COL].head(25).to_string(index=False))
        for pk in sorted(EARLY):
            h = D[D.inwindow.str.contains(pk)]
            print('\n%s : %d admissible configurations, %d distinct series'
                  % (pk, len(h), h.proposer.nunique()))
            if len(h): print(h.sort_values('n_fire').head(4)[COL].to_string(index=False))
