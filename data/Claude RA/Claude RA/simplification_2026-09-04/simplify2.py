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
 "F  Sahm + IUR + 6-month bill (gated) | Sahm 0.55, IUR 0.50 (ungated)":
   ([SAHM[0.35], gapch(iur4,0.40), fall(tb6,60,1.43)], ["Sahm>=0.55 x1 [nogate]","IUR gap>=0.5 [nogate]"], []),
 "G  F + live lane":
   ([SAHM[0.35], gapch(iur4,0.40), fall(tb6,60,1.43)], ["Sahm>=0.55 x1 [nogate]","IUR gap>=0.5 [nogate]"], LANE2),
 "H  Sahm + IUR + bill, no ungated clauses at all":
   ([SAHM[0.35], gapch(iur4,0.40), fall(tb6,60,1.43)], [], []),
 "I  Sahm + bill only":
   ([SAHM[0.35], fall(tb6,60,1.43)], ["Sahm>=0.55 x1 [nogate]"], []),
}
for name,(fast,bsl,lane) in CAND.items():
    trig,lfa=build(fast,bsl,lane if lane else [])
    eps=replay(trig)
    r,f=score_eps(eps,T_P1)
    lags=[x[chr(39)+"lag"+chr(39)] if False else x["lag"] for x in r]
    el=[x["end_lag"] for x in r]; tr=[x["tr_err"] for x in r]
    print(f"\n{name}")
    print(f"   detected {len(r)}/9  false {f}  voided lane {len(lfa)}")
    print(f"   onset lags {lags}  max|lag| {max(abs(v) for v in lags) if lags else chr(45)}")
    print(f"   end lags   {el}")
    print(f"   trough err {tr}")

