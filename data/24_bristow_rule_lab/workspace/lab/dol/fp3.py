import pandas as pd, numpy as np, warnings, itertools; warnings.filterwarnings('ignore')
PAN=pd.read_csv('/home/claude/lab/dol/US_state_monthly_4ch_sa.csv',index_col=0,parse_dates=True)
CHS=['initial claims','continued weeks claimed','weeks compensated','first payments']
SUB={ch:PAN[[c for c in PAN.columns if c.endswith('| '+ch)]] for ch in CHS}
PK=['1973-11','1980-01','1981-07','1990-07','2001-03','2007-12','2020-02','2023-06','2024-03']
PKT=np.array([pd.Timestamp(k+'-01').year*12+pd.Timestamp(k+'-01').month for k in PK])
S0=pd.Timestamp('1973-01-01').year*12+1
def runlen(bl):
    out=np.zeros(len(bl),dtype=np.int32); c=0
    for i in range(len(bl)):
        c=c+1 if bl[i] else 0
        out[i]=c
    return out
def breadth(chs,sm,L,gap,mode,sw=60):
    P=pd.concat([SUB[c] for c in chs],axis=1)
    K=P.rolling(sm).mean()*100.0
    S=K-K.rolling(L,min_periods=L//2).min()
    D=(S>=gap) if mode=='fixed' else (S>=gap*K.diff().rolling(sw,min_periods=sw//2).std())
    return ((D&S.notna()).sum(axis=1)/S.notna().sum(axis=1)*100.0).dropna()
def machine(on_idx,rearm_pts,lastbelow,mn):
    out=[]; pos=0
    while True:
        p=np.searchsorted(on_idx,pos,'left')
        if p>=len(on_idx): break
        i=int(on_idx[p]); out.append((mn[i]+1,mn[lastbelow[i]]))
        q=np.searchsorted(rearm_pts,i+1,'left')
        if q>=len(rearm_pts): break
        pos=int(rearm_pts[q])+1
        if len(out)>80: break
    return out
def score(pairs):
    hits=set(); other=0
    for pub,dt in pairs:
        if pub<S0: continue
        k=int(np.argmin(np.abs(PKT-dt)))
        if abs(pub-PKT[k])<=2 and abs(dt-PKT[k])<=2 and k not in hits: hits.add(k)
        else: other+=1
    return hits,other
COMBOS=[('initial claims',),('continued weeks claimed',),
        ('initial claims','continued weeks claimed'),
        ('initial claims','continued weeks claimed','weeks compensated','first payments')]
LINES=[35.,45.,55.,65.]; REBS=[10.,20.,30.]; MPS=(1,2,3)
best={}
def keep(nh,no,par,hits):
    k=(nh,no)
    if k not in best: best[k]=(par,tuple(sorted(PK[i] for i in hits)))
for chs in COMBOS:
  for mode,gaps in [('fixed',[10.,15.,20.,25.,30.]),('z',[1.0,1.5,2.0,2.5,3.0])]:
    for sm in (1,2,3):
      for L in (18,24,36,48):
        for gap in gaps:
          Bd=breadth(chs,sm,L,gap,mode); b=Bd.values
          mn=np.array([t.year*12+t.month for t in Bd.index]); n=len(b)
          lb=pd.Series(b,index=Bd.index).rolling(24,min_periods=12).min().values
          LB={ln:np.maximum.accumulate(np.where(b<ln,np.arange(n),0)) for ln in LINES}
          for firemode in ('level','rise'):
            trig=b if firemode=='level' else b-lb
            ok=np.isfinite(trig); tg=np.where(ok,trig,-1e9)
            REB={reb:{mp:np.flatnonzero(runlen((tg<reb)&ok)>=mp) for mp in MPS} for reb in REBS}
            ths=[40.,50.,60.,70.,80.] if firemode=='level' else [15.,25.,35.,45.,55.]
            for thb in ths:
              on1=tg>=thb
              for r in (1,2):
                on=on1 if r==1 else (on1 & np.r_[False,on1[:-1]])
                oi=np.flatnonzero(on)
                if len(oi)==0: continue
                for ln in LINES:
                  if firemode=='level' and ln>thb: continue
                  for reb in REBS:
                    if reb>=thb: continue
                    for mp in MPS:
                      h,o=score(machine(oi,REB[reb][mp],LB[ln],mn))
                      keep(len(h),o,(chs,mode,gap,sm,L,firemode,thb,ln,reb,r,mp),h)
print('PEAKS  (hits, other)')
for k in sorted(best,key=lambda x:(-x[0],x[1]))[:18]:
    par,h=best[k]
    print(f'  {k[0]}/9  other {k[1]:2d}   {par}')
    print(f'        {list(h)}')
