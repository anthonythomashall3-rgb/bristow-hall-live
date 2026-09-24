"""A weekly breadth index across the states, from the same ETA 539 file.

Fifty-three jurisdictions report initial claims every week from February 1986.  Each is
seasonally adjusted on its own by the same iterated decomposition, then each is asked the
same question the rule asks of any channel: has activity in this state fallen away from
its own recent best?  The index is the share of states answering yes.  Breadth does not
depend on how deep any one state falls, so it does not need a threshold calibrated to the
amplitude of a particular recession.
"""
import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
d=pd.read_csv('/home/claude/lab/dol/ar539.csv',low_memory=False)
d['wk']=pd.to_datetime(d['c2'],errors='coerce'); d=d.dropna(subset=['wk'])
d['ic']=pd.to_numeric(d['c3'],errors='coerce')
P=d.pivot_table(index='wk',columns='st',values='ic',aggfunc='sum').sort_index()
P=P[P.index>=pd.Timestamp('1986-02-01')]
P=P.loc[:,P.notna().mean()>0.95]
grid=pd.date_range(P.index.min(),P.index.max(),freq='W-SAT')
P=P.reindex(P.index.union(grid)).interpolate(method='time').reindex(grid)
print('states',P.shape)
def woy(idx): return np.array([min(53,(t.dayofyear-1)//7+1) for t in idx])
def stl(s,passes=3):
    x=np.log(s.astype(float).replace(0,np.nan)).interpolate().bfill().ffill()
    w=woy(x.index); seas=np.zeros(len(x))
    for p in range(passes):
        de=pd.Series(x.values-seas,index=x.index)
        span=53 if p==0 else 27
        tr=de.rolling(span,center=True,min_periods=max(6,span//3)).mean().bfill().ffill()
        r=x.values-tr.values; ns=np.zeros(len(x))
        for k in range(1,54):
            m=(w==k)
            if m.sum(): ns[m]=np.mean(r[m])
        ns-=ns.mean(); seas=ns
    return pd.Series(x.values-seas,index=x.index)      # log level, seasonally adjusted
SA=pd.DataFrame({c:stl(P[c]) for c in P.columns})
SA.to_csv('/home/claude/lab/dol/US_state_claims_sa_log.csv')
print('saved', SA.shape, SA.index.min().date(), SA.index.max().date())
