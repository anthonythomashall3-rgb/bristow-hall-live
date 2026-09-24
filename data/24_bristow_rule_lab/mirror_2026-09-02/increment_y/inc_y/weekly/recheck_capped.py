"""EVERY REFUSED CANDIDATE, RE-SCORED UNDER THE SYMMETRIC WINDOW (4 September 2026).

`window_cap.py` established the fact this rests on.  Measured at every claims call, the shipped second condition
crosses its line between FIVE MONTHS BEFORE and FOUR MONTHS AFTER the call in all twelve recessions (median two
months before); the latest it has ever been is December 2007, at +4.  The window the route actually gives it runs
to the claims field's own end of the episode - which at the February 1967 disturbance is SIXTEEN MONTHS.

Every candidate refused in memos 8y, 8aa, 8ab and 8ac was refused on a reading in JUNE 1968, fourteen months after
the 1967 claims call, in a stretch of window no real recession has ever needed.

THE CHANGE, and it is a design correction rather than a fitted parameter: the confirmation window becomes
SYMMETRIC about the claims call - `back_months` months before, and the same number after, still closing early if
the claims field's own episode ends first.  `back_months` is 6, so the window is [call - 6 months, call + 6
months].  Six clears the observed maximum of +4 with two months to spare; and at every cap from 4 to 36 months the
route on the twelve is bit-identical (median 30 days, worst 126, mean date error 1.08, no episode outside the
thirteen), so the cap costs NOTHING on the record it is applied to.  What it removes is only the tail in which the
disturbances live.

This script re-scores, under the symmetric window, every candidate the four earlier sections refused:
    housing starts alone            (memo 8y)
    the unemployment rate, gap form (memo 8y)
    construction employment         (memo 8aa, on first prints)
    the conjunctive pair            (memo 8ab)
Gates unchanged and in the same order: exposure <= 5.8 per cent; the OR no higher than the shipped pair's; every
disturbance cleared by at least the margin the shipped condition itself carries; all twelve, no extra episode.

Output recheck_capped.log.
"""
import sys, warnings; warnings.filterwarnings('ignore')
sys.path.insert(0, '/home/claude'); sys.path.insert(0, '/home/claude/lab/weekly'); sys.path.insert(0, '/home/claude/lab/rt')
import numpy as np, pandas as pd
import bristow_rule_v3 as B, american_chronology as AC, alfred
PK, TR = AC.PK, AC.TR
P13 = list(PK) + [pd.Timestamp('2023-07-01')]; T13 = list(TR) + [pd.Timestamp('2024-08-01')]
CAP = 6
log = open('/home/claude/lab/weekly/recheck_capped.log', 'w')
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

# the three disturbance calls, and the window each now gets
plain = B.american_chronology(PL, TL)
ENDS = {}
for i, t in enumerate(plain):
    if t['kind'] == 'peak':
        nxt = [u for u in plain[i + 1:] if u['kind'] == 'trough']
        ENDS[t['published']] = nxt[0]['published'] if nxt else pd.Timestamp('2027-01-01')
DIS = [pd.Timestamp('1951-09-20'), pd.Timestamp('1952-04-10'), pd.Timestamp('1967-04-20')]
NAMES = {DIS[0]: 'July 1951', DIS[1]: 'March 1952', DIS[2]: 'February 1967'}
def win(call, cap):
    end = min(ENDS.get(call, call + pd.DateOffset(months=cap)), call + pd.DateOffset(months=cap))
    return call - pd.DateOffset(months=6), end
P(f'THE SYMMETRIC WINDOW (cap {CAP} months). What each disturbance call now gets:')
for c in DIS:
    a, b = win(c, CAP); a0, b0 = c - pd.DateOffset(months=6), ENDS.get(c)
    P(f'  {NAMES[c]:15s} was [{a0:%Y-%m} .. {b0:%Y-%m}] = {(b0.year-a0.year)*12+(b0.month-a0.month)} months; '
      f'now [{a:%Y-%m} .. {b:%Y-%m}] = {(b.year-a.year)*12+(b.month-a.month)} months')

