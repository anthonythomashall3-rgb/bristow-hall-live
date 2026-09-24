import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
CFG=dict(band_t=0.03,band_p=0.01,peak_cap=18,n=3,min_depth=5.0)
LEVEL=[c for c in ALL if CONCEPT[c]=='level']
A=[];B=[];D=[]
for c in LEVEL:
    A+=run_country2(c,**CFG)
    B+=run_country_ci(c,band_t=0.03,band_p=0.01,n=3,peak_cap=18)
    D+=run_country4(c,band_t=0.03,band_p=0.01,n=3,peak_cap=18)
for r,t in ((A,'A median of the channel dates'),(B,'B date a chain-linked composite index'),(D,'D date the cross-channel median level')):
    s=score(r,'',show=False)
    print(f'{t:44s} peak {s["hp"]:3d}/{s["n"]:<3d} trough {s["ht"]:3d}/{s["n"]:<3d}')
