"""Monthly detectors, 1971 on, with the baseline length swept.

A twelve-month trailing minimum sits inside the elevated period during a double dip, so
the 1981-82 gap never looks large.  The baseline length is therefore a parameter, not a
constant: the same problem the memo records for the rolling window at the trough.
Both detectors use the three-state machine - quiet, armed, called - so neither can fire
twice on the same episode.
"""
import pandas as pd, numpy as np, itertools, warnings; warnings.filterwarnings('ignore')
SA=pd.read_csv('/home/claude/lab/dol/US_state_claims_monthly_sa_rt.csv',index_col=0,parse_dates=True)
NC=pd.read_csv('/home/claude/lab/dol/US_nat_claims_monthly_rt.csv',index_col=0,parse_dates=True)
PK={'1973-11':'NBER','1980-01':'NBER','1981-07':'NBER'}
TR={'1975-03':'NBER','1980-07':'NBER','1982-11':'NBER'}
def md(x,y): return (x.year-y.year)*12+(x.month-y.month)
_BC={}
def breadth(sm,L,gap):
    k=(sm,L,gap)
    if k in _BC: return _BC[k]
    ks=(sm,L)
    if ks not in _BC:
        K=SA.rolling(sm).mean()*100.0
        _BC[ks]=K-K.rolling(L,min_periods=L//2).min()
    S=_BC[ks]
    _BC[k]=((S>=gap).sum(axis=1)/S.notna().sum(axis=1)*100.0).dropna()
    return _BC[k]
_NG={}
def natgap(sm,L):
    if (sm,L) not in _NG:
        N=(np.log(NC['initial claims'])*100.0).rolling(sm).mean()
        _NG[(sm,L)]=pd.concat([N.rename('n'),(N-N.rolling(L,min_periods=L//2).min()).rename('g')],axis=1).dropna()
    return _NG[(sm,L)]
def peak_calls(B,thb,rearm_b,r,mp,line=50.,pub=1):
    b=B.values; idx=B.index; out=[]; state='armed'; off=0
    for i in range(r,len(b)):
        on=bool(np.all(b[i-r+1:i+1]>=thb))
        if state=='called':
            off = off+1 if b[i]<rearm_b else 0
            if off>=mp: state='armed'; off=0
            continue
        if on:
            j=i
            while j>0 and b[j]>=line: j-=1
            k=min(j+1,len(b)-1)
            out.append((idx[i]+pd.DateOffset(months=pub),idx[k])); state='called'; off=0
    return out
def trough_calls(D,run,drop,arm,rearm,mp,pub=1):
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
            out.append((idx[i]+pd.DateOffset(months=pub),idx[nmax_i])); state='called'; off=0
    return out
def sc(calls,T,cut='1973-01',end='1986-02'):
    got={}; fa=[]
    for pub,dt in calls:
        if pub<pd.Timestamp(cut) or pub>pd.Timestamp(end): continue
        b=None
        for k in T:
            if k in got: continue
            lag=md(pub,pd.Timestamp(k+'-01')); err=md(dt,pd.Timestamp(k+'-01'))
            if abs(lag)<=2 and abs(err)<=2 and (b is None or abs(lag)+abs(err)<b[3]):
                b=(k,lag,err,abs(lag)+abs(err))
        if b: got[b[0]]=(b[1],b[2])
        else: fa.append((pub,dt))
    return got,fa
bp=None
for sm,L,gap,thb,reb,r,mp in itertools.product((1,2,3),(12,18,24,36,48),(5.,10.,15.,20.,25.,30.,40.),
                                               (40.,50.,55.,60.,65.,70.,75.,80.),(15.,20.,25.,30.,35.,40.,45.),(1,2),(1,2,3,4,6)):
    g,fa=sc(peak_calls(breadth(sm,L,gap),thb,reb,r,mp),PK)
    key=(len(g),-len(fa))
    if bp is None or key>bp[0]: bp=(key,(sm,L,gap,thb,reb,r,mp),dict(g),fa)
print('PEAK  ',bp[0],'(sm,L,gap,thb,rearm,r,mp)=',bp[1]); print('   hits',bp[2])
print('   false',[(a.strftime('%Y-%m'),b.strftime('%Y-%m')) for a,b in bp[3]])
bt=None
for sm,L,run,drop,arm,rearm,mp in itertools.product((1,2,3),(12,18,24,36,48),(1,2,3),
                                                    (1.,3.,5.,10.),(20.,30.,40.,50.,60.),
                                                    (5.,10.,15.,20.),(3,6,12)):
    g,fa=sc(trough_calls(natgap(sm,L),run,drop,arm,rearm,mp),TR)
    key=(len(g),-len(fa))
    if bt is None or key>bt[0]: bt=(key,(sm,L,run,drop,arm,rearm,mp),dict(g),fa)
print('TROUGH',bt[0],'(sm,L,run,drop,arm,rearm,mp)=',bt[1]); print('   hits',bt[2])
print('   false',[(a.strftime('%Y-%m'),b.strftime('%Y-%m')) for a,b in bt[3]])
