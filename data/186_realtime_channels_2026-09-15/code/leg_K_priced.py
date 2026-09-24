#!/usr/bin/env python3
"""Leg K -- the cost-and-financing leg, priced in exactly the form a walk would inject it.

WHY PRICE IT AGAIN. `cost_channel.py` measured the cost channel as a CONJUNCTION: two daily boolean
series held open for a window and intersected. A walk does not take a conjunction; it takes a list of
(published, dated) proposals and arms them. Those are different objects and they do not have to score
the same, so a leg must be priced in the form it will actually be used in. Carrying a conjunction's
numbers over to a leg would be the same class of error as reading a revised series and calling it a
first print.

THE FORM. The prime rate's six-month rise, above the 90th percentile of its own trailing twenty years,
with a 540-day lockout applied to the ungated proposals. Each surviving proposal is then asked one
question on its publication day: were housing starts falling year on year at or above the 95th
percentile of their own trailing twenty years, using only the starts figures published by then? If not,
the proposal is dropped. The lockout comes first and the gate second, which is the order leg U is
priced and injected in -- the reverse lets a suppressed proposal re-arm the clock.

WHY THESE TWO SERIES. The prime rate is **never revised**. Housing starts have **first prints from July
1960**. Every call this leg makes is therefore readable on the day it is made, which is not true of
legs A, H, D or O. Causally it is a cost-side proposer with a housing confirmer -- different from the
labour proposers the rule already has, which is the point: the Canadian test and the 2024-versus-now
profile both say a labour-only proposer cannot see a downturn that starts in the cost of money.
"""
import os, json, itertools, warnings, numpy as np, pandas as pd
warnings.filterwarnings('ignore')
_C = [os.path.expanduser('~/Projects/Onset Detector Data'), os.path.expanduser('~/mnt/Onset Detector Data')]
ROOT = next((c for c in _C if os.path.isdir(os.path.join(c, '186_realtime_channels_2026-09-15'))), _C[0])
HERE = os.path.join(ROOT, '186_realtime_channels_2026-09-15')
DATA, VDIR, OUT = os.path.join(HERE, 'data'), os.path.join(HERE, 'vintages'), os.path.join(HERE, 'out')
NBER = [('1948-11','1949-10'),('1953-07','1954-05'),('1957-08','1958-04'),('1960-04','1961-02'),
        ('1969-12','1970-11'),('1973-11','1975-03'),('1980-01','1980-07'),('1981-07','1982-11'),
        ('1990-07','1991-03'),('2001-03','2001-11'),('2007-12','2009-06'),('2020-02','2020-04'),
        ('2024-04','2024-08')]
def me(y): return pd.Timestamp(y + '-01') + pd.offsets.MonthEnd(0)
PK = [me(p) for p, _ in NBER]; TR = [me(t) for _, t in NBER]
def inside(t): return any(p <= t <= r for p, r in zip(PK, TR))
CRUNCH = (pd.Timestamp('1965-07-01'), pd.Timestamp('1968-06-30'))

def rd(sid):
    q = pd.read_csv(os.path.join(DATA, sid + '.csv')); c = list(q.columns)
    s = pd.Series(pd.to_numeric(q[c[1]], errors='coerce').values,
                  index=pd.to_datetime(q[c[0]], errors='coerce')).dropna().sort_index()
    return s[~s.index.duplicated(keep='last')]
def fp(sid):
    q = pd.read_csv(os.path.join(VDIR, sid + '_firstprint.csv'))
    d = pd.to_datetime(q['date'], errors='coerce'); p = pd.to_datetime(q['published'], errors='coerce')
    v = pd.to_numeric(q['value'], errors='coerce'); k = d.notna() & p.notna() & v.notna()
    s = pd.Series(v[k].values, index=d[k]).sort_index(); pb = pd.Series(p[k].values, index=d[k]).sort_index()
    return s[~s.index.duplicated(keep='first')], pb[~pb.index.duplicated(keep='first')]

HS, HSPUB = fp('HOUST')
GSTART = (-HS.pct_change(12) * 100).dropna()          # starts falling year on year
PRIME = rd('DPRIME')                                   # daily, never revised
FF = rd('DFF')
MORT = rd('MORTGAGE30US')
try:    CPI, CPIPUB = fp('CPIAUCSL')
except Exception: CPI, CPIPUB = None, None

