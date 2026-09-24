#!/usr/bin/env python3
"""Re-price the admissible objects on FIRST PRINTS, dated by their actual publication day.

WHAT CHANGES FROM `price_realtime.py`. That sweep read today's file and charged each firing an assumed
publication lag -- forty days for a monthly series, a hundred and twenty for a quarterly one. Both
approximations are removed here. The value is the one first published for that observation, and the
day it fired is the day ALFRED says it appeared. Nothing is assumed about either.

This is a harder test and a smaller one. Most series' vintages begin between 1996 and 2011, so the
peaks in reach are 2001, 2007, 2020 and 2024 -- and since 2007 is the only call the rule currently
makes late, that is the era that matters. A result here is what a rule standing on the day could have
done. A result in the other sweep is an upper bound.

The scoring is unchanged: a firing within 400 days before a peak covers it, a firing covering no peak
and not inside a recession is a quiet firing, the bar is zero quiet firings and at least one lead
inside [-92, -1], and the 1965-68 credit crunch is scored like any other stretch rather than excluded
-- though no series here reaches back to it.
"""
import os, json, warnings, numpy as np, pandas as pd
warnings.filterwarnings('ignore')
_C = [os.path.expanduser('~/Projects/Onset Detector Data'), os.path.expanduser('~/mnt/Onset Detector Data')]
BASE = next((c for c in _C if os.path.isdir(os.path.join(c, '186_realtime_channels_2026-09-15'))), _C[0])
HERE = os.path.join(BASE, '186_realtime_channels_2026-09-15')
VDIR, OUT = os.path.join(HERE, 'vintages'), os.path.join(HERE, 'out')
NBER = [('1948-11','1949-10'),('1953-07','1954-05'),('1957-08','1958-04'),('1960-04','1961-02'),
        ('1969-12','1970-11'),('1973-11','1975-03'),('1980-01','1980-07'),('1981-07','1982-11'),
        ('1990-07','1991-03'),('2001-03','2001-11'),('2007-12','2009-06'),('2020-02','2020-04'),
        ('2024-04','2024-08')]
def me(y): return pd.Timestamp(y + '-01') + pd.offsets.MonthEnd(0)
PK = [me(p) for p, _ in NBER]; TR = [me(t) for _, t in NBER]
def inside(t): return any(p <= t <= r for p, r in zip(PK, TR))

def load_fp(sid):
    """Returns (value series indexed by OBSERVATION date, publication date per observation)."""
    p = os.path.join(VDIR, sid + '_firstprint.csv')
    if not os.path.exists(p): return None, None
    q = pd.read_csv(p)
    d = pd.to_datetime(q['date'], errors='coerce')
    pub = pd.to_datetime(q['published'], errors='coerce')
    v = pd.to_numeric(q['value'], errors='coerce')
    k = d.notna() & pub.notna() & v.notna()
    s = pd.Series(v[k].values, index=d[k]).sort_index()
    pb = pd.Series(pub[k].values, index=d[k]).sort_index()
    s = s[~s.index.duplicated(keep='first')]; pb = pb[~pb.index.duplicated(keep='first')]
    return s, pb

def spacing_days(s):
    if len(s) < 8: return 999
    return float(np.median(np.diff(s.index.values).astype('timedelta64[D]').astype(int)))

def build(s, sp):
    k6 = max(1, int(round(182.0 / sp))); k12 = max(1, int(round(365.0 / sp)))
    w24 = max(4, int(round(730.0 / sp)))
    out = {'level': s, 'neg': -s, 'chg6m': s.diff(k6), 'negchg6m': -s.diff(k6)}
    with np.errstate(all='ignore'):
        out['yoy'] = s.pct_change(k12) * 100; out['negyoy'] = -s.pct_change(k12) * 100
        out['gap_low'] = (s / s.rolling(w24, min_periods=max(3, w24 // 3)).min() - 1) * 100
        out['gap_high'] = (1 - s / s.rolling(w24, min_periods=max(3, w24 // 3)).max()) * 100
    return {k: v.replace([np.inf, -np.inf], np.nan).dropna() for k, v in out.items()}

def proposals(x, pb, q, win, lock=540):
    ln = x.shift(1).rolling(win, min_periods=max(6, win // 2)).quantile(q / 100.0)
    hit = (x > ln) & ln.notna()
    out, last = [], None
    for t, h in hit.items():
        if h and (last is None or (t - last).days >= lock):
            a = pb.get(t)
            if a is None or pd.isna(a): continue
            out.append((pd.Timestamp(a), t)); last = t
    return out

def score(props):
    used, leads = set(), {}
    for p in PK:
        cand = [a for a, _ in props if 0 <= (p - a).days <= 400]
        if cand:
            a = max(cand); leads[p.strftime('%Y-%m')] = (a - p).days; used.add(a)
    quiet = [a for a, _ in props if a not in used and not inside(a)]
    return len(props), len(leads), len({k: v for k, v in leads.items() if -92 <= v <= -1}), len(quiet), \
           {k: v for k, v in leads.items() if -92 <= v <= -1}, leads

rows = []
for fn in sorted(f for f in os.listdir(VDIR) if f.endswith('_firstprint.csv')):
    sid = fn[:-len('_firstprint.csv')]
    s, pb = load_fp(sid)
    if s is None or len(s) < 40: continue
    sp = spacing_days(s); n_year = max(1, int(round(365.0 / max(sp, 1))))
    covered = [p.strftime('%Y-%m') for p in PK if p >= s.index.min() and p <= s.index.max()]
    for tname, x in build(s, sp).items():
        if len(x) < 40: continue
        for q in (95, 97, 99):
            for wy in (5, 10, 20):
                w = max(10, int(round(wy * n_year)))
                if len(x) < w + 8: continue
                pr = proposals(x, pb, q, w)
                if not pr: continue
                n, nh, ni, nq, inw, leads = score(pr)
                rows.append(dict(series=sid, transform=tname, q=q, win_years=wy,
                                 fp_from=str(s.index.min().date()), peaks_in_reach=len(covered),
                                 n_fire=n, n_peak=nh, n_in=ni, n_quiet=nq,
                                 inwindow=json.dumps(inw), all_leads=json.dumps(leads)))
D = pd.DataFrame(rows)
D.to_csv(os.path.join(OUT, 'priced_firstprints.csv'), index=False)
pd.set_option('display.width', 250)
print('configurations priced on first prints: %d' % len(D))
adm = D[(D.n_quiet == 0) & (D.n_in > 0)]
print('ADMISSIBLE (zero quiet firings, >=1 lead inside [-92,-1]): %d\n' % len(adm))
COLS = ['series','transform','q','win_years','fp_from','peaks_in_reach','n_fire','n_peak','n_in','inwindow']
if len(adm):
    print(adm.sort_values(['n_in','n_peak','n_fire'], ascending=[False,False,True])[COLS].head(30).to_string(index=False))
print('\n--- configurations that call DECEMBER 2007 inside [-92,-1] with zero quiet firings ---')
h = adm[adm.inwindow.str.contains('2007-12')]
print(h[COLS].to_string(index=False) if len(h) else '   none')
