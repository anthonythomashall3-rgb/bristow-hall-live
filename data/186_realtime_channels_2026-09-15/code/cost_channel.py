#!/usr/bin/env python3
"""A cost-and-financing proposer channel, priced the same way every other channel has been.

WHY BUILD THIS NOW. `onset_2024_profile.py` measured what is extreme today: the mortgage rate's
six-month rise at the 86th percentile of its own history, supply-chain pressure at the 90th, oil at the
80th, policy uncertainty at the 100th -- while every labour and demand object has fallen back toward
ordinary. The rule reads that configuration weakly. Its proposers are labour objects; a downturn that
began in the cost of money and the cost of goods would reach them late.

The Canadian test found the same gap from the other direction: Canadian recessions start in rates and
construction, Canadian labour never exceeds the 79th percentile before a peak, and a rule that
hard-wires labour as its only proposer cannot see them. The two findings are the same finding.

So this prices a cost proposer against a demand or labour confirmer, on the standard used throughout:
a rolling quantile of the object's own past, a 540-day lockout, the publication lag charged by
frequency, zero quiet firings as the bar, and the July 1965 - June 1968 credit crunch scored like any
other stretch rather than excluded.

WHAT WOULD MAKE THIS CHANNEL REAL. Two things, and both are tested here. It must fire before the two
peaks that were cost-led -- November 1973 and January 1980 -- and it must stay silent through the many
episodes when costs rose and no recession followed, of which 1966, 1987, 2011 and 2022 are the obvious
ones. A channel that only fires in 1973 and 1980 and nowhere else is worth having even if it never adds
a day to a call the rule already makes, because the next cost-led recession is the one it is for.
"""
import os, json, itertools, warnings, numpy as np, pandas as pd
warnings.filterwarnings('ignore')
_C = [os.path.expanduser('~/Projects/Onset Detector Data'), os.path.expanduser('~/mnt/Onset Detector Data')]
ROOT = next((c for c in _C if os.path.isdir(os.path.join(c, '186_realtime_channels_2026-09-15'))), _C[0])
DATA = os.path.join(ROOT, '186_realtime_channels_2026-09-15', 'data')
OUT = os.path.join(ROOT, '186_realtime_channels_2026-09-15', 'out')
S182 = os.path.join(ROOT, '182_channel_coverage_2026-09-15', 'data')
NBER = [('1948-11','1949-10'),('1953-07','1954-05'),('1957-08','1958-04'),('1960-04','1961-02'),
        ('1969-12','1970-11'),('1973-11','1975-03'),('1980-01','1980-07'),('1981-07','1982-11'),
        ('1990-07','1991-03'),('2001-03','2001-11'),('2007-12','2009-06'),('2020-02','2020-04'),
        ('2024-04','2024-08')]
def me(y): return pd.Timestamp(y + '-01') + pd.offsets.MonthEnd(0)
PK = [me(p) for p, _ in NBER]; TR = [me(t) for _, t in NBER]
def inside(t): return any(p <= t <= r for p, r in zip(PK, TR))
CRUNCH = (pd.Timestamp('1965-07-01'), pd.Timestamp('1968-06-30'))

def rd(sid, folder=None):
    for f in ([folder] if folder else [DATA, S182]):
        p = os.path.join(f, sid + '.csv')
        if os.path.exists(p):
            q = pd.read_csv(p); c = list(q.columns)
            s = pd.Series(pd.to_numeric(q[c[1]], errors='coerce').values,
                          index=pd.to_datetime(q[c[0]], errors='coerce')).dropna().sort_index()
            return s[~s.index.duplicated(keep='last')]
    return None

def steps(s, days):
    sp = float(np.median(np.diff(s.index.values).astype('timedelta64[D]').astype(int))) if len(s) > 8 else 30.0
    return max(1, int(round(days / max(sp, 1)))), sp
def lag_for(sp): return 1 if sp <= 3 else (12 if sp <= 10 else (40 if sp <= 45 else 120))
def lag(s, d): s = s.copy(); s.index = s.index + pd.Timedelta(days=d); return s

def mk(sid, fn):
    s = rd(sid)
    if s is None or len(s) < 60: return None
    k, sp = steps(s, 182); x = fn(s, k).replace([np.inf, -np.inf], np.nan).dropna()
    if len(x) < 60: return None
    return lag(x, lag_for(sp)), max(1, int(round(365.0 / max(sp, 1))))

# ---- cost and financing proposers. High = the cost is rising fast against its own history.
PROP = {}
for name, sid, fn in [
    ('mortgage_rate_rise6m',  'MORTGAGE30US', lambda s, k: s.diff(k)),
    ('mortgage_spread_rise',  'MORTGAGE30US', lambda s, k: s.diff(k)),      # replaced below if DGS10 loads
    ('prime_rate_rise6m',     'DPRIME',       lambda s, k: s.diff(k)),
    ('oil_yoy',               'WTISPLC',      lambda s, k: s.pct_change(2 * k) * 100),
    ('gas_price_yoy',         'GASREGW',      lambda s, k: s.pct_change(2 * k) * 100),
    ('ppi_yoy',               'PPIACO',       lambda s, k: s.pct_change(2 * k) * 100),
    ('cpi_yoy',               'CPIAUCSL',     lambda s, k: s.pct_change(2 * k) * 100),
    ('supply_chain',          'GSCPI',        lambda s, k: s),
    ('policy_uncertainty',    'USEPUINDXD',   lambda s, k: s),
    ('real_rate_rise',        'DFF',          lambda s, k: s.diff(k)),
]:
    r = mk(sid, fn)
    if r: PROP[name] = r
