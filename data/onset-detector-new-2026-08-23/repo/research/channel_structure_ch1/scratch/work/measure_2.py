#!/usr/bin/env python3
"""CH1 part 2 — §4 lead/lag, §6A stationarity (hand-rolled ADF/KPSS), §6B persistence/
windows, §6C staircase. READ-ONLY. Writes JSON in scratch/work."""
import sys, os, json, math, datetime as dt, bisect
import numpy as np
HERE=os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE,"..","..","..","..","method_source")))
os.chdir(HERE)
os.environ["NOWCAST_DISABLE"]="1"
import index_v1 as ix
OUT={}
MEM17=["ICSA","IURSA","SAHM","UNRATEv","INDPRO","CMRMT","TCU","PHILLY","NASDAQ",
       "BAAAAA","BAA10Y","VIX","NFCI","PERMIT","HOUST","UMCSENT","W875"]
CH=ix.CHANNELS; DAYS=ix.DAYS
# raw source per member (for stationarity on raw)
RAWSRC={"ICSA":"ICSA","IURSA":"IURSA","SAHM":"SAHMREALTIME","UNRATEv":"UNRATE",
 "INDPRO":"INDPRO","CMRMT":"CMRMTSPL","TCU":"TCU","PHILLY":"GACDFSA066MSFRBPHI",
 "NASDAQ":"NASDAQCOM","BAAAAA":None,"BAA10Y":"BAA10Y","VIX":"VIXCLS","NFCI":"NFCI",
 "PERMIT":"PERMIT","HOUST":"HOUST","UMCSENT":"UMCSENT","W875":"W875RX1"}
def raw_series(m):
    return ix.BAAAAA if m=="BAAAAA" else ix.S[RAWSRC[m]]
def as_arr(series):
    ks=sorted(series); return np.array([series[k] for k in ks],float), ks

# ---------- OLS helper ----------
def ols(X,y):
    b,_,_,_=np.linalg.lstsq(X,y,rcond=None)
    resid=y-X@b; n,k=X.shape
    dof=max(n-k,1); s2=(resid@resid)/dof
    xtxi=np.linalg.pinv(X.T@X); se=np.sqrt(np.diag(xtxi)*s2)
    return b,se,resid

