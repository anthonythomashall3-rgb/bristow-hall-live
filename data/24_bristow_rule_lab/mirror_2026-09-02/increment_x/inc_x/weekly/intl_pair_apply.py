"""THE FOREIGN SAMPLE'S LINE, APPLIED TO THE UNITED STATES UNCHANGED (4 September 2026).

`intl_pair_calibration.py` chose the pair's form and its two lines on twenty-seven contractions in Canada, Japan
and Korea, with no American datum anywhere in the file.  This script applies that choice to the American route
ONCE and reports what happens.  It is a test, not a search: nothing here is tuned, and whatever the numbers are,
they are the numbers.

The foreign choice, in raw units (the leave-one-contraction-out mode, 24 of 27 folds):
    k = 2 months, trailing window 6 months, HOUSING >= 15.0 log points below its trailing maximum
    AND the UNEMPLOYMENT RATE >= 0.10 points above its trailing minimum
The standardized calibration's mode is applied as well, in each object's own quiet standard deviations.

American data, on first prints: housing starts (HOUST, ALFRED vintages from July 1960) and the unemployment rate
(UNRATE, vintages from March 1960).  Published the 18th (the later of the two release days).

The four gates of memo 8aa are then REPORTED, not imposed - a line handed over from outside the sample is not
re-selected here; if it fails a gate that is the finding.

Output intl_pair_apply.log.
"""
import sys, warnings; warnings.filterwarnings('ignore')
sys.path.insert(0, '/home/claude'); sys.path.insert(0, '/home/claude/lab/weekly'); sys.path.insert(0, '/home/claude/lab/rt')
import numpy as np, pandas as pd
import bristow_rule_v3 as B, american_chronology as AC, alfred
PK, TR = AC.PK, AC.TR
P13 = list(PK) + [pd.Timestamp('2023-07-01')]; T13 = list(TR) + [pd.Timestamp('2024-08-01')]
log = open('/home/claude/lab/weekly/intl_pair_apply.log', 'w')
def P(*a): print(*a); print(*a, file=log, flush=True)
def quiet(idx):
    q = pd.Series(True, index=idx)
    for p, t in zip(P13, T13): q[(idx >= p - pd.DateOffset(months=9)) & (idx <= t + pd.DateOffset(months=18))] = False
    return q
def exp_s(o, line):
    h = (o >= line)
    return (h[::-1].rolling(1, min_periods=1).max()[::-1].astype(bool) | h.rolling(7, min_periods=1).max().astype(bool))
PL, TL = AC.legs(safe=True, with_S=True, with_U=True)
G = AC.sahm_rt(); VR = AC.vacancy_gap_rt(2, 6)
BASE = [dict(name='vacancy(2,6)', gap=VR, line=0.36, pub_day=30)]
IDX = pd.date_range('1949-01-01', '2026-07-01', freq='MS'); QM = quiet(IDX)
eS = exp_s(G, 0.5).reindex(IDX).fillna(False).astype(bool); eV = exp_s(VR, 0.36).reindex(IDX).fillna(False).astype(bool)
SHIPPED_OR = float((eS | eV)[QM].mean() * 100)
DIS = [(pd.Timestamp('1951-09-20'), 'July 1951', pd.Timestamp('1951-12-10')),
       (pd.Timestamp('1952-04-10'), 'March 1952', pd.Timestamp('1952-10-10')),
       (pd.Timestamp('1967-04-20'), 'February 1967', pd.Timestamp('1968-08-20'))]
def rt(sid):
    cur = pd.read_csv(f'/home/claude/archive/data/fred/{sid}.csv'); cur.columns = ['d', 'v']
    cur = cur.set_index(pd.to_datetime(cur['d']))['v'].astype(float).dropna()
    fp = alfred.first_prints(sid)
    return pd.concat([cur[cur.index < fp.index.min()], fp]).sort_index()
H = rt('HOUST'); U = rt('UNRATE')
def pct_fall(s, k, back):
    m = (np.log(s.clip(lower=1e-9)) * 100).rolling(k).mean(); return (m.shift(1).rolling(back).max() - m).dropna()
def lvl_rise(s, k, back):
    m = s.rolling(k).mean(); return (m - m.shift(1).rolling(back).min()).dropna()
