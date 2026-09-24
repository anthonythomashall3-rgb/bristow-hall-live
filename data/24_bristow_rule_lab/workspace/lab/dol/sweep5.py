"""Scale-free variants of the breadth object and of the peak clause.

Two things in the first breadth object are calibrated to nothing: a jurisdiction counts as
deteriorating when it stands a FIXED twenty-five log points above its own trailing
minimum, and the peak fires when breadth crosses a FIXED share.  Both are replaced here by
scale-free forms and the choice is made on the record.

  gapmode 'fixed'  a jurisdiction is deteriorating when its gap exceeds `gap` log points
  gapmode 'z'      ... when its gap exceeds `gap` times its own trailing standard deviation
  firemode 'level' the peak fires when breadth reaches `thb`
  firemode 'rise'  ... when breadth stands `thb` points above its own trailing two-year low
"""
import pandas as pd, numpy as np, sys, warnings; warnings.filterwarnings('ignore')
PAN=pd.read_csv('/home/claude/lab/dol/US_state_monthly_4ch_sa.csv',index_col=0,parse_dates=True)
CHS=['initial claims','continued weeks claimed','weeks compensated','first payments']
SUB={ch:PAN[[c for c in PAN.columns if c.endswith('| '+ch)]] for ch in CHS}
START=pd.Timestamp('1973-01-01')
def mo(t): return pd.Timestamp(t.year,t.month,1)
def md(x,y): return (x.year-y.year)*12+(x.month-y.month)
PK=['1973-11','1980-01','1981-07','1990-07','2001-03','2007-12','2020-02','2023-06','2024-03']
_bc={}
def breadth(chs,sm,L,gap,mode,sw=60):
    k=(chs,sm,L,gap,mode,sw)
    if k in _bc: return _bc[k]
    P=pd.concat([SUB[c] for c in chs],axis=1)
    K=P.rolling(sm).mean()*100.0
    S=K-K.rolling(L,min_periods=L//2).min()
    if mode=='fixed': D=(S>=gap)
    else:
        sd=K.diff().rolling(sw,min_periods=sw//2).std()
        D=(S>=gap*sd)
    _bc[k]=((D&S.notna()).sum(axis=1)/S.notna().sum(axis=1)*100.0).dropna()
    return _bc[k]
def peaks(Bd,thb,reb,r,mp,line,firemode,lb=24):
    b=Bd.values; idx=Bd.index
    if firemode=='rise':
        base=Bd.rolling(lb,min_periods=lb//2).min().values
        trig=b-base; ln=line
    else:
        trig=b; ln=line
    out=[]; state='armed'; off=0
    for i in range(r,len(b)):
        if not np.isfinite(trig[i]): continue
        if state=='called':
            off = off+1 if trig[i]<reb else 0
            if off>=mp: state='armed'; off=0
            continue
        if bool(np.all(trig[i-r+1:i+1]>=thb)):
            j=i
            while j>0 and b[j]>=ln: j-=1
            out.append((idx[i]+pd.DateOffset(months=1),mo(idx[j]))); state='called'; off=0
    return out
def score(calls,T=PK):
    hits={}; other=0
    for pub,dt in sorted(calls):
        if pub<START: continue
        near=min(T,key=lambda k: abs(md(dt,pd.Timestamp(k+'-01'))))
        lag=md(mo(pub),pd.Timestamp(near+'-01')); err=md(dt,pd.Timestamp(near+'-01'))
        if abs(lag)<=2 and abs(err)<=2 and near not in hits: hits[near]=(lag,err)
        else: other+=1
    return hits,other
COMBOS=[('initial claims',),('continued weeks claimed',),
        ('initial claims','continued weeks claimed'),
        ('initial claims','continued weeks claimed','weeks compensated','first payments')]
res=[]
for chs in COMBOS:
    for mode,gaps in [('fixed',[10.,15.,20.,25.,30.]),('z',[1.0,1.5,2.0,2.5,3.0,4.0])]:
        for sm in [1,2,3]:
            for L in [18,24,36]:
                for gap in gaps:
                    Bd=breadth(chs,sm,L,gap,mode)
                    for firemode in ['level','rise']:
                        ths=[40.,45.,50.,55.,60.,65.,70.,75.] if firemode=='level' else [20.,25.,30.,35.,40.,45.,50.,55.]
                        for thb in ths:
                            for line in [30.,35.,40.,45.,50.,55.,60.,65.]:
                                if firemode=='level' and line>thb: continue
                                for reb in [5.,10.,15.,20.,25.,30.,35.]:
                                    if reb>=thb: continue
                                    for r in [1,2]:
                                        for mp in [1,2,3]:
                                            h,o=score(peaks(Bd,thb,reb,r,mp,line,firemode))
                                            res.append((len(h),-o,f'chs={"+".join(c[:4] for c in chs)} {mode} gap={gap} sm={sm} L={L} {firemode} thb={thb} line={line} reb={reb} r={r} mp={mp}',tuple(sorted(h))))
        _bc.clear()
res.sort(reverse=True); seen=set()
print('PEAKS, scale-free variants')
for row in res:
    key=(row[0],row[1])
    if key in seen: continue
    seen.add(key); print('  ',row[2]); print('     ',row[0],'hits, other',-row[1],list(row[3]))
    if len(seen)>=14: break
