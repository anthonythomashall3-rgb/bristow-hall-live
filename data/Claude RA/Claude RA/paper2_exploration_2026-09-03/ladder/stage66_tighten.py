"""Stage 66: (b) tighten every threshold to its breaking point, (c) freshness, (d) persistence."""
exec(open("stage65_minimal.py").read().split('P0=dict(')[0])
import numpy as np, itertools, json
P0=dict(sahm=0.35,iur=0.40,pay=0.001,hou=20,bill=1.43,sahmC=0.55,iurC=0.50,houC=25,
        claims=0.40,ip=0.02,vix=17.425,baa=1.50)
ALL=["sahm","iur","pay","hou","bill","sahmC","iurC","houC","claims","ip","vix","baa"]
# keep the five channels that carry nothing anywhere out; keep payrolls (distinct mechanism)
KEEP=[c for c in ALL if c not in ("iurC","houC","claims","ip","baa")]
print("keep set:", KEEP)
print("check:", run(P0,KEEP)[0], run(P0,KEEP)[1])

GR={"sahm":[0.35,0.36,0.38,0.40,0.42,0.45],"iur":[0.40,0.42,0.45,0.48,0.50],
    "pay":[0.001,0.0012,0.0015,0.002,0.0025],"hou":[20,21,22,24,26,28],
    "bill":[1.43,1.45,1.50,1.60,1.75,1.90],"sahmC":[0.55,0.60,0.70,0.80,1.00],
    "vix":[17.425,18,19,20,22,25]}
print("\n(b) largest value of each threshold that keeps everything (one at a time)")
top={}
for k,vals in GR.items():
    best=vals[0]
    for v in vals:
        p=dict(P0); p[k]=v
        if run(p,KEEP)[0]: best=v
        else: break
    top[k]=best
    print("   %-6s %-8s -> %-8s %s" % (k,P0[k],best,"(no room)" if best==P0[k] else "TIGHTER"))
print("\n   joint application of every tightening found:")
pj=dict(P0); pj.update(top)
o,l,f,n,lv=run(pj,KEEP); print("   ok=%s lags=%s false=%s no-inv=%d/9" % (o,l,f,n))
if not o:
    # back off greedily
    for k in sorted(top, key=lambda x:-GR[x].index(top[x])):
        while top[k]!=P0[k]:
            i=GR[k].index(top[k]); top[k]=GR[k][i-1]
            pj=dict(P0); pj.update(top)
            if run(pj,KEEP)[0]: break
        pj=dict(P0); pj.update(top)
        if run(pj,KEEP)[0]: break
    o,l,f,n,lv=run(pj,KEEP); print("   after backing off: ok=%s %s no-inv=%d/9 -> %s" % (o,l,n,{k:v for k,v in top.items() if v!=P0[k]}))

print("\n(c) freshness window")
for fw in [120,105,90,75,60,45,30]:
    o,l,f,n,_=run(pj,KEEP,fw=fw)
    print("   %3dd ok=%-5s no-inv %d/9 %s" % (fw,o,n,"" if o else "lags %s false %s"%(l,f)))
print("\n(d) persistence on the Sahm no-inversion clause (x1 -> xk consecutive days)")
fastP,clauseP,ungP,laneP=pieces(pj)
for k in [1,2,3,5,10]:
    def run_k(kk):
        frozen=np.zeros(N,bool)
        for kk2,c in fastP.items():
            if kk2 in KEEP: frozen|=fresh(c,120)&G
        frozen|=fresh(per(clauseP["sahmC"],kk)&NG,120)
        la=fresh(laneP["vix"],120); valid=la.copy()
        for i in np.flatnonzero(np.diff(la.astype(np.int8))==1)+1:
            if not frozen[i:i+121].any():
                j=i
                while j<N and la[j]: valid[j]=False; j+=1
        res,false=score_eps(replay(frozen|valid),T_P1)
        fz=fresh(per(clauseP["sahmC"],kk),120)
        resN,_=score_eps(replay(fz),T_P1)
        return [r["lag"] for r in res], false, sum(1 for r in resN if r["lag"] is not None)
    l,f,n=run_k(k)
    print("   x%-2d lags %s false %s no-inv %d/9" % (k,l,f,n))
json.dump({"keep":KEEP,"top":top}, open("stage66_top.json","w"))
