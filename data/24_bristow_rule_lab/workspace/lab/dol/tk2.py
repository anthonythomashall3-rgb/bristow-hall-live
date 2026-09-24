"""Two keys: the diffusion index dates the turn, the level field confirms it.

ESRI's own current statement of its procedure (Cabinet Office, Economic and Social
Research Institute, "第22回景気動向指数研究会について", 23 July 2026, note 3) makes the
turning point the month immediately before its historical diffusion index crosses fifty
per cent, and then requires three further things before the date is set: that the change
has spread to nearly all the components, that the quantitative change is at least as large
as the smallest past reference phase, and that the phase has run five months and the cycle
fifteen.  The detector here has the same three parts.

    DATE      the share of state channels higher than k months earlier crosses the line;
              the turn is dated at the last month the share stood on the other side.
    CONFIRM   the level field - the share of channels standing `gap` log points above
              their own trailing minimum - reaches `conf` within `W` months.
    CENSOR    no call within `cens` months of the previous one.
"""
import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
PAN=pd.read_csv('/home/claude/lab/dol/US_state_monthly_4ch_sa.csv',index_col=0,parse_dates=True)
CHS=['initial claims','continued weeks claimed','weeks compensated','first payments']
SUB={ch:PAN[[c for c in PAN.columns if c.endswith('| '+ch)]] for ch in CHS}
PK=['1973-11','1980-01','1981-07','1990-07','2001-03','2007-12','2020-02','2023-06','2024-03']
TR=['1975-03','1980-07','1982-11','1991-03','2001-11','2009-06','2020-04','2024-08','2026-05']
S0=pd.Timestamp('1973-01-01').year*12+1
def panel(chs): return pd.concat([SUB[c] for c in chs],axis=1)
def DI(P,sm,k):
    Q=P.rolling(sm).mean(); d=Q-Q.shift(k)
    return ((d>0).sum(axis=1)/d.notna().sum(axis=1)*100.0).values
def LEV(P,sm,L,gap):
    K=P.rolling(sm).mean()*100.0; S=K-K.rolling(L,min_periods=L//2).min()
    return ((S>=gap).sum(axis=1)/S.notna().sum(axis=1)*100.0).values
def nextge(v,thr):
    """first index j>=i with v[j]>=thr, for every i."""
    n=len(v); out=np.full(n,n,dtype=np.int64); nxt=n
    for i in range(n-1,-1,-1):
        if np.isfinite(v[i]) and v[i]>=thr: nxt=i
        out[i]=nxt
    return out
def events(sig,thb,line,r):
    n=len(sig); on=sig>=thb
    if r>1: on=on&np.r_[False,on[:-1]]
    lastb=np.maximum.accumulate(np.where(sig<line,np.arange(n),0))
    return np.flatnonzero(on),lastb
def machine(oi,lastb,sig,reb,nc,W,cens,mn):
    out=[]; pos=0; last=-10**6; n=len(sig)
    rp=np.flatnonzero(sig<reb)
    while True:
        p=np.searchsorted(oi,pos,'left')
        if p>=len(oi): break
        i=int(oi[p]); j=int(nc[i])
        if j<=i+W and j<n and (mn[j]+1-last)>=cens:
            out.append((mn[j]+1,mn[lastb[i]])); last=mn[j]+1
            q=np.searchsorted(rp,j+1,'left')
        else:
            q=np.searchsorted(rp,i+1,'left')
        if q>=len(rp): break
        pos=int(rp[q])+1
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
COMBOS=[('initial claims',),('continued weeks claimed',),
        ('initial claims','continued weeks claimed'),
        ('initial claims','continued weeks claimed','weeks compensated','first payments')]
for tag,T,up in [('PEAKS',PK,True),('TROUGHS',TR,False)]:
    TT=np.array([pd.Timestamp(k+'-01').year*12+pd.Timestamp(k+'-01').month for k in T])
    best={}
    for chs in COMBOS:
        P=panel(chs); mn=np.array([t.year*12+t.month for t in P.index],dtype=np.int64)
        for sm in (1,2,3,4):
            for k in (1,3,6):
                di=DI(P,sm,k); s=np.where(np.isfinite(di),di if up else -di,-1e9)
                for Lg,gap in [(24,20.),(24,25.),(36,20.),(36,25.),(36,30.),(48,25.)]:
                    lv=LEV(P,sm,Lg,gap)
                    NC={c:nextge(lv,c) for c in (30.,40.,50.,60.,70.,80.)}
                    for thb in (55.,60.,65.,70.,75.):
                        TH=thb if up else -thb
                        for line in (45.,50.,55.,60.):
                            if line>thb: continue
                            LN=line if up else -line
                            for r in (1,2):
                                oi,lastb=events(s,TH,LN,r)
                                if len(oi)==0: continue
                                for reb in (35.,40.,45.,50.):
                                    if reb>=thb: continue
                                    RB=reb if up else -reb
                                    for conf in (30.,40.,50.,60.,70.,80.):
                                        for W in (3,6,9,12,18,24):
                                            for cens in (15,24,36):
                                                h,o=score(machine(oi,lastb,s,RB,NC[conf],W,cens,mn),TT)
                                                key=(len(h),o)
                                                if key not in best:
                                                    best[key]=(chs,sm,k,Lg,gap,thb,line,r,reb,conf,W,cens,tuple(sorted(T[i] for i in h)))
    print(f'=== {tag}')
    for key in sorted(best,key=lambda x:(-x[0],x[1]))[:12]:
        chs,sm,k,Lg,gap,thb,line,r,reb,conf,W,cens,h=best[key]
        print(f'  {key[0]}/9 other {key[1]:2d}  chs={"+".join(c[:4] for c in chs)} sm={sm} k={k} '
              f'L={Lg} gap={gap} thb={thb} line={line} r={r} reb={reb} conf={conf} W={W} cens={cens}')
        print(f'        {list(h)}')
