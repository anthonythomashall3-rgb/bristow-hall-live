"""The walls, tried against every daily and weekly object the sweep holds (3 September 2026, night, fifth pass).

The route's three onset walls are 1973 (120 d), 2007 (126 d) and 1981 (142 d); 2007's is the second
condition (the rate's crossing in April 2008).  screen.py ranked every object of every fetched series at
the sixteen claims calls (the veto read) and at the thirteen peaks (the quiet-ceiling read).  Here the
candidates that survive the screen's cuts - history to 1951 (all three disturbances read), a positive
margin at the calls, and an exposure on quiet days below EXPO per cent - are rebuilt and run INSIDE the
route as a third second-condition object beside the rate and the vacancy rate, read on their own dates
and public `pub_lag_days` after each reading; the line is the midpoint between the disturbances' ceiling
and the recessions' floor at the calls (the screen's line), and a leave-one-out pass sets the line
without each recession in turn and reads that recession's crossing.  Output walls.log.

    python3 walls.py [EXPO=10] [freq list: daily,weekly,biweekly,other_daily,other_weekly]
"""
import sys, os, warnings; warnings.filterwarnings('ignore')
sys.path.insert(0, '/home/claude'); sys.path.insert(0, '/home/claude/lab/weekly')
import numpy as np, pandas as pd
import bristow_rule_v3 as B, american_chronology as AC
import importlib.util
spec = importlib.util.spec_from_file_location('screen_defs', '/home/claude/lab/data/screen.py')
ROOT = '/home/claude/lab/data'
EXPO = float(sys.argv[1]) if len(sys.argv) > 1 else 10.0
MIN_DIS = int(sys.argv[3]) if len(sys.argv) > 3 else 3     # 3 = all three disturbances read; 1 = partials (1967 only) too
FREQS = sys.argv[2].split(',') if len(sys.argv) > 2 else ['daily', 'weekly', 'biweekly', 'other_daily', 'other_weekly']
LAG = {'daily': 1, 'weekly': 7, 'biweekly': 7, 'other_daily': 1, 'other_weekly': 7}

# the screen's object definitions, re-implemented here (screen.py runs on import)
PER = {'daily': 21, 'weekly': 4.33, 'biweekly': 2.17}
def objects(x, units, freq):
    W = {m: int(round(PER[freq.replace('other_', '')] * m)) for m in (1, 3, 6, 12)}
    out = {}
    positive = (x > 0).all() and not any(k in str(units).lower() for k in ('%', 'percent', 'per cent', 'rate', 'ratio', 'index', 'points', 'basis', 'spread', 'yield'))
    base = np.log(x) * 100 if positive else x
    for m, w in W.items(): out[f'chg{m}m'] = base - base.shift(w)
    if positive:
        out['dd12m'] = (x / x.rolling(W[12], min_periods=int(W[12] * 0.8)).max() - 1) * 100
        out['up12m'] = (x / x.rolling(W[12], min_periods=int(W[12] * 0.8)).min() - 1) * 100
    out['lvl-mean12m'] = x - x.rolling(W[12], min_periods=int(W[12] * 0.8)).mean()
    out['level'] = x
    return out

def load_series(freq, row):
    D = f'{ROOT}/{freq}' if freq.startswith('other_') else f'{ROOT}/fred_{freq}'
    if freq.startswith('other_'):
        f, c = row['id'].split(':', 1)
        s = pd.to_numeric(pd.read_csv(f'{D}/{f}.csv', index_col=0, parse_dates=True)[c], errors='coerce')
        units = ''
    else:
        s = pd.read_csv(f'{D}/{row["id"]}.csv', index_col=0, parse_dates=True)['value']
        idx = pd.read_csv(f'{D}/_INDEX.csv') if os.path.exists(f'{D}/_INDEX.csv') else pd.read_csv(f'{ROOT}/fred_{freq}_index.csv')
        units = idx.set_index('id').loc[row['id'], 'units']
    s = s.dropna().astype(float); s = s[~s.index.duplicated()].sort_index()
    return s, units

CALLS = [('1948-12-10', 'R'), ('1951-09-20', 'D'), ('1952-04-10', 'D'), ('1953-09-20', 'R'), ('1957-08-20', 'R'), ('1960-02-20', 'R'), ('1967-04-20', 'D'),
         ('1970-01-31', 'R'), ('1974-02-16', 'R'), ('1980-03-20', 'R'), ('1981-12-20', 'R'), ('1990-09-20', 'R'), ('2001-03-31', 'R'), ('2007-12-28', 'R'),
         ('2020-03-28', 'R'), ('2023-08-28', 'R')]
