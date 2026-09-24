"""Stage 65: drive the false-alarm hazard to its floor.
(a) joint deletion of channels that carry nothing; (b) tighten every surviving
threshold to its breaking point; (c) freshness window; (d) persistence.
Constraints: the nine onset lags must stay [-2,-1,0,1,1,-1,1,0,1], zero false
episodes on the record, and nine of nine in the no-inversion world."""
exec(open("stage46_v7.py").read().split("t6,l6=build")[0])
import numpy as np, pandas as pd, itertools
G=np.asarray(GATE[12],bool); NG=~G
ip3c=fpch3("INDPRO_all_vintages.csv")
BASE=[-2,-1,0,1,1,-1,1,0,1]
def A(x): return np.asarray(x,bool)
def PAYc(x): return A(D(pd.Series((pay.d1.astype(float)<=-x*100).values, index=pd.to_datetime(pay.rel.values))))
def per(arr,k):
    a=A(arr)
    if k<=1: return a
    out=a.copy()
    for j in range(1,k): out &= np.concatenate([np.zeros(j,bool), a[:-j]])
    return out

def pieces(p):
    fast={"sahm":A(SAHM[p["sahm"]]) if p["sahm"] in SAHM else A(D(Srel>=p["sahm"]-1e-9)),
          "iur": A(gapch(iur4,p["iur"])), "pay": PAYc(p["pay"]),
          "hou": A(persist2(h3,p["hou"])), "bill":A(fall(tb6,60,p["bill"]))}
    clause={"sahmC":A(D(Srel>=p["sahmC"]-1e-9)), "iurC":A(gapch(iur4,p["iurC"])),
            "houC": A(persist2(h3,p["houC"]))}
    ung={"claims":A(wk(r8>=p["claims"])),
         "ip":    A(D((ip3c<=-p["ip"])&(ip3c.shift(1)<=-p["ip"])))}
    lane={"vix":A(lane_arr(vix-vix.shift(20),1,p["vix"])),
          "baa":A(lane_arr(baa-baa.rolling(250).min(),1,p["baa"]))}
    return fast,clause,ung,lane

def run(p, keep, fw=120):
    fast,clause,ung,lane=pieces(p)
    frozen=np.zeros(N,bool)
    for k,c in fast.items():
        if k in keep: frozen|=fresh(c,fw)&G
    for k,c in clause.items():
        if k in keep: frozen|=fresh(c&NG,fw)
    for k,c in ung.items():
        if k in keep: frozen|=fresh(c,fw)
    la=np.zeros(N,bool)
    for k,c in lane.items():
        if k in keep: la|=fresh(c,fw)
    valid=la.copy(); lfa=[]
    for i in np.flatnonzero(np.diff(la.astype(np.int8))==1)+1:
        if not frozen[i:i+121].any():
            j=i
            while j<N and la[j]: valid[j]=False; j+=1
            if cal[i]>=pd.Timestamp("1968-06-01"): lfa.append(str(cal[i].date()))
    res,false=score_eps(replay(frozen|valid),T_P1)
    lags=[r["lag"] for r in res]
    # no-inversion world: the gate never arms, so fast channels are silent and the
    # clauses are always live
    fz=np.zeros(N,bool)
    for k,c in clause.items():
        if k in keep: fz|=fresh(c,fw)
    for k,c in ung.items():
        if k in keep: fz|=fresh(c,fw)
    resN,falseN=score_eps(replay(fz),T_P1)
    nN=sum(1 for r in resN if r["lag"] is not None)
    ok=(len(false)==0) and lags==BASE and nN==9 and len(falseN)==0
    return ok,lags,false,nN,lfa

P0=dict(sahm=0.35,iur=0.40,pay=0.001,hou=20,bill=1.43,sahmC=0.55,iurC=0.50,houC=25,
        claims=0.40,ip=0.02,vix=17.425,baa=1.50)
ALL=["sahm","iur","pay","hou","bill","sahmC","iurC","houC","claims","ip","vix","baa"]
print("baseline v7.2:", run(P0,ALL)[:1], run(P0,ALL)[1], "no-inv", run(P0,ALL)[3])
print("\n(a) single drops")
drop_ok=[]
for c in ALL:
    o,l,f,n,_=run(P0,[x for x in ALL if x!=c])
    if o: drop_ok.append(c)
    print("   -%-7s ok=%-5s no-inv %d/9 %s" % (c,o,n,"" if o else ("lags %s false %s"%(l,f))))
print("   individually droppable:", drop_ok)
best=None
for r in range(len(drop_ok),0,-1):
    for combo in itertools.combinations(drop_ok,r):
        o,_,_,n,_=run(P0,[x for x in ALL if x not in combo])
        if o: best=combo; break
    if best: break
print("   MAXIMAL JOINT DROP:", best, "-> keeps", [x for x in ALL if x not in (best or ())])
import json; json.dump({"drop_ok":drop_ok,"best":list(best or ())}, open("stage65_drop.json","w"))
