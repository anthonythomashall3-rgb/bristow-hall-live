#!/usr/bin/env python3
"""A fully causal leg for the December 2007 call: the unemployment rate year-on-year, first prints,
gated by a second witness that is also readable at the time.

THE PROBLEM THIS ADDRESSES. Every walk since walk 55 calls the December 2007 peak four days late.
Collection 186 found four objects that call it early -- mortgage delinquency at -63, all-loan
delinquency at -63, capital goods orders at -81, building permits at -51 -- and then
`price_firstprints.py` found that **none of them survives on first prints with zero false alarms.**
The delinquency series have no vintages before April 2011 at all; the orders and permits series have
vintages from 1997 and 1999 but produce quiet firings once their real publication days are used.

That is not a failure of the approach. It is the programme's own central result restated: a single
object cannot do this, which is why the rule is a conjunction. What it means is that the 2007 witness
must itself be a conjunction, and both halves of it must be readable on the day.

THE PROPOSER. The unemployment rate's twelve-month change, above the 95th percentile of its own
trailing five years. ALFRED holds first prints of `UNRATE` from **March 1960**, so every peak from
1960 on is in reach on the figure actually published. Alone it fires eleven times, covers five peaks
and puts three inside one day to three months early -- 1969 at -86, 2001 at -57 and **2007 at -59** --
with three quiet firings. The three quiet firings are what the gate is for.

THE GATES. Each is causally different from the unemployment rate and each is readable at the time:

  term spread        GS10 minus GS1. Treasury yields are never revised.
  mortgage spread    the 30-year mortgage rate over the 10-year Treasury. Neither is revised.
  housing starts     first prints from July 1960.
  factory hours      first prints from November 1961.
  high-yield spread  BofA option-adjusted spread, a market price, never revised, from 1996.

The gate is not a second proposer. It is asked one question on the day the proposer fires: was this
gate also at an extreme of its own past? If not, the proposal is dropped. That is collection 85's
device, and it is the only thing recorded as moving this programme's causal frontier outward.
"""
import os, json, itertools, warnings, numpy as np, pandas as pd
warnings.filterwarnings('ignore')
_C = [os.path.expanduser('~/Projects/Onset Detector Data'), os.path.expanduser('~/mnt/Onset Detector Data')]
ROOT = next((c for c in _C if os.path.isdir(os.path.join(c, '186_realtime_channels_2026-09-15'))), _C[0])
HERE = os.path.join(ROOT, '186_realtime_channels_2026-09-15')
VDIR, DATA, OUT = os.path.join(HERE, 'vintages'), os.path.join(HERE, 'data'), os.path.join(HERE, 'out')
S176 = os.path.join(ROOT, '176_financial_leg_conjunction_2026-09-15', 'data')
NBER = [('1948-11','1949-10'),('1953-07','1954-05'),('1957-08','1958-04'),('1960-04','1961-02'),
        ('1969-12','1970-11'),('1973-11','1975-03'),('1980-01','1980-07'),('1981-07','1982-11'),
        ('1990-07','1991-03'),('2001-03','2001-11'),('2007-12','2009-06'),('2020-02','2020-04'),
        ('2024-04','2024-08')]
def me(y): return pd.Timestamp(y + '-01') + pd.offsets.MonthEnd(0)
PK = [me(p) for p, _ in NBER]; TR = [me(t) for _, t in NBER]
def inside(t): return any(p <= t <= r for p, r in zip(PK, TR))
CRUNCH = (pd.Timestamp('1965-07-01'), pd.Timestamp('1968-06-30'))

def fp(sid):
    q = pd.read_csv(os.path.join(VDIR, sid + '_firstprint.csv'))
    d = pd.to_datetime(q['date'], errors='coerce'); p = pd.to_datetime(q['published'], errors='coerce')
    v = pd.to_numeric(q['value'], errors='coerce'); k = d.notna() & p.notna() & v.notna()
    s = pd.Series(v[k].values, index=d[k]).sort_index(); pb = pd.Series(p[k].values, index=d[k]).sort_index()
    return s[~s.index.duplicated(keep='first')], pb[~pb.index.duplicated(keep='first')]

def rd(path):
    q = pd.read_csv(path); c = list(q.columns)
    s = pd.Series(pd.to_numeric(q[c[1]], errors='coerce').values,
                  index=pd.to_datetime(q[c[0]], errors='coerce')).dropna().sort_index()
    return s[~s.index.duplicated(keep='last')]

U, UPUB = fp('UNRATE')
HS, HSPUB = fp('HOUST')
AW, AWPUB = fp('AWHMAN')

# never-revised market series, dated one business day after the observation
def mkt(sid, folder):
    s = rd(os.path.join(folder, sid + '.csv')); s.index = s.index + pd.Timedelta(days=1); return s
g10 = rd(os.path.join(S176, 'GS10.csv')); g1 = rd(os.path.join(S176, 'GS1.csv'))
TS = (g10 - g1.reindex(g10.index, method='ffill')).dropna(); TS.index = TS.index + pd.Timedelta(days=15)
try:
    m30 = mkt('MORTGAGE30US', DATA); d10 = mkt('DGS10', DATA)
    MSPR = (m30 - d10.reindex(m30.index, method='ffill')).dropna()
except Exception:
    MSPR = None
