import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.,band_t=0.12,band_p=0.01,peak_cap=18)
tot=[]
for c in ALL:
    r=run_country_concept(c,**K); tot+=r
    for x in r:
        if x['hp'] and x['ht']: continue
        f=lambda d: d.strftime('%Y-%m') if d is not None else '--'
        ep=x['ep'] if x['ep'] is not None else '-'; et=x['et'] if x['et'] is not None else '-'
        print(f"{c:26s} {str(x['peak_off']):12s}->{str(x['tr_off']):12s} ours {f(x['pk'])}/{f(x['tr'])} "
              f"{'P' if x['hp'] else '-'}{'T' if x['ht'] else '-'} err {ep:>4}/{et:<4} nch={x['nch']:2d} {x['verdict']}")
s=score(tot,'',show=False)
print(f"\nTOTAL peak {s['hp']}/80 trough {s['ht']}/80")
