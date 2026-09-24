"""Stage 99: sweep the FORM of the Sahm signal from the first-print unemployment rates:
m-month mean less the minimum of the prior L monthly means, k confirming prints, line by
max margin.  Scored in the machine, with every constraint v10 already meets."""
exec(open("stage98_sahmform.py").read().split('S=Srel.reindex(cal)')[0])
import numpy as np, pandas as pd
rt=pd.read_csv(HOME+"/mnt/Recession Papers/Paper 2/data/realtime_first_print_sahm_by_vintage.csv", parse_dates=["vintage","latest_month"])
f=rt.sort_values("vintage").drop_duplicates("latest_month",keep="first").set_index("latest_month").sort_index()
u=f.u_latest.astype(float); rel=f.vintage
REFd=[pd.Timestamp(x) for x in REF]
base=machine2(sahm_arr(0.36,1))
print("v10 baseline lags", base[1], "| ends", base[2])
out=[]
for m in (2,3,4,6):
    mu=u.rolling(m).mean()
    for L in (6,9,12,18,24):
        gap=mu-mu.rolling(L).min().shift(1)
        g=pd.Series(gap.values,index=pd.to_datetime(rel.values)).dropna()
        v=g.reindex(cal).ffill().values.astype(float)
        q=v[QC&CO&G]; q=q[np.isfinite(q)]
        if len(q)<400: continue
        qm=float(np.max(q)); sdv=float(np.nanstd(q))
        for extra in (0.01,0.02,0.03,0.05,0.08,0.12,0.18):
            th=round(qm+extra,3)
            for k in (1,2):
                a=(g>=th-1e-9)
                for j in range(1,k): a=a & g.shift(j).ge(th-1e-9)
                arrv=np.asarray(D(a.fillna(False)),bool)
                d,l,e,fa,n,arm=machine2(arrv)
                if fa or n!=9 or arm!=0 or e!=base[2]: continue
                if any(x is None or abs(x)>1 for x in l): continue
                days=sum((rd-dd).days for dd,rd in zip(d,REFd))
                out.append((extra/max(sdv,1e-9),days,m,L,th,qm,sdv,[str(x.date()) for x in d],l))
out.sort(reverse=True)
print("\nforms that keep all nine lags inside a month, ends unchanged, zero false, zero quiet arming")
print("%-30s %-9s %-8s %s" % ("form","margin sd","days +/-","changed calls"))
seen=set()
for msd,days,m,L,th,qm,sdv,d,l in out[:40]:
    key=(m,L,round(th,2))
    if key in seen: continue
    seen.add(key)
    ch=[("%s->%s"%(REF[i],d[i])) for i in range(9) if d[i]!=REF[i]]
    print("%-30s %-9.2f %-8d %s" % ("%dm mean over %2dm min >= %.3f"%(m,L,th), msd, days, ch if ch else "none"))
    if len(seen)>=10: break
if not out: print("  none")
print("\ncurrent form: 3m mean over 12m min >= 0.36, quiet max 0.333, margin 0.027")
