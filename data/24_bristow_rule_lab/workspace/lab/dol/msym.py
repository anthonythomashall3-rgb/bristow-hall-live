"""Monthly caller, 1971 on: breadth arms, national claims dates both ends.
Independent detectors; the peak is dated by the low-band clause on claims."""
import sys; sys.path.insert(0,'/home/claude')
import bristow_rule_v3 as B
import pandas as pd, numpy as np, itertools, warnings; warnings.filterwarnings('ignore')
SA=pd.read_csv('/home/claude/lab/dol/US_state_claims_monthly_sa_rt.csv',index_col=0,parse_dates=True)
NC=pd.read_csv('/home/claude/lab/dol/US_nat_claims_monthly_rt.csv',index_col=0,parse_dates=True)
PK={'1973-11':'NBER','1980-01':'NBER','1981-07':'NBER','1990-07':'NBER','2001-03':'NBER',
    '2007-12':'NBER','2020-02':'NBER','2023-06':'Paper 1'}
TR={'1975-03':'NBER','1980-07':'NBER','1982-11':'NBER','1991-03':'NBER','2001-11':'NBER',
    '2009-06':'NBER','2020-04':'NBER'}
def md(x,y): return (x.year-y.year)*12+(x.month-y.month)
_B={}
def breadth(sm,L,gap):
    if (sm,L) not in _B:
        K=SA.rolling(sm).mean()*100.0
        _B[(sm,L)]=K-K.rolling(L,min_periods=L//2).min()
    S=_B[(sm,L)]
    return ((S>=gap).sum(axis=1)/S.notna().sum(axis=1)*100.0).dropna()
def act(sm): return (-np.log(NC['initial claims'])*100.0).rolling(sm).mean().dropna()
def peak_calls(A,Bd,thb,reb,r,mp,W,band,pub=1):
    idx=A.index; bd=Bd.reindex(idx).ffill().values; out=[]; state='armed'; off=0
    for i in range(max(r,W),len(idx)):
        on=bool(np.all(bd[i-r+1:i+1]>=thb))
        if state=='called':
            off = off+1 if bd[i]<reb else 0
            if off>=mp: state='armed'; off=0
            continue
        if on:
            w0=idx[max(0,i-W)]
            # the peak of ACTIVITY is the high of A, which is the low of claims
            d=B.channel_peak(A[w0:idx[i]],w0,idx[i],band,1,False)
            if d is None: d=idx[i]
            out.append((idx[i]+pd.DateOffset(months=pub),d)); state='called'; off=0
    return out
def trough_calls(A,Bd,thb,reb,rt,drop,mp,W,band,pub=1):
    idx=A.index; a=A.values; bd=Bd.reindex(idx).ffill().values
    out=[]; state='quiet'; off=0; amin=1e9; amin_i=0; rise=0; prev=a[0]
    for i in range(1,len(a)):
        if a[i]<amin: amin=a[i]; amin_i=i; rise=0
        elif a[i]>prev: rise+=1
        else: rise=0
        prev=a[i]
        if state=='called':
            off = off+1 if bd[i]<reb else 0
            if off>=mp: state='quiet'; off=0
            continue
        if state=='quiet':
            if bd[i]>=thb: state='armed'; amin=a[i]; amin_i=i; rise=0
            continue
        if rise>=rt and (a[i]-amin)>=drop:
            w0=idx[max(0,i-W)]
            # the trough of ACTIVITY is the low of A, which is the high of claims
            d=B.channel_trough(A[w0:idx[i]],w0,idx[i],band,1,W,False)
            if d is None: d=idx[amin_i]
            out.append((idx[i]+pd.DateOffset(months=pub),d)); state='called'; off=0
    return out
def sc(calls,T,cut='1973-01'):
    got={}; fa=[]
    for pub,dt in calls:
        if pub<pd.Timestamp(cut): continue
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
for sm,L,gap,thb,reb,r,mp,W,band in itertools.product((1,2,3),(18,24,36),(20.,30.),(50.,60.,70.),
        (25.,30.,40.),(1,2),(3,6,12),(9,12,18,24),(0.05,0.12,0.25)):
    g,fa=sc(peak_calls(act(sm),breadth(sm,L,gap),thb,reb,r,mp,W,band),PK)
    key=(len(g),-len(fa))
    if bp is None or key>bp[0]: bp=(key,(sm,L,gap,thb,reb,r,mp,W,band),dict(g),fa)
print('PEAK  ',bp[0],bp[1]); print('  hits',bp[2])
print('  other',[(a.strftime('%Y-%m'),b.strftime('%Y-%m')) for a,b in bp[3]])
bt=None
for sm,L,gap,thb,reb,rt,drop,mp,W,band in itertools.product((1,2,3),(18,24),(20.,30.),(50.,60.),
        (25.,30.,40.),(1,2,3),(1.,3.,5.),(3,6,12),(12,18,24),(0.05,0.12,0.25)):
    g,fa=sc(trough_calls(act(sm),breadth(sm,L,gap),thb,reb,rt,drop,mp,W,band),TR)
    key=(len(g),-len(fa))
    if bt is None or key>bt[0]: bt=(key,(sm,L,gap,thb,reb,rt,drop,mp,W,band),dict(g),fa)
print('TROUGH',bt[0],bt[1]); print('  hits',bt[2])
print('  other',[(a.strftime('%Y-%m'),b.strftime('%Y-%m')) for a,b in bt[3]])
