exec(open('minimise.py').read().split('print("PEAK-LEG SUBSETS')[0])
import pickle, pandas as pd, numpy as np, sys
W=shim.W
out=dict(sahm=g, vac=vr, PL=PL, TLG=TLG, arm=arm, PK=PK, TR=TR)
# leg U as frozen in v8 (re-arm when gap closes)
s=pd.read_csv(W+'/archive/data/fred/IURSA.csv'); s.columns=['d','v']; s['d']=pd.to_datetime(s['d']); s=s.set_index('d')['v'].astype(float).dropna()
out['iursa']=s
def leg_U2(line=0.50,smooth=1,look=52,pub=5):
    x=s.rolling(smooth).mean(); gap=x-x.rolling(look,min_periods=look).min().shift(1)
    c=[]; armed=True
    for t,v in gap.dropna().items():
        if armed and v>=line: c.append((t+pd.Timedelta(days=pub),pd.Timestamp(t.year,t.month,1))); armed=False
        elif not armed and v<=0.0: armed=True
    return c
out['PL']['U']=leg_U2()
out['nat67']=pd.read_csv(W+'/lab/weekly/DOL_national_weekly_claims_1967.csv',index_col=0,parse_dates=True)
out['nat_sa_rt']=pd.read_csv(W+'/lab/weekly/DOL_national_weekly_claims_sa_rt.csv',index_col=0,parse_dates=True)
out['state_sa_rt']=pd.read_csv(W+'/lab/dol/US_state_claims_sa_rt.csv',index_col=0,parse_dates=True)
out['fh_nat']=pd.read_csv(W+'/lab/fh/FH_nat_sa_rt.csv',index_col=0,parse_dates=True)
# unemployment rate first prints & current
import alfred
out['unrate_fp']=alfred.first_prints('UNRATE')
cur=pd.read_csv(W+'/archive/data/fred/UNRATE.csv'); cur.columns=['d','v']; cur['d']=pd.to_datetime(cur['d']); out['unrate_cur']=cur.set_index('d')['v'].astype(float)
out['sahm_cur']=B.sahm_gap(out['unrate_cur'])
# Sahm end calls (Paper 1 Bristow rule) gated and ungated
out['S_gated']=TLG['S']; out['S_ungated']=leg_S(g)
# the american_chronology function is needed later: keep the source path
pickle.dump(out,open('cache/objects.pkl','wb'))
print('cached:',{k:(type(v).__name__) for k,v in out.items()})
print('sahm fp span',g.index.min(),g.index.max(),' vac span',vr.index.min(),vr.index.max())
print('legs:',{k:len(v) for k,v in out['PL'].items()},{k:len(v) for k,v in TLG.items()})
