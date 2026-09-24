"""Stage 154: a causal rule that survives its own misses.  Stage 150 failed because a machine
running in real time has no list of which past days were quiet, so the readings of a recession it
missed entered its own calibration and silenced it for fifty years.  Two repairs are tried: a
high quantile instead of a record, so no single observation can set the line; and a cordon --
readings above the current line, and everything for some months afterwards, are refused entry to
the sample.  Nothing here looks forward."""
exec(open("stage128_ztwolane.py").read().split("def machine(c,c2")[0])
import numpy as np, pandas as pd
CH4=["Sahm","payrolls","housing","bill"]
X={n:np.asarray(CH[n],float) for n in CH4}
XS=np.asarray(CH["Sahm"],float)
IURh=np.asarray(gapch(iur4,0.40),bool)
LANE=np.asarray(lane_arr(vix-vix.shift(20),1,22.0),bool)
i0=int(np.searchsorted(cal,pd.Timestamp("1968-06-01")))
def causal(q=0.98,delta=1.0,delta2=2.0,warm_yr=5,cordon_m=18,refresh=28,use_iur=True):
    samp={n:[] for n in CH4}; sampS=[]
    lines={n:np.inf for n in CH4}; lineS=np.inf
    cord={n:-10**9 for n in CH4}; cordS=-10**9
    eps=[]; open_=False; last=-10**9; cd=int(cordon_m*30.4)
    for i in range(N):
        if open_:
            v=ma8d[i]
            if not np.isnan(v):
                if v>runmax: runmax=v; pk=i; endcall=None
            ok=(not np.isnan(v)) and pk is not None and v<=runmax*(1-0.03)
            if ok and endcall is None: endcall=i
            if endcall is not None and B3[i] and CALM[i]:
                eps.append(dict(onset=cal[start],trough_week=cal[pk],end_call=cal[endcall],close=cal[i]))
                open_=False
                for n in CH4: cord[n]=max(cord[n],i+cd)
                cordS=max(cordS,i+cd)
            continue
        if i-last>=refresh:
            last=i
            for n in CH4:
                a=np.asarray(samp[n])
                if len(a)>=warm_yr*250:
                    med=np.median(a); mad=np.median(np.abs(a-med))*1.4826
                    if mad>0: lines[n]=float(np.quantile(a,q)+delta*mad)
            a=np.asarray(sampS)
            if len(a)>=warm_yr*250:
                med=np.median(a); mad=np.median(np.abs(a-med))*1.4826
                if mad>0: lineS=float(np.quantile(a,q)+delta2*mad)
        hit=False
        if i>=i0:
            if G[i] and CO[i]:
                for n in CH4:
                    x=X[n][i]
                    if np.isfinite(x) and x>=lines[n]: hit=True; break
                if (not hit) and use_iur and IURh[i]: hit=True
            if (not hit) and (not G[i]) and CCO[i] and np.isfinite(XS[i]) and XS[i]>=lineS: hit=True
        if hit:
            open_=True; start=i; runmax=-1; pk=None; endcall=None
            continue
        for n in CH4:
            x=X[n][i]
            if not np.isfinite(x): continue
            if x>=lines[n]: cord[n]=max(cord[n],i+cd); continue
            if i<cord[n]: continue
            if G[i] and CO[i]: samp[n].append(x)
        if np.isfinite(XS[i]):
            if XS[i]>=lineS: cordS=max(cordS,i+cd)
            elif i>=cordS and (not G[i]) and CCO[i]: sampS.append(XS[i])
    if open_: eps.append(dict(onset=cal[start],trough_week=cal[pk] if pk else None,end_call=cal[endcall] if endcall else None,close=None))
    return eps
print("%-6s %-7s %-8s %-6s %-8s %-7s %s"%("q","delta","cordon","det","false","warm","lags from the NBER peak month"))
best=[]
for q in [0.95,0.98,0.99]:
  for delta in [0.0,1.0,2.0]:
    for cordon in [0,24]:
      eps=causal(q=q,delta=delta,cordon_m=cordon)
      res,f=score_eps(eps,T_P1); det=sum(1 for x in res if x["lag"] is not None)
      if True:
          print("%-6.3f %-7.2f %-8d %-6s %-8d %-7d %s"%(q,delta,cordon,"%d/9"%det,len(f) if f else 0,5,[r["lag"] for r in res]))
          if det==9 and not f: best.append((q,delta,cordon,[r["lag"] for r in res],eps))
if best:
    print("\ncausal settings that detect nine of nine with no false alarm:")
    for q,delta,cordon,lags,eps in best:
        d=[(e["onset"]-FIRST[i]).days for i,e in enumerate(eps)][:9]
        print("  q=%.3f delta=%.2f cordon=%d months | lags %s | days %s"%(q,delta,cordon,lags,d))
else:
    print("\nno causal setting reaches nine of nine with no false alarm")