def route(second):
    t = B.american_chronology(PL, TL, sahm=G, second=second)
    hit = {}; err = {}; other = []
    for x in [y for y in t if y['kind'] == 'peak']:
        c = [i for i, (p, q) in enumerate(zip(PK, TR)) if p - pd.DateOffset(months=6) <= x['date'] <= q]
        if c:
            hit[PK[c[0]]] = (x['published'] - AC.month_end(PK[c[0]])).days
            err[PK[c[0]]] = (x['date'].year - PK[c[0]].year) * 12 + (x['date'].month - PK[c[0]].month)
        else: other.append(f"{x['published']:%Y-%m-%d}")
    return hit, err, other
b, be, bo = route(BASE)
P(f'version 43: median {np.median(list(b.values())):.0f} d, worst {max(b.values())}, 1973 {b[pd.Timestamp("1973-11-01")]}, '
  f'2007 {b[pd.Timestamp("2007-12-01")]}, within a month {sum(0 <= v <= 30 for v in b.values())}/12, '
  f'mae {np.mean([abs(x) for x in be.values()]):.2f}, other {bo}')

def apply(k, back, lh, lu, standardized, label):
    Ho = pct_fall(H, k, back); Uo = lvl_rise(U, k, back)
    if standardized:
        sh = float(Ho[quiet(Ho.index)].std()); su = float(Uo[quiet(Uo.index)].std())
        Ho = Ho / sh; Uo = Uo / su
        P(f'\n{label}  (American quiet standard deviations: housing {sh:.2f} log points, rate {su:.3f} points)')
    else:
        P(f'\n{label}')
    z = pd.concat([Ho / lh, Uo / lu], axis=1).dropna().min(axis=1)
    e = float(exp_s(z, 1.0).reindex(IDX).fillna(False).astype(bool)[QM].mean() * 100)
    comb = float((eS | eV | exp_s(z, 1.0).reindex(IDX).fillna(False).astype(bool))[QM].mean() * 100)
    sd = float(z[quiet(z.index)].std()); marg = []
    for call, nm, end in DIS:
        seg = z[call - pd.DateOffset(months=6): end]
        if len(seg): marg.append(((1.0 - float(seg.max())) / sd, nm, float(seg.max()), seg.idxmax()))
    hit, err, other = route(BASE + [dict(name='pair', gap=z, line=1.0, pub_day=18)])
    P(f'  GATE 1 window exposure {e:.2f} per cent (the gate is 5.8)                    {"PASS" if e <= 5.8 else "FAIL"}')
    P(f'  GATE 2 the OR of the second condition {comb:.2f} per cent against the shipped {SHIPPED_OR:.2f}   {"PASS" if comb <= SHIPPED_OR + 1e-9 else "FAIL"}')
    for m, nm, mx, at in marg:
        P(f'  GATE 3 {nm:15s} maximum {mx:6.3f} in {at:%Y-%m}, margin {1 - mx:+.3f} ({m:+.2f} sd)   '
          f'{"PASS" if m >= 0.46 else "FAIL"}')
    P(f'  GATE 4 peaks {len(hit)}/12, outside the thirteen {other}                      '
      f'{"PASS" if len(hit) == 12 and len(other) <= 1 else "FAIL"}')
    if len(hit) == 12:
        P(f'  THE ROUTE: median {np.median(list(hit.values())):.0f} d (was {np.median(list(b.values())):.0f}), '
          f'worst {max(hit.values())} (was {max(b.values())}), 1973 {hit[pd.Timestamp("1973-11-01")]} (was {b[pd.Timestamp("1973-11-01")]}), '
          f'2007 {hit[pd.Timestamp("2007-12-01")]} (was {b[pd.Timestamp("2007-12-01")]}), '
          f'within a month {sum(0 <= v <= 30 for v in hit.values())}/12, mae {np.mean([abs(x) for x in err.values()]):.2f}')
        P('  ' + '  '.join(f'{p:%Y-%m}:{v:+d}[{err[p]:+d}]' + (f'(was {b[p]:+d})' if v != b[p] else '') for p, v in hit.items()))

apply(2, 6, 15.0, 0.10, False, "THE FOREIGN SAMPLE'S CHOICE IN RAW UNITS: housing 15.0 log points AND the rate 0.10 points, k=2, back=6")
apply(1, 6, 0.75, 1.75, True, "THE FOREIGN SAMPLE'S CHOICE IN STANDARD DEVIATIONS (whole-sample best): housing 0.75 sd AND the rate 1.75 sd, k=1, back=6")
log.close()
