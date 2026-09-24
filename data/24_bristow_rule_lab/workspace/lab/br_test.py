import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
from sa import sa_ratio_ma
import os, pandas as pd
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.,band_p=0.01,peak_cap=18)
IB='/home/claude/lab/ibge'
# write seasonally adjusted copies
for f in ('BRA_capital','BRA_intermediate','BRA_consumer','BRA_durables','BRA_nondurables'):
    p=f'{IB}/{f}_nsa.csv'
    if not os.path.exists(p): continue
    s=sa_ratio_ma(load(p))
    with open(f'{IB}/{f}_sa.csv','w') as g:
        g.write('date,value\n')
        for d,v in s.items(): g.write(f'{d:%Y-%m-%d},{v:.6f}\n')
ORIG=list(PANELS['Brazil']['ch'])
NAMES={'BRA_capital':'Brazil capital goods','BRA_intermediate':'Brazil intermediate goods',
       'BRA_durables':'Brazil consumer durables','BRA_nondurables':'Brazil consumer nondurables'}
SETS={'base':[], '+categories':[(n,f'{IB}/{k}_sa.csv','level') for k,n in NAMES.items()]}
for tag,add in SETS.items():
    PANELS['Brazil']['ch']=ORIG+[a for a in add if os.path.exists(a[1])]
    bench._cache.pop('Brazil',None)
    tot=[]
    for c in ALL: tot+=run_country_concept(c,**K)
    s=score(tot,'',show=False)
    b=score([r for r in tot if r['country']=='Brazil'],'',show=False)
    print(f'{tag:14s} ALL peak {s["hp"]}/83 trough {s["ht"]}/83   Brazil {b["hp"]}/10 {b["ht"]}/10')
    for x in [r for r in tot if r['country']=='Brazil' and not (r['hp'] and r['ht'])]:
        g=lambda d: d.strftime('%Y-%m') if d is not None else '--'
        print(f"     {x['peak_off']}->{x['tr_off']}  {g(x['pk'])}/{g(x['tr'])} {'P' if x['hp'] else '-'}{'T' if x['ht'] else '-'} nch={x['nch']}")
PANELS['Brazil']['ch']=ORIG; bench._cache.pop('Brazil',None)
