"""Fieldhouse, Munro, Koch & Howard (BPEA Spring 2024) state claims, 1946-12 to 2024-01:
build the 102-channel log panel (51 x initial, 51 x continued) in the tool's format."""
import pandas as pd, numpy as np
df=pd.read_stata("/home/claude/lab/fh/src/CBUR Data.dta")
df['Date']=pd.to_datetime(df['Date']).dt.to_period('M').dt.to_timestamp()
for basis,ic,cc in (('sa','IC_SA','CC_SA'),('nsa','IC_NSA','CC_NSA')):
    a=df.pivot(index='Date',columns='State',values=ic); b=df.pivot(index='Date',columns='State',values=cc)
    a.columns=[f'{s} | initial claims' for s in a.columns]; b.columns=[f'{s} | continued weeks claimed' for s in b.columns]
    P=pd.concat([a,b],axis=1).astype(float)
    P=P.where(P>0)
    np.log(P).to_csv(f'FH_state_claims_{basis}_log.csv')
    print(basis, P.shape, P.index.min().date(), P.index.max().date(), 'nan cells', int(P.isna().sum().sum()))
nat=df.groupby('Date')[['US_IC_SA','US_CC_SA','IC_CC_Week_US','USIUR','UR_Claims_US','USUR']].first()
nat.to_csv('FH_national.csv'); print(nat.dropna(subset=['US_IC_SA']).index.min().date(), nat.index.max().date())
# state payrolls too
for basis,col in (('sa','nonfarm_SA'),('nsa','nonfarm_NSA')):
    e=df.pivot(index='Date',columns='State',values=col).astype(float)
    e.to_csv(f'FH_state_payrolls_{basis}.csv'); print('payrolls',basis,e.shape,'nan',int(e.isna().sum().sum()), e.dropna(how='all').index.min().date())
