"""Legs A, M, J, H rebuilt on the programme's OWN state claims field (5 September 2026) and set beside the
Fieldhouse-based legs the frozen route v9 runs.  The own field: 59_dol_weekly_state_claims_1945-1983_2026-09/
own_panel/OWN_state_claims_nsa_weeklyavg.csv (the weekly release as first printed 1945-83, ETA 5159 and ETA 539
after), 51 jurisdictions x 2 fields, 1946-06 to date.  Same seasonal routine (lab/fh/build_rt.py sa_realtime:
month-of-year medians, moving seven-year window, refitted each December), same objects, same lines - nothing
re-chosen: A = claims_diffusion 36/8 on two-month means, diffusion_peak_calls phase_min 5, published the 20th of
the month after; M = claims_conjunct(weeks=12, smooth=1) at 0.20, quiet 6, published the 10th; J, H =
level_trough_calls on the national adjusted series, drop 5.0 / 8.0 (the v9 'safe' setting) and defaults."""
import shim, sys, io, contextlib, numpy as np, pandas as pd, warnings; warnings.filterwarnings('ignore')
W=shim.W
sys.path.insert(0,W+'/lab/fh')
src=open('/home/claude/lab/fh/build_rt.py').read().split("L=pd.read_csv(")[0]
G={}; exec(src,G); sa_realtime=G['sa_realtime']
import bristow_rule_v3 as B
OWN="/sessions/rcw-01xbsq1sgk1kphgfxvqjpnj7/mnt/Onset Detector Data/59_dol_weekly_state_claims_1945-1983_2026-09/own_panel/"
P=pd.read_csv(OWN+'OWN_state_claims_nsa_weeklyavg.csv',index_col=0,parse_dates=True)
N=pd.read_csv(OWN+'OWN_national_claims_nsa_weeklyavg.csv',index_col=0,parse_dates=True)
import os
if not os.path.exists(OWN+'OWN_state_claims_sa_rt_log.csv'):
    parts=[]; nats={}
    for ch in ('initial claims','continued weeks claimed'):
        cols=[c for c in P.columns if c.endswith('| '+ch)]
        parts.append(sa_realtime(P[cols]))
        nats[ch]=np.exp(sa_realtime(pd.DataFrame({'US':N[ch]}).dropna())['US'])
    PAN=pd.concat(parts,axis=1); PAN.to_csv(OWN+'OWN_state_claims_sa_rt_log.csv'); pd.DataFrame(nats).to_csv(OWN+'OWN_nat_sa_rt.csv')
PAN=pd.read_csv(OWN+'OWN_state_claims_sa_rt_log.csv',index_col=0,parse_dates=True); NAT=pd.read_csv(OWN+'OWN_nat_sa_rt.csv',index_col=0,parse_dates=True)
PK=[pd.Timestamp(x) for x in ('1948-11','1953-07','1957-08','1960-04','1969-12','1973-11','1980-01','1981-07','1990-07','2001-03','2007-12','2020-02')]
TR=[pd.Timestamp(x) for x in ('1949-10','1954-05','1958-04','1961-02','1970-11','1975-03','1980-07','1982-11','1991-03','2001-11','2009-06','2020-04')]
def pub10(m): return pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=9)
RECORD_START=pd.Timestamp('1949-01-01')
# --- own legs
X=PAN.rolling(2).mean().dropna(how='all'); D=B.claims_diffusion(X,36.,8)
A_own=[(pd.Timestamp(p.year,p.month,20),d) for p,d in B.diffusion_peak_calls(D,phase_min=5)]
F_own=[(pd.Timestamp(p.year,p.month,20),d) for p,d in B.diffusion_trough_calls(D)]
ic=N['initial claims'].dropna(); cc=N['continued weeks claimed'].dropna()
c=B.claims_conjunct(ic,cc,weeks=12,smooth=1)
M_own=[(pub10(p-pd.Timedelta(days=7)),None) for p in B.conjunct_peak_calls(c,line=0.20,quiet_weeks=6,publication_days=7)]
def JH(s,drop):
    out=[(pub10(p-pd.DateOffset(months=1)),d) for p,d in B.level_trough_calls(s,drop=drop)]
    return [x for x in out if x[0]>=RECORD_START]