def read_at(o, day, how, kind='R'):
    """the screen's reads: 'call' = the value in hand on the call day; 'win' = the extreme over the route's window
    (six months before the call to thirty days after it for a recession, six months after for a disturbance)"""
    d = pd.Timestamp(day); seg = o[:d].dropna()
    if seg.empty or (d - seg.index[-1]).days > 45: return None
    if how == 'call': return float(seg.iloc[-1])
    w = o[d - pd.DateOffset(months=6): d + (pd.Timedelta(days=30) if kind == 'R' else pd.DateOffset(months=6))].dropna()
    return None if w.empty else float(w.max())

log = open(f'{ROOT}/walls.log', 'w')
def P(*a):
    print(*a); print(*a, file=log, flush=True)

PL, TL = AC.legs(safe=True, with_S=True); g = AC.sahm_rt(); vr = AC.vacancy_gap_rt(2, 6)
base_second = [dict(name='vacancy(2,6)', gap=vr, line=0.36, pub_day=30)]
def run(second, label, with_rate=True):
    turns = B.american_chronology(PL, TL, sahm=g if with_rate else None, second=second)
    pk = [t for t in turns if t['kind'] == 'peak']
    rows = []; other = []
    for t in pk:
        c = [i for i, (p, q) in enumerate(zip(AC.PK, AC.TR)) if p - pd.DateOffset(months=6) <= t['date'] <= q]
        if c: rows.append((AC.PK[c[0]], (t['published'] - AC.month_end(AC.PK[c[0]])).days, t.get('condition', 'Sahm')))
        else: other.append(t['published'].strftime('%Y-%m-%d'))
    lags = [r[1] for r in rows]
    P(f'  {label}: peaks {len(rows)}/{len(AC.PK)}, median {np.median(lags):.0f} d, within a month {sum(l <= 30 for l in lags)}, worst {max(lags)}; other onset calls {other}')
    P('     ' + ' '.join(f'{p:%Y-%m}:{l:+d}{"*" if c not in ("Sahm", "vacancy(2,6)") else ""}' for p, l, c in rows))
    return rows

P('the default (version 39) for reference:')
run(base_second, 'route B'' + S')

cands = []
for freq in FREQS:
    f = f'{ROOT}/screen_{freq}.csv'
    if not os.path.exists(f): continue
    df = pd.read_csv(f)
    if 'veto_dis' not in df: continue
    c = df[(df.veto_dis >= MIN_DIS) & (df.veto_margin > 0) & (df.veto_exposure < EXPO)].copy(); c['freq'] = freq
    cands.append(c)
cands = pd.concat(cands) if cands else pd.DataFrame()
P(f'\ncandidates surviving the screen ({"all three disturbances read" if MIN_DIS == 3 else "PARTIALS ADMITTED - 1967 read, 1951 and 1952 not"}, margin > 0, exposure < {EXPO} per cent): {len(cands)}')
if len(cands):
    P(cands[['freq', 'id', 'title', 'start', 'object', 'veto_dis', 'veto_sign', 'veto_margin', 'veto_line', 'veto_exposure']].to_string(index=False))
for _, r in cands.sort_values('veto_margin', ascending=False).iterrows():
    s, units = load_series(r.freq, r)
    o = (r.veto_sign * objects(s, units, r.freq)[r.object]).dropna()
    P(f"\n--- {r.id} [{r.object}, sign {r.veto_sign:+.0f}, the window read] {str(r.title)[:70]}")
    # leave-one-out lines
    reads = {day: read_at(o, day, 'win', k) for day, k in CALLS}
    dis = [reads[d] for d, k in CALLS if k == 'D' and reads[d] is not None]
    recs = {d: reads[d] for d, k in CALLS if k == 'R' and reads[d] is not None}
    ceil = max(dis); lines = []
    for d in recs:
        floor = min(v for dd, v in recs.items() if dd != d); ln = (ceil + floor) / 2
        seg = o[pd.Timestamp(d) - pd.DateOffset(months=6): pd.Timestamp(d) + pd.DateOffset(months=18)]; h = seg[seg >= ln]
        lines.append((d, round(ln, 4), None if h.empty else h.index[0].strftime('%Y-%m-%d')))
    P('  leave-one-out: line without each recession, and that recession\'s first crossing after the claims call: ' + '; '.join(f'{d[:4]} {ln} -> {x}' for d, ln, x in lines))
    ln = float(r.veto_line)
    run(base_second + [dict(name=r.id, gap=o, line=ln, pub_day=0, pub_lag_days=LAG[r.freq])], f'route with {r.id} as a third second-condition object at {ln:.4g} (public {LAG[r.freq]} d after the reading)')
    run([dict(name=r.id, gap=o, line=ln, pub_day=0, pub_lag_days=LAG[r.freq])], f'{r.id} ALONE as the second condition', with_rate=False)
log.close()
