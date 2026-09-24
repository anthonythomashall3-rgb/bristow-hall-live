"""Stage 91: filter the 1981 candidates.  A channel that carries only 1981 is a
fingerprint of the Volcker tightening, not a mechanism.  Require: zero crossings on the
canonical quiet set, a call within a month of the peak in 1981, AND at least one other
recession carried on time."""
exec(open("stage90_1981.py").read().split("rows=[]")[0])
import numpy as np, pandas as pd
PK=[(pd.Timestamp(a),pd.Timestamp(b)) for a,b in T_P1]
res=[]
for nm,v in cands.items():
    q=v[QC&CO]; q=q[np.isfinite(q)]
    if len(q)<500: continue
    qm=float(np.max(q)); sdv=float(np.nanstd(q))
    if sdv<=0: continue
    w=v[WIN&CO]; w=w[np.isfinite(w)]
    if len(w)<10 or np.max(w)<=qm: continue
    line=(qm+float(np.max(w)))/2.0
    on=(v>=line)&CO&G
    on=np.nan_to_num(on,nan=False).astype(bool)
    if (on&QC).any(): continue                      # must never arm in a quiet period
    calls=[]
    for (p,t) in PK:
        m=on&(cal>=p-pd.DateOffset(months=6))&(cal<=t)
        if m.any():
            d=cal[m][0]; calls.append((str(p.date())[:7], (d.year-p.year)*12+(d.month-p.month)))
    ontime=[c for c in calls if abs(c[1])<=1]
    if not any(c[0]=="1981-07" and abs(c[1])<=1 for c in ontime): continue
    res.append(((float(np.max(w))-qm)/sdv, nm, qm, line, calls))
res.sort(reverse=True)
print("candidates that (a) never arm in a quiet period, (b) call 1981 within a month:")
print("%-40s %8s %8s  %s" % ("statistic","quiet max","line","recessions carried (lag)"))
for m,nm,qm,line,calls in res[:20]:
    print("%-40s %8.3f %8.3f  %s   [margin %.2f sd]" % (nm,qm,line,calls,m))
multi=[r for r in res if len([c for c in r[4] if abs(c[1])<=1])>=2]
print("\ncarrying 1981 AND at least one other recession on time:", len(multi))
for m,nm,qm,line,calls in multi[:10]:
    print("   %-38s %s  [margin %.2f sd]" % (nm,calls,m))
