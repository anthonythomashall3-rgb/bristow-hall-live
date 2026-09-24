"""Stage 85: v9 -- perturbation map, leave-one-out on the two claims floors, and the
first-print check."""
exec(open("stage46_v7.py").read().split("t6,l6=build")[0])
import numpy as np, pandas as pd
G=np.asarray(GATE[12],bool); NG=~G
def sd(s,lag):
    x=s.copy(); x.index=x.index+pd.Timedelta(days=lag); return x.reindex(cal).ffill().values.astype(float)
CL=np.nan_to_num(sd(r8,5),nan=-9)
REF=['1969-10-06','1973-10-25','1980-01-03','1981-08-18','1990-08-03','2001-02-02','2008-01-04','2020-02-28','2024-05-03']
def mk(sahm=0.36,iur=0.40,payx=0.18,hou=20,bill=1.45,clause=0.55,vixx=22.0,gf=0.03,cf=0.10):
    co=CL>=gf; cco=CL>=cf
    F=[np.asarray(D(Srel>=sahm-1e-9),bool),np.asarray(gapch(iur4,iur),bool),
       np.asarray(D(pd.Series((pay.d1.astype(float)<=-payx).values,index=pd.to_datetime(pay.rel.values))),bool),
       np.asarray(persist2(h3,hou),bool),np.asarray(fall(tb6,60,bill),bool)]
    fr=np.zeros(N,bool)
    for c in F: fr|=fresh(c&co,120)&G
    CLA=np.asarray(D(Srel>=clause-1e-9),bool)&cco
    fr|=fresh(CLA&NG,120)
    la=fresh(np.asarray(lane_arr(vix-vix.shift(20),1,vixx),bool),120); valid=la.copy()
    for i in np.flatnonzero(np.diff(la.astype(np.int8))==1)+1:
        if not fr[i:i+121].any():
            j=i
            while j<N and la[j]: valid[j]=False; j+=1
    eps=replay(fr|valid); r,f=score_eps(eps,T_P1)
    fz=fresh(CLA,120); rN,_=score_eps(replay(fz),T_P1)
    return [str(e["onset"].date()) for e in eps],[x["lag"] for x in r],f,sum(1 for x in rN if x["lag"] is not None)
print("=== perturbation map, v9 ===")
nfa=0; tot=0
for lab,kw in [("Sahm 0.36 -> 0.34",dict(sahm=0.34)),("Sahm 0.36 -> 0.38",dict(sahm=0.38)),
  ("IUR 0.40 -> 0.35",dict(iur=0.35)),("IUR 0.40 -> 0.45",dict(iur=0.45)),
  ("payrolls 0.18 -> 0.13",dict(payx=0.13)),("payrolls 0.18 -> 0.23",dict(payx=0.23)),
  ("housing 20% -> 18%",dict(hou=18)),("housing 20% -> 22%",dict(hou=22)),
  ("bill 1.45 -> 1.40",dict(bill=1.40)),("bill 1.45 -> 1.50",dict(bill=1.50)),
  ("clause 0.55 -> 0.50",dict(clause=0.50)),("clause 0.55 -> 0.60",dict(clause=0.60)),
  ("VIX 22 -> 20",dict(vixx=20)),("VIX 22 -> 24",dict(vixx=24)),
  ("global floor 3% -> 2%",dict(gf=0.02)),("global floor 3% -> 4%",dict(gf=0.04)),
  ("clause floor 10% -> 8%",dict(cf=0.08)),("clause floor 10% -> 12%",dict(cf=0.12))]:
    d,l,f,n=mk(**kw); tot+=1
    if f: nfa+=1
    out=[x for x in l if x is not None and abs(x)>1]; miss=sum(1 for x in l if x is None)
    print("  %-26s false %-3s miss %-3d outside-month %s%s" % (lab,len(f) if f else 0,miss,out,"" if n==9 else "  [no-inv %d/9]"%n))
print("  %d of %d one-tick moves create a false alarm" % (nfa,tot))
print("\n=== leave-one-out on the two claims floors ===")
def largest_floor(exclude):
    best=(-9,-9)
    for gf in [0.0,0.01,0.02,0.03,0.04,0.05]:
        for cf in [0.05,0.08,0.10,0.12,0.15]:
            d,l,f,n=mk(gf=gf,cf=cf)
            keep=[i for i in range(9) if i!=exclude]
            ok=(not f) and n>=8 and all(d[i]==REF[i] for i in keep)
            if ok and (gf,cf)>best: best=(gf,cf)
    return best
bad=0
for k in range(9):
    gf,cf=largest_floor(k)
    d,l,f,n=mk(gf=gf,cf=cf)
    held_ok = d[k]==REF[k]
    if not held_ok: bad+=1
    print("  hold out %s: floors fitted on the other eight = %.2f / %.2f -> held-out call %s %s" %
          (REF[k][:7], gf, cf, d[k], "OK" if held_ok else "MOVED (was %s)"%REF[k]))
print("  held-out calls unchanged: %d of 9" % (9-bad))
