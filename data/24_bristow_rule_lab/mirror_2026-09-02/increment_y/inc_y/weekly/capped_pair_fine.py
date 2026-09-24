"""THE ADMISSIBLE PAIRS ON A FINE GRID, UNDER THE SYMMETRIC WINDOW, WITH SELECTION (4 September 2026).

`recheck_capped.py` used a coarse grid (five housing lines, five rate lines) and its leave-one-out folds split
eleven to one.  A mode on a coarse grid can be an artefact of the grid, so this repeats the whole exercise on a
fine one - housing lines 15 to 45 in steps of 2.5, rate lines 0.15 to 0.65 in steps of 0.05, six housing forms and
four rate forms, 3,432 settings - and runs the selection again.

Gates, in order, unchanged: window exposure at or below 5.8 per cent; the OR of the second condition no higher
than the shipped pair's 6.72; every one of the three disturbance calls cleared, on the tool's own symmetric
window, by at least the margin the shipped condition itself carries (+0.68 sd, Sahm's, measured under the same
window); all twelve called and no episode outside the thirteen.

Output capped_pair_fine.log / .csv.
"""
import sys, warnings; warnings.filterwarnings('ignore')
sys.path.insert(0, '/home/claude'); sys.path.insert(0, '/home/claude/lab/weekly'); sys.path.insert(0, '/home/claude/lab/rt')
import numpy as np, pandas as pd
import bristow_rule_v3 as B, american_chronology as AC, alfred
PK, TR = AC.PK, AC.TR
P13 = list(PK) + [pd.Timestamp('2023-07-01')]; T13 = list(TR) + [pd.Timestamp('2024-08-01')]
CAP = 6
log = open('/home/claude/lab/weekly/capped_pair_fine.log', 'w')
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
plain = B.american_chronology(PL, TL); ENDS = {}
for i, t in enumerate(plain):
    if t['kind'] == 'peak':
        nxt = [u for u in plain[i + 1:] if u['kind'] == 'trough']
        ENDS[t['published']] = nxt[0]['published'] if nxt else pd.Timestamp('2027-01-01')
DIS = [pd.Timestamp('1951-09-20'), pd.Timestamp('1952-04-10'), pd.Timestamp('1967-04-20')]
def win(c): return c - pd.DateOffset(months=6), min(ENDS.get(c, c + pd.DateOffset(months=CAP)), c + pd.DateOffset(months=CAP))
def tight(o, line):
    o = o.dropna(); sd = float(o[quiet(o.index)].std()); out = []
    for c in DIS:
        a, b = win(c); seg = o[a:b]
        if len(seg): out.append((line - float(seg.max())) / sd)
    return min(out) if out else -9.9
GATE3 = tight(G, 0.5)
P(f'the gate on the disturbance margin, from the shipped condition itself under the symmetric window: {GATE3:+.3f} sd')
def rt(sid):
    cur = pd.read_csv(f'/home/claude/archive/data/fred/{sid}.csv'); cur.columns = ['d', 'v']
    cur = cur.set_index(pd.to_datetime(cur['d']))['v'].astype(float).dropna()
    fp = alfred.first_prints(sid)
    return pd.concat([cur[cur.index < fp.index.min()], fp]).sort_index()
HS = rt('HOUST'); UR = rt('UNRATE')
def pfall(s, k, back):
    m = (np.log(s.clip(lower=1e-9)) * 100).rolling(k).mean(); return (m.shift(1).rolling(back).max() - m).dropna()
def lrise(s, k, back):
    m = s.rolling(k).mean(); return (m - m.shift(1).rolling(back).min()).dropna()
def route(second):
    t = B.american_chronology(PL, TL, sahm=G, second=second, horizon_months=CAP)
    hit = {}; err = {}; other = []
    for x in [y for y in t if y['kind'] == 'peak']:
        c = [i for i, (p, q) in enumerate(zip(PK, TR)) if p - pd.DateOffset(months=6) <= x['date'] <= q]
        if c:
            hit[PK[c[0]]] = (x['published'] - AC.month_end(PK[c[0]])).days
            err[PK[c[0]]] = (x['date'].year - PK[c[0]].year) * 12 + (x['date'].month - PK[c[0]].month)
        else: other.append(f"{x['published']:%Y-%m-%d}")
    return hit, err, other
b, be, bo = route(BASE)
P(f'version 43 under the symmetric window: median {np.median(list(b.values())):.0f} d, worst {max(b.values())}, '
  f'1973 {b[pd.Timestamp("1973-11-01")]}, 2007 {b[pd.Timestamp("2007-12-01")]}, mae {np.mean([abs(x) for x in be.values()]):.2f}, other {bo}')