try:    HY = mkt('BAMLH0A0HYM2', DATA)
except Exception: HY = None

def q_line(x, q, win, lo=False):
    ln = x.shift(1).rolling(win, min_periods=max(6, win // 2)).quantile(q / 100.0)
    return (x < ln) if lo else (x > ln), ln

def propose(x, pb, q, win, lock=540):
    hit, _ = q_line(x, q, win)
    out, last = [], None
    for t in x.index[hit.reindex(x.index).fillna(False)]:
        if last is not None and (t - last).days < lock: continue
        a = pb.get(t)
        if a is None or pd.isna(a): continue
        out.append((pd.Timestamp(a), t)); last = t
    return out

def gate_ok(series, pub_day, q, win, lo, is_first_print=False, pb=None):
    """Was the gate at an extreme of its own past, as of pub_day, using only what was public then?"""
    if series is None: return False
    if is_first_print:
        ok_idx = [t for t in series.index if pb is not None and pd.notna(pb.get(t)) and pd.Timestamp(pb.get(t)) <= pub_day]
        s = series.reindex(ok_idx).sort_index()
    else:
        s = series[series.index <= pub_day]
    if len(s) < max(24, win): return False
    hist = s.iloc[:-1].tail(win)
    if len(hist) < max(6, win // 2): return False
    v = float(s.iloc[-1]); ln = float(np.quantile(hist.values, q / 100.0))
    return (v < ln) if lo else (v > ln)

def score(props):
    used, leads = set(), {}
    for p in PK:
        cand = [a for a, _ in props if 0 <= (p - a).days <= 400]
        if cand:
            a = max(cand); leads[p.strftime('%Y-%m')] = (a - p).days; used.add(a)
    quiet = [a for a, _ in props if a not in used and not inside(a)]
    crunch = [a for a in quiet if CRUNCH[0] <= a <= CRUNCH[1]]
    inw = {k: v for k, v in leads.items() if -92 <= v <= -1}
    return len(props), len(leads), len(inw), len(quiet), len(crunch), inw, leads

UY = (U.pct_change(12) * 100).dropna()          # the twelve-month change, in per cent
UD = U.diff(12).dropna()                         # and in points, since the level is a rate
GATES = {
 'term_spread_low':     dict(s=TS,   q=None, lo=True,  fpp=False),
 'mortgage_spread_high':dict(s=MSPR, q=None, lo=False, fpp=False),
 'high_yield_high':     dict(s=HY,   q=None, lo=False, fpp=False),
 'starts_falling':      dict(s=(-HS.pct_change(12) * 100).dropna(), q=None, lo=False, fpp=True, pb=HSPUB),
 'hours_falling':       dict(s=(-AW.diff(6)).dropna(),              q=None, lo=False, fpp=True, pb=AWPUB),
}
rows = []
for pname, px in [('unrate_yoy_pct', UY), ('unrate_chg12_points', UD)]:
    for pq, pw in itertools.product((90, 95, 97), (36, 60, 120)):
        pr = propose(px, UPUB, pq, pw)
        if not pr: continue
        n, nh, ni, nq, nc, inw, leads = score(pr)
        rows.append(dict(proposer=pname, p_q=pq, p_win=pw, gate='NONE', g_q='', g_win='',
                         n_fire=n, n_peak=nh, n_in=ni, n_quiet=nq, n_crunch=nc,
                         inwindow=json.dumps(inw), all_leads=json.dumps(leads)))
        for gname, g in GATES.items():
            if g['s'] is None or len(g['s']) < 60: continue
            for gq, gwin in itertools.product((5, 10, 20) if g['lo'] else (80, 90, 95), (60, 120, 240)):
                kept = [(a, d) for a, d in pr
                        if gate_ok(g['s'], a, gq, gwin, g['lo'], g.get('fpp', False), g.get('pb'))]
                if not kept: continue
                n, nh, ni, nq, nc, inw, leads = score(kept)
                rows.append(dict(proposer=pname, p_q=pq, p_win=pw, gate=gname, g_q=gq, g_win=gwin,
                                 n_fire=n, n_peak=nh, n_in=ni, n_quiet=nq, n_crunch=nc,
                                 inwindow=json.dumps(inw), all_leads=json.dumps(leads)))
D = pd.DataFrame(rows); D.to_csv(os.path.join(OUT, 'leg_U_gated.csv'), index=False)
pd.set_option('display.width', 250)
C = ['proposer','p_q','p_win','gate','g_q','g_win','n_fire','n_peak','n_in','n_quiet','n_crunch','inwindow']
print('configurations: %d' % len(D))
z = D[(D.n_quiet == 0) & (D.n_in > 0)]
print('\nZERO quiet firings and at least one call inside [-92,-1]: %d' % len(z))
if len(z): print(z.sort_values(['n_in','n_peak','n_fire'], ascending=[False,False,True])[C].head(20).to_string(index=False))
print('\n--- configurations calling DECEMBER 2007 inside [-92,-1] ---')
h = D[D.inwindow.str.contains('2007-12')].sort_values(['n_quiet','n_in'], ascending=[True,False])
print(h[C].head(20).to_string(index=False) if len(h) else '   none')
print('\nfirings in the 1965-68 credit crunch, counted not excluded: %d configurations' % int((D.n_crunch > 0).sum()))
