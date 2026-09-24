#!/usr/bin/env python3
"""CH4 supplement — complete the 17-member delta table (read-only).
The main CH4 pass found 9/17 seated members carried as current_revised bases in the live
store. This resolves the other 8:
 - 4 vintage-only (IURSA,SAHM,UNRATE,UMCSENT): store carries them ONLY as archive_snapshot_asof
   vintages; current_revised = latest ASOF vintage per observation_period -> reconstruct & measure.
 - 3 absent (NASDAQ,VIX,BAA10Y): NOT in the live acquisition store at all (site build carries
   them from method_source). Persistence taken from CH1 s6B (raw native) as the standing number.
Writes research/ only. Same CH1 hand-rolled ADF/KPSS/ACF."""
import sys,os,json,math,re
sys.path.insert(0,"live_data")
import numpy as np
from pathlib import Path
from datetime import date
from collections import defaultdict
from rmv2_live.config import load_config, load_env_file
from rmv2_live.store import LiveStore
PR=Path(".").resolve()
cfgp=PR/"live_data/config/sources.v1.json"
load_env_file(cfgp.parent/"local.env"); cfg=load_config(cfgp)
st=LiveStore(PR,cfg); st.initialize(); heads=st.all_source_heads()
def pdate(s):
    s=str(s).strip()
    m=re.match(r"^(\d{4})-Q([1-4])$",s)
    if m: return date(int(m.group(1)),(int(m.group(2))-1)*3+1,1)
    m=re.match(r"^(\d{4})-(\d{2})-(\d{2})$",s)
    if m: return date(*map(int,m.groups()))
    m=re.match(r"^(\d{4})-(\d{2})$",s)
    if m: return date(int(m.group(1)),int(m.group(2)),1)
    m=re.match(r"^(\d{4})$",s)
    if m: return date(int(m.group(1)),1,1)
    return None
def ols(X,y):
    b,_,_,_=np.linalg.lstsq(X,y,rcond=None); resid=y-X@b; n,k=X.shape
    dof=max(n-k,1); s2=(resid@resid)/dof; se=np.sqrt(np.diag(np.linalg.pinv(X.T@X))*s2); return b,se
