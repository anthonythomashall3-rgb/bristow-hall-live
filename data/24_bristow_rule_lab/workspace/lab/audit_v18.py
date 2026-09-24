"""Every number added in version 18, re-derived from the data and checked against the memo."""
import sys; sys.path.insert(0,'/home/claude'); sys.path.insert(0,'/home/claude/lab')
import bristow_rule_v3 as B, pandas as pd, numpy as np, re, warnings; warnings.filterwarnings('ignore')
M=open('/home/claude/Paper1.5_Bristow_Rule_Evidence_Memo.md').read()
ok=bad=0
def chk(label,cond,detail=''):
    global ok,bad
    if cond: ok+=1; print(f'  OK   {label}')
    else: bad+=1; print(f'  FAIL {label}   {detail}')
print('=== 1. residual seasonality figures')
d=pd.read_csv('/home/claude/lab/dol/ar5159.csv',low_memory=False)
d['dt']=pd.to_datetime(d['rptdate'],errors='coerce'); d['ic']=pd.to_numeric(d['c1'],errors='coerce')
d=d.dropna(subset=['dt','ic']); d['m']=d['dt'].dt.to_period('M').dt.to_timestamp()
P=d.pivot_table(index='m',columns='st',values='ic',aggfunc='sum').sort_index()
P=P.loc[:,P.notna().mean()>0.9].reindex(pd.date_range('1971-01-01','2026-07-01',freq='MS')).interpolate()
def mf(X,med=True):
    R=X-X.rolling(13,center=True,min_periods=7).mean(); pooled={}
    for mth in range(1,13):
        v=R[R.index.month==mth].values; v=v[~np.isnan(v)]
        if len(v): pooled[mth]=float(np.median(v) if med else np.mean(v))
    mu=np.median(list(pooled.values())); return {k:v-mu for k,v in pooled.items()}
def sa(P,win=None):
    X=np.log(P.replace(0,np.nan)).interpolate().bfill(); out=X.copy()*np.nan
    for y in sorted(set(X.index.year)):
        h=X[X.index.year<y]
        if win: h=h[h.index.year>=y-win]
        if len(h)<24: out.loc[X.index.year==y]=X.loc[X.index.year==y]; continue
        f=mf(h); m=X.index.year==y
        for c in X.columns:
            out.loc[m,c]=X.loc[m,c].values-np.array([f.get(t.month,0.) for t in X.index[m]])
    return out
def resid(X,lo,hi):
    s=X[lo:hi]; r=(s-s.rolling(13,center=True,min_periods=7).mean()).dropna()
    f=r.groupby(r.index.month).median(); return float(f.max()-f.min())
nat=pd.DataFrame({'US':P.sum(axis=1)})
old=sa(nat)['US']*100; new=sa(nat,7)['US']*100
r_old=(resid(old,'1973-01','2026-07'),resid(old,'1973-01','1990-12'),resid(old,'2015-01','2026-07'))
r_new=(resid(new,'1973-01','2026-07'),resid(new,'1973-01','1990-12'),resid(new,'2015-01','2026-07'))
print(f'   whole-history factors: whole {r_old[0]:.1f}  1973-90 {r_old[1]:.1f}  2015-26 {r_old[2]:.1f}')
print(f'   seven-year window    : whole {r_new[0]:.1f}  1973-90 {r_new[1]:.1f}  2015-26 {r_new[2]:.1f}')
chk('memo says 10.4 whole', abs(r_old[0]-10.4)<0.05 and '10.4 log points' in M)
chk('memo says 18.8 recent', abs(r_old[2]-18.8)<0.05 and '18.8 over 2015' in M)
chk('memo says 7.0 early',   abs(r_old[1]-7.0)<0.05 and '7.0 over 1973' in M)
chk('memo says 4.5 whole after', abs(r_new[0]-4.5)<0.05 and '4.5 log points' in M)
chk('memo says 6.9 recent after', abs(r_new[2]-6.9)<0.05 and '6.9 over 2015' in M)
print('=== 2. the ETA 539 field identification')
w=pd.read_csv('/home/claude/lab/dol/ar539.csv',low_memory=False)
for c in ('c3','c7','c8'): w[c]=pd.to_numeric(w[c],errors='coerce')
w['wk']=pd.to_datetime(w['c2'],errors='coerce'); w=w.dropna(subset=['wk'])
g=w.groupby('wk')[['c3','c7','c8']].sum()
print(f"   national totals, week of 2020-04-04: IC(c3) {g.loc['2020-04-04','c3']:,.0f}  "
      f"c7 {g.loc['2020-04-04','c7']:,.0f}  CW(c8) {g.loc['2020-04-04','c8']:,.0f}")