def adf(y,maxlag=None):
    y=np.asarray(y,float); n=len(y)
    if n<20: return None
    if maxlag is None: maxlag=int(12*(n/100)**0.25); maxlag=min(maxlag,n//3)
    dy=np.diff(y); lag=maxlag
    # build regression Δy_t = a + b*y_{t-1} + Σ c_i Δy_{t-i}
    T=len(dy)-lag
    if T<10: return None
    Y=dy[lag:]
    cols=[np.ones(T), y[lag:-1]]
    for i in range(1,lag+1): cols.append(dy[lag-i:-i] if i<lag else dy[lag-i:len(dy)-i])
    # rebuild lagged diffs cleanly
    cols=[np.ones(T), y[lag:n-1]]
    for i in range(1,lag+1): cols.append(dy[lag-i:len(dy)-i])
    X=np.column_stack(cols)
    b,se,_=ols(X,Y)
    stat=b[1]/se[1] if se[1]>0 else None
    return stat
def kpss(y):
    y=np.asarray(y,float); n=len(y)
    if n<20: return None
    r=y-y.mean(); S=np.cumsum(r)
    l=int(4*(n/100)**0.25)
    s2=(r@r)/n
    for j in range(1,l+1):
        w=1-j/(l+1); s2+=2*w*(r[j:]@r[:-j])/n
    if s2<=0: return None
    return float(np.sum(S**2)/(n**2*s2))
ADF_CV={"1%":-3.43,"5%":-2.86,"10%":-2.57}   # constant, large-n MacKinnon approx
KPSS_CV={"1%":0.739,"5%":0.463,"10%":0.347}

# ---------- §6A stationarity on raw and transformed (native cadence) ----------
def stat_row(vals):
    a=adf(vals); k=kpss(vals)
    adf_stationary = (a is not None and a < ADF_CV["5%"])
    kpss_stationary = (k is not None and k < KPSS_CV["5%"])
    return {"adf": round(a,3) if a is not None else None,
            "adf_stationary_5pct": bool(adf_stationary),
            "kpss": round(k,3) if k is not None else None,
            "kpss_stationary_5pct": bool(kpss_stationary),
            "agree": bool(adf_stationary==kpss_stationary)}
# which transform each member gets (from code)
TRANSFORM={"ICSA":"yoy","IURSA":"rise_floor370","SAHM":"none","UNRATEv":"rise_floor120",
 "INDPRO":"yoy","CMRMT":"yoy","TCU":"yoy","PHILLY":"none","NASDAQ":"drawdown",
 "BAAAAA":"none","BAA10Y":"none","VIX":"none","NFCI":"none","PERMIT":"yoy",
 "HOUST":"yoy","UMCSENT":"drawdown","W875":"yoy"}
s6a=[]
for m in MEM17:
    rv,_=as_arr(raw_series(m))
    tv,_=as_arr(ix.T[m])
    raw=stat_row(rv); tr=stat_row(tv)
    # what a test would choose: if raw already stationary -> none; else needs transform
    test_says = "none" if raw["kpss_stationary_5pct"] and raw["adf_stationary_5pct"] else "transform"
    code_applies = "none" if TRANSFORM[m]=="none" else "transform"
    s6a.append({"m":m,"transform":TRANSFORM[m],"raw":raw,"transformed":tr,
                "test_says":test_says,"code_applies":code_applies,
                "disagree": test_says!=code_applies,
                "transform_fixed": bool(tr["kpss_stationary_5pct"] and tr["adf_stationary_5pct"])})
OUT["s6A_stationarity"]=s6a
OUT["s6A_note"]="ADF (constant, MacKinnon 5% CV -2.86; reject=stationary). KPSS level (5% CV 0.463; reject=NON-stationary). Native obs cadence, not daily grid. lag=12*(n/100)^.25."

# ---------- §6B persistence / windows ----------
def acf_cross(vals, level=1/math.e):
    v=np.asarray(vals,float)-np.mean(vals); n=len(v); denom=v@v
    if denom<=0: return None
    for lag in range(1,min(n-1,600)):
        ac=(v[lag:]@v[:-lag])/denom
        if ac<level: return lag
    return None
WINDOW={"ICSA":365,"IURSA":370,"SAHM":None,"UNRATEv":120,"INDPRO":365,"CMRMT":365,
 "TCU":365,"PHILLY":None,"NASDAQ":370,"BAAAAA":None,"BAA10Y":None,"VIX":None,"NFCI":None,
 "PERMIT":365,"HOUST":365,"UMCSENT":370,"W875":365}
# persistence measured on raw native series; convert lag(obs) -> days via median obs spacing
def obs_spacing_days(ks):
    if len(ks)<2: return None
    dd=[(ks[i+1]-ks[i]).days for i in range(len(ks)-1)]
    return float(np.median(dd))
s6b=[]
for m in MEM17:
    rv,ks=as_arr(raw_series(m))
    sp=obs_spacing_days(ks)
    lag=acf_cross(rv)
    pers_days=(lag*sp) if (lag is not None and sp) else None
    s6b.append({"m":m,"transform_window_days":WINDOW[m],
                "acf_1e_lag_obs":lag,"obs_spacing_days":sp,
                "persistence_days":round(pers_days,0) if pers_days else None})
OUT["s6B_persistence"]=s6b
OUT["s6B_note"]="persistence = lag (in obs) at which raw-series ACF falls below 1/e, times median obs spacing (days). transform_window is the code's fixed look-back."

# §6B.3 sensitivity: recompute windowed transforms at alt windows, measure z & headline move
def rise_floor_look(series,look):
    from collections import deque
    ks=sorted(series); vals=[series[k] for k in ks]; lo=0; dq=deque(); out={}
    for i,k in enumerate(ks):
        while lo<i and (k-ks[lo]).days>look: lo+=1
        while dq and dq[0]<lo: dq.popleft()
        while dq and vals[dq[-1]]>=vals[i]: dq.pop()
        dq.append(i); out[k]=series[k]-vals[dq[0]]
    return out
def drawdown_look(series,look):
    from collections import deque
    ks=sorted(series); vals=[series[k] for k in ks]; lo=0; dq=deque(); mx={}
    for i,k in enumerate(ks):
        while lo<i and (k-ks[lo]).days>look: lo+=1
        while dq and dq[0]<lo: dq.popleft()
        while dq and vals[dq[-1]]<=vals[i]: dq.pop()
        dq.append(i); mx[k]=vals[dq[0]]
    return {k:(series[k]/mx[k]-1)*100 if mx[k] else 0 for k in ks}
def yoy_look(series,daysback):
    out={};ks=sorted(series)
    for k in ks:
        prior=k-dt.timedelta(days=daysback); i=bisect.bisect_left(ks,prior)
        cand=[x for x in ks[max(0,i-1):i+2] if abs((x-prior).days)<=20]
        if cand:
            p=min(cand,key=lambda x:abs((x-prior).days))
            if series[p]!=0: out[k]=(series[k]/series[p]-1)*100
    return out
def zseries(transf):  # standardize a transform dict on baseline (current baseline)
    ks=sorted(transf); base=[transf[k] for k in ks if ix.is_baseline(k)]
    mu=sum(base)/len(base); sd=(sum((x-mu)**2 for x in base)/len(base))**.5 or 1.0
    return {k:(transf[k]-mu)/sd for k in ks}, mu, sd
def zval_from(zdict,keys,d):
    i=bisect.bisect_right(keys,d)-1; return zdict[keys[i]] if i>=0 else None
sens=[]
tests={"IURSA":("rise_floor",370,[180,555]),"UNRATEv":("rise_floor",120,[60,240]),
       "NASDAQ":("drawdown",370,[185,740]),"UMCSENT":("drawdown",370,[185,740]),
       "ICSA":("yoy",365,[180,730]),"INDPRO":("yoy",365,[180,730])}
for m,(kind,base,alts) in tests.items():
    src={"IURSA":"IURSA","UNRATEv":"UNRATE","NASDAQ":"NASDAQCOM","UMCSENT":"UMCSENT",
         "ICSA":"ICSA","INDPRO":"INDPRO"}[m]
    ser=ix.S[src]
    def mk(look):
        if kind=="rise_floor": t=rise_floor_look(ser,look)
        elif kind=="drawdown": t={k:-v for k,v in drawdown_look(ser,look).items()}
        else: t={k:-v for k,v in yoy_look(ser,look).items()} if m in("INDPRO",) else yoy_look(ser,look)
        z,_,_=zseries(t); return z,sorted(z)
    z0,k0=mk(base)
    row={"m":m,"kind":kind,"base_window":base,"alts":{}}
    grid=[d for d in DAYS[::7]]
    v0=np.array([zval_from(z0,k0,d) for d in grid],float)
    for a in alts:
        za,ka=mk(a); va=np.array([zval_from(za,ka,d) for d in grid],float)
        mask=np.isfinite(v0)&np.isfinite(va)
        corr=float(np.corrcoef(v0[mask],va[mask])[0,1]) if mask.sum()>30 else None
        rms=float(np.sqrt(np.nanmean((v0[mask]-va[mask])**2))) if mask.sum()>30 else None
        row["alts"][a]={"z_corr_vs_base":round(corr,3) if corr else None,
                        "z_rmsd":round(rms,3) if rms else None}
    sens.append(row)
OUT["s6B3_sensitivity"]=sens

# ---------- §6C staircase ----------
# per day: age of freshest member obs per channel; change vs carry-forward repeat
memkeys={m:sorted(ix.T[m]) for m in MEM17}
def fresh_age(m,d):
    ks=memkeys[m]; i=bisect.bisect_right(ks,d)-1
    return (d-ks[i]).days if i>=0 else None
ages=[]; change_days=0; total=0
# per-channel freshest = min age among members that exist
era_bins={}
for d in DAYS:
    total+=1
    day_ages=[]; any_new=False
    for ch,(w,mem) in CH.items():
        m_ages=[fresh_age(m,d) for m in mem]; m_ages=[a for a in m_ages if a is not None]
        if m_ages:
            day_ages.append(min(m_ages))
            if 0 in m_ages: any_new=True
    if day_ages: ages.append(max(day_ages))  # coarsest channel age that day
    if any_new: change_days+=1
    era_bins.setdefault(d.year//10*10,[]).append(max(day_ages) if day_ages else 0)
ages=np.array(ages)
OUT["s6C_staircase"]={
 "age_days_of_coarsest_channel": {"p50":float(np.percentile(ages,50)),
    "p90":float(np.percentile(ages,90)),"p99":float(np.percentile(ages,99)),
    "max":float(ages.max())},
 "carryforward_repeat_fraction": round(1-change_days/total,4),
 "change_days":change_days,"total_days":total}
# effective resolution per era (median coarsest age)
OUT["s6C_resolution_by_decade"]={str(k):round(float(np.median(v)),1) for k,v in sorted(era_bins.items())}

with open("results_2.json","w") as f: json.dump(OUT,f,indent=1,default=str)
print("PART2 DONE:", list(OUT.keys()))
