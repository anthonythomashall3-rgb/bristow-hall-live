#!/usr/bin/env python3
"""CH3 — FACTOR STRUCTURE ON THE FULL LANDED UNIVERSE (window 3, read-only, §20-class).
Zero store writes. Outputs research/ only. Evidence for S2/S5; NO channel adoption.

Universe = current_revised base set (one representative per first-dot base, richest series)
+ vintage-only landed bases carried by their LATEST vintage as a current-proxy (flagged).
Derived channel count by Kaiser + Horn parallel analysis + scree-elbow (all three, none
chosen). Hierarchical cluster cross-check (correlation distance). Instrumentable-only
restriction (18 vintage-lane bases). 2020 robustness (winsorized + ex-2020). CH1 collinear
twins -> factor map. numpy only (no scipy)."""
import os, json, glob, bisect, datetime as dt
import numpy as np
np.random.seed(20260806)

REPO="/Users/anthonyhall/Desktop/RecessionMonitor 2/Recession Monitor V2"
NORM=REPO+"/live_data/store/normalized"
enum=json.load(open(REPO+"/research/ch3_bases_enum.json"))
VINT_BASES=set(enum["vint_bases"])              # 18 bases with an archive_snapshot_asof lane
CR_BASES=set(enum["cr_bases"])                  # 144 bases with current_revised
VINT_ONLY=VINT_BASES-CR_BASES                   # carried by latest-vintage proxy

# ---- analysis window: 2000-01..2024-12 monthly (store universe starts ~2000) ----
WIN_START=dt.date(2000,1,1); WIN_END=dt.date(2024,12,1)
months=[]; y,mo=WIN_START.year,WIN_START.month
while dt.date(y,mo,1)<=WIN_END:
    months.append(dt.date(y,mo,1)); mo=mo+1
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

# ---- PASS: collect per (series_id) current_revised obs; per base latest-vintage obs ----
# representative choice: for a base with current_revised, pick the current_revised series_id
# with the most numeric obs. For vintage-only base, use the archive_snapshot_asof series
# with the newest vintage date (proxy for current).
cr_obs={}       # series_id -> list[(ord,val)]  (current_revised only)
cr_series_base={}   # series_id -> base
vint_latest={}  # base -> (vintage_key, list[(ord,val)])  newest vintage snapshot
import re
def vintage_key(sid):
    m=re.search(r'(?:ASOF|DEEPASOF)(\d{6,8})', sid)
    return m.group(1) if m else ""
files=sorted(glob.glob(NORM+"/sha256/*/*.json"))
for f in files:
    try: d=json.load(open(f))
    except: continue
    for r in d.get("records",[]):
        sid=r.get("series_id");
        if not sid: continue
        base=sid.split(".")[0]
        m=r.get("information_set_mode")
        op=r.get("observation_period"); v=r.get("value")
        if op is None or v in (None,"","."): continue
        o=parse_period(op)
        if o is None: continue
        try: fv=float(v)
        except: continue
        if m=="current_revised":
            cr_obs.setdefault(sid,[]).append((o,fv)); cr_series_base[sid]=base
# second pass: collect vintage obs keyed by series_id for vint_only bases
vo_obs={}
for f in files:
    try: d=json.load(open(f))
    except: continue
    for r in d.get("records",[]):
        sid=r.get("series_id")
        if not sid: continue
        base=sid.split(".")[0]
        if base not in VINT_ONLY: continue
        if r.get("information_set_mode")!="archive_snapshot_asof": continue
        op=r.get("observation_period"); v=r.get("value")
        if op is None or v in (None,"","."): continue
        o=parse_period(op)
        if o is None: continue
        try: fv=float(v)
        except: continue
        vo_obs.setdefault(sid,[]).append((o,fv))
# pick newest-vintage series id per vint_only base
vo_rep={}
for sid in vo_obs:
    base=sid.split(".")[0]; vk=vintage_key(sid)
    cur=vo_rep.get(base)
    if cur is None or vk>cur[1]: vo_rep[base]=(sid,vk)

