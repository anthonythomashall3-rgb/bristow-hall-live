"""Choose the two real-time detectors on the four-channel monthly state panel."""
import pandas as pd, numpy as np, itertools, sys, warnings; warnings.filterwarnings('ignore')
PAN=pd.read_csv('/home/claude/lab/dol/US_state_monthly_4ch_sa.csv',index_col=0,parse_dates=True)
NAT=pd.read_csv('/home/claude/lab/dol/US_nat_monthly_4ch_sa.csv',index_col=0,parse_dates=True)
CHS=['initial claims','continued weeks claimed','weeks compensated','first payments']
START=pd.Timestamp('1973-01-01')
def mo(t): return pd.Timestamp(t.year,t.month,1)
def md(x,y): return (x.year-y.year)*12+(x.month-y.month)
PK={'1973-11':1,'1980-01':1,'1981-07':1,'1990-07':1,'2001-03':1,'2007-12':1,'2020-02':1,
    '2023-06':1,'2024-03':1}
TR={'1975-03':1,'1980-07':1,'1982-11':1,'1991-03':1,'2001-11':1,'2009-06':1,'2020-04':1,
    '2024-08':1,'2026-05':1}
SUB={}
for ch in CHS: SUB[ch]=PAN[[c for c in PAN.columns if c.endswith('| '+ch)]]
def sub(chs): return pd.concat([SUB[c] for c in chs],axis=1)
_bc={}
def breadth(chs,sm,L,gap):
    k=(chs,sm,L,gap)
    if k not in _bc:
        P=sub(list(chs)); K=P.rolling(sm).mean()*100.0
        S=K-K.rolling(L,min_periods=L//2).min()
        _bc[k]=((S>=gap).sum(axis=1)/S.notna().sum(axis=1)*100.0).dropna()
    return _bc[k]
def peaks(Bd,thb,reb,r,mp,line):
    b=Bd.values; idx=Bd.index; out=[]; state='armed'; off=0
    for i in range(r,len(b)):
        if state=='called':
            off = off+1 if b[i]<reb else 0
            if off>=mp: state='armed'; off=0
            continue
        if bool(np.all(b[i-r+1:i+1]>=thb)):
            j=i
            while j>0 and b[j]>=line: j-=1
            out.append((idx[i]+pd.DateOffset(months=1),mo(idx[j]))); state='called'; off=0
    return out
_ng={}
def natgap(ch,sm,L):
    k=(ch,sm,L)
    if k not in _ng:
        N=(np.log(NAT[ch])*100.0).rolling(sm).mean()
        G=N-N.rolling(L,min_periods=L//2).min()
        _ng[k]=pd.concat([N.rename('n'),G.rename('g')],axis=1).dropna()
    return _ng[k]
def troughs(ch,sm,L,run,drop,arm,rearm,mp):
    df=natgap(ch,sm,L); n=df['n'].values; g=df['g'].values; idx=df.index
    out=[]; state='quiet'; off=0; nmax=-1e9; nmax_i=0; fall=0; prev=n[0]
    for i in range(1,len(n)):
        if n[i]>nmax: nmax=n[i]; nmax_i=i; fall=0
        elif n[i]<prev: fall+=1
        else: fall=0
        prev=n[i]
        if state=='called':
            off = off+1 if g[i]<rearm else 0
            if off>=mp: state='quiet'; off=0
            continue
        if state=='quiet':
            if g[i]>=arm: state='armed'; nmax=n[i]; nmax_i=i; fall=0
            continue
        if fall>=run and (nmax-n[i])>=drop and g[nmax_i]>=arm:
            out.append((idx[i]+pd.DateOffset(months=1),mo(idx[nmax_i]))); state='called'; off=0
    return out
def score(calls,T):
    hits={}; other=0
    for pub,dt in sorted(calls):
        if pub<START: continue
        near=min(T,key=lambda k: abs(md(dt,pd.Timestamp(k+'-01'))))
        lag=md(mo(pub),pd.Timestamp(near+'-01')); err=md(dt,pd.Timestamp(near+'-01'))
        if abs(lag)<=2 and abs(err)<=2 and near not in hits: hits[near]=(lag,err)
        else: other+=1
    return hits,other
def show(res,label,n=10):
    res.sort(reverse=True); print(label); seen=set()
    for row in res:
        key=(row[0],row[1])
        if key in seen: continue
        seen.add(key); print('  ',row[2]); print('     ',row[0],'hits, other',-row[1],list(row[3]))
        if len(seen)>=n: break
COMBOS=[('initial claims',),('continued weeks claimed',),('weeks compensated',),('first payments',),
        ('initial claims','continued weeks claimed'),
        ('initial claims','continued weeks claimed','weeks compensated','first payments'),
        ('continued weeks claimed','weeks compensated'),
        ('initial claims','first payments')]
if sys.argv[1]=='peak':
    res=[]
    for chs in COMBOS:
        for sm in [1,2,3]:
            for L in [18,24,30,36,48]:
                for gap in [10.,15.,20.,25.,30.,40.]:
                    Bd=breadth(chs,sm,L,gap)
                    for thb in [40.,45.,50.,55.,60.,65.,70.,75.,80.]:
                        for line in [t for t in [30.,35.,40.,45.,50.,55.,60.,65.,70.] if t<=thb]:
                            for reb in [10.,15.,20.,25.,30.,35.,40.]:
                                if reb>=thb: continue
                                for r in [1,2]:
                                    for mp in [1,2,3,4]:
                                        h,o=score(peaks(Bd,thb,reb,r,mp,line),PK)
                                        res.append((len(h),-o,f'chs={"+".join(c[:4] for c in chs)} sm={sm} L={L} gap={gap} thb={thb} reb={reb} r={r} mp={mp} line={line}',tuple(sorted(h))))
        _bc.clear()
    show(res,'PEAKS')
else:
    res=[]
    for ch in CHS:
        for sm in [1,2,3]:
            for L in [12,18,24,30,36]:
                for run in [1,2,3]:
                    for drop in [1.,2.,3.,5.,8.]:
                        for arm in [10.,15.,20.,25.,30.,40.,50.]:
                            for rearm in [5.,10.,15.,20.,25.]:
                                if rearm>=arm: continue
                                for mp in [1,2,3]:
                                    h,o=score(troughs(ch,sm,L,run,drop,arm,rearm,mp),TR)
                                    res.append((len(h),-o,f'ch={ch} sm={sm} L={L} run={run} drop={drop} arm={arm} rearm={rearm} mp={mp}',tuple(sorted(h))))
    show(res,'TROUGHS')
