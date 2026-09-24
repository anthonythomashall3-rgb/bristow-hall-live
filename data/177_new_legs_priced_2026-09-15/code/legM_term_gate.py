#!/usr/bin/env python3
"""Leg M gated by the TERM SPREAD — collection 85's own named-but-never-built next step.

Collection 85 (pkg85) is the only thing in this programme's history recorded as moving the causal
frontier outward: adding a term-spread inversion gate took causal detection from 0 to 42 at a
ten-false-alarm budget. It named three follow-ups and none was built. This is one of them.

WHY IT SHOULD WORK, stated before the numbers. Leg M's five quiet firings (1966, 1978, 1987, 1998,
1999) are money-market stress without a recession. A labour witness cannot separate them from 1973 —
measured: the Sahm gap read 0.000 on 12 October 1973, exactly as it did in 1966, 1978, 1987 and
1999, because in an energy or monetary shock the price moves first and labour follows. The term
spread is the object that does distinguish them, because an inverted curve is the market pricing a
contraction while a stress episode without one leaves the curve alone.

NO HAND-PICKED CONSTANT. The gate is the spread below a QUANTILE OF ITS OWN TRAILING HISTORY,
expanding and shifted — a moving line, of exactly the kind that works for a confirmer. Every
quantile in a declared grid is run against every setting of leg M, and all are reported. A result
that holds at one setting only is noise; one that holds across the grid is a property.
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

g10, g1 = rd('GS10'), rd('GS1')
ts = (g10 - g1.reindex(g10.index, method='ffill')).dropna()
ts.index = ts.index + pd.Timedelta(days=15)          # published mid-following-month
QS = [2, 5, 10, 15, 20]
LINES = {q: ts.shift(1).expanding(min_periods=120).quantile(q / 100.0) for q in QS}

prop = pd.read_csv(os.path.join(OUT, 'leg_M_money_proposals.csv'))
prop['published'] = pd.to_datetime(prop['published'])

rows = []
for (mw, mq), g in prop.groupby(['mwin', 'mq']):
    pubs = sorted(g['published'])
    for q in QS:
        line = LINES[q]
        kept = []
        for t in pubs:
            pv = ts[ts.index <= t]; pl = line[line.index <= t]
            if len(pv) and len(pl) and pd.notna(pl.iloc[-1]) and float(pv.iloc[-1]) <= float(pl.iloc[-1]):
                kept.append(t)
        hits, used = {}, set()
        for pk in PK:
            c = [t for t in kept if 0 <= (pk - t).days <= 400]
            if c:
                tt = c[-1]; hits[pk.strftime('%Y-%m')] = (tt - pk).days; used.add(tt)
        inw = {k: v for k, v in hits.items() if -92 <= v <= -1}
        quiet = [t for t in kept if t not in used and not inside(t)]
        rows.append(dict(mwin=mw, mq=mq, gate_q=q, n_fire=len(kept), n_hit=len(hits),
                         n_in=len(inw), n_quiet=len(quiet), inwindow=json.dumps(inw),
                         quiet=';'.join(str(t.date()) for t in quiet[:6])))
d = pd.DataFrame(rows)
d.to_csv(os.path.join(OUT, 'legM_term_gate.csv'), index=False)
print('%-10s %-7s %-6s %-6s %-6s %-30s %s' % ('legM','gate_q','fires','hits','quiet','in-window','quiet dates'))
for _, r in d.iterrows():
    print('m=%-2s,%-3s %-7d %-6d %-6d %-6d %-30s %s'
          % (r.mwin, r.mq, r.gate_q, r.n_fire, r.n_hit, r.n_quiet, r.inwindow[:30], r.quiet[:40]))
z = d[(d.n_quiet == 0) & (d.n_in > 0)]
print('\n=== ZERO quiet firings AND at least one in-window call: %d of %d settings ===' % (len(z), len(d)))
if len(z): print(z[['mwin','mq','gate_q','n_fire','n_hit','n_in','inwindow']].to_string(index=False))