# ---- build representative per base ----
# current_revised bases: richest cr series per base
by_base_cr={}
for sid,base in cr_series_base.items():
    by_base_cr.setdefault(base,[]).append(sid)
rep={}   # base -> (rep_series_id, source_mode, obslist)
for base,sids in by_base_cr.items():
    best=max(sids,key=lambda s:len(cr_obs[s]))
    rep[base]=(best,"current_revised",cr_obs[best])
for base,(sid,vk) in vo_rep.items():
    rep[base]=(sid,"latest_vintage_proxy",vo_obs[sid])

# ---- ADF + yoy (from CH2) ----
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

# ---- assemble transformed matrix (warmup=12; analysis rows months[12:]) ----
kept=[]; cols=[]; meta=[]; dropped_cov=0; dropped_nonstat=0
for base in sorted(rep):
    sid,mode,obs=rep[base]
    col=month_end(obs)
    if np.isnan(col[12:]).any():
        dropped_cov+=1; continue
    st=adf_stat(col[12:])
    if st is not None and st<ADF5:
        use=col[12:]; tr="level"
    else:
        yy=yoy12(col)
        if np.isnan(yy[12:]).any() or np.nanstd(yy[12:])==0:
            dropped_nonstat+=1; continue
        use=yy[12:]; tr="yoy"
    if np.nanstd(use)==0: continue
    kept.append(base); cols.append(use)
    meta.append({"base":base,"rep_series":sid,"source_mode":mode,"transform":tr,
                 "instrumentable":base in VINT_BASES})
X=np.column_stack(cols); used_months=months[12:]
n_obs,n_ser=X.shape

def eig_counts(Xmat,nsim=50,label=""):
    """Gram-trick eigenvalues on standardized cols; Kaiser, Horn parallel, scree elbow."""
    m,p=Xmat.shape
    Xs=(Xmat-Xmat.mean(0))/Xmat.std(0)
    G=Xs@Xs.T/m
    ev=np.linalg.eigvalsh(G)[::-1]; ev=np.clip(ev,0,None)
    kaiser=int(np.sum(ev>1))
    rank=min(p,m)
    rnd=np.zeros((nsim,rank))
    for k in range(nsim):
        R=np.random.standard_normal((m,p)); Rs=(R-R.mean(0))/R.std(0)
        e=np.linalg.eigvalsh(Rs@Rs.T/m)[::-1]; rnd[k,:min(len(e),rank)]=e[:rank]
    p95=np.percentile(rnd,95,axis=0)
    q=min(len(ev),len(p95))
    horn=int(np.sum((ev[:q]>p95[:q]) & (ev[:q]>1e-6)))
    # scree elbow: largest drop between consecutive eigenvalues in top min(15,rank)
    top=ev[:min(15,rank)]
    gaps=top[:-1]-top[1:]
    elbow=int(np.argmax(gaps))+1 if len(gaps)>0 else 0   # factors before the biggest gap
    return {"n_series":p,"n_obs":m,"kaiser_eig_over1":kaiser,"horn_parallel_95":horn,
            "scree_elbow":elbow,"scree_top12":[round(float(x),3) for x in ev[:12]],
            "var_share_top12":[round(float(x/ev.sum()),4) for x in ev[:12]],
            "horn_p95_top12":[round(float(x),3) for x in p95[:12]]}, ev, Xs

full_counts, ev_full, Xs_full = eig_counts(X,label="full")

# ---- loadings on top NF factors (full) ----
G=Xs_full@Xs_full.T/n_obs
gev,gvec=np.linalg.eigh(G); o=np.argsort(gev)[::-1]; gvec=gvec[:,o]
NF=min(8,n_ser)
load=(Xs_full.T@gvec[:,:NF])/np.sqrt(n_obs)   # n_ser x NF
top_factor=[int(np.argmax(np.abs(load[i]))) for i in range(n_ser)]
for i,mt in enumerate(meta):
    mt["top_factor"]=top_factor[i]
    mt["loadings"]=[round(float(load[i,j]),3) for j in range(NF)]

