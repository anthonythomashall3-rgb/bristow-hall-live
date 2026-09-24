#!/usr/bin/env python3
"""The frozen channel screen, run on Canada. The same method, a different country, nothing refitted.

WHAT THIS TESTS. The American screen asks, of every channel held, whether some (proposer, confirmer)
conjunction fires early at recessions and stays quiet otherwise. That question is about the METHOD, not
about the particular American series that happened to answer it, and a method that only works in the
country it was built in is a fitted method. Canada is the peer: an advanced economy with an
independent, published recession chronology (the C.D. Howe Business Cycle Council, 2021 vintage) and,
now, 1,127 collected series reaching back to 1914.

THE GRID IS THE AMERICAN ONE, UNCHANGED. Same directions, same proposer quantiles (95, 97), same
windows (10, 20 years), same holds (180, 270 days), same confirmer quantiles (90, 95), same
[-92, -1] day window, same nine-month re-arming, same bar: zero quiet firings and at least one call
inside the window. Nothing here is tuned to Canada. If Canadian channels clear an American bar, the
architecture travels; if they do not, it does not, and that is the finding.

TWO THINGS THIS FILE REFUSES TO HIDE.
1. REACHABILITY. Canada's chronology has twelve peaks, but only CPI reaches 1929 and 1937, and a
   ten-year quantile line cannot exist before a series' eleventh year. The American early-peaks sweep
   returned zeros for 1948, 1953 and 1957 and the zeros were an artefact of exactly this. So the
   screen computes, for every peak, how many candidate channels could have had a line at all, and
   reports it beside the hit counts. A peak no channel can reach is reported as unreachable, never as
   a miss.
2. THE 1980 DISPUTE. Cross and Bergevin (2012) dated a Canadian recession January-June 1980. The
   Business Cycle Council's 2021 chronology REMOVED it. This screen scores against the Council's
   chronology, so a firing in 1980 counts as a quiet firing -- against the channel. The count of
   firings landing in the disputed window is reported separately so the cost of that choice is
   visible rather than buried.
"""
import os, re, sys, json, itertools, warnings, numpy as np, pandas as pd
import multiprocessing as mp
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fastscreen import hold_np, episodes_np, daily_np
warnings.filterwarnings('ignore')

CA = os.environ.get('CA_DATA', '/mnt/user-data/outputs/ca')
FOLDERS = [CA] + [p for p in [os.environ.get('CA_DATA2', ''), os.environ.get('CA_DATA3', '')] if p and os.path.isdir(p)]
OUT = os.environ.get('CA_OUT', '/mnt/user-data/outputs/ca_out')
os.makedirs(OUT, exist_ok=True)
LEAK = re.compile(r'^(CANREC|.*RECD[MPQ]$|USREC|RECPRO)', re.I)

# C.D. Howe Business Cycle Council (2021). Peaks and troughs, monthly.
BCC = [('1929-04', '1933-02'), ('1937-11', '1938-06'), ('1947-08', '1948-03'), ('1951-04', '1951-12'),
       ('1953-07', '1954-07'), ('1957-03', '1958-01'), ('1960-03', '1961-03'), ('1974-10', '1975-03'),
       ('1981-06', '1982-10'), ('1990-03', '1992-05'), ('2008-10', '2009-05'), ('2020-02', '2020-04')]
DISPUTED = (pd.Timestamp('1980-01-01'), pd.Timestamp('1980-06-30'))   # Cross-Bergevin, removed by the Council
def me(y): return pd.Timestamp(y + '-01') + pd.offsets.MonthEnd(0)
PK = [me(p) for p, _ in BCC]; TR = [me(t) for _, t in BCC]
def inside(t): return any(p <= t <= r for p, r in zip(PK, TR))
IDX = pd.date_range('1919-01-31', '2026-09-30', freq='D')

def rd_any(sid):
    for f in FOLDERS:
        p = os.path.join(f, sid + '.csv')
        if not os.path.exists(p): continue
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
def spacing(s):
    return float(np.median(np.diff(s.index.values).astype('timedelta64[D]').astype(int))) if len(s) > 8 else 30.0
def lag_for(sp): return 1 if sp <= 3 else (12 if sp <= 10 else (40 if sp <= 45 else 120))
def as_of(sid, fn):
    s = rd_any(sid)
    if s is None or len(s) < 60: return None, None
    sp = spacing(s); k = max(1, int(round(182.0 / max(sp, 1))))
    x = fn(s, k).replace([np.inf, -np.inf], np.nan).dropna()
    if len(x) < 60: return None, None
    x.index = x.index + pd.Timedelta(days=lag_for(sp))
    return x, max(1, int(round(365.0 / max(sp, 1))))
