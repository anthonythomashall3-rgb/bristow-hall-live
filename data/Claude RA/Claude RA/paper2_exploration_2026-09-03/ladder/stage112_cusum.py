"""Stage 112: a different statistical object for the onsets.  Every channel now waits for a
LEVEL crossing.  A CUSUM accumulates evidence instead -- S_t = max(0, S_{t-1} + x_t - k) --
and fires when the accumulated sum clears h.  It detects a sustained small deviation sooner
than a level rule detects a large single one.  Scored in the machine: zero armed days on the
canonical quiet set, every lag inside a month, and days gained."""
exec(open("stage106_v11.py").read().split('eps,l,e,t,f,n,arm,lv,co,cco=machine()')[0])
import numpy as np, pandas as pd
REFd=[pd.Timestamp(x) for x in REF]
m8=ic.rolling(8).mean(); rr=(m8/m8.shift(1).rolling(52).min()-1)
CLx=np.nan_to_num(sd(rr,5),nan=-9)
CO=pd.Series(CLx>=0.03).rolling(8*7,min_periods=1).max().fillna(0).astype(bool).values
CCO=CLx>=0.12
def cusum(v, k, h):
    x=np.nan_to_num(v,nan=k)      # missing contributes nothing
    s=np.zeros(len(x)); acc=0.0
    for i in range(len(x)):
        acc=max(0.0, acc + (x[i]-k))
        s[i]=acc
    return s>=h
def machine_with(sahm_arr=None, iur_arr=None, bill_arr=None):
    F=[sahm_arr if sahm_arr is not None else np.asarray(D(Srel>=0.36-1e-9),bool),
       iur_arr  if iur_arr  is not None else np.asarray(gapch(iur4,0.40),bool),
       np.asarray(D(pd.Series((pay.d1.astype(float)<=-0.18).values,index=pd.to_datetime(pay.rel.values))),bool),
       HOU,
       bill_arr if bill_arr is not None else np.asarray(fall(tb6,60,1.45),bool)]
    fr=np.zeros(N,bool)
    for c in F: fr|=fresh(c&CO,120)&G
    CLA=np.asarray(D(Srel>=0.55-1e-9),bool)&CCO
    fr|=fresh(CLA&NG,120)
    la=fresh(np.asarray(lane_arr(vix-vix.shift(20),1,22.0),bool),120); valid=la.copy()
    for i in np.flatnonzero(np.diff(la.astype(np.int8))==1)+1:
        if not fr[i:i+121].any():
            j=i
            while j<N and la[j]: valid[j]=False; j+=1
    eps=replay(fr|valid); res,f=score_eps(eps,T_P1)
    fz=fresh(CLA,120); rN,_=score_eps(replay(fz),T_P1)
    armed=np.zeros(N,bool)
    for c in F: armed|=(c&CO&G)
    armed|=(CLA&NG)
    return ([e["onset"] for e in eps],[x["lag"] for x in res],[str(e["end_call"].date()) for e in eps],f,
            sum(1 for x in rN if x["lag"] is not None),int((armed&QC).sum()))
d0,l0,e0,f0,n0,a0=machine_with()
print("v11 baseline: lags %s | false %s | no-inv %d/9 | quiet-armed %d" % (l0,f0 if f0 else 0,n0,a0))
S=Srel.reindex(cal).ffill().values.astype(float)
IURg=sd(iur4-iur4.rolling(52).min(),12)
BILL=sd(-(tb6-tb6.shift(60)),1)
CH={"Sahm":(S,"sahm"),"IUR gap":(IURg,"iur"),"bill fall":(BILL,"bill")}
print("\n%-12s %-22s %-8s %-34s %s" % ("channel","CUSUM (k, h)","armed","lags","days gained"))
found=[]
for nm,(v,slot) in CH.items():
    q=v[QC&CO&G]; q=q[np.isfinite(q)]
    mu=float(np.nanmean(q)); sg=float(np.nanstd(q))
    for kmul in (0.0,0.5,1.0,1.5,2.0):
        k=mu+kmul*sg
        for hmul in (2,4,8,16,32,64,128):
            h=hmul*sg
            arr=cusum(v,k,h)
            kw={slot+"_arr":arr}
            d,l,e,f,n,a=machine_with(**kw)
            if f or n!=9 or a!=0 or e!=e0: continue
            if any(x is None or abs(x)>1 for x in l): continue
            days=sum((rd-dd).days for dd,rd in zip(d,REFd))
            if days<=0: continue
            found.append((days,nm,kmul,hmul,l,[str(x.date()) for x in d]))
            print("%-12s %-22s %-8s %-34s +%d" % (nm,"mean+%.1fsd, h=%dsd"%(kmul,hmul),"0",str(l),days))
found.sort(reverse=True)
if found:
    days,nm,kmul,hmul,l,d=found[0]
    print("\nbest: %s CUSUM (drift mean+%.1f sd, threshold %d sd) gains %d days" % (nm,kmul,hmul,days))
    print("   onsets %s" % d)
else:
    print("  no CUSUM form gains days without breaking a constraint")
