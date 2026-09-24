"""The OWN claims field in the tool's format (6 September 2026): the programme's own transcription of the Department's
weekly release 1945-83 (collection 59, with volumes 23 and 34:27-52 read from the page harvest), ETA 5159 and ETA 539
after, as 102 channels of log monthly NSA totals (weekly average x weekdays/5 - Fieldhouse's form), adjusted with
build_rt.py's routine, with the national weekly averages for leg M.  Written to lab/fh/OWN_* so that
CLAIMS_FIELD=OWN runs the frozen rule on a field transcribed independently of Fieldhouse's."""
import pandas as pd, numpy as np, sys
R="/sessions/rcw-01xbsq1sgk1kphgfxvqjpnj7/mnt/Onset Detector Data/"; FH=R+"24_bristow_rule_lab/workspace/lab/fh/"
def wk(m): return np.busday_count(m.date(),(m+pd.offsets.MonthEnd(0)+pd.Timedelta(days=1)).date())/5.0
P=pd.read_csv('OWN_state_claims_nsa_weeklyavg.csv',index_col=0,parse_dates=True)
N=pd.read_csv('OWN_national_claims_nsa_weeklyavg.csv',index_col=0,parse_dates=True)
w=pd.Series([wk(m) for m in P.index],index=P.index)
TOT=P.mul(w,axis=0).where(lambda x:x>0)
np.log(TOT).to_csv(FH+'OWN_state_claims_nsa_log.csv'); N.to_csv(FH+'OWN_national_nsa_weeklyavg.csv')
G={}; exec(open(FH+'build_rt.py').read().split("L=pd.read_csv(")[0],G); sa_realtime=G['sa_realtime']
parts=[]; nats={}
for ch in ('initial claims','continued weeks claimed'):
    cols=[c for c in TOT.columns if c.endswith('| '+ch)]
    parts.append(sa_realtime(TOT[cols])); nats[ch]=np.exp(sa_realtime(pd.DataFrame({'US':N[ch].dropna()}))['US'])
PAN=pd.concat(parts,axis=1); PAN.to_csv(FH+'OWN_state_claims_sa_rt_log.csv'); pd.DataFrame(nats).to_csv(FH+'OWN_nat_sa_rt.csv')
fh=pd.read_csv(FH+'FH_state_claims_nsa_log.csv',index_col=0,parse_dates=True)
d=(np.log(TOT).reindex(fh.index)[fh.columns]-fh).stack()
print(f"OWN field {TOT.shape} {TOT.index.min().date()}..{TOT.index.max().date()}; vs Fieldhouse 1946-12..2024-01: {len(d)} cells, within 0.2 log: {(d.abs()<=0.2).mean()*100:.1f}%, median {d.median():+.3f}")
for y in (1967,1968,1979):
    dy=d[d.index.get_level_values(0).year==y]; print(f"   {y}: within 0.2 log {(dy.abs()<=0.2).mean()*100:.1f}% of {len(dy)}")