def over_q(x, q, win):
    ln = x.shift(1).rolling(win, min_periods=max(10, win // 2)).quantile(q / 100.0)
    return (x > ln) & ln.notna()
def episodes(fire): return list(IDX[episodes_np(fire, 9)])
def score(calls):
    used, leads = set(), {}
    for p in PK:
        c = [t for t in calls if 0 <= (p - t).days <= 400]
        if c: t = max(c); leads[p.strftime('%Y-%m')] = (t - p).days; used.add(t)
    quiet = [t for t in calls if t not in used and not inside(t)]
    disp = [t for t in quiet if DISPUTED[0] <= t <= DISPUTED[1]]
    inwin = {k: v for k, v in leads.items() if -92 <= v <= -1}
    return (len(calls), len(leads), len(inwin), len(quiet), len(disp),
            json.dumps(inwin), json.dumps(leads))

DIRS = {'rise6m': lambda s, k: s.diff(k), 'fall6m': lambda s, k: -s.diff(k),
        'yoy_up': lambda s, k: s.pct_change(2 * k) * 100, 'yoy_down': lambda s, k: -s.pct_change(2 * k) * 100}
# Canadian confirmers, chosen for REACH rather than for fit: the earliest-starting object in each of
# the causally distinct families the American screen confirms with. Claims 1943, permits and starts
# 1948, electric power sales 1949, rail 1946, industrial production 1961, unemployment 1960s.
CONFS = {
 'claims_rising':    ('CA14100005_INITIAL_CLAIMS_RECEIVED', lambda s, k: s.pct_change(k) * 100),
 'starts_falling':   ('CA34100143_HOUSING_STARTS_TOTAL_UNITS', lambda s, k: -s.pct_change(2 * k) * 100),
 'permits_falling':  ('CA34100008_SEASONALLY_ADJUSTED_TOTAL_RESIDENTIAL_AND_NON_', lambda s, k: -s.pct_change(2 * k) * 100),
 'power_falling':    ('CA25100033_TOTAL_SALES', lambda s, k: -s.pct_change(2 * k) * 100),
 'ip_falling':       ('CANPROINDMISMEI', lambda s, k: -s.pct_change(k) * 100),
 'unrate_rising':    ('LRHUTTTTCAM156S', lambda s, k: s.diff(k)),
 'covered_falling':  ('CA14100006_PERSONS_COVERED_BY_EMPLOYMENT_INSURANCE', lambda s, k: -s.pct_change(2 * k) * 100),
 'completions_falling': ('CA34100143_HOUSING_COMPLETIONS_TOTAL_UNITS', lambda s, k: -s.pct_change(2 * k) * 100),
}
CB = None
def init():
    global CB
    CB = {}
    for cn, (sid, fn) in CONFS.items():
        x, ny = as_of(sid, fn)
        if x is None: continue
        for cq in (90, 95):
            b = over_q(x, cq, max(12, int(10 * ny)))
            CB[(cn, cq, 10)] = hold_np(daily_np(b, IDX), 270)
def one(sid):
    out = []
    for dname, dfn in DIRS.items():
        x, ny = as_of(sid, dfn)
        if x is None: continue
        for pq, pwy, phold in itertools.product((95, 97), (10, 20), (180, 270)):
            Pb = hold_np(daily_np(over_q(x, pq, max(12, int(pwy * ny))), IDX), phold)
            for (cn, cq, cwy), Cb in CB.items():
                n, nh, ni, nq, nd, iw, al = score(episodes(Pb & Cb))
                if nq == 0 and ni > 0:
                    out.append(dict(proposer=sid, direction=dname, p_q=pq, p_win=pwy, p_hold=phold,
                                    confirmer=cn, c_q=cq, c_win=cwy, n_fire=n, n_peak=nh, n_in=ni,
                                    n_quiet=nq, n_disputed1980=nd, inwindow=iw, all_leads=al))
    return out

def reachability():
    """For each peak, how many candidate channels could have had a quantile line by then at all."""
    rows = []
    for p in PK:
        n10 = n20 = 0
        for sid in CAND:
            s = rd_any(sid)
            if s is None or len(s) < 60: continue
            st = s.index.min()
            if st + pd.DateOffset(years=10) <= p: n10 += 1
            if st + pd.DateOffset(years=20) <= p: n20 += 1
        rows.append((p.strftime('%Y-%m'), n10, n20))
    return rows

CAND = []
if __name__ == '__main__':
    import time
    conf_ids = {v[0] for v in CONFS.values()}
    seen = set()
    for f in FOLDERS:
        if not os.path.isdir(f): continue
        for fn_ in sorted(os.listdir(f)):
            if not fn_.endswith('.csv') or fn_.startswith('MANIFEST'): continue
            sid = fn_[:-4]
            if sid in seen or sid in conf_ids or LEAK.match(sid): continue
            seen.add(sid); CAND.append(sid)
    ncpu = max(1, (os.cpu_count() or 2))
    print('Canadian candidate channels %d, workers %d' % (len(CAND), ncpu), flush=True)
    init()
    print('confirmers with a usable line: %d of %d' % (len({k[0] for k in CB}), len(CONFS)), flush=True)
    t0 = time.time(); rows = []
    with mp.Pool(ncpu, initializer=init) as pool:
        for i, res in enumerate(pool.imap_unordered(one, CAND, chunksize=8)):
            rows += res
            if (i + 1) % 200 == 0:
                print('  %d/%d, %d admissible, %.1f min' % (i + 1, len(CAND), len(rows),
                                                            (time.time() - t0) / 60), flush=True)
    D = pd.DataFrame(rows)
    if len(D): D = D.sort_values(['proposer', 'direction', 'p_q', 'p_win', 'p_hold', 'confirmer', 'c_q']).reset_index(drop=True)
    D.to_csv(os.path.join(OUT, 'canada_screen.csv'), index=False)
    print('\ncompleted in %.1f minutes' % ((time.time() - t0) / 60))
    print('ADMISSIBLE leg configurations: %d over %d distinct channels'
          % (len(D), D.proposer.nunique() if len(D) else 0))
    R = pd.DataFrame(reachability(), columns=['peak', 'channels_with_10y_history', 'channels_with_20y_history'])
    cov = {}
    for s in (D.inwindow if len(D) else []):
        for k in json.loads(s): cov[k] = cov.get(k, 0) + 1
    R['admissible_configs_hitting'] = R.peak.map(lambda p: cov.get(p, 0))
    R.to_csv(os.path.join(OUT, 'canada_reachability.csv'), index=False)
    print('\n' + R.to_string(index=False))
