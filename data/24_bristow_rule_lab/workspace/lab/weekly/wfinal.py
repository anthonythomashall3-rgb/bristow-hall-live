"""The weekly detectors on the pooled-warm-up seasonal adjustment.
Targets are the NBER's turning points plus the episode Paper 1 dates."""
import pandas as pd, numpy as np, itertools, warnings; warnings.filterwarnings('ignore')
SA=pd.read_csv('/home/claude/lab/dol/US_state_claims_both_sa.csv',index_col=0,parse_dates=True)
NC=pd.read_csv('/home/claude/lab/weekly/US_nat_claims_pooled.csv',index_col=0,parse_dates=True)
PK={'1990-07':'NBER','2001-03':'NBER','2007-12':'NBER','2020-02':'NBER','2023-06':'Paper 1'}
TR={'1991-03':'NBER','2001-11':'NBER','2009-06':'NBER','2020-04':'NBER'}
def mo(t): return pd.Timestamp(t.year,t.month,1)
def md(x,y): return (x.year-y.year)*12+(x.month-y.month)
_B={}
def breadth(sm,L,gap):
    if (sm,L) not in _B:
        K=SA.rolling(sm).mean()*100.0
        _B[(sm,L)]=K-K.rolling(L,min_periods=L//2).min()
    S=_B[(sm,L)]
    return ((S>=gap).sum(axis=1)/S.notna().sum(axis=1)*100.0).dropna()
_N={}
def natgap(sm,L):
    if (sm,L) not in _N:
        N=(np.log(NC['initial claims'])*100.0).rolling(sm).mean()
        _N[(sm,L)]=pd.concat([N.rename('n'),(N-N.rolling(L,min_periods=L//2).min()).rename('g')],axis=1).dropna()
    return _N[(sm,L)]
def peak_calls(B,thb,rearm_b,r,mp,line=50.,pub=7,G=None,nth=0.0):
    b=B.values; idx=B.index; out=[]; state='armed'; off=0
    gg=(G.reindex(idx).ffill().values if G is not None else np.zeros(len(b)))
    for i in range(r,len(b)):
        on=bool(np.all(b[i-r+1:i+1]>=thb)) and gg[i]>=nth
        if state=='called':
            off = off+1 if b[i]<rearm_b else 0
            if off>=mp: state='armed'; off=0
            continue
        if on:
            j=i
            while j>0 and b[j]>=line: j-=1
            k=min(j+1,len(b)-1)
            out.append((idx[i]+pd.Timedelta(days=pub),mo(idx[k]))); state='called'; off=0
    return out
def trough_calls(D,run,drop,arm,rearm,mp,pub=7):
    n=D['n'].values; g=D['g'].values; idx=D.index
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
            d=idx[nmax_i]
            out.append((idx[i]+pd.Timedelta(days=pub),mo(d))); state='called'; off=0
    return out
def sc(calls,T,cut='1988-01'):
    got={}; fa=[]
    for pub,dt in calls:
        if pub<pd.Timestamp(cut): continue
        b=None
        for k in T:
            if k in got: continue
            lag=md(mo(pub),pd.Timestamp(k+'-01')); err=md(dt,pd.Timestamp(k+'-01'))
            if abs(lag)<=2 and abs(err)<=2 and (b is None or abs(lag)+abs(err)<b[3]):
                b=(k,lag,err,abs(lag)+abs(err))
        if b: got[b[0]]=(b[1],b[2])
        else: fa.append((pub,dt))
    return got,fa
bp=None
for sm,L,gap,thb,reb,r,mp,nth in itertools.product((13,26),(78,104,156),(15.,20.,25.,30.),
                                               (40.,45.,50.,55.,60.,65.,70.),(20.,25.,30.,35.,40.),(2,4,8),(26,52,78,104),
                                               (0.,)):
    G=natgap(13,52)['g']
    g,fa=sc(peak_calls(breadth(sm,L,gap),thb,reb,r,mp,G=G,nth=nth),PK)
    key=(len(g),-len(fa))
    if bp is None or key>bp[0]: bp=(key,(sm,L,gap,thb,reb,r,mp,nth),dict(g),fa)
print('PEAK  ',bp[0],'(sm,L,gap,thb,rearm,r,mp,nth)=',bp[1]); print('   hits',bp[2])
print('   other',[(a.strftime('%Y-%m'),b.strftime('%Y-%m')) for a,b in bp[3]])
bt=None
for sm,L,run,drop,arm,rearm,mp in itertools.product((4,8,13),(52,78,104),(4,6,8),(5.,10.),
                                                    (30.,40.,50.),(10.,15.,20.),(13,26,52)):
    g,fa=sc(trough_calls(natgap(sm,L),run,drop,arm,rearm,mp),TR)
    key=(len(g),-len(fa))
    if bt is None or key>bt[0]: bt=(key,(sm,L,run,drop,arm,rearm,mp),dict(g),fa)
print('TROUGH',bt[0],'(sm,L,run,drop,arm,rearm,mp)=',bt[1]); print('   hits',bt[2])
print('   other',[(a.strftime('%Y-%m'),b.strftime('%Y-%m')) for a,b in bt[3]])
