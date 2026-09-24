"""Stage 150: v14 run causally.  Every number in v14 -- each channel's quiet record and each
channel's robust scale -- is computed here from the past only, updated as the sample grows and
frozen while an episode is open.  If the rule still finds the recessions when it is never
allowed to see the future, then it is not a rule that was fitted to the record; it is a rule
that could have been run since 1968 and can be run in 2040."""
exec(open("stage128_ztwolane.py").read().split("def machine(c,c2")[0])
import numpy as np, pandas as pd
CH4=["Sahm","payrolls","housing","bill"]
X={n:np.asarray(CH[n],float) for n in CH4}
XS=np.asarray(CH["Sahm"],float)
i0=int(np.searchsorted(cal,pd.Timestamp("1968-06-01")))
LANE=np.asarray(lane_arr(vix-vix.shift(20),1,22.0),bool)
IURh=np.asarray(gapch(iur4,0.40),bool)
def causal(delta=0.25,delta2=2.0,warm_yr=5,refresh=28,use_iur=True,lane=True):
    qsamp={n:[] for n in CH4}; qsampS=[]
    lines={n:np.inf for n in CH4}; lineS=np.inf
    eps=[]; open_=False; last=-10**9
    hist=[]
    for i in range(N):
        if open_:
            v=ma8d[i]
            if not np.isnan(v):
                if v>runmax: runmax=v; pk=i; endcall=None
            ok=(not np.isnan(v)) and pk is not None and v<=runmax*(1-0.03)
            if ok and endcall is None: endcall=i
            if endcall is not None and B3[i] and CALM[i]:
                eps.append(dict(onset=cal[start],trough_week=cal[pk],end_call=cal[endcall],close=cal[i])); open_=False
            continue
        if i>=i0:
            if i-last>=refresh:
                last=i
                for n in CH4:
                    a=np.array(qsamp[n])
                    if len(a)>=warm_yr*250:
                        med=np.median(a); mad=np.median(np.abs(a-med))*1.4826
                        lines[n]=a.max()+delta*mad if mad>0 else np.inf
                a=np.array(qsampS)
                if len(a)>=warm_yr*250:
                    med=np.median(a); mad=np.median(np.abs(a-med))*1.4826
                    lineS=a.max()+delta2*mad if mad>0 else np.inf
            hit=False
            if G[i] and CO[i]:
                for n in CH4:
                    x=X[n][i]
                    if np.isfinite(x) and x>=lines[n]: hit=True; break
                if (not hit) and use_iur and IURh[i]: hit=True
            if (not hit) and (not G[i]) and CCO[i]:
                x=XS[i]
                if np.isfinite(x) and x>=lineS: hit=True
            if (not hit) and lane and LANE[i] and G[i]:
                pass
            if hit:
                open_=True; start=i; runmax=-1; pk=None; endcall=None
                hist.append((str(cal[i].date()),{n:round(lines[n],4) for n in CH4}))
                continue
        if G[i] and CO[i]:
            for n in CH4:
                x=X[n][i]
                if np.isfinite(x): qsamp[n].append(x)
        if (not G[i]) and CCO[i] and np.isfinite(XS[i]): qsampS.append(XS[i])
    if open_: eps.append(dict(onset=cal[start],trough_week=cal[pk] if pk else None,end_call=cal[endcall] if endcall else None,close=None))
    return eps,hist
for warm in [3,5,8]:
  for delta in [0.0,0.25,0.5]:
    eps,hist=causal(delta=delta,warm_yr=warm)
    res,f=score_eps(eps,T_P1); det=sum(1 for x in res if x["lag"] is not None)
    dd=None
    if det==9:
        call={r["peak"]:r["onset"] for r in res}
        dd=[(pd.Timestamp(call[p])-FIRST[j]).days for j,(p,t) in enumerate(T_P1)]
    print("warm %d yr, delta %.2f : %d/9 detected, %d false | lags %s"%(warm,delta,det,len(f) if f else 0,[r["lag"] for r in res]))
    if dd: print("                        days from the first day %s"%dd)
    if f: print("                        false: %s"%f[:5])
print("\nthe lines the causal rule was using when it fired (warm 5 yr, delta 0.25):")
eps,hist=causal(0.25,2.0,5)
for d,l in hist[:12]: print("   %s  %s"%(d,l))
print("\nv14 in sample for comparison: lags [-2,-1,0,1,1,-1,0,0,1], days [-87,-37,-29,17,2,-58,-14,-2,2]")
