import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
from sa import sa_ratio_ma
import os
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.,band_p=0.01,peak_cap=18)
SC='/home/claude/lab/statcan'
# the raw series is not seasonally adjusted
for f in ('CAN_rail_tonmiles',):
    s=sa_ratio_ma(load(f'{SC}/{f}.csv'))
    with open(f'{SC}/{f}_sa.csv','w') as g:
        g.write('date,value\n')
        for d,v in s.items(): g.write(f'{d:%Y-%m-%d},{v:.6f}\n')
ORIG=list(PANELS['Canada']['ch'])
for tag,add in [('base',[]),
                ('+rail freight',[('railway freight ton-miles',f'{SC}/CAN_rail_tonmiles_sa.csv','level')])]:
    PANELS['Canada']['ch']=ORIG+[a for a in add if os.path.exists(a[1])]
    bench._cache.pop('Canada',None)
    tot=[]
    for c in ALL: tot+=run_country_concept(c,**K)
    s=score(tot,'',show=False)
    b=score([r for r in tot if r['country']=='Canada'],'',show=False)
    print(f'{tag:16s} ALL peak {s["hp"]}/83 trough {s["ht"]}/83   Canada {b["hp"]}/12 {b["ht"]}/12')
    for x in [r for r in tot if r['country']=='Canada' and not (r['hp'] and r['ht'])]:
        g=lambda d: d.strftime('%Y-%m') if d is not None else '--'
        print(f"     {x['peak_off']}->{x['tr_off']}  {g(x['pk'])}/{g(x['tr'])} {'P' if x['hp'] else '-'}{'T' if x['ht'] else '-'} nch={x['nch']}")
PANELS['Canada']['ch']=ORIG; bench._cache.pop('Canada',None)
