#!/usr/bin/env python3
"""CH-R56 — COLLINEARITY ON THE INSTRUMENTABLE 18 (read-only, §20-class).
Redo the twin/collinearity map on exactly the 18 vintage-lane (as-of-instrumentable)
bases. Transformed-signal correlations (CH-R21 lesson), effective independent count vs
CH3-R2's Horn 2 / Kaiser 3, realized-vs-nominal weight (de-dup diagnosis), load-bearing
vs redundant-passenger ranking. numpy only. Zero store writes. Outputs research/ only.

DO NOT propose a member set or weighting (S5/S3 owner sittings). Measure and rank only."""
import os, json, glob, bisect, re, datetime as dt
import numpy as np
np.random.seed(20260806)

REPO="/Users/anthonyhall/Desktop/RecessionMonitor 2/Recession Monitor V2"
NORM=REPO+"/live_data/store/normalized"

# the 18 named in the batch (GACDFSA066...PHI = GACDFSA066MSFRBPHI)
WANT=["CLAIMSx","CMRMTSPL","CMRMTSPLx","GACDFSA066MSFRBPHI","GDPC1","HOUST","ICSA",
      "INDPRO","IURSA","NFCI","PAYEMS","PERMIT","RTDSM_RUC","SAHMREALTIME","TCU",
      "UMCSENT","UNRATE","W875RX1"]
WANTSET=set(WANT)

# nominal channel assignment (inherited monitor's grouping, for realized-vs-nominal)
LABOR={"UNRATE","PAYEMS","ICSA","CLAIMSx","IURSA","SAHMREALTIME"}
PRODUCTION={"INDPRO","TCU","CMRMTSPL","CMRMTSPLx","W875RX1","GDPC1"}
HOUSING={"HOUST","PERMIT"}
FINANCIAL={"NFCI"}
SENTIMENT={"UMCSENT","GACDFSA066MSFRBPHI"}
REALTIME={"RTDSM_RUC"}
CHANNEL={}
for grp,name in [(LABOR,"labor"),(PRODUCTION,"production"),(HOUSING,"housing"),
                 (FINANCIAL,"financial"),(SENTIMENT,"sentiment"),(REALTIME,"realtime")]:
    for b in grp: CHANNEL[b]=name

WIN_START=dt.date(2000,1,1); WIN_END=dt.date(2024,12,1)
months=[]; y,mo=WIN_START.year,WIN_START.month
while dt.date(y,mo,1)<=WIN_END:
    months.append(dt.date(y,mo,1)); mo+=1
    if mo>12: mo=1; y+=1
MONTH_ORD=[d.toordinal() for d in months]; NM=len(months)

def parse_period(s):
    try:
        if "Q" in s: yy,q=s.split("-Q"); return dt.date(int(yy),(int(q)-1)*3+1,1).toordinal()
        p=s.split("-")
        if len(p)==1: return dt.date(int(p[0]),1,1).toordinal()
        if len(p)==2: return dt.date(int(p[0]),int(p[1]),1).toordinal()
        return dt.date(int(p[0]),int(p[1]),int(p[2])).toordinal()
    except: return None

def month_end(pairs):
    pairs=sorted(set(pairs)); ks=[p[0] for p in pairs]; vv=[p[1] for p in pairs]
    out=np.full(NM,np.nan)
    for i,mo in enumerate(MONTH_ORD):
        j=bisect.bisect_right(ks,mo)-1
        if j>=0: out[i]=vv[j]
    return out

def vintage_key(sid):
    m=re.search(r'(?:ASOF|DEEPASOF)(\d{6,8})', sid)
    return m.group(1) if m else ""

