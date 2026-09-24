"""The trough clause, searched again on the corrected national series."""
import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
NAT=pd.read_csv('/home/claude/lab/dol/US_nat_monthly_4ch_sa.csv',index_col=0,parse_dates=True)
PANEL=pd.read_csv('/home/claude/lab/dol/US_state_monthly_4ch_sa.csv',index_col=0,parse_dates=True)
TR=['1975-03','1980-07','1982-11','1991-03','2001-11','2009-06','2020-04','2024-08','2026-05']
TT=np.array([pd.Timestamp(k+'-01').year*12+pd.Timestamp(k+'-01').month for k in TR])
S0=pd.Timestamp('1973-01-01').year*12+1
CH=list(NAT.columns)
def mn_of(idx): return np.array([t.year*12+t.month for t in idx],dtype=np.int64)
def series(name):
    if name in CH: return np.log(NAT[name])*100.0
    a,b=name.split('+')
    return (np.log(NAT[a])*100.0+np.log(NAT[b])*100.0)/2.0
def troughs(S,sm,L,run,drop,arm,rearm,mp):
    N=S.rolling(sm).mean(); G=N-N.rolling(L,min_periods=L//2).min()
    df=pd.concat([N.rename('n'),G.rename('g')],axis=1).dropna()
    n=df['n'].values; g=df['g'].values; mn=mn_of(df.index)
    out=[]; state='quiet'; off=0; nmax=-1e9; ni=0; fall=0; prev=n[0]
    for i in range(1,len(n)):
        if n[i]>nmax: nmax=n[i]; ni=i; fall=0
        elif n[i]<prev: fall+=1
        else: fall=0
        prev=n[i]
        if state=='called':
            off = off+1 if g[i]<rearm else 0
            if off>=mp: state='quiet'; off=0
            continue
        if state=='quiet':
            if g[i]>=arm: state='armed'; nmax=n[i]; ni=i; fall=0
            continue
        if fall>=run and (nmax-n[i])>=drop and g[ni]>=arm:
            out.append((mn[i]+1,mn[ni])); state='called'; off=0
    return out
def score(pairs):
    hits=set(); other=0
    for pub,dt in pairs:
        if pub<S0: continue
        k=int(np.argmin(np.abs(TT-dt)))
        if abs(pub-TT[k])<=2 and abs(dt-TT[k])<=2 and k not in hits: hits.add(k)
        else: other+=1
    return hits,other
best={}
NAMES=CH+['initial claims+continued weeks claimed','initial claims+first payments',
          'continued weeks claimed+weeks compensated']
for nm in NAMES:
    S=series(nm)
    for sm in (1,2,3,4):
        for L in (12,18,24,30,36,48):
            for run in (1,2,3):
                for drop in (0.5,1.,2.,3.,5.,8.,12.):
                    for arm in (15.,20.,25.,30.,35.,40.,50.,60.):
                        for rearm in (2.,5.,10.,15.,20.,25.,30.):
                            if rearm>=arm: continue
                            for mp in (1,2,3,4,6):
                                h,o=score(troughs(S,sm,L,run,drop,arm,rearm,mp))
                                key=(len(h),o)
                                if key not in best: best[key]=(nm,sm,L,run,drop,arm,rearm,mp,tuple(sorted(TR[i] for i in h)))
print('TROUGHS')
for key in sorted(best,key=lambda x:(-x[0],x[1]))[:14]:
    nm,sm,L,run,drop,arm,rearm,mp,h=best[key]
    print(f'  {key[0]}/9 other {key[1]:2d}  {nm} sm={sm} L={L} run={run} drop={drop} arm={arm} rearm={rearm} mp={mp}')
    print(f'        {list(h)}')
