import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
bench.ABSTAIN=True; bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set()
BASE={'exports','imports','car registrations','unemployment'}
CONS={'construction production','construction output'}
GB={'capital goods production','intermediate goods production','consumer durables production'}
print(f'{"channels":34s} {"cap":>4s}  {"peak":>9s} {"trough":>9s}  sum   {"level chronologies":>22s}')
best=None
for lab,sk in [('core (no constr, no breakdown)',BASE|CONS|GB),
               ('core + construction',BASE|GB),
               ('core + breakdown',BASE|CONS),
               ('core + both',BASE)]:
    for cap in [6,9,12,18]:
        bench.SKIP=sk
        tot=[]; lev=[]
        for c in ALL:
            r=run_country_concept(c,min_depth=5.0,lam=500000.,peak_cap=cap); tot+=r
            if CONCEPT[c]=='level': lev+=r
        s=score(tot,'',show=False); sl=score(lev,'',show=False)
        print(f'{lab:34s} {cap:4d}  {s["hp"]:4d}/{s["n"]:<4d} {s["ht"]:4d}/{s["n"]:<4d}  {s["hp"]+s["ht"]:3d}   {sl["hp"]:3d}/{sl["n"]} {sl["ht"]:3d}/{sl["n"]}')
        if best is None or s['hp']+s['ht']>best[0]: best=(s['hp']+s['ht'],lab,cap)
print('\nbest:',best)
