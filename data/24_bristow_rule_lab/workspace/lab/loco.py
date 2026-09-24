import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import numpy as np
bench.ABSTAIN=True; bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set()
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
GRID=[]
for n in [3]:
    for bt in [0.03,0.08,0.12,0.16]:
        for bp in [0.01,0.02,0.03,0.05]:
            for cap in [9,12,18,24]:
                for mdp in [3.0,5.0,8.0]:
                    GRID.append(dict(n=n,band_t=bt,band_p=bp,peak_cap=cap,min_depth=mdp,lam=500000.))
print(f'{len(GRID)} candidate configurations\n')
CACHE={}
def sc(c,g):
    k=(c,tuple(sorted(g.items())))
    if k not in CACHE: CACHE[k]=run_country_concept(c,**g)
    return CACHE[k]
SHIP=dict(n=3,band_t=0.12,band_p=0.01,peak_cap=18,min_depth=5.0,lam=500000.)
print(f'{"held-out chronology":26s} {"in-sample pick":34s} {"held-out":>10s}  {"shipped":>9s}')
oos=[0,0,0]; shp=[0,0,0]
for held in ALL:
    train=[c for c in ALL if c!=held]
    best=None
    for g in GRID:
        rows=[]
        for c in train: rows+=sc(c,g)
        s=score(rows,'',show=False)
        if best is None or s['hp']+s['ht']>best[0]: best=(s['hp']+s['ht'],g)
    g=best[1]
    r=sc(held,g); s=score(r,'',show=False)
    r2=sc(held,SHIP); s2=score(r2,'',show=False)
    oos[0]+=s['hp']; oos[1]+=s['ht']; oos[2]+=s['n']
    shp[0]+=s2['hp']; shp[1]+=s2['ht']; shp[2]+=s2['n']
    tag=f"bt={g['band_t']} bp={g['band_p']} cap={g['peak_cap']} md={g['min_depth']}"
    print(f'{held:26s} {tag:34s} {s["hp"]:3d}/{s["ht"]:<3d}/{s["n"]:<3d} {s2["hp"]:3d}/{s2["ht"]:<3d}')
print()
print(f'OUT OF SAMPLE   peak {oos[0]}/{oos[2]}  trough {oos[1]}/{oos[2]}  = {100*(oos[0]+oos[1])/(2*oos[2]):.0f}%')
print(f'SHIPPED CONFIG  peak {shp[0]}/{shp[2]}  trough {shp[1]}/{shp[2]}  = {100*(shp[0]+shp[1])/(2*shp[2]):.0f}%')
