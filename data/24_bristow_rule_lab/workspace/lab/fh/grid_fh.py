import sys; sys.path.insert(0,'/home/claude'); sys.path.insert(0,'/home/claude/lab/fh')
import bristow_rule_v3 as B, pandas as pd, numpy as np, warnings, itertools; warnings.filterwarnings('ignore')
from test1 import PK, TR
import io, contextlib
def score_q(calls, ref, tol=6, start='1949-01-01'):
    used=set(); rows=[]
    for r in ref:
        best=None
        for i,(pub,dt) in enumerate(calls):
            if i in used: continue
            e=B._md(dt,r)
            if abs(e)<=tol and (best is None or abs(e)<abs(best[1])): best=(i,e,pub)
        if best is None: rows.append(None); continue
        used.add(best[0]); rows.append((best[1],B._md(best[2],r)))
    other=[c for i,c in enumerate(calls) if i not in used and c[0]>=pd.Timestamp(start)]
    hit=sum(r is not None for r in rows); ex=sum(r is not None and r[0]==0 for r in rows); w1=sum(r is not None and abs(r[0])<=1 for r in rows)
    return hit,ex,w1,len(other),rows,other
basis=sys.argv[1] if len(sys.argv)>1 else 'sa_rt'
P=pd.read_csv(f'FH_state_claims_{basis}_log.csv',index_col=0,parse_dates=True)
res=[]
for chs in (('initial claims','continued weeks claimed'),('initial claims',),('continued weeks claimed',)):
    cols=[c for c in P.columns if any(c.endswith('| '+x) for x in chs)]
    for sm in (1,2):
        X=P[cols].rolling(sm).mean().dropna(how='all') if sm>1 else P[cols]
        for amp in range(24,65,4):
            for mph in (8,10,13,16):
                D=B.claims_diffusion(X,float(amp),mph)
                for pm in (4,5):
                    for line in (50.,):
                        calls=B.diffusion_peak_calls(D,line=line,phase_min=pm)
                        h,ex,w1,oth,rows,other=score_q(calls,PK)
                        res.append(('+'.join(x[:4] for x in chs),sm,amp,mph,pm,h,ex,w1,oth,[None if r is None else r[0] for r in rows]))
res.sort(key=lambda r:(-r[5],r[8],-r[7],-r[6]))
for r in res[:25]: print(r)
