"""The generic screen (3 September 2026): every fetched daily, weekly and biweekly series, read two ways.

    python3 screen.py daily|weekly|biweekly      -> screen_<freq>.csv, screen_<freq>.log

VETO (the second condition's job): at each of the sixteen claims calls since 1948 - thirteen recessions
(2023 counted, as Anthony instructs) and the three disturbances 1951, 1952, 1967 - read each object at
the call day and its extreme within thirty days after.  Does a line separate the recessions read from
the disturbances read?  The margin is (weakest recession - strongest disturbance) in units of the
object's own standard deviation; a series must reach all three disturbances (history from 1951) to be
a full candidate; one reaching only 1967 is a partial.

SPEED (a call object's job): the object's quiet ceiling - the largest value it attained on any day
outside [peak - 9 months, trough + 6 months] of the thirteen since 1948 - is the line it never crossed
in quiet times over its own history; at that line, the first crossing inside [peak - 6 months, trough]
of each recession the history covers, in days after the peak month's end.  Reported: coverage, median
and worst lag, days within a month (<= 30 d after the peak month's end), and the history start (a short
history has a low ceiling: the ceiling of a series from 1990 rests on 25 quiet years, from 1954 on 60).

Objects per series X (both signs, so a fall is read as the rise of -X):
    change over 1, 3, 6, 12 months (log change for positive level series; difference for rates, spreads,
    indexes in per cent, and anything with a non-positive value); drawdown from the trailing-year maximum
    and rise from the trailing-year minimum (positive series); level less its trailing-year mean.
"""
import sys, os, warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd

FREQ = sys.argv[1]
ROOT = '/home/claude/lab/data'
OTHER = FREQ.startswith('other_')          # other_daily / other_weekly: the non-FRED files, every numeric column a series
D = f'{ROOT}/{FREQ}' if OTHER else f'{ROOT}/fred_{FREQ}'
if OTHER:
    rows_ = []
    for f in sorted(os.listdir(D)):
        if not f.endswith('.csv') or f.startswith('_'): continue
        cols = pd.read_csv(f'{D}/{f}', index_col=0, nrows=5).columns
        for c in cols: rows_.append(dict(id=f'{f[:-4]}:{c}', title=f'{f[:-4]} {c}', units='', file=f, col=c))
    idx = pd.DataFrame(rows_)
else:
    idx = pd.read_csv(f'{D}/_INDEX.csv') if os.path.exists(f'{D}/_INDEX.csv') else pd.read_csv(f'{ROOT}/fred_{FREQ}_index.csv')
if len(sys.argv) > 2: idx = idx[idx.id.isin(sys.argv[2].split(','))]
PER_MONTH = {'daily': 21, 'weekly': 4.33, 'biweekly': 2.17}[FREQ.replace('other_', '')]
W = {m: int(round(PER_MONTH * m)) for m in (1, 3, 6, 12)}

CALLS = [('1948-12-10', 'R', '1948-11'), ('1951-09-20', 'D', '1951'), ('1952-04-10', 'D', '1952'), ('1953-09-20', 'R', '1953-07'),
         ('1957-08-20', 'R', '1957-08'), ('1960-02-20', 'R', '1960-04'), ('1967-04-20', 'D', '1967'), ('1970-01-31', 'R', '1969-12'),
         ('1974-02-16', 'R', '1973-11'), ('1980-03-20', 'R', '1980-01'), ('1981-12-20', 'R', '1981-07'), ('1990-09-20', 'R', '1990-07'),
         ('2001-03-31', 'R', '2001-03'), ('2007-12-28', 'R', '2007-12'), ('2020-03-28', 'R', '2020-02'), ('2023-08-28', 'R', '2023-07')]
PEAKS = ['1948-11', '1953-07', '1957-08', '1960-04', '1969-12', '1973-11', '1980-01', '1981-07', '1990-07', '2001-03', '2007-12', '2020-02', '2023-07']
TROUGHS = ['1949-10', '1954-05', '1958-04', '1961-02', '1970-11', '1975-03', '1980-07', '1982-11', '1991-03', '2001-11', '2009-06', '2020-04', '2024-08']
M = lambda s: pd.Timestamp(s + '-01')

def objects(x, units):
    """the transformations of one series (a float Series on its own dates)"""
    out = {}
    positive = (x > 0).all() and not any(k in str(units).lower() for k in ('%', 'percent', 'per cent', 'rate', 'ratio', 'index', 'points', 'basis', 'spread', 'yield'))
    base = np.log(x) * 100 if positive else x
    for m, w in W.items():
        out[f'chg{m}m'] = base - base.shift(w)
    if positive:
        out['dd12m'] = (x / x.rolling(W[12], min_periods=int(W[12] * 0.8)).max() - 1) * 100
        out['up12m'] = (x / x.rolling(W[12], min_periods=int(W[12] * 0.8)).min() - 1) * 100
    out['lvl-mean12m'] = x - x.rolling(W[12], min_periods=int(W[12] * 0.8)).mean()
    out['level'] = x
    return out

