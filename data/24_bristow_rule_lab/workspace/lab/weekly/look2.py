import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
NCM=pd.read_csv('/home/claude/lab/dol/US_nat_claims_monthly_rt.csv',index_col=0,parse_dates=True)
print(NCM.columns.tolist(), NCM.index.min(), NCM.index.max())
N=np.log(NCM.iloc[:,0])*100.0
for lo,hi in [('1979-06','1983-06'),('2022-01','2026-08')]:
    s=N[lo:hi]
    print(f'=== national claims, log x100, {lo}..{hi}')
    for y,g in s.groupby(s.index.year):
        print(' ',y,' '.join(f'{v:6.1f}' for v in g.values))