# headline members
MEMBERS={"ICSA":"ICSA","INDPRO":"INDPRO","CMRMT":"CMRMTSPL","TCU":"TCU",
 "PHILLY":"GACDFSA066MSFRBPHI","NFCI":"NFCI","PERMIT":"PERMIT","HOUST":"HOUST",
 "W875":"W875RX1","GDPC1":"GDPC1","UNRATE":"UNRATE","PAYEMS":"PAYEMS",
 "CLAIMSx":"CLAIMSx","CMRMTSPLx":"CMRMTSPLx","IURSA":"IURSA","SAHM":"SAHMREALTIME",
 "UMCSENT":"UMCSENT"}
pos={b:i for i,b in enumerate(kept)}
member_map={}
for name,base in MEMBERS.items():
    if base in pos:
        i=pos[base]
        member_map[name]={"in_universe":True,"base":base,"top_factor":top_factor[i],
          "source_mode":meta[i]["source_mode"],"instrumentable":meta[i]["instrumentable"],
          "loadings":meta[i]["loadings"]}
    else:
        member_map[name]={"in_universe":False,"reason":"dropped (no current_revised / coverage / non-stationary)"}

top_series_per_factor={}
for fn in range(min(NF,6)):
    idx=np.argsort(np.abs(load[:,fn]))[::-1][:12]
    top_series_per_factor[fn]=[{"base":kept[j],"loading":round(float(load[j,fn]),3)} for j in idx]

# ---- hierarchical clustering (average linkage) on distance = 1 - |corr| ----
C=np.corrcoef(Xs_full.T)
D=1-np.abs(C); np.fill_diagonal(D,0.0)
def hclust_average(D):
    n=D.shape[0]
    clusters={i:[i] for i in range(n)}
    active=list(range(n)); dist={}
    for a in range(n):
        for b in range(a+1,n): dist[(a,b)]=D[a,b]
    merges=[]; nid=n
    def gd(i,j):
        return dist[(i,j)] if (i,j) in dist else dist[(j,i)]
    while len(active)>1:
        best=None;bp=None
        for ii in range(len(active)):
            for jj in range(ii+1,len(active)):
                a,b=active[ii],active[jj]; dd=gd(a,b)
                if best is None or dd<best: best=dd;bp=(a,b)
        a,b=bp
        merged=clusters[a]+clusters[b]
        # average linkage vs remaining
        for c in active:
            if c in (a,b): continue
            na,nb=len(clusters[a]),len(clusters[b])
            nd=(gd(a,c)*na+gd(b,c)*nb)/(na+nb)
            dist[(min(nid,c),max(nid,c))]=nd
        clusters[nid]=merged
        merges.append((a,b,best,len(merged)))
        active=[c for c in active if c not in (a,b)]+[nid]
        del clusters[a]; del clusters[b]
        nid+=1
    return merges
merges=hclust_average(D)
def cut_k(merges,n,k):
    # rebuild membership by replaying merges until n-k merges done
    parent=list(range(2*n))
    members={i:[i] for i in range(n)}
    nid=n; done=0; labels=list(range(n))
    comp={i:[i] for i in range(n)}
    for (a,b,d,sz) in merges:
        if done>=n-k: break
        comp[nid]=comp[a]+comp[b]; del comp[a]; del comp[b]; nid+=1; done+=1
    lab=np.empty(n,dtype=int)
    for ci,(cid,mem) in enumerate(comp.items()):
        for m in mem: lab[m]=ci
    return lab
def adj_rand(a,b):
    a=np.asarray(a);b=np.asarray(b);n=len(a)
    from collections import Counter
    ct={}
    for x,y in zip(a,b): ct[(x,y)]=ct.get((x,y),0)+1
    ai=Counter(a); bi=Counter(b)
    comb=lambda x:x*(x-1)//2
    sum_ij=sum(comb(v) for v in ct.values())
    sa=sum(comb(v) for v in ai.values()); sb=sum(comb(v) for v in bi.values())
    exp=sa*sb/comb(n); mx=(sa+sb)/2
    return (sum_ij-exp)/(mx-exp) if mx!=exp else 1.0
