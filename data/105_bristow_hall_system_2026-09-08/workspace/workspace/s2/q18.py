# q18.py - THE MENU, DATED (Rule 23 clause 3): for every object the rule reads, the underlying series as the lab holds
# it, its first observation, the first month at which the object itself has a reading, and the first cut of the walk
# (January 1962) - so that the paper can state which objects existed and were published before the walk began.
# Run in the workspace: PYTHONPATH=. python3 s2/q18.py
import sys,pickle,io,contextlib,os
sys.path.insert(0,os.getcwd()); sys.argv=['walk46.py','1962','2026','w46']
import pandas as pd, numpy as np
_MARK="# ---- the walk "+"itself"
exec(open('walk46.py').read().split(_MARK)[0])
pw=pickle.load(open('cache/w46_carry.pkl','rb'))
def first(s):
    s=s.dropna() if hasattr(s,'dropna') else pd.Series(s)
    return s.index.min().date().isoformat() if len(s) else None
rows=[]
rows.append(('insured unemployment rate, weekly (U, L; the survey-week rate W, V; the closers)','spl (Department of Labor; the programme\'s transcription 1945-71, FRED IURSA)',first(spl)))
rows.append(('survey-week insured rate (W, V)','SI',first(SI)))
rows.append(('initial claims, weekly (I, K, the closer C)','ICfp (Department of Labor advance figures from Oct 2002; FRED ICSA before)',first(ICfp)))
rows.append(('state breadth (B)','BR (state insured rates: collection 59 transcription 1945-83, ETA 539 from 1986)',first(BR)))
rows.append(('unemployment rate, monthly (the hub X, the co-signer, the rate half)','g_asof / rate_asof (CPS via ALFRED UNRATE vintages)',first(g_asof)))
rows.append(('vacancy rate (the vacancy confirmer, the hub\'s hold, the starts x vacancy pair)','V0 (help-wanted composite before Dec 2000; JOLTS first prints; JOLTS vintages from Jul 2010)',first(V0)))
rows.append(('housing starts (the housing halves)','hh_asof (Census via ALFRED HOUST vintages from Jul 1960)',first(hh_asof)))
rows.append(('factory hours and nondurable employment (the hours pair)','hp_asof (CES via ALFRED AWHMAN, NDMANEMP vintages)',first(hp_asof)))
rows.append(('commercial paper spread (the spread confirmer)','GSP (H.15 prime paper / AA nonfinancial and financial; the bill)',first(GSP)))
rows.append(('S&P 500 daily close (the sudden stop K, the closer C)','_SPX',first(_SPX)))
print('object | series | first observation in the lab')
for a,b,c in rows: print(f'  {a} | {b} | {c}')
# the pre-1962 recessions each object could be scored on at the 1962 cut
PKm=[pd.Timestamp(x) for x in PK][:4]
for a,b,c in rows:
    if c: print(f'  {a[:40]:40} exists for', [p.strftime('%Y-%m') for p in PKm if pd.Timestamp(c)<=p-pd.DateOffset(months=12)])
# the calls of the walked record with each object masked before its own first reading are, by construction, the record:
# an object with no reading contributes nothing. Check: build_v at the walk-end lines equals the frozen record.
r,t=build_v(pw); print('frozen at walk-end lines: peaks',len(r['lags_p']),'others',r['other'])
