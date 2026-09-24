import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.,band_p=0.01,peak_cap=18)
# NBER's own interwar chronology, all five contractions from 1920
FULL=[('1920-01','1921-07'),('1923-05','1924-07'),('1926-10','1927-11'),
      ('1929-08','1933-03'),('1937-05','1938-06')]
PANELS['United States (interwar)']['chrono']=FULL
r=run_country_concept('United States (interwar)',**K)
s=score(r,'',show=False)
print(f'US interwar, NBER\'s five contractions from 1920: peak {s["hp"]}/5 trough {s["ht"]}/5')
for x in r:
    f=lambda d: d.strftime('%Y-%m') if d is not None else '--'
    print(f"   {x['peak_off']}->{x['tr_off']}  ours {f(x['pk'])}/{f(x['tr'])} "
          f"{'P' if x['hp'] else '-'}{'T' if x['ht'] else '-'} nch={x['nch']}")
