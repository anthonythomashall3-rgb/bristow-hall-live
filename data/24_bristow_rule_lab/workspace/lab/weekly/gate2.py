"""Two conditions, both weekly: breadth across the states, and depth in the nation.
Minimise false alerts subject to alerting all four peaks within two months."""
import pandas as pd, numpy as np, itertools, warnings; warnings.filterwarnings('ignore')
SA=pd.read_csv('/home/claude/lab/dol/US_state_claims_sa_log.csv',index_col=0,parse_dates=True)
W=pd.read_csv('/home/claude/lab/weekly/US_weekly_panel.csv',index_col=0,parse_dates=True)
PK=['1990-07','2001-03','2007-12','2020-02']
def mo(t): return pd.Timestamp(t.year,t.month,1)
def md(x,y): return (x.year-y.year)*12+(x.month-y.month)
NAT=(np.log(W['initial claims'])*100.0)
def nat_gap(sm,L):
    K=NAT.rolling(sm).mean()
    return (K-K.rolling(L,min_periods=L//2).min())
def breadth(sm,L,thsq):
    K=SA.rolling(sm).mean()*100.0
    S=K-K.rolling(L,min_periods=L//2).min()
    return (S>=thsq).sum(axis=1)/S.notna().sum(axis=1)*100.0
def alerts(cond,r,mp,idx):
    out=[]; last=-10**9; v=cond.values
    for i in range(r,len(v)):
        if i-last<mp: continue
        if np.all(v[i-r+1:i+1]):
            out.append(idx[i]+pd.Timedelta(days=7)); last=i
    return out
rows=[]
for sm,L,thsq,thb in itertools.product((13,26),(52,78,104),(10.,15.,20.,25.),(40.,50.,60.,70.,80.)):
    B=breadth(sm,L,thsq)
    for nsm,nL,nth in itertools.product((13,),(52,104),(0.,5.,10.,15.,20.)):
        G=nat_gap(nsm,nL)
        df=pd.concat([B.rename('b'),G.rename('g')],axis=1,sort=True).dropna()
        cond=(df['b']>=thb)&(df['g']>=nth)
        for r,mp in itertools.product((4,8,13),(52,78,104)):
            al=alerts(cond,r,mp,df.index)
            if not al: continue
            hit={}; fa=0
            for a in al:
                m=mo(a); best=None
                for k in PK:
                    if k in hit: continue
                    e=md(m,pd.Timestamp(k+'-01'))
                    if abs(e)<=2 and (best is None or abs(e)<abs(best[1])): best=(k,e)
                if best: hit[best[0]]=best[1]
                else: fa+=1
            if len(hit)==4:
                rows.append((-fa,fa,sm,L,thsq,thb,nsm,nL,nth,r,mp,dict(hit),
                             [a.strftime('%Y-%m') for a in al]))
rows.sort(reverse=True)
print(f'{"false":>5s} {"sm":>3s} {"L":>4s} {"thsq":>5s} {"thb":>4s} {"nL":>4s} {"nth":>4s} {"r":>3s} {"mp":>4s}  lags')
for b in rows[:12]:
    print(f'{b[1]:5d} {b[2]:3d} {b[3]:4d} {b[4]:5.0f} {b[5]:4.0f} {b[7]:4d} {b[8]:4.0f} {b[9]:3d} {b[10]:4d}  {b[11]}')
if rows:
    b=rows[0]; print(); print('alerts of the best:', ', '.join(b[12]))
