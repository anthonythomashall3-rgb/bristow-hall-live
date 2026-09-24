"""Re-fit the two real-time detectors on the corrected seasonal adjustment.

The month-of-year factors were re-estimated on a moving seven-year window (see
monthly_states2.py), which cut the residual seasonality in the adjusted national series
from 10.4 log points to 4.5.  The detector settings chosen on the old series no longer
fit, so they are chosen again on the corrected one, on the same criterion: the number of
turning points published within two months and dated within two months, then the number of
other calls.
"""
import pandas as pd, numpy as np, itertools, warnings; warnings.filterwarnings('ignore')
M=pd.read_csv('/home/claude/lab/dol/US_state_claims_monthly_sa_rt.csv',index_col=0,parse_dates=True)
NC=pd.read_csv('/home/claude/lab/dol/US_nat_claims_monthly_rt.csv',index_col=0,parse_dates=True)
START=pd.Timestamp('1973-01-01')
def mo(t): return pd.Timestamp(t.year,t.month,1)
def md(x,y): return (x.year-y.year)*12+(x.month-y.month)
PK={'1973-11':'NBER','1980-01':'NBER','1981-07':'NBER','1990-07':'NBER','2001-03':'NBER',
    '2007-12':'NBER','2020-02':'NBER','2023-06':'Paper 1','2024-03':'Paper 1'}
TR={'1975-03':'NBER','1980-07':'NBER','1982-11':'NBER','1991-03':'NBER','2001-11':'NBER',
    '2009-06':'NBER','2020-04':'NBER','2024-08':'Paper 1','2026-05':'Paper 1'}
_bc={}
def breadth(sm,L,gap):
    k=(sm,L,gap)
    if k not in _bc:
        K=M.rolling(sm).mean()*100.0
        S=K-K.rolling(L,min_periods=L//2).min()
        _bc[k]=((S>=gap).sum(axis=1)/S.notna().sum(axis=1)*100.0).dropna()
    return _bc[k]
def peaks(Bd,thb,reb,r,mp,line):
    b=Bd.values; idx=Bd.index; out=[]; state='armed'; off=0
    for i in range(r,len(b)):
        if state=='called':
            off = off+1 if b[i]<reb else 0
            if off>=mp: state='armed'; off=0
            continue
        if bool(np.all(b[i-r+1:i+1]>=thb)):
            j=i
            while j>0 and b[j]>=line: j-=1
            out.append((idx[i]+pd.DateOffset(months=1),mo(idx[j]))); state='called'; off=0
    return out
_nc={}
def natgap(sm,L):
    k=(sm,L)
    if k not in _nc:
        N=(np.log(NC.iloc[:,0])*100.0).rolling(sm).mean()
        G=N-N.rolling(L,min_periods=L//2).min()
        _nc[k]=pd.concat([N.rename('n'),G.rename('g')],axis=1).dropna()
    return _nc[k]
def troughs(sm,L,run,drop,arm,rearm,mp):
    df=natgap(sm,L); n=df['n'].values; g=df['g'].values; idx=df.index
    out=[]; state='quiet'; off=0; nmax=-1e9; nmax_i=0; fall=0; prev=n[0]
    for i in range(1,len(n)):
        if n[i]>nmax: nmax=n[i]; nmax_i=i; fall=0
        elif n[i]<prev: fall+=1
        else: fall=0
        prev=n[i]
        if state=='called':
            off = off+1 if g[i]<rearm else 0
            if off>=mp: state='quiet'; off=0
            continue
        if state=='quiet':
            if g[i]>=arm: state='armed'; nmax=n[i]; nmax_i=i; fall=0
            continue
        if fall>=run and (nmax-n[i])>=drop and g[nmax_i]>=arm:
            out.append((idx[i]+pd.DateOffset(months=1),mo(idx[nmax_i]))); state='called'; off=0
    return out
def score(calls,T):
    hits={}; other=0
    for pub,dt in sorted(calls):
        if pub<START: continue
        near=min(T,key=lambda k: abs(md(dt,pd.Timestamp(k+'-01'))))
        lag=md(mo(pub),pd.Timestamp(near+'-01')); err=md(dt,pd.Timestamp(near+'-01'))
        if abs(lag)<=2 and abs(err)<=2 and near not in hits: hits[near]=(lag,err)
        else: other+=1
    return hits,other
if __name__=='__main__':
    res=[]
    for sm in [1,2,3]:
        for L in [18,24,30,36,48]:
            for gap in [10.,15.,20.,25.,30.]:
                Bd=breadth(sm,L,gap)
                for thb in [45.,50.,55.,60.,65.,70.,75.]:
                    for line in [t for t in [40.,45.,50.,55.,60.,65.,70.] if t<=thb]:
                        for reb in [15.,20.,25.,30.,35.,40.]:
                            if reb>=thb: continue
                            for r in [1,2]:
                                for mp in [1,2,3]:
                                    h,o=score(peaks(Bd,thb,reb,r,mp,line),PK)
                                    res.append((len(h),-o,sm,L,gap,thb,reb,r,mp,line,tuple(sorted(h))))
    res.sort(reverse=True)
    print('PEAKS  best by (hits, fewest other):')
    seen=set()
    for row in res[:4000]:
        key=(row[0],row[1])
        if key in seen: continue
        seen.add(key)
        n,no,sm,L,gap,thb,reb,r,mp,line,h=row
        print(f'  {n}/9  other {-no:2d}   sm={sm} L={L} gap={gap} thb={thb} reb={reb} r={r} mp={mp} line={line}')
        print(f'        {list(h)}')
        if len(seen)>=12: break
