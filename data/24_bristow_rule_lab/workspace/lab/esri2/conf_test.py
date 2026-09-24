import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import os
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.)
KEI='/home/claude/lab/kei'
AR={'United States':'USA','Canada':'CAN','Japan':'JPN','Korea':'KOR','Brazil':'BRA',
    'Spain':'ESP','France':'FRA'}
EAA=['DEU','ITA','NLD','FRA','ESP','BEL','AUT','FIN','EA20']
ORIG={c:list(PANELS[c]['ch']) for c in ALL}
def setup(which):
    for c in ALL: PANELS[c]['ch']=list(ORIG[c]); bench._cache.pop(c,None)
    if which=='none': return
    meas=[]
    if which in ('bci','both'): meas.append(('BCICP','business confidence'))
    if which in ('cci','both'): meas.append(('CCICP','consumer confidence'))
    for c,a in AR.items():
        ex=[(nm,f'{KEI}/{a}_{m}.csv','balance') for m,nm in meas if os.path.exists(f'{KEI}/{a}_{m}.csv')]
        if ex: PANELS[c]['ch']=ORIG[c]+ex; bench._cache.pop(c,None)
    ex=[]
    for a in EAA:
        for m,nm in meas:
            p=f'{KEI}/{a}_{m}.csv'
            if os.path.exists(p): ex.append((f'{a} {nm}',p,'balance'))
    if ex: PANELS['Euro area']['ch']=ORIG['Euro area']+ex; bench._cache.pop('Euro area',None)
for which in ('none','bci','cci','both'):
    setup(which)
    tot=[]
    for c in ALL: tot+=run_country_concept(c,**K)
    s=score(tot,'',show=False)
    per=' '.join(f'{c[:4]}{score([r for r in tot if r["country"]==c],"",show=False)["hp"]}/{score([r for r in tot if r["country"]==c],"",show=False)["ht"]}' for c in ALL)
    print(f'{which:5s} peak {s["hp"]}/80 trough {s["ht"]}/80 | {per}')
