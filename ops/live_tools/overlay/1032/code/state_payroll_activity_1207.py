#!/usr/bin/env python3
"""1207 (PREREG-1207; Anthony 27 Nov 2026 13:23 PT: 'yes' to the payroll rule at 1.0 percent, three-month average). No AI.
THE STATE CLASS RULE READS PAYROLLS AS WELL AS THE STATE INDEX. The rule of 1167 asks the State activity index (Philadelphia Fed) to
fall 1.0 percent before a window can be a recession; that index barely falls where jobs fell hard (North Dakota 2014-16: payrolls 8.0
percent, index 0.74; California 1990-92: 4.0 and 0.69; RECORD-1205). Where the index fell under 1.0 percent, the window's payrolls are
read the same way; a fall of PAY_MIN percent or more grades the window on the months payrolls fell.
Used by state_chronology_v4_growth_cycle_a198_1032.py and by the stress map's State layer (stress_map_v3_1_1052.py run_v4), so the two stay one file."""
import os, numpy as np, pandas as pd
PAY_MIN = 1.0
def sa_log(x):   # the stress map's own seasonal adjustment (stress_map_v3_1_1052.py), copied
    x = x.astype(float); T = x.rolling(12, center=True).mean().rolling(2).mean().shift(-1); r = x - T
    S = pd.Series(np.nan, index=x.index)
    for mo in range(1, 13):
        k = x.index.month == mo; s = r[k].rolling(7, center=True, min_periods=3).mean(); S[k] = s.ffill().bfill().values
    S = S - S.rolling(12, center=True).mean().rolling(2).mean().shift(-1).ffill().bfill()
    return x - S
def _read(f):
    u = pd.read_csv(f); return pd.Series(pd.to_numeric(u.iloc[:, 1], errors='coerce').values, index=pd.to_datetime(u.iloc[:, 0])).dropna()
def series(st, sa_dir, nsa_dir):
    """official seasonally adjusted payrolls from 1990; before that the unadjusted series of 1970-1995 adjusted with sa_log and set to the official 1990 mean; trailing three-month average"""
    sa = _read(os.path.join(sa_dir, f'{st}NA.csv')); sa = sa[sa.index >= '1990-01-01']; assert sa.index[0] == pd.Timestamp('1990-01-01'), (st, sa.index[0])
    n = _read(os.path.join(nsa_dir, f'{st}NAN.csv')); n = n[(n.index >= '1970-01-01') & (n.index <= '1995-12-01')]; assert len(n) == 312, (st, len(n))
    a = np.exp(sa_log(np.log(n))); a = a * float(sa['1990-01-01':'1990-12-01'].mean() / a['1990-01-01':'1990-12-01'].mean())
    return pd.concat([a[a.index < '1990-01-01'], sa]).rolling(3).mean().dropna()
def fall(w, p, te, last, lo=None, hi=None):
    """(high month, low month, percent): the largest fall of w from a high in [p - 6 months, te] to the lowest level after it (to te + 6 months), the margins stopping at the neighbouring windows (lo, hi)"""
    a = p - pd.DateOffset(months=6); b = min(te + pd.DateOffset(months=6), last)
    if lo is not None: a = max(a, lo + pd.DateOffset(months=1))
    if hi is not None: b = min(b, hi - pd.DateOffset(months=1))
    s = w[(w.index >= a) & (w.index <= max(b, te))]
    if len(s) < 2 or not (s.index <= te).any(): return None
    dd_ = 1 - s / s.where(s.index <= te).cummax().ffill(); tl = dd_.idxmax(); pl = s[:tl].idxmax()
    return pl, tl, float(100 * dd_.max())
