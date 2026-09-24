#!/usr/bin/env python3
"""Price every series in this collection as an armed leg, on one standard, with no hand-picking.

THE STANDARD, fixed before the sweep and applied to all of them. An object is a series put through
one declared transform. Its line is a rolling quantile of its own trailing window, so the line moves
with the series and never needs a hand-set level. It fires when it crosses the line, and is then
locked out for 540 days so that one episode counts once. Each firing is charged the days it takes for
that observation to be public: one day for a market price, twelve for a weekly release, forty for a
monthly one, a hundred and twenty for a quarterly one -- inferred from the spacing of the series
itself, never assumed.

A firing is scored against the NBER peaks. A firing within four hundred days before a peak COVERS it;
its lead is the days from the firing to the peak month's last day. A firing that covers no peak and
does not fall inside a recession is a QUIET FIRING -- what the programme elsewhere calls a false
alarm. The bar to be admissible is zero quiet firings and at least one lead inside [-92, -1].

WHAT REVISION DOES TO THIS, stated because it decides which results may be used. A series that is
revised after first publication cannot be read this way without look-ahead: today's file says what
the number became, not what it said at the time. Market prices -- yields, spreads, the oil price, the
volatility index, the mortgage rate -- are never revised, and the news-based uncertainty index is
never revised. Everything else here is revised, and its result below is an upper bound on what a
real-time rule could have done, not a measurement of it. The column `revised` records which is which,
and nothing marked revised may enter a walk without its vintages.
"""
import os, json, itertools, warnings, numpy as np, pandas as pd
warnings.filterwarnings('ignore')
_C = [os.path.expanduser('~/Projects/Onset Detector Data'), os.path.expanduser('~/mnt/Onset Detector Data')]
BASE = next((c for c in _C if os.path.isdir(os.path.join(c, '186_realtime_channels_2026-09-15'))), _C[0])
HERE = os.path.join(BASE, '186_realtime_channels_2026-09-15')
DATA, OUT = os.path.join(HERE, 'data'), os.path.join(HERE, 'out')
os.makedirs(OUT, exist_ok=True)

NBER = [('1948-11','1949-10'),('1953-07','1954-05'),('1957-08','1958-04'),('1960-04','1961-02'),
        ('1969-12','1970-11'),('1973-11','1975-03'),('1980-01','1980-07'),('1981-07','1982-11'),
        ('1990-07','1991-03'),('2001-03','2001-11'),('2007-12','2009-06'),('2020-02','2020-04'),
        ('2024-04','2024-08')]
def me(y): return pd.Timestamp(y + '-01') + pd.offsets.MonthEnd(0)
PK = [me(p) for p, _ in NBER]; TR = [me(t) for _, t in NBER]
def inside(t): return any(p <= t <= r for p, r in zip(PK, TR))

# The 1966 credit crunch. Scored, never excluded: a firing here is a quiet firing like any other, and
# the rule is required to stay silent through it rather than have it removed from the test.
CRUNCH = (pd.Timestamp('1965-07-01'), pd.Timestamp('1968-06-30'))

# Never revised after first publication. Everything not listed is treated as revised.
NEVER_REVISED = {
 'DGS1','DGS2','DGS10','DGS30','DGS3MO','DTB3','DTB6','DPRIME','DFF','DAAA','DBAA','T10Y2Y','T10Y3M',
 'SOFR','EFFR','OBFR','MORTGAGE30US','MORTGAGE15US','VIXCLS','SP500','DJIA','NASDAQCOM','DTWEXBGS',
 'DTWEXAFEGS','DEXCAUS','BAMLH0A0HYM2','BAMLC0A0CM','BAMLH0A3HYC','TEDRATE','DCOILWTICO',
 'DCOILBRENTEU','DHHNGSP','GASREGW','USEPUINDXD','RRPONTSYD','WTISPLC'}

def rd(p):
    q = pd.read_csv(p); c = list(q.columns)
    s = pd.Series(pd.to_numeric(q[c[1]], errors='coerce').values,
                  index=pd.to_datetime(q[c[0]], errors='coerce')).dropna().sort_index()
    return s[~s.index.duplicated(keep='last')]

def spacing_days(s):
    if len(s) < 8: return 999
    return float(np.median(np.diff(s.index.values).astype('timedelta64[D]').astype(int)))

def lag_for(sp):
    if sp <= 3:   return 1, 'daily'
    if sp <= 10:  return 12, 'weekly'
    if sp <= 45:  return 40, 'monthly'
    return 120, 'quarterly'

def per_year(sp):
    return max(1, int(round(365.0 / max(sp, 1))))

