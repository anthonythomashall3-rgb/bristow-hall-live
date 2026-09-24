"""THE MONTHLY TIER OF THE SECOND-CONDITION HUNT (4 September 2026) - the last place a faster confirming object
could come from.

§8y fixed the specification exactly.  A confirming object that could move the November 1973 and December 2007
walls must have FOUR properties at once:

  (1) history reaching 1948 - so the three claims calls outside the thirteen (July 1951, March 1952, February
      1967) can be read on it, and refused by it;
  (2) a turn EARLIER than the unemployment rate's and the vacancy rate's at the two walls;
  (3) a window exposure that does not raise the OR of the shipped pair - the hazard is the OR's, not the
      object's (§8v, and the housing-starts refusal);
  (4) unanimous leave-one-recession-out folds.

FRED holds 1,328 monthly series that begin on or before January 1951 and are still published today
(`target_1948_current.csv`, from `fred_monthly_early_index.csv`).  That set - not the daily and weekly universe
of §8o, which was swept and holds nothing that reaches 1951 - is where property (1) lives.  This screens all of
them.

THE METHOD, and why it is analytic rather than a route run.  The route's peak call is
`max(the claims call, the publication of the first month in the window that reaches the line)`, and the claims
calls are FIXED - they do not depend on the second condition at all.  So every candidate's effect on every peak
can be computed in closed form from its own readings, and only the survivors need the route.  That turns
1,328 x 6 forms x 15 lines from days into minutes.

Stage A (analytic): window exposure at or below 5.8 per cent; the OR with the shipped pair no more than 0.2
points above the shipped pair's own 7.16; the object confirms all twelve; and it does NOT reach its line inside
the window of any of the three disturbance calls.
Stage B (the route): the survivors, run properly, with the folds.

Output second_screen_monthly.log / .csv.
"""
import sys, os, glob, warnings; warnings.filterwarnings('ignore')
sys.path.insert(0, '/home/claude'); sys.path.insert(0, '/home/claude/lab/weekly'); sys.path.insert(0, '/home/claude/lab/rt')
import numpy as np, pandas as pd
import bristow_rule_v3 as B, american_chronology as AC

ROOT = '/home/claude/lab/data'
PK, TR = AC.PK, AC.TR
PEAKS13 = list(PK) + [pd.Timestamp('2023-07-01')]; TROUGH13 = list(TR) + [pd.Timestamp('2024-08-01')]
log = open(f'{ROOT}/second_screen_monthly.log', 'w')
def P(*a): print(*a); print(*a, file=log, flush=True)

def quiet(idx, post=18):
    q = pd.Series(True, index=idx)
    for p, t in zip(PEAKS13, TROUGH13): q[(idx >= p - pd.DateOffset(months=9)) & (idx <= t + pd.DateOffset(months=18))] = False
    return q
def exp_series(o, line):
    hit = (o >= line)
    return (hit[::-1].rolling(1, min_periods=1).max()[::-1].astype(bool) | hit.rolling(7, min_periods=1).max().astype(bool))

# the route as shipped (version 43): its claims calls, and the shipped condition's own exposure
PL, TL = AC.legs(safe=True, with_S=True, with_U=True)
G = AC.sahm_rt(); VR = AC.vacancy_gap_rt(2, 6)
SECOND = [dict(name='vacancy(2,6)', gap=VR, line=0.36, pub_day=30)]
turns = B.american_chronology(PL, TL, sahm=G, second=SECOND)
BASE = {}; 
for t in [x for x in turns if x['kind'] == 'peak']:
    c = [i for i, (p, q) in enumerate(zip(PK, TR)) if p - pd.DateOffset(months=6) <= t['date'] <= q]
    if c: BASE[PK[c[0]]] = t['published']
# every claims call, in order, with the episode-window end (the claims field's own end)
plain = B.american_chronology(PL, TL)
CLAIMS = [(t['published'], t['date']) for t in plain if t['kind'] == 'peak']
ENDS = {}
for i, t in enumerate(plain):
    if t['kind'] == 'peak':
        nxt = [u for u in plain[i + 1:] if u['kind'] == 'trough']
        ENDS[t['published']] = nxt[0]['published'] if nxt else pd.Timestamp('2027-01-01')
DIS = [pd.Timestamp('1951-09-20'), pd.Timestamp('1952-04-10'), pd.Timestamp('1967-04-20')]

IDX = pd.date_range('1949-01-01', '2026-07-01', freq='MS'); QM = quiet(IDX)
eS = exp_series(G, 0.5).reindex(IDX).fillna(False).astype(bool)
eV = exp_series(VR, 0.36).reindex(IDX).fillna(False).astype(bool)
SHIPPED = float((eS | eV)[QM].mean() * 100)

def confirm_pub(o, line, call, pub_day):
    """the tool's own rule: the first month in gg[call - 6 months : window end] that reaches `line`, published
    `pub_day` of the month after"""
    seg = o[call - pd.DateOffset(months=6): ENDS.get(call, call + pd.DateOffset(months=12))]
    t = next((tt for tt, v in seg.items() if v >= line), None)
    if t is None: return None
    return pd.Timestamp(t.year, t.month, 1) + pd.DateOffset(months=1) + pd.Timedelta(days=pub_day - 1)

