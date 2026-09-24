"""Two keys: the diffusion index dates the turn, the level field confirms it.

ESRI reads its turning point off the fifty-per-cent line of a diffusion index, and the
Institute does not publish on the crossing alone - the crossing is confirmed against the
composite index and censored by a minimum phase length, which is Bry and Boschan's rule.
The two clauses do different jobs and are kept separate here:

    DATE   the share of state channels higher than k months earlier crosses the line;
           the turn is dated at the last month the share stood below it.
    PUBLISH the call is made only once the level field confirms - the share of channels
           standing `gap` log points above their own trailing minimum reaches `conf` -
           and never within `cens` months of the previous call.

The date therefore comes from the fast, scale-free object and the publication lag from
the slow, confirming one.
"""
import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
PAN=pd.read_csv('/home/claude/lab/dol/US_state_monthly_4ch_sa.csv',index_col=0,parse_dates=True)
NAT=pd.read_csv('/home/claude/lab/dol/US_nat_monthly_4ch_sa.csv',index_col=0,parse_dates=True)
CHS=['initial claims','continued weeks claimed','weeks compensated','first payments']
SUB={ch:PAN[[c for c in PAN.columns if c.endswith('| '+ch)]] for ch in CHS}
PK=['1973-11','1980-01','1981-07','1990-07','2001-03','2007-12','2020-02','2023-06','2024-03']
TR=['1975-03','1980-07','1982-11','1991-03','2001-11','2009-06','2020-04','2024-08','2026-05']
S0=pd.Timestamp('1973-01-01').year*12+1
def mnum(idx): return np.array([t.year*12+t.month for t in idx],dtype=np.int64)
def panel(chs): return pd.concat([SUB[c] for c in chs],axis=1)
def DI(P,sm,k):
    Q=P.rolling(sm).mean(); d=Q-Q.shift(k)
    return ((d>0).sum(axis=1)/d.notna().sum(axis=1)*100.0)
def LEV(P,sm,L,gap):
    K=P.rolling(sm).mean()*100.0; S=K-K.rolling(L,min_periods=L//2).min()
    return ((S>=gap).sum(axis=1)/S.notna().sum(axis=1)*100.0)
def machine(di,lv,mn,thb,line,conf,reb,r,W,cens,up=True):
    s = di.copy() if up else -di.copy()
    T,LN,RB = (thb,line,reb) if up else (-thb,-line,-reb)
    n=len(s); on=s>=T
    if r>1: on=on & np.r_[False,on[:-1]]
    lastb=np.maximum.accumulate(np.where(s<LN,np.arange(n),0))
    out=[]; i=0; last_pub=-10**6; state=0; cand=-1; cross=-1
    while i<n:
        if state==0:
            if on[i] and np.isfinite(s[i]):
                cross=i; cand=lastb[i]; state=1
        elif state==1:
            if i-cross>W: state=0
            elif np.isfinite(lv[i]) and lv[i]>=conf and (mn[i]+1-last_pub)>=cens:
                out.append((mn[i]+1,mn[cand])); last_pub=mn[i]+1; state=2
        else:
            if np.isfinite(s[i]) and s[i]<RB: state=0
        i+=1
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
COMBOS=[('initial claims',),('continued weeks claimed',),
        ('initial claims','continued weeks claimed'),
        ('initial claims','continued weeks claimed','weeks compensated','first payments')]
for tag,T,up in [('PEAKS',PK,True),('TROUGHS',TR,False)]:
    best={}
    for chs in COMBOS:
        P=panel(chs); mn=mnum(P.index)
        for sm in (1,2,3,4):
            for k in (1,3,6):
                di=DI(P,sm,k).values
                for Lg,gap in [(24,20.),(24,25.),(36,20.),(36,25.),(36,30.),(48,25.)]:
                    lv=LEV(P,sm,Lg,gap).values
                    for thb in (55.,60.,65.,70.,75.):
                        for line in (45.,50.,55.,60.):
                            if line>thb: continue
                            for conf in (40.,50.,60.,70.,80.):
                                for reb in (35.,40.,45.,50.):
                                    if reb>=thb: continue
                                    for W in (3,6,9,12,18):
                                        for cens in (12,18,24):
                                            h,o=score(machine(di,lv,mn,thb,line,conf,reb,1,W,cens,up),T)
                                            key=(len(h),o)
                                            if key not in best:
                                                best[key]=(chs,sm,k,Lg,gap,thb,line,conf,reb,W,cens)
    print(f'=== {tag}')
    for key in sorted(best,key=lambda x:(-x[0],x[1]))[:10]:
        chs,sm,k,Lg,gap,thb,line,conf,reb,W,cens=best[key]
        print(f'  {key[0]}/9 other {key[1]:2d}  chs={"+".join(c[:4] for c in chs)} sm={sm} k={k} '
              f'L={Lg} gap={gap} thb={thb} line={line} conf={conf} reb={reb} W={W} cens={cens}')
