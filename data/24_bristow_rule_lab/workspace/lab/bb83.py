import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.,band_t=0.12,band_p=0.01,peak_cap=18)
LEVEL=[c for c in ALL if CONCEPT[c]=='level']
R={c:run_country_concept(c,**K) for c in ALL}
out={}
for sm in (1,3,5,6):
  for win in (5,6):
    for mp in (5,6):
      for mc in (15,12):
        for tag,cs in [('level',LEVEL),('all',ALL)]:
            B=[];Rr=[]
            for c in cs:
                B+=run_country_bb(c,smooth=sm,window=win,min_phase=mp,min_cycle=mc); Rr+=R[c]
            idx=[i for i,r in enumerate(B) if r['nch']>0 and (r['pk'] is not None or r['tr'] is not None)]
            n=len(idx)
            hb=(sum(B[i]['hp'] for i in idx),sum(B[i]['ht'] for i in idx))
            hr=(sum(Rr[i]['hp'] for i in idx),sum(Rr[i]['ht'] for i in idx))
            out.setdefault(tag,[]).append((hb[0]+hb[1],hb,hr,n,sm,win,mp,mc))
for tag in ('level','all'):
    rows=sorted(out[tag],reverse=True)
    b=rows[0]
    std=[r for r in out[tag] if r[4:]==(3,5,5,15)][0]
    print(f'{tag}: Bristow {b[2][0]}/{b[3]} {b[2][1]}/{b[3]}   BB best-of-32 {b[1][0]}/{b[3]} {b[1][1]}/{b[3]} '
          f'(smooth={b[4]} win={b[5]} mp={b[6]} mc={b[7]})   BB standard {std[1][0]}/{std[3]} {std[1][1]}/{std[3]}')
