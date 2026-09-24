#!/usr/bin/env python3
"""Leg M with a second witness — the fix the archive's own architecture implies.

Leg M (the paper-bill spread) reaches November 1973 at -45 to -63 days, which is the peak the
labour-only rule handles worst. It is inadmissible alone because it also fires in 1966, 1978, 1987,
1998 and 1999 — money-market stress with no recession behind it.

THE STRUCTURAL FIX, and it is the programme's own: financial stress is not a recession, so the
spread needs a SECOND, CAUSALLY DIFFERENT WITNESS. In 1987, 1998 and 1999 the labour market was
strong while the money market seized. In 1973 it was already turning. So the witness is a labour
object, required to be off its own floor at the moment the spread fires.

The witness is deliberately WEAK — far below any line that could open a recession by itself, so
that it can only ever veto, never propose. Three candidate witnesses and four levels are tried and
all are reported. Nothing is chosen by result.

The witness levels are stated as a FRACTION of the rule's own hub line (0.3667 on the Sahm gap), so
the device has no new fitted constant of its own: 1/6, 1/3, 1/2 and 2/3 of the line the rule
already uses. Collection 121 set leg N's arming gate the same way, at a third of the hub.
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
HUB = 0.3667

def rd(sid):
    d = pd.read_csv(os.path.join(SRC, sid + '.csv')); c = list(d.columns)
    s = pd.Series(pd.to_numeric(d[c[1]], errors='coerce').values,
                  index=pd.to_datetime(d[c[0]], errors='coerce'))
    s = s[~s.index.isna()].dropna().sort_index()
    return s[~s.index.duplicated(keep='last')]

# the witnesses, each charged its real publication lag
u = rd('UNRATE'); m3 = u.rolling(3).mean()
sahm = (m3 - m3.rolling(12).min()); sahm.index = sahm.index + pd.Timedelta(days=40)
iur = rd('IURNSA'); ins = (iur - iur.rolling(52).min()); ins.index = ins.index + pd.Timedelta(days=12)
ic = rd('ICNSA').rolling(4).mean(); clm = (ic / ic.rolling(52).min() - 1.0) * 100
clm.index = clm.index + pd.Timedelta(days=12)
WIT = {'sahm_gap': (sahm, [HUB/6, HUB/3, HUB/2, HUB*2/3]),
       'insured_gap': (ins, [HUB/6, HUB/3, HUB/2, HUB*2/3]),
       'claims_pct': (clm, [5.0, 10.0, 15.0, 20.0])}

prop = pd.read_csv(os.path.join(OUT, 'leg_M_money_proposals.csv'))
prop['published'] = pd.to_datetime(prop['published'])

rows = []
print('%-8s %-12s %-8s %-6s %-6s %-28s %s' % ('setting','witness','level','fires','quiet','in-window','quiet dates'))
for (mw, mq), g in prop.groupby(['mwin','mq']):
    pubs = sorted(g['published'])
    for wname, (w, levels) in WIT.items():
        for lv in levels:
            kept = []
            for t in pubs:
                prior = w[w.index <= t]
                if len(prior) and float(prior.iloc[-1]) >= lv:
                    kept.append(t)
            hits, used = {}, set()
            for pk in PK:
                c = [t for t in kept if 0 <= (pk - t).days <= 400]
                if c:
                    tt = c[-1]; hits[pk.strftime('%Y-%m')] = (tt - pk).days; used.add(tt)
            inw = {k: v for k, v in hits.items() if -92 <= v <= -1}
            quiet = [t for t in kept if t not in used and not inside(t)]
            rows.append(dict(mwin=mw, mq=mq, witness=wname, level=round(lv,4), n_fire=len(kept),
                             n_hit=len(hits), n_in=len(inw), n_quiet=len(quiet),
                             inwindow=json.dumps(inw),
                             quiet=';'.join(str(t.date()) for t in quiet[:6])))
            if len(inw) and len(quiet) <= 1:
                print('m=%-2s,%-3s %-12s %-8.3f %-6d %-6d %-28s %s'
                      % (mw, mq, wname, lv, len(kept), len(quiet), json.dumps(inw)[:28],
                         ';'.join(str(t.date()) for t in quiet[:4])))
d = pd.DataFrame(rows); d.to_csv(os.path.join(OUT, 'legM_second_witness.csv'), index=False)
print('\n=== ZERO quiet firings AND at least one in-window call ===')
z = d[(d.n_quiet == 0) & (d.n_in > 0)].sort_values(['n_in','n_hit'], ascending=False)
print(z[['mwin','mq','witness','level','n_fire','n_hit','n_in','inwindow']].to_string(index=False) if len(z) else 'none')
