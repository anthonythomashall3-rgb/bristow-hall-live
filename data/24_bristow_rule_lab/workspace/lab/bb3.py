import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.,band_p=0.01,peak_cap=18)
LEVEL=[c for c in ALL if CONCEPT[c]=='level']
R={}
for c in ALL: R[c]=run_country_concept(c,**K)
best=[]
for sm in (1,3,5,6):
  for win in (5,6):
    for mp in (5,6):
      for mc in (15,12):
        for cs_tag,cs in [('level',LEVEL),('all',ALL)]:
            B=[];Rr=[]
            for c in cs:
                B+=run_country_bb(c,smooth=sm,window=win,min_phase=mp,min_cycle=mc); Rr+=R[c]
            idx=[i for i,r in enumerate(B) if r['nch']>0 and (r['pk'] is not None or r['tr'] is not None)]
            n=len(idx)
            hb=(sum(B[i]['hp'] for i in idx),sum(B[i]['ht'] for i in idx))
            hr=(sum(Rr[i]['hp'] for i in idx),sum(Rr[i]['ht'] for i in idx))
            best.append((cs_tag,sm,win,mp,mc,n,hb,hr))
for tag in ('level','all'):
    rows=[b for b in best if b[0]==tag]
    rows.sort(key=lambda b:-(b[6][0]+b[6][1]))
    print(f'--- {tag}: Bry-Boschan at its own best over 32 settings')
    for b in rows[:3]:
        print(f'   smooth={b[1]} window={b[2]} min_phase={b[3]} min_cycle={b[4]}  BB {b[6][0]}/{b[5]} {b[6][1]}/{b[5]}   Bristow {b[7][0]}/{b[5]} {b[7][1]}/{b[5]}')
