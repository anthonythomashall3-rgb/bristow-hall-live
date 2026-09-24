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
 "J  Sahm + IUR + bill + housing":
   ([SAHM[0.35], gapch(iur4,0.40), fall(tb6,60,1.43), persist2(h3,20)], ["Sahm>=0.55 x1 [nogate]","IUR gap>=0.5 [nogate]"], []),
 "K  Sahm + IUR + bill + payrolls":
   ([SAHM[0.35], gapch(iur4,0.40), fall(tb6,60,1.43), PAY], ["Sahm>=0.55 x1 [nogate]","IUR gap>=0.5 [nogate]"], []),
 "L  Sahm + IUR + housing (no bill)":
   ([SAHM[0.35], gapch(iur4,0.40), persist2(h3,20)], ["Sahm>=0.55 x1 [nogate]","IUR gap>=0.5 [nogate]"], []),
 "M  Sahm + IUR + bill + housing + payrolls  (= v7 minus claims and IP backstops)":
   ([SAHM[0.35], gapch(iur4,0.40), fall(tb6,60,1.43), persist2(h3,20), PAY], ["Sahm>=0.55 x1 [nogate]","IUR gap>=0.5 [nogate]"], []),
 "N  J + live lane":
   ([SAHM[0.35], gapch(iur4,0.40), fall(tb6,60,1.43), persist2(h3,20)], ["Sahm>=0.55 x1 [nogate]","IUR gap>=0.5 [nogate]"], LANE2),
}
for name,(fast,bsl,lane) in CAND.items():
    trig,lfa=build(fast,bsl,lane if lane else [])
    eps=replay(trig); r,f=score_eps(eps,T_P1)
    lags=[x["lag"] for x in r]; el=[x["end_lag"] for x in r]; tr=[x["tr_err"] for x in r]
    print(f"\n{name}")
    print(f"   detected {len(r)}/9  false {f}  voided lane {len(lfa)}")
    print(f"   onset lags {lags}  max|lag| {max(abs(v) for v in lags)}")
    print(f"   end lags   {el}   trough err {tr}")
    print("   onset dates", [x["onset"] for x in r])

