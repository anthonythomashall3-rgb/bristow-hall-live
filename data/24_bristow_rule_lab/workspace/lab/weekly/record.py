"""The complete real-time record, 1973-2026.

Weekly where the weekly file reaches (1986 on), monthly before it.
Breadth is pooled over 106 state-channels: fifty-three jurisdictions' initial claims and
the same jurisdictions' continued claims, each seasonally adjusted in real time with a
pooled warm-up.  Both are counter-cyclical, so a state counts as deteriorating when its
thirteen-week mean stands twenty-five log points or more above its own trailing two-year
minimum.  The peak is the crossing of the fifty-per-cent line, dated at the last week
below it - ESRI's clause.  The trough is the maximum of national claims, called once they
have fallen for four weeks and by five log points.
"""
import sys; sys.path.insert(0,'/home/claude')
import bristow_rule_v3 as B
import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
W_IC=pd.read_csv('/home/claude/lab/dol/US_state_claims_sa_pooled.csv',index_col=0,parse_dates=True)
W_BOTH=pd.read_csv('/home/claude/lab/dol/US_state_claims_both_sa.csv',index_col=0,parse_dates=True)
NCW=pd.read_csv('/home/claude/lab/weekly/US_nat_claims_pooled.csv',index_col=0,parse_dates=True)
M_SA=pd.read_csv('/home/claude/lab/dol/US_state_claims_monthly_sa_rt.csv',index_col=0,parse_dates=True)
NCM=pd.read_csv('/home/claude/lab/dol/US_nat_claims_monthly_rt.csv',index_col=0,parse_dates=True)
def mo(t): return pd.Timestamp(t.year,t.month,1)
def md(x,y): return (x.year-y.year)*12+(x.month-y.month)
def breadth(P,sm,L,gap):
    K=P.rolling(sm).mean()*100.0
    S=K-K.rolling(L,min_periods=L//2).min()
    return ((S>=gap).sum(axis=1)/S.notna().sum(axis=1)*100.0).dropna()
def peaks(Bd,thb,reb,r,mp,line=50.,pub=None,freq='W'):
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
            p=idx[i]+(pd.Timedelta(days=7) if freq=='W' else pd.DateOffset(months=1))
            out.append((p,mo(idx[j]))); state='called'; off=0
    return out
def troughs(NC,sm,L,run,drop,arm,rearm,mp,freq='W'):
    N=(np.log(NC.iloc[:,0])*100.0).rolling(sm).mean()
    G=N-N.rolling(L,min_periods=L//2).min()
    df=pd.concat([N.rename('n'),G.rename('g')],axis=1).dropna()
    n=df['n'].values; g=df['g'].values; idx=df.index
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
            p=idx[i]+(pd.Timedelta(days=7) if freq=='W' else pd.DateOffset(months=1))
            out.append((p,mo(idx[nmax_i]))); state='called'; off=0
    return out
PK={'1973-11':'NBER','1980-01':'NBER','1981-07':'NBER','1990-07':'NBER','2001-03':'NBER',
    '2007-12':'NBER','2020-02':'NBER','2023-06':'Paper 1, rolling episode onset',
    '2024-03':'Paper 1, national labour-market recession onset'}
TR={'1975-03':'NBER','1980-07':'NBER','1982-11':'NBER','1991-03':'NBER','2001-11':'NBER',
    '2009-06':'NBER','2020-04':'NBER',
    '2024-08':'Paper 1, national labour-market recession end',
    '2026-05':'Paper 1, rolling episode end'}
mp_=[c for c in peaks(breadth(M_SA,2,36,25.),65.,30.,1,2,line=60.,freq='M')
     if c[0]>=pd.Timestamp('1973-01-01')]
mt_=[c for c in troughs(NCM,1,18,1,1.,50.,15.,3,freq='M')
     if pd.Timestamp('1973-01-01')<=c[0]<pd.Timestamp('1986-02-01')]
wp_ic=[c for c in peaks(breadth(W_IC,13,104,25.),50.,30.,2,26) if c[0]>=pd.Timestamp('1988-01-01')]
wp_bo=[c for c in peaks(breadth(W_BOTH,13,104,25.),50.,30.,2,26) if c[0]>=pd.Timestamp('1988-01-01')]
wt_=[c for c in troughs(NCW,8,104,4,5.,50.,10.,13) if c[0]>=pd.Timestamp('1988-01-01')]
def report(calls,T,label):
    print(f'--- {label}')
    hits={}; other=[]
    for pub,dt in sorted(calls):
        near=min(T,key=lambda k: abs(md(dt,pd.Timestamp(k+'-01'))))
        lag=md(mo(pub),pd.Timestamp(near+'-01')); err=md(dt,pd.Timestamp(near+'-01'))
        ok=abs(lag)<=2 and abs(err)<=2 and near not in hits
        if ok: hits[near]=(lag,err)
        else: other.append((pub,dt))
        print(f'   {"HIT " if ok else "    "} published {pub:%Y-%m}  dated {dt:%Y-%m}   nearest {near} '
              f'({T[near]})  lag {lag:+3d}  error {err:+3d}')
    print(f'   => {len(hits)} of {len(T)} inside two months at both;  {len(other)} other calls')
    print(f'   => never called: {[k for k in T if k not in hits]}')
    return hits,other
report(mp_,PK,'PEAKS: the monthly state panel, 1973-2026, one configuration throughout')
report(mt_+wt_,TR,'TROUGHS: monthly before 1986, weekly after')
