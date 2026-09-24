"""Accuracy meter: monthly means of our weekly state prints against the Fieldhouse field (weekly average = monthly total / MonthtoWeekWeight)."""
import pandas as pd, numpy as np, glob, sys
R="/sessions/rcw-01xbsq1sgk1kphgfxvqjpnj7/mnt/Onset Detector Data/"
FH=np.exp(pd.read_csv(R+'24_bristow_rule_lab/workspace/lab/fh/FH_state_claims_nsa_log.csv',index_col=0,parse_dates=True))
d2=pd.read_stata(R+'24_bristow_rule_lab/workspace/lab/fh/src/CBUR Data.dta'); d2['Date']=pd.to_datetime(d2['Date']).dt.to_period('M').dt.to_timestamp()
wgt=d2.groupby('Date')['MonthtoWeekWeight'].first()
NAME2AB={'Alabama':'AL','Alaska':'AK','Arizona':'AZ','Arkansas':'AR','California':'CA','Colorado':'CO','Connecticut':'CT','Delaware':'DE','District of Columbia':'DC','Florida':'FL','Georgia':'GA','Hawaii':'HI','Idaho':'ID','Illinois':'IL','Indiana':'IN','Iowa':'IA','Kansas':'KS','Kentucky':'KY','Louisiana':'LA','Maine':'ME','Maryland':'MD','Massachusetts':'MA','Michigan':'MI','Minnesota':'MN','Mississippi':'MS','Missouri':'MO','Montana':'MT','Nebraska':'NE','Nevada':'NV','New Hampshire':'NH','New Jersey':'NJ','New Mexico':'NM','New York':'NY','North Carolina':'NC','North Dakota':'ND','Ohio':'OH','Oklahoma':'OK','Oregon':'OR','Pennsylvania':'PA','Rhode Island':'RI','South Carolina':'SC','South Dakota':'SD','Tennessee':'TN','Texas':'TX','Utah':'UT','Vermont':'VT','Virginia':'VA','Washington':'WA','West Virginia':'WV','Wisconsin':'WI','Wyoming':'WY'}
def fh(ch):
    X=FH[[c for c in FH.columns if c.endswith('| '+ch)]]; X.columns=[c.split(' |')[0] for c in X.columns]; return X.div(wgt.reindex(X.index),axis=0)
FIC,FCC=fh('initial claims'),fh('continued weeks claimed')
def score(df,valcol,field_ref,label):
    df=df.copy(); df['st']=df.state.map(NAME2AB); df=df.dropna(subset=['st']); df['m']=df.week.dt.to_period('M').dt.to_timestamp()
    m=df.groupby(['st','m'])[valcol].median().unstack(0)
    st=[s for s in m.columns if s in field_ref.columns]
    r=(np.log(m[st])-np.log(field_ref.reindex(m.index)[st]))
    s=r.stack().dropna()
    if not len(s): print(label,'no cells'); return
    yr=(r.abs()>0.3).sum(axis=1).groupby(r.index.year).sum().div(r.notna().sum(axis=1).groupby(r.index.year).sum()).round(2)
    print(f"{label:34} cells {len(s):6d} median {s.median():+.3f} |r|>0.1 {(s.abs()>0.1).mean():.2f} |r|>0.3 {(s.abs()>0.3).mean():.3f}  by year>0.3: {yr.dropna().to_dict()}")
if __name__=='__main__':
    E=pd.concat([pd.read_csv(f,parse_dates=['week']) for f in sorted(glob.glob('early_verified_v*.csv'))])
    E=E[(E.week>='1945-01-01')&(E.week<='1955-12-31')]
    for lay in ['L11','L9','E1953-IC','E1953-IU']:
        for tier in ['verified','partial']:
            for field,ref in [('ic',FIC),('cc',FCC)]:
                e=E[(E.layout==lay)&(E.tier==tier)&(E.field==field)]
                if len(e): score(e,'value',ref,f"{lay} {tier} {field}")