def at(s, day):
    seg = s[:day].dropna(); return None if seg.empty or (day - seg.index[-1]).days > 45 else float(seg.iloc[-1])

def veto(o):
    """separation at the sixteen calls, both signs; two reads - 'call' (the value in hand on the call day) and 'win'
    (the route's own read: a recession must reach the line between six months before its claims call and thirty
    days after it; a disturbance must not reach it anywhere between six months before and six months after its
    call - the window the state machine actually scans); returns the best (margin, sign, read, coverage, line, exposure)"""
    best = {}
    sd = float(o.std())
    if not sd or np.isnan(sd): return None
    at_call = {}; hi_r = {}; lo_r = {}; hi_d = {}; lo_d = {}
    for day, kind, what in CALLS:
        d = pd.Timestamp(day); v = at(o, d)
        if v is None: continue
        at_call[what] = v
        seg = o[d - pd.DateOffset(months=6): d + (pd.Timedelta(days=30) if kind == 'R' else pd.DateOffset(months=6))].dropna()
        if seg.empty: continue
        if kind == 'R': hi_r[what] = float(seg.max()); lo_r[what] = float(seg.min())
        else: hi_d[what] = float(seg.max()); lo_d[what] = float(seg.min())
    for rd in ('call', 'win'):
        if rd == 'call':
            dis = [at_call[w] for _, k, w in CALLS if k == 'D' and w in at_call]; rec = [at_call[w] for _, k, w in CALLS if k == 'R' and w in at_call]
            if len(dis) == 0 or len(rec) < 6: continue
            for sign in (1, -1):
                r = [sign * v for v in rec]; q = [sign * v for v in dis]
                margin = (min(r) - max(q)) / sd; ln = (min(r) + max(q)) / 2
                cand = (margin, sign, rd, len(dis), len(rec), ln)
                if rd not in best or cand[0] > best[rd][0]: best[rd] = cand
        else:
            if len(hi_d) == 0 or len(hi_r) < 6: continue
            for sign in (1, -1):
                r = [hi_r[w] for w in hi_r] if sign == 1 else [-lo_r[w] for w in lo_r]
                q = [hi_d[w] for w in hi_d] if sign == 1 else [-lo_d[w] for w in lo_d]
                margin = (min(r) - max(q)) / sd; ln = (min(r) + max(q)) / 2
                cand = (margin, sign, rd, len(hi_d), len(hi_r), ln)
                if rd not in best or cand[0] > best[rd][0]: best[rd] = cand
    if not best: return None
    o48 = o['1948':]
    quiet = pd.Series(True, index=o48.index)
    for p, q in zip(PEAKS, TROUGHS):
        quiet[(o48.index >= M(p) - pd.DateOffset(months=9)) & (o48.index <= M(q) + pd.DateOffset(months=6))] = False
    out = {}
    for rd, b in best.items():
        # exposure: the share of quiet days since 1948 on which sign*object is at or above the separating line
        expo = float(((b[1] * o48)[quiet] >= b[5]).mean() * 100) if quiet.sum() else float('nan')
        out[rd] = b + (expo,)
    return out

def speed(o):
    """quiet ceiling and lags, both signs; returns the sign with the better (coverage, median lag)"""
    best = None
    o = o.dropna()
    if o.empty or o.index[0] > pd.Timestamp('2005-12-31'): return best
    o48 = o['1948':]
    quiet = pd.Series(True, index=o48.index)
    for p, q in zip(PEAKS, TROUGHS):
        quiet[(o48.index >= M(p) - pd.DateOffset(months=9)) & (o48.index <= M(q) + pd.DateOffset(months=6))] = False
    if quiet.sum() < 100: return best
    for sign in (1, -1):
        s = sign * o48; ceiling = float(s[quiet].max())
        lags = {}
        for p, q in zip(PEAKS, TROUGHS):
            seg = s[M(p) - pd.DateOffset(months=6): M(q) + pd.offsets.MonthEnd(0)]
            if seg.empty or seg.index[0] > M(p): continue        # history must be there before the peak
            h = seg[seg > ceiling]
            lags[p] = None if h.empty else (h.index[0] - (M(p) + pd.offsets.MonthEnd(0))).days
        cov = [p for p in lags if lags[p] is not None]
        if len(lags) == 0: continue
        med = float(np.median([lags[p] for p in cov])) if cov else None
        cand = (len(cov), len(lags), med, max(lags[p] for p in cov) if cov else None, sum(1 for p in cov if lags[p] <= 30), sign, ceiling, lags)
        key = (len(cov) / len(lags), -(med if med is not None else 9e9))
        if best is None or key > best[0]: best = (key, cand)
    return best[1] if best else None

