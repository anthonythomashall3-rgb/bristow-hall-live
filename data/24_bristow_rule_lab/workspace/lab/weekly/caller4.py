"""Two independent weekly detectors, one for each end.

The two ends are different questions and are asked separately; neither waits for the
other.  Both are censored by Bry and Boschan's minimum phase.

PEAK    the share of states whose 13-week mean of seasonally adjusted initial claims
        stands thsq log points or more above its own trailing L-week minimum reaches
        thb per cent and holds r weeks.  Dated at the last week the share stood below
        the fifty-per-cent line.
TROUGH  national initial claims have fallen for rt weeks and by delta log points from
        their running maximum, and that maximum stands nth log points above the
        trailing 52-week minimum.  Dated at the week claims peaked.
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
def peaks(B,thb,r,mp,line=50.,pub=7):
    b=B.values; idx=B.index; out=[]; last=-10**9
    for i in range(r,len(b)):
        if i-last<mp: continue
        if np.all(b[i-r+1:i+1]>=thb):
            j=i
            while j>0 and b[j]>=line: j-=1
            out.append((idx[i]+pd.Timedelta(days=pub),mo(idx[j]))); last=i
    return out
def troughs(D,rt,delta,nth,mp,pub=7):
    n=D['n'].values; g=D['g'].values; idx=D.index; out=[]; last=-10**9
    nmax=-1e9; nmax_i=0; fall=0; prev=n[0]
    for i in range(1,len(n)):
        if n[i]>nmax: nmax=n[i]; nmax_i=i; fall=0
        elif n[i]<prev: fall+=1
        else: fall=0
        prev=n[i]
        if i-last>=mp and fall>=rt and (nmax-n[i])>=delta and g[nmax_i]>=nth:
            out.append((idx[i]+pd.Timedelta(days=pub),mo(idx[nmax_i]))); last=i
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
bp=[]
for sm,L,thsq,thb,r,mp in itertools.product((13,26),(52,78,104),(10.,15.,20.,25.),
                                            (35.,40.,50.,60.,70.),(2,4,8),(52,78,104)):
    B=breadth(sm,L,thsq); got,fa=sc(peaks(B,thb,r,mp),PK)
    if got: bp.append((len(got),-fa,sm,L,thsq,thb,r,mp,fa,dict(got)))
bp.sort(reverse=True)
print('PEAK detector')
for b in bp[:6]:
    print(f'  {b[0]}/4 false {b[8]:2d}  sm={b[2]} L={b[3]} thsq={b[4]:.0f} thb={b[5]:.0f} r={b[6]} mp={b[7]}  {b[9]}')
bt=[]
for nsm,rt,delta,nth,mp in itertools.product((4,13,26),(4,6,8,12),(2.,5.,10.),(10.,20.,30.),(52,78,104)):
    D=nat(nsm); got,fa=sc(troughs(D,rt,delta,nth,mp),TR)
    if got: bt.append((len(got),-fa,nsm,rt,delta,nth,mp,fa,dict(got)))
bt.sort(reverse=True)
print('TROUGH detector')
for b in bt[:6]:
    print(f'  {b[0]}/4 false {b[7]:2d}  nsm={b[2]} rt={b[3]} delta={b[4]:.0f} nth={b[5]:.0f} mp={b[6]}  {b[8]}')
