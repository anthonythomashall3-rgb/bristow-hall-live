import sys; sys.path.insert(0,'/home/claude'); sys.path.insert(0,'/home/claude/lab/fh')
import bristow_rule_v3 as B, pandas as pd, numpy as np, warnings, itertools; warnings.filterwarnings('ignore')
from test1 import PK, TR
from grid_fh import score_q
nat=pd.read_csv('FH_nat_sa_rt.csv',index_col=0,parse_dates=True)
res=[]
for col in nat.columns:
    s=np.log(nat[col].dropna())
    for sm,lb,arm,drop,run in itertools.product((1,2,3),(18,24,30,36),(30,40,50,60),(0.5,1.0,2.0),(1,2)):
        calls=B.level_trough_calls(s,smooth=sm,lookback=lb,run=run,drop=drop,arm_gap=arm)
        h,ex,w1,oth,rows,other=score_q(calls,TR)
        lag=[r[1] for r in rows if r is not None]
        res.append((col[:4],sm,lb,arm,drop,run,h,ex,w1,oth,max(lag) if lag else None,[None if r is None else r[0] for r in rows]))
res.sort(key=lambda r:(-r[6],r[9],-r[7],-r[8]))
for r in res[:20]: print(r)
# Paper 1's rule on the claims-based unemployment rate (Fieldhouse national CBUR)
fh=pd.read_csv('FH_national.csv',index_col=0,parse_dates=True)
def sahm_calls(u, arm=0.5, confirm=1):
    m3=u.rolling(3).mean(); s=(m3-m3.shift(1).rolling(12).min()).dropna()
    calls=[]; state='quiet'; pk=None; pv=None
    for t,v in s.items():
        if state=='quiet':
            if v>=arm: state='armed'; pk=t; pv=v
        elif state=='armed':
            if v>pv: pk=t; pv=v; continue
            if v<pv: calls.append((t+pd.DateOffset(months=1),pk)); state='called'
        else:
            if v<arm: state='quiet'
    return calls
for col in ('UR_Claims_US3MA','UR_Claims_US','USIUR','USUR'):
    u=fh[col].dropna()
    for arm in (0.3,0.5,0.8):
        calls=sahm_calls(u,arm)
        h,ex,w1,oth,rows,other=score_q(calls,TR)
        print(f'Sahm-max on {col:16s} arm {arm}: {h}/12 exact {ex} within1 {w1} other {oth}', [None if r is None else r[0] for r in rows], [(p.strftime("%Y-%m"),d.strftime("%Y-%m")) for p,d in other][:6])