def adf(y):
    y=np.asarray(y,float); n=len(y)
    if n<20: return None
    maxlag=min(int(12*(n/100)**0.25),n//3); dy=np.diff(y); lag=maxlag; T=len(dy)-lag
    if T<10: return None
    Y=dy[lag:]; cols=[np.ones(T),y[lag:n-1]]
    for i in range(1,lag+1): cols.append(dy[lag-i:len(dy)-i])
    try: b,se=ols(np.column_stack(cols),Y)
    except Exception: return None
    return float(b[1]/se[1]) if se[1]>0 else None
def kpss(y):
    y=np.asarray(y,float); n=len(y)
    if n<20: return None
    r=y-y.mean(); S=np.cumsum(r); l=int(4*(n/100)**0.25); s2=(r@r)/n
    for j in range(1,l+1):
        w=1-j/(l+1); s2+=2*w*(r[j:]@r[:-j])/n
    if s2<=0: return None
    return float(np.sum(S**2)/(n**2*s2))
def acf_cross(v,level):
    v=np.asarray(v,float)-np.mean(v); denom=v@v; n=len(v)
    if denom<=0: return None
    for lag in range(1,min(n-1,800)):
        if ((v[lag:]@v[:-lag])/denom)<level: return lag
    return None
def measure(dates,vals):
    n=len(vals); gaps=[(dates[i+1]-dates[i]).days for i in range(n-1) if (dates[i+1]-dates[i]).days>0]
    sp=float(np.median(gaps)) if gaps else None
    a=adf(vals); k=kpss(vals)
    astat=(a is not None and a<-2.86); kstat=(k is not None and k<0.463)
    verdict=("stationary" if astat and kstat else "nonstationary" if not astat and not kstat
             else "ambiguous")
    l1e=acf_cross(vals,1/math.e)
    return dict(n=n,spacing_days=sp,adf=(round(a,3) if a else None),adf_stationary=astat,
        kpss=(round(k,3) if k else None),kpss_stationary=kstat,stationarity=verdict,
        acf_1e_lag=l1e,derived_window_days=(round(l1e*sp) if (l1e and sp) else None))

VINTSRC={"IURSA":"fred_iursa_api_vintages","SAHM":"fred_sahmrealtime_api_vintages",
         "UNRATE":"fred_unrate_api_vintages","UMCSENT":"fred_umcsent_api_vintages"}
MEMKEY={"IURSA":"IURSA","SAHM":"SAHM","UNRATE":"UNRATEv","UMCSENT":"UMCSENT"}
INHERIT={"IURSA":370,"SAHM":None,"UNRATEv":120,"UMCSENT":370,"NASDAQ":370,"VIX":None,"BAA10Y":None}
rows=[]
for base,src in VINTSRC.items():
    norm=st.read_normalized(heads[src]["normalized_sha256"])
    # latest ASOF vintage per observation_period = current_revised proxy
    by_obs={}   # obs_date -> (asof_str, value)
    for r in norm["records"]:
        if r.get("information_set_mode")!="archive_snapshot_asof": continue
        try: fv=float(r.get("value"))
        except: continue
        od=pdate(r.get("observation_period"))
        if od is None: continue
        asof=str(r.get("series_id","")).split("ASOF")[-1]
        prev=by_obs.get(od)
        if prev is None or asof>prev[0]: by_obs[od]=(asof,fv)
    ds=sorted(by_obs); vals=[by_obs[d][1] for d in ds]
    mk=MEMKEY[base]; m=measure(ds,vals)
    rows.append(dict(member=mk,series_id=base,source_id=src,source_class="latest_vintage_reconstruction",
        inherited_window_days=INHERIT[mk],**m,
        derived_over_inherited=(round(m["derived_window_days"]/INHERIT[mk],3)
            if (m["derived_window_days"] and INHERIT[mk]) else None)))

# 3 absent — cite CH1 s6B raw persistence
ch1=json.load(open("research/channel_structure_ch1/CH1_CHANNEL_STRUCTURE_PROBE.v1.json"))
rawp={e["m"]:e for e in ch1["s6A_stationarity"]["per_member"]}
pers={e["m"]:e for e in ch1["s6B_windows"]["persistence_vs_window"]}
for mk,sid in [("NASDAQ","NASDAQCOM"),("VIX","VIXCLS"),("BAA10Y","BAA10Y")]:
    pe=pers.get(mk,{}); se=rawp.get(mk,{}).get("raw",{})
    dw=pe.get("persistence_days")
    rows.append(dict(member=mk,series_id=sid,source_id="(none: method_source only)",
        source_class="site_build_only_not_in_live_store",
        inherited_window_days=INHERIT[mk],n=None,spacing_days=pe.get("obs_spacing_days"),
        adf=se.get("adf"),adf_stationary=se.get("adf_stationary_5pct"),
        kpss=se.get("kpss"),kpss_stationary=se.get("kpss_stationary_5pct"),
        stationarity=("stationary" if se.get("adf_stationary_5pct") and se.get("kpss_stationary_5pct")
                      else "nonstationary" if not se.get("adf_stationary_5pct") and not se.get("kpss_stationary_5pct")
                      else "ambiguous"),
        acf_1e_lag=pe.get("acf_1e_lag_obs"),derived_window_days=dw,
        derived_over_inherited=(round(dw/INHERIT[mk],3) if (dw and INHERIT[mk]) else None)))

import csv
cols=["member","series_id","source_id","source_class","inherited_window_days","n","spacing_days",
      "adf","adf_stationary","kpss","kpss_stationary","stationarity","acf_1e_lag",
      "derived_window_days","derived_over_inherited"]
with open("research/ch4_member_supplement_v1.csv","w",newline="") as f:
    w=csv.DictWriter(f,fieldnames=cols); w.writeheader()
    for r in rows: w.writerow({k:r.get(k) for k in cols})
json.dump(rows,open("research/ch4_member_supplement.json","w"),indent=1,default=str)
for r in rows:
    print(f"{r['member']:8s} {r['source_class']:34s} inherit={r['inherited_window_days']} "
          f"derived={r['derived_window_days']} ratio={r['derived_over_inherited']} stat={r['stationarity']}")
print("WROTE research/ch4_member_supplement_v1.csv")
