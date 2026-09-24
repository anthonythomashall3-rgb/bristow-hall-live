"""How fast can a weekly panel say a peak has happened, and how often is it wrong?
Scored to the bar: an alert counts for a peak if it falls within 2 months of it."""
import sys; sys.path.insert(0,'/home/claude/lab')
import pandas as pd, numpy as np, itertools, warnings; warnings.filterwarnings('ignore')
W=pd.read_csv('/home/claude/lab/weekly/US_weekly_panel.csv',index_col=0,parse_dates=True)
SIGN={'initial claims':-1,'continued claims':-1,'petroleum products supplied':1,'withheld taxes':1}
PK=['1990-07','2001-03','2007-12','2020-02']
def mo(t): return pd.Timestamp(t.year,t.month,1)
def md(x,y): return (x.year-y.year)*12+(x.month-y.month)
def comp(sm,L,scale):
    ch={c:(np.log(W[c])*SIGN[c]*100.0).rolling(sm).mean() for c in W.columns}
    cols=[]
    for c,v in ch.items():
        d=(v.rolling(L,min_periods=L//2).max()-v)
        if scale=='mad': d=d/(v.diff().abs().median() or 1.)
        elif scale=='sd': d=d/(v.diff().std() or 1.)
        cols.append(d.rename(c))
    return pd.concat(cols,axis=1,sort=True).mean(axis=1,skipna=True).dropna()
def alerts(D,th,r,mp):
    out=[]; last=-10**9; v=D.values; idx=D.index
    for i in range(r,len(v)):
        if i-last<mp: continue
        if all(v[j]>=th for j in range(i-r+1,i+1)):
            out.append(idx[i]+pd.Timedelta(days=7)); last=i
    return out
rows=[]
for scale in ('none','mad','sd'):
 for sm,L in itertools.product((4,13,26),(52,78,104)):
    D=comp(sm,L,scale)
    ths=np.percentile(D,[90,93,95,97,98,99])
    for th in ths:
      for r,mp in itertools.product((2,4,8,13),(26,52,78)):
        al=alerts(D,th,r,mp)
        hit={}; false_=0
        for a in al:
            m=mo(a); best=None
            for k in PK:
                if k in hit: continue
                e=md(m,pd.Timestamp(k+'-01'))
                if abs(e)<=2 and (best is None or abs(e)<abs(best[1])): best=(k,e)
            if best: hit[best[0]]=e
            else: false_+=1
        if len(hit)>=3:
            rows.append((len(hit),-false_,scale,sm,L,round(float(th),2),r,mp,false_,
                         {k:v for k,v in hit.items()}))
rows.sort(reverse=True)
print(f'{"hits":>4s} {"scale":>5s} {"sm":>3s} {"L":>4s} {"th":>8s} {"r":>3s} {"mp":>4s} {"false":>6s}  detail')
seen=set()
for b in rows[:18]:
    key=(b[2],b[3],b[4],b[6],b[7])
    print(f'{b[0]:2d}/4 {b[2]:>5s} {b[3]:3d} {b[4]:4d} {b[5]:8.2f} {b[6]:3d} {b[7]:4d} {b[8]:6d}  {b[9]}')
