"""The speed frontier under Rule 21 (4 September 2026): what would make the route faster, and what each candidate
costs in future risk.

Anthony: "is there anything truly beneficial that would speed us up without adding too much risk of false alarms or
failure - anything from the other chat - make sure the speed is worth the decline in accuracy."

The route's design decides where speed is cheap.  A peak call needs a CLAIMS object at its line AND the second
condition inside the window.  So:

  * a new CLAIMS leg raises only P(a claims call in a quiet year); the second condition still has to confirm it, and
    the hazard is multiplied by 0.009 to 0.065 (the window exposure of window_exposure.py).  Cheap.
  * a new SECOND-CONDITION object raises the multiplier itself.  Expensive - which is why the 5-year yield (23.6 per
    cent) and the Baa rise (48.3) were refused in memo 8o.

This script prices the cheap side.  Candidates, all weekly and all in the claims family the route already reads:

  IUR   the insured unemployment rate (FRED IURSA, 1971-), four-week mean `x` points above its 52-week minimum -
        the Paper 2 chat's v7 channel (its line 0.40; its margin 2.4 standard deviations)
  CC6   continued claims, six-month log change (the screen's own winner in memo 8o: nine of nine since 1969 at the
        quiet ceiling, median 14 days) - on the route's real-time seasonal factors
  IC4   initial claims, four-week mean `x` log points above its 52-week minimum (Hester's object in the route's units)

Each is run as an EXTRA PEAK LEG in the version-39 route: the twelve's lags, the calls the route then makes outside
the thirteen, and the count of quiet-year claims calls the leg itself would add (the hazard input).  Output
speed_frontier.log.
"""
import sys, warnings; warnings.filterwarnings('ignore')
sys.path.insert(0, '/home/claude'); sys.path.insert(0, '/home/claude/lab/weekly')
import numpy as np, pandas as pd
import bristow_rule_v3 as B, american_chronology as AC

PK = AC.PK; TR = AC.TR
log = open('/home/claude/lab/weekly/speed_frontier.log', 'w')
def P(*a): print(*a); print(*a, file=log, flush=True)

PL, TL = AC.legs(safe=True, with_S=True)
g = AC.sahm_rt(); vr = AC.vacancy_gap_rt(2, 6)
SECOND = [dict(name='vacancy(2,6)', gap=vr, line=0.36, pub_day=30)]

def report(peak_legs, label):
    turns = B.american_chronology(peak_legs, TL, sahm=g, second=SECOND)
    pk = [t for t in turns if t['kind'] == 'peak']
    rows = []; other = []
    for t in pk:
        c = [i for i, (p, q) in enumerate(zip(PK, TR)) if p - pd.DateOffset(months=6) <= t['date'] <= q]
        if c: rows.append((PK[c[0]], (t['published'] - AC.month_end(PK[c[0]])).days, t['leg']))
        else: other.append(f"{t['published']:%Y-%m-%d}({t['leg']})")
    lags = [r[1] for r in rows]
    P(f'  {label}')
    P(f'    peaks {len(rows)}/{len(PK)}  median {np.median(lags):.0f} d  within a month {sum(l <= 30 for l in lags)}  worst {max(lags)}  other calls {other}')
    P('    ' + ' '.join(f'{p:%Y-%m}:{l:+d}[{lg}]' for p, l, lg in rows))
    return {p: l for p, l, _ in rows}

# ---- the candidates -------------------------------------------------------
iur = pd.read_csv('/home/claude/archive/data/fred/IURSA.csv'); iur.columns = ['d', 'v']
iur = iur.set_index(pd.to_datetime(iur['d']))['v'].astype(float)
N = pd.read_csv('/home/claude/lab/weekly/DOL_national_weekly_claims_sa_rt.csv', index_col=0, parse_dates=True)
cc_rt = np.log(N['cc_sa_rt']) * 100.0
ic_rt = np.log(N['ic_sa_rt']) * 100.0

def gap_calls(s, line, weeks_back=52, quiet=26, pub_days=5, smooth=4):
    """the leg's calls: the first week a `smooth`-week mean stands `line` above its trailing minimum, after `quiet`
    quiet weeks; published `pub_days` after the week; dated to the month of that week"""
    m = s.rolling(smooth).mean(); gap = (m - m.rolling(weeks_back, min_periods=26).min()).dropna()
    out = []; below = 0
    for t, v in gap.items():
        if v >= line:
            if below >= quiet: out.append((t + pd.Timedelta(days=pub_days), pd.Timestamp(t.year, t.month, 1)))
            below = 0
        else: below += 1
    return out

def chg_calls(s, line, months=6, quiet=26, pub_days=5):
    w = int(round(4.33 * months)); gap = (s - s.shift(w)).dropna()
    out = []; below = 0
    for t, v in gap.items():
        if v >= line:
            if below >= quiet: out.append((t + pd.Timedelta(days=pub_days), pd.Timestamp(t.year, t.month, 1)))
            below = 0
        else: below += 1
    return out

def quiet_extra(calls, label):
    """how many of the leg's own calls fall outside [peak-9m, trough+18m] of the thirteen - the hazard input"""
    ex = []
    for pub, d in calls:
        inside = any(AC.M(p) - pd.DateOffset(months=9) <= pub <= AC.M(q) + pd.DateOffset(months=18) for p, q in zip(PK, TR)) if hasattr(AC, 'M') else \
                 any(pd.Timestamp(p) - pd.DateOffset(months=9) <= pub <= pd.Timestamp(q) + pd.DateOffset(months=18) for p, q in zip(PK, TR))
        if not inside: ex.append(f'{pub:%Y-%m-%d}')
    P(f'    {label}: {len(calls)} calls, {len(ex)} in quiet periods {ex}')
    return len(ex)

P('THE ROUTE AS SHIPPED (version 39)')
base = report(PL, 'route B'' + leg S')

P('\nCANDIDATE LEGS (each added to the peak side; the second condition is unchanged and still guards every call)')
cands = {}
for line in (0.30, 0.40, 0.50):
    cands[f'IUR {line:.2f} pp (1971-)'] = gap_calls(iur, line, smooth=4, pub_days=5)
for line in (10, 15, 20):
    cands[f'CC six-month change {line} log points (real-time factors, 1969-)'] = chg_calls(cc_rt, line, 6, pub_days=5)
for line in (25, 30, 40):
    cands[f'IC four-week mean {line} log points over its 52-week low (1969-)'] = gap_calls(ic_rt, line, smooth=4, pub_days=5)

for name, calls in cands.items():
    P(f'\n{name}')
    n_extra = quiet_extra(calls, 'the leg alone')
    lags = report({**PL, 'X': calls}, f'route + [{name}]')
    faster = {p: base[p] - lags[p] for p in lags if p in base and lags[p] < base[p]}
    P(f'    speed gained (days, per peak): {faster if faster else "none"}')
log.close()
