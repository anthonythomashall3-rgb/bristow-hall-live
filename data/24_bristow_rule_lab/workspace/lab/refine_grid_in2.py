import sys; sys.path.insert(0,'/home/claude'); sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import pandas as pd
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.,band_t=0.12,band_p=0.01,peak_cap=18)
def apply(spec):
    for kv in spec.split(';'):
        k,v=kv.split('=')
        if k=='T': bench.REFINE_T=None if v=='none' else tuple(int(x) for x in v.split(','))
        elif k=='P': bench.REFINE_P=None if v=='none' else tuple(int(x) for x in v.split(','))
        elif k=='rsT': bench.REFINE_SMOOTH_T=int(v)
        elif k=='rsP': bench.REFINE_SMOOTH_P=int(v)
        elif k=='scope': bench.REFINE_SCOPE=v
def cnt(e):
    e=[x for x in e if x is not None]
    return f"{sum(abs(x)==0 for x in e):2d}/{sum(abs(x)<=1 for x in e):2d}/{sum(abs(x)<=3 for x in e):2d} bias {sum(e)/len(e):+.2f} mae {sum(abs(x) for x in e)/len(e):.2f}"
def run(tag,spec):
    apply(spec); ep=[];et=[];q=0;qn=0;per={}
    for c in ALL:
        r=run_country_concept(c,**K); cfg=PANELS[c]
        for _e,b in zip(cfg['chrono'],r):
            pk_off,tr_off,freq=ep3(_e,cfg['freq'])
            if freq=='Q':
                qn+=2; q+=int(b['ep'] is not None and abs(b['ep'])<=1)+int(b['et'] is not None and abs(b['et'])<=1)
            else: ep.append(b['ep']); et.append(b['et'])
            per.setdefault(c,[]).append((str(pk_off),b['ep'],b['et']))
    line=f"{tag:16s} {spec:42s}|| peaks {cnt(ep)} | troughs {cnt(et)} | Q {q}/{qn}"
    print(line,flush=True); open('/tmp/refine_grid_in.log','a').write(line+'\n')
    import json; json.dump(per,open(f'/tmp/refine_in_{tag}.json','w'),default=str)
V=[("all_T31P10","T=3,1;P=1,0;rsT=1;rsP=2;scope=all"),("all_T22P10","T=2,2;P=1,0;rsT=1;rsP=2;scope=all"),
   ("all_T20P10","T=2,0;P=1,0;rsT=1;rsP=2;scope=all"),("all_T32P10","T=3,2;P=1,0;rsT=1;rsP=2;scope=all"),
   ("all_T41P10","T=4,1;P=1,0;rsT=1;rsP=2;scope=all"),("all_T21rs2P10","T=2,1;P=1,0;rsT=2;rsP=2;scope=all"),
   ("all_T21P11rs2","T=2,1;P=1,1;rsT=1;rsP=2;scope=all"),("all_T21P10rs1","T=2,1;P=1,0;rsT=1;rsP=1;scope=all")]
for tag,spec in V: run(tag,spec)
open('/tmp/refine_grid_in.log','a').write('ALLDONE2\n')
