import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
M=pd.read_csv('/home/claude/lab/dol/US_state_claims_monthly_sa_rt.csv',index_col=0,parse_dates=True)
def breadth(P,sm,L,gap):
    K=P.rolling(sm).mean()*100.0
    S=K-K.rolling(L,min_periods=L//2).min()
    return ((S>=gap).sum(axis=1)/S.notna().sum(axis=1)*100.0).dropna()
for L,gap in [(12,15.),(12,25.),(15,15.),(18,20.),(9,10.),(9,15.)]:
    BD=breadth(M,2,L,gap)
    print(f'=== L={L} gap={gap}')
    for lo,hi in [('1980-06','1982-06'),('2023-06','2025-06')]:
        s=BD[lo:hi]
        for y,g in s.groupby(s.index.year):
            print(f'   {y}',' '.join(f'{v:5.1f}' for v in g.values))
        print('   --')
