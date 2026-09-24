"""Monthly peak detector with two ways to go quiet.

The machine must return to quiet before it can call again.  There are two ways for an
episode to be over as far as the arming is concerned: the field thins out (breadth falls
back) or the level recovers (national claims fall back to their own base).  Requiring both
is what kept the 1981 peak from being called after the 1980 one, since state claims breadth
never thinned between them while the national level plainly recovered.
"""
import pandas as pd, numpy as np, itertools, warnings; warnings.filterwarnings('ignore')
SA=pd.read_csv('/home/claude/lab/dol/US_state_claims_monthly_sa_rt.csv',index_col=0,parse_dates=True)
NC=pd.read_csv('/home/claude/lab/dol/US_nat_claims_monthly_rt.csv',index_col=0,parse_dates=True)
PK={'1973-11':'NBER','1980-01':'NBER','1981-07':'NBER','1990-07':'NBER','2001-03':'NBER',
    '2007-12':'NBER','2020-02':'NBER',
    '2023-06':'Paper 1, rolling episode onset',
    '2024-03':'Paper 1, national labour-market recession onset'}
def md(x,y): return (x.year-y.year)*12+(x.month-y.month)
_B={}
def breadth(sm,L,gap):
    if (sm,L) not in _B:
        K=SA.rolling(sm).mean()*100.0
        _B[(sm,L)]=K-K.rolling(L,min_periods=L//2).min()
    S=_B[(sm,L)]
    return ((S>=gap).sum(axis=1)/S.notna().sum(axis=1)*100.0).dropna()
_G={}
def natgap(sm,L):
    if (sm,L) not in _G:
        N=(np.log(NC['initial claims'])*100.0).rolling(sm).mean()
        _G[(sm,L)]=(N-N.rolling(L,min_periods=L//2).min())
    return _G[(sm,L)]
def peaks(Bd,G,thb,reb,reg,r,mp,line):
    b=Bd.values; idx=Bd.index; g=G.reindex(idx).ffill().values
    out=[]; state='armed'; off=0
    for i in range(r,len(b)):
        on=bool(np.all(b[i-r+1:i+1]>=thb))
        if state=='called':
            quiet = (b[i]<reb) or (g[i]<reg)
            off = off+1 if quiet else 0
            if off>=mp: state='armed'; off=0
            continue
        if on:
            j=i
            while j>0 and b[j]>=line: j-=1
            out.append((idx[i]+pd.DateOffset(months=1),idx[j])); state='called'; off=0
    return out
def sc(calls,cut='1973-01'):
    got={}; fa=[]
    for pub,dt in calls:
        if pub<pd.Timestamp(cut): continue
        b=None
        for k in PK:
            if k in got: continue
            lag=md(pub,pd.Timestamp(k+'-01')); err=md(dt,pd.Timestamp(k+'-01'))
            if abs(lag)<=2 and abs(err)<=2 and (b is None or abs(lag)+abs(err)<b[3]):
                b=(k,lag,err,abs(lag)+abs(err))
        if b: got[b[0]]=(b[1],b[2])
        else: fa.append((pub,dt))
    return got,fa
rows=[]
for sm,L,gap,thb,reb,reg,r,mp,line in itertools.product((1,2,3),(24,36,48),(20.,25.,30.),
        (55.,60.,65.,70.),(25.,30.,35.,40.),(5.,10.,15.,20.),(1,2),(2,3,4),(50.,60.)):
    g,fa=sc(peaks(breadth(sm,L,gap),natgap(sm,12),thb,reb,reg,r,mp,line))
    rows.append((len(g),-len(fa),(sm,L,gap,thb,reb,reg,r,mp,line),dict(g),fa))
rows.sort(key=lambda x:(-x[0],x[1]))
for b in rows[:6]:
    print(f'{b[0]}/9 other {-b[1]}  cfg(sm,L,gap,thb,reb,reg,r,mp,line)={b[2]}')
    print(f'   hits {b[3]}')
    print(f'   other {[(a.strftime("%Y-%m"),c.strftime("%Y-%m")) for a,c in b[4]]}')
