"""THE CONJUNCTIVE SECOND CONDITION (4 September 2026) - the design the diagnosis of §8aa points to.

§8aa's finding: every single object fast enough to move the 1973 and 2007 walls is also close enough to the
February 1967 credit crunch to call it.  Four candidates refused, one cause.

But this route already knows the answer to that shape of problem, because it is the route's own design.  A claims
object alone opens three episodes outside the thirteen; the claims object AND a second condition opens none.  The
conjunction is what buys the safety, and it is worth one to two orders of magnitude (§8v).  So the question this
script asks is: can the SECOND condition be given the same treatment - not "the rate OR the vacancy rate OR a fast
object", which is what §8y and §8aa tested and refused, but "the rate OR the vacancy rate OR (fast object A AND
fast object B)"?

Why this could work where a single object cannot.  A pair fires only where BOTH readings are at their lines in the
same month, so its window exposure is at most the smaller of the two and usually far less; and 1967 is precisely a
month in which SOME labour readings fell hard (construction, manufacturing, industrial production) while others did
not move at all (the unemployment rate, total employment).  A pair that takes one from each family should separate
1967 from the thirteen at lines much lower - which is to say much faster - than either object can alone.

THE GATES, unchanged from §8aa and applied in that order, before any selection:
  1  window exposure at or below 5.8 per cent;
  2  the OR of the whole second condition no higher than the shipped pair's 6.72 per cent;
  3  every one of the three disturbance calls cleared by at least +0.46 sd, the margin the shipped condition
     itself carries - measured ON FIRST PRINTS, on the tool's own window;
  4  all twelve called, no episode outside the thirteen.

FIRST PRINTS.  Only series whose ALFRED vintages begin before 1967 are admitted, so 1967 is read as it was
printed: INDPRO (1927), UNRATE (1960), HOUST (1960), AWHMAN, CE16OV, CLF16OV, MANEMP, PAYEMS, USCONS (1961),
PI (1966), UNEMPLOY (1966).  The pair is public on the LATER of its two publication days.

Output second_pairs_all.log.
"""
import sys, itertools, warnings; warnings.filterwarnings('ignore')
sys.path.insert(0, '/home/claude'); sys.path.insert(0, '/home/claude/lab/weekly'); sys.path.insert(0, '/home/claude/lab/rt')
import numpy as np, pandas as pd
import bristow_rule_v3 as B, american_chronology as AC, alfred

PK, TR = AC.PK, AC.TR
P13 = list(PK) + [pd.Timestamp('2023-07-01')]; T13 = list(TR) + [pd.Timestamp('2024-08-01')]
log = open('/home/claude/lab/weekly/second_pairs_all.log', 'w')
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
def tightest(o, line):
    o = o.dropna(); sd = float(o[quiet(o.index)].std()); out = []
    for call, nm, end in DIS:
        seg = o[call - pd.DateOffset(months=6): end]
        if len(seg): out.append((line - float(seg.max())) / sd)
    return min(out) if out else -9.9
GATE3 = 0.46

def rt(sid, path=None):
    cur = pd.read_csv(path or f'/home/claude/archive/data/fred/{sid}.csv'); cur.columns = ['d', 'v']
    cur = cur.set_index(pd.to_datetime(cur['d']))['v'].astype(float).dropna()
    fp = alfred.first_prints(sid)
    return pd.concat([cur[cur.index < fp.index.min()], fp]).sort_index()

def pct_fall(s, k, back):
    m = (np.log(s) * 100).rolling(k).mean(); return (m.shift(1).rolling(back).max() - m).dropna()
def pct_rise(s, k, back):
    m = (np.log(s) * 100).rolling(k).mean(); return (m - m.shift(1).rolling(back).min()).dropna()
def lvl_rise(s, k, back):
    m = s.rolling(k).mean(); return (m - m.shift(1).rolling(back).min()).dropna()

SRC = {}
for sid, pub in (('INDPRO', 15), ('UNRATE', 7), ('HOUST', 18), ('AWHMAN', 7), ('CE16OV', 7),
                 ('MANEMP', 7), ('PAYEMS', 7), ('USCONS', 7), ('UNEMPLOY', 7)):
    try: SRC[sid] = (rt(sid), pub)
    except Exception as e: P(f'  ({sid}: {e})')
P(f'first-print sources admitted: ' + ', '.join(f'{k} (vintages from {alfred.vintages(k)[0]:%Y-%m}, published day {v[1]})' for k, v in SRC.items()))

