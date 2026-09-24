import sys; sys.path.insert(0,'/home/claude')
import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
M_SA=pd.read_csv('/home/claude/lab/dol/US_state_claims_monthly_sa_rt.csv',index_col=0,parse_dates=True)
def breadth(P,sm,L,gap):
    K=P.rolling(sm).mean()*100.0
    S=K-K.rolling(L,min_periods=L//2).min()
    return ((S>=gap).sum(axis=1)/S.notna().sum(axis=1)*100.0).dropna()
BD=breadth(M_SA,2,36,25.)
for lo,hi in [('1979-06','1983-06'),('2022-06','2026-08')]:
    s=BD[lo:hi]
    print(f'=== {lo}..{hi}')
    for y,g in s.groupby(s.index.year):
        print(' ',y,' '.join(f'{v:5.1f}' for v in g.values))
