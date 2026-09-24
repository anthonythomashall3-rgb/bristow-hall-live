"""Monthly peak detector, 1971 panel, scored on every peak target; top configurations."""
import pandas as pd, numpy as np, itertools, warnings; warnings.filterwarnings('ignore')
SA=pd.read_csv('/home/claude/lab/dol/US_state_claims_monthly_sa_rt.csv',index_col=0,parse_dates=True)
# the full chronology: the committee's peaks plus the two objects Paper 1 dates
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
def peaks(Bd,thb,reb,r,mp,line=50.):
    b=Bd.values; idx=Bd.index; out=[]; state='armed'; off=0
    for i in range(r,len(b)):
        on=bool(np.all(b[i-r+1:i+1]>=thb))
        if state=='called':
            off = off+1 if b[i]<reb else 0
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
for sm,L,gap,thb,reb,r,mp,line in itertools.product((1,2,3),(18,24,36,48),(15.,20.,25.,30.,35.),
        (40.,45.,50.,55.,60.,65.),(20.,25.,30.,35.,40.),(1,2),(2,3,6,12),(40.,50.,60.)):
    g,fa=sc(peaks(breadth(sm,L,gap),thb,reb,r,mp,line))
    rows.append((len(g),-len(fa),(sm,L,gap,thb,reb,r,mp,line),dict(g),fa))
rows.sort(key=lambda x:(-x[0],x[1]))
for b in rows[:8]:
    print(f'{b[0]}/8 other {-b[1]}  cfg(sm,L,gap,thb,rearm,r,mp,line)={b[2]}')
    print(f'   hits {b[3]}')
    print(f'   other {[(a.strftime("%Y-%m"),c.strftime("%Y-%m")) for a,c in b[4]]}')
w=[r for r in rows if '1990-07' in r[3]]
print(); print(f'configurations that catch 1990-07: {len(w)}')
w.sort(key=lambda x:(-x[0],x[1]))
for b in w[:4]:
    print(f'   {b[0]}/8 other {-b[1]} cfg={b[2]}  1990 {b[3]["1990-07"]}  hits {sorted(b[3])}')