# ---- single scan: collect cr obs and asof obs for the 18 bases only ----
cr_obs={}   # sid -> [(ord,val)]
as_obs={}   # sid -> [(ord,val)]
for f in sorted(glob.glob(NORM+"/sha256/*/*.json")):
    try: d=json.load(open(f))
    except: continue
    for r in d.get("records",[]):
        sid=r.get("series_id")
        if not sid: continue
        base=sid.split(".")[0]
        if base not in WANTSET: continue
        m=r.get("information_set_mode")
        op=r.get("observation_period"); v=r.get("value")
        if op is None or v in (None,"","."): continue
        o=parse_period(op)
        if o is None: continue
        try: fv=float(v)
        except: continue
        if m=="current_revised": cr_obs.setdefault(sid,[]).append((o,fv))
        elif m=="archive_snapshot_asof": as_obs.setdefault(sid,[]).append((o,fv))

# representative per base: richest current_revised; else newest-vintage asof proxy (FLAGGED)
by_base_cr={}
for sid in cr_obs: by_base_cr.setdefault(sid.split(".")[0],[]).append(sid)
by_base_as={}
for sid in as_obs: by_base_as.setdefault(sid.split(".")[0],[]).append(sid)

rep={}  # base -> (sid, mode, obs)
for base in WANT:
    if base in by_base_cr:
        best=max(by_base_cr[base], key=lambda s: len(cr_obs[s]))
        rep[base]=(best,"current_revised",cr_obs[best])
    elif base in by_base_as:
        # newest vintage; tie-break richest
        cand=by_base_as[base]
        best=max(cand, key=lambda s:(vintage_key(s), len(as_obs[s])))
        rep[base]=(best,"latest_vintage_proxy",as_obs[best])
    else:
        rep[base]=(None,"ABSENT",[])