k=max(2,full_counts["horn_parallel_95"])
clab=cut_k(merges,n_ser,k)
for i,mt in enumerate(meta): mt["cluster_id"]=int(clab[i])
ari=adj_rand(top_factor,clab)

# ---- instrumentable-only restriction ----
inst_idx=[i for i in range(n_ser) if kept[i] in VINT_BASES]
inst_counts=None
if len(inst_idx)>=4:
    inst_counts,_,_=eig_counts(X[:,inst_idx],label="instrumentable")
inst_bases=[kept[i] for i in inst_idx]

# ---- 2020 robustness ----
# ex-2020: drop analysis rows in calendar year 2020
keep_rows=[i for i,d in enumerate(used_months) if d.year!=2020]
ex2020_counts,_,_=eig_counts(X[keep_rows,:],label="ex2020")
# winsorize each column at 1/99 percentile then recount
Xw=X.copy()
for j in range(n_ser):
    lo,hi=np.percentile(Xw[:,j],[1,99]); Xw[:,j]=np.clip(Xw[:,j],lo,hi)
wins_counts,_,_=eig_counts(Xw,label="winsor")

# ---- CH1 collinear twins -> which factor each loads on ----
PAIRS=[("PERMIT","HOUST"),("INDPRO","TCU"),("INDPRO","CMRMTSPL"),
       ("CMRMTSPL","TCU"),("IURSA","SAHMREALTIME")]
twin_report=[]
for a,b in PAIRS:
    if a in pos and b in pos:
        r=float(np.corrcoef(X[:,pos[a]],X[:,pos[b]])[0,1])
        fa,fb=top_factor[pos[a]],top_factor[pos[b]]
        twin_report.append({"pair":f"{a}~{b}","r_transformed":round(r,3),
          "factor_a":fa,"factor_b":fb,"same_factor":fa==fb,
          "same_cluster":int(clab[pos[a]])==int(clab[pos[b]])})
    else:
        twin_report.append({"pair":f"{a}~{b}","measurable":False,
          "reason":f"{'both' if a not in pos and b not in pos else (a if a not in pos else b)} absent"})

