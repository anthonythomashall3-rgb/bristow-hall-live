import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import os
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
CORE={'exports','imports','car registrations','unemployment','construction production',
      'construction output','capital goods production','intermediate goods production',
      'consumer durables production'}
bench.SKIP=set(CORE)
K=dict(min_depth=5.0,lam=500000.,band_t=0.12,band_p=0.01,peak_cap=18)
KEI='/home/claude/lab/kei'; IMF='/home/claude/lab/imf'
AR={'United States':'USA','Canada':'CAN','Japan':'JPN','Korea':'KOR','Brazil':'BRA',
    'Spain':'ESP','France':'FRA'}
EAA=['DEU','ITA','NLD','FRA','ESP','BEL','AUT','FIN','EA20']
ORIG={c:list(PANELS[c]['ch']) for c in ALL}
def reset():
    for c in ALL: PANELS[c]['ch']=list(ORIG[c]); bench._cache.pop(c,None)
def total():
    t=[]
    for c in ALL: t+=run_country_concept(c,**K)
    s=score(t,'',show=False); return s['hp'],s['ht']
reset(); base=total(); print(f'base  peak {base[0]}/83 trough {base[1]}/83')
def add(spec, ea_spec=None, kind='level'):
    reset()
    for c,a in AR.items():
        ex=[(nm,p,kind) for nm,p in spec(a) if os.path.exists(p)]
        if ex: PANELS[c]['ch']=ORIG[c]+ex; bench._cache.pop(c,None)
    if ea_spec:
        ex=[]
        for a in EAA: ex+=[(f'{a} {nm}',p,kind) for nm,p in ea_spec(a) if os.path.exists(p)]
        if ex: PANELS['Euro area']['ch']=ORIG['Euro area']+ex; bench._cache.pop('Euro area',None)
    return total()
tests=[
 ('dwellings started', lambda a:[('dwellings started',f'{KEI}/{a}_WSDW_F41.csv')],
                       lambda a:[('dwellings started',f'{KEI}/{a}_WSDW_F41.csv')],'level'),
 ('dwelling permits',  lambda a:[('dwelling permits',f'{KEI}/{a}_NODW_F41.csv')],
                       lambda a:[('dwelling permits',f'{KEI}/{a}_NODW_F41.csv')],'level'),
 ('business confidence', lambda a:[('business confidence',f'{KEI}/{a}_BCICP.csv')],
                       lambda a:[('business confidence',f'{KEI}/{a}_BCICP.csv')],'balance'),
 ('consumer confidence', lambda a:[('consumer confidence',f'{KEI}/{a}_CCICP.csv')],
                       lambda a:[('consumer confidence',f'{KEI}/{a}_CCICP.csv')],'balance'),
 ('IMF added not spliced', lambda a:[('IMF industrial production',f'{IMF}/{a}_IND_SA_IX.csv')],
                       None,'level'),
]
for name,spec,ea,kind in tests:
    r=add(spec,ea,kind)
    print(f'   {name:26s} peak {r[0]:2d} ({r[0]-base[0]:+d})  trough {r[1]:2d} ({r[1]-base[1]:+d})')
reset()
# drop the reference series from the level route
for c in ALL:
    bench.SKIP = CORE if CONCEPT.get(c)=='growth' else CORE|{'monthly reference GDP'}
t=[]
for c in ALL:
    bench.SKIP = CORE if CONCEPT.get(c)=='growth' else CORE|{'monthly reference GDP'}
    t+=run_country_concept(c,**K)
bench.SKIP=set(CORE)
s=score(t,'',show=False)
print(f'   {"drop reference series from level":26s} peak {s["hp"]:2d} ({s["hp"]-base[0]:+d})  trough {s["ht"]:2d} ({s["ht"]-base[1]:+d})')
