import os, time
os.chdir("/sessions/rcw-01xbsq1sgk1kphgfxvqjpnj7/mnt/Recession Papers/Claude RA/paper2_exploration_2026-09-03/ladder")
import sys; sys.path.insert(0,"/sessions/rcw-01xbsq1sgk1kphgfxvqjpnj7/mnt/Recession Papers/Claude RA/paper2_exploration_2026-09-03/ladder")
t=time.time()
exec(open("stage46_v7.py").read().split('print("\\n=== (b) END')[0])
pass
import numpy as np
G=np.asarray(GATE[12],bool); NG=~G
def nogate(nm):
    a=np.asarray(BS[nm],bool); return a&NG
CAND={
 "O  Sahm + IUR + housing + payrolls (no bill)":
   ([SAHM[0.35], gapch(iur4,0.40), persist2(h3,20), PAY], ["Sahm>=0.55 x1 [nogate]","IUR gap>=0.5 [nogate]"], []),
 "P  Sahm + IUR + payrolls":
   ([SAHM[0.35], gapch(iur4,0.40), PAY], ["Sahm>=0.55 x1 [nogate]","IUR gap>=0.5 [nogate]"], []),
 "M  Sahm + IUR + bill + housing + payrolls":
   ([SAHM[0.35], gapch(iur4,0.40), fall(tb6,60,1.43), persist2(h3,20), PAY], ["Sahm>=0.55 x1 [nogate]","IUR gap>=0.5 [nogate]"], []),
}
for name,(fast,bsl,lane) in CAND.items():
    trig,lfa=build(fast,bsl,lane if lane else [])
    eps=replay(trig); r,f=score_eps(eps,T_P1)
    lags=[x["lag"] for x in r]
    print(f"\n{name}")
    print(f"   detected {len(r)}/9 false {f} | lags {lags} max|lag| {max(abs(v) for v in lags)}")
    print(f"   episodes {len(eps)} (9 recessions + {len(eps)-9} extra)")
    for e in eps:
        wd = e.get("withdrawn", None)
        print(f"     onset {e[chr(39)+chr(39)] if False else e['onset'].date()} peak-week {e['trough_week'].date()} end {e['end_call'].date()}"
              + (f" withdrawn {wd}" if wd else ""))