OUT={"CH3_factor_structure":{
 "universe":{
   "distinct_first_dot_bases_in_store":len(CR_BASES|VINT_BASES),
   "current_revised_bases":len(CR_BASES),
   "vintage_lane_bases_instrumentable":sorted(VINT_BASES),
   "vintage_only_carried_by_latest_vintage_proxy":sorted(VINT_ONLY),
   "RTDSM_RUC_status":("LANDED (in vintage universe)" if "RTDSM_RUC" in VINT_BASES else "NOT LANDED -> excluded"),
   "candidate_bases_assembled":len(rep),
   "kept_after_coverage_and_stationarity":n_ser,
   "dropped_coverage":dropped_cov,"dropped_nonstationary_no_yoy":dropped_nonstat,
   "analysis_window":f"{used_months[0]}..{used_months[-1]} monthly, {n_obs} rows (2000 window, 12mo yoy warmup dropped)",
   "transform_rule":"per-base ADF(const) on level; level if t<-2.86 else 12mo %-change; else drop (no forced level, no interpolation)",
   "representative_rule":"one per first-dot base; current_revised->richest cr series; vintage-only->newest archive_snapshot_asof vintage as current-proxy (FLAGGED)",
   "CAVEAT_family_collapse":"first-dot dedup collapses namespaced families (e.g. all CENSUS.* -> one 'CENSUS' representative), inherited from CH2. This universe is the ~macro base set, NOT the 5k granular census cells. Granular universe factor counts (CH2: 19 Horn / 50 Kaiser) are census/vintage-cluster inflated and not comparable."},
 "derived_channel_count_full":{
   **full_counts,
   "three_criteria":{"kaiser":full_counts["kaiser_eig_over1"],
     "horn_parallel":full_counts["horn_parallel_95"],"scree_elbow":full_counts["scree_elbow"]},
   "inherited_channel_count":5,
   "finding":f"data supports Horn={full_counts['horn_parallel_95']} / Kaiser={full_counts['kaiser_eig_over1']} / scree-elbow={full_counts['scree_elbow']} factors on {n_ser} bases; inherited monitor asserts 5 channels."},
 "cluster_cross_check":{
   "method":"hierarchical average-linkage, distance=1-|corr|, cut at k=Horn count",
   "k_used":k,"adjusted_rand_vs_factor_topload":round(float(ari),3),
   "finding":f"cluster-vs-factor agreement ARI={round(float(ari),3)} at k={k} (1.0=identical, 0=chance)."},
 "instrumentable_only":{
   "n_instrumentable_bases_kept":len(inst_idx),"bases":inst_bases,
   "counts":inst_counts,
   "note":"instrumentable = has archive_snapshot_asof vintage lane (18 store bases; SAHMREALTIME never-revised also here). Certified-never-revised series lacking a store base are outside this universe.",
   "finding":(None if inst_counts is None else
     f"restricted to {len(inst_idx)} as-of-instrumentable bases the data supports Horn={inst_counts['horn_parallel_95']} / Kaiser={inst_counts['kaiser_eig_over1']} / elbow={inst_counts['scree_elbow']} factors.")},
 "robustness_2020":{
   "ex2020":{"horn":ex2020_counts["horn_parallel_95"],"kaiser":ex2020_counts["kaiser_eig_over1"],"elbow":ex2020_counts["scree_elbow"],"n_obs":ex2020_counts["n_obs"]},
   "winsorized_1_99":{"horn":wins_counts["horn_parallel_95"],"kaiser":wins_counts["kaiser_eig_over1"],"elbow":wins_counts["scree_elbow"]},
   "full_ref":{"horn":full_counts["horn_parallel_95"],"kaiser":full_counts["kaiser_eig_over1"],"elbow":full_counts["scree_elbow"]},
   "finding":"structure that only appears with 2020 present is artifact (CH2 §1). Compare deltas."},
 "headline_member_map":member_map,
 "top_series_per_factor_first6":top_series_per_factor,
 "collinear_twins_ch1":twin_report,
 "NO_ADOPTION":"evidence only; channel count NOT adopted. S2 sitting decides member/channel structure."}}

json.dump(OUT,open(REPO+"/research/ch3_factor_structure_v1.json","w"),indent=1,default=str)

# ---- CSV: per-base rows ----
import csv
with open(REPO+"/research/ch3_factor_structure_v1.csv","w",newline="") as fh:
    w=csv.writer(fh)
    hdr=["base","rep_series","source_mode","transform","instrumentable","top_factor","cluster_id"]+[f"load_f{j}" for j in range(NF)]
    w.writerow(hdr)
    for mt in meta:
        w.writerow([mt["base"],mt["rep_series"],mt["source_mode"],mt["transform"],
                    mt["instrumentable"],mt["top_factor"],mt["cluster_id"]]+mt["loadings"])

print("=== CH3 ===")
print("candidate bases:",len(rep)," kept:",n_ser," obs rows:",n_obs)
print("dropped coverage:",dropped_cov," nonstat:",dropped_nonstat)
print("FULL   Horn/Kaiser/elbow:",full_counts["horn_parallel_95"],full_counts["kaiser_eig_over1"],full_counts["scree_elbow"])
print("scree top12:",full_counts["scree_top12"])
print("INST(",len(inst_idx),") Horn/Kaiser/elbow:",(inst_counts["horn_parallel_95"],inst_counts["kaiser_eig_over1"],inst_counts["scree_elbow"]) if inst_counts else None)
print("ex2020 Horn/Kaiser/elbow:",ex2020_counts["horn_parallel_95"],ex2020_counts["kaiser_eig_over1"],ex2020_counts["scree_elbow"])
print("winsor Horn/Kaiser/elbow:",wins_counts["horn_parallel_95"],wins_counts["kaiser_eig_over1"],wins_counts["scree_elbow"])
print("cluster ARI vs factor (k=%d): %.3f"%(k,ari))
print("member factors:",{n:member_map[n].get("top_factor") for n in member_map if member_map[n].get("in_universe")})
print("twins:")
for t in twin_report: print("  ",t)
