"""The vacancy object's forms (3 September 2026, night, fourth pass): how fast can the vacancy rate's
fall be read without touching 1951, 1952 or 1967?

Forms: k-month mean of the vacancy rate (k = 1, 2, 3) below its maximum over the previous `back`
months (6 or 12).  For each form: the maximum inside the three disturbances (the negatives' ceiling),
the minimum of the twelve's maxima (the positives' floor), the midpoint line, and at that line the
first crossing month of each of the twelve and of 2023-24 relative to the peak month, plus the
object's own crossings outside recession windows since 1948.  Petrosky-Nadeau-Zhang to 2000, JOLTS
after (current vintage).  Output vacancy_forms.log.
"""
import sys; sys.path.insert(0, '/home/claude/lab/slack')
import numpy as np, pandas as pd
from objects import load
from bound import PEAKS, TROUGHS, M, months

v = -load()['-vacancy rate']    # the vacancy rate itself
EPS = [('1948-11', '1949-10'), ('1953-07', '1954-05'), ('1957-08', '1958-04'), ('1960-04', '1961-02'), ('1969-12', '1970-11'), ('1973-11', '1975-03'),
       ('1980-01', '1980-07'), ('1981-07', '1982-11'), ('1990-07', '1991-03'), ('2001-03', '2001-11'), ('2007-12', '2009-06'), ('2020-02', '2020-04')]
NEG = [('1951-06', '1952-08'), ('1952-03', '1952-12'), ('1967-01', '1968-03')]
E24 = ('2023-06', '2025-06')

def form(k, back):
    m = v.rolling(k).mean()
    return (m.shift(1).rolling(back).max() - m).dropna()

def alone(g, line, since='1949'):
    """own crossings from 1949 - the route's record start (legs_1948.RECORD_START: the claims field's factors need 24 months)"""
    on = False; out = []
    for t, val in g[since:].items():
        if val >= line and not on:
            inside = any(M(p) - pd.DateOffset(months=9) <= t <= M(q) + pd.DateOffset(months=6) for p, q in zip(PEAKS, TROUGHS)) or (M('2022-06') <= t <= M('2026-06'))
            if not inside: out.append(t.strftime('%Y-%m'))
            on = True
        elif val < line: on = False
    return out

print('form (k, back)   negatives ceiling   positives floor   line (midpoint)   crossings, months after the peak (twelve)          <=0  <=1  median  2023-24   own crossings outside recessions')
for k in (1, 2, 3):
    for back in (6, 12):
        g = form(k, back)
        neg = max(float(g[M(a) - pd.DateOffset(months=3): M(b)].max()) for a, b in NEG)
        pos = [float(g[M(a) - pd.DateOffset(months=3): M(b)].max()) for a, b in EPS]
        floor = min(pos); line = round((neg + floor) / 2, 2)
        lags = []
        for a, b in EPS:
            seg = g[M(a) - pd.DateOffset(months=3): M(b)]; h = seg[seg >= line]
            lags.append(None if h.empty else months(h.index[0], M(a)))
        seg = g[M(E24[0]) - pd.DateOffset(months=3): M(E24[1])]; h = seg[seg >= line]; t24 = 'never' if h.empty else h.index[0].strftime('%Y-%m')
        cov = [l for l in lags if l is not None]
        print(f'({k}, {back:2d})           {neg:5.2f}              {floor:5.2f}            {line:5.2f}            ' + ' '.join(f'{l:>3d}' if l is not None else '  -' for l in lags) +
              f'   {sum(1 for l in cov if l <= 0):2d}   {sum(1 for l in cov if l <= 1):2d}   {np.median(cov):4.1f}   {t24:8s}  {alone(g, line)}')
print('\nthe twelve\'s maxima, form (1, 12):', [round(float(form(1, 12)[M(a) - pd.DateOffset(months=3): M(b)].max()), 2) for a, b in EPS])
print("the twelve's maxima, form (3, 12):", [round(float(form(3, 12)[M(a) - pd.DateOffset(months=3): M(b)].max()), 2) for a, b in EPS])

print('\nLEAVE-ONE-OUT: for each recession left out, the line from the negatives and the remaining eleven, the form with the best median crossing on the eleven, and the left-out crossing at that form and line')
forms = [(k, back) for k in (1, 2, 3) for back in (6, 12)]
G = {f: form(*f) for f in forms}
negs = {f: max(float(G[f][M(a) - pd.DateOffset(months=3): M(b)].max()) for a, b in NEG) for f in forms}
maxes = {f: [float(G[f][M(a) - pd.DateOffset(months=3): M(b)].max()) for a, b in EPS] for f in forms}
def cross(f, line, a, b):
    seg = G[f][M(a) - pd.DateOffset(months=3): M(b)]; h = seg[seg >= line]
    return None if h.empty else months(h.index[0], M(a))
picks = []
for i, (a, b) in enumerate(EPS):
    best = None
    for f in forms:
        floor = min(m for j, m in enumerate(maxes[f]) if j != i); line = (negs[f] + floor) / 2
        lags = [cross(f, line, aa, bb) for j, (aa, bb) in enumerate(EPS) if j != i]
        if any(l is None for l in lags): continue
        noise = len(alone(G[f], line))
        key = (noise, np.median(lags), max(lags))
        if best is None or key < best[0]: best = (key, f, line)
    key, f, line = best
    out = cross(f, line, a, b)
    picks.append(f)
    print(f'  leave out {a}: picks form {f} at line {line:.2f} (own crossings {key[0]}, median {key[1]:.1f}, worst {key[2]}); the left-out recession crosses at {out:+d} months')
print('  every fold picks the same form:', len(set(picks)) == 1, set(picks))

print('\nOUT OF SAMPLE, 1920-1947 (Petrosky-Nadeau-Zhang from 1919): each form at the line set on 1948-2026 - the interwar recessions reached, and every crossing outside their windows')
IW = [('1920-01', '1921-07'), ('1923-05', '1924-07'), ('1926-10', '1927-11'), ('1929-08', '1933-03'), ('1937-05', '1938-06'), ('1945-02', '1945-10')]
def alone_iw(g, line):
    on = False; out = []
    for t, val in g['1920-06':'1947-12'].items():
        if val >= line and not on:
            inside = any(M(p) - pd.DateOffset(months=9) <= t <= M(q) + pd.DateOffset(months=6) for p, q in IW)
            if not inside: out.append(t.strftime('%Y-%m'))
            on = True
        elif val < line: on = False
    return out
LINES = {(1, 6): 0.41, (1, 12): 0.67, (2, 6): 0.36, (2, 12): 0.65, (3, 6): 0.35, (3, 12): 0.62}
for f, line in LINES.items():
    g = G[f]
    lags = []
    for a, b in IW:
        seg = g[M(a) - pd.DateOffset(months=3): M(b)]; h = seg[seg >= line]
        lags.append(None if h.empty else months(h.index[0], M(a)))
    print(f'  form {f} line {line:.2f}: interwar crossings (months after the peak) ' + ' '.join(f'{l:>3d}' if l is not None else '  -' for l in lags) + f'   reached {sum(l is not None for l in lags)}/6;  crossings outside the windows: {alone_iw(g, line)}')
