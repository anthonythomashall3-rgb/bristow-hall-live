"""Stage 121: the running record, but with a memory.  A record set in 1982 should not set the
bar for 2008, and a rule meant to run forever cannot let one violent decade silence it for
the next fifty years.  The record is therefore the largest quiet reading of the last L years
rather than of all history.  L and the multiplier m are the only two numbers in the machine."""
exec(open("stage118_agree.py").read().split('FIRST=[pd.Timestamp')[0])
import numpy as np, pandas as pd
from collections import deque
CORE=["Sahm","IUR","payrolls","housing","bill"]
FIRST=[pd.Timestamp(x) for x in ["1970-01-01","1973-12-01","1980-02-01","1981-08-01","1990-08-01",
                                 "2001-04-01","2008-01-01","2020-03-01","2024-05-01"]]
i0=int(np.searchsorted(cal,pd.Timestamp("1968-06-01")))
LANE=np.asarray(lane_arr(vix-vix.shift(20),1,22.0),bool)
def run(names,m,L_years,warm_yr=5,lane=True,clause_m=None):
    X=np.vstack([np.asarray(CH[n],float) for n in names]); nch=len(names)
    L=int(L_years*365.25) if L_years else 10**9
    dq=[deque() for _ in range(nch)]          # (index, value), decreasing values
    cnt=np.zeros(nch,int); first_seen=np.full(nch,-1,int)
    Sr=np.asarray(CH["Sahm"],float); dqs=deque(); cnt_s=0; first_s=-1
    warm=int(warm_yr*365.25)
    eps=[]; open_=False; trig=np.zeros(N,bool); lane_used=[]
    for i in range(N):
        x=X[:,i]; ok=np.isfinite(x)
        for j in range(nch):
            while dq[j] and dq[j][0][0] < i-L: dq[j].popleft()
        while dqs and dqs[0][0] < i-L: dqs.popleft()
        if open_:
            v=ma8d[i]
            if not np.isnan(v):
                if v>runmax: runmax=v; pk=i; endcall=None
            okend=(not np.isnan(v)) and pk is not None and v<=runmax*(1-0.03)
            if okend and endcall is None: endcall=i
            if endcall is not None and B3[i] and CALM[i]:
                eps.append(dict(onset=cal[start],trough_week=cal[pk],end_call=cal[endcall],close=cal[i])); open_=False
            continue
        hit=False
        if i>=i0:
            if G[i] and CO[i]:
                for j in range(nch):
                    if not ok[j] or not dq[j]: continue
                    if first_seen[j]<0 or i-first_seen[j]<warm: continue
                    if x[j] >= m*dq[j][0][1]: hit=True; break
            if (not hit) and clause_m is not None and CCO[i] and (not G[i]) and dqs and np.isfinite(Sr[i]):
                if first_s>=0 and i-first_s>=warm and Sr[i]>=clause_m*dqs[0][1]: hit=True
            if (not hit) and lane and LANE[i] and G[i]:
                hit="lane"
        if hit:
            trig[i]=True; open_=True; start=i; runmax=-1; pk=None; endcall=None
            if hit=="lane": lane_used.append(str(cal[i].date()))
            continue
        for j in range(nch):
            if not ok[j]: continue
            if first_seen[j]<0: first_seen[j]=i
            while dq[j] and dq[j][-1][1]<=x[j]: dq[j].pop()
            dq[j].append((i,x[j])); cnt[j]+=1
        if np.isfinite(Sr[i]):
            if first_s<0: first_s=i
            while dqs and dqs[-1][1]<=Sr[i]: dqs.pop()
            dqs.append((i,Sr[i]))
    if open_: eps.append(dict(onset=cal[start],trough_week=cal[pk] if pk else None,
                              end_call=cal[endcall] if endcall else None,close=None))
    return eps,lane_used
print("%-5s %-6s %-6s %-6s %-6s %-5s %s"%("m","L(yr)","lane","det","false","inwk","days from the first day"))
rows=[]
for lane in [False,True]:
  for L in [5,8,10,12,15,20,25,None]:
    for m in [0.90,0.95,1.00,1.05,1.10,1.15,1.20,1.30]:
        eps,lu=run(CORE,m,L,lane=lane)
        res,f=score_eps(eps,T_P1); det=sum(1 for x in res if x["lag"] is not None)
        dd=None
        if det==9:
            call={r["peak"]:r["onset"] for r in res}
            dd=[(pd.Timestamp(call[p])-FIRST[j]).days for j,(p,t) in enumerate(T_P1)]
        if det==9 and not f:
            rows.append(dict(m=m,L=L,lane=lane,inwk=sum(1 for x in dd if abs(x)<=7),
                             mad=round(float(np.mean([abs(x) for x in dd])),1),
                             mx=max(dd),dd=dd))
        print("%-5.2f %-6s %-6s %-6s %-6d %-5s %s"%(m,L,lane,"%d/9"%det,len(f) if f else 0,
              (sum(1 for x in dd if abs(x)<=7) if dd else "-"),(dd if dd else "")))
d=pd.DataFrame(rows)
if len(d):
    print("\nzero false, nine of nine, ranked by mean absolute distance from the first day:")
    print(d.sort_values(["mad"]).head(20).to_string(index=False))
    d.to_csv("/root/out/stage121_rolling.csv",index=False)
