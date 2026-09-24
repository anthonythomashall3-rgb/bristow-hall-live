import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import pandas as pd
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.)
LEVEL=[c for c in ALL if CONCEPT[c]=='level']
def bb_dates(chs,w0,w1):
    """Bry-Boschan on each channel; deepest trough in the window and the highest
    preceding peak; median across channels.  No official date is consulted."""
    tps=[];pks=[]
    for nm,s in chs:
        m=ma(s,3)[w0:w1].dropna()
        if len(m)<20: continue
        tp=bry_boschan(m)
        tr=[d for d,k in tp if k=='T']; pk=[d for d,k in tp if k=='P']
        if tr:
            t=min(tr,key=lambda d: float(m[d])); tps.append(t)
            pre=[d for d in pk if d<t]
            if pre: pks.append(max(pre,key=lambda d: float(m[d])))
        elif pk:
            pks.append(max(pk,key=lambda d: float(m[d])))
    return med(pks),med(tps)
for tag,cs in [('level chronologies',LEVEL),('all nine chronologies',ALL)]:
    hb=[0,0];hr=[0,0];n=0
    for c in cs:
        cfg=PANELS[c]; chs=[(nm,s) for nm,s in channels(c) if nm not in bench.SKIP]
        rows=run_country_concept(c,**K); i=0
        for _e in cfg['chrono']:
            pk_off,tr_off,freq=ep3(_e,cfg['freq'])
            pkm=ts(pk_off) if freq=='M' else q2m(pk_off); trm=ts(tr_off) if freq=='M' else q2m(tr_off)
            w0=pkm-pd.DateOffset(months=12); w1=trm+pd.DateOffset(months=12)
            use=[(nm,s) for nm,s in chs if s.index.min()<=w0 and s.index.max()>=trm]
            r=rows[i]; i+=1
            if not use: continue
            p,t=bb_dates(use,w0,w1)
            if p is None and t is None: continue
            n+=1
            hb[0]+=hit(p,pk_off,freq)[0]; hb[1]+=hit(t,tr_off,freq)[0]
            hr[0]+=r['hp']; hr[1]+=r['ht']
    print(f'{tag}: {n} episodes both rules reach   Bristow {hr[0]}/{n} {hr[1]}/{n}   Bry-Boschan {hb[0]}/{n} {hb[1]}/{n}')
