"""Stage 71: redo the tightening under a DAY-level constraint -- the nine onset dates
must be identical to v7.2's, not merely the month lags."""
exec(open("stage65_minimal.py").read().split('P0=dict(')[0])
import numpy as np, json
P0=dict(sahm=0.35,iur=0.40,pay=0.001,hou=20,bill=1.43,sahmC=0.55,iurC=0.50,houC=25,
        claims=0.40,ip=0.02,vix=17.425,baa=1.50)
ALL=["sahm","iur","pay","hou","bill","sahmC","iurC","houC","claims","ip","vix","baa"]
KEEP=[c for c in ALL if c not in ("iurC","houC","claims","ip","baa")]
def dates(p,keep,fw=120):
    fast,clause,ung,lane=pieces(p)
    fr=np.zeros(N,bool)
    for k,c in fast.items():
        if k in keep: fr|=fresh(c,fw)&G
    for k,c in clause.items():
        if k in keep: fr|=fresh(c&NG,fw)
    for k,c in ung.items():
        if k in keep: fr|=fresh(c,fw)
    la=np.zeros(N,bool)
    for k,c in lane.items():
        if k in keep: la|=fresh(c,fw)
    valid=la.copy()
    for i in np.flatnonzero(np.diff(la.astype(np.int8))==1)+1:
        if not fr[i:i+121].any():
            j=i
            while j<N and la[j]: valid[j]=False; j+=1
    eps=replay(fr|valid); res,false=score_eps(eps,T_P1)
    fz=np.zeros(N,bool)
    for k,c in clause.items():
        if k in keep: fz|=fresh(c,fw)
    for k,c in ung.items():
        if k in keep: fz|=fresh(c,fw)
    nN=sum(1 for r in score_eps(replay(fz),T_P1)[0] if r["lag"] is not None)
    return [str(e["onset"].date()) for e in eps], [str(e["end_call"].date()) for e in eps], false, nN
REF=['1969-10-06','1973-10-25','1980-01-03','1981-08-18','1990-08-03','2001-02-02','2008-01-04','2020-02-28','2024-05-03']
d0,e0,f0,n0=dates(P0,KEEP)
print("after deleting the five dead channels:", "dates match" if d0==REF else d0, "| false",f0,"| no-inv",n0)
GR={"sahm":[0.35,0.36,0.37,0.38,0.40,0.42,0.45],"iur":[0.40,0.42,0.45,0.48,0.50],
    "pay":[0.001,0.0012,0.0015,0.0018,0.002,0.0025,0.003],"hou":[20,21,22,24,26],
    "bill":[1.43,1.45,1.48,1.50,1.55,1.60,1.75],"sahmC":[0.55,0.58,0.60],
    "vix":[17.425,18,19,20,22,25,28]}
cur={k:GR[k][0] for k in GR}
for _ in range(6):
    ch=False
    for k in GR:
        i=GR[k].index(cur[k])
        while i+1<len(GR[k]):
            t=dict(P0); t.update(cur); t[k]=GR[k][i+1]
            dd,ee,ff,nn=dates(t,KEEP)
            if dd==REF and not ff and nn==9: cur[k]=GR[k][i+1]; i+=1; ch=True
            else: break
    if not ch: break
pj=dict(P0); pj.update(cur)
dd,ee,ff,nn=dates(pj,KEEP)
print("\nfree tightenings at DAY level:", {k:(P0[k],v) for k,v in cur.items() if v!=P0[k]})
print("  onset dates:", dd)
print("  identical to v7.2:", dd==REF, "| ends identical:", ee==dates(P0,ALL)[1], "| false", ff, "| no-inv", nn)
json.dump(cur, open("stage71_cur.json","w"))
