"""The real-time record, 1973 to 2026, on the corrected panel.

PEAK   the causal historical diffusion index across the fifty-three jurisdictions'
       initial claims and continued weeks claimed, read with ESRI's fifty-per-cent clause
       and censored by ESRI's own duration rule.
TROUGH the level clause of the rule itself: national initial claims reach a maximum inside
       an armed episode and fall away from it; the trough is dated at the maximum.
"""
import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
PAN=pd.read_csv('/home/claude/lab/dol/US_state_monthly_4ch_sa.csv',index_col=0,parse_dates=True)
NAT=pd.read_csv('/home/claude/lab/dol/US_nat_monthly_4ch_sa.csv',index_col=0,parse_dates=True)
CHS=['initial claims','continued weeks claimed','weeks compensated','first payments']
SUB={ch:PAN[[c for c in PAN.columns if c.endswith('| '+ch)]] for ch in CHS}
PK={'1973-11':'NBER','1980-01':'NBER','1981-07':'NBER','1990-07':'NBER','2001-03':'NBER',
    '2007-12':'NBER','2020-02':'NBER','2023-06':'Paper 1, rolling episode onset',
    '2024-03':'Paper 1, national labour-market recession onset'}
TR={'1975-03':'NBER','1980-07':'NBER','1982-11':'NBER','1991-03':'NBER','2001-11':'NBER',
    '2009-06':'NBER','2020-04':'NBER','2024-08':'Paper 1, national labour-market recession end',
    '2026-05':'Paper 1, rolling episode end'}
S0=pd.Timestamp('1973-01-01').year*12+1
def mn_of(idx): return np.array([t.year*12+t.month for t in idx],dtype=np.int64)
def lab(m): return f'{(m-1)//12:04d}-{((m-1)%12)+1:02d}'
def phase(X,amp,mph):
    T,N=X.shape; out=np.zeros((T,N),dtype=np.int8)
    st=np.ones(N,dtype=np.int8); ext=np.where(np.isfinite(X[0]),X[0],0.0).copy()
    since=np.zeros(N,dtype=np.int32)
    for t in range(T):
        x=X[t]; fin=np.isfinite(x); up=st==1
        np.copyto(ext,np.maximum(ext,x),where=fin&up)
        np.copyto(ext,np.minimum(ext,x),where=fin&~up)
        fd=fin&up&((ext-x)>=amp)&(since>=mph); fu=fin&~up&((x-ext)>=amp)&(since>=mph)
        fl=fd|fu
        st=np.where(fd,np.int8(-1),np.where(fu,np.int8(1),st))
        ext=np.where(fl,x,ext); since=np.where(fl,0,since+1); out[t]=st
    return out
def hdi(chs,sm,amp,mph):
    P=pd.concat([SUB[c] for c in chs],axis=1)
    X=(P.rolling(sm).mean()*100.0).values
    ph=phase(X,amp,mph)
    return (ph>0).sum(axis=1)/np.isfinite(X).sum(axis=1)*100.0, mn_of(P.index)
def esri_calls(D,mn,r,pmin,cyc):
    n=len(D); on=D>=50.
    if r>1:
        on=np.convolve(on.astype(int),np.ones(r,dtype=int),'full')[:n]==r
    lastb=np.maximum.accumulate(np.where(D<50.,np.arange(n),0))
    out=[]; i=0; last=-10**6; state=0; off=0
    while i<n:
        if state==0 and on[i] and (mn[i]+1-last)>=cyc:
            out.append((mn[i]+1,mn[lastb[i]])); last=mn[i]+1; state=1; off=0
        elif state==1:
            off = off+1 if D[i]<50. else 0
            if off>=pmin: state=0
        i+=1
    return out
def troughs(ch,sm,L,run,drop,arm,rearm,mp):
    N=(np.log(NAT[ch])*100.0).rolling(sm).mean()
    G=N-N.rolling(L,min_periods=L//2).min()
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
def report(pairs,T,title):
    TT={k:pd.Timestamp(k+'-01').year*12+pd.Timestamp(k+'-01').month for k in T}
    print(f'--- {title}')
    hits={}; other=[]
    for pub,dt in sorted(pairs):
        if pub<S0: continue
        near=min(TT,key=lambda k: abs(dt-TT[k])); lag=pub-TT[near]; err=dt-TT[near]
        ok=abs(lag)<=2 and abs(err)<=2 and near not in hits
        if ok: hits[near]=(lag,err)
        else: other.append((pub,dt))
        print(f'   {"HIT " if ok else "    "} published {lab(pub)}  dated {lab(dt)}   '
              f'nearest {near} ({T[near]})  lag {lag:+3d}  error {err:+3d}')
    print(f'   => {len(hits)} of {len(T)} inside two months at both;  {len(other)} other calls')
    print(f'   => never called: {[k for k in T if k not in hits]}')
    return hits,other
D,mn=hdi(('initial claims','continued weeks claimed'),1,48.,13)
hp,op=report(esri_calls(D,mn,1,5,15),PK,
       'PEAKS  causal historical diffusion index across the fifty-three jurisdictions\' initial '
       'claims and continued weeks claimed, ESRI clause, 1973-2026')
ht,ot=report(troughs('initial claims',2,30,1,1.,50.,5.,3),TR,
       'TROUGHS  national initial claims, the level clause, 1973-2026')
import numpy as np
def stats(h):
    lg=[v[0] for v in h.values()]; er=[v[1] for v in h.values()]
    return (np.mean(np.abs(lg)),np.mean(lg),np.mean(np.abs(er)),np.mean(er))
print()
print('peaks : mean |lag| %.2f  mean lag %+0.2f  mean |error| %.2f  mean error %+0.2f'%stats(hp))
print('troughs: mean |lag| %.2f  mean lag %+0.2f  mean |error| %.2f  mean error %+0.2f'%stats(ht))
