"""Stage 89: re-check the 'zero quiet days' claim for v9 against the CANONICAL quiet set
(the one the machine sees: no episode open), not the cruder peak-6/trough+12 mask used
in stage 82.  Uses the real channel arrays, not daily proxies."""
exec(open("stage46_v7.py").read().split("t6,l6=build")[0])
exec(open("stage44_evt.py").read().split("print(\"\\n=== (B) EXTREME")[0])
import numpy as np, pandas as pd
G=np.asarray(GATE[12],bool); NG=~G
def sd(s,lag=0):
    x=s.copy(); x.index=x.index+pd.Timedelta(days=lag); return x.reindex(cal).ffill().values.astype(float)
CL=np.nan_to_num(sd(r8,5),nan=-9); CO=CL>=0.03; CCO=CL>=0.12
QC=(~allowed)&(~openmask)&(cal>=pd.Timestamp("1968-06-01"))          # canonical
QX=np.ones(N,bool)&(cal>=pd.Timestamp("1968-06-01"))                  # crude
for p,t in [(pd.Timestamp(a),pd.Timestamp(b)) for a,b in T_P1]:
    QX &= ~((cal>=p-pd.DateOffset(months=6))&(cal<=t+pd.DateOffset(months=12)))
CH={"sahm fast":(np.asarray(D(Srel>=0.36-1e-9),bool)&CO&G),
    "iur fast":(np.asarray(gapch(iur4,0.40),bool)&CO&G),
    "payrolls fast":(np.asarray(D(pd.Series((pay.d1.astype(float)<=-0.18).values,index=pd.to_datetime(pay.rel.values))),bool)&CO&G),
    "housing fast":(np.asarray(persist2(h3,20),bool)&CO&G),
    "bill fast":(np.asarray(fall(tb6,60,1.45),bool)&CO&G),
    "Sahm clause":(np.asarray(D(Srel>=0.55-1e-9),bool)&CCO&NG)}
print("%-15s %-24s %s" % ("channel","armed days in CANONICAL quiet","armed days in crude quiet"))
anyc=np.zeros(N,bool)
for k,a in CH.items():
    anyc|=a
    print("%-15s %-24d %d" % (k,int((a&QC).sum()),int((a&QX).sum())))
print("%-15s %-24d %d" % ("ANY CHANNEL",int((anyc&QC).sum()),int((anyc&QX).sum())))
print("\ncanonical quiet days: %d | crude quiet days: %d" % (int(QC.sum()),int(QX.sum())))
if (anyc&QC).any():
    d=cal[anyc&QC]
    runs=[]; prev=None
    for x in d:
        if prev is None or (x-prev).days>40: runs.append([x,x])
        else: runs[-1][1]=x
        prev=x
    print("\ncanonical-quiet armings, by run:")
    for a,b in runs:
        who=[k for k,arr in CH.items() if (arr&QC&(cal>=a)&(cal<=b)).any()]
        print("   %s .. %s  (%s)" % (a.date(), b.date(), ", ".join(who)))
# does any of these open an EPISODE under v9?  the replay is the authority
frozen=np.zeros(N,bool)
for k in ("sahm fast","iur fast","payrolls fast","housing fast","bill fast"): frozen|=fresh(CH[k],120)
frozen|=fresh(CH["Sahm clause"],120)
la=fresh(np.asarray(lane_arr(vix-vix.shift(20),1,22.0),bool),120); valid=la.copy()
for i in np.flatnonzero(np.diff(la.astype(np.int8))==1)+1:
    if not frozen[i:i+121].any():
        j=i
        while j<N and la[j]: valid[j]=False; j+=1
eps=replay(frozen|valid); res,false=score_eps(eps,T_P1)
print("\nv9 replay: onsets %s | false %s" % ([str(e["onset"].date()) for e in eps], false if false else 0))