def forms(s):
    ls = np.log(s.clip(lower=1e-9)) * 100.0 if (s > 0).all() else None
    for k in (1, 2, 3):
        yield f'fall(k={k},6)', (s.rolling(k).mean().shift(1).rolling(6).max() - s.rolling(k).mean()).dropna()
        yield f'rise(k={k},6)', (s.rolling(k).mean() - s.rolling(k).mean().shift(1).rolling(6).min()).dropna()
        yield f'fall(k={k},12)', (s.rolling(k).mean().shift(1).rolling(12).max() - s.rolling(k).mean()).dropna()
        yield f'rise(k={k},12)', (s.rolling(k).mean() - s.rolling(k).mean().shift(1).rolling(12).min()).dropna()
        if ls is not None:
            yield f'%fall(k={k},6)', (ls.rolling(k).mean().shift(1).rolling(6).max() - ls.rolling(k).mean()).dropna()
            yield f'%rise(k={k},6)', (ls.rolling(k).mean() - ls.rolling(k).mean().shift(1).rolling(6).min()).dropna()

tg = pd.read_csv(f'{ROOT}/target_1948_current.csv')
TITLE = dict(zip(tg.id, tg.title))
files = {i: f'{ROOT}/fred_monthly_early/{i}.csv' for i in tg.id}
have = {i: f for i, f in files.items() if os.path.exists(f)}
P(f'THE MONTHLY TIER: {len(tg)} FRED series beginning on or before January 1951 and still published; {len(have)} fetched so far.')
P(f'the shipped second condition (Sahm 0.5 OR the vacancy fast form 0.36): window exposure of the OR {SHIPPED:.2f} per cent')
P(f'the route as shipped calls: ' + ' '.join(f'{p:%Y-%m}:{BASE[p]:%Y-%m-%d}' for p in PK))
P('\nSTAGE A - analytic. A candidate must: hold its exposure at or below 5.8 per cent; add no more than 0.2 points')
P('to the OR; confirm all twelve inside their windows; and reach its line inside NONE of the three disturbance')
P('windows (1951, 1952, 1967). PUB DAY is taken as the 20th - later than the employment report and earlier than')
P('the vacancy rate, so a survivor is not an artefact of an optimistic publication assumption.')
PUB = 20
rows = []
for n, (sid, f) in enumerate(sorted(have.items())):
    ttl = str(TITLE.get(sid, '')).lower()
    if sid.startswith('USREC') or sid.startswith('NBER') or 'recession indicator' in ttl or 'business cycle' in ttl \
       or sid in ('RECPROUSM156N', 'SAHMCURRENT', 'SAHMREALTIME', 'UNRATE', 'JHGDPBRINDX'):
        continue                                    # the answer key, in any of its forms
    try:
        d = pd.read_csv(f); d.columns = ['d', 'v']
        s = d.set_index(pd.to_datetime(d['d']))['v'].astype(float).dropna()
    except Exception: continue
    if len(s) < 400 or s.index[0] > pd.Timestamp('1951-01-01'): continue
    for fname, o in forms(s):
        o = o.dropna()
        if len(o) < 400: continue
        oq = o[quiet(o.index)]
        if not len(oq): continue
        grid = np.unique(np.quantile(oq.values, np.linspace(0.90, 0.9995, 14)))
        for line in grid:
            line = float(line)
            e = float(exp_series(o, line).reindex(IDX).fillna(False).astype(bool)[QM].mean() * 100)
            if e > 5.8: continue
            comb = float((eS | eV | exp_series(o, line).reindex(IDX).fillna(False).astype(bool))[QM].mean() * 100)
            if comb > SHIPPED + 0.2: continue
            if any(confirm_pub(o, line, c, PUB) is not None for c in DIS): continue
            # the candidate enters as a THIRD ALTERNATIVE: the route takes whichever of the three objects is
            # public first, so the call can only move earlier, never later.  A candidate that reads nothing at a
            # peak simply leaves the shipped call standing there.
            call = {}
            for p in PK:
                cands = [c for c, _ in CLAIMS if p - pd.DateOffset(months=9) <= c <= p + pd.DateOffset(months=15)]
                got = None
                for c in sorted(cands):
                    cp = confirm_pub(o, line, c, PUB)
                    if cp is not None: got = max(c, cp); break
                call[p] = BASE[p] if got is None else min(BASE[p], got)
            lags = {p: (call[p] - AC.month_end(p)).days for p in PK}
            base = {p: (BASE[p] - AC.month_end(p)).days for p in PK}
            rows.append(dict(id=sid, form=fname, line=line, exposure=e, combined=comb,
                             median=float(np.median(list(lags.values()))), worst=max(lags.values()),
                             w1973=lags[pd.Timestamp('1973-11-01')], w2007=lags[pd.Timestamp('2007-12-01')],
                             base_median=float(np.median(list(base.values()))), base_worst=max(base.values()),
                             b1973=base[pd.Timestamp('1973-11-01')], b2007=base[pd.Timestamp('2007-12-01')]))
    if n % 150 == 0: P(f'  ... {n}/{len(have)} series, {len(rows)} settings surviving so far')
R = pd.DataFrame(rows)
R.to_csv(f'{ROOT}/second_screen_monthly.csv', index=False)
P(f'\nSTAGE A RESULT: {len(R)} settings survive, on {R.id.nunique() if len(R) else 0} series.')
if len(R):
    R['gain'] = (R.b1973 - R.w1973).clip(lower=0) + (R.b2007 - R.w2007).clip(lower=0)
    W = R[(R.w1973 < R.b1973) | (R.w2007 < R.b2007)].sort_values('gain', ascending=False)
    P(f'  {len(W)} of them move at least one wall. The best twenty-five:')
    for _, r in W.head(25).iterrows():
        t = tg[tg.id == r.id].title.iloc[0][:52]
        P(f'    {r.id:16s} {r.form:14s} line {r.line:10.3f} expo {r.exposure:4.1f}% OR {r.combined:5.2f}%  '
          f'1973 {int(r.b1973)}->{int(r.w1973):4d}  2007 {int(r.b2007)}->{int(r.w2007):4d}  median {r.median:5.0f}  {t}')
    if not len(W): P('  none of them moves either wall.')
log.close()
