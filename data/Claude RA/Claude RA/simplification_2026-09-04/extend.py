import sys, os, io, contextlib
os.chdir("/sessions/rcw-01xbsq1sgk1kphgfxvqjpnj7/mnt/Recession Papers/Claude RA/paper2_exploration_2026-09-03/ladder")
sys.path.insert(0,os.getcwd())
buf=io.StringIO()
with contextlib.redirect_stdout(buf):
    exec(open("stage46_v7.py").read().split('print("\\n=== (b) END')[0])
import numpy as np, pandas as pd
def replay_from(trig, START, endpct=0.03):
    eps=[]; open_=False; i=0
    while i<N:
        if not open_:
            if trig[i] and cal[i]>=pd.Timestamp(START): open_=True; start=i; runmax=-1; pk=None; endcall=None
            i+=1; continue
        v=ma8d[i]
        if not np.isnan(v):
            if v>runmax: runmax=v; pk=i; endcall=None
        ok=(not np.isnan(v)) and pk is not None and v<=runmax*(1-endpct)
        if ok and endcall is None: endcall=i
        if endcall is not None and B3[i] and CALM[i]:
            eps.append(dict(onset=cal[start],trough_week=cal[pk],end_call=cal[endcall],close=cal[i])); open_=False
        i+=1
    if open_: eps.append(dict(onset=cal[start],trough_week=cal[pk] if pk else None,end_call=cal[endcall] if endcall else None,close=None))
    return eps
CAND={
 "O  Sahm + IUR + housing + payrolls":
   ([SAHM[0.35], gapch(iur4,0.40), persist2(h3,20), PAY], ["Sahm>=0.55 x1 [nogate]","IUR gap>=0.5 [nogate]"], []),
 "M  O + 6-month bill":
   ([SAHM[0.35], gapch(iur4,0.40), fall(tb6,60,1.43), persist2(h3,20), PAY], ["Sahm>=0.55 x1 [nogate]","IUR gap>=0.5 [nogate]"], []),
 "v7.2 (for reference)":
   ([SAHM[0.35], gapch(iur4,0.40), PAY, persist2(h3,20), fall(tb6,60,1.43)], ["Sahm>=0.55 x1 [nogate]","IUR gap>=0.5 [nogate]","claims 8wk>=40% [nogate]","IP 3m first print <=-2.0% x2 [nogate]"], LANE2),
}
print("calendar available:", cal[0].date(), "->", cal[-1].date())
for START in ("1968-06-01","1962-01-01"):
    print(f"\n########## scoring floor {START} ##########")
    for name,(fast,bsl,lane) in CAND.items():
        trig,lfa=build(fast,bsl,lane if lane else [])
        eps=replay_from(trig,START)
        r,f=score_eps(eps,T_P1)
        lags=[x["lag"] for x in r]
        print(f"{name}")
        print(f"   episodes {len(eps)} | detected {len(r)}/9 | FALSE {f} | lane voided {len(lfa)}")
        print(f"   onset lags {lags} worst {max(abs(v) for v in lags)} | ends {[x['end_lag'] for x in r]} | troughs {[x['tr_err'] for x in r]}")
        extra=[]
        pass
