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
ORIG={c:list(PANELS[c]['ch']) for c in ALL}
def add(which):
    for c in ALL: PANELS[c]['ch']=list(ORIG[c]); bench._cache.pop(c,None)
    if which=='none': return
    for c,a in AR.items():
        ex=[]
        for meas,nm in (('WSDW','dwellings started'),('NODW','dwelling permits')):
            if which=='started' and meas!='WSDW': continue
            if which=='permits' and meas!='NODW': continue
            p=f'{KEI}/{a}_{meas}_F41.csv'
            if os.path.exists(p): ex.append((nm,p,'level'))
        if ex: PANELS[c]['ch']=ORIG[c]+ex; bench._cache.pop(c,None)
    if which in ('both','permits','started'):
        ex=[]
        for a in ('FRA','FIN','BEL','ESP','DEU','NLD'):
            for meas,nm in (('WSDW',f'{a} dwellings started'),('NODW',f'{a} dwelling permits')):
                if which=='started' and meas!='WSDW': continue
                if which=='permits' and meas!='NODW': continue
                p=f'{KEI}/{a}_{meas}_F41.csv'
                if os.path.exists(p): ex.append((nm,p,'level'))
        if ex: PANELS['Euro area']['ch']=ORIG['Euro area']+ex; bench._cache.pop('Euro area',None)
for which in ('none','started','permits','both'):
    add(which)
    tot=[]
    for c in ALL: tot+=run_country_concept(c,**K)
    s=score(tot,'',show=False)
    per=' '.join(f'{c[:4]}{score([r for r in tot if r["country"]==c],"",show=False)["hp"]}/{score([r for r in tot if r["country"]==c],"",show=False)["ht"]}' for c in ALL)
    print(f'{which:8s} peak {s["hp"]}/80 trough {s["ht"]}/80 | {per}')
