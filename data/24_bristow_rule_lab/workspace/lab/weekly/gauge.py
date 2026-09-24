"""The recession gauge - Anthony's question of 4 September 2026: "Should our tool be a % of recession taking place in the
current moment? If we do take this route, when there is a recession it MUST say 100% chance, and the % always accurate."

The route's ruling is a state: closed or open (one call, one date).  A percentage can only be a WATCH beside it: the
calibrated probability that the machine opens within the next three months, read from where the route's own objects
stand against their lines.  Readiness r = min( max(A's diffusion / 50, M's conjunct / 0.20), max(Sahm gap / 0.5, vacancy
fast form / 0.36) ), clipped to [0, 1] - the claims condition AND the second condition, each at the nearer of its two
objects, monthly, on the real-time series the route reads.  "Accurate" is calibration: in every bin of r the realized
frequency of an opening within three months must equal the bin's stated probability, on the record 1949-2026.
The table below is that test, with the Brier score; the last section shows r in the six months before each of the
thirteen calls and at the committee's peak month - the answer to "100% when there is a recession".  Output gauge.log.
"""
import sys, warnings; warnings.filterwarnings('ignore')
sys.path.insert(0, '/home/claude'); sys.path.insert(0, '/home/claude/lab/weekly')
import numpy as np, pandas as pd, bristow_rule_v3 as B
import american_chronology as AC, legs_1948 as L
log = open('/home/claude/lab/weekly/gauge.log', 'w')
def P(*a): print(*a); print(*a, file=log)

# the objects, monthly, as the route reads them
Pn = pd.read_csv('/home/claude/lab/fh/FH_state_claims_sa_rt_log.csv', index_col=0, parse_dates=True)
D = B.claims_diffusion(Pn.rolling(2).mean().dropna(how='all'), 36., 8)            # leg A's index, per cent; line 50
ic, cc = L.national_nsa(); c = B.claims_conjunct(ic, cc, weeks=12, smooth=1)       # leg M's conjunct (weekly series); line 0.20
cm = c.resample('MS').max()                                                         # the month's highest weekly reading
g = AC.sahm_rt(); v = AC.vacancy_gap_rt(2, 6)
idx = pd.date_range('1949-01-01', '2026-08-01', freq='MS')
def al(s): return s.reindex(idx)
a = al(D) / 50.0; m = al(cm) / 0.20; s = al(g) / 0.5; vv = al(v) / 0.36
claims = pd.concat([a, m], axis=1).max(axis=1); second = pd.concat([s, vv], axis=1).max(axis=1)
r = pd.concat([claims, second], axis=1).min(axis=1).clip(0, 1)
# the route's own openings (version 39)
PL, TL = AC.legs(safe=True, with_S=True)
turns = B.american_chronology(PL, TL, sahm=g, second=[dict(name='vacancy(2,6)', gap=v, line=0.36, pub_day=30)])
opens = sorted(t['published'] for t in turns if t['kind'] == 'peak')
closes = sorted(t['published'] for t in turns if t['kind'] == 'trough')
def state_open(t):
    o = [p for p in opens if p <= t];
    if not o: return False
    last = max(o); cl = [q for q in closes if q > last]
    return not cl or min(cl) > t
# outcome: an opening published within three months after the month's data are public (the 20th of the month after)
rows = []
for t in idx:
    pub = pd.Timestamp(t.year, t.month, 1) + pd.DateOffset(months=1) + pd.Timedelta(days=19)
    if state_open(pub): continue                                                   # the machine is open: the state is the answer, 100
    y = any(pub < p <= pub + pd.DateOffset(months=3) for p in opens)
    rows.append(dict(month=t, r=r.get(t, np.nan), y=int(y), claims=claims.get(t, np.nan), second=second.get(t, np.nan)))
df = pd.DataFrame(rows).dropna(subset=['r'])
P('THE GAUGE - readiness r (0 to 1) on the closed months of the record, and whether the machine opened within three months')
P(f'closed months read: {len(df)}; openings within three months of a reading: {int(df.y.sum())} readings')
bins = [-0.001, 0.3, 0.5, 0.7, 0.85, 0.999, 1.0]
labels = ['0-0.3', '0.3-0.5', '0.5-0.7', '0.7-0.85', '0.85-1', '1.0 (both conditions at their lines, call pending)']
df['bin'] = pd.cut(df.r, bins, labels=labels)
P('\nCALIBRATION - the share of readings in each bin followed by an opening within three months (the frequency the gauge must state to be "accurate")')
P('  bin                                              readings   opened within 3 months   frequency')
for b, gdf in df.groupby('bin', observed=False):
    P(f'  {str(b):48s} {len(gdf):8d}   {int(gdf.y.sum()):22d}   {gdf.y.mean() * 100 if len(gdf) else float("nan"):6.1f}%')
# a calibrated gauge: the bin frequencies themselves; Brier against a flat rate
freq = df.groupby('bin', observed=False).y.mean(); df['p'] = df.bin.map(freq).astype(float)
brier = ((df.p - df.y) ** 2).mean(); base = ((df.y.mean() - df.y) ** 2).mean()
P(f'\nBrier score of the calibrated gauge {brier:.4f} against the flat base rate {base:.4f} ({df.y.mean() * 100:.1f}% of closed months open within three months)')
P('\nTHE THIRTEEN - r in the six months before each opening, then the reading for the committee\'s peak month (the "100% when there is a recession" test)')
PK = ['1948-11', '1953-07', '1957-08', '1960-04', '1969-12', '1973-11', '1980-01', '1981-07', '1990-07', '2001-03', '2007-12', '2020-02', '2023-07']
for p in opens:
    pk = [k for k in PK if pd.Timestamp(k + '-01') - pd.DateOffset(months=6) <= p <= pd.Timestamp(k + '-01') + pd.DateOffset(months=9)]
    pkm = pd.Timestamp(pk[0] + '-01') if pk else None
    seg = r[p - pd.DateOffset(months=7): p]
    path = ' '.join(f'{x:.2f}' for x in seg.values[-7:])
    atpk = f'{r.get(pkm, np.nan):.2f}' if pkm is not None else '-'
    P(f'  opening {p:%Y-%m-%d} (peak {pk[0] if pk else "none"}): r over the seven months to the call: {path} | r in the peak month: {atpk}')
P('\nREADING. Only the open state is 100: the gauge on the peak month is the objects\' distance to their lines, and in the recessions the claims')
P('field carried late (1973, 1981) it is far below one there. A percentage "always accurate" is the calibration table, not a promise of 100 at the onset.')
log.close()
