import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
CFGS={
 'shipped        bt=.03 bp=.02 cap=12 md=5':dict(band_t=0.03,band_p=0.02,peak_cap=12,min_depth=5.0),
 'modal LOCO     bt=.03 bp=.01 cap=18 md=5':dict(band_t=0.03,band_p=0.01,peak_cap=18,min_depth=5.0),
 '               bt=.03 bp=.01 cap=12 md=5':dict(band_t=0.03,band_p=0.01,peak_cap=12,min_depth=5.0),
 '               bt=.03 bp=.02 cap=18 md=5':dict(band_t=0.03,band_p=0.02,peak_cap=18,min_depth=5.0),
 '               bt=.02 bp=.01 cap=18 md=5':dict(band_t=0.02,band_p=0.01,peak_cap=18,min_depth=5.0),
}
for tag,g in CFGS.items():
    tot=[]
    for c in ALL: tot+=run_country_concept(c,n=3,L=12,lam=500000.,**g)
    s=score(tot,'',show=False)
    per=' '.join(f'{c[:4]}{score([r for r in tot if r["country"]==c],"",show=False)["hp"]}/{score([r for r in tot if r["country"]==c],"",show=False)["ht"]}' for c in ALL)
    print(f'{tag}  peak {s["hp"]}/80 trough {s["ht"]}/80 | {per}')
