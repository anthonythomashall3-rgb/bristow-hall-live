"""Stage 153: who carries each recession, and what happens if a series disappears.  A rule that
is to run forever must survive the discontinuation of any one of its inputs.  For each episode
this stage reports which channels were on when the call was made, and then deletes each channel
in turn and replays the whole record."""
exec(open("stage128_ztwolane.py").read().split("def machine(c,c2")[0])
import numpy as np, pandas as pd
CH4=["Sahm","payrolls","housing","bill"]
LIN={"Sahm":0.35804,"payrolls":0.10610,"housing":0.14924,"bill":1.44378}
def chan_hits(names):
    out={}
    for n in names:
        if n=="IUR": out[n]=np.asarray(gapch(iur4,0.40),bool)
        else:
            x=np.asarray(CH[n],float); out[n]=np.where(np.isfinite(x),x,-9e9)>=LIN[n]
    return out
ALLN=CH4+["IUR"]
H=chan_hits(ALLN)
def build(names):
    hits=np.zeros(N,bool)
    for n in names: hits|=H[n]
    fr=fresh(hits&CO,120)&G
    xs=np.asarray(CH["Sahm"],float)
    fr=fr|fresh((np.where(np.isfinite(xs),xs,-9e9)>=0.55)&CCO&NG,120)
    la=fresh(np.asarray(lane_arr(vix-vix.shift(20),1,22.0),bool),120); valid=la.copy()
    for i in np.flatnonzero(np.diff(la.astype(np.int8))==1)+1:
        if not fr[i:i+121].any():
            j=i
            while j<N and la[j]: valid[j]=False; j+=1
    eps=replay(fr|valid); res,f=score_eps(eps,T_P1)
    det=sum(1 for x in res if x["lag"] is not None)
    dd=None
    if det==9:
        call={r["peak"]:r["onset"] for r in res}
        dd=[(pd.Timestamp(call[p])-FIRST[j]).days for j,(p,t) in enumerate(T_P1)]
    return det,f,dd,[r["lag"] for r in res],eps
det,f,dd,lags,eps=build(ALLN)
print("v14: %d/9, %d false, days %s"%(det,len(f) if f else 0,dd))
print("\nwhich channels were on, and by how much, on the day of each call")
print("%-12s %s"%("call"," ".join("%-22s"%n for n in ALLN)))
for e in eps:
    i=int(np.searchsorted(cal,e["onset"])); row=[]
    for n in ALLN:
        if n=="IUR":
            row.append("on" if H[n][i] else "-")
        else:
            x=np.asarray(CH[n],float)[i]
            row.append(("ON  %+.3f over"%(x-LIN[n])) if H[n][i] else ("    %+.3f"%(x-LIN[n]) if np.isfinite(x) else "  n/a"))
    print("%-12s %s"%(str(e["onset"].date())," ".join("%-22s"%c for c in row)))
print("\nremoving one channel at a time")
print("%-30s %-7s %-7s %s"%("instrument","det","false","days from the first day"))
for drop in [None]+ALLN:
    names=[n for n in ALLN if n!=drop]
    d2,f2,dd2,lg2,_=build(names)
    print("%-30s %-7s %-7d %s"%("all five" if drop is None else "without "+drop,"%d/9"%d2,len(f2) if f2 else 0,dd2))
print("\nremoving two at a time (the pairs that still work)")
import itertools
for a,b in itertools.combinations(ALLN,2):
    names=[n for n in ALLN if n not in (a,b)]
    d2,f2,dd2,lg2,_=build(names)
    if d2==9 and not f2:
        print("  without %s and %s: 9/9, no false alarm, days %s"%(a,b,dd2))
