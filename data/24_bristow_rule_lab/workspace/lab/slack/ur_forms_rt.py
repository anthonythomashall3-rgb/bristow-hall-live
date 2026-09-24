"""The unemployment-rate gap in real time: which form, and how low a line the 1951 and 1967 episodes
allow (3 September 2026).

Forms: k-month mean of the rate less the minimum of that mean over the previous `back` months
(k = 1, 2, 3; back = 6, 12; Sahm's is k = 3, back = 12).  The rate is read as first published where
ALFRED holds vintages (UNRATE vintages from March 1960; `lab/rt/vint`), the current vintage before.
For each form: the maximum reading inside the 1951 episode (current vintage - no vintages exist) and
inside the 1967 episode (first prints), the line just above both, and at that line the crossing month
of each of the twelve committee recessions relative to the peak month (first prints from 1960,
current vintage before), the 2023-24 crossing, and the object's own firings outside recession windows.
Output lab/slack/ur_forms_rt.log.
"""
import sys; sys.path.insert(0, '/home/claude/lab/rt'); sys.path.insert(0, '/home/claude/lab/slack')
import numpy as np, pandas as pd, alfred
from objects import load
from bound import PEAKS, TROUGHS, M, months

cur = load()['UR']
fp = alfred.first_prints('UNRATE')
# splice: current vintage before the first vintage, first prints after
rt = pd.concat([cur[cur.index < fp.index.min()], fp]).sort_index()

def form(s, k, back):
    m = s.rolling(k).mean()
    return (m - m.shift(1).rolling(back).min()).dropna()

def alone(g, line):
    on = False; out = []
    for t, v in g.items():
        if v >= line and not on:
            inside = any(M(p) - pd.DateOffset(months=6) <= t <= M(q) + pd.DateOffset(months=6) for p, q in zip(PEAKS, TROUGHS)) or (M('2023-06') <= t <= M('2026-06'))
            if not inside: out.append(t.strftime('%Y-%m'))
            on = True
        elif v < line: on = False
    return out

print('UR gap, first prints from 1960 (current vintage before); the 1951 window is current vintage, the 1967 window first prints')
print('k back   max1951 max1967(rt)  line   lags after the peak month (twelve)             <=0  <=1  median worst  2024 crossing  alone firings')
for k in (1, 2, 3):
    for back in (6, 12):
        g = form(rt, k, back)
        m51 = float(g['1951-06':'1952-08'].max()); m67 = float(g['1967-01':'1968-03'].max())
        line = max(m51, m67) + 1e-9
        lags = []
        for p in PEAKS:
            seg = g[M(p) - pd.DateOffset(months=3): M(p) + pd.DateOffset(months=12)]
            hit = seg[seg >= line]; lags.append(None if hit.empty else months(hit.index[0], M(p)))
        seg = g['2023-06':'2025-06']; hit = seg[seg >= line]; t24 = None if hit.empty else hit.index[0].strftime('%Y-%m')
        cov = [l for l in lags if l is not None]
        print(f'{k} {back:3d}    {m51:5.2f}   {m67:5.2f}      {line:5.3f}  ' + ' '.join(f'{l:>3d}' if l is not None else '  -' for l in lags) +
              f'   {sum(1 for l in cov if l <= 0):2d}   {sum(1 for l in cov if l <= 1):2d}   {np.median(cov):4.1f}  {max(cov):3d}    {t24 or "never":10s}  {alone(g, line)}')
# Sahm's own line for reference
g = form(rt, 3, 12)
lags = []
for p in PEAKS:
    seg = g[M(p) - pd.DateOffset(months=3): M(p) + pd.DateOffset(months=12)]; hit = seg[seg >= 0.5]; lags.append(None if hit.empty else months(hit.index[0], M(p)))
seg = g['2023-06':'2025-06']; hit = seg[seg >= 0.5]
print(f"Sahm's form at her line 0.5:  lags {lags}  median {np.median(lags):.1f} worst {max(lags)}  2024 crossing {hit.index[0]:%Y-%m}  alone {alone(g, 0.5)}")
print('first prints, 1967: ' + ', '.join(f'{t:%Y-%m} {v:.1f}' for t, v in fp['1967-05':'1967-12'].items()))
