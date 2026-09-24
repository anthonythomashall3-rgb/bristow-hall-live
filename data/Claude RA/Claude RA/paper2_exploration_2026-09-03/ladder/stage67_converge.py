"""Stage 67: greedy tightening to convergence; freshness measured in armed days;
persistence in RELEASES (not calendar days)."""
exec(open("stage65_minimal.py").read().split('P0=dict(')[0])
import numpy as np, json
P0=dict(sahm=0.35,iur=0.40,pay=0.001,hou=20,bill=1.43,sahmC=0.55,iurC=0.50,houC=25,
        claims=0.40,ip=0.02,vix=17.425,baa=1.50)
ALL=["sahm","iur","pay","hou","bill","sahmC","iurC","houC","claims","ip","vix","baa"]
KEEP=[c for c in ALL if c not in ("iurC","houC","claims","ip","baa")]
GR={"sahm":[0.35,0.36,0.37,0.38,0.40,0.42,0.45,0.50],"iur":[0.40,0.42,0.45,0.48,0.50,0.55,0.60],
    "pay":[0.001,0.0012,0.0015,0.0018,0.002,0.0025,0.003],"hou":[20,21,22,24,26,28],
    "bill":[1.43,1.45,1.48,1.50,1.55,1.60,1.75,1.90],"sahmC":[0.55,0.58,0.60,0.65,0.70],
    "vix":[17.425,18,19,20,22,25,28,32]}
cur={k:GR[k][0] for k in GR}
improved=True; rounds=0
while improved and rounds<8:
    improved=False; rounds+=1
    for k in GR:
        i=GR[k].index(cur[k])
        while i+1<len(GR[k]):
            trial=dict(P0); trial.update(cur); trial[k]=GR[k][i+1]
            if run(trial,KEEP)[0]: cur[k]=GR[k][i+1]; i+=1; improved=True
            else: break
pj=dict(P0); pj.update(cur)
o,l,f,n,_=run(pj,KEEP)
print("converged thresholds:", {k:v for k,v in cur.items()})
print("  moved:", {k:(P0[k],v) for k,v in cur.items() if v!=P0[k]})
print("  ok=%s lags=%s false=%s no-inv=%d/9" % (o,l,f,n))

print("\n(c) freshness: armed days and the record")
fastP,clauseP,ungP,laneP=pieces(pj)
for fw in [120,90,60,45,30,20,10]:
    armed=np.zeros(N,bool)
    for k,c in fastP.items():
        if k in KEEP: armed|=fresh(c,fw)&G
    armed|=fresh(clauseP["sahmC"]&NG,fw)
    o2,l2,f2,n2,_=run(pj,KEEP,fw=fw)
    print("   %3dd armed %5d days (%4.1f%% of record) ok=%-5s no-inv %d/9" %
          (fw,int(armed.sum()),100*armed.mean(),o2,n2))

print("\n(d) persistence in RELEASES on each channel (k consecutive prints/readings)")
def per_rel(series_bool_idx, k):
    s=series_bool_idx.copy()
    out=s.copy()
    for j in range(1,k): out &= s.shift(j).fillna(False)
    return D(out)
tests={"sahmC":(pd.Series(Srel>=pj["sahmC"]-1e-9),"clause"),
       "sahm":(pd.Series(Srel>=pj["sahm"]-1e-9),"fast")}
for nm,(sb,kind) in tests.items():
    for k in [1,2,3]:
        arr=np.asarray(per_rel(sb,k),bool)
        frozen=np.zeros(N,bool)
        for k2,c in fastP.items():
            if k2 in KEEP: frozen|=fresh(arr if (k2==nm and kind=="fast") else c,120)&G
        frozen|=fresh((arr if nm=="sahmC" else clauseP["sahmC"])&NG,120)
        la=fresh(laneP["vix"],120); valid=la.copy()
        for i in np.flatnonzero(np.diff(la.astype(np.int8))==1)+1:
            if not frozen[i:i+121].any():
                j=i
                while j<N and la[j]: valid[j]=False; j+=1
        res,false=score_eps(replay(frozen|valid),T_P1)
        fz=fresh(arr if nm=="sahmC" else clauseP["sahmC"],120)
        resN,_=score_eps(replay(fz),T_P1)
        print("   %-6s x%d  lags %s false %s no-inv %d/9" %
              (nm,k,[r["lag"] for r in res],false,sum(1 for r in resN if r["lag"] is not None)))
json.dump(cur, open("stage67_cur.json","w"))
