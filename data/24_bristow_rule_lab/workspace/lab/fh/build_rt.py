"""Fieldhouse NSA state claims -> the same real-time seasonal adjustment as the DOL panel
(mpanel4.py: month-of-year medians, moving seven-year window, refitted each December)."""
import sys, pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
sys.path.insert(0,'/home/claude/lab/dol')
WIN=7; OWN_YEARS=5
def month_factors(X):
    R=X-X.rolling(13,center=True,min_periods=7).mean()
    own={}; pooled={}
    for mth in range(1,13):
        sel=R[R.index.month==mth]
        if len(sel)==0: continue
        v=sel.values[~np.isnan(sel.values)]
        if len(v): pooled[mth]=float(np.median(v))
        for c in X.columns:
            q=sel[c].dropna()
            if len(q)>=3: own[(c,mth)]=float(np.median(q))
    if pooled:
        mu=np.median(list(pooled.values())); pooled={k:v-mu for k,v in pooled.items()}
    if own:
        mo_=np.median(list(own.values())); own={k:v-mo_ for k,v in own.items()}
    return own,pooled
def sa_realtime(P,own_years=OWN_YEARS,win=WIN):
    X=np.log(P.replace(0,np.nan)).interpolate().bfill()
    out=pd.DataFrame(index=X.index,columns=X.columns,dtype=float)
    for y in sorted(set(X.index.year)):
        hist=X[(X.index.year<y)&(X.index.year>=y-win)]
        m=(X.index.year==y)
        if len(hist)<24: out.loc[m]=X.loc[m]; continue
        own,pooled=month_factors(hist)
        for c in X.columns:
            use_own=len(X[X.index.year<y][c].dropna())>=own_years*12
            adj=np.array([(own.get((c,t.month),pooled.get(t.month,0.0)) if use_own
                           else pooled.get(t.month,0.0)) for t in X.index[m]])
            out.loc[m,c]=X.loc[m,c].values-adj
    return out.dropna(how='all')
L=pd.read_csv('FH_state_claims_nsa_log.csv',index_col=0,parse_dates=True)
P=np.exp(L)
parts=[]; nats={}
for ch in ('initial claims','continued weeks claimed'):
    cols=[c for c in P.columns if c.endswith('| '+ch)]
    SA=sa_realtime(P[cols]); parts.append(SA)
    N=sa_realtime(pd.DataFrame({'US':P[cols].sum(axis=1)}))['US']; nats[ch]=np.exp(N)
PAN=pd.concat(parts,axis=1); PAN.to_csv('FH_state_claims_sa_rt_log.csv')
pd.DataFrame(nats).to_csv('FH_nat_sa_rt.csv')
print(PAN.shape, PAN.index.min().date(), PAN.index.max().date())
