"""The activity panel is a choice: eight American panels measured on the record and on 2022-2026.

Anthony (3 September 2026): "you say it is not an activity-panel event, but you didn't consider that
maybe we have to edit our activity panel."  Measured here.  The shipped panel is the six series the
committee names plus retail volume; the variants add or drop channels that exist on today's data:
the unemployment rate (inverted, 100 - r), car registrations, construction production, national
initial and continued claims as levels (the Department's weekly file 1967 on, monthly means, the
inverse so that rising claims is a falling level), manufacturing hours and employment (ALFRED's
current vintage), the committee's six alone, and a labor-market-only panel.  Three readings for each:

  record      the twelve postwar contractions in the shipped windows (twelve months before the
              committee's peak to twelve after its trough), date_turning_points at the shipped
              configuration - exact / within one / within three at each end
  confirm     causal: the first month the panel's composite D (median of the channels' drawdowns
              of the three-month mean from the trailing twelve-month maximum) stands at 2.0 or more
              - months after the committee's peak for each recession, and every such crossing
              outside [peak-3, trough+3] as an other call (one per episode, re-armed once D is back
              below 1.0)
  2022-2026   the window from January 2022 to the data edge: the panel's verdict and dates, the
              composite D's maximum, and how many channels' own D reaches 2.0
Output panel_edit_test.log.  A measurement of the panel as a choice; nothing adopted on it.
"""
import sys, warnings; warnings.filterwarnings('ignore')
sys.path.insert(0,'/home/claude'); sys.path.insert(0,'/home/claude/lab'); sys.path.insert(0,'/home/claude/lab/rt'); sys.argv=['x']
import numpy as np, pandas as pd, bristow_rule_v3 as B, bench, alfred as al
from bench import PANELS, channels, ep3, ts, md
SKIP={'exports','imports','car registrations','unemployment','construction production','construction output','capital goods production','intermediate goods production','consumer durables production'}
ALL=dict(channels('United States'))
NBER=[(ts(ep3(e,'M')[0]),ts(ep3(e,'M')[1])) for e in PANELS['United States']['chrono']]
def monthly_inverse(sid):
    s=al.wide(sid).iloc[:,-1].dropna(); s.index=pd.DatetimeIndex(s.index)
    m=s.resample('MS').mean(); return (1.0/m)*1e6
def current(sid):
    s=al.wide(sid).iloc[:,-1].dropna(); s.index=pd.DatetimeIndex([pd.Timestamp(d.year,d.month,1) for d in s.index]); return s.astype(float)
SHIP=[nm for nm in ALL if nm not in SKIP]
EXTRA={'unemployment (100 - r)':ALL['unemployment'],'car registrations':ALL['car registrations'],'construction production':ALL['construction production'],
       'initial claims (inverse)':monthly_inverse('ICSA'),'continued claims (inverse)':monthly_inverse('CCSA'),
       'manufacturing hours':current('AWHMAN'),'manufacturing employment':current('MANEMP')}