rows = []; log = open(f'{ROOT}/screen_{FREQ}.log', 'w')
for i, r in enumerate(idx.itertuples()):
    try:
        if OTHER:
            s = pd.read_csv(f'{D}/{r.file}', index_col=0, parse_dates=True)[r.col]
            s = pd.to_numeric(s, errors='coerce').dropna().astype(float)
        else:
            s = pd.read_csv(f'{D}/{r.id}.csv', index_col=0, parse_dates=True)['value'].dropna().astype(float)
    except Exception as e:
        continue
    if len(s) < 200 or s.index[0] > pd.Timestamp('2005-12-31') or 'Recession Indicators' in str(r.title): continue
    s = s[~s.index.duplicated()].sort_index()
    for name, o in objects(s, r.units).items():
        o = o.dropna()
        if o.empty: continue
        v = veto(o); sp = speed(o)
        row = dict(id=r.id, title=str(r.title)[:80], start=str(s.index[0].date()), object=name)
        if v:
            for rd, b in v.items():
                sfx = '' if rd == 'win' else '_call'
                row.update({f'veto_margin{sfx}': round(b[0], 3), f'veto_sign{sfx}': b[1], f'veto_dis{sfx}': b[3], f'veto_rec{sfx}': b[4], f'veto_line{sfx}': round(b[5], 4), f'veto_exposure{sfx}': round(b[6], 1)})
        if sp: row.update(speed_cov=sp[0], speed_of=sp[1], speed_median=sp[2], speed_worst=sp[3], speed_within30=sp[4], speed_sign=sp[5], speed_ceiling=round(sp[6], 4),
                          speed_lags=' '.join(f'{p}:{sp[7][p]}' for p in sp[7]))
        rows.append(row)
    if (i + 1) % 200 == 0: print(f'{i + 1}/{len(idx)}', file=log, flush=True)
df = pd.DataFrame(rows); df.to_csv(f'{ROOT}/screen_{FREQ}.csv', index=False)
print(f'{FREQ}: {df.id.nunique()} series with history to 2005 or earlier, {len(df)} objects', file=log)

print("\nVETO leaderboard, the route's window read - full candidates (read at 1951, 1952 and 1967), by margin (>0 separates: every recession reaches the line within 30 days of its claims call, no disturbance within six months of its own); the margin is in own standard deviations", file=log)
cols = ['id', 'title', 'start', 'object', 'veto_sign', 'veto_margin', 'veto_rec', 'veto_line', 'veto_exposure']
full = df[(df.get('veto_dis', pd.Series(dtype=float)) == 3)].sort_values('veto_margin', ascending=False)
print(full.head(40)[cols].to_string(index=False), file=log)
print('\nVETO, window read - partial candidates (1967 only), by margin', file=log)
part = df[(df.get('veto_dis', pd.Series(dtype=float)) == 1)].sort_values('veto_margin', ascending=False)
print(part.head(30)[cols].to_string(index=False), file=log)
print('\nVETO, the call-day read (the value in hand on the call day) - full candidates, by margin', file=log)
colsc = ['id', 'title', 'start', 'object', 'veto_sign_call', 'veto_margin_call', 'veto_rec_call', 'veto_line_call', 'veto_exposure_call']
fullc = df[(df.get('veto_dis_call', pd.Series(dtype=float)) == 3)].sort_values('veto_margin_call', ascending=False)
print(fullc.head(25)[colsc].to_string(index=False), file=log)
print('\nSPEED leaderboard - objects reaching every recession their history covers at their own quiet ceiling, by coverage then median lag (days after the peak month\'s end)', file=log)
sp = df[df.speed_cov.notna() & (df.speed_cov == df.speed_of) & (df.speed_of >= 6)].sort_values(['speed_of', 'speed_median'], ascending=[False, True])
print(sp.head(60)[['id', 'title', 'start', 'object', 'speed_sign', 'speed_of', 'speed_median', 'speed_worst', 'speed_within30', 'speed_lags']].to_string(index=False), file=log)
print('\nSPEED - objects covering all thirteen since 1948 (history from 1948), best median lag, any coverage', file=log)
sp13 = df[df.speed_of == 13].sort_values(['speed_cov', 'speed_median'], ascending=[False, True])
print(sp13.head(40)[['id', 'title', 'object', 'speed_sign', 'speed_cov', 'speed_median', 'speed_worst', 'speed_within30', 'speed_lags']].to_string(index=False), file=log)
log.close()
