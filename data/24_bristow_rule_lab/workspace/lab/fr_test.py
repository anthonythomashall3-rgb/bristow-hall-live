import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import os
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.,band_p=0.01,peak_cap=18)
I='/home/claude/lab/insee'
ORIG=list(PANELS['France']['ch'])
SETS={'base':[],
      '+consumption':[('real consumption',f'{I}/FR_conso_biens.csv','level')],
      '+consumption+manuf':[('real consumption',f'{I}/FR_conso_biens.csv','level'),
                            ('manufactured goods consumption',f'{I}/FR_conso_manuf.csv','level')]}
for tag,add in SETS.items():
    PANELS['France']['ch']=ORIG+[a for a in add if os.path.exists(a[1])]
    bench._cache.pop('France',None)
    tot=[]
    for c in ALL: tot+=run_country_concept(c,**K)
    s=score(tot,'',show=False)
    f=score([r for r in tot if r['country']=='France'],'',show=False)
    print(f'{tag:20s} ALL peak {s["hp"]}/83 trough {s["ht"]}/83   France {f["hp"]}/5 {f["ht"]}/5')
    if tag!='base':
        for x in [r for r in tot if r['country']=='France']:
            g=lambda d: d.strftime('%Y-%m') if d is not None else '--'
            print(f"     {x['peak_off']}->{x['tr_off']}  {g(x['pk'])}/{g(x['tr'])} {'P' if x['hp'] else '-'}{'T' if x['ht'] else '-'} nch={x['nch']}")
PANELS['France']['ch']=ORIG; bench._cache.pop('France',None)