def daily_prop(s, months, q, win_years, lagd=1, lock=540):
    """A daily rate series: its change over `months` months, above a rolling quantile of its own past."""
    x = (s - s.shift(int(round(months * 21)))).dropna()          # trading-day approximation
    w = int(round(win_years * 252))
    ln = x.shift(1).rolling(w, min_periods=max(60, w // 2)).quantile(q / 100.0)
    hit = (x > ln) & ln.notna()
    out, last = [], None
    for t in x.index[hit]:
        if last is not None and (t - last).days < lock: continue
        out.append((t + pd.Timedelta(days=lagd), t.to_period('M').to_timestamp())); last = t
    return out

def monthly_fp_prop(s, pb, k, q, win_m, lock=540):
    x = (s.pct_change(k) * 100).dropna()
    ln = x.shift(1).rolling(win_m, min_periods=max(12, win_m // 2)).quantile(q / 100.0)
    hit = (x > ln) & ln.notna()
    out, last = [], None
    for t in x.index[hit]:
        if last is not None and (t - last).days < lock: continue
        a = pb.get(t)
        if a is None or pd.isna(a): continue
        out.append((pd.Timestamp(a), t.to_period('M').to_timestamp())); last = t
    return out

def gate(props, gq, gwin):
    kept = []
    for a, d in props:
        idx = [u for u in GSTART.index if pd.notna(HSPUB.get(u)) and pd.Timestamp(HSPUB.get(u)) <= a]
        gs = GSTART.reindex(idx).sort_index()
        if len(gs) < max(24, gwin): continue
        hist = gs.iloc[:-1].tail(gwin)
        if len(hist) < max(6, gwin // 2): continue
        if float(gs.iloc[-1]) <= float(np.quantile(hist.values, gq / 100.0)): continue
        kept.append((a, d))
    return kept

def score(props):
    used, leads = set(), {}
    for p in PK:
        c = [a for a, _ in props if 0 <= (p - a).days <= 400]
        if c: a = max(c); leads[p.strftime('%Y-%m')] = (a - p).days; used.add(a)
    quiet = [a for a, _ in props if a not in used and not inside(a)]
    crunch = [a for a in quiet if CRUNCH[0] <= a <= CRUNCH[1]]
    return len(props), len(leads), len({k: v for k, v in leads.items() if -92 <= v <= -1}), \
           len(quiet), len(crunch), json.dumps({k: v for k, v in leads.items() if -92 <= v <= -1}), \
           json.dumps(leads), json.dumps([a.strftime('%Y-%m') for a in quiet][:8])

rows = []
BASES = [('prime_rise', PRIME), ('fedfunds_rise', FF), ('mortgage_rise', MORT)]
for bn, bs in BASES:
    if bs is None or len(bs) < 500: continue
    for months, pq, pwy in itertools.product((6, 12), (90, 95, 97), (10, 20)):
        pr = daily_prop(bs, months, pq, pwy)
        if not pr: continue
        n, nh, ni, nq, nc, iw, al, qz = score(pr)
        rows.append(dict(base=bn, form='%dm' % months, p_q=pq, p_win=pwy, gate='NONE', g_q='', g_win='',
                         n_fire=n, n_peak=nh, n_in=ni, n_quiet=nq, n_crunch=nc, inwindow=iw, all_leads=al, quiet=qz))
        for gq, gwin in itertools.product((90, 95, 97), (120, 240)):
            k = gate(pr, gq, gwin)
            if not k: continue
            n, nh, ni, nq, nc, iw, al, qz = score(k)
            rows.append(dict(base=bn, form='%dm' % months, p_q=pq, p_win=pwy, gate='starts_falling',
                             g_q=gq, g_win=gwin, n_fire=n, n_peak=nh, n_in=ni, n_quiet=nq, n_crunch=nc,
                             inwindow=iw, all_leads=al, quiet=qz))
if CPI is not None:
    for pq, pwm in itertools.product((90, 95, 97), (120, 240)):
        pr = monthly_fp_prop(CPI, CPIPUB, 12, pq, pwm)
        if not pr: continue
        n, nh, ni, nq, nc, iw, al, qz = score(pr)
        rows.append(dict(base='cpi_yoy_firstprint', form='12m', p_q=pq, p_win=pwm // 12, gate='NONE',
                         g_q='', g_win='', n_fire=n, n_peak=nh, n_in=ni, n_quiet=nq, n_crunch=nc,
                         inwindow=iw, all_leads=al, quiet=qz))
        for gq, gwin in itertools.product((90, 95, 97), (120, 240)):
            k = gate(pr, gq, gwin)
            if not k: continue
            n, nh, ni, nq, nc, iw, al, qz = score(k)
            rows.append(dict(base='cpi_yoy_firstprint', form='12m', p_q=pq, p_win=pwm // 12,
                             gate='starts_falling', g_q=gq, g_win=gwin, n_fire=n, n_peak=nh, n_in=ni,
                             n_quiet=nq, n_crunch=nc, inwindow=iw, all_leads=al, quiet=qz))
D = pd.DataFrame(rows); D.to_csv(os.path.join(OUT, 'leg_K_priced.csv'), index=False)
pd.set_option('display.width', 250)
C = ['base','form','p_q','p_win','gate','g_q','g_win','n_fire','n_peak','n_in','n_quiet','n_crunch','inwindow']
print('configurations: %d' % len(D))
z = D[(D.n_quiet == 0) & (D.n_in > 0)]
print('\nZERO quiet firings and at least one call inside [-92,-1]: %d' % len(z))
if len(z): print(z.sort_values(['n_in','n_peak','n_fire'], ascending=[False,False,True])[C].head(20).to_string(index=False))
print('\nall configurations with <=1 quiet firing, best coverage first:')
print(D[D.n_quiet <= 1].sort_values(['n_in','n_peak','n_quiet'], ascending=[False,False,True])[C].head(15).to_string(index=False))