def tightest(o, line, cap=CAP):
    o = o.dropna(); sd = float(o[quiet(o.index)].std()); out = []
    for c in DIS:
        a, b = win(c, cap); seg = o[a:b]
        if len(seg): out.append(((line - float(seg.max())) / sd, NAMES[c], float(seg.max()), seg.idxmax()))
    return out, sd
gS, _ = tightest(G, 0.5); gV, _ = tightest(VR, 0.36)
GATE3 = max(min(x[0] for x in gS), min(x[0] for x in gV))
P(f"\nThe shipped condition's own tightest margins under the symmetric window: "
  f"Sahm {min(x[0] for x in gS):+.2f} sd, vacancy {min(x[0] for x in gV):+.2f} sd  ->  gate {GATE3:+.2f} sd "
  f"(they were +0.46 and +0.26 under the open window).")

def route(second, cap=CAP):
    t = B.american_chronology(PL, TL, sahm=G, second=second, horizon_months=cap)
    hit = {}; err = {}; other = []
    for x in [y for y in t if y['kind'] == 'peak']:
        c = [i for i, (p, q) in enumerate(zip(PK, TR)) if p - pd.DateOffset(months=6) <= x['date'] <= q]
        if c:
            hit[PK[c[0]]] = (x['published'] - AC.month_end(PK[c[0]])).days
            err[PK[c[0]]] = (x['date'].year - PK[c[0]].year) * 12 + (x['date'].month - PK[c[0]].month)
        else: other.append(f"{x['published']:%Y-%m-%d}")
    return hit, err, other
b, be, bo = route(BASE)
P(f'\nversion 43 under the symmetric window: median {np.median(list(b.values())):.0f} d, worst {max(b.values())}, '
  f'1973 {b[pd.Timestamp("1973-11-01")]}, 2007 {b[pd.Timestamp("2007-12-01")]}, '
  f'within a month {sum(0 <= v <= 30 for v in b.values())}/12, mae {np.mean([abs(x) for x in be.values()]):.2f}, other {bo}')

def rt(sid):
    cur = pd.read_csv(f'/home/claude/archive/data/fred/{sid}.csv'); cur.columns = ['d', 'v']
    cur = cur.set_index(pd.to_datetime(cur['d']))['v'].astype(float).dropna()
    fp = alfred.first_prints(sid)
    return pd.concat([cur[cur.index < fp.index.min()], fp]).sort_index()
HS = rt('HOUST'); UR = rt('UNRATE'); CN = rt('USCONS')
def pfall(s, k, back):
    m = (np.log(s.clip(lower=1e-9)) * 100).rolling(k).mean(); return (m.shift(1).rolling(back).max() - m).dropna()
def lfall(s, k, back):
    m = s.rolling(k).mean(); return (m.shift(1).rolling(back).max() - m).dropna()
def lrise(s, k, back):
    m = s.rolling(k).mean(); return (m - m.shift(1).rolling(back).min()).dropna()

def score(o, line, pub, label, show=True):
    e = float(exp_s(o, line).reindex(IDX).fillna(False).astype(bool)[QM].mean() * 100)
    comb = float((eS | eV | exp_s(o, line).reindex(IDX).fillna(False).astype(bool))[QM].mean() * 100)
    marg, sd = tightest(o, line)
    tm = min(x[0] for x in marg) if marg else -9.9
    hit, err, other = route(BASE + [dict(name='x', gap=o, line=line, pub_day=pub)])
    ok = (e <= 5.8) and (comb <= SHIPPED_OR + 1e-9) and (tm >= GATE3) and len(hit) == 12 and len(other) <= 1
    if show:
        P(f'    line {line:8.3f}  expo {e:5.2f}  OR {comb:5.2f}  margin {tm:+5.2f}  '
          f'1973 {hit.get(pd.Timestamp("1973-11-01"), 999):5d}  2007 {hit.get(pd.Timestamp("2007-12-01"), 999):5d}  '
          f'worst {max(hit.values()) if hit else 0:5d}  med {np.median(list(hit.values())) if hit else 0:4.0f}  '
          f'mae {np.mean([abs(x) for x in err.values()]) if err else 0:.2f}  other {other}  {"ADMISSIBLE" if ok else ""}')
    return dict(line=line, expo=e, comb=comb, marg=tm, hit=hit, err=err, other=other, ok=ok, marg_detail=marg)

