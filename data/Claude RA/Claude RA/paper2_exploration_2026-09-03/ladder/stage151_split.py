"""Stage 151: split sample.  v14's lines are each channel's quiet record plus a quarter of a
robust standard deviation, computed over 1968-2026.  Here they are computed over the first half
of the sample only and the second half is replayed with them untouched, and then the other way
round.  Nothing in the replayed half enters the calibration."""
exec(open("stage128_ztwolane.py").read().split("def machine(c,c2")[0])
import numpy as np, pandas as pd
CH4=["Sahm","payrolls","housing","bill"]
def lines_from(mask,delta=0.25,delta2=2.0):
    L={}
    for n in CH4:
        v=np.asarray(CH[n],float)[mask&QC&G&CO]; v=v[np.isfinite(v)]
        if len(v)<500: L[n]=np.inf; continue
        med=np.median(v); mad=np.median(np.abs(v-med))*1.4826
        L[n]=float(v.max()+delta*mad)
    v=np.asarray(CH["Sahm"],float)[mask&QC&NG&CCO]; v=v[np.isfinite(v)]
    med=np.median(v); mad=np.median(np.abs(v-med))*1.4826
    return L,float(v.max()+delta2*mad)
def replay_with(L,LS,use_iur=True):
    hits=np.zeros(N,bool)
    for n in CH4:
        x=np.asarray(CH[n],float); hits|=(np.where(np.isfinite(x),x,-9e9)>=L[n])
    if use_iur: hits|=np.asarray(gapch(iur4,0.40),bool)
    fr=fresh(hits&CO,120)&G
    xs=np.asarray(CH["Sahm"],float)
    fr=fr|fresh((np.where(np.isfinite(xs),xs,-9e9)>=LS)&CCO&NG,120)
    la=fresh(np.asarray(lane_arr(vix-vix.shift(20),1,22.0),bool),120); valid=la.copy()
    for i in np.flatnonzero(np.diff(la.astype(np.int8))==1)+1:
        if not fr[i:i+121].any():
            j=i
            while j<N and la[j]: valid[j]=False; j+=1
    eps=replay(fr|valid)
    return eps,hits
CUT=pd.Timestamp("1990-01-01")
early=cal<CUT; late=cal>=CUT
T_EARLY=[t for t in T_P1 if pd.Timestamp(t[0]+"-01")<CUT]
T_LATE =[t for t in T_P1 if pd.Timestamp(t[0]+"-01")>=CUT]
for lab,calib,test,TT in [("calibrated 1968-1989, tested 1990-2026",early,late,T_LATE),
                          ("calibrated 1990-2026, tested 1968-1989",late,early,T_EARLY)]:
    L,LS=lines_from(calib)
    eps,hits=replay_with(L,LS)
    epsT=[e for e in eps if test[int(np.searchsorted(cal,e["onset"]))]]
    res,f=score_eps(epsT,TT); det=sum(1 for x in res if x["lag"] is not None)
    fa=[x for x in f]
    print("\n%s"%lab)
    print("  lines %s | clause %.3f"%({k:round(v,4) for k,v in L.items()},LS))
    print("  in the tested half: %d of %d detected, %d false | lags %s"%(det,len(TT),len(fa),[r["lag"] for r in res]))
    print("  onsets %s"%[str(e["onset"].date()) for e in epsT])
    if fa: print("  false: %s"%fa)
print("\nv14's own lines for comparison: %s"%{n:round(float(np.asarray(CH[n],float)[QC&G&CO][np.isfinite(np.asarray(CH[n],float)[QC&G&CO])].max()),4) for n in CH4})
print("\nthird test: calibrate on everything EXCEPT one recession's own decade, nine times")
DEC=[("1969-12",1965,1975),("1973-11",1970,1980),("1980-01",1976,1986),("1981-07",1977,1987),
     ("1990-07",1986,1996),("2001-03",1997,2007),("2007-12",2003,2013),("2020-02",2016,2026),("2024-04",2020,2026)]
for pk,a,b in DEC:
    m=~((pd.Series(cal).dt.year>=a)&(pd.Series(cal).dt.year<=b)).values
    L,LS=lines_from(m)
    eps,hits=replay_with(L,LS)
    res,f=score_eps(eps,T_P1)
    r=[x for x in res if x["peak"]==pk][0]
    print("  %-8s excluded %d-%d -> held-out %s (lag %s) | false episodes elsewhere %d"%(
        pk,a,b,"detected" if r["lag"] is not None else "MISSED",r["lag"],len(f) if f else 0))
