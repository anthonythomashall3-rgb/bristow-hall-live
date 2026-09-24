"""Symmetric weekly caller: one series dates both ends, breadth only arms.

Claims are counter-cyclical, so on the negated log claims the rule's two clauses date the
two ends directly:
  PEAK   the low-band clause - the last week claims stood within the band of their own low
         before the rise.  That is the month activity peaked.
  TROUGH the high-band clause - the last week claims stood within the band of their own
         high.  That is the month activity bottomed.
Breadth across the states is the ARMING condition, not the dating object: it is the
pervasiveness test, and it is what stops a one-state or one-industry disturbance being
called a national turning point.
"""
import sys; sys.path.insert(0,'/home/claude')
import bristow_rule_v3 as B
import pandas as pd, numpy as np, itertools, warnings; warnings.filterwarnings('ignore')
SA=pd.read_csv('/home/claude/lab/dol/US_state_claims_sa_pooled.csv',index_col=0,parse_dates=True)
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
def activity(sm):
    return (-np.log(NC['initial claims'])*100.0).rolling(sm).mean().dropna()
def run(A,Bd,thb,rearm_b,r,mp,W,band,rt,drop,pub=7):
    """A: activity (negated log claims).  Bd: breadth."""
    idx=A.index; a=A.values; n=len(a)
    bd=Bd.reindex(idx).ffill().values
    out=[]; state='armed'; off=0; pk_i=None; amin=1e9; amin_i=0; rise=0; prev=None
    for i in range(max(r,W),n):
        if state=='called_trough':
            off = off+1 if bd[i]<rearm_b else 0
            if off>=mp: state='armed'; off=0
            continue
        if state=='armed':
            if np.all(bd[i-r+1:i+1]>=thb):
                w0=idx[max(0,i-W)]
                d=B.channel_trough(A[w0:idx[i]],w0,idx[i],band,1,W,False)   # low of activity
                if d is None: d=idx[i]
                out.append(('peak',idx[i]+pd.Timedelta(days=pub),mo(d)))
                state='contraction'; pk_i=i; amin=a[i]; amin_i=i; rise=0; prev=a[i]
            continue
        # contraction: wait for activity to turn up
        if a[i]<amin: amin=a[i]; amin_i=i; rise=0
        elif a[i]>prev: rise+=1
        else: rise=0
        prev=a[i]
        if rise>=rt and (a[i]-amin)>=drop:
            w0=idx[amin_i]
            d=B.channel_peak(-A[idx[pk_i]:idx[i]],idx[pk_i],idx[i],band,1,False)
            d=idx[amin_i] if d is None else d
            out.append(('trough',idx[i]+pd.Timedelta(days=pub),mo(d)))
            state='called_trough'; off=0
    return out
def sc(calls,cut='1988-01'):
    hp={}; ht={}; fa=[]
    for kind,pub,dt in calls:
        if pub<pd.Timestamp(cut): continue
        T,store=(PK,hp) if kind=='peak' else (TR,ht)
        b=None
        for k in T:
            if k in store: continue
            lag=md(mo(pub),pd.Timestamp(k+'-01')); err=md(dt,pd.Timestamp(k+'-01'))
            if abs(lag)<=2 and abs(err)<=2 and (b is None or abs(lag)+abs(err)<b[3]):
                b=(k,lag,err,abs(lag)+abs(err))
        if b: store[b[0]]=(b[1],b[2])
        else: fa.append((kind,pub,dt))
    return hp,ht,fa
best=None
for sm,L,gap,thb,reb,r,mp,W,band,rt,drop in itertools.product(
        (13,),(104,),(25.,),(50.,60.),(30.,40.),(2,4),(26,52),(78,104,156),
        (0.05,0.12,0.25),(4,8,13),(2.,5.,10.)):
    A=activity(sm); Bd=breadth(sm,L,gap)
    hp,ht,fa=sc(run(A,Bd,thb,reb,r,mp,W,band,rt,drop))
    key=(len(hp)+len(ht),-len(fa))
    if best is None or key>best[0]: best=(key,(sm,L,gap,thb,reb,r,mp,W,band,rt,drop),hp,ht,fa)
print('BEST',best[0]); print('  cfg (sm,L,gap,thb,rearm,r,mp,W,band,rt,drop)=',best[1])
print('  peaks  ',best[2]); print('  troughs',best[3])
print('  other  ',[(k,a.strftime('%Y-%m'),b.strftime('%Y-%m')) for k,a,b in best[4]])