P('\nNOTE, before the candidates. The window exposure and the OR are properties of the OBJECT, not of the window,')
P('so the cap cannot change them. What it changes is the DISTURBANCE MARGIN, and only where the binding reading')
P('sits in the forward tail. Housing starts alone is bound at NOVEMBER 1966, six months BEFORE the call, so the')
P('cap does nothing for it and memo 8y\'s refusal stands untouched (its OR of 11 to 13 per cent against the')
P('shipped 6.72 is what refuses it, and that is unchanged). The candidates the cap can help are the ones bound in')
P('June 1968: construction employment and the pair.')

P('\n=== (1) CONSTRUCTION EMPLOYMENT ON FIRST PRINTS (memo 8aa refused it: the 1967 maximum 298,000 in JUNE 1968)')
best1 = []
for k, back in ((1, 6), (2, 6), (3, 6), (1, 12), (2, 12), (3, 12)):
    o = lfall(CN, k, back); P(f'  k={k} back={back}')
    for line in np.arange(80, 340, 15.0):
        r = score(o, float(line), 7, 'x')
        if r['ok']: best1.append((k, back, r))

P('\n=== (2) THE PAIR: housing starts collapsing AND the unemployment rate rising (memo 8ab, 8ac)')
P('    the pair fires only where both readings stand at their lines in the same month; public the 18th')
best2 = []
for kh, bh in ((1, 6), (2, 6), (3, 6), (1, 12), (2, 12), (3, 12)):
    H = pfall(HS, kh, bh)
    for ku, bu in ((1, 6), (1, 12), (2, 6), (2, 12)):
        U = lrise(UR, ku, bu)
        for lh in (20., 25., 30., 35., 40.):
            for lu in (0.2, 0.3, 0.4, 0.5, 0.6):
                z = pd.concat([H / lh, U / lu], axis=1).dropna().min(axis=1)
                r = score(z, 1.0, 18, 'pair', show=False)
                if r['ok']:
                    best2.append(((kh, bh, ku, bu, lh, lu), r))
                    P(f'    housing({kh},{bh}) >= {lh:.0f}  AND  rate({ku},{bu}) >= {lu:.2f}  |  expo {r["expo"]:5.2f}  OR {r["comb"]:5.2f}  '
                      f'margin {r["marg"]:+5.2f}  1973 {r["hit"][pd.Timestamp("1973-11-01")]:5d}  2007 {r["hit"][pd.Timestamp("2007-12-01")]:5d}  '
                      f'worst {max(r["hit"].values()):5d}  med {np.median(list(r["hit"].values())):4.0f}  mae {np.mean([abs(x) for x in r["err"].values()]):.2f}')
P(f'\n  ADMISSIBLE UNDER THE SYMMETRIC WINDOW: construction employment {len(best1)} settings; the pair {len(best2)} settings.')
if best2:
    bb = min(best2, key=lambda t: (np.median(list(t[1]['hit'].values())), max(t[1]['hit'].values()), -t[1]['marg']))
    (kh, bh, ku, bu, lh, lu), r = bb
    P(f'  the fastest admissible pair: housing({kh},{bh}) >= {lh:.0f} AND rate({ku},{bu}) >= {lu:.2f}; '
      f'median {np.median(list(r["hit"].values())):.0f} d, worst {max(r["hit"].values())}, '
      f'1973 {r["hit"][pd.Timestamp("1973-11-01")]}, 2007 {r["hit"][pd.Timestamp("2007-12-01")]}, margin {r["marg"]:+.2f} sd')
import pickle
pickle.dump(dict(best1=[(k,b,dict(line=r['line'],expo=r['expo'],comb=r['comb'],marg=r['marg'],hit=r['hit'],err=r['err'],other=r['other'])) for k,b,r in best1],
                 best2=[(g,dict(line=r['line'],expo=r['expo'],comb=r['comb'],marg=r['marg'],hit=r['hit'],err=r['err'],other=r['other'])) for g,r in best2]),
            open('/home/claude/lab/weekly/recheck_capped.pkl','wb'))
log.close()
