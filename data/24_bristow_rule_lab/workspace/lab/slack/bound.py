"""The separation bound, object by object (3 September 2026).

For every labor-slack object on hand and two forms of its gap (Sahm's three-month form and the
one-month form, each against the previous twelve months' minimum), the LOWEST line that no reading
inside the 1951 or 1967 claims episodes reaches is found, and at that line the object's speed is
read on the twelve committee recessions and on 2023-24.  The line is the infimum that excludes the
two episodes Anthony does not count; anything an object can do as the second condition of the
American call, it does at least this fast and no faster.  Also counted: every crossing of that line
outside the recession windows (the object alone, no claims condition).  Current vintage.
Output lab/slack/bound.log.
"""
import sys; sys.path.insert(0, '/home/claude/lab/slack')
import numpy as np, pandas as pd
from objects import load, sahm, gap1

PEAKS = ['1948-11', '1953-07', '1957-08', '1960-04', '1969-12', '1973-11', '1980-01', '1981-07', '1990-07', '2001-03', '2007-12', '2020-02']
TROUGHS = ['1949-10', '1954-05', '1958-04', '1961-02', '1970-11', '1975-03', '1980-07', '1982-11', '1991-03', '2001-11', '2009-06', '2020-04']
NOT = {'1951': ('1951-06', '1952-08'), '1967': ('1967-01', '1968-03')}
EP24 = ('2023-06', '2025-06')
M = lambda s: pd.Timestamp(s + '-01')

def first_cross(g, line, lo, hi):
    seg = g[M(lo):M(hi)]
    hit = seg[seg >= line]
    return None if hit.empty else hit.index[0]

def months(a, b):
    return (a.year - b.year) * 12 + a.month - b.month

def alone_firings(g, line):
    """Episode starts of g >= line outside [peak-6, trough+6] of the twelve and outside 2023-06..2026-06."""
    on = False; out = []
    for t, v in g.items():
        if v >= line and not on:
            inside = any(M(p) - pd.DateOffset(months=6) <= t <= M(q) + pd.DateOffset(months=6) for p, q in zip(PEAKS, TROUGHS))
            inside = inside or (M('2023-06') <= t <= M('2026-06'))
            if not inside: out.append(t)
            on = True
        elif v < line:
            on = False
    return out

def table(o, form, name):
    rows = []
    for k, s in o.items():
        g = form(s)
        if g.empty: continue
        nots = {}
        for nm, (a, b) in NOT.items():
            seg = g[M(a):M(b)]
            nots[nm] = float(seg.max()) if not seg.empty else np.nan
        if all(np.isnan(v) for v in nots.values()):
            line = np.nan
        else:
            line = np.nanmax(list(nots.values())) + 1e-9      # an object that begins after 1951 is tested on 1967 alone, and the table says so (max1951 nan)
        lags = []
        for p in PEAKS:
            if g.index.min() > M(p) + pd.DateOffset(months=12): lags.append(None); continue
            t = None if np.isnan(line) else first_cross(g, line, (M(p) - pd.DateOffset(months=3)).strftime('%Y-%m'), (M(p) + pd.DateOffset(months=12)).strftime('%Y-%m'))
            lags.append(None if t is None else months(t, M(p)))
        t24 = None if np.isnan(line) else first_cross(g, line, *EP24)
        fa = [] if np.isnan(line) else alone_firings(g, line)
        covered = [l for l in lags if l is not None]
        n_avail = sum(1 for p in PEAKS if g.index.min() <= M(p) + pd.DateOffset(months=12))
        rows.append(dict(object=k, form=name, line=line, max1951=nots['1951'], max1967=nots['1967'],
                         reached=f'{len(covered)}/{n_avail}', lags=lags, median=(np.median(covered) if covered else None),
                         worst=(max(covered) if covered else None), t24=(None if t24 is None else t24.strftime('%Y-%m')),
                         alone=len(fa), alone_list=[t.strftime('%Y-%m') for t in fa][:8]))
    return rows

if __name__ == '__main__':
    o = load()
    out = []
    for form, name in ((lambda s: sahm(s, 3, 12), 'sahm3'), (gap1, 'gap1')):
        out += table(o, form, name)
    print('object                   form   line(excl 51/67)  max51  max67  reached  lags after the peak month (twelve)                         median worst  2024 crossing  alone-firings')
    for r in out:
        lg = ' '.join(f'{l:>3d}' if l is not None else '  -' for l in r['lags'])
        med = '    -' if r['median'] is None else f"{r['median']:5.1f}"
        wst = '   -' if r['worst'] is None else f"{r['worst']:4d}"
        print(f"{r['object']:24s} {r['form']:6s} {r['line']:8.3f}         {r['max1951']:5.2f}  {r['max1967']:5.2f}  {r['reached']:7s}  {lg}   {med}  {wst}   {(r['t24'] or 'never'):10s}  {r['alone']:3d} {r['alone_list']}")
