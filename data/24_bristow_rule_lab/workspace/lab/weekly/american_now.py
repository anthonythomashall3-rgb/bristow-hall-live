"""The American route's standing today: every live object at its latest observation, and what the
route currently says (3 September 2026).  Run it on any day; it reads the files on disk and prints
where each object stands against its own line - no chronology, no confirmation stage, one call per
episode (AMERICAN_ROUTE, "one call, one date").

Objects and lines:
  A   monthly state claims diffusion index, the Department's file 1971 on (claims_diffusion 48/13 on
      initial and continued claims, the shipped monthly record; the Fieldhouse field carries the same
      index 1947-2024) - a downturn is open while the share stands at or above 50
  C   weekly state breadth (final_rt.breadth 13, 104, 25: share of states whose 13-week mean of
      claims stands 25 log points above its two-year low), line 50
  B   the national weekly claims conjunct (claims_conjunct on unadjusted initial and continued
      claims, four-week mean), line 0.20
  K/I the trough legs on weekly continued and initial claims (level_trough_calls' state: armed when
      the four-week mean stands 30 / 40 log points above its 52-week minimum)
  Sahm's gap on the unemployment rate (line 0.5) and the vacancy rate's fall (line 0.6) - the second objects of the default route (version 37)
  the panel's composite D (median drawdown of the seven activity series, per cent; the level clause
      opens at 2.0)
Output american_now.log.
"""
import sys, warnings; warnings.filterwarnings('ignore')
sys.path.insert(0,'/home/claude'); sys.path.insert(0,'/home/claude/lab'); sys.path.insert(0,'/home/claude/lab/weekly'); sys.argv=['x']
import numpy as np, pandas as pd, bristow_rule_v3 as B
PAN=pd.read_csv('/home/claude/lab/dol/US_state_monthly_4ch_sa.csv',index_col=0,parse_dates=True)
cols=[c for c in PAN.columns if c.endswith('| initial claims') or c.endswith('| continued weeks claimed')]
A=B.claims_diffusion(PAN[cols],48.,13)
pk=B.diffusion_peak_calls(A,phase_min=5); tr=B.diffusion_trough_calls(A)
SA=pd.read_csv('/home/claude/lab/dol/US_state_claims_sa_rt.csv',index_col=0,parse_dates=True)
K13=SA.rolling(13).mean()*100.0; S=K13-K13.rolling(104,min_periods=52).min(); C=((S>=25).sum(axis=1)/S.notna().sum(axis=1)*100.0).dropna()
W=pd.read_csv('/home/claude/lab/weekly/US_weekly_panel.csv',index_col=0,parse_dates=True)
conj=B.claims_conjunct(W['initial claims'].dropna(),W['continued claims'].dropna())
N=pd.read_csv('/home/claude/lab/weekly/DOL_national_weekly_claims_sa_rt.csv',index_col=0,parse_dates=True)
def gap(col,sm=4):
    n=(np.log(N[col])*100.0).rolling(sm).mean(); return (n-n.rolling(52,min_periods=26).min()).dropna()
gK=gap('cc_sa_rt',4); gI=gap('ic_sa_rt',8)
import bench
from bench import channels
bench.SKIP={'exports','imports','car registrations','unemployment','construction production','construction output','capital goods production','intermediate goods production','consumer durables production'}
chs=[(nm,s) for nm,s in channels('United States') if nm not in bench.SKIP]
comp=B.composite_deviation(chs,12,3,2).dropna()
u=pd.read_csv('/home/claude/lab/cps/01_labor_unemployment/monthly/UNRATE.csv')   # the Mac's copy (01_labor_unemployment), to July 2026
u.columns=['date','v']; u['date']=pd.to_datetime(u['date']); u=u.set_index('date')['v'].astype(float)
sg=B.sahm_gap(u)
print(f'read on {pd.Timestamp.today():%Y-%m-%d}')
print(f'A  monthly state claims diffusion index: latest {A.index.max():%Y-%m} = {A.iloc[-1]:.0f} per cent (line 50); last twelve: {[int(round(v)) for v in A.iloc[-12:]]}')
print(f'   peak calls since 2015: {[(p.strftime("%Y-%m"),d.strftime("%Y-%m")) for p,d in pk if p>=pd.Timestamp("2015-01-01")]}; trough calls since 2015: {[(p.strftime("%Y-%m"),d.strftime("%Y-%m")) for p,d in tr if p>=pd.Timestamp("2015-01-01")]}')
print(f'C  weekly state breadth: latest {C.index.max():%Y-%m-%d} = {C.iloc[-1]:.0f} per cent (line 50); monthly maxima, last twelve months: {[float(x) for x in C.resample("ME").max().iloc[-12:].round(0)]}')
print(f'B  national claims conjunct: latest {conj.index.max():%Y-%m-%d} = {conj.iloc[-1]:+.3f} log points (line +0.20); 52-week maximum {conj.iloc[-52:].max():+.3f}')
print(f'K  continued claims, four-week mean above its 52-week low: {gK.iloc[-1]:.1f} log points (arms at 30); I initial claims, eight-week mean: {gI.iloc[-1]:.1f} (arms at 40); latest week {N.index.max():%Y-%m-%d}')
print(f"Sahm's gap (route B's second object): latest {sg.index.max():%Y-%m} = {sg.iloc[-1]:+.2f} points (line 0.5); maximum since 2023 {sg['2023':].max():.2f} in {sg['2023':].idxmax():%Y-%m}")
import american_chronology as AC
vg=AC.vacancy_gap_rt(2,6); print(f"the vacancy rate's fall, fast form (the second object beside the rate; two-month mean below its six-month maximum; line 0.36): latest {vg.index.max():%Y-%m} = {vg.iloc[-1]:+.2f} points; maximum since 2022 {vg['2022':].max():.2f} in {vg['2022':].idxmax():%Y-%m}")
print(f'panel composite D: latest {comp.index.max():%Y-%m} = {comp.iloc[-1]:+.2f} per cent (the level clause opens at 2.0); maximum since 2022 {comp["2022":].max():.2f} in {comp["2022":].idxmax():%Y-%m}')
PL,TL=AC.legs(safe=True, with_S=True); turns=B.american_chronology(PL,TL,sahm=AC.sahm_rt(),second=[dict(name='vacancy(2,6)',gap=AC.vacancy_gap_rt(2,6),line=0.36,pub_day=30)])   # the default from version 39: the rate OR the vacancy rate's fast form, first prints; leg S (Paper 1's end) gated by the claims field's arming
last=turns[-1]; prev=turns[-2]
state='open' if last['kind']=='peak' else 'closed'
print(f"\nthe route's standing (the default: claims objects AND (Sahm's gap at 0.5 OR the vacancy rate's fast form at 0.36), one call one date; ends by the claims legs, or by Paper 1's Sahm-maximum rule where the claims field never armed): the last onset was called {prev['published'] if prev['kind']=='peak' else last['published']:%-d %B %Y} by leg {(prev if prev['kind']=='peak' else last)['leg']}, dated {(prev if prev['kind']=='peak' else last)['date']:%B %Y};"
      f" the last end was called {(last if last['kind']=='trough' else prev)['published']:%-d %B %Y} by leg {(last if last['kind']=='trough' else prev)['leg']}, dated {(last if last['kind']=='trough' else prev)['date']:%B %Y}; the downturn is {state}."
      f" No object is at its line today: A {A.iloc[-1]:.0f}, C {C.iloc[-1]:.0f}, B {conj.iloc[-1]:+.2f}, Sahm {sg.iloc[-1]:+.2f}, composite D {comp.iloc[-1]:+.2f}.")
