"""Stage 140: is the channel set fitted?  Stage 139 chose both the channels and the margin by
searching against all nine episodes.  Here the search is run nine times over, each time
against the other eight, and the held-out recession is then asked of an instrument that never
saw it.  A rule that survives this is one whose channels were not picked to fit the record."""
exec(open("stage128_ztwolane.py").read().split("def machine(c,c2")[0])
import numpy as np, pandas as pd, itertools, json
ALL=["Sahm","IUR","payrolls","housing","bill","claims","contclaims","IP"]
ZMAXg={n:float(np.nanmax(np.where(QC&G&CO,np.where(np.isfinite(Zz[n]),Zz[n],-99),-99))) for n in ALL}
ZMAXn=float(np.nanmax(np.where(QC&NG&CCO,np.where(np.isfinite(ZU["Sahm"]),ZU["Sahm"],-99),-99)))
Zarr={n:np.where(np.isfinite(Zz[n]),Zz[n],-99.0) for n in ALL}
Zc=np.where(np.isfinite(ZU["Sahm"]),ZU["Sahm"],-99.0)
PK=[p for p,t in T_P1]
def run(names,d,d2=2.0):
    hits=np.zeros(N,bool)
    for n in names: hits|=(Zarr[n]>=ZMAXg[n]+d)
    fr=fresh(hits&CO,120)&G
    fr=fr|fresh((Zc>=ZMAXn+d2)&CCO&NG,120)
    eps=replay(fr); res,f=score_eps(eps,T_P1)
    det=[r["lag"] is not None for r in res]
    call={r["peak"]:r["onset"] for r in res}
    dd=[( (pd.Timestamp(call[p])-FIRST[j]).days if call.get(p) else None) for j,p in enumerate(PK)]
    return det,f,dd
DS=[0.0,0.25,0.5,0.75,1.0,1.25,1.5,1.75,2.0,2.5,3.0]
REC=[]
for r in range(1,9):
  for names in itertools.combinations(ALL,r):
    for d in DS:
        det,f,dd=run(names,d)
        REC.append((names,d,det,f,dd))
print("configurations evaluated: %d"%len(REC))
def falses_excluding(f,h):
    """false-alarm dates, ignoring any that fall inside the held-out episode's own window"""
    p,t=T_P1[h]
    lo=(pd.Period(p,"M")-6).to_timestamp(); hi=(pd.Period(t,"M")+12).to_timestamp(how="end")
    return [x for x in f if not (lo<=pd.Timestamp(x)<=hi)]
print("\nleave-one-out: the channels and the margin are chosen on the other eight episodes only")
print("%-9s %-46s %-6s %-9s %s"%("held out","chosen channels","delta","detected","days from the first day"))
nd=0
for h in range(9):
    best=None
    for names,d,det,f,dd in REC:
        o=[det[j] for j in range(9) if j!=h]
        if not all(o): continue
        if falses_excluding(f,h): continue
        md=float(np.mean([abs(dd[j]) for j in range(9) if j!=h and dd[j] is not None]))
        sc=(-md,-len(names))
        if best is None or sc>best[0]: best=(sc,names,d,det,dd)
    if best is None:
        print("%-9s %-46s %-6s %-9s"%(PK[h],"(nothing detects the other eight)","-","-")); continue
    _,names,d,det,dd=best
    ok=det[h]; nd+=int(ok)
    print("%-9s %-46s %-6.2f %-9s %s"%(PK[h]," + ".join(names),d,"yes" if ok else "NO",dd[h]))
print("\nheld-out recessions detected by an instrument that never saw them: %d of 9"%nd)
print("\nfor comparison, the same test on the margin alone, channels fixed to v11's five:")
FIVE=("Sahm","IUR","payrolls","housing","bill")
nd2=0
for h in range(9):
    best=None
    for names,d,det,f,dd in REC:
        if names!=FIVE: continue
        o=[det[j] for j in range(9) if j!=h]
        if not all(o) or falses_excluding(f,h): continue
        md=float(np.mean([abs(dd[j]) for j in range(9) if j!=h and dd[j] is not None]))
        if best is None or -md>best[0]: best=(-md,d,det,dd)
    if best is None: print("  %-9s no margin works on the other eight"%PK[h]); continue
    _,d,det,dd=best; nd2+=int(det[h])
    print("  %-9s delta %.2f -> held-out %s (%s days)"%(PK[h],d,"detected" if det[h] else "MISSED",dd[h]))
print("held-out detected: %d of 9"%nd2)
