"""Stage 77: a cheaper no-inversion channel for the April-2024 case.
The Sahm clause (>=0.55, ungated) is 54% of v8's residual hazard and cannot be raised.
Search for an ungated channel that (i) fires in the 2024 window with the gate off,
(ii) has zero quiet crossings on its own record, (iii) has a larger relative margin."""
exec(open("stage46_v7.py").read().split("t6,l6=build")[0])
import numpy as np, pandas as pd, itertools, os, glob
G=np.asarray(GATE[12],bool)
ODD2=ODD
def L(path):
    try: return load(path)
    except Exception: return None
CAND={}
for nm,p in [("U6","01_labor_unemployment/monthly/U6RATE.csv"),
             ("U5","01_labor_unemployment/monthly/U5RATE.csv"),
             ("U4","01_labor_unemployment/monthly/U4RATE.csv"),
             ("PTECON","01_labor_unemployment/monthly/LNS12032194.csv"),
             ("LT27","01_labor_unemployment/monthly/UEMP27OV.csv"),
             ("MEANDUR","01_labor_unemployment/monthly/UEMPMEAN.csv"),
             ("JOLTS_SEP","02_labor_demand_vacancies/monthly/JTSTSL.csv"),
             ("JOLTS_LAY","02_labor_demand_vacancies/monthly/JTSLDL.csv"),
             ("JOLTS_HIR","02_labor_demand_vacancies/monthly/JTSHIL.csv"),
             ("JOLTS_QUIT","02_labor_demand_vacancies/monthly/JTSQUL.csv"),
             ("JOLTS_OPEN","02_labor_demand_vacancies/monthly/JTSJOL.csv"),
             ("VU","02_labor_demand_vacancies/monthly/JTSJOL.csv"),
             ("TEMPHELP","03_payroll_employment/monthly/TEMPHELPS.csv"),
             ("AWHMAN","04_hours_earnings/monthly/AWHMAN.csv"),
             ("HOURSIDX","04_hours_earnings/monthly/AWHAETP.csv")]:
    s=L(os.path.join(ODD2,p))
    if s is not None and len(s)>60: CAND[nm]=s
print("loaded:", sorted(CAND))
W24=(pd.Timestamp("2024-03-01"),pd.Timestamp("2024-09-01"))
WINS=[(pd.Timestamp(p),pd.Timestamp(t)) for p,t in T_P1]
def quiet_mask(idx):
    q=pd.Series(True,index=idx)
    for p,t in WINS: q &= ~((idx>=p-pd.DateOffset(months=6))&(idx<=t+pd.DateOffset(months=12)))
    return q
print("\n%-12s %-22s %8s %9s %9s %8s %s" % ("series","statistic","2024 pk","quiet max","margin","m/range","verdict"))
best=[]
for nm,s in CAND.items():
    idx=s.index
    q=quiet_mask(idx)
    stats={}
    up = nm in ("U6","U5","U4","PTECON","LT27","MEANDUR","JOLTS_SEP","JOLTS_LAY")
    for w in (3,6,12):
        x=s.rolling(3).mean()
        stats["gap%dm"%w] = (x - s.rolling(w).min()) if up else (s.rolling(w).max() - x)
        stats["pct%dm"%w] = ((x/s.shift(w)-1)*100) * (1 if up else -1)
    for k,v in stats.items():
        v=v.dropna()
        if len(v)<120: continue
        w24=v[(v.index>=W24[0])&(v.index<=W24[1])]
        if not len(w24): continue
        pk=float(w24.max()); qm=float(v[q.reindex(v.index).fillna(False)].max())
        rng=float(v.max()-v.min())
        if pk<=qm or rng<=0: continue
        marg=(pk-qm); rel=marg/rng
        best.append((rel,nm,k,pk,qm,marg))
best.sort(reverse=True)
for rel,nm,k,pk,qm,marg in best[:12]:
    print("%-12s %-22s %8.3f %9.3f %9.3f %8.3f %s" % (nm,k,pk,qm,marg,rel,"clean, margin %.0f%% of range"%(100*rel)))
if not best: print("  none clean")
