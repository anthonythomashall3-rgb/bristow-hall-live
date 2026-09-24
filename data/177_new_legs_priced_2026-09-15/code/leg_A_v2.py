#!/usr/bin/env python3
"""Leg A, rebuilt to collection 165's OWN specification rather than a generic quantile.

165's stated result, which the first attempt failed to reproduce because it used the wrong
object and the wrong line:

  "Brave-Butters-Kelley coincident index, SIX-MONTH CUMULATIVE, against the FIFTH percentile of
   its own TRAILING TEN YEARS: seven firings in sixty-six years, no false alarms, calling March
   2001 twenty-nine days early and February 2020 thirty days early."

  "Chicago Fed national activity index, LEVEL against the FIRST percentile of its TRAILING FIVE
   YEARS: seven firings, no false alarms, calling December 1969 five days early and reaching 2020
   at thirty-five days. Its three-month average reaches November 1973 at SIXTY-SIX days."

Three things differ from the first attempt and each one matters: the object is BBKMCOIX, not
CFNAIMA3; the line is a ROLLING window quantile, not an expanding one; and the firing is on the
LOW side of the raw series, not the high side of its negation with an expanding line.

Lags charged as 165 states them: 60 days for the Brave-Butters-Kelley family, 55 for the national
activity index. Eighteen-month lockout, as 165 used.
"""
import os, numpy as np, pandas as pd, warnings
warnings.filterwarnings('ignore')
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA, OUT = os.path.join(HERE, 'data'), os.path.join(HERE, 'out')

def rd(sid):
    d = pd.read_csv(os.path.join(DATA, sid + '.csv')); c = list(d.columns)
    s = pd.Series(pd.to_numeric(d[c[1]], errors='coerce').values,
                  index=pd.to_datetime(d[c[0]], errors='coerce'))
    return s[~s.index.isna()].dropna().sort_index()

def fires_low(x, q_pct, win_months, lag_days, lockout_months=18):
    """Fire when x falls below the q-th percentile of its own trailing window, shifted."""
    line = x.shift(1).rolling(win_months, min_periods=max(24, win_months // 2)).quantile(q_pct / 100.0)
    hit = (x < line) & line.notna()
    out, last = [], None
    for t in x.index[hit]:
        if last is not None and (t - last).days < lockout_months * 30:
            continue
        out.append((t, t + pd.Timedelta(days=lag_days))); last = t
    return out

CAND = [
    ('BBKMCOIX_cum6', lambda: rd('BBKMCOIX').rolling(6).sum(), [5, 10], [120], 60),
    ('BBKMCOIX_level', lambda: rd('BBKMCOIX'),                 [1, 5],  [60, 120], 60),
    ('BBKMLEIX_cum6', lambda: rd('BBKMLEIX').rolling(6).sum(), [5, 10], [120], 60),
    ('CFNAI_level',   lambda: rd('CFNAI'),                      [1, 5],  [60], 55),
    ('CFNAIMA3_level',lambda: rd('CFNAIMA3'),                   [1, 5],  [60, 120], 55),
]
PEAKS = ['1948-11','1953-07','1957-08','1960-04','1969-12','1973-11','1980-01',
         '1981-07','1990-07','2001-03','2007-12','2020-02','2024-04']
TROUGHS = ['1949-10','1954-05','1958-04','1961-02','1970-11','1975-03','1980-07',
           '1982-11','1991-03','2001-11','2009-06','2020-04','2024-09']
def me(ym): return pd.Timestamp(ym+'-01') + pd.offsets.MonthEnd(0)
PK = [me(p) for p in PEAKS]
TR = [me(t) for t in TROUGHS]
def inside(t):
    # A firing while a recession is already under way is NEITHER a call NOR a false alarm:
    # the rule would be open and would not be listening. Scoring it as a false alarm was a
    # defect in the first pass and is what made collection 165's result look unreproducible.
    return any(p <= t <= tr for p, tr in zip(PK, TR))

rows = []
for name, fn, qs, wins, lag in CAND:
    x = fn().dropna()
    for q in qs:
        for w in wins:
            f = fires_low(x, q, w, lag)
            pubs = [p for _, p in f]
            hits, used = {}, set()
            for pk in PK:
                c = [t for t in pubs if 0 <= (pk - t).days <= 400]
                if c:
                    t = c[-1]; hits[pk.strftime('%Y-%m')] = (t - pk).days; used.add(t)
            inw = {k: v for k, v in hits.items() if -92 <= v <= -1}
            quiet = [t for t in pubs if t not in used and not inside(t)]
            rows.append(dict(object=name, q=q, win_m=w, n_fire=len(pubs), n_hit=len(hits),
                             n_in=len(inw), n_quiet=len(quiet), inwindow=str(inw),
                             quiet=';'.join(str(t.date()) for t in quiet[:6])))
            print('%-16s q=%-3d win=%-4d fires=%-3d hits=%-2d IN=%-2d quiet=%-2d %s'
                  % (name, q, w, len(pubs), len(hits), len(inw), len(quiet), inw))
d = pd.DataFrame(rows); d.to_csv(os.path.join(OUT, 'leg_A_v2_pricing.csv'), index=False)
print('\n=== zero quiet firings, ranked by in-window hits ===')
z = d[d.n_quiet == 0].sort_values(['n_in','n_hit'], ascending=False)
print(z[['object','q','win_m','n_fire','n_hit','n_in','inwindow']].to_string(index=False) if len(z) else 'none')
