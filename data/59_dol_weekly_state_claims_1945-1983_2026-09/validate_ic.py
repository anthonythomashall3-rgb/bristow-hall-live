"""Validate the reconciled weekly state initial claims (1945-83) against (a) ETA 5159 monthly state initial claims, 1971-83,
and (b) the Department's national weekly initial claims, 1967-83."""
import pandas as pd, numpy as np, os
ODD=os.path.expanduser('~/mnt/Onset Detector Data')
W=pd.read_csv('ic_weekly_state_1945_1983_wide.csv',index_col=0,parse_dates=True)
ST={'Alabama':'AL','Alaska':'AK','Arizona':'AZ','Arkansas':'AR','California':'CA','Colorado':'CO','Connecticut':'CT','Delaware':'DE','District of Columbia':'DC','Florida':'FL','Georgia':'GA','Hawaii':'HI','Idaho':'ID','Illinois':'IL','Indiana':'IN','Iowa':'IA','Kansas':'KS','Kentucky':'KY','Louisiana':'LA','Maine':'ME','Maryland':'MD','Massachusetts':'MA','Michigan':'MI','Minnesota':'MN','Mississippi':'MS','Missouri':'MO','Montana':'MT','Nebraska':'NE','Nevada':'NV','New Hampshire':'NH','New Jersey':'NJ','New Mexico':'NM','New York':'NY','North Carolina':'NC','North Dakota':'ND','Ohio':'OH','Oklahoma':'OK','Oregon':'OR','Pennsylvania':'PA','Puerto Rico':'PR','Rhode Island':'RI','South Carolina':'SC','South Dakota':'SD','Tennessee':'TN','Texas':'TX','Utah':'UT','Vermont':'VT','Virginia':'VA','Virgin Islands':'VI','Washington':'WA','West Virginia':'WV','Wisconsin':'WI','Wyoming':'WY'}
W.columns=[ST.get(c,c) for c in W.columns]
P=pd.read_csv(f'{ODD}/37_dol_eta5159_2026-09/panel/panel_5159_monthly.csv',parse_dates=['month'])
# (a) monthly: sum the weeks whose Saturday falls in the month, only months with all weeks present for that state
Wm=W.copy(); Wm['m']=Wm.index.to_period('M')
cnt=Wm.groupby('m').apply(lambda g: g.drop(columns='m').notna().sum())
nweeks=Wm.groupby('m').size()
S=Wm.groupby('m').sum(min_count=1)
full=cnt.eq(nweeks,axis=0)
S=S.where(full)
S.index=S.index.to_timestamp()
M=P.pivot_table(index='month',columns='st',values='ic_total')
common=[c for c in S.columns if c in M.columns]
rat=[]; 
for c in common:
    a=S[c].dropna(); b=M[c].reindex(a.index)
    ok=a.notna()&b.notna()&(b>0)
    if ok.sum()>=6:
        r=(a[ok]/b[ok]); rat.append((c,int(ok.sum()),round(float(r.median()),3),round(float(np.corrcoef(np.log(a[ok]),np.log(b[ok]))[0,1]),3),round(float((abs(r-1)<=0.15).mean()*100),0)))
R=pd.DataFrame(rat,columns=['state','months','median_ratio_weekly_sum_over_5159','corr_log','pct_within_15'])
print('(a) vs ETA 5159 monthly, 1971-83:',len(R),'states;','median of state median ratios',R.median_ratio_weekly_sum_over_5159.median(),'| median corr',R.corr_log.median(),'| median % within 15%',R.pct_within_15.median())
print(R.sort_values('corr_log').head(6).to_string(index=False)); print(R.sort_values('corr_log').tail(3).to_string(index=False))
# (b) national weekly
N=pd.read_csv(f'{ODD}/24_bristow_rule_lab/workspace/lab/weekly/DOL_national_weekly_claims_1967.csv',index_col=0,parse_dates=True)
col=[c for c in N.columns if 'initial' in c.lower() and ('nsa' in c.lower() or 'ns' in c.lower() or 'nsa' in c.lower())] or [c for c in N.columns if 'initial' in c.lower()]
n=N[col[0]].dropna(); print('(b) national column used:',col[0],n.index[0].date(),'->',n.index[-1].date())
cov=W.notna().sum(axis=1); full=W[cov>=52].sum(axis=1)
j=pd.concat([full.rename('states_sum'),n.rename('national')],axis=1).dropna(); j=j[(j.index>='1967-01-01')&(j.index<='1983-12-31')]
r=j.states_sum/j.national; print('   weeks with >=52 states and a national print:',len(j),'| ratio median',round(float(r.median()),3),'| 10-90th',round(float(r.quantile(.1)),3),round(float(r.quantile(.9)),3),'| corr log',round(float(np.corrcoef(np.log(j.states_sum),np.log(j.national))[0,1]),3))
