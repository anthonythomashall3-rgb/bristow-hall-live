import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
bench.ABSTAIN=True
TRADE={'exports','imports'}; CARS={'car registrations'}; U={'unemployment'}
CONS={'construction production','construction output'}
GB={'capital goods production','intermediate goods production','consumer durables production'}
RS={'monthly reference GDP'}; MFG={'manufacturing production','durable manufacturing'}
V={
 'J   core only':                                   (TRADE|CARS|U|CONS|GB, set(), set()),
 'J+  core, unemployment at the peak only':         (TRADE|CARS|CONS|GB, set(), U),
 'J+t core, unemployment at the trough only':       (TRADE|CARS|CONS|GB, U, set()),
 'J-  core minus manufacturing duplicates':         (TRADE|CARS|U|CONS|GB|MFG, set(), set()),
 'J-+ that, unemployment at the peak only':         (TRADE|CARS|CONS|GB|MFG, set(), U),
 'K   core + construction at the peak only':        (TRADE|CARS|U|GB, CONS, set()),
 'L   core + goods breakdown at the peak only':     (TRADE|CARS|U|CONS, GB, set()),
 'M   core, exports at the peak only':              (CARS|U|CONS|GB|{'imports'}, {'exports'}, set()),
}
print(f'{"channel set":50s} {"peak":>9s} {"trough":>9s}  sum')
best=None
for lab,(sk,sp,st) in V.items():
    bench.SKIP=sk; bench.SKIP_PEAK=sp; bench.SKIP_TROUGH=st
    tot=[]
    for c in ALL: tot+=run_country_concept(c,min_depth=5.0,lam=500000.)
    s=score(tot,'',show=False)
    print(f'{lab:50s} {s["hp"]:4d}/{s["n"]:<4d} {s["ht"]:4d}/{s["n"]:<4d}  {s["hp"]+s["ht"]}')
