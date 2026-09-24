"""Drive the trough detector to zero false calls: re-arm only after the national claims
gap has fallen back below a lower threshold and stayed there."""
import pandas as pd, numpy as np, itertools, warnings; warnings.filterwarnings('ignore')
NC=pd.read_csv('/home/claude/lab/weekly/US_nat_claims_rt.csv',index_col=0,parse_dates=True)
TR={'1991-03':'NBER','2001-11':'NBER','2009-06':'NBER','2020-04':'NBER'}
def mo(t): return pd.Timestamp(t.year,t.month,1)
def md(x,y): return (x.year-y.year)*12+(x.month-y.month)
def calls(smooth,run,drop,arm_gap,rearm_gap,min_phase,pub=7):
    N=(np.log(NC['initial claims'])*100.0).rolling(smooth).mean()
    G=N-N.rolling(52,min_periods=26).min()
    df=pd.concat([N.rename('n'),G.rename('g')],axis=1).dropna()
    n=df['n'].values; g=df['g'].values; idx=df.index
    # three states.  quiet -> armed when the gap reaches arm_gap; armed -> fires when
    # claims have turned down; called -> quiet again only after the gap has stayed below
    # rearm_gap for min_phase weeks.  The middle leg is what stops a jobless recovery
    # being called twice: the gap must go quiet AND rise again before a second call.
    out=[]; state='quiet'; off=0; nmax=-1e9; nmax_i=0; fall=0; prev=n[0]
    for i in range(1,len(n)):
        if n[i]>nmax: nmax=n[i]; nmax_i=i; fall=0
        elif n[i]<prev: fall+=1
        else: fall=0
        prev=n[i]
        if state=='called':
            off = off+1 if g[i]<rearm_gap else 0
            if off>=min_phase: state='quiet'; off=0
            continue
        if state=='quiet':
            if g[i]>=arm_gap: state='armed'; nmax=n[i]; nmax_i=i; fall=0
            continue
        if fall>=run and (nmax-n[i])>=drop and g[nmax_i]>=arm_gap:
            d=idx[nmax_i]
            out.append((idx[i]+pd.Timedelta(days=pub),mo(d)))
            state='called'; off=0
    return out
best=[]
for smooth,run,drop,arm,rearm,mp in itertools.product((4,8,13),(4,6,8),(5.,10.),(30.,40.,50.),
                                                      (5.,10.,15.,20.),(13,26,52,78)):
    cs=[c for c in calls(smooth,run,drop,arm,rearm,mp) if c[0]>=pd.Timestamp('1991-01-01')]
    hit={}; fa=0
    for pub,dt in cs:
        b=None
        for k in TR:
            if k in hit: continue
            lag=md(mo(pub),pd.Timestamp(k+'-01')); err=md(dt,pd.Timestamp(k+'-01'))
            if abs(lag)<=2 and abs(err)<=2 and (b is None or abs(lag)+abs(err)<b[3]):
                b=(k,lag,err,abs(lag)+abs(err))
        if b: hit[b[0]]=(b[1],b[2])
        else: fa+=1
    best.append((len(hit),-fa,smooth,run,drop,arm,rearm,mp,fa,dict(hit)))
best.sort(reverse=True)
print(f'{"hit":>4s} {"false":>5s} {"sm":>3s} {"run":>4s} {"drop":>5s} {"arm":>4s} {"rearm":>6s} {"mp":>4s}')
for b in best[:8]:
    print(f'{b[0]}/4 {b[8]:5d} {b[2]:3d} {b[3]:4d} {b[4]:5.0f} {b[5]:4.0f} {b[6]:6.0f} {b[7]:4d}   {b[9]}')
