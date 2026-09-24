#!/usr/bin/env python3
"""Leg C — the Moody's credit spread, gated the way leg M now is.

THE REASONING, stated before the run. Three peaks remain uncovered by any live object: 1953, 1957
and 1960. The only objects that reach them AND still publish are Moody's Aaa and Baa corporate bond
yields, monthly from January 1919. Collection 171 measured that the Baa-Aaa spread has ZERO
zero-false-alarm settings out of 158 on its own, which is why it was set aside.

But leg M was in the same position this morning and is not now. What changed was not the object, it
was the GATE: a second, causally different witness that distinguishes stress-with-a-recession from
stress-without-one. If that device is real rather than a 1973 coincidence, it should rescue the
credit spread on the same principle — and if it does not, that is evidence the device is narrower
than it looked.

The gate cannot be the term spread here: `GS10`/`GS1` begin in April 1953, too late for the 1953
peak and marginal for 1957. So two gates are tried, both of which reach the 1950s:

  RATE   the three-month Treasury bill rate (`TB3MS`, from 1934) high against its own trailing
         history -- tight money, which is what precedes these episodes.
  REAL   industrial production (`INDPRO`, from 1919) falling over six months -- a real-activity
         witness, causally different from a credit price.

Both gates and the spread's own line are quantiles of their OWN TRAILING HISTORY, expanding and
shifted. No hand-picked constants. Every combination in the declared grid is reported, including
the failures.
"""
import json, os, numpy as np, pandas as pd, warnings
warnings.filterwarnings('ignore')
_C = [os.path.expanduser('~/Projects/Onset Detector Data'), os.path.expanduser('~/mnt/Onset Detector Data')]
BASE = next((c for c in _C if os.path.isdir(os.path.join(c, '176_financial_leg_conjunction_2026-09-15'))), _C[0])
SRC = os.path.join(BASE, '176_financial_leg_conjunction_2026-09-15', 'data')
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, 'out')

PEAKS = ['1948-11','1953-07','1957-08','1960-04','1969-12','1973-11','1980-01',
         '1981-07','1990-07','2001-03','2007-12','2020-02','2024-04']
TROUGHS = ['1949-10','1954-05','1958-04','1961-02','1970-11','1975-03','1980-07',
           '1982-11','1991-03','2001-11','2009-06','2020-04','2024-09']
def me(ym): return pd.Timestamp(ym+'-01') + pd.offsets.MonthEnd(0)
PK, TR = [me(p) for p in PEAKS], [me(t) for t in TROUGHS]
def inside(t): return any(p <= t <= tr for p, tr in zip(PK, TR))

def rd(sid):
    d = pd.read_csv(os.path.join(SRC, sid + '.csv')); c = list(d.columns)
    s = pd.Series(pd.to_numeric(d[c[1]], errors='coerce').values,
                  index=pd.to_datetime(d[c[0]], errors='coerce'))
    s = s[~s.index.isna()].dropna().sort_index()
    return s[~s.index.duplicated(keep='last')]

baa, aaa = rd('BAA'), rd('AAA')
spread = (baa - aaa).dropna(); spread.index = spread.index + pd.Timedelta(days=40)
tb = rd('TB3MS'); tb.index = tb.index + pd.Timedelta(days=40)
ip = rd('INDPRO'); ipf = (-ip.pct_change(6)); ipf.index = ipf.index + pd.Timedelta(days=40)

def fires_high(x, q, win=120, minobs=60, lockout=18):
    # ROLLING, not expanding. An expanding quantile on a series that contains the 1930s is
    # poisoned by them: Baa-Aaa exceeded five points in 1932 and nothing since approaches it, so
    # a line anchored on the whole history can never be crossed again. Measured: the expanding
    # form fires 0 to 2 times in 107 years. A rolling window asks whether the spread is wide
    # BY THE STANDARDS OF ITS OWN RECENT PAST, which is the question the rule actually needs,
    # and is the same form that works for legs A and P.
    line = x.shift(1).rolling(win, min_periods=minobs).quantile(q/100.0)
    hit = (x > line) & line.notna()
    out, last = [], None
    for t in x.index[hit]:
        if last is not None and (t - last).days < lockout*30: continue
        out.append(t); last = t
    return out

def gate_ok(g, t, q, win=120, minobs=60):
    line = g.shift(1).rolling(win, min_periods=minobs).quantile(q/100.0)
    pv, pl = g[g.index <= t], line[line.index <= t]
    if not len(pv) or not len(pl) or pd.isna(pl.iloc[-1]): return False
    return float(pv.iloc[-1]) >= float(pl.iloc[-1])

rows = []
for sq in [90, 95, 97, 99]:
  for swin in [60, 120, 240]:
    pubs = fires_high(spread, sq, win=swin)
    for gname, g in (('RATE_tbill', tb), ('REAL_indpro_fall', ipf), ('NONE', None)):
        for gq in ([70, 80, 90] if g is not None else [0]):
            kept = pubs if g is None else [t for t in pubs if gate_ok(g, t, gq)]
            hits, used = {}, set()
            for p in PK:
                c = [t for t in kept if 0 <= (p - t).days <= 400]
                if c:
                    tt = c[-1]; hits[p.strftime('%Y-%m')] = (tt - p).days; used.add(tt)
            inw = {k: v for k, v in hits.items() if -92 <= v <= -1}
            quiet = [t for t in kept if t not in used and not inside(t)]
            early50 = {k: v for k, v in inw.items() if k < '1965'}
            rows.append(dict(spread_q=sq, spread_win=swin, gate=gname, gate_q=gq, n_fire=len(kept), n_hit=len(hits),
                             n_in=len(inw), n_quiet=len(quiet), n_in_1950s=len(early50),
                             inwindow=json.dumps(inw),
                             quiet=';'.join(str(t.date()) for t in quiet[:5])))
d = pd.DataFrame(rows); d.to_csv(os.path.join(OUT, 'legC_credit_gated.csv'), index=False)
print('%-6s %-5s %-18s %-7s %-6s %-6s %-4s %s' % ('spr_q','win','gate','gate_q','fires','quiet','IN','in-window calls'))
for _, r in d.sort_values(['n_quiet','n_in'], ascending=[True, False]).head(22).iterrows():
    print('%-6d %-5d %-18s %-7d %-6d %-6d %-4d %s' % (r.spread_q, r.spread_win, r.gate, r.gate_q,
                                                  r.n_fire, r.n_quiet, r.n_in, r.inwindow[:58]))
z = d[(d.n_quiet == 0) & (d.n_in > 0)]
print('\n=== zero quiet AND at least one in-window: %d of %d ===' % (len(z), len(d)))
if len(z): print(z[['spread_q','spread_win','gate','gate_q','n_fire','n_hit','n_in','n_in_1950s','inwindow']].to_string(index=False))