J_own=JH(np.log(NAT['continued weeks claimed'].dropna()),5.0); H_own=JH(np.log(NAT['initial claims'].dropna()),8.0)
J_own1=JH(np.log(NAT['continued weeks claimed'].dropna()),1.0); H_own1=JH(np.log(NAT['initial claims'].dropna()),1.0)
# --- Fieldhouse legs (the route's)
sys.path.insert(0,W+'/lab/weekly'); sys.path.insert(0,W+'/lab')
import union_peaks as U, legs_1948 as L
with contextlib.redirect_stdout(io.StringIO()):
    A_fh=U.leg_A(); M_fh=L.leg_M(0.20)
    nat=L._nat_rt(); icm=np.log(nat['initial claims'].dropna()); ccm=np.log(nat['continued weeks claimed'].dropna())
    J_fh=[(pub10(p-pd.DateOffset(months=1)),d) for p,d in B.level_trough_calls(ccm,drop=5.0)]; J_fh=[x for x in J_fh if x[0]>=RECORD_START]
    H_fh=[(pub10(p-pd.DateOffset(months=1)),d) for p,d in B.level_trough_calls(icm,drop=8.0)]; H_fh=[x for x in H_fh if x[0]>=RECORD_START]
    J_fh1=L.leg_J(); H_fh1=L.leg_H()
    Pn=pd.read_csv('/home/claude/lab/fh/FH_state_claims_sa_rt_log.csv',index_col=0,parse_dates=True)
    Df=B.claims_diffusion(Pn.rolling(2).mean().dropna(how='all'),36.,8); F_fh=[(pd.Timestamp(p.year,p.month,20),d) for p,d in B.diffusion_trough_calls(Df)]
def show(nm,calls,turns,kind):
    calls=[(p,d) for p,d in calls if p>=pd.Timestamp('1948-06-01')]
    print(f"\n{nm}: {len(calls)} calls")
    for p,d in calls:
        near=[t for t in turns if abs((t-(d if d is not None else p)).days)<=270]
        tag=f"{kind} {near[0]:%Y-%m}" if near else 'OTHER'
        lag=f"{(p-(near[0]+pd.offsets.MonthEnd(0))).days:+5d}d" if near else '     '
        print(f"   pub {p:%Y-%m-%d} dated {(d.strftime('%Y-%m') if d is not None else '  --  ')}  {tag} {lag}")
out=io.StringIO()
with contextlib.redirect_stdout(out):
    print(f"own field {PAN.shape} {PAN.index.min().date()}..{PAN.index.max().date()} | Fieldhouse {Pn.shape} {Pn.index.min().date()}..{Pn.index.max().date()}")
    show('A own (diffusion 36/8, phase 5)',A_own,PK,'peak'); show('A Fieldhouse',A_fh,PK,'peak')
    show('M own (conjunct 0.20)',M_own,PK,'peak'); show('M Fieldhouse',M_fh,PK,'peak')
    show('J own (drop 5)',J_own,TR,'trough'); show('J Fieldhouse (drop 5)',J_fh,TR,'trough')
    show('H own (drop 8)',H_own,TR,'trough'); show('H Fieldhouse (drop 8)',H_fh,TR,'trough')
    show('F own (diffusion trough clause)',F_own,TR,'trough'); show('F Fieldhouse',F_fh,TR,'trough')
    show('J own (drop 1, default)',J_own1,TR,'trough'); show('J Fieldhouse (drop 1)',J_fh1,TR,'trough')
    show('H own (drop 1, default)',H_own1,TR,'trough'); show('H Fieldhouse (drop 1)',H_fh1,TR,'trough')
txt=out.getvalue(); print(txt); open('OWN_PANEL_LEGS_2026-09-05.txt','w').write(txt)
