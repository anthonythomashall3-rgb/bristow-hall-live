"""The trough on the weekly state claims file, read as breadth: the mirror of the peak caller.

speed_final.py calls peaks from the share of states whose initial claims have risen from
their trailing low (real-time factors, 1986 on; record from 1991) and troughs from the
national count alone (2 of 4 inside the month).  Here the trough is read the way the peak
is: the share of states whose smoothed log claims have FALLEN `th` log points below their
trailing `L`-week maximum; inside a contraction (from a peak call to the next trough call)
the trough is called the first week that share has stood at or above `q` per cent for `r`
weeks, dated at the month of the national count's maximum inside the contraction, published
seven days after the week's data (the Department's release lag).  Grid over (smooth, L, th,
q, r); the peak calls are speed_final's own.  Scored against the NBER troughs since 1991:
error in months, publication lag in months (within the month = lag <= 1), and other calls.
"""
import sys, itertools, warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
sys.path.insert(0,'/home/claude/lab/weekly')
SA=pd.read_csv('/home/claude/lab/dol/US_state_claims_sa_rt.csv',index_col=0,parse_dates=True)
NC=pd.read_csv('/home/claude/lab/weekly/US_nat_claims_rt.csv',index_col=0,parse_dates=True)
TR=[pd.Timestamp(x+'-01') for x in ['1991-03','2001-11','2009-06','2020-04']]
def mo(t): return pd.Timestamp(t.year,t.month,1)
def md(x,y): return (x.year-y.year)*12+(x.month-y.month)
src=open('/home/claude/lab/weekly/final_caller.py').read()
exec("def peak_calls"+src.split("def peak_calls")[1].split("def sc(")[0].split("def trough_calls")[0])
def breadth_up(sm,L,th):
    K=SA.rolling(sm).mean()*100.0; S=K-K.rolling(L,min_periods=L//2).min()
    return ((S>=th).sum(axis=1)/S.notna().sum(axis=1)*100.0).dropna()
def breadth_down(sm,L,th):
    K=SA.rolling(sm).mean()*100.0; S=K.rolling(L,min_periods=L//2).max()-K
    return ((S>=th).sum(axis=1)/S.notna().sum(axis=1)*100.0).dropna()
PK=peak_calls(breadth_up(13,104,25.),50.,2,52,'first_above')      # speed_final's peak setting
N=(np.log(NC['initial claims'])*100.0).rolling(4).mean()
def trough_breadth(Bd,q,r,pub=7,min_gap=26):
    out=[]; pk_iter=iter(sorted(PK)); nxt=next(pk_iter,None); state='quiet'; start=None; run=0
    for t,v in Bd.items():
        while nxt is not None and nxt[0]<=t:
            state='open'; start=nxt[0]; run=0; nxt=next(pk_iter,None)
        if state!='open': continue
        if (t-start).days<7*min_gap: continue
        run=run+1 if v>=q else 0
        if run>=r:
            seg=N[start:t].dropna()
            if len(seg): out.append((t+pd.Timedelta(days=pub),mo(seg.idxmax())))
            state='quiet'; run=0
    return out
def score(calls,cut='1991-01'):
    calls=[(p,d) for p,d in calls if p>=pd.Timestamp(cut)]
    got={}; other=[]
    for p,d in calls:
        best=None
        for k in TR:
            if k in got: continue
            e=md(d,k)
            if abs(e)<=6 and (best is None or abs(e)<abs(best[1])): best=(k,e)
        if best: got[best[0]]=(p,d,best[1])
        else: other.append((p,d))
    return got,other
if __name__=='__main__':
    print('peak calls (speed_final setting):',[(p.strftime('%Y-%m-%d'),d.strftime('%Y-%m')) for p,d in PK if p>=pd.Timestamp('1991-01-01')])
    rows=[]
    for sm,L,th,q,r in itertools.product((4,8,13),(26,52,104),(10.,15.,25.,35.),(50.,60.,70.),(2,4,8)):
        Bd=breadth_down(sm,L,th); calls=trough_breadth(Bd,q,r); got,other=score(calls)
        e=[v[2] for v in got.values()]; lag=[md(mo(v[0]),k) for k,v in got.items()]
        rows.append((len(got),-len(other),sum(l<=1 for l in lag),sum(abs(x)<=1 for x in e),sum(x==0 for x in e),(sm,L,th,q,r),got,other))
    rows.sort(key=lambda x:(x[0],x[1],x[2],x[3],x[4]),reverse=True)
    print('\nhits / other / in-month / within 1 / exact | (smooth, L weeks, th log points, q %, r weeks)')
    for x in rows[:8]:
        print(f'  hits {x[0]}/4 other {-x[1]} inMonth {x[2]} w1 {x[3]} exact {x[4]} | {x[5]}')
        print('     ',{k.strftime('%Y-%m'):(v[1].strftime('%Y-%m'),v[2],'pub '+v[0].strftime('%Y-%m-%d'),'lag '+str(md(mo(v[0]),k))) for k,v in x[6].items()})
        if x[7]: print('      other:',[(p.strftime('%Y-%m-%d'),d.strftime('%Y-%m')) for p,d in x[7]])
    z=[x for x in rows if x[1]==0]
    if z:
        z.sort(key=lambda x:(x[0],x[2],x[3],x[4]),reverse=True); x=z[0]
        print(f'  best with no other call: hits {x[0]}/4 inMonth {x[2]} w1 {x[3]} exact {x[4]} | {x[5]}')
        print('     ',{k.strftime('%Y-%m'):(v[1].strftime('%Y-%m'),v[2],'pub '+v[0].strftime('%Y-%m-%d'),'lag '+str(md(mo(v[0]),k))) for k,v in x[6].items()})
