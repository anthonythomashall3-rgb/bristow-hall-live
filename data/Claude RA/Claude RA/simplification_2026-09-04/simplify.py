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
 "A  Sahm only (0.35 gated | 0.55 ungated)":
   ([SAHM[0.35]], ["Sahm>=0.55 x1 [nogate]"], []),
 "B  Sahm + IUR  (0.35/0.40 gated | 0.55/0.50 ungated)":
   ([SAHM[0.35], gapch(iur4,0.40)], ["Sahm>=0.55 x1 [nogate]","IUR gap>=0.5 [nogate]"], []),
 "C  B + claims 8wk backstop":
   ([SAHM[0.35], gapch(iur4,0.40)], ["Sahm>=0.55 x1 [nogate]","IUR gap>=0.5 [nogate]","claims 8wk>=40% [nogate]"], []),
 "D  B + live lane":
   ([SAHM[0.35], gapch(iur4,0.40)], ["Sahm>=0.55 x1 [nogate]","IUR gap>=0.5 [nogate]"], LANE2),
 "E  C + live lane":
   ([SAHM[0.35], gapch(iur4,0.40)], ["Sahm>=0.55 x1 [nogate]","IUR gap>=0.5 [nogate]","claims 8wk>=40% [nogate]"], LANE2),
}
for name,(fast,bsl,lane) in CAND.items():
    trig,lfa=build(fast,bsl,lane if lane else [])
    eps=replay(trig)
    r,f=score_eps(eps,T_P1)
    lags=[x['lag'] for x in r]; el=[x['end_lag'] for x in r]; tr=[x['tr_err'] for x in r]
    print(f"\n{name}")
    print(f"   detected {len(r)}/9  false {f}  voided lane {len(lfa)}")
    print(f"   onset lags {lags}  max|lag| {max(abs(v) for v in lags) if lags else '-'}")
    print(f"   end lags   {el}")
    print(f"   trough err {tr}")
