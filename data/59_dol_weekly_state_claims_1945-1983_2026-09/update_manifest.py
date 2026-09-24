"""Recompute the MANIFEST rows whose files changed (6 September 2026, sixth pass): true first/last observation dates,
n_obs and pct_repeated_values read off the values themselves, for every series drawn from the weekly-release panels,
the monthly means and the own field.  The HYB rows are untouched (that field does not use the release)."""
import pandas as pd, numpy as np, re
NAME2AB={'Alabama':'AL','Alaska':'AK','Arizona':'AZ','Arkansas':'AR','California':'CA','Colorado':'CO','Connecticut':'CT','Delaware':'DE','District of Columbia':'DC','Florida':'FL','Georgia':'GA','Hawaii':'HI','Idaho':'ID','Illinois':'IL','Indiana':'IN','Iowa':'IA','Kansas':'KS','Kentucky':'KY','Louisiana':'LA','Maine':'ME','Maryland':'MD','Massachusetts':'MA','Michigan':'MI','Minnesota':'MN','Mississippi':'MS','Missouri':'MO','Montana':'MT','Nebraska':'NE','Nevada':'NV','New Hampshire':'NH','New Jersey':'NJ','New Mexico':'NM','New York':'NY','North Carolina':'NC','North Dakota':'ND','Ohio':'OH','Oklahoma':'OK','Oregon':'OR','Pennsylvania':'PA','Puerto Rico':'PR','Rhode Island':'RI','South Carolina':'SC','South Dakota':'SD','Tennessee':'TN','Texas':'TX','Utah':'UT','Vermont':'VT','Virgin Islands':'VI','Virginia':'VA','Washington':'WA','West Virginia':'WV','Wisconsin':'WI','Wyoming':'WY'}
def stat(s):
    s=s.dropna()
    if not len(s): return None
    rep=float((s.diff()==0).mean()*100)
    return s.index.min(),s.index.max(),len(s),round(rep,1)
IC=pd.read_csv('ic_weekly_state_1945_1983_wide.csv',index_col=0,parse_dates=True)
IU=pd.read_csv('iu_weekly_state_1945_1983_wide.csv',index_col=0,parse_dates=True)
ICL=pd.read_csv('ic_weekly_state_1945_1983_long.csv',parse_dates=['week']); IUL=pd.read_csv('iu_weekly_state_1945_1983_long.csv',parse_dates=['week'])
WIC=pd.read_csv('weekly_ic_1945_1983.csv',index_col=0,parse_dates=True); WCC=pd.read_csv('weekly_cc_1945_1983.csv',index_col=0,parse_dates=True)
M=pd.read_csv('ic_monthly_state_1945_1983_from_weekly.csv',index_col=0,parse_dates=True)
OWN=pd.read_csv('own_panel/OWN_state_claims_nsa_weeklyavg.csv',index_col=0,parse_dates=True)
NAT=pd.read_csv('national_weekly_first_prints_1945_1983.csv',index_col=0,parse_dates=True)
IURrt=pd.read_csv('national_iur_realtime_sa_first_prints_1948_1983.csv',index_col=0,parse_dates=True).iloc[:,0]
m=pd.read_csv('MANIFEST.csv'); n=0
for i,r in m.iterrows():
    ser=str(r['series']); src=str(r['source']); s=None; note=None
    if src.startswith('US DOL weekly release') and 'reconciled by reconcile_ic.py' in src:
        st=ser.split(': ')[-1]; ab=NAME2AB.get(st)
        if ab in IC.columns:
            s=IC[ab]; sub=ICL[ICL.state==st]; note='sources: '+str(sub.source.value_counts().to_dict())
    elif src.startswith('US DOL weekly release') and 'reconcile_iu.py' in src:
        st=ser.split(': ')[-1]; ab=NAME2AB.get(st)
        if ab in IU.columns:
            s=IU[ab]; sub=IUL[IUL.state==st]; note='sources: '+str(sub.source.value_counts().to_dict())
    elif 'assembled by assemble_weekly.py' in src:
        ab=ser.split(': ')[-1]; D=WIC if 'initial claims' in ser else WCC
        if ab in D.columns: s=D[ab]
    elif src.startswith('monthly mean of the weekly release'):
        ab=ser.split(': ')[-1]
        if ab in M.columns: s=M[ab]
    elif src.startswith('Own monthly state claims field'):
        key=re.sub(r'\s*\(.*\)$','',ser).strip()
        if key in OWN.columns: s=OWN[key]
    elif 'the national Total row read by parse_national.py' in src:
        c='ic' if ser.startswith('national initial') else ('iu' if 'insured unemployment (continued' in ser else 'iur'); s=NAT[c]
    elif src.startswith('Derived: national insured unemployment'): s=IURrt
    if s is None: continue
    t=stat(s)
    if t is None: continue
    a,b,k,rep=t
    fmt='%Y-%m' if str(r['frequency'])=='M' else '%Y-%m-%d'
    m.at[i,'first_obs']=a.strftime(fmt); m.at[i,'last_obs']=b.strftime(fmt); m.at[i,'n_obs']=k; m.at[i,'pct_repeated_values']=rep
    if note: m.at[i,'note']=note
    n+=1
m.to_csv('MANIFEST.csv',index=False); print('rows refreshed',n,'of',len(m))
