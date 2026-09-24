"""The states' unemployment rates as a breadth object (3 September 2026).

Each state's rate gets Sahm's gap (three-month mean less its minimum over the previous twelve
months); the object is the share of states whose gap stands at or above a state line (0.5, Sahm's;
also 0.3).  Current vintage 1976 on (44 FRED state files plus seven rebuilt from LAUS counts);
first prints 1994 on from the BLS state releases the Mac holds (median publication 50 days after the
reference month begins - about the 20th of the month after).  For lines 20-40 per cent: crossing
month relative to the committee peak for the six recessions since 1976 and for 2023-24, the
object's own firings outside recession windows, and the same read on first prints where they exist.
Output lab/slack/state_breadth.log.
"""
import sys; sys.path.insert(0, '/home/claude/lab/slack')
import numpy as np, pandas as pd
from objects import state_ur, sahm
from bound import PEAKS, TROUGHS, M, months

SU = state_ur()
def breadth(df, state_line=0.5):
    G = df.apply(lambda c: sahm(c.dropna(), 3, 12))
    return ((G >= state_line).sum(axis=1) / G.notna().sum(axis=1) * 100).dropna()

def first_prints():
    d = pd.read_csv('/home/claude/lab/cps/21_vintage_realtime/monthly/bls_laus_first_prints/state_ur_first_prints_refmonth_fixed.csv')
    d['obs_period'] = pd.to_datetime(d['obs_period'])
    w = d.pivot_table(index='obs_period', columns='geo_code', values='value', aggfunc='first')
    w = w[[c for c in w.columns if c not in ('PR', 'DC') or c == 'DC']]
    return w.sort_index()

def alone(g, line, since='1977-01'):
    on = False; out = []
    for t, v in g[since:].items():
        if v >= line and not on:
            inside = any(M(p) - pd.DateOffset(months=6) <= t <= M(q) + pd.DateOffset(months=6) for p, q in zip(PEAKS, TROUGHS)) or (M('2023-06') <= t <= M('2026-06'))
            if not inside: out.append(t.strftime('%Y-%m'))
            on = True
        elif v < line: on = False
    return out

def report(B, label, peaks):
    print(f'\n{label}: share of states with Sahm gap >= 0.5')
    print('line   crossings relative to the peak month ' + ' '.join(f'{p:>8s}' for p in peaks) + '   2023-24    own firings outside recessions')
    for line in (15, 20, 25, 30, 35, 40, 50):
        lags = []
        for p in peaks:
            seg = B[M(p) - pd.DateOffset(months=3): M(p) + pd.DateOffset(months=12)]; hit = seg[seg >= line]
            lags.append('   -' if hit.empty else f'{months(hit.index[0], M(p)):+4d}')
        seg = B['2023-06':'2025-06']; hit = seg[seg >= line]; t24 = 'never' if hit.empty else hit.index[0].strftime('%Y-%m')
        print(f'{line:3d}%   ' + ' '.join(f'{l:>8s}' for l in lags) + f'   {t24:8s}   {alone(B, line, since=B.index.min().strftime("%Y-%m"))}')

if __name__ == '__main__':
    B = breadth(SU, 0.5)
    print(f'states {SU.shape[1]}, {SU.index.min():%Y-%m} to {SU.index.max():%Y-%m}; breadth series from {B.index.min():%Y-%m}')
    report(B, 'CURRENT VINTAGE', [p for p in PEAKS if p >= '1978'])
    B3 = breadth(SU, 0.3)
    print('\nstate line 0.3 instead of 0.5:')
    report(B3, 'CURRENT VINTAGE, state gap >= 0.3', [p for p in PEAKS if p >= '1978'])
    print('\nmonthly path of the 0.5-breadth (per cent), 2023-06 to 2024-12:', [int(round(v)) for v in B['2023-06':'2024-12']])
    print('monthly path 1979-06 to 1980-06:', [int(round(v)) for v in B['1979-06':'1980-06']])
    print('monthly path 1981-01 to 1981-12:', [int(round(v)) for v in B['1981-01':'1981-12']])
    print('monthly path 1990-03 to 1991-03:', [int(round(v)) for v in B['1990-03':'1991-03']])
    print('monthly path 2000-10 to 2001-10:', [int(round(v)) for v in B['2000-10':'2001-10']])
    print('monthly path 2007-09 to 2008-09:', [int(round(v)) for v in B['2007-09':'2008-09']])
    FP = first_prints()
    print(f'\nfirst prints: {FP.shape[1]} jurisdictions, {FP.index.min():%Y-%m} to {FP.index.max():%Y-%m}; gap needs 15 months of prints, so the breadth begins {(FP.index.min() + pd.DateOffset(months=15)):%Y-%m}')
    BF = breadth(FP, 0.5)
    report(BF, 'FIRST PRINTS (1994 on)', [p for p in PEAKS if p >= '1996'])
    print('\nfirst-print path 2023-06 to 2024-12:', [int(round(v)) for v in BF['2023-06':'2024-12']])
    print('first-print path 2007-09 to 2008-09:', [int(round(v)) for v in BF['2007-09':'2008-09']])
    print('first-print path 2000-10 to 2001-10:', [int(round(v)) for v in BF['2000-10':'2001-10']])
    print('first-print path 2020-01 to 2020-06:', [int(round(v)) for v in BF['2020-01':'2020-06']])
    # the breadth against the national gap: the same rise read at a lower line?
    from objects import load
    nat = sahm(load()['UR'], 3, 12)
    df = pd.concat([nat.rename('nat'), B.rename('breadth')], axis=1).dropna()['1977-03':]
    print('\n--- the breadth against the national gap (current vintage, 1977-2026): the same rise read at a lower line?')
    for lo, hi in ((0.0, 0.1), (0.1, 0.2), (0.2, 0.3), (0.3, 0.4), (0.4, 0.5), (0.5, 0.7), (0.7, 1.0)):
        s = df[(df.nat >= lo) & (df.nat < hi)]
        if len(s): print(f'  national gap in [{lo:.1f},{hi:.1f}): {len(s):3d} months, breadth median {s.breadth.median():4.0f}%, min {s.breadth.min():3.0f}, max {s.breadth.max():3.0f}; share of months at or above 30%: {(s.breadth >= 30).mean() * 100:3.0f}%')
    print('  first month the breadth reaches 30% in each episode, and the national gap that month:')
    for p in ('1979-10', '1981-04', '1990-04', '2000-12', '2007-09', '2019-11', '2023-06'):
        seg = df[p:]; hit = seg[seg.breadth >= 30]
        if not hit.empty: t = hit.index[0]; print(f'    {t:%Y-%m}: breadth {hit.breadth.iloc[0]:.0f}%, national gap {hit.nat.iloc[0]:.2f}')
    print('  months since 1977 with breadth >= 30% while the national gap < 0.5:', int(((df.breadth >= 30) & (df.nat < 0.5)).sum()), 'of', int((df.breadth >= 30).sum()))
