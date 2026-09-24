"""What does each weekly channel say on its own, given the episode window?
Retrospective, not real time: this measures whether the information is there at all."""
import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import ch_trough, ch_peak
import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
W=pd.read_csv('/home/claude/lab/weekly/US_weekly_panel.csv',index_col=0,parse_dates=True)
SIGN={'initial claims':-1,'continued claims':-1,'petroleum products supplied':1,'withheld taxes':1}
EP=[('1990-07','1991-03'),('2001-03','2001-11'),('2007-12','2009-06'),('2020-02','2020-04')]
def md(x,y): return (x.year-y.year)*12+(x.month-y.month)
for sm in (4,13):
  print(f'--- {sm}-week smoothing')
  for c in W.columns:
    v=(np.log(W[c])*SIGN[c]*100.0).rolling(sm).mean().dropna()
    row=[]
    for pk,tr in EP:
        w0=pd.Timestamp(pk)-pd.DateOffset(months=12); w1=pd.Timestamp(tr)+pd.DateOffset(months=12)
        if v.index.min()>w0 or v.index.max()<pd.Timestamp(tr): row.append('  --/--  '); continue
        T=ch_trough(v,w0,w1,0.12,1,52,abstain=False)
        P=ch_peak(v,w0,T if T is not None else w1,0.01,1,abstain=False)
        e1=md(P,pd.Timestamp(pk)) if P is not None else None
        e2=md(T,pd.Timestamp(tr)) if T is not None else None
        row.append(f'{str(e1):>4s}/{str(e2):<4s}')
    print(f'   {c:30s} '+'  '.join(row))
