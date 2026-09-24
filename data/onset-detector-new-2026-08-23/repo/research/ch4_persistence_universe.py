#!/usr/bin/env python3
"""CH4 — persistence + transform evidence for the FULL landed universe (read-only, §20-class).
Extends CH-R21's 17-member table to every current_revised base series in the store.
Method reused verbatim from CH1 measure_2.py: hand-rolled ADF (const, MacKinnon 5% CV -2.86,
reject=stationary), KPSS level (5% CV 0.463, reject=non-stationary), native obs cadence,
lag=12*(n/100)^.25; ACF 1/e persistence * median obs spacing.  Writes research/ only."""
import sys,os,json,math,re,time
sys.path.insert(0,"live_data")
import numpy as np
from pathlib import Path
from datetime import date
from collections import defaultdict
from rmv2_live.config import load_config, load_env_file
from rmv2_live.store import LiveStore

PR=Path(".").resolve()
LOG=open("research/ch4_run.log","w")
def log(*a):
    print(*a,file=LOG,flush=True); print(*a,flush=True)

cfgp=PR/"live_data/config/sources.v1.json"
load_env_file(cfgp.parent/"local.env"); cfg=load_config(cfgp)
st=LiveStore(PR,cfg); st.initialize()
heads=st.all_source_heads()
VINT=re.compile(r"vintage|deep|asof|archive|_alfred|snapshot",re.I)

# ---- date parse ----
def pdate(s):
    s=str(s).strip()
    m=re.match(r"^(\d{4})-Q([1-4])$",s)
    if m: return date(int(m.group(1)),(int(m.group(2))-1)*3+1,1)
    m=re.match(r"^(\d{4})-(\d{2})-(\d{2})$",s)
    if m: return date(int(m.group(1)),int(m.group(2)),int(m.group(3)))
    m=re.match(r"^(\d{4})-(\d{2})$",s)
    if m: return date(int(m.group(1)),int(m.group(2)),1)
    m=re.match(r"^(\d{4})$",s)
    if m: return date(int(m.group(1)),1,1)
    return None

# ---- gather current_revised series (pick richest source per series_id) ----
t0=time.time()
cand=defaultdict(dict)   # series_id -> source_id -> {date:value}
label={}; unit={}
kept=[(h.get("record_count",0),sid) for sid,h in heads.items() if not VINT.search(sid)]
kept.sort()
log(f"sources to scan: {len(kept)}  start")
for i,(rc,sid) in enumerate(kept):
    try: norm=st.read_normalized(heads[sid]["normalized_sha256"])
    except Exception as e: log("ERR read",sid,e); continue
    n_cr=0
    for r in norm.get("records",[]):
        if r.get("information_set_mode")!="current_revised": continue
        v=r.get("value")
        try: fv=float(v)
        except: continue
        d=pdate(r.get("observation_period"))
        if d is None: continue
        si=r.get("series_id")
        if not si: continue
        cand[si].setdefault(sid,{})[d]=fv; n_cr+=1
        label.setdefault(si,r.get("label")); unit.setdefault(si,r.get("unit"))
    if i%20==0 or n_cr: log(f"  [{i+1}/{len(kept)}] {sid} cr={n_cr}  t={time.time()-t0:.0f}s")
log(f"scan done in {time.time()-t0:.0f}s; distinct current_revised series={len(cand)}")

# collapse to one series per series_id (richest source); record collisions
series={}; collisions={}
for si,bys in cand.items():
    best=max(bys,key=lambda s:len(bys[s]))
    series[si]=(best,bys[best])
    if len(bys)>1: collisions[si]={s:len(bys[s]) for s in bys}
log(f"collisions (series in >1 current source): {len(collisions)}")

# ---- CH1 hand-rolled stats ----
def ols(X,y):
    b,_,_,_=np.linalg.lstsq(X,y,rcond=None)
    resid=y-X@b; n,k=X.shape; dof=max(n-k,1); s2=(resid@resid)/dof
    xtxi=np.linalg.pinv(X.T@X); se=np.sqrt(np.diag(xtxi)*s2); return b,se,resid
