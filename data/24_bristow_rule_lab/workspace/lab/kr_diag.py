import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.)
import copy
ORIG=list(PANELS["Korea"]["ch"])
for tag,ch in [('base',ORIG),('+IMF',ORIG+imf('KOR'))]:
    PANELS['Korea']['ch']=ch
    bench._cache.pop('Korea',None)
    r=run_country_concept('Korea',**K)
    print('===',tag)
    for x in r:
        pk=x['pk'].strftime('%Y-%m') if x['pk'] is not None else '  --   '
        tr=x['tr'].strftime('%Y-%m') if x['tr'] is not None else '  --   '
        print(f"  official {x['peak_off']} -> {x['tr_off']}   ours {pk} / {tr}   hp={x['hp']} ht={x['ht']} nch={x['nch']} verdict={x.get('verdict','')}")
PANELS['Korea']['ch']=ORIG