OBJ = {}
for sid, (s, pub) in SRC.items():
    for k in (1, 2, 3):
        if sid in ('UNRATE', 'UNEMPLOY'):
            OBJ[f'{sid} rise({k},6)'] = (lvl_rise(s, k, 6) if sid == 'UNRATE' else pct_rise(s, k, 6), pub)
            OBJ[f'{sid} rise({k},12)'] = (lvl_rise(s, k, 12) if sid == 'UNRATE' else pct_rise(s, k, 12), pub)
        else:
            OBJ[f'{sid} %fall({k},6)'] = (pct_fall(s, k, 6), pub)
            OBJ[f'{sid} %fall({k},12)'] = (pct_fall(s, k, 12), pub)
P(f'{len(OBJ)} objects, {len(list(itertools.combinations(OBJ, 2)))} pairs.')

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
B1973 = b[pd.Timestamp('1973-11-01')]; B2007 = b[pd.Timestamp('2007-12-01')]
P(f'version 43 base: median {np.median(list(b.values())):.0f} d, worst {max(b.values())}, 1973 {B1973}, 2007 {B2007}, '
  f'within a month {sum(0 <= v <= 30 for v in b.values())}/12, other {bo}')

# each object's own quantile grid on quiet months (so the lines are comparable across objects)
GRID = {}
for nm, (o, pub) in OBJ.items():
    oq = o[quiet(o.index)]
    if len(oq) < 200: continue
    GRID[nm] = np.unique(np.round(np.quantile(oq.values, [0.80, 0.88, 0.93, 0.96, 0.98, 0.99]), 4))

P('\nEVERY PAIR, as a CONJUNCTION: the month both readings stand at their lines, public on the later of the two days.')
P('Reported only where all four gates pass AND at least one wall moves.')
hits = []
names = sorted(GRID)
for a, c in itertools.combinations(names, 2):
    if a.split()[0] == c.split()[0]: continue                 # not the same series twice
    oa, pa = OBJ[a]; oc, pc = OBJ[c]; pub = max(pa, pc)
    for la in GRID[a]:
        for lc in GRID[c]:
            z = pd.concat([(oa / la if la else oa), (oc / lc if lc else oc)], axis=1).dropna().min(axis=1)
            if len(z) < 300: continue
            e = float(exp_s(z, 1.0).reindex(IDX).fillna(False).astype(bool)[QM].mean() * 100)
            if e > 5.8: continue
            comb = float((eS | eV | exp_s(z, 1.0).reindex(IDX).fillna(False).astype(bool))[QM].mean() * 100)
            if comb > SHIPPED_OR + 1e-9: continue
            if tightest(z, 1.0) < GATE3: continue
            hit, err, other = route(BASE + [dict(name='pair', gap=z, line=1.0, pub_day=pub)])
            if len(hit) < 12 or len(other) > 1: continue
            w73, w07 = hit[pd.Timestamp('1973-11-01')], hit[pd.Timestamp('2007-12-01')]
            hits.append(dict(a=a, la=float(la), c=c, lc=float(lc), pub=pub, expo=e, comb=comb,
                             marg=tightest(z, 1.0), w1973=w73, w2007=w07, worst=max(hit.values()),
                             med=float(np.median(list(hit.values()))), mae=float(np.mean([abs(x) for x in err.values()])),
                             inm=sum(0 <= v <= 30 for v in hit.values()), other=str(other),
                             **{f'lag_{p:%Y%m}': v for p, v in hit.items()},
                             **{f'err_{p:%Y%m}': v for p, v in err.items()}))
H = pd.DataFrame(hits)
H.to_csv('/home/claude/lab/weekly/second_pairs_all.csv', index=False)
P(f'\n{len(H)} pair settings pass all four gates (every admissible setting, whether or not it moves a wall).')
P(f'  of them, {int(((H.w1973 < B1973) | (H.w2007 < B2007)).sum())} move at least one wall.')
if len(H):
    H['gain'] = (B1973 - H.w1973).clip(lower=0) + (B2007 - H.w2007).clip(lower=0)
    for _, r in H.sort_values('gain', ascending=False).head(30).iterrows():
        P(f'  {r.a:22s} >= {r.la:8.3f}  AND  {r.c:22s} >= {r.lc:8.3f}  | pub {int(r.pub):2d}  expo {r.expo:4.1f}%  '
          f'OR {r.comb:5.2f}%  margin {r.marg:+.2f} sd  1973 {B1973}->{int(r.w1973):4d}  2007 {B2007}->{int(r.w2007):4d}  '
          f'worst {int(r.worst):4d}  med {r.med:4.0f}  mae {r.mae:.2f}')
else:
    P('  none: the conjunctive design does not move a wall inside the gates either.')
log.close()