def adf(y):
    y=np.asarray(y,float); n=len(y)
    if n<20: return None
    maxlag=min(int(12*(n/100)**0.25),n//3); dy=np.diff(y); lag=maxlag
    T=len(dy)-lag
    if T<10: return None
    Y=dy[lag:]; cols=[np.ones(T),y[lag:n-1]]
    for i in range(1,lag+1): cols.append(dy[lag-i:len(dy)-i])
    try:
        b,se,_=ols(np.column_stack(cols),Y)
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
ADF5=-2.86; KPSS5=0.463
def acf_cross(vals,level):
    v=np.asarray(vals,float)-np.mean(vals); denom=v@v; n=len(v)
    if denom<=0: return None
    for lag in range(1,min(n-1,800)):
        ac=(v[lag:]@v[:-lag])/denom
        if (ac<level) if level>0 else (ac<=level): return lag
    return None
def stat_verdict(vals):
    a=adf(vals); k=kpss(vals)
    astat=(a is not None and a<ADF5); kstat=(k is not None and k<KPSS5)
    if a is None or k is None: verdict="undet"
    elif astat and kstat: verdict="stationary"
    elif (not astat) and (not kstat): verdict="nonstationary"
    else: verdict="ambiguous"
    return dict(adf=(round(a,3) if a is not None else None),adf_stat=bool(astat),
                kpss=(round(k,3) if k is not None else None),kpss_stat=bool(kstat),verdict=verdict)

INV_E=1/math.e
def persist(vals,spacing):
    l1e=acf_cross(vals,INV_E); lhf=acf_cross(vals,0.5); lz=acf_cross(vals,0.0)
    dy=lambda l:(round(l*spacing) if (l and spacing) else None)
    return dict(acf_1e_lag=l1e,acf_half_lag=lhf,acf_zero_lag=lz,
                persist_1e_days=dy(l1e),half_life_days=dy(lhf),first_zero_days=dy(lz))

# ---- transforms ----
def build_transforms(dates,vals):
    n=len(vals)
    gaps=[(dates[i+1]-dates[i]).days for i in range(n-1) if (dates[i+1]-dates[i]).days>0]
    spacing=float(np.median(gaps)) if gaps else None
    out={}
    out["level"]=(vals,spacing)
    if n>=22:
        out["diff"]=([vals[i]-vals[i-1] for i in range(1,n)],spacing)
    if spacing:
        k=max(1,round(365.0/spacing))
        if n>k+21:
            out["yoy"]=([vals[i]-vals[i-k] for i in range(k,n)],spacing)  # additive yoy over ~1yr
    # z = (level-mean)/std is an affine transform => ACF/ADF/KPSS identical to level; recorded once as degenerate.
    return out,spacing,(k if spacing else None) if spacing else None

# ---- 17 site members: inherited windows + raw-source map (from CH1) ----
MEMBER_SRC={"ICSA":"ICSA","IURSA":"IURSA","SAHM":"SAHMREALTIME","UNRATEv":"UNRATE",
 "INDPRO":"INDPRO","CMRMT":"CMRMTSPL","TCU":"TCU","PHILLY":"GACDFSA066MSFRBPHI",
 "NASDAQ":"NASDAQCOM","BAA10Y":"BAA10Y","VIX":"VIXCLS","NFCI":"NFCI",
 "PERMIT":"PERMIT","HOUST":"HOUST","UMCSENT":"UMCSENT","W875":"W875RX1"}
INHERIT_WIN={"ICSA":365,"IURSA":370,"SAHM":None,"UNRATEv":120,"INDPRO":365,"CMRMT":365,
 "TCU":365,"PHILLY":None,"NASDAQ":370,"BAA10Y":None,"VIX":None,"NFCI":None,
 "PERMIT":365,"HOUST":365,"UMCSENT":370,"W875":365}
SRC2MEMBER={v:k for k,v in MEMBER_SRC.items()}

# ---- compute per series x transform ----
import csv
rows=[]; judg=[]; member_delta=[]
t1=time.time()
for si,(src,dv) in sorted(series.items()):
    ds=sorted(dv); vals=[dv[d] for d in ds]; n=len(vals)
    if n<20: continue
    tfs,spacing,k=build_transforms(ds,vals)
    verdicts={}
    per_t={}
    for tname,(tv,sp) in tfs.items():
        if len(tv)<20: continue
        sv=stat_verdict(tv); pv=persist(tv,sp)
        verdicts[tname]=sv["verdict"]
        per_t[tname]=dict(**sv,**pv,n=len(tv),spacing_days=sp,
                          derived_window_days=pv["persist_1e_days"])
        rows.append(dict(series_id=si,source_id=src,member=SRC2MEMBER.get(si,""),
            label=(label.get(si) or "")[:60],unit=unit.get(si) or "",
            transform=tname,n=len(tv),spacing_days=sp,
            adf=sv["adf"],adf_stationary=sv["adf_stat"],kpss=sv["kpss"],
            kpss_stationary=sv["kpss_stat"],stationarity=sv["verdict"],
            acf_1e_lag=pv["acf_1e_lag"],persist_1e_days=pv["persist_1e_days"],
            half_life_days=pv["half_life_days"],first_zero_days=pv["first_zero_days"],
            derived_window_days=pv["persist_1e_days"]))
    # §6A flip class: stationarity verdict changes across {level,diff,yoy}
    dv_set={t:v for t,v in verdicts.items() if v in ("stationary","nonstationary","ambiguous")}
    uniq=set(dv_set.values())
    if len(uniq)>1:
        judg.append(dict(series_id=si,member=SRC2MEMBER.get(si,""),
                         verdicts=dv_set,
                         flips="stationary" in uniq and "nonstationary" in uniq))
    # member delta vs inherited window (derived from LEVEL persistence, matching CH1 §6B raw-series rule)
    if si in SRC2MEMBER:
        mm=SRC2MEMBER[si]; lvl=per_t.get("level",{})
        member_delta.append(dict(member=mm,series_id=si,
            inherited_window_days=INHERIT_WIN[mm],
            derived_window_level_days=lvl.get("derived_window_days"),
            derived_over_inherited=(round(lvl.get("derived_window_days")/INHERIT_WIN[mm],3)
                if (lvl.get("derived_window_days") and INHERIT_WIN[mm]) else None)))
log(f"metrics done in {time.time()-t1:.0f}s; rows={len(rows)} series={len(series)} judgment={len(judg)}")

# ---- write CSV ----
cols=["series_id","source_id","member","label","unit","transform","n","spacing_days",
      "adf","adf_stationary","kpss","kpss_stationary","stationarity",
      "acf_1e_lag","persist_1e_days","half_life_days","first_zero_days","derived_window_days"]
with open("research/ch4_persistence_universe_v1.csv","w",newline="") as f:
    w=csv.DictWriter(f,fieldnames=cols); w.writeheader()
    for r in rows: w.writerow({k:r.get(k) for k in cols})

# ---- distributions of derived windows (per transform) ----
def dist(xs):
    xs=[x for x in xs if x];
    if not xs: return None
    xs=sorted(xs); import statistics as sx
    q=lambda p: xs[min(len(xs)-1,int(p*(len(xs)-1)))]
    return dict(n=len(xs),min=xs[0],p25=q(.25),median=sx.median(xs),p75=q(.75),
                p90=q(.90),max=xs[-1])
by_t=defaultdict(list)
for r in rows: by_t[r["transform"]].append(r["derived_window_days"])
dw_dist={t:dist(v) for t,v in by_t.items()}

summary=dict(
    schema_version="rmv2.ch4_persistence_universe.v1",
    batch_id="CH4_PERSISTENCE_UNIVERSE",writes_store=False,network=False,
    n_sources_scanned=len(kept),n_current_revised_series=len(series),
    n_series_measured=len({r["series_id"] for r in rows}),n_rows=len(rows),
    n_collisions=len(collisions),
    transforms_tested=["level","diff","yoy"],
    z_note="z=(x-mean)/std is affine of level; ACF/ADF/KPSS are scale/shift invariant so z is "
           "identical to level for every metric here -> reported once, not a distinct column.",
    yoy_note="yoy = additive difference over ~1yr (k=round(365/median_spacing)); sign-safe.",
    method_note="ADF const MacKinnon 5% CV -2.86 (reject=stationary); KPSS level 5% CV 0.463 "
                "(reject=nonstationary); native cadence lag=12*(n/100)^.25; persistence=ACF<1/e "
                "lag * median obs-spacing days. Verbatim from CH1 measure_2.py.",
    derived_window_rule="S6 rule: candidate look-back = 1/e ACF persistence in days (adopt nothing).",
    derived_window_distribution_by_transform=dw_dist,
    n_flip_series=len(judg),n_hard_flips=sum(1 for j in judg if j["flips"]),
    member_delta_vs_inherited=member_delta,
    collisions_sample={k:collisions[k] for k in list(collisions)[:20]},
)
json.dump(summary,open("research/CH4_PERSISTENCE_UNIVERSE.v1.json","w"),indent=1,default=str)
json.dump(judg,open("research/ch4_judgment_list.json","w"),indent=1,default=str)
log("WROTE ch4_persistence_universe_v1.csv, CH4_PERSISTENCE_UNIVERSE.v1.json, ch4_judgment_list.json")
log("DONE")
LOG.close()
