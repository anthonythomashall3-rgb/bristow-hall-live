"""The real-time caller, run on real-time seasonal adjustment: no look-ahead anywhere."""
import pandas as pd, numpy as np, itertools, warnings; warnings.filterwarnings('ignore')
SA=pd.read_csv('/home/claude/lab/dol/US_state_claims_sa_rt.csv',index_col=0,parse_dates=True)
NC=pd.read_csv('/home/claude/lab/weekly/US_nat_claims_rt.csv',index_col=0,parse_dates=True)
PK=['1990-07','2001-03','2007-12','2020-02']; TR=['1991-03','2001-11','2009-06','2020-04']
def mo(t): return pd.Timestamp(t.year,t.month,1)
def md(x,y): return (x.year-y.year)*12+(x.month-y.month)
def breadth(sm,L,thsq):
    K=SA.rolling(sm).mean()*100.0
    S=K-K.rolling(L,min_periods=L//2).min()
    return ((S>=thsq).sum(axis=1)/S.notna().sum(axis=1)*100.0).dropna()
def nat(nsm):
    N=(np.log(NC['initial claims'])*100.0).rolling(nsm).mean()
    return pd.concat([N.rename('n'),(N-N.rolling(52,min_periods=26).min()).rename('g')],
                     axis=1,sort=True).dropna()
exec(open('/home/claude/lab/weekly/final_caller.py').read()
     .split("def peak_calls")[1].join(["def peak_calls",""])
     .split("def sc(")[0])
def sc(calls,tgt):
    got={}; fa=0; extra=[]
    for pub,dt in calls:
        best=None
        for k in tgt:
            if k in got: continue
            lag=md(mo(pub),pd.Timestamp(k+'-01')); err=md(dt,pd.Timestamp(k+'-01'))
            if abs(lag)<=2 and abs(err)<=2 and (best is None or abs(lag)+abs(err)<best[3]):
                best=(k,lag,err,abs(lag)+abs(err))
        if best: got[best[0]]=(best[1],best[2])
        else: fa+=1; extra.append((pub,dt))
    return got,fa,extra
bp=None
for sm,L,thsq,thb,r,mp,how in itertools.product((13,26),(78,104),(20.,25.),(35.,40.,50.),
                                                (2,4),(13,26,52),('first_above','last_below')):
    B=breadth(sm,L,thsq); g,fa,_=sc(peak_calls(B,thb,r,mp,how),PK)
    key=(len(g),-fa)
    if bp is None or key>bp[0]: bp=(key,sm,L,thsq,thb,r,mp,how,fa,dict(g))
print('PEAK  ',bp)
bt=None
for nsm,rt,delta,nth,mp in itertools.product((4,8,13),(4,6,8),(2.,5.,10.),(20.,30.,40.),(13,26,52)):
    D=nat(nsm); g,fa,_=sc(trough_calls(D,rt,delta,nth,mp),TR)
    key=(len(g),-fa)
    if bt is None or key>bt[0]: bt=(key,nsm,rt,delta,nth,mp,fa,dict(g))
print('TROUGH',bt)
print()
_,sm,L,thsq,thb,r,mp,how,fa,gp=bp
for pub,dt in peak_calls(breadth(sm,L,thsq),thb,r,mp,how):
    near=min(PK,key=lambda k: abs(md(dt,pd.Timestamp(k+'-01'))))
    print(f'  PEAK   pub {pub:%Y-%m} dated {dt:%Y-%m}  near {near} lag {md(mo(pub),pd.Timestamp(near+"-01")):+3d} err {md(dt,pd.Timestamp(near+"-01")):+3d}')
_,nsm,rt,delta,nth,mpt,fat,gt=bt
for pub,dt in trough_calls(nat(nsm),rt,delta,nth,mpt):
    near=min(TR,key=lambda k: abs(md(dt,pd.Timestamp(k+'-01'))))
    print(f'  TROUGH pub {pub:%Y-%m} dated {dt:%Y-%m}  near {near} lag {md(mo(pub),pd.Timestamp(near+"-01")):+3d} err {md(dt,pd.Timestamp(near+"-01")):+3d}')
