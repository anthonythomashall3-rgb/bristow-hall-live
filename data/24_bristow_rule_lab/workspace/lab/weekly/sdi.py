"""The historical diffusion index across the states, weekly.

Each state's seasonally adjusted claims series is turned into its own expansion and
contraction phases by the same Bry-Boschan procedure the rule uses elsewhere, on the
negated log level so that the phases are phases of activity.  The index is the share of
states in expansion, in per cent - ESRI's object, built weekly across states instead of
monthly across indicators.
"""
import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import phase_series
import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
SA=pd.read_csv('/home/claude/lab/dol/US_state_claims_sa_log.csv',index_col=0,parse_dates=True)
cols=[]
for c in SA.columns:
    v=-SA[c]                      # negated log claims = state activity
    p=phase_series(v,13)
    if p is not None: cols.append(p.rename(c))
P=pd.concat(cols,axis=1,sort=True)
DI=(P.mean(axis=1,skipna=True)*100.0).where(P.notna().sum(axis=1)>=40).dropna()
DI.to_csv('/home/claude/lab/dol/US_state_hist_di.csv',header=['value'])
print('state historical DI:',DI.index.min().date(),DI.index.max().date(),len(DI))
m=DI.resample('MS').mean()
for a,b in (('1989-06','1992-06'),('2000-06','2002-06'),('2007-01','2010-06'),('2019-06','2021-06')):
    print(f'--- {a}..{b}')
    print('   '+'  '.join(f"{d.strftime('%y-%m')}:{v:.0f}" for d,v in m[a:b].items()))
