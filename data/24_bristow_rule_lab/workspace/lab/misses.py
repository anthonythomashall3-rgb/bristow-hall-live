import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.)
for c in ALL:
    if c=='Japan': continue
    r=run_country_concept(c,**K)
    bad=[x for x in r if not (x['hp'] and x['ht'])]
    if not bad: continue
    print('==',c)
    for x in bad:
        fq=PANELS[c]['freq']
        pk=x['pk'].strftime('%Y-%m') if x['pk'] is not None else '--'
        tr=x['tr'].strftime('%Y-%m') if x['tr'] is not None else '--'
        print(f"   {str(x['peak_off']):12s}->{str(x['tr_off']):12s}  ours {pk}/{tr}  {'P' if x['hp'] else '-'}{'T' if x['ht'] else '-'}  nch={x['nch']} {x['verdict']}")
