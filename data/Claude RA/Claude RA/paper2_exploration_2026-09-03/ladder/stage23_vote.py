"""Stage 23: k-of-N vote. Loosen every channel, require at least k channels on (each fresh within 120 days) at the same time
(a channel counts as 'on' for a window after its release: monthly 45 days, weekly 21 days). Purpose: widen per-channel margins
without losing speed. Scored like the state machine (same end/close rules), zero false episodes required."""
exec(open("stage19b_iur.py").read().split("base=[SAHM[0.35]")[0])
import itertools
def hold(a, days):
    """extend each True by `days` days (a release stays 'on' for its window)"""
    out=a.copy(); idx=np.flatnonzero(a)
    for i in idx: out[i:i+days]=True
    return out
def edge_hold(a, days):
    """only the onset edges are held: True where the channel turned on within the last `days` days"""
    d=np.diff(a.astype(np.int8), prepend=0); starts=np.flatnonzero(d==1); out=np.zeros(N,bool)
    for i in starts: out[i:i+days]=True
    return out
# loose channel menu
LO={}
for th in [0.25,0.30,0.35]: LO[f"sahm{th}"]=SAHM[th] if th in SAHM else D(Srel>=th-1e-9)
for g in [0.20,0.25,0.30,0.40]: LO[f"iur{g}"]=gapch(iur4,g)
for p in [0.15,0.20,0.25,0.30]: LO[f"ic{p}"]=IC[f"ic8_{int(p*100)}_k1"] if f"ic8_{int(p*100)}_k1" in IC else wk(r8>=p)
LO["pay0.05"]=D(pd.Series((pay.d1.astype(float)<=-0.05).values, index=pd.to_datetime(pay.rel.values))); LO["pay0.1"]=PAY
for x in [6,8,10]: LO[f"sent{x}"]=UM[f"um_d1_{x}"]
for x in [15,20]: LO[f"hou{x}"]=persist2(h3,x); LO[f"hou{x}_k1"]=D(h3<=-x/100)
def vote_trigger(names, k, mwin=45, wwin=21):
    cnt=np.zeros(N,int)
    for n in names:
        a=LO[n]; w=wwin if n.startswith(("iur","ic")) else mwin
        cnt+=hold(fresh(a,120), w).astype(int)
    return cnt>=k
def replay_trig(trig):
    """state machine with a precomputed trigger array (same end/close as replay3)"""
    trig=trig&GATE[12]; eps=[]; open_=False; i=0
    while i<N:
        if not open_:
            if trig[i] and cal[i]>=pd.Timestamp("1968-06-01"): open_=True; start=i; runmax=-1; pk=None; endcall=None
            i+=1; continue
        v=ma8d[i]
        if not np.isnan(v):
            if v>runmax: runmax=v; pk=i; endcall=None
            elif endcall is None and v<=runmax*0.97: endcall=i
        if endcall is not None and B3[i] and CALM[i]:
            eps.append(dict(onset=cal[start], trough_week=cal[pk], end_call=cal[endcall], close=cal[i])); open_=False
        i+=1
    if open_: eps.append(dict(onset=cal[start], trough_week=cal[pk] if pk else None, end_call=cal[endcall] if endcall else None, close=None))
    return eps
rows=[]
menus={
 "A: sahm.30 iur.25 ic.20 pay.05 sent8 hou15": ["sahm0.3","iur0.25","ic0.2","pay0.05","sent8","hou15"],
 "B: sahm.30 iur.30 ic.25 pay.05 sent8 hou15": ["sahm0.3","iur0.3","ic0.25","pay0.05","sent8","hou15"],
 "C: sahm.25 iur.20 ic.15 pay.05 sent6 hou15_k1": ["sahm0.25","iur0.2","ic0.15","pay0.05","sent6","hou15_k1"],
 "D: sahm.30 iur.25 ic.20 sent8 hou15 (no pay)": ["sahm0.3","iur0.25","ic0.2","sent8","hou15"],
 "E: sahm.35 iur.30 ic.30 pay.1 sent10 hou20 (v-tight)": ["sahm0.35","iur0.3","ic0.3","pay0.1","sent10","hou20"],
 "F: sahm.30 iur.25 ic.20 pay.05 sent8 hou15 + iur.40 solo": None,
}
for nm,names in menus.items():
    if names is None: continue
    for k in [1,2,3]:
        for mw,ww in [(45,21),(60,28),(90,42)]:
            eps=replay_trig(vote_trigger(names,k,mw,ww)); res,false=score_eps(eps,T_P1); L=[r["lag"] for r in res]
            rows.append(dict(menu=nm, k=k, mwin=mw, wwin=ww, n_false=len(false), false=false[:3], lags=L, out1=sum(1 for l in L if l is None or abs(l)>1), out2=sum(1 for l in L if l is None or abs(l)>2), onsets=[r["onset"] for r in res]))
df=pd.DataFrame(rows); pd.set_option("display.width",340); pd.set_option("display.max_colwidth",120); pd.set_option("display.max_rows",200)
print(df.sort_values(["n_false","out1","out2"]).drop(columns=["onsets"]).head(30).to_string())
best=df[df.n_false==0].sort_values(["out1","out2"]).head(5)
for _,r in best.iterrows(): print("\n", r.menu, "k=",r.k, r.mwin, r.wwin, "lags", r.lags, "onsets", r.onsets)
# hybrid: v3 solo channels (Sahm .35, IUR .40) OR a 2-of-6 vote on the loose menu
print("\nHYBRID: v3 (Sahm.35 | IUR.40 | pay.1 | sent10 | hou20) OR 2-of-N loose vote")
for nm,names in menus.items():
    if names is None: continue
    for mw,ww in [(45,21),(60,28)]:
        v3=np.zeros(N,bool)
        for a in [SAHM[0.35], gapch(iur4,0.40), PAY, UM["um_d1_10"], persist2(h3,20)]: v3|=fresh(a,120)
        trig=v3|vote_trigger(names,2,mw,ww)
        eps=replay_trig(trig); res,false=score_eps(eps,T_P1); L=[r["lag"] for r in res]
        print(f"  {nm} win {mw}/{ww}: false {len(false)} {false[:3]} lags {L} out1 {sum(1 for l in L if l is None or abs(l)>1)} onsets {[r['onset'] for r in res]}")