TRANSFORMS = {
 'level'   : lambda s: s,
 'neg'     : lambda s: -s,
 'chg6m'   : None,   # filled per-series using its own frequency
 'negchg6m': None,
 'yoy'     : None,
 'negyoy'  : None,
 'gap_low' : None,   # gap above its own trailing two-year low, in per cent
 'gap_high': None,   # gap below its own trailing two-year high, in per cent
}

def build(s, name, sp):
    k6 = max(1, int(round(182.0 / sp)))       # six months of this series' own steps
    k12 = max(1, int(round(365.0 / sp)))      # twelve months
    w24 = max(4, int(round(730.0 / sp)))      # a two-year window in steps
    out = {'level': s, 'neg': -s}
    out['chg6m'] = s.diff(k6); out['negchg6m'] = -s.diff(k6)
    with np.errstate(all='ignore'):
        out['yoy'] = s.pct_change(k12) * 100; out['negyoy'] = -s.pct_change(k12) * 100
        lo = s.rolling(w24, min_periods=max(3, w24 // 3)).min()
        hi = s.rolling(w24, min_periods=max(3, w24 // 3)).max()
        out['gap_low'] = (s / lo - 1) * 100
        out['gap_high'] = (1 - s / hi) * 100
    return {k: v.replace([np.inf, -np.inf], np.nan).dropna() for k, v in out.items()}

def proposals(x, q, win_steps, lagd, lock=540):
    ln = x.shift(1).rolling(win_steps, min_periods=max(8, win_steps // 2)).quantile(q / 100.0)
    hit = (x > ln) & ln.notna()
    out, last = [], None
    for t, h in hit.items():
        if h and (last is None or (t - last).days >= lock):
            out.append((t + pd.Timedelta(days=lagd), t)); last = t
    return out

def score(props):
    used, leads = set(), {}
    for i, p in enumerate(PK):
        cand = [a for a, _ in props if 0 <= (p - a).days <= 400]
        if cand:
            a = max(cand); leads[p.strftime('%Y-%m')] = (a - p).days; used.add(a)
    quiet = [a for a, _ in props if a not in used and not inside(a)]
    crunch = [a for a in quiet if CRUNCH[0] <= a <= CRUNCH[1]]
    inw = {k: v for k, v in leads.items() if -92 <= v <= -1}
    return len(props), len(leads), len(inw), len(quiet), len(crunch), inw

rows = []
files = sorted(f for f in os.listdir(DATA) if f.endswith('.csv'))
for fn in files:
    sid = fn[:-4]
    try:
        s = rd(os.path.join(DATA, fn))
    except Exception:
        continue
    if len(s) < 60: continue
    sp = spacing_days(s); lagd, freq = lag_for(sp)
    objs = build(s, sid, sp)
    n_year = per_year(sp)
    for tname, x in objs.items():
        if len(x) < 60: continue
        for q in (95, 97, 99):
            for win_years in (5, 10, 20):
                w = max(12, int(round(win_years * n_year)))
                if len(x) < w + 12: continue
                pr = proposals(x, q, w, lagd)
                if not pr: continue
                n, nh, ni, nq, nc, inw = score(pr)
                rows.append(dict(series=sid, transform=tname, q=q, win_years=win_years, freq=freq,
                                 lag_days=lagd, revised=(sid not in NEVER_REVISED),
                                 n_fire=n, n_peak=nh, n_in=ni, n_quiet=nq, n_crunch=nc,
                                 first=str(x.index.min().date()), last=str(x.index.max().date()),
                                 inwindow=json.dumps(inw)))
D = pd.DataFrame(rows)
D.to_csv(os.path.join(OUT, 'priced_realtime.csv'), index=False)
pd.set_option('display.width', 260)
print('series read: %d   configurations priced: %d' % (len(files), len(D)))
adm = D[(D.n_quiet == 0) & (D.n_in > 0)]
print('\nADMISSIBLE  (zero quiet firings, at least one lead inside [-92,-1]): %d' % len(adm))
COLS = ['series','transform','q','win_years','freq','revised','n_fire','n_peak','n_in','first','inwindow']
if len(adm):
    print('\n-- never revised (usable in a causal walk) --')
    a = adm[~adm.revised].sort_values(['n_in','n_peak'], ascending=False)
    print(a[COLS].head(25).to_string(index=False) if len(a) else '   none')
    print('\n-- revised (upper bound only, needs vintages before use) --')
    b = adm[adm.revised].sort_values(['n_in','n_peak'], ascending=False)
    print(b[COLS].head(25).to_string(index=False) if len(b) else '   none')
print('\nany configuration firing in the 1966 credit crunch is counted, never excluded:')
print('  configurations with a crunch firing: %d of %d' % (int((D.n_crunch > 0).sum()), len(D)))
