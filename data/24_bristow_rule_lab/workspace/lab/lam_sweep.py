import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
ORIG=list(PANELS['Korea']['ch'])
VAR={'base':ORIG,'+IMF':ORIG+imf('KOR')}
print(f'{"panel":6s} {"lambda":>9s}  Korea p/t     ALL peak  ALL trough')
for tag,ch in VAR.items():
    for lam in [14400.,129600.,500000.,1e6,2e6,1e5,5e4]:
        PANELS['Korea']['ch']=ch; bench._cache.pop('Korea',None)
        tot=[]
        for c in ALL: tot+=run_country_concept(c,min_depth=5.0,lam=lam)
        s=score(tot,'',show=False)
        k=score([r for r in tot if r['country']=='Korea'],'',show=False)
        j=score([r for r in tot if r['country']=='Japan'],'',show=False)
        print(f'{tag:6s} {lam:9.0f}  {k["hp"]:2d}/{k["ht"]:2d}  JP {j["hp"]:2d}/{j["ht"]:2d}   {s["hp"]:3d}/80    {s["ht"]:3d}/80')
PANELS['Korea']['ch']=ORIG; bench._cache.pop('Korea',None)
