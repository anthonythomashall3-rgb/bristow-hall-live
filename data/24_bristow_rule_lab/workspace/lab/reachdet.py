import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import pandas as pd, collections
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.,band_t=0.12,band_p=0.01,peak_cap=18)
TARGETS=[('Korea','1979-02'),('Spain',(1978,3)),('United States','1969-12')]
for c,pk in TARGETS:
    cnt=collections.Counter()
    for cpt in ('level','growth','diffusion'):
        for bt in (0.01,0.02,0.03,0.05):
            for bp in (0.01,0.02,0.03,0.05):
                for cap in (9,12,18,24):
                    for md in (3.0,5.0,8.0):
                        rs=run_country_concept(c,concept=cpt,band_t=bt,band_p=bp,peak_cap=cap,
                                               min_depth=md,lam=500000.)
                        for r in rs:
                            if r['peak_off']==pk and r['hp'] and r['ht']: cnt[cpt]+=1
    print(c,pk,dict(cnt))
