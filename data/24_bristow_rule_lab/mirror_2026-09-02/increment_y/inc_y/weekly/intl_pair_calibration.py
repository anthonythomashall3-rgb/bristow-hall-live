"""THE PAIR'S LINES, IDENTIFIED OUT OF SAMPLE ON THE FOREIGN CHRONOLOGIES (4 September 2026).

§8ab found a conjunctive second condition that moves BOTH American walls at zero added hazard - housing collapsing
AND unemployment rising - and refused to adopt it, because twelve American recessions cannot pin two thresholds at
once and the leave-one-out folds disagreed on the line.  The remedy §8ab named is the one this program has used
before (the refinement clause of §8e, the vacancy form of §8l): IDENTIFY THE LINE ON DATA THAT HAD NO PART IN THE
AMERICAN RESULT, then apply it to the United States unchanged.

THE FOREIGN SAMPLE.  Three official monthly chronologies with a monthly housing series and a monthly unemployment
rate of their own, none of them American:

  Canada    the C.D. Howe Institute's Business Cycle Council, twelve contractions; dwelling permits from January
            1948 (FRED CANPERMITMISMEI), unemployment rate from January 1955 (LRHUTTTTCAM156S)
  Japan     the Cabinet Office (ESRI), sixteen contractions; construction work started on dwellings from January
            1955 (JPNWSCNDW01IXOBSAM), unemployment rate from January 1955 (LRHUTTTTJPM156S)
  Korea     Statistics Korea, eleven contractions; dwelling permits from January 1990 (KORPERMITMISMEI),
            unemployment rate from January 1990 (LRHUTTTTKRM156S)

THE OBJECTS, in the same scale-free form the American test used, so the lines transfer:
    HOUSING   the k-month mean, in log points, below its trailing `back`-month maximum
    LABOUR    the unemployment rate, in points, above its trailing `back`-month minimum

THE FOREIGN CRITERION, stated before it is run.  For a candidate (k, back, housing line, rate line):
    COVERAGE   the share of foreign contractions in which the pair stands at both its lines somewhere inside
               [peak - 6 months, trough] - the same window the American route gives a second condition
    EXPOSURE   the share of QUIET foreign months (outside [peak - 9 months, trough + 18 months]) at which the pair
               stands at both its lines
    SCORE      the COVERAGE, maximized SUBJECT TO the exposure being at or below 5.8 per cent - the same bound
               the American gate uses, and for the same reason (Rule 21 puts the false alarm first, and only then
               asks for speed); ties to the wider housing line, which is the more conservative clause.  The
               selection is run LEAVE-ONE-ECONOMY-OUT and LEAVE-ONE-CONTRACTION-OUT, so the line is never chosen
               on the case it is scored on.

Nothing American enters this file.  The chosen line is then handed to the American test in `intl_pair_apply.py`.

Output intl_pair_calibration.log.
"""
import sys, warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
D = '/home/claude/lab/intlpair'
log = open('/home/claude/lab/weekly/intl_pair_calibration.log', 'w')
def P(*a): print(*a); print(*a, file=log, flush=True)

CA = [('1947-08','1948-03'),('1951-04','1951-12'),('1953-07','1954-07'),('1957-03','1958-01'),
      ('1960-03','1961-03'),('1974-10','1975-03'),('1981-06','1982-10'),('1990-03','1992-05'),
      ('2008-10','2009-05'),('2020-02','2020-04')]
JP = [('1957-06','1958-06'),('1961-12','1962-10'),('1964-10','1965-10'),('1970-07','1971-12'),
      ('1973-11','1975-03'),('1977-01','1977-10'),('1980-02','1983-02'),('1985-06','1986-11'),
      ('1991-02','1993-10'),('1997-05','1999-01'),('2000-11','2002-01'),('2008-02','2009-03'),
      ('2012-03','2012-11'),('2018-10','2020-05')]
KR = [('1992-01','1993-01'),('1996-03','1998-08'),('2000-08','2001-07'),('2002-12','2005-04'),
      ('2008-01','2009-02'),('2011-08','2013-03'),('2017-09','2020-05')]
ECON = {'Canada': (CA, 'CANPERMITMISMEI', 'LRHUTTTTCAM156S'),
        'Japan':  (JP, 'JPNWSCNDW01IXOBSAM', 'LRHUTTTTJPM156S'),
        'Korea':  (KR, 'KORPERMITMISMEI', 'LRHUTTTTKRM156S')}
M = lambda s: pd.Timestamp(s + '-01')

def load(f):
    d = pd.read_csv(f'{D}/{f}.csv'); d.columns = ['d', 'v']
    return d.set_index(pd.to_datetime(d['d']))['v'].astype(float).dropna()

def pct_fall(s, k, back):
    m = (np.log(s.clip(lower=1e-9)) * 100).rolling(k).mean()
    return (m.shift(1).rolling(back).max() - m).dropna()
