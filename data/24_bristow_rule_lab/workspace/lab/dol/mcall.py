"""The caller on the monthly state panel, 1971 on: eight US recessions plus the episode
Paper 1 says was missed."""
import pandas as pd, numpy as np, itertools, warnings; warnings.filterwarnings('ignore')
SA=pd.read_csv('/home/claude/lab/dol/US_state_claims_monthly_sa_rt.csv',index_col=0,parse_dates=True)
NC=pd.read_csv('/home/claude/lab/dol/US_nat_claims_monthly_rt.csv',index_col=0,parse_dates=True)
# the monthly panel is the only source before the weekly file begins in 1986, so the
# monthly detectors are tuned and scored on the episodes only it reaches
PK={'1973-11':'NBER','1980-01':'NBER','1981-07':'NBER'}
TR={'1975-03':'NBER','1980-07':'NBER','1982-11':'NBER'}
def md(x,y): return (x.year-y.year)*12+(x.month-y.month)
def breadth(sm,L,gap):
    K=SA.rolling(sm).mean()*100.0
    S=K-K.rolling(L,min_periods=L//2).min()
    return ((S>=gap).sum(axis=1)/S.notna().sum(axis=1)*100.0).dropna()
def natgap(sm,L=12):
    N=(np.log(NC['initial claims'])*100.0).rolling(sm).mean()
    return pd.concat([N.rename('n'),(N-N.rolling(L,min_periods=L//2).min()).rename('g')],axis=1).dropna()
def peak_calls(B,thb,r,mp,line=50.,pub=1):
    b=B.values; idx=B.index; out=[]; armed=True; off=0
    for i in range(r,len(b)):
        on=bool(np.all(b[i-r+1:i+1]>=thb))
        if not armed:
            off = off+1 if not on else 0
            if off>=mp: armed=True
            continue
        if on:
            j=i
            while j>0 and b[j]>=line: j-=1
            k=min(j+1,len(b)-1)
            out.append((idx[i]+pd.DateOffset(months=pub),idx[k])); armed=False; off=0
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
for sm,L,gap,thb,r,mp in itertools.product((1,3,6),(12,18,24,36),(5.,10.,15.,20.,25.,30.),(30.,40.,50.,60.,70.),(1,2,3),(6,12,18,24)):
    B=breadth(sm,L,gap); g,fa=sc(peak_calls(B,thb,r,mp),PK)
    key=(len(g),-len(fa))
    if bp is None or key>bp[0]: bp=(key,sm,L,gap,thb,r,mp,len(fa),dict(g),fa)
print('PEAK  ',bp[0],'sm',bp[1],'L',bp[2],'gap',bp[3],'thb',bp[4],'r',bp[5],'mp',bp[6])
print('   hits',bp[8]); print('   false',[(a.strftime("%Y-%m"),b.strftime("%Y-%m")) for a,b in bp[9]])
bt=None
for sm,run,drop,arm,rearm,mp in itertools.product((1,2,3),(1,2,3,4),(1.,3.,5.,10.),(10.,20.,30.,40.,50.),(2.,5.,10.,15.),(3,6,12,18)):
    D=natgap(sm); g,fa=sc(trough_calls(D,run,drop,arm,rearm,mp),TR)
    key=(len(g),-len(fa))
    if bt is None or key>bt[0]: bt=(key,sm,run,drop,arm,rearm,mp,len(fa),dict(g),fa)
print('TROUGH',bt[0],'sm',bt[1],'run',bt[2],'drop',bt[3],'arm',bt[4],'rearm',bt[5],'mp',bt[6])
print('   hits',bt[8]); print('   false',[(a.strftime("%Y-%m"),b.strftime("%Y-%m")) for a,b in bt[9]])
