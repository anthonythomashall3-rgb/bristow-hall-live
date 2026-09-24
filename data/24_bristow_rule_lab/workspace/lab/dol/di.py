"""The diffusion index as the Economic and Social Research Institute actually builds it.

The first breadth object counted a jurisdiction as deteriorating when its claims stood a
fixed distance above their own trailing minimum.  That is a level test, and its threshold
has to be calibrated to how deep a recession turns out to be.  ESRI's historical diffusion
index does something different and simpler: it counts the share of component series whose
value is HIGHER THAN k MONTHS EARLIER, and reads the turning point off the fifty-per-cent
line.  Applied across jurisdictions rather than across indicators, and to claims, which
are counter-cyclical, the share rising is the share deteriorating.

Nothing in it is calibrated: no threshold, no depth, no window minimum.  Only k, the span
of the comparison, which is three months in ESRI's own index.
"""
import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
PAN=pd.read_csv('/home/claude/lab/dol/US_state_monthly_4ch_sa.csv',index_col=0,parse_dates=True)
CHS=['initial claims','continued weeks claimed','weeks compensated','first payments']
SUB={ch:PAN[[c for c in PAN.columns if c.endswith('| '+ch)]] for ch in CHS}
PK=['1973-11','1980-01','1981-07','1990-07','2001-03','2007-12','2020-02','2023-06','2024-03']
TR=['1975-03','1980-07','1982-11','1991-03','2001-11','2009-06','2020-04','2024-08','2026-05']
def mnum(idx): return np.array([t.year*12+t.month for t in idx])
S0=pd.Timestamp('1973-01-01').year*12+1
def DI(chs,sm,k):
    P=pd.concat([SUB[c] for c in chs],axis=1).rolling(sm).mean()
    d=P-P.shift(k)
    return ((d>0).sum(axis=1)/d.notna().sum(axis=1)*100.0).dropna()
def runlen(bl):
    out=np.zeros(len(bl),dtype=np.int32); c=0
    for i in range(len(bl)):
        c=c+1 if bl[i] else 0; out[i]=c
    return out
def calls(D,thb,line,reb,r,mp,up=True):
    """ESRI's clause: fire when the index has stood on the wrong side of `thb` for r
    months; date the turn at the last month it stood on the right side of `line`."""
    d=D.values; n=len(d); mn=mnum(D.index)
    sig = d if up else -d
    T = thb if up else -thb; LN = line if up else -line; RB = reb if up else -reb
    on=sig>=T
    if r>1: on = on & np.r_[False,on[:-1]]
    oi=np.flatnonzero(on)
    lastb=np.maximum.accumulate(np.where(sig<LN,np.arange(n),0))
    rp=np.flatnonzero(runlen(sig<RB)>=mp)
    out=[]; pos=0
    while True:
        p=np.searchsorted(oi,pos,'left')
        if p>=len(oi): break
        i=int(oi[p]); out.append((mn[i]+1,mn[lastb[i]]))
        q=np.searchsorted(rp,i+1,'left')
        if q>=len(rp): break
        pos=int(rp[q])+1
        if len(out)>80: break
    return out
def score(pairs,T):
    TT=np.array([pd.Timestamp(k+'-01').year*12+pd.Timestamp(k+'-01').month for k in T])
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
    best={}
    for chs in COMBOS:
        for sm in (1,2,3,4,6):
            for k in (1,3,6,9,12):
                D=DI(chs,sm,k)
                for thb in (50.,55.,60.,65.,70.,75.,80.):
                    for line in (40.,45.,50.,55.,60.,65.,70.):
                        if line>thb: continue
                        for reb in (25.,30.,35.,40.,45.,50.):
                            if reb>=thb: continue
                            for r in (1,2,3):
                                for mp in (1,2,3,4,6):
                                    h,o=score(calls(D,thb,line,reb,r,mp,up),T)
                                    key=(len(h),o)
                                    if key not in best:
                                        best[key]=((chs,sm,k,thb,line,reb,r,mp),tuple(sorted(T[i] for i in h)))
    print(f'=== {tag}  (ESRI diffusion clause on the state panel)')
    for key in sorted(best,key=lambda x:(-x[0],x[1]))[:10]:
        par,h=best[key]
        print(f'  {key[0]}/9  other {key[1]:2d}   chs={"+".join(c[:4] for c in par[0])} sm={par[1]} k={par[2]} '
              f'thb={par[3]} line={par[4]} reb={par[5]} r={par[6]} mp={par[7]}')
        print(f'        {list(h)}')
