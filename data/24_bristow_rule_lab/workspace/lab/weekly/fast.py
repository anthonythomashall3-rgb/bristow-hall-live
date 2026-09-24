"""Two stages, one rule.

STAGE 1, weekly: the composite deviation over the weekly panel crosses a threshold and
holds.  This is the alert - the claim that a turning point has happened.  Weekly data
is published within a week, so the alert is charged one week.

STAGE 2, monthly: at the moment of the alert, the same rule is run on the monthly panel
with only the data that existed then, and returns the date.  Monthly coincident series
appear one to two months after the month they cover, so the panel is truncated at
alert month minus two.

Reported: months from the official turning point to the alert (the LAG), and months
between the date given and the official date (the ERROR).
"""
import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import pandas as pd, numpy as np, itertools, warnings; warnings.filterwarnings('ignore')
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.ABSTAIN=True
W=pd.read_csv('/home/claude/lab/weekly/US_weekly_panel.csv',index_col=0,parse_dates=True)
SIGN={'initial claims':-1,'continued claims':-1,'petroleum products supplied':1,'withheld taxes':1}
MCH=[(nm,s) for nm,s in channels('United States') if nm not in bench.SKIP]
PK=['1990-07','2001-03','2007-12','2020-02']; TR=['1991-03','2001-11','2009-06','2020-04']
def mo(t): return pd.Timestamp(t.year,t.month,1)
def md(x,y): return (x.year-y.year)*12+(x.month-y.month)
def wcomp(sm,L):
    ch={c:(np.log(W[c])*SIGN[c]*100.0).rolling(sm).mean() for c in W.columns}
    cols=[]
    for c,v in ch.items():
        sd=(v.diff().abs().median() or 1.0)
        cols.append(((v.rolling(L,min_periods=L//2).max()-v)/sd).rename(c))
    return pd.concat(cols,axis=1,sort=True).mean(axis=1,skipna=True).dropna()
def alerts(D,th,r,mp):
    out=[]; last=-10**9; v=D.values; idx=D.index
    for i in range(r,len(v)):
        if i-last<mp: continue
        if all(v[j]>=th for j in range(i-r+1,i+1)):
            out.append(idx[i]+pd.Timedelta(days=7)); last=i
    return out
def date_at(asof, lag_months=2):
    cut=mo(asof)-pd.DateOffset(months=lag_months)
    use=[(nm,s[:cut]) for nm,s in MCH]
    use=[(nm,s) for nm,s in use if len(s.dropna())>60]
    if not use: return None,None
    w0=cut-pd.DateOffset(months=48)
    r=date_any('United States',use,w0,cut,band_t=0.12,band_p=0.01,n=3,L=12,peak_cap=18,
               min_depth=5.0,lam=500000.)
    return r['peak'],r['trough']
best=[]
for sm,L,th,r,mp in itertools.product((4,13),(52,78),(1.5,2.,3.,4.,6.),(2,4,6),(26,52)):
    D=wcomp(sm,L); al=alerts(D,th,r,mp)
    if not al or len(al)>25: continue
    best.append((len(al),sm,L,th,r,mp,al))
best.sort(key=lambda x:x[0])
print('alert counts (fewest first):')
for b in best[:8]:
    print(f'  sm={b[1]} L={b[2]} th={b[3]} r={b[4]} mp={b[5]}: {b[0]} alerts  '
          +', '.join(a.strftime('%Y-%m') for a in b[6][:12]))
