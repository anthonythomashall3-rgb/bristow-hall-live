"""Stage 147: state breadth as a fast channel, calibrated the v14 way.  National claims are an
average; the number of STATES whose own claims are rising is a different object and may move
earlier.  It is calibrated here exactly as v14's lines are -- a quarter of a robust standard
deviation above its own quiet record -- and added to the machine."""
exec(open("stage128_ztwolane.py").read().split("def machine(c,c2")[0])
import numpy as np, pandas as pd
ALL=["Sahm","IUR","payrolls","housing","bill"]
ZMAXg={n:float(np.nanmax(np.where(QC&G&CO,np.where(np.isfinite(Zz[n]),Zz[n],-99),-99))) for n in NAMES}
ZMAXn=float(np.nanmax(np.where(QC&NG&CCO,np.where(np.isfinite(ZU["Sahm"]),ZU["Sahm"],-99),-99)))
Zc=np.where(np.isfinite(ZU["Sahm"]),ZU["Sahm"],-99.0)
print("state panel: continued claims %s, initial claims %s, %d states, %s to %s"%(
    g8.shape,gi8.shape,g8.shape[1],g8.index.min().date(),g8.index.max().date()))
CAND={}
for q in [0.25,0.50,0.75]:
    for w in [8,13,26]:
        m=cw.rolling(w).mean(); mn=m.shift(1).rolling(52).min()
        CAND["continued claims, %dwk, %dth percentile state above its own year low"%(w,100*q)]=(m/mn-1).quantile(q,axis=1).astype(float)
        mi=icst.rolling(w).mean(); mni=mi.shift(1).rolling(52).min()
        CAND["initial claims, %dwk, %dth percentile state above its own year low"%(w,100*q)]=(mi/mni-1).quantile(q,axis=1).astype(float)
for w in [8,13]:
    m=cw.rolling(w).mean(); mn=m.shift(1).rolling(52).min()
    CAND["continued claims, %dwk, mean state gap"%w]=(m/mn-1).mean(axis=1).astype(float)
    CAND["continued claims, %dwk, share of states above their year low"%w]=((m/mn-1)>0).mean(axis=1).astype(float)
def scale(x, lag=5):
    v=sd(x,lag)
    m=QC&G&CO
    q=v[m]; q=q[np.isfinite(q)]
    if len(q)<200: return None
    med=float(np.median(q)); mad=float(np.median(np.abs(q-med)))*1.4826
    if mad<=0: return None
    z=(v-med)/mad
    rec=float(np.nanmax(np.where(m,np.where(np.isfinite(z),z,-99),-99)))
    return z, rec, med, mad
def build(extra_hits):
    hits=np.zeros(N,bool)
    for n in ["Sahm","payrolls","housing","bill"]:
        z=np.where(np.isfinite(Zz[n]),Zz[n],-99.0); hits|=(z>=ZMAXg[n]+0.25)
    hits|=np.asarray(gapch(iur4,0.40),bool)
    if extra_hits is not None: hits|=extra_hits
    fr=fresh(hits&CO,120)&G
    fr=fr|fresh((Zc>=ZMAXn+2.0)&CCO&NG,120)
    la=fresh(np.asarray(lane_arr(vix-vix.shift(20),1,22.0),bool),120); valid=la.copy()
    for i in np.flatnonzero(np.diff(la.astype(np.int8))==1)+1:
        if not fr[i:i+121].any():
            j=i
            while j<N and la[j]: valid[j]=False; j+=1
    fr=fr|valid
    eps=replay(fr); res,f=score_eps(eps,T_P1)
    det=sum(1 for x in res if x["lag"] is not None)
    armed=int((hits&CO&G&QC).sum())
    dd=[(e["onset"]-FIRST[i]).days for i,e in enumerate(eps)][:9] if det==9 else None
    return det,f,armed,dd,[r["lag"] for r in res]
b=build(None)
print("\nv14 baseline: %d/9 false %d armed %d | days %s"%(b[0],len(b[1]) if b[1] else 0,b[2],b[3]))
print("\n%-58s %-6s %-6s %-7s %s"%("added channel (at its own quiet record + 0.25 robust sd)","det","false","armedQ","days from the first day"))
best=[]
for nm,s in CAND.items():
    r=scale(s)
    if r is None: continue
    z,rec,med,mad=r
    hits=np.where(np.isfinite(z),z,-99.0)>=rec+0.25
    det,f,armed,dd,lags=build(hits)
    mark=""
    if det==9 and not f and dd is not None:
        base=b[3]; faster=sum(1 for i in range(9) if dd[i]<base[i])
        mark=" faster on %d"%faster
        best.append((float(np.mean(np.abs(dd))),nm,dd,armed,lags))
    print("%-58s %-6s %-6d %-7d %s%s"%(nm,"%d/9"%det,len(f) if f else 0,armed,dd,mark))
if best:
    best.sort()
    print("\nbest addition by mean absolute distance: %s"%best[0][1])
    print("  days %s | mean %.1f | lags %s"%(best[0][2],best[0][0],best[0][4]))
