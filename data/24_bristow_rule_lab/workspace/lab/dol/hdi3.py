"""The amplitude filter, scaled to each channel's own noise.

Bry and Boschan's amplitude filter is conventionally set relative to the variability of the
series it is applied to, not in absolute units.  The causal monitor above used a single
thirty-log-point threshold for every jurisdiction and every era, which is why the crossing
arrives late in a shallow episode: a quiet state has to move as far as a volatile one
before its phase is allowed to turn.  Here the threshold is `kappa` times the channel's own
trailing standard deviation of monthly changes, with an optional floor.
"""
import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
PAN=pd.read_csv('/home/claude/lab/dol/US_state_monthly_4ch_sa.csv',index_col=0,parse_dates=True)
CHS=['initial claims','continued weeks claimed','weeks compensated','first payments']
SUB={ch:PAN[[c for c in PAN.columns if c.endswith('| '+ch)]] for ch in CHS}
PK=['1973-11','1980-01','1981-07','1990-07','2001-03','2007-12','2020-02','2023-06','2024-03']
S0=pd.Timestamp('1973-01-01').year*12+1
def phase_v(X,A,mph):
    """A: (T,N) per-channel amplitude threshold."""
    T,N=X.shape; out=np.zeros((T,N),dtype=np.int8)
    st=np.ones(N,dtype=np.int8); ext=np.where(np.isfinite(X[0]),X[0],0.0).copy()
    since=np.zeros(N,dtype=np.int32)
    for t in range(T):
        x=X[t]; a=A[t]; fin=np.isfinite(x)&np.isfinite(a); up=st==1
        np.copyto(ext,np.maximum(ext,x),where=np.isfinite(x)&up)
        np.copyto(ext,np.minimum(ext,x),where=np.isfinite(x)&~up)
        fd=fin&up&((ext-x)>=a)&(since>=mph); fu=fin&~up&((x-ext)>=a)&(since>=mph)
        fl=fd|fu
        st=np.where(fd,np.int8(-1),np.where(fu,np.int8(1),st))
        ext=np.where(fl,x,ext); since=np.where(fl,0,since+1); out[t]=st
    return out
def esri_calls(D,mn,r,pmin,cyc):
    n=len(D); on=D>=50.
    if r>1: on=np.convolve(on.astype(int),np.ones(r,dtype=int),'full')[:n]==r
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
def score(pairs,TT):
    hits=set(); other=0
    for pub,dt in pairs:
        if pub<S0: continue
        k=int(np.argmin(np.abs(TT-dt)))
        if abs(pub-TT[k])<=2 and abs(dt-TT[k])<=2 and k not in hits: hits.add(k)
        else: other+=1
    return hits,other
TT=np.array([pd.Timestamp(k+'-01').year*12+pd.Timestamp(k+'-01').month for k in PK])
COMBOS=[('initial claims',),('continued weeks claimed',),
        ('initial claims','continued weeks claimed'),
        ('initial claims','continued weeks claimed','weeks compensated','first payments')]
best={}
for chs in COMBOS:
    P=pd.concat([SUB[c] for c in chs],axis=1); mn=np.array([t.year*12+t.month for t in P.index])
    for sm in (2,3,4):
        K=P.rolling(sm).mean()*100.0; X=K.values
        for sw in (60,120):
            SD=K.diff().rolling(sw,min_periods=sw//2).std().values
            for kap in (2.,3.,4.,5.,6.,8.,10.,12.):
                for floor in (0.,10.,20.):
                    A=np.maximum(kap*SD,floor)
                    for mph in (6,9,12,15,18):
                        ph=phase_v(X,A,mph)
                        D=(ph>0).sum(axis=1)/np.isfinite(X).sum(axis=1)*100.0
                        for r in (1,2):
                            for pmin in (3,5,8):
                                for cyc in (15,18,24):
                                    h,o=score(esri_calls(D,mn,r,pmin,cyc),TT)
                                    key=(len(h),o)
                                    if key not in best:
                                        best[key]=(chs,sm,sw,kap,floor,mph,r,pmin,cyc,tuple(sorted(PK[i] for i in h)))
print('PEAKS  noise-scaled amplitude filter')
for key in sorted(best,key=lambda x:(-x[0],x[1]))[:14]:
    chs,sm,sw,kap,floor,mph,r,pmin,cyc,h=best[key]
    print(f'  {key[0]}/9 other {key[1]:2d}  chs={"+".join(c[:4] for c in chs)} sm={sm} sw={sw} '
          f'kappa={kap} floor={floor} mph={mph} r={r} pmin={pmin} cyc={cyc}')
    print(f'        {list(h)}')
