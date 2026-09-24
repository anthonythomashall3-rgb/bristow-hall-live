"""The tool's claims field for the live machine (5 September 2026).

Finding that decides the construction: the Fieldhouse-Munro-Koch-Howard field (BPEA 2024) IS the Department's ETA 5159
monthly report from January 1971 on - initial claims = c1 and continued weeks claimed = c21 + c22 (intrastate plus
interstate liable) agree cell for cell (0.0 per cent of 1984-2023 state-months differ by more than one per cent),
except that Fieldhouse corrected the fifteen jurisdictions whose 5159 continued-weeks entries are understated in
1971-76 (they agree there with the Department's weekly release as first printed, collection 59).  Before 1971 the
Fieldhouse field is a transcription of the same weekly releases this programme has transcribed (own_panel/
OWN_state_claims_nsa_weeklyavg.csv agrees with it in 95 per cent of state-months within 0.2 log points).

So the field that runs the record AND the live tool is: Fieldhouse through January 2024 (its last month), the ETA 5159
monthly report from February 2024 on, no factor, no seam (same file, same columns).  Format identical to
lab/fh/FH_state_claims_nsa_log.csv (102 channels, log of monthly NSA totals); adjusted with build_rt.py's routine;
national NSA weekly averages for leg M (Fieldhouse totals / MonthtoWeekWeight; 5159 totals / (weekdays/5) after).
Set CLAIMS_FIELD=HYB to run the legs on it; unset, the frozen v9 reads Fieldhouse alone."""
import pandas as pd, numpy as np
R="/sessions/rcw-01xbsq1sgk1kphgfxvqjpnj7/mnt/Onset Detector Data/"; FH=R+"24_bristow_rule_lab/workspace/lab/fh/"; LAB=R+"24_bristow_rule_lab/workspace/lab/dol/"
def wk(m): return np.busday_count(m.date(),(m+pd.offsets.MonthEnd(0)+pd.Timedelta(days=1)).date())/5.0
fh=np.exp(pd.read_csv(FH+'FH_state_claims_nsa_log.csv',index_col=0,parse_dates=True))
d2=pd.read_stata(FH+'src/CBUR Data.dta'); d2['Date']=pd.to_datetime(d2['Date']).dt.to_period('M').dt.to_timestamp(); wgt=d2.groupby('Date')['MonthtoWeekWeight'].first()
d=pd.read_csv(LAB+'ar5159.csv',low_memory=False); d['m']=pd.to_datetime(d['rptdate'],errors='coerce').dt.to_period('M').dt.to_timestamp(); d=d.dropna(subset=['m'])
for c in ('c1','c21','c22'): d[c]=pd.to_numeric(d[c],errors='coerce')
d['cw']=d[['c21','c22']].sum(axis=1,min_count=1)
def piv(col): return d.dropna(subset=[col]).pivot_table(index='m',columns='st',values=col,aggfunc='sum').sort_index().where(lambda x:x>0)
log=[]; parts=[]; nat={}
LAST=fh.index.max()
for ch,col in (('initial claims','c1'),('continued weeks claimed','cw')):
    F=fh[[c for c in fh.columns if c.endswith('| '+ch)]]; F.columns=[c.split(' |')[0] for c in F.columns]
    A=piv(col).reindex(columns=F.columns)
    r=(np.log(F)-np.log(A)).loc['1977-01':LAST]; s=r.stack()
    log.append(f"{ch}: Fieldhouse vs ETA 5159 ({col}) 1977-01..{LAST:%Y-%m}: cells differing >1%: {(s.abs()>0.01).mean()*100:.2f}%, >5%: {(s.abs()>0.05).mean()*100:.2f}% of {len(s)}")
    H=pd.concat([F,A.loc[LAST+pd.DateOffset(months=1):]]); parts.append(H.add_suffix(' | '+ch))
    nat[ch]=pd.concat([(F.sum(axis=1)/wgt.reindex(F.index)), (A.sum(axis=1)/pd.Series([wk(m) for m in A.index],index=A.index)).loc[LAST+pd.DateOffset(months=1):]])
HYB=pd.concat(parts,axis=1).where(lambda x:x>0)
np.log(HYB).to_csv(FH+'HYB_state_claims_nsa_log.csv'); pd.DataFrame(nat).to_csv(FH+'HYB_national_nsa_weeklyavg.csv')
G={}; exec(open(FH+'build_rt.py').read().split("L=pd.read_csv(")[0],G); sa_realtime=G['sa_realtime']
parts=[]; nats={}
for ch in ('initial claims','continued weeks claimed'):
    cols=[c for c in HYB.columns if c.endswith('| '+ch)]
    parts.append(sa_realtime(HYB[cols])); nats[ch]=np.exp(sa_realtime(pd.DataFrame({'US':HYB[cols].sum(axis=1)}))['US'])
PAN=pd.concat(parts,axis=1); PAN.to_csv(FH+'HYB_state_claims_sa_rt_log.csv'); pd.DataFrame(nats).to_csv(FH+'HYB_nat_sa_rt.csv')
old=pd.read_csv(FH+'FH_state_claims_sa_rt_log.csv',index_col=0,parse_dates=True)
diff=(PAN.reindex(old.index)[old.columns]-old).abs().max().max()
log.append(f"HYB field {HYB.shape} {HYB.index.min().date()}..{HYB.index.max().date()}; adjusted values through {LAST:%Y-%m} differ from the frozen Fieldhouse file by at most {diff:.2e} (the factors of 2024 now see a full year)")
print('\n'.join(log)); open('HYBRID_BUILD_LOG.txt','w').write('\n'.join(log)+'\n')
