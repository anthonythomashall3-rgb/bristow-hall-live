import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import os
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.)
N='/home/claude/lab/nber/data'
SETS={
 'none':[],
 'four':[('business activity index (Babson)',f'{N}/m01001.csv'),
         ('department store sales',f'{N}/m06002b.csv'),
         ('manufacturing employment',f'{N}/m08010b.csv'),
         ('manufacturing payrolls',f'{N}/m08069b.csv')],
 'four+prod':[('business activity index (Babson)',f'{N}/m01001.csv'),
         ('department store sales',f'{N}/m06002b.csv'),
         ('manufacturing employment',f'{N}/m08010b.csv'),
         ('manufacturing payrolls',f'{N}/m08069b.csv'),
         ('electric power production',f'{N}/m01128.csv'),
         ('freight carloadings',f'{N}/m03031.csv'),
         ('pig iron production',f'{N}/m01130a.csv'),
         ('steel ingot production',f'{N}/m01135a.csv')],
}
ORIG=list(PANELS['United States (interwar)']['ch'])
for tag,add in SETS.items():
    PANELS['United States (interwar)']['ch']=ORIG+[(nm,p,'level') for nm,p in add if os.path.exists(p)]
    bench._cache.pop('United States (interwar)',None)
    r=run_country_concept('United States (interwar)',**K)
    s=score(r,'',show=False)
    print(f'{tag:10s} peak {s["hp"]}/2 trough {s["ht"]}/2')
    for x in r:
        f=lambda d: d.strftime('%Y-%m') if d is not None else '--'
        print(f"    {x['peak_off']}->{x['tr_off']}  ours {f(x['pk'])}/{f(x['tr'])}  {'P' if x['hp'] else '-'}{'T' if x['ht'] else '-'} nch={x['nch']}")
PANELS['United States (interwar)']['ch']=ORIG; bench._cache.pop('United States (interwar)',None)
