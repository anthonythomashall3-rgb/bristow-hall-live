"""Shipped real-time clauses on the Fieldhouse panel, 1947-2024: twelve NBER peaks and troughs."""
import sys; sys.path.insert(0,'/home/claude'); sys.path.insert(0,'/home/claude/lab/rt')
import bristow_rule_v3 as B, pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
PK=[pd.Timestamp(x) for x in ('1948-11','1953-07','1957-08','1960-04','1969-12','1973-11','1980-01','1981-07','1990-07','2001-03','2007-12','2020-02')]
TR=[pd.Timestamp(x) for x in ('1949-10','1954-05','1958-04','1961-02','1970-11','1975-03','1980-07','1982-11','1991-03','2001-11','2009-06','2020-04')]
def score(calls, ref, label, tol=6):
    used=set(); rows=[]
    for r in ref:
        best=None
        for i,(pub,dt) in enumerate(calls):
            if i in used: continue
            e=B._md(dt,r)
            if abs(e)<=tol and (best is None or abs(e)<abs(best[1])): best=(i,e,pub)
        if best is None: rows.append((r,None,None,None)); continue
        used.add(best[0]); rows.append((r,calls[best[0]][1],best[1],B._md(best[2],r)))
    other=[c for i,c in enumerate(calls) if i not in used and c[0]>=pd.Timestamp('1949-01-01')]
    hit=sum(r[1] is not None for r in rows); ex=sum(r[2]==0 for r in rows); w1=sum(r[2] is not None and abs(r[2])<=1 for r in rows)
    print(f'{label}: {hit}/12 called, {ex} exact, {w1} within 1, other calls {len(other)}')
    print('   '+'  '.join(f'{r[0]:%Y-%m}:{"-" if r[2] is None else f"{r[2]:+d}/{r[3]:+d}m"}' for r in rows))
    if other: print('   other:',[(p.strftime('%Y-%m'),d.strftime('%Y-%m')) for p,d in other])
    return hit,ex,w1,len(other)
if __name__=='__main__':
    for basis in ('sa',):
        P=pd.read_csv(f'FH_state_claims_{basis}_log.csv',index_col=0,parse_dates=True)
        for sm in (1,2,3):
            X=P.rolling(sm).mean() if sm>1 else P
            D=B.claims_diffusion(X.dropna(how='all'),48.,13)
            for pm in (4,5):
                calls=B.diffusion_peak_calls(D,phase_min=pm)
                score(calls,PK,f'PEAK  diffusion(amp48,mph13) smooth {sm} phase_min {pm}  [{basis}]')
        nat=pd.read_csv('FH_national.csv',index_col=0,parse_dates=True)
        for col in ('US_IC_SA','US_CC_SA'):
            s=np.log(nat[col].dropna())
            for sm in (1,2,3):
                calls=B.level_trough_calls(s,smooth=sm)
                score(calls,TR,f'TROUGH level clause on {col} smooth {sm}')
