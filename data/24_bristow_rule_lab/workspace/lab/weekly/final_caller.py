"""The real-time caller, weekly, both ends, one call per episode.

Both detectors fire once and then disarm; each re-arms only after its own condition has
been false for mp weeks, which is Bry and Boschan's minimum phase in weeks.

PEAK    breadth across the states.  B(t) = the share of states whose sm-week mean of
        seasonally adjusted initial claims stands thsq log points or more above its own
        trailing L-week minimum.  Fires when B >= thb for r weeks; dated at the first
        week B stood at or above the fifty-per-cent line.
TROUGH  national claims.  Fires when the nsm-week mean of seasonally adjusted initial
        claims has fallen rt weeks and delta log points from its running maximum, and
        that maximum stands nth log points above its own trailing 52-week minimum;
        dated at the week claims peaked.  The running maximum is the current spike's:
        it restarts whenever claims stand at their trailing 52-week minimum (the gap
        is zero), the same base the gap itself is measured from.  Until 2 September
        2026 the maximum ran from the last call and was never restarted, so on the
        Department's national file the 1982 maximum, which stands above the 2001
        maximum, was still 'the maximum' in 2001 and its gap (38 points) failed the
        arm test: the 2001 trough could not be called.  On the state-sum file this
        script was built on (1986 on) the two definitions give the same calls at
        every week (final_caller_pre_fix_2026-09-02.py is the old file).
Weekly data is published the following week, so every call is charged seven days.
"""
import pandas as pd, numpy as np, itertools, warnings; warnings.filterwarnings('ignore')
SA=pd.read_csv('/home/claude/lab/dol/US_state_claims_sa_log.csv',index_col=0,parse_dates=True)
W=pd.read_csv('/home/claude/lab/weekly/US_weekly_panel.csv',index_col=0,parse_dates=True)
PK=['1990-07','2001-03','2007-12','2020-02']; TR=['1991-03','2001-11','2009-06','2020-04']
def mo(t): return pd.Timestamp(t.year,t.month,1)
def md(x,y): return (x.year-y.year)*12+(x.month-y.month)
def breadth(sm,L,thsq):
    K=SA.rolling(sm).mean()*100.0
    S=K-K.rolling(L,min_periods=L//2).min()
    return ((S>=thsq).sum(axis=1)/S.notna().sum(axis=1)*100.0).dropna()
def nat(nsm):
    N=(np.log(W['initial claims'])*100.0).rolling(nsm).mean()
    return pd.concat([N.rename('n'),(N-N.rolling(52,min_periods=26).min()).rename('g')],
                     axis=1,sort=True).dropna()
def peak_calls(B,thb,r,mp,how='first_above',line=50.,pub=7):
    b=B.values; idx=B.index; out=[]; armed=True; off=0
    for i in range(r,len(b)):
        on=np.all(b[i-r+1:i+1]>=thb)
        if not armed:
            off = off+1 if not on else 0
            if off>=mp: armed=True
            continue
        if on:
            j=i
            while j>0 and b[j]>=line: j-=1
            k=j if how=='last_below' else min(j+1,len(b)-1)
            out.append((idx[i]+pd.Timedelta(days=pub),mo(idx[k]))); armed=False; off=0
    return out
def trough_calls(D,rt,delta,nth,mp,pub=7):
    n=D['n'].values; g=D['g'].values; idx=D.index; out=[]; armed=False; off=0
    nmax=-1e9; nmax_i=0; fall=0; prev=n[0]
    for i in range(1,len(n)):
        if g[i]<=0 or n[i]>nmax: nmax=n[i]; nmax_i=i; fall=0   # a new 52-week low restarts the spike's maximum
        elif n[i]<prev: fall+=1
        else: fall=0
        prev=n[i]
        on = fall>=rt and (nmax-n[i])>=delta and g[nmax_i]>=nth
        if not armed:
            off = off+1 if not on else 0
            if off>=mp and g[i]<nth: armed=True
            continue
        if on:
            out.append((idx[i]+pd.Timedelta(days=pub),mo(idx[nmax_i]))); armed=False; off=0
            nmax=n[i]; nmax_i=i; fall=0
    return out
def sc(calls,tgt):
    got={}; fa=0
    for pub,dt in calls:
        best=None
        for k in tgt:
            if k in got: continue
            lag=md(mo(pub),pd.Timestamp(k+'-01')); err=md(dt,pd.Timestamp(k+'-01'))
            if abs(lag)<=2 and abs(err)<=2 and (best is None or abs(lag)+abs(err)<best[3]):
                best=(k,lag,err,abs(lag)+abs(err))
        if best: got[best[0]]=(best[1],best[2])
        else: fa+=1
    return got,fa
if __name__=='__main__':
    bp=None
    for sm,L,thsq,thb,r,mp,how in itertools.product((13,26),(78,104),(20.,25.),(35.,40.,50.),
                                                    (2,4),(13,26,52),('first_above','last_below')):
        B=breadth(sm,L,thsq); g,fa=sc(peak_calls(B,thb,r,mp,how),PK)
        key=(len(g),-fa)
        if bp is None or key>bp[0]: bp=(key,sm,L,thsq,thb,r,mp,how,fa,dict(g))
    print('PEAK  ',bp)
    bt=None
    for nsm,rt,delta,nth,mp in itertools.product((4,8,13),(4,6,8),(2.,5.,10.),(20.,30.,40.),(13,26,52)):
        D=nat(nsm); g,fa=sc(trough_calls(D,rt,delta,nth,mp),TR)
        key=(len(g),-fa)
        if bt is None or key>bt[0]: bt=(key,nsm,rt,delta,nth,mp,fa,dict(g))
    print('TROUGH',bt)
