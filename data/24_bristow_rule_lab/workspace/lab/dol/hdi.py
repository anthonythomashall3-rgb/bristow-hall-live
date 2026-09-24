"""The historical diffusion index, built the way ESRI builds it, but causally.

ESRI's historical diffusion index is not the share of series that rose this month.  It is
built by first putting a turning point on EACH component series, then setting the series to
+1 from its own trough to its own peak and to -1 from its peak to its own trough, and
taking the share at +1.  The result changes only when a component turns, so it is a step
function with n+1 levels rather than a noisy share, and that is why the fifty-per-cent
crossing is readable at all.

Bry and Boschan's procedure is two-sided, so it cannot be used in real time.  The causal
form of the same idea is a monitor: a channel is in the deteriorating phase until it has
fallen `amp` log points from its running maximum and `mph` months have passed since its
last turn, and in the improving phase until the mirror condition.  Nothing about the future
enters.  Claims are counter-cyclical, so a channel in its rising phase is a jurisdiction
whose labour market is deteriorating.

The turning point is then read with ESRI's own clause and censored by ESRI's own duration
rule - a phase of at least five months and a cycle of at least fifteen (Cabinet Office,
Economic and Social Research Institute, 23 July 2026, note 3).
"""
import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
PAN=pd.read_csv('/home/claude/lab/dol/US_state_monthly_4ch_sa.csv',index_col=0,parse_dates=True)
CHS=['initial claims','continued weeks claimed','weeks compensated','first payments']
SUB={ch:PAN[[c for c in PAN.columns if c.endswith('| '+ch)]] for ch in CHS}
PK=['1973-11','1980-01','1981-07','1990-07','2001-03','2007-12','2020-02','2023-06','2024-03']
TR=['1975-03','1980-07','1982-11','1991-03','2001-11','2009-06','2020-04','2024-08','2026-05']
S0=pd.Timestamp('1973-01-01').year*12+1
def phase(X,amp,mph):
    """X: (T,N) log levels x100.  Returns (T,N) int: +1 rising (deteriorating), -1 falling."""
    T,N=X.shape; out=np.zeros((T,N),dtype=np.int8)
    st=np.ones(N,dtype=np.int8); ext=np.where(np.isfinite(X[0]),X[0],0.0).copy(); since=np.zeros(N,dtype=np.int32)
    for t in range(T):
        x=X[t]; fin=np.isfinite(x)
        up=st==1
        np.copyto(ext,np.maximum(ext,x),where=fin&up)
        np.copyto(ext,np.minimum(ext,x),where=fin&~up)
        flip_dn = fin&up&((ext-x)>=amp)&(since>=mph)
        flip_up = fin&~up&((x-ext)>=amp)&(since>=mph)
        fl=flip_dn|flip_up
        st=np.where(flip_dn,np.int8(-1),np.where(flip_up,np.int8(1),st))
        ext=np.where(fl,x,ext); since=np.where(fl,0,since+1)
        out[t]=st
    return out
def runlen(bl):
    out=np.zeros(len(bl),dtype=np.int32); c=0
    for i in range(len(bl)):
        c=c+1 if bl[i] else 0; out[i]=c
    return out
def esri_calls(D,mn,r,phase_min,cycle_min,up=True):
    """D: the share deteriorating, per cent.  For a peak the share crosses ABOVE fifty and
    stays; the peak is the last month it stood below."""
    s=D if up else -D; TH=50. if up else -50.
    n=len(s); on=s>=TH
    if r>1:
        k=np.ones(r,dtype=int); on=np.convolve(on.astype(int),k,'full')[:n]==r
    lastb=np.maximum.accumulate(np.where(s<TH,np.arange(n),0))
    out=[]; i=0; last=-10**6; state=0
    while i<n:
        if state==0 and on[i] and (mn[i]+1-last)>=cycle_min:
            out.append((mn[i]+1,mn[lastb[i]])); last=mn[i]+1; state=1; off=0
        elif state==1:
            off = off+1 if s[i]<TH else 0
            if off>=phase_min: state=0
        i+=1
        if len(out)>80: break
    return out
def score(pairs,TT):
    hits=set(); other=0
    for pub,dt in pairs:
        if pub<S0: continue
        k=int(np.argmin(np.abs(TT-dt)))
        if abs(pub-TT[k])<=2 and abs(dt-TT[k])<=2 and k not in hits: hits.add(k)
        else: other+=1
    return hits,other
COMBOS=[('initial claims',),('continued weeks claimed',),('weeks compensated',),
        ('initial claims','continued weeks claimed'),
        ('initial claims','continued weeks claimed','weeks compensated','first payments')]
for tag,T,up in [('PEAKS',PK,True),('TROUGHS',TR,False)]:
    TT=np.array([pd.Timestamp(k+'-01').year*12+pd.Timestamp(k+'-01').month for k in T])
    best={}
    for chs in COMBOS:
        P=pd.concat([SUB[c] for c in chs],axis=1)
        mn=np.array([t.year*12+t.month for t in P.index],dtype=np.int64)
        for sm in (2,3,4,6):
            X=(P.rolling(sm).mean()*100.0).values
            for amp in (20.,25.,30.,35.,40.,45.,50.,60.,75.):
                for mph in (6,9,12,15,18,24):
                    ph=phase(X,amp,mph)
                    D=(ph>0).sum(axis=1)/np.isfinite(X).sum(axis=1)*100.0
                    for r in (1,2,3,4,5):
                        for pmin in (3,5,8):
                            for cyc in (15,18,24,30,36):
                                h,o=score(esri_calls(D,mn,r,pmin,cyc,up),TT)
                                key=(len(h),o)
                                if key not in best:
                                    best[key]=(chs,sm,amp,mph,r,pmin,cyc,tuple(sorted(T[i] for i in h)))
    print(f'=== {tag}  (causal historical diffusion index, ESRI clause)')
    for key in sorted(best,key=lambda x:(-x[0],x[1]))[:12]:
        chs,sm,amp,mph,r,pmin,cyc,h=best[key]
        print(f'  {key[0]}/9 other {key[1]:2d}  chs={"+".join(c[:4] for c in chs)} sm={sm} amp={amp} '
              f'mph={mph} r={r} phase_min={pmin} cycle_min={cyc}')
        print(f'        {list(h)}')
