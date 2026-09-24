"""The weekly state breadth index, and how fast it says a peak has happened."""
import pandas as pd, numpy as np, itertools, warnings; warnings.filterwarnings('ignore')
SA=pd.read_csv('/home/claude/lab/dol/US_state_claims_sa_log.csv',index_col=0,parse_dates=True)
PK=['1990-07','2001-03','2007-12','2020-02']
TR=['1991-03','2001-11','2009-06','2020-04']
def mo(t): return pd.Timestamp(t.year,t.month,1)
def md(x,y): return (x.year-y.year)*12+(x.month-y.month)
def breadth(sm,L,thsq):
    K=SA.rolling(sm).mean()*100.0                      # log points, claims
    S=K-K.rolling(L,min_periods=L//2).min()            # state Sahm gap, log points
    return (S>=thsq).sum(axis=1)/S.notna().sum(axis=1)*100.0
def alerts(B,th,r,mp):
    out=[]; last=-10**9; v=B.values; idx=B.index
    for i in range(r,len(v)):
        if i-last<mp: continue
        if np.all(v[i-r+1:i+1]>=th):
            out.append(idx[i]+pd.Timedelta(days=7)); last=i
    return out
rows=[]
for sm,L,thsq in itertools.product((4,13,26),(52,78,104),(5.,10.,15.,20.,25.)):
    B=breadth(sm,L,thsq).dropna()
    for th,r,mp in itertools.product((40.,50.,60.,70.,80.),(2,4,8,13),(26,52,78)):
        al=alerts(B,th,r,mp)
        if not al: continue
        hit={}; fa=0; lags=[]
        for a in al:
            m=mo(a); best=None
            for k in PK:
                if k in hit: continue
                e=md(m,pd.Timestamp(k+'-01'))
                if abs(e)<=2 and (best is None or abs(e)<abs(best[1])): best=(k,e)
            if best: hit[best[0]]=best[1]
            else: fa+=1
        if len(hit)>=3:
            rows.append((len(hit),-fa,sm,L,thsq,th,r,mp,fa,dict(hit)))
rows.sort(reverse=True)
print(f'{"hits":>4s} {"sm":>3s} {"L":>4s} {"thsq":>5s} {"th":>5s} {"r":>3s} {"mp":>4s} {"false":>6s}  lags')
for b in rows[:20]:
    print(f'{b[0]:2d}/4 {b[2]:3d} {b[4]:5.0f}{"":0s} {b[3]:4d} {b[5]:5.0f} {b[6]:3d} {b[7]:4d} {b[8]:6d}  {b[9]}')
