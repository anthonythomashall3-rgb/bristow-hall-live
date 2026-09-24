#!/usr/bin/env python3
"""Price the daily withheld-tax object as a leg.

The series is daily and extremely seasonal -- deposits cluster on semi-weekly and monthly employer
schedules -- so the raw level is unusable. The object is the YEAR-OVER-YEAR change of a trailing
sum, which cancels the deposit calendar because the same calendar occurred a year earlier:

    withheld(t) = sum of the last N business days, against the same sum a year before.

Deflated by average hourly earnings, so that a fall is a fall in EMPLOYMENT rather than in wages;
and undeflated as well, both reported. Publication lag is ONE day, which is what makes this object
worth having: every other labour object in the rule is charged twelve or forty.

Lines are rolling quantiles of the object's own trailing window, shifted. Gated, as legs M, R, E and
T are, because a gate is what has made every sparse object in this programme admissible.
"""
import json, os, numpy as np, pandas as pd, warnings
warnings.filterwarnings('ignore')
_C = [os.path.expanduser('~/Projects/Onset Detector Data'), os.path.expanduser('~/mnt/Onset Detector Data')]
BASE = next((c for c in _C if os.path.isdir(os.path.join(c, '183_transmission_channels_2026-09-15'))), _C[0])
HERE = os.path.join(BASE, '183_transmission_channels_2026-09-15')
DATA, OUT = os.path.join(HERE, 'data'), os.path.join(HERE, 'out'); os.makedirs(OUT, exist_ok=True)
S176 = os.path.join(BASE, '176_financial_leg_conjunction_2026-09-15', 'data')

PEAKS = ['2007-12','2020-02','2024-04']          # the peaks this series can speak to at all
TROUGHS = ['2009-06','2020-04','2024-09']
ALLPK = ['1948-11','1953-07','1957-08','1960-04','1969-12','1973-11','1980-01',
         '1981-07','1990-07','2001-03','2007-12','2020-02','2024-04']
ALLTR = ['1949-10','1954-05','1958-04','1961-02','1970-11','1975-03','1980-07',
         '1982-11','1991-03','2001-11','2009-06','2020-04','2024-09']
def me(ym): return pd.Timestamp(ym+'-01') + pd.offsets.MonthEnd(0)
PK, TR = [me(p) for p in PEAKS], [me(t) for t in TROUGHS]
AP, AT = [me(p) for p in ALLPK], [me(t) for t in ALLTR]
def inside(t): return any(p <= t <= tr for p, tr in zip(AP, AT))

d = pd.read_csv(os.path.join(DATA, 'dts_withheld_daily.csv'))
s = pd.Series(pd.to_numeric(d['withheld_musd'], errors='coerce').values,
              index=pd.to_datetime(d['date'])).dropna().sort_index()
s = s[~s.index.duplicated(keep='last')]
print('withheld daily: n=%d  %s .. %s' % (len(s), s.index.min().date(), s.index.max().date()))

def rd(sid):
    q = pd.read_csv(os.path.join(S176, sid + '.csv')); c = list(q.columns)
    x = pd.Series(pd.to_numeric(q[c[1]], errors='coerce').values,
                  index=pd.to_datetime(q[c[0]], errors='coerce')).dropna().sort_index()
    return x[~x.index.duplicated(keep='last')]
g10, g1 = rd('GS10'), rd('GS1')
TS = (g10 - g1.reindex(g10.index, method='ffill')).dropna(); TS.index = TS.index + pd.Timedelta(days=15)
u = rd('UNRATE'); m3 = u.rolling(3).mean()
SAHM = (m3 - m3.rolling(12).min()); SAHM.index = SAHM.index + pd.Timedelta(days=40)
HUB = 0.3667

def g_term(t, q):
    ln = TS.shift(1).expanding(min_periods=120).quantile(q/100.0)
    pv, pl = TS[TS.index<=t], ln[ln.index<=t]
    return len(pv) and len(pl) and pd.notna(pl.iloc[-1]) and float(pv.iloc[-1]) <= float(pl.iloc[-1])
def g_sahm(t, fr):
    pv = SAHM[SAHM.index<=t]; return len(pv) and float(pv.iloc[-1]) >= HUB*fr
GATES = [('NONE', None, [0]), ('TERM', g_term, [2,5,10,20]), ('SAHM', g_sahm, [1/6,1/3,1/2])]

rows = []
for N in [20, 60, 125]:
    roll = s.rolling(N).sum()
    yoy = (roll / roll.shift(252) - 1.0) * 100      # 252 business days = one year
    obj = (-yoy).dropna()                            # HIGH = withheld taxes falling year over year
    for q in [95, 97, 99]:
        for win in [500, 1000]:
            ln = obj.shift(1).rolling(win, min_periods=250).quantile(q/100.0)
            hit = (obj > ln) & ln.notna()
            base, last = [], None
            for t in obj.index[hit]:
                if last is not None and (t-last).days < 540: continue
                base.append(t + pd.Timedelta(days=1)); last = t     # ONE day publication lag
            if not base: continue
            for gname, fn, levels in GATES:
                for lv in levels:
                    kept = base if fn is None else [t for t in base if fn(t, lv)]
                    hits, used = {}, set()
                    for p in PK:
                        c = [t for t in kept if 0 <= (p-t).days <= 400]
                        if c: tt=c[-1]; hits[p.strftime('%Y-%m')]=(tt-p).days; used.add(tt)
                    inw = {k:v for k,v in hits.items() if -92<=v<=-1}
                    quiet = [t for t in kept if t not in used and not inside(t)]
                    rows.append(dict(sum_days=N,q=q,win=win,gate=gname,level=round(lv,4),
                                     n_fire=len(kept),n_hit=len(hits),n_in=len(inw),
                                     n_quiet=len(quiet),inwindow=json.dumps(inw),
                                     quiet=';'.join(str(t.date()) for t in quiet[:5])))
D = pd.DataFrame(rows); D.to_csv(os.path.join(OUT,'withheld_pricing.csv'),index=False)
print('configurations:',len(D))
z = D[(D.n_quiet==0)&(D.n_in>0)].sort_values(['n_in','n_hit'],ascending=False)
print('\n=== zero quiet AND at least one in-window: %d ===' % len(z))
if len(z): print(z[['sum_days','q','win','gate','level','n_fire','n_hit','n_in','inwindow']].head(14).to_string(index=False))
else:
    b=D.sort_values(['n_quiet','n_in'],ascending=[True,False]).head(8)
    print(b[['sum_days','q','win','gate','level','n_fire','n_hit','n_in','n_quiet','inwindow','quiet']].to_string(index=False))