m30, d10 = rd('MORTGAGE30US'), rd('DGS10')
if m30 is not None and d10 is not None:
    sp = (m30 - d10.reindex(m30.index, method='ffill')).dropna()
    PROP['mortgage_spread_rise'] = (lag(sp, 1), 52)

# ---- demand and labour confirmers. High = demand or labour is deteriorating.
CONF = {}
for name, sid, fn in [
    ('claims_up_yoy',       'IC4WSA',  lambda s, k: s.pct_change(2 * k) * 100),
    ('continued_up_yoy',    'CCSA',    lambda s, k: s.pct_change(2 * k) * 100),
    ('permits_falling',     'PERMIT',  lambda s, k: -s.pct_change(k) * 100),
    ('starts_falling',      'HOUST',   lambda s, k: -s.pct_change(k) * 100),
    ('hours_falling',       'AWHMAN',  lambda s, k: -s.diff(k)),
    ('retail_falling',      'RSAFS',   lambda s, k: -s.pct_change(k) * 100),
    ('ip_falling',          'INDPRO',  lambda s, k: -s.pct_change(k) * 100),
    ('caputil_falling',     'TCU',     lambda s, k: -s.diff(k)),
    ('sentiment_falling',   'UMCSENT', lambda s, k: -s.pct_change(k) * 100),
    ('orders_falling',      'NEWORDER', lambda s, k: -s.pct_change(k) * 100),
    ('temp_help_falling',   'TEMPHELPS', lambda s, k: -s.pct_change(2 * k) * 100),
]:
    r = mk(sid, fn)
    if r: CONF[name] = r
print('cost proposers :', list(PROP.keys()))
print('demand confirmers:', list(CONF.keys()))

IDX = pd.date_range('1946-01-31', '2026-09-30', freq='D')
def daily(b): return b.reindex(IDX.union(b.index)).ffill().reindex(IDX).fillna(False).astype(bool)
def hold(b, d): return b.rolling(d, min_periods=1).max().astype(bool)
def over_q(x, q, win):
    ln = x.shift(1).rolling(win, min_periods=max(10, win // 2)).quantile(q / 100.0)
    return (x > ln) & ln.notna()
def episodes(fire, minexp=9):
    calls, armed, last = [], True, None
    for t, f in fire.items():
        if armed and f: calls.append(t); armed = False; last = t
        elif not armed and last is not None and (t - last).days >= minexp * 30 and not f: armed = True
    return calls
def score(calls):
    used, leads = set(), {}
    for p in PK:
        c = [t for t in calls if 0 <= (p - t).days <= 400]
        if c: t = max(c); leads[p.strftime('%Y-%m')] = (t - p).days; used.add(t)
    quiet = [t for t in calls if t not in used and not inside(t)]
    crunch = [t for t in quiet if CRUNCH[0] <= t <= CRUNCH[1]]
    inw = {k: v for k, v in leads.items() if -92 <= v <= -1}
    return len(calls), len(leads), len(inw), len(quiet), len(crunch), json.dumps(inw), \
           json.dumps([t.strftime('%Y-%m') for t in quiet][:6])

rows = []
for pn, (px, pny) in PROP.items():
    for pq, pwy in itertools.product((90, 95, 97), (10, 20)):
        P = hold(daily(over_q(px, pq, max(12, pq and int(pwy * pny)))), 270)
        for cn, (cx, cny) in CONF.items():
            for cq, cwy in itertools.product((80, 90, 95), (10, 20)):
                C = hold(daily(over_q(cx, cq, max(12, int(cwy * cny)))), 270)
                n, nh, ni, nq, nc, iw, qz = score(episodes(P & C))
                rows.append(dict(cost_proposer=pn, p_q=pq, p_win_yrs=pwy, demand_confirmer=cn,
                                 c_q=cq, c_win_yrs=cwy, n_call=n, n_peak=nh, n_in=ni,
                                 n_quiet=nq, n_crunch=nc, inwindow=iw, quiet=qz))
D = pd.DataFrame(rows); D.to_csv(os.path.join(OUT, 'cost_channel.csv'), index=False)
pd.set_option('display.width', 250)
C = ['cost_proposer','p_q','p_win_yrs','demand_confirmer','c_q','c_win_yrs','n_call','n_peak','n_in','n_quiet','n_crunch','inwindow']
print('\nconfigurations: %d' % len(D))
z = D[(D.n_quiet == 0) & (D.n_in > 0)]
print('ZERO quiet firings and at least one call inside [-92,-1]: %d' % len(z))
if len(z): print(z.sort_values(['n_in','n_peak','n_call'], ascending=[False,False,True])[C].head(20).to_string(index=False))
print('\n--- configurations calling the two cost-led peaks, 1973-11 or 1980-01, inside the window ---')
h = D[D.inwindow.str.contains('1973-11|1980-01')].sort_values(['n_quiet','n_in'], ascending=[True,False])
print(h[C].head(15).to_string(index=False) if len(h) else '   none')
print('\nconfigurations firing in the 1965-68 credit crunch: %d of %d' % (int((D.n_crunch > 0).sum()), len(D)))