VARIANTS={
 'shipped (committee six + retail volume)':[(nm,ALL[nm]) for nm in SHIP],
 '+ unemployment rate':[(nm,ALL[nm]) for nm in SHIP]+[('unemployment (100 - r)',EXTRA['unemployment (100 - r)'])],
 '+ car registrations':[(nm,ALL[nm]) for nm in SHIP]+[('car registrations',EXTRA['car registrations'])],
 '+ construction production':[(nm,ALL[nm]) for nm in SHIP]+[('construction production',EXTRA['construction production'])],
 '+ initial and continued claims':[(nm,ALL[nm]) for nm in SHIP]+[('initial claims (inverse)',EXTRA['initial claims (inverse)']),('continued claims (inverse)',EXTRA['continued claims (inverse)'])],
 '+ hours and manufacturing employment':[(nm,ALL[nm]) for nm in SHIP]+[('manufacturing hours',EXTRA['manufacturing hours']),('manufacturing employment',EXTRA['manufacturing employment'])],
 '+ unemployment, claims, hours (labor inside)':[(nm,ALL[nm]) for nm in SHIP]+[(k,EXTRA[k]) for k in ('unemployment (100 - r)','initial claims (inverse)','continued claims (inverse)','manufacturing hours')],
 'the committee six alone':[(nm,ALL[nm]) for nm in SHIP if nm!='retail volume'],
 'labor market only':[('payroll employment',ALL['payroll employment']),('household employment',ALL['household employment'])]+[(k,EXTRA[k]) for k in ('unemployment (100 - r)','initial claims (inverse)','continued claims (inverse)','manufacturing hours','manufacturing employment')],
}
def record(chs):
    P=[];T=[]
    for pk,tr in NBER:
        w0=pk-pd.DateOffset(months=12); w1=tr+pd.DateOffset(months=12)
        use=[(nm,s) for nm,s in chs if s.index.min()<=w0 and s.index.max()>=tr] or [(nm,s) for nm,s in chs if s.index.min()<=tr and s.index.max()>=tr] or chs
        vol=[(nm,s) for nm,s in use if 'unemployment' not in nm]
        r=B.date_turning_points(use,w0,w1,volume_channels=vol or use,concept='level',lam=500000.0,band_trough=0.12,band_peak=0.01,peak_cap=18,smooth=3,lookback=12)
        P.append(None if r['peak'] is None else md(r['peak'],pk)); T.append(None if r['trough'] is None else md(r['trough'],tr))
    f=lambda e:(sum(1 for x in e if x==0),sum(1 for x in e if x is not None and abs(x)<=1),sum(1 for x in e if x is not None and abs(x)<=3))
    return f(P),f(T),P,T
def confirm(chs):
    comp=B.composite_deviation(chs,12,3,2).dropna(); comp=comp[comp.index>=pd.Timestamp('1948-01-01')]
    on=False; cross=[]
    for t,v in comp.items():
        if not on and v>=2.0: cross.append(t); on=True
        elif on and v<1.0: on=False
    lags=[]; used=set()
    for pk,tr in NBER:
        c=[x for x in cross if pk-pd.DateOffset(months=3)<=x<=tr+pd.DateOffset(months=3)]
        if c: lags.append(md(c[0],pk)); used|=set(c)
        else: lags.append(None)
    other=[x.strftime('%Y-%m') for x in cross if x not in used]
    return lags,other
def now(chs):
    w0=pd.Timestamp('2022-01-01'); use=[(nm,s) for nm,s in chs if s.index.min()<=w0]; w1=max(s.index.max() for _,s in use)
    comp=B.composite_deviation(use,12,3,2)[w0:w1]
    D=B._panel_frame(use,lambda s:B.deviation(s,12,3))[w0:w1]
    r=B.date_turning_points(use,w0,w1,volume_channels=[(nm,s) for nm,s in use if 'unemployment' not in nm] or use,concept='level',lam=500000.0,band_trough=0.12,band_peak=0.01,peak_cap=18,smooth=3,lookback=12)
    return float(comp.max()),comp.idxmax(),int((D.max()>=2.0).sum()),len(use),r
if __name__=='__main__':
    print('panel                                          n | record: peaks exact/w1/w3, troughs | confirmation: months from the committee peak to composite D >= 2 (None = never); other crossings | 2022-2026: composite D max, channels at 2.0, verdict, dates')
    for name,chs in VARIANTS.items():
        (pe,te,P,T)=record(chs); lags,other=confirm(chs); mx,mxm,k,n,r=now(chs)
        print(f"{name:46s} {len(chs):2d} | {pe[0]}/{pe[1]}/{pe[2]}, {te[0]}/{te[1]}/{te[2]} | {lags} other {other} | {mx:.2f} ({mxm:%Y-%m}), {k}/{n}, {r['verdict']}, P {r['peak']:%Y-%m} T {r['trough']:%Y-%m}")
        print(f"{'':46s}    per-episode errors P {P}  T {T}")