HF = {(k, bk): pfall(HS, k, bk) for k in (1, 2, 3) for bk in (6, 12)}
UF = {(k, bk): lrise(UR, k, bk) for k in (1, 2) for bk in (6, 12)}
rows = []
for (kh, bh), Ho in HF.items():
    for (ku, bu), Uo in UF.items():
        for lh in np.arange(15, 45.1, 2.5):
            for lu in np.arange(0.15, 0.66, 0.05):
                z = pd.concat([Ho / lh, Uo / lu], axis=1).dropna().min(axis=1)
                e = float(exp_s(z, 1.0).reindex(IDX).fillna(False).astype(bool)[QM].mean() * 100)
                if e > 5.8: continue
                comb = float((eS | eV | exp_s(z, 1.0).reindex(IDX).fillna(False).astype(bool))[QM].mean() * 100)
                if comb > SHIPPED_OR + 1e-9: continue
                m = tight(z, 1.0)
                if m < GATE3: continue
                hit, err, other = route(BASE + [dict(name='pair', gap=z, line=1.0, pub_day=18)])
                if len(hit) < 12 or len(other) > 1: continue
                rows.append(dict(kh=kh, bh=bh, ku=ku, bu=bu, lh=float(lh), lu=round(float(lu), 3), marg=m, expo=e, comb=comb,
                                 other=str(other),
                                 **{f'lag_{p:%Y%m}': hit[p] for p in PK},
                                 **{f'err_{p:%Y%m}': err[p] for p in PK}))
H = pd.DataFrame(rows); H.to_csv('/home/claude/lab/weekly/capped_pair_fine.csv', index=False)
P(f'\n{len(H)} settings admissible on the fine grid (of {6*4*13*11} tried).')
LAG = [f'lag_{p:%Y%m}' for p in PK]; ERR = [f'err_{p:%Y%m}' for p in PK]
H['sum_lag'] = H[LAG].sum(axis=1); H['sum_err'] = H[ERR].abs().sum(axis=1)
base = {p: v for p, v in zip(PK, [10, 51, -11, -70, 31, 120, 30, 122, 51, 30, 126, 26])}
picks = []
P('\nLEAVE-ONE-RECESSION-OUT (the kept lags, then the kept date errors, then the wider margin):')
for p in PK:
    k = f'lag_{p:%Y%m}'; e = f'err_{p:%Y%m}'
    sc = H.assign(s1=H.sum_lag - H[k], s2=H.sum_err - H[e].abs(), s3=-H.marg)
    r = sc.sort_values(['s1', 's2', 's3']).iloc[0]
    picks.append((int(r.kh), int(r.bh), int(r.ku), int(r.bu), float(r.lh), float(r.lu)))
    P(f'  leave out {p:%Y-%m}: housing({int(r.kh)},{int(r.bh)}) >= {r.lh:.1f} AND rate({int(r.ku)},{int(r.bu)}) >= {r.lu:.2f} '
      f'(margin {r.marg:+.2f} sd); held-out lag {int(r[k]):+d} against {base[p]:+d}, date {int(r[e]):+d}')
from collections import Counter
c = Counter(picks)
P(f'\nevery fold the same: {len(c) == 1}; distinct choices {len(c)}')
for g, n in c.most_common(): P(f'  {g}  in {n} of 12 folds')
P('\nWHAT THE FOLDS AGREE ON:')
for i, nm in enumerate(('housing k', 'housing back', 'rate k', 'rate back', 'housing line', 'rate line')):
    v = sorted({q[i] for q in picks}); P(f'  {nm:13s}: {v}   {"AGREED" if len(v) == 1 else ""}')
g = c.most_common(1)[0][0]
r = H[(H.kh == g[0]) & (H.bh == g[1]) & (H.ku == g[2]) & (H.bu == g[3]) & (H.lh == g[4]) & (H.lu == round(g[5], 3))].iloc[0]
lags = [int(r[f'lag_{p:%Y%m}']) for p in PK]; errs = [int(r[f'err_{p:%Y%m}']) for p in PK]
P(f'\nTHE MODAL CHOICE: housing starts, {g[0]}-month mean {g[4]:.1f} log points below its trailing {g[1]}-month maximum,')
P(f'  AND the unemployment rate, {g[2]}-month mean {g[5]:.2f} points above its trailing {g[3]}-month minimum; published the 18th.')
P(f'  exposure {r.expo:.2f}%, the OR {r.comb:.2f}% (shipped 6.72 - unchanged), margin {r.marg:+.2f} sd (gate {GATE3:+.2f})')
P(f'  median {np.median(lags):.0f} d (was 30), worst {max(lags)} (was 126), within a month {sum(0<=v<=30 for v in lags)}/12 (was 4), '
  f'mae {np.mean([abs(x) for x in errs]):.2f} (was 1.08), outside the thirteen {r.other}')
P('  ' + '  '.join(f'{p:%Y-%m}:{v:+d}[{e:+d}]' + (f'(was {base[p]:+d})' if v != base[p] else '') for p, v, e in zip(PK, lags, errs)))
log.close()
