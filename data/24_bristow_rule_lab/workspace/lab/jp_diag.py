import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.)
ORIG=list(PANELS['Japan']['ch'])
for tag,ch in [('base',ORIG),('+IMF',ORIG+[('IMF industrial production','/home/claude/lab/imf/JPN_IND_IX.csv','level'),
                                            ('IMF manufacturing production','/home/claude/lab/imf/JPN_C_IX.csv','level')])]:
    PANELS['Japan']['ch']=ch; bench._cache.pop('Japan',None)
    r=run_country_concept('Japan',**K)
    s=score(r,'',show=False)
    print(f'=== {tag}  peak {s["hp"]}/16  trough {s["ht"]}/16')
    for x in r:
        pk=x['pk'].strftime('%Y-%m') if x['pk'] is not None else '  --   '
        tr=x['tr'].strftime('%Y-%m') if x['tr'] is not None else '  --   '
        print(f"  {x['peak_off']}->{x['tr_off']}  ours {pk}/{tr}  {'P' if x['hp'] else '-'}{'T' if x['ht'] else '-'}  nch={x['nch']}")
PANELS['Japan']['ch']=ORIG; bench._cache.pop('Japan',None)
