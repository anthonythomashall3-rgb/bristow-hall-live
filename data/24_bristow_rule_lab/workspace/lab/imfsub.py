"""The IMF's production sub-indices as extra channels.

Mining (B), manufacturing (C), utilities (D) and construction (F), for every economy
where the IMF publishes them.  These are the same concept split finer, so the test is
whether more granular production helps or simply double-weights production.
"""
import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
from w2 import w2
import os
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.,band_t=0.12,band_p=0.01,peak_cap=18)
IMF='/home/claude/lab/imf'
AR={'United States':'USA','Canada':'CAN','Japan':'JPN','Korea':'KOR','Brazil':'BRA',
    'Spain':'ESP','France':'FRA'}
EAA=['DEU','ITA','NLD','BEL','AUT','FIN','ESP']
ORIG={c:list(PANELS[c]['ch']) for c in ALL}
NAMES={'B_IX':'IMF mining production','D_IX':'IMF utilities production',
       'C_IX':'IMF manufacturing production','F_IX':'IMF construction production'}
def setp(codes):
    for c in ALL: PANELS[c]['ch']=list(ORIG[c]); bench._cache.pop(c,None)
    if not codes: return
    for c,a in AR.items():
        ex=[(NAMES[k],f'{IMF}/{a}_{k}.csv','level') for k in codes if os.path.exists(f'{IMF}/{a}_{k}.csv')]
        if ex: PANELS[c]['ch']=ORIG[c]+ex; bench._cache.pop(c,None)
    ex=[]
    for a in EAA:
        for k in codes:
            p=f'{IMF}/{a}_{k}.csv'
            if os.path.exists(p): ex.append((f'{a} {NAMES[k]}',p,'level'))
    if ex: PANELS['Euro area']['ch']=ORIG['Euro area']+ex; bench._cache.pop('Euro area',None)
for tag,codes in (('none',[]),('mining',['B_IX']),('utilities',['D_IX']),
                  ('manufacturing',['C_IX']),('construction',['F_IX']),
                  ('mining+utilities',['B_IX','D_IX']),
                  ('all four',['B_IX','C_IX','D_IX','F_IX'])):
    setp(codes)
    tot=[]
    for c in ALL: tot+=run_country_concept(c,**K)
    a,na,b,nb,ma_,mb,sa,sb=w2(tot); s=score(tot,'',show=False)
    print(f'{tag:18s} within2 {a}+{b}={a+b}  hits {s["hp"]}/{s["ht"]}  MAE {ma_:.2f}/{mb:.2f}')
setp([])
