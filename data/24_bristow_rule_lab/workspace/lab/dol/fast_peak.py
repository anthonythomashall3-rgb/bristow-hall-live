"""Choose the peak detector on the four-channel monthly state panel.

The machine is the same three-state one - armed, called, back to armed only after the
signal has stood below a low line for `mp` months - but written so that it steps from
crossing to crossing rather than month by month, which is what makes the search over the
whole grid affordable.
"""
import pandas as pd, numpy as np, itertools, sys, warnings; warnings.filterwarnings('ignore')
PAN=pd.read_csv('/home/claude/lab/dol/US_state_monthly_4ch_sa.csv',index_col=0,parse_dates=True)
CHS=['initial claims','continued weeks claimed','weeks compensated','first payments']
SUB={ch:PAN[[c for c in PAN.columns if c.endswith('| '+ch)]] for ch in CHS}
START=pd.Timestamp('1973-01-01')
PK=['1973-11','1980-01','1981-07','1990-07','2001-03','2007-12','2020-02','2023-06','2024-03']
PKT=np.array([ (pd.Timestamp(k+'-01').year)*12+pd.Timestamp(k+'-01').month for k in PK])
def mnum(idx): return np.array([t.year*12+t.month for t in idx])
def breadth(chs,sm,L,gap,mode,sw=60):
    P=pd.concat([SUB[c] for c in chs],axis=1)
    K=P.rolling(sm).mean()*100.0
    S=K-K.rolling(L,min_periods=L//2).min()
    if mode=='fixed': D=(S>=gap)
    else: D=(S>=gap*K.diff().rolling(sw,min_periods=sw//2).std())
    return ((D&S.notna()).sum(axis=1)/S.notna().sum(axis=1)*100.0).dropna()
def run_machine(b,on_idx,below_run,mp,lastbelow):
    """on_idx: sorted indices where the fire condition holds.  Returns list of (i, j)."""
    out=[]; k=0; n=len(b); pos=0
    rearm_pts=np.flatnonzero(below_run>=mp)
    while True:
        p=np.searchsorted(on_idx,pos,side='left')
        if p>=len(on_idx): break
        i=on_idx[p]; out.append((i,lastbelow[i]))
        q=np.searchsorted(rearm_pts,i+1,side='left')
        if q>=len(rearm_pts): break
        pos=rearm_pts[q]+1
        if len(out)>60: break
    return out
def score(pairs,mn):
    hits={}; other=0
    for i,j in pairs:
        pub=mn[i]+1; dt=mn[j] if j>=0 else mn[i]
        if pub<START.year*12+START.month: continue
        k=int(np.argmin(np.abs(PKT-dt))); lag=pub-PKT[k]; err=dt-PKT[k]
        if abs(lag)<=2 and abs(err)<=2 and k not in hits: hits[k]=(lag,err)
        else: other+=1
    return hits,other
COMBOS=[('initial claims',),('continued weeks claimed',),('weeks compensated',),('first payments',),
        ('initial claims','continued weeks claimed'),
        ('initial claims','first payments'),
        ('continued weeks claimed','weeks compensated'),
        ('initial claims','continued weeks claimed','weeks compensated','first payments')]
res=[]
for chs in COMBOS:
    for mode,gaps in [('fixed',[10.,15.,20.,25.,30.,40.]),('z',[1.0,1.5,2.0,2.5,3.0,4.0])]:
        for sm in [1,2,3]:
            for L in [18,24,30,36,48]:
                for gap in gaps:
                    Bd=breadth(chs,sm,L,gap,mode); b=Bd.values; mn=mnum(Bd.index); n=len(b)
                    lb24=pd.Series(b,index=Bd.index).rolling(24,min_periods=12).min().values
                    for firemode in ['level','rise']:
                        trig = b if firemode=='level' else b-lb24
                        ok=np.isfinite(trig)
                        ths=[40.,45.,50.,55.,60.,65.,70.,75.,80.] if firemode=='level' else [15.,20.,25.,30.,35.,40.,45.,50.,55.]
                        for line in [30.,35.,40.,45.,50.,55.,60.,65.,70.]:
                            lastbelow=np.empty(n,dtype=int); last=-1
                            for i in range(n):
                                if b[i]<line: last=i
                                lastbelow[i]=last
                            for thb in ths:
                                if firemode=='level' and line>thb: continue
                                on1=(trig>=thb)&ok
                                for r in [1,2]:
                                    on = on1 if r==1 else (on1 & np.r_[False,on1[:-1]])
                                    on_idx=np.flatnonzero(on)
                                    if len(on_idx)==0: continue
                                    for reb in [5.,10.,15.,20.,25.,30.,35.,40.]:
                                        if reb>=thb: continue
                                        bel=(trig<reb)&ok
                                        run=np.zeros(n,dtype=int); c=0
                                        for i in range(n):
                                            c = c+1 if bel[i] else 0
                                            run[i]=c
                                        for mp in [1,2,3,4]:
                                            h,o=score(run_machine(b,on_idx,run,mp,lastbelow),mn)
                                            res.append((len(h),-o,f'chs={"+".join(c[:4] for c in chs)} {mode} gap={gap} sm={sm} L={L} {firemode} thb={thb} line={line} reb={reb} r={r} mp={mp}',tuple(sorted(PK[k] for k in h))))
res.sort(reverse=True); seen=set()
print('PEAKS, four channels, fixed and noise-scaled breadth, level and rise clauses')
for row in res:
    key=(row[0],row[1])
    if key in seen: continue
    seen.add(key); print('  ',row[2]); print('     ',row[0],'hits, other',-row[1],list(row[3]))
    if len(seen)>=16: break
