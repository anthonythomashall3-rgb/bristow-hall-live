import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import numpy as np, pandas as pd, itertools
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
DI=pd.read_csv('/home/claude/lab/statcan/CA_gdp_diffusion.csv',index_col=0,parse_dates=True)['value']
ch=dict(channels('Canada'))
def run(n_s,band_di,where):
    rows=[]
    for _e in PANELS['Canada']['chrono']:
        pk_off,tr_off,freq=ep3(_e,'M')
        pkm=ts(pk_off); trm=ts(tr_off)
        w0=pkm-pd.DateOffset(months=12); w1=trm+pd.DateOffset(months=12)
        gdp=ch.get('monthly GDP'); ip=ch.get('industrial production'); emp=ch.get('employment')
        ok=lambda s: s is not None and s.index.min()<=w0 and s.index.max()>=trm
        core = gdp if ok(gdp) else (ip if ok(ip) else None)
        if core is None: rows.append((pk_off,None,tr_off,None)); continue
        td=[ch_trough(core,w0,w1,0.12,3,12,abstain=False)]
        if ok(emp): td.append(ch_trough(emp,w0,w1,0.12,3,12,abstain=False))
        if DI.index.min()<=w0 and DI.index.max()>=trm:
            td.append(ch_trough(DI,w0,w1,band_di,n_s,12,abstain=False,where=where))
        tr=med([x for x in td if x is not None])
        pk=med([ch_peak(core,w0,tr if tr is not None else w1,0.01,3,abstain=False)])
        a,e1=hit(pk,pk_off,'M'); b,e2=hit(tr,tr_off,'M')
        rows.append((pk_off,e1,tr_off,e2))
    et=[abs(r[3]) for r in rows if r[3] is not None]
    ep=[abs(r[1]) for r in rows if r[1] is not None]
    return (sum(1 for x in ep if x<=3),sum(1 for x in et if x<=3),np.mean(ep),np.mean(et),
            sum(1 for x in et if x<=2),rows)
print('       n_s band  where     P    T   MADp  MADt  w2T')
for n_s,bd,wh in itertools.product((3,5),(0.12,0.20,0.30),('mid','last')):
    r=run(n_s,bd,wh)
    print(f'       {n_s:3d} {bd:.2f}  {wh:5s}  {r[0]:3d} {r[1]:4d}  {r[2]:.2f}  {r[3]:.2f}  {r[4]}')
print()
r=run(3,0.12,'mid')
print('n_s=3 band=0.12 where=mid (the rule\'s own settings):')
for x in r[5]: print('   ',x)

def run2(with_peak):
    rows=[]
    for _e in PANELS['Canada']['chrono']:
        pk_off,tr_off,freq=ep3(_e,'M')
        pkm=ts(pk_off); trm=ts(tr_off)
        w0=pkm-pd.DateOffset(months=12); w1=trm+pd.DateOffset(months=12)
        gdp=ch.get('monthly GDP'); ip=ch.get('industrial production'); emp=ch.get('employment')
        ok=lambda s: s is not None and s.index.min()<=w0 and s.index.max()>=trm
        core = gdp if ok(gdp) else (ip if ok(ip) else None)
        if core is None: rows.append((pk_off,None,tr_off,None)); continue
        hasdi = DI.index.min()<=w0 and DI.index.max()>=trm
        td=[ch_trough(core,w0,w1,0.12,3,12,abstain=False)]
        if ok(emp): td.append(ch_trough(emp,w0,w1,0.12,3,12,abstain=False))
        if hasdi: td.append(ch_trough(DI,w0,w1,0.30,3,12,abstain=False,where='last'))
        tr=med([x for x in td if x is not None])
        pd_=[ch_peak(core,w0,tr if tr is not None else w1,0.01,3,abstain=False)]
        if with_peak and hasdi:
            p=di_peak_first(ma(DI,3),w0,tr if tr is not None else w1,45.,4)
            if p is not None: pd_.append(p)
        pk=med([x for x in pd_ if x is not None])
        a,e1=hit(pk,pk_off,'M'); b,e2=hit(tr,tr_off,'M')
        rows.append((pk_off,e1,tr_off,e2))
    ep=[abs(r[1]) for r in rows if r[1] is not None]; et=[abs(r[3]) for r in rows if r[3] is not None]
    return (sum(1 for x in ep if x<=3),sum(1 for x in et if x<=3),np.mean(ep),np.mean(et),
            sum(1 for x in ep if x<=2),sum(1 for x in et if x<=2),rows)
print()
for wp in (False,True):
    r=run2(wp)
    print(f'DI in peak={wp}:  P{r[0]} T{r[1]}  MAD {r[2]:.2f}/{r[3]:.2f}  w2 {r[4]},{r[5]}')
    for x in r[6]: print('     ',x)