chk('c8 is the large continued-claims series', g.loc['2020-04-04','c8']>10e6)
chk('c7 is near zero', g['c7'].median()<g['c8'].median()/50)
print('=== 3. the record itself')
PAN=pd.read_csv('/home/claude/lab/dol/US_state_monthly_4ch_sa.csv',index_col=0,parse_dates=True)
NAT=pd.read_csv('/home/claude/lab/dol/US_nat_monthly_4ch_sa.csv',index_col=0,parse_dates=True)
cols=[c for c in PAN.columns if c.endswith('| initial claims') or c.endswith('| continued weeks claimed')]
D=B.claims_diffusion(PAN[cols],48.,13)
pk=B.diffusion_peak_calls(D); tr=B.level_trough_calls(np.log(NAT['initial claims']))
want_p=[('1973-12','1973-10'),('1980-02','1979-12'),('1990-09','1990-07'),('2001-05','2001-03'),
        ('2008-08','2008-06'),('2020-04','2020-02'),('2023-08','2023-06')]
want_t=[('1975-04','1975-01'),('1980-08','1980-06'),('1991-05','1991-03'),('2002-01','2001-11'),
        ('2009-06','2009-04'),('2020-06','2020-04')]
got_p=[(p.strftime('%Y-%m'),d.strftime('%Y-%m')) for p,d in pk]
got_t=[(p.strftime('%Y-%m'),d.strftime('%Y-%m')) for p,d in tr]
chk('seven peak calls, exactly as tabled', got_p==want_p, str(got_p))
chk('six trough calls, exactly as tabled', got_t==want_t, str(got_t))
chk('thirteen calls in all', len(got_p)+len(got_t)==13)
print('=== 4. what 2024 does not contain')
D24=D['2024-01':'2024-12']
N=(np.log(NAT['initial claims'])*100).rolling(2).mean(); G=(N-N.rolling(30,min_periods=15).min())['2024-01':'2024-12']
print(f'   deteriorating share in 2024: min {D24.min():.1f}   national gap max {G.max():.1f} log points')
chk('share never below fifty in 2024', D24.min()>=50.)
chk('gap never exceeds twenty log points in 2024', G.max()<20.)
print('=== 5. the 1981 re-arm')
d81=D['1981-01':'1981-12']
print('   1981 diffusion:', ' '.join(f'{v:.1f}' for v in d81.values))
below=[i for i,v in enumerate(d81.values) if v<50]
chk('exactly four months below fifty in 1981', len(below)==4, str(below))
c4=[(p.strftime('%Y-%m'),dd.strftime('%Y-%m')) for p,dd in B.diffusion_peak_calls(D,phase_min=4)]
chk('at a four-month phase it fires 1982-01 dating 1981-11', ('1982-01','1981-11') in c4, str(c4))
print('=== 6. the diffusion clause at the trough')
dt_=B.diffusion_trough_calls(D)
NB=['1975-03','1980-07','1982-11','1991-03','2001-11','2009-06','2020-04']
TT={k:pd.Timestamp(k+'-01').year*12+pd.Timestamp(k+'-01').month for k in NB}
hits=0; oth=0
for p,dd in dt_:
    pm=p.year*12+p.month; dm=dd.year*12+dd.month
    if pm<1973*12+1: continue
    k=min(TT,key=lambda x:abs(dm-TT[x]))
    if abs(pm-TT[k])<=2 and abs(dm-TT[k])<=2: hits+=1
    else: oth+=1
print(f'   diffusion trough clause: {hits} of the seven NBER troughs, {oth} other calls')
chk('none of the seven, eight other calls', hits==0 and oth==8, f'{hits}/{oth}')
feb26=[ (p,dd) for p,dd in dt_ if dd.year==2026]
chk('it does find a 2026 trough dated February', any(dd.strftime('%Y-%m')=='2026-02' for _,dd in feb26), str(feb26))
print('=== 7. NBER announcement comparison')
ANN={'1980-01':'1980-06','1980-07':'1981-07','1981-07':'1982-01','1982-11':'1983-07',
     '1990-07':'1991-04','1991-03':'1992-12','2001-03':'2001-11','2001-11':'2003-07',
     '2007-12':'2008-12','2009-06':'2010-09','2020-02':'2020-06','2020-04':'2021-07'}
calls={'1980-01':'1980-02','1990-07':'1990-09','2001-03':'2001-05','2007-12':'2008-08',
       '2020-02':'2020-04','1975-03':'1975-04','1980-07':'1980-08','1991-03':'1991-05',
       '2001-11':'2002-01','2009-06':'2009-06','2020-04':'2020-06'}
gaps=[]
for k,a in ANN.items():
    if k in calls:
        am=pd.Timestamp(a+'-01'); cm=pd.Timestamp(calls[k]+'-01')
        gaps.append(((am.year-cm.year)*12+(am.month-cm.month),k))
print('   months earlier than the NBER:', sorted(gaps))
chk('ten comparisons', len(gaps)==10, str(len(gaps)))
chk('earlier on every one', all(g>0 for g,_ in gaps))
chk('range two to nineteen', min(g for g,_ in gaps)==2 and max(g for g,_ in gaps)==19,
    f'{min(g for g,_ in gaps)}..{max(g for g,_ in gaps)}')
print()
print(f'=== {ok} checks passed, {bad} failed')