# ---- transform (per-base ADF level-or-yoy; identical rule to CH3-R2) ----
ADF5=-2.86
def adf_stat(yv):
    yv=np.asarray(yv,float); n=len(yv)
    if n<24: return None
    dy=np.diff(yv); p=min(4,n//4); T=n-1-p
    if T<12: return None
    yl=yv[p:n-1]; X=[np.ones(T),yl]
    for i in range(1,p+1): X.append(dy[p-i:n-1-i])
    X=np.column_stack(X); Y=dy[p:]
    try:
        beta,*_=np.linalg.lstsq(X,Y,rcond=None)
        resid=Y-X@beta; s2=resid@resid/(T-X.shape[1])
        se=np.sqrt(s2*np.linalg.pinv(X.T@X)[1,1]); return beta[1]/se if se>0 else None
    except: return None
def yoy12(col):
    out=np.full(NM,np.nan)
    for i in range(12,NM):
        if not np.isnan(col[i]) and not np.isnan(col[i-12]) and col[i-12]!=0:
            out[i]=(col[i]/col[i-12]-1)*100
    return out

kept=[]; cols=[]; meta=[]; dropped=[]
for base in WANT:
    sid,mode,obs=rep[base]
    if sid is None: dropped.append({"base":base,"reason":"absent from store"}); continue
    col=month_end(obs)
    if np.isnan(col[12:]).any():
        dropped.append({"base":base,"reason":"coverage gap in 2001-2024 window","mode":mode}); continue
    st=adf_stat(col[12:])
    if st is not None and st<ADF5:
        use=col[12:]; tr="level"
    else:
        yy=yoy12(col)
        if np.isnan(yy[12:]).any() or np.nanstd(yy[12:])==0:
            dropped.append({"base":base,"reason":"nonstationary, no clean yoy","mode":mode}); continue
        use=yy[12:]; tr="yoy"
    if np.nanstd(use)==0:
        dropped.append({"base":base,"reason":"zero variance","mode":mode}); continue
    kept.append(base); cols.append(use)
    meta.append({"base":base,"rep_series":sid,"source_mode":mode,"transform":tr,
                 "channel_nominal":CHANNEL.get(base,"?"),"adf_t":round(st,3) if st is not None else None})
X=np.column_stack(cols); used_months=months[12:]
n_obs,n_ser=X.shape
pos={b:i for i,b in enumerate(kept)}

Xs=(X-X.mean(0))/X.std(0)
C=np.corrcoef(Xs.T)

# ---- 1. pairwise correlation, flag >0.9 / >0.8 ----
pairs=[]
for i in range(n_ser):
    for j in range(i+1,n_ser):
        r=float(C[i,j])
        pairs.append({"a":kept[i],"b":kept[j],"r":round(r,3),"abs_r":round(abs(r),3),
                      "flag":(">0.9" if abs(r)>0.9 else (">0.8" if abs(r)>0.8 else ""))})
pairs.sort(key=lambda p:-p["abs_r"])
above9=[p for p in pairs if p["abs_r"]>0.9]
above8=[p for p in pairs if p["abs_r"]>0.8]

# ---- 2. effective independent count (Horn/Kaiser) ----
def eig_counts(Xmat,nsim=200):
    m,p=Xmat.shape
    Z=(Xmat-Xmat.mean(0))/Xmat.std(0)
    Cc=np.corrcoef(Z.T)
    ev=np.linalg.eigvalsh(Cc)[::-1]; ev=np.clip(ev,0,None)
    kaiser=int(np.sum(ev>1))
    rnd=np.zeros((nsim,p))
    for k in range(nsim):
        R=np.random.standard_normal((m,p))
        e=np.linalg.eigvalsh(np.corrcoef(R.T))[::-1]; rnd[k]=e
    p95=np.percentile(rnd,95,axis=0)
    horn=int(np.sum((ev>p95)&(ev>1e-9)))
    top=ev[:min(12,p)]; gaps=top[:-1]-top[1:]
    elbow=int(np.argmax(gaps))+1 if len(gaps)>0 else 0
    # effective rank (participation ratio of eigenvalues) & 90% var
    pr=float((ev.sum()**2)/np.sum(ev**2))
    cum=np.cumsum(ev)/ev.sum()
    n90=int(np.searchsorted(cum,0.90)+1)
    return {"n_series":p,"n_obs":m,"kaiser":kaiser,"horn_parallel_95":horn,
            "scree_elbow":elbow,"participation_ratio":round(pr,2),
            "n_factors_90pct_var":n90,
            "eigs":[round(float(x),3) for x in ev],
            "var_share":[round(float(x/ev.sum()),4) for x in ev],
            "horn_p95":[round(float(x),3) for x in p95]}, ev
counts, ev = eig_counts(X)

# ---- loadings on top factors (from correlation matrix eig) ----
gev,gvec=np.linalg.eigh(C); o=np.argsort(gev)[::-1]; gev=gev[o]; gvec=gvec[:,o]
NF=max(3,counts["horn_parallel_95"])
NF=min(NF,n_ser)
load=gvec[:,:NF]*np.sqrt(np.clip(gev[:NF],0,None))   # n_ser x NF loadings
top_factor=[int(np.argmax(np.abs(load[i]))) for i in range(n_ser)]
for i,mt in enumerate(meta):
    mt["top_factor"]=top_factor[i]
    mt["loadings"]=[round(float(load[i,j]),3) for j in range(NF)]

top_loader_per_factor={}
for fn in range(NF):
    idx=np.argsort(np.abs(load[:,fn]))[::-1]
    top_loader_per_factor[fn]=[{"base":kept[j],"loading":round(float(load[j,fn]),3)} for j in idx[:6]]

# ---- 3. realized vs nominal weight ----
# SIGN-ALIGN each series to the common cycle (sign of its factor-0 loading) before the
# composite: an unsigned composite makes pro-cyclical (PAYEMS) and counter-cyclical
# (UNRATE) labor series cancel, spuriously zeroing the labor channel. Aligned so
# "moves-with-the-common-cycle" is +. Factor structure & raw pair-r below stay UNSIGNED.
flip=np.sign(load[:,0]); flip[flip==0]=1.0
Ca=C*np.outer(flip,flip)             # correlation matrix in aligned frame
for i,mt in enumerate(meta): mt["cycle_sign"]=int(flip[i])
# equal-weight standardized aligned composite I = mean_i (flip_i * z_i).
# realized contribution of base i = cov(a_i,I)/Var(I) = (1/p) sum_j corr_aligned(i,j)/Var(I)
VarI=float(np.mean(Ca))              # Var of equal-weight mean of aligned standardized cols
contrib=(Ca.mean(axis=1))/ (n_ser*VarI)   # per base, sums to 1
realized_base={kept[i]:round(float(contrib[i]),4) for i in range(n_ser)}
# channel realized vs nominal-equal (each base nominal 1/n)
chan_real={}; chan_n={}
for i in range(n_ser):
    ch=CHANNEL.get(kept[i],"?")
    chan_real[ch]=chan_real.get(ch,0.0)+float(contrib[i])
    chan_n[ch]=chan_n.get(ch,0)+1
realized_channel={ch:{"realized_weight":round(chan_real[ch],4),
                      "nominal_equal_weight":round(chan_n[ch]/n_ser,4),
                      "n_bases":chan_n[ch]} for ch in sorted(chan_real)}

# de-dup diagnosis: cluster the 18, sum realized contribution per cluster; if a cluster
# of near-twins dominates, weighting problem is de-duplication.
D=1-np.abs(C); np.fill_diagonal(D,0.0)
def hclust_labels(D,k):
    n=D.shape[0]
    comp={i:[i] for i in range(n)}; active=list(range(n))
    dist={(a,b):D[a,b] for a in range(n) for b in range(a+1,n)}
    def gd(i,j): return dist.get((i,j),dist.get((j,i)))
    nid=n
    while len(active)>k:
        best=None;bp=None
        for ii in range(len(active)):
            for jj in range(ii+1,len(active)):
                a,b=active[ii],active[jj]; dd=gd(a,b)
                if best is None or dd<best: best=dd; bp=(a,b)
        a,b=bp
        na,nb=len(comp[a]),len(comp[b])
        for c in active:
            if c in (a,b): continue
            nd=(gd(a,c)*na+gd(b,c)*nb)/(na+nb)
            dist[(min(nid,c),max(nid,c))]=nd
        comp[nid]=comp[a]+comp[b]; del comp[a]; del comp[b]
        active=[c for c in active if c not in (a,b)]+[nid]; nid+=1
    lab=np.empty(n,dtype=int)
    for ci,(cid,mem) in enumerate(comp.items()):
        for m in mem: lab[m]=ci
    return lab
kcl=max(2,counts["horn_parallel_95"])
clab=hclust_labels(D,kcl)
for i,mt in enumerate(meta): mt["cluster_id"]=int(clab[i])
cluster_contrib={}
for i in range(n_ser):
    c=int(clab[i])
    cluster_contrib.setdefault(c,{"bases":[],"realized_weight":0.0})
    cluster_contrib[c]["bases"].append(kept[i])
    cluster_contrib[c]["realized_weight"]+=float(contrib[i])
for c in cluster_contrib:
    cluster_contrib[c]["realized_weight"]=round(cluster_contrib[c]["realized_weight"],4)
    cluster_contrib[c]["n"]=len(cluster_contrib[c]["bases"])

# ---- 4. what breaks if a member is dropped ----
# drop-one Horn (coarse: Horn is over-determined, rarely moves) kept for the record.
drop_one=[]
for i in range(n_ser):
    idx=[j for j in range(n_ser) if j!=i]
    dc,_=eig_counts(X[:,idx])
    drop_one.append({"drop":kept[i],"horn_after":dc["horn_parallel_95"],
        "kaiser_after":dc["kaiser"],"horn_delta":dc["horn_parallel_95"]-counts["horn_parallel_95"]})
# redundancy: max |r| to any OTHER base + nearest twin. A base with no near-twin (max|r|<0.8)
# carries variance nobody else does -> load-bearing. A base with a >=0.9 twin is a passenger
# (its factor is safe if it is dropped). is_top_loader = the largest |loading| on its factor.
factor_membership={}
for fn in range(NF):
    loaders=sorted([kept[j] for j in range(n_ser)],key=lambda b:-abs(load[kept.index(b),fn]))
    factor_membership[fn]=[b for b in loaders if top_factor[kept.index(b)]==fn]
top_loader_of_factor={fn:(factor_membership[fn][0] if factor_membership[fn] else None) for fn in range(NF)}
redundancy=[]
for i in range(n_ser):
    others=[(kept[j],abs(C[i,j]),float(C[i,j])) for j in range(n_ser) if j!=i]
    others.sort(key=lambda x:-x[1]); nb,mar,mr=others[0]
    is_top=(kept[i] in top_loader_of_factor.values())
    redundancy.append({"base":kept[i],"max_abs_r_to_other":round(mar,3),"nearest_twin":nb,
        "nearest_r":round(mr,3),"top_factor":top_factor[i],"is_factor_top_loader":is_top,
        "realized_weight":round(float(contrib[i]),4)})
redundancy.sort(key=lambda d:d["max_abs_r_to_other"])
loadbearing=[d["base"] for d in redundancy if d["max_abs_r_to_other"]<0.8 or d["is_factor_top_loader"]]
passengers=[d["base"] for d in redundancy if d["base"] not in loadbearing]

OUT={"CH_R56_instrumentable_collinearity":{
 "scope":{
   "requested_18":WANT,"kept":kept,"n_kept":n_ser,"dropped":dropped,
   "analysis_window":f"{used_months[0]}..{used_months[-1]} monthly, {n_obs} rows (2000 window, 12mo yoy warmup dropped)",
   "transform_rule":"per-base ADF(const) t<-2.86 -> level, else 12mo %-change (CH-R21 lesson: raw-level correlations mislead)",
   "representative_rule":"one per base; current_revised richest series; else newest archive_snapshot_asof vintage as current-proxy (FLAGGED source_mode)",
   "W875RX1_caveat":"CH-R22 warning honored: representative is a single W875RX1 construct; panel-W875RX1 and store deep-lane as-of are NOT merged here.",
   "CMRMTSPL_vs_CMRMTSPLx":"kept as two distinct bases; their measured r is reported below (do not assume identity)."},
 "pairwise_correlation":{
   "n_pairs":len(pairs),
   "n_above_0_9":len(above9),"n_above_0_8":len(above8),
   "pairs_above_0_9":above9,
   "pairs_above_0_8_only":[p for p in above8 if p["abs_r"]<=0.9],
   "top20_by_abs_r":pairs[:20],
   "CMRMTSPL_CMRMTSPLx_r": next((p["r"] for p in pairs if set([p["a"],p["b"]])==set(["CMRMTSPL","CMRMTSPLx"])), None)},
 "effective_independent_count":{
   **{k:counts[k] for k in ["n_series","n_obs","kaiser","horn_parallel_95","scree_elbow","participation_ratio","n_factors_90pct_var","eigs","var_share","horn_p95"]},
   "chr3r2_reference":{"horn":2,"kaiser":3},
   "gap_explanation":None},  # filled below
 "realized_vs_nominal_weight":{
   "method":"sign-aligned (to factor-0 / common-cycle) equal-weight standardized composite I=mean(flip*z); realized contribution_i=cov(a_i,I)/Var(I), sums to 1. Sign alignment prevents pro/counter-cyclical labor series from cancelling.",
   "Var_equal_weight_composite":round(VarI,4),
   "realized_weight_per_base":realized_base,
   "realized_vs_nominal_channel":realized_channel,
   "cluster_realized_weight":cluster_contrib,
   "dedup_diagnosis":None},  # filled below
 "load_bearing":{
   "n_factors_used":NF,
   "top_loader_per_factor":top_loader_per_factor,
   "factor_membership_by_topload":factor_membership,
   "top_loader_of_each_factor":top_loader_of_factor,
   "redundancy_ranking":redundancy,
   "drop_one_horn":drop_one,
   "criterion":"load-bearing = no near-twin (max|r|<0.8) OR sole top-loader of a factor; passenger = has a twin AND not a factor's top loader",
   "load_bearing_bases":loadbearing,
   "redundant_passenger_bases":passengers},
 "NO_ADOPTION":"evidence only. Does NOT propose a member set (S5) or weighting (S3). Rankings are recommendations at most."}}

# gap explanation (Horn here vs CH3-R2's Horn 2)
here_horn=counts["horn_parallel_95"]
OUT["CH_R56_instrumentable_collinearity"]["effective_independent_count"]["gap_explanation"]=(
  f"CH-R56 restricted to the {n_ser} instrumentable bases (correlation-matrix Horn) yields "
  f"Horn={here_horn}/Kaiser={counts['kaiser']}; CH3-R2 reported Horn 2 / Kaiser 3 on a "
  f"Gram-trick covariance eig. Difference is method (corr-matrix vs standardized-Gram) and "
  f"whether latest-vintage-proxy bases enter; participation ratio {counts['participation_ratio']} "
  f"and {counts['n_factors_90pct_var']} factors to 90% var bracket the true effective count.")

# dedup diagnosis text
maxcl=max(cluster_contrib.values(),key=lambda c:c["realized_weight"])
OUT["CH_R56_instrumentable_collinearity"]["realized_vs_nominal_weight"]["dedup_diagnosis"]=(
  f"{len(above9)} pairs exceed |r|>0.9, {len(above8)} exceed 0.8. Largest near-twin cluster "
  f"{maxcl['bases']} carries realized weight {maxcl['realized_weight']} of 1.0 across {maxcl['n']} bases. "
  f"If a handful of twins concentrate realized weight, S3's weighting problem is first a "
  f"DE-DUPLICATION problem (thin twins before weighting), not a pure weight-tuning problem.")

json.dump(OUT,open(REPO+"/research/instrumentable_collinearity_v1.json","w"),indent=1,default=str)

import csv
with open(REPO+"/research/instrumentable_collinearity_pairs_v1.csv","w",newline="") as fh:
    w=csv.writer(fh); w.writerow(["a","b","r","abs_r","flag"])
    for p in pairs: w.writerow([p["a"],p["b"],p["r"],p["abs_r"],p["flag"]])

print("=== CH-R56 ===")
print("kept:",n_ser,"of 18; dropped:",[d["base"] for d in dropped])
print("Horn/Kaiser/elbow:",counts["horn_parallel_95"],counts["kaiser"],counts["scree_elbow"],
      "| PR:",counts["participation_ratio"],"| 90%var:",counts["n_factors_90pct_var"])
print("eigs:",counts["eigs"][:6])
print("pairs >0.9:",len(above9)," >0.8:",len(above8))
for p in above9: print("   ",p["a"],p["b"],p["r"])
print("CMRMTSPL~CMRMTSPLx r:",OUT["CH_R56_instrumentable_collinearity"]["pairwise_correlation"]["CMRMTSPL_CMRMTSPLx_r"])
print("realized channel:")
for ch,d in realized_channel.items(): print("   %-11s real=%.3f nom=%.3f n=%d"%(ch,d["realized_weight"],d["nominal_equal_weight"],d["n_bases"]))
print("cluster realized weight:")
for c,d in sorted(cluster_contrib.items(),key=lambda x:-x[1]["realized_weight"]): print("   c%d %.3f %s"%(c,d["realized_weight"],d["bases"]))
print("load-bearing:",loadbearing)
print("passengers:",passengers)