def lvl_rise(s, k, back):
    m = s.rolling(k).mean(); return (m - m.shift(1).rolling(back).min()).dropna()

BOOK = {}
for nm, (chron, hid, uid) in ECON.items():
    h = load(hid); u = load(uid)
    BOOK[nm] = dict(chron=chron, h=h, u=u,
                    start=max(h.index[0], u.index[0]), end=min(h.index[-1], u.index[-1]))
    reach = [c for c in chron if M(c[0]) >= BOOK[nm]['start'] + pd.DateOffset(months=15) and M(c[1]) <= BOOK[nm]['end']]
    BOOK[nm]['reach'] = reach
    P(f'{nm:8s} housing {h.index[0]:%Y-%m} to {h.index[-1]:%Y-%m}; unemployment {u.index[0]:%Y-%m} to {u.index[-1]:%Y-%m}; '
      f'{len(reach)} of {len(chron)} contractions reachable')
NC = sum(len(BOOK[n]['reach']) for n in BOOK)
P(f'the foreign calibration sample: {NC} contractions in three economies, none American.\n')

def evaluate(k, back, lh, lu, econs=None, drop=None):
    """(covered, total, exposure per cent) over the economies given"""
    cov = tot = 0; q_hit = q_all = 0
    for nm in (econs or BOOK):
        B = BOOK[nm]
        H = pct_fall(B['h'], k, back); U = lvl_rise(B['u'], k, back)
        both = ((H >= lh) & (U.reindex(H.index) >= lu)).dropna()
        if not len(both): continue
        for p, t in B['reach']:
            if drop is not None and (nm, p) == drop: continue
            tot += 1
            seg = both[M(p) - pd.DateOffset(months=6): M(t)]
            if len(seg) and bool(seg.max()): cov += 1
        q = pd.Series(True, index=both.index)
        for p, t in B['chron']:
            q[(both.index >= M(p) - pd.DateOffset(months=9)) & (both.index <= M(t) + pd.DateOffset(months=18))] = False
        q_hit += int(both[q].sum()); q_all += int(q.sum())
    return cov, tot, (q_hit / q_all * 100 if q_all else 0.0)

GRID = [(k, back, float(lh), float(lu))
        for k in (1, 2, 3) for back in (6, 12)
        for lh in np.arange(5, 45, 2.5) for lu in np.arange(0.1, 1.05, 0.05)]
P(f'{len(GRID)} candidate settings on the grid (k, back, housing line 5-42.5 log points, rate line 0.10-1.00 points).')

def best(econs=None, drop=None):
    sc = None; arg = None
    for g in GRID:
        c, t, e = evaluate(*g, econs=econs, drop=drop)
        if t == 0: continue
        if e > 5.8: continue
        s = c / t
        if sc is None or s > sc + 1e-12 or (abs(s - sc) <= 1e-12 and (g[2], g[3]) > (arg[2], arg[3])):
            sc, arg = s, g
    return arg, sc

P('\nTHE WHOLE FOREIGN SAMPLE:')
g0, s0 = best()
c, t, e = evaluate(*g0)
P(f'  best setting k={g0[0]} back={g0[1]} housing {g0[2]:.1f} log points AND rate {g0[3]:.2f} points: '
  f'coverage {c}/{t} ({c/t*100:.0f} per cent), quiet exposure {e:.2f} per cent (the gate is 5.8)')

P('\nLEAVE-ONE-ECONOMY-OUT:')
picks = []
for nm in BOOK:
    others = [x for x in BOOK if x != nm]
    g, s = best(econs=others); picks.append(g)
    c, t, e = evaluate(*g, econs=[nm])
    P(f'  leave out {nm:8s}: picks k={g[0]} back={g[1]} housing {g[2]:.1f} AND rate {g[3]:.2f}; '
      f'on the held-out economy coverage {c}/{t}, quiet exposure {e:.2f}%')
P(f'  every fold the same: {len(set(picks)) == 1} {set(picks)}')

P('\nLEAVE-ONE-CONTRACTION-OUT (all three economies, one contraction withheld at a time):')
picks2 = []
for nm in BOOK:
    for p, t_ in BOOK[nm]['reach']:
        g, s = best(drop=(nm, p)); picks2.append(g)
from collections import Counter
cnt = Counter(picks2)
P(f'  {len(picks2)} folds; distinct choices {len(cnt)}')
for g, n in cnt.most_common(6):
    P(f'    k={g[0]} back={g[1]} housing {g[2]:.1f} AND rate {g[3]:.2f}  chosen in {n} of {len(picks2)} folds')
P(f'  every fold the same: {len(cnt) == 1}')
P(f'\nTHE FOREIGN SAMPLE\'S CHOICE, to be handed to the American test unchanged: '
  f'k={cnt.most_common(1)[0][0][0]} back={cnt.most_common(1)[0][0][1]} '
  f'housing {cnt.most_common(1)[0][0][2]:.1f} log points AND rate {cnt.most_common(1)[0][0][3]:.2f} points')
log.close()
