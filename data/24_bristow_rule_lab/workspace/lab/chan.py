import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
bench.ABSTAIN=True
TRADE={'exports','imports'}; CARS={'car registrations'}; U={'unemployment'}
CONS={'construction production','construction output'}
GB={'capital goods production','intermediate goods production','consumer durables production'}
RS={'monthly reference GDP'}
V={
 'A  current (no trade, cars, unemployment)': (TRADE|CARS|U, set(), set()),
 'B  + unemployment':                          (TRADE|CARS,    set(), set()),
 'C  + unemployment + cars':                   (TRADE,         set(), set()),
 'D  everything':                              (set(),         set(), set()),
 'E  unemployment at the peak only':           (TRADE|CARS,    set(), U),
 'F  unemployment at the trough only':         (TRADE|CARS,    U,     set()),
 'G  A minus construction':                    (TRADE|CARS|U|CONS, set(), set()),
 'H  A minus goods breakdown':                 (TRADE|CARS|U|GB, set(), set()),
 'I  A minus reference GDP':                   (TRADE|CARS|U|RS, set(), set()),
 'J  core only (production, employment, sales, GDP)': (TRADE|CARS|U|CONS|GB, set(), set()),
}
print(f'{"channel set":52s} {"peak":>9s} {"trough":>9s}  sum')
for lab,(sk,sp,st) in V.items():
    bench.SKIP=sk; bench.SKIP_PEAK=sp; bench.SKIP_TROUGH=st
    tot=[]
    for c in ALL: tot+=run_country_concept(c,min_depth=5.0,lam=500000.)
    s=score(tot,'',show=False)
    print(f'{lab:52s} {s["hp"]:4d}/{s["n"]:<4d} {s["ht"]:4d}/{s["n"]:<4d}  {s["hp"]+s["ht"]}')
