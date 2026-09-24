#!/usr/bin/env python3
"""PROBE CH2 §4 — derive channel structure on the §3 survivor universe (NOT the 17
someone chose). Read-only. Second stream over normalized objects to reconstruct monthly
values for monthly/weekly/daily survivors; per-series transform derived by §5 tests;
correlation + PCA + parallel analysis; compare to inherited 4/4/4/1/4; test the 6 CH1
collinear pairs; §4.8 as-of representability from the 9 present headline members.
No interpolation (§7.5): quarterly/annual survivors are EXCLUDED and counted (no silent cap)."""
import os, json, glob, datetime as dt, array
import numpy as np
np.random.seed(20260805)

REPO=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REPO="/Users/anthonyhall/Desktop/RecessionMonitor 2/Recession Monitor V2"
NORM=REPO+"/live_data/store/normalized"
SV=json.load(open(REPO+"/research/universe_ch2/scratch/ch2_survivors.json"))
survrows=SV["rows"]; survivors=set(SV["survivors"])
# PCA universe: monthly/weekly/daily survivors only (no interpolation of quarterly/annual)
pca_ids=[s for s in survivors if survrows[s]["cadence"] in ("monthly","weekly","daily")]
excluded_quarterly=[s for s in survivors if survrows[s]["cadence"] in ("quarterly","annual")]
pca_set=set(pca_ids)

# ---- ANALYSIS WINDOW (chosen; stated). monthly grid month-starts ----
WIN_START=dt.date(1990,1,1); WIN_END=dt.date(2024,12,1)
months=[]
y,mo=WIN_START.year,WIN_START.month
while dt.date(y,mo,1)<=WIN_END:
    months.append(dt.date(y,mo,1)); mo+=1
    if mo>12: mo=1; y+=1
MONTH_ORD=[d.toordinal() for d in months]; NM=len(months)

import bisect
def parse_period(s):
    try:
        if "Q" in s:
            yy,q=s.split("-Q");return dt.date(int(yy),(int(q)-1)*3+1,1).toordinal()
        p=s.split("-")
        if len(p)==1:return dt.date(int(p[0]),1,1).toordinal()
        if len(p)==2:return dt.date(int(p[0]),int(p[1]),1).toordinal()
        return dt.date(int(p[0]),int(p[1]),int(p[2])).toordinal()
    except: return None
def month_end_series(pairs):
    """value as-of each month-start (last obs at or before month-start): step carry."""
    pairs=sorted(set(pairs))
    ks=[p[0] for p in pairs]; vv=[p[1] for p in pairs]
    out=np.full(NM,np.nan)
    for i,mo in enumerate(MONTH_ORD):
        j=bisect.bisect_right(ks,mo)-1
        if j>=0: out[i]=vv[j]
    return out

# ---- pass 2 (cached): monthly month_end matrix for pca_ids ----
CACHE=REPO+"/research/universe_ch2/scratch/ch2_monthly_cache.npz"
pca_list=sorted(pca_set)
if os.path.exists(CACHE):
    z=np.load(CACHE,allow_pickle=True)
    RAWM=z["RAWM"]; cache_ids=list(z["ids"])
    assert cache_ids==pca_list, "cache id mismatch; delete cache"
else:
    vals={s:[] for s in pca_set}
    files=sorted(glob.glob(NORM+"/sha256/*/*.json"))
    for f in files:
        try: d=json.load(open(f))
        except: continue
        for r in d.get("records",[]):
            sid=r.get("series_id")
            if sid not in pca_set: continue
            op=r.get("observation_period"); v=r.get("value")
            if op is None or v in (None,"","."): continue
            o=parse_period(op)
            if o is None: continue
            try: fv=float(v)
            except: continue
            vals[sid].append((o,fv))
    RAWM=np.column_stack([month_end_series(vals[s]) for s in pca_list])
    np.savez(CACHE,RAWM=RAWM,ids=np.array(pca_list,dtype=object))
raw_col={s:RAWM[:,i] for i,s in enumerate(pca_list)}

# ---- ADF (constant) for transform derivation ----
ADF5=-2.86
def adf_stat(y):
    y=np.asarray(y,float); n=len(y)
    if n<24: return None
    dy=np.diff(y); p=min(4,n//4)
    T=n-1-p
    if T<12: return None
    yl=y[p:n-1]; X=[np.ones(T),yl]
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

# ---- build transformed complete matrix over window ----
# analysis rows = post-warmup (months[12:]); a series enters only if fully covered there,
# and non-stationary levels get yoy (NOT forced-level) so correlations aren't spurious.
kept=[]; cols=[]; transform_used={}; dropped_nonstat_no_yoy=0
for s in pca_ids:
    col=raw_col[s]
    if np.isnan(col[12:]).any():   # require full coverage on analysis rows (no interpolation)
        continue
    st=adf_stat(col[12:])
    if st is not None and st<ADF5:
        use=col[12:]; tr="level"
    else:
        yy=yoy12(col)              # yoy defined on [12:]
        if np.isnan(yy[12:]).any() or np.nanstd(yy[12:])==0:
            dropped_nonstat_no_yoy+=1; continue   # drop, do not force spurious level
        use=yy[12:]; tr="yoy"
    if use is None or np.isnan(use).any() or np.nanstd(use)==0: continue
    kept.append(s); cols.append(use); transform_used[s]=tr
X=np.column_stack(cols) if cols else np.zeros((len(months)-12,0))
used_months=months[12:]
# guard: remove any residual nan/const cols
good=[j for j in range(X.shape[1]) if not np.isnan(X[:,j]).any() and X[:,j].std()>0]
X=X[:,good]; kept=[kept[j] for j in good]
n_obs,n_ser=X.shape

# ---- correlation eigenvalues via the Gram trick (n_obs<<n_ser: rank<=n_obs) ----
# C = Xs^T Xs / n_obs (n_ser x n_ser); nonzero eig(C) = eig(Xs Xs^T / n_obs) (n_obs x n_obs).
# Standardize columns population-std so each col sumsq=n_obs -> eig sum to n_ser (Kaiser>1 valid).
Xs=(X-X.mean(0))/X.std(0)
G=Xs@Xs.T/n_obs
gev,gvec=np.linalg.eigh(G)
order=np.argsort(gev)[::-1]; gev=np.clip(gev[order],0,None); gvec=gvec[:,order]
evals=gev  # correlation-scale eigenvalues (the nonzero ones)

# ---- parallel analysis (Horn) via same Gram trick ----
NSIM=50
rank=len(evals)
rand_ev=np.zeros((NSIM,rank))
for k in range(NSIM):
    R=np.random.standard_normal((n_obs,n_ser))
    Rs=(R-R.mean(0))/R.std(0)
    ev=np.linalg.eigvalsh(Rs@Rs.T/n_obs)[::-1]
    rand_ev[k,:len(ev)]=ev[:rank]
rand_p95=np.percentile(rand_ev,95,axis=0)
m=min(len(evals),len(rand_p95))
n_parallel=int(np.sum(evals[:m]>rand_p95[:m]))
n_eig_over1=int(np.sum(evals>1))
scree=[round(float(e),3) for e in evals[:15]]
var_share=[round(float(e/evals.sum()),4) for e in evals[:15]]
rand_p95_top15=[round(float(x),3) for x in rand_p95[:15]]

# ---- headline members present in PCA universe: their loadings on top factors ----
MEMBER_IDS={"ICSA":"ICSA","INDPRO":"INDPRO","CMRMT":"CMRMTSPL","TCU":"TCU","PHILLY":"GACDFSA066MSFRBPHI",
 "NFCI":"NFCI","PERMIT":"PERMIT","HOUST":"HOUST","W875":"W875RX1"}
pos={s:i for i,s in enumerate(kept)}
NF=min(8,len(evals))
# loadings = corr(series column, factor-score vector). gvec cols are unit-norm obs-space
# factor scores; Xs cols have sumsq=n_obs, so corr = (Xs^T gvec)/sqrt(n_obs).
load=(Xs.T@gvec[:,:NF])/np.sqrt(n_obs)   # n_ser x NF
member_loadings={}
for mem,sid in MEMBER_IDS.items():
    if sid in pos:
        row=load[pos[sid]]
        member_loadings[mem]={"in_pca_universe":True,
          "top_factor":int(np.argmax(np.abs(row))),
          "loadings":[round(float(x),3) for x in row]}
    else:
        member_loadings[mem]={"in_pca_universe":False}
# which factor each present member loads highest on -> do labor members share a factor? etc.
factor_of_member={mem:member_loadings[mem]["top_factor"] for mem in MEMBER_IDS if member_loadings[mem]["in_pca_universe"]}
# top-loading series per factor (name factor by its highest-loading members only, no economic label)
top_series_per_factor={}
for fnum in range(min(NF,6)):
    order=np.argsort(np.abs(load[:,fnum]))[::-1][:12]
    top_series_per_factor[fnum]=[{"series":kept[j],"loading":round(float(load[j,fnum]),3)} for j in order]

# ---- CH1 collinear pairs: which are measurable here + correlation ----
PAIRS=[("PERMIT","HOUST",0.911,"PERMIT","HOUST"),("INDPRO","TCU",0.900,"INDPRO","TCU"),
 ("INDPRO","CMRMT",0.875,"INDPRO","CMRMTSPL"),("IURSA","SAHM",0.857,None,None),
 ("CMRMT","TCU",0.816,"CMRMTSPL","TCU"),("BAAAAA","BAA10Y",0.816,None,None)]
pair_report=[]
def yoy_of(sid):
    if sid not in pos: return None
    return X[:,pos[sid]]
for a,b,ch1r,ida,idb in PAIRS:
    if ida and idb and ida in pos and idb in pos:
        r=float(np.corrcoef(X[:,pos[ida]],X[:,pos[idb]])[0,1])
        same=factor_of_member.get(a)==factor_of_member.get(b) if (a in factor_of_member and b in factor_of_member) else None
        pair_report.append({"pair":f"{a}~{b}","ch1_r":ch1r,"universe_r_transformed":round(r,3),
          "both_in_universe":True,"collapses_same_factor":same,
          "factor_a":factor_of_member.get(a),"factor_b":factor_of_member.get(b)})
    else:
        pair_report.append({"pair":f"{a}~{b}","ch1_r":ch1r,"both_in_universe":False,
          "reason":"one or both members absent from store universe"})

# ---- §4.8 as-of representability (headline members only; universe series are class 'none') ----
ASOF={"ICSA":"alfred_vintage","INDPRO":"alfred_vintage","CMRMT":"alfred_vintage","TCU":"alfred_vintage",
 "PHILLY":"alfred_vintage","NFCI":"alfred_vintage","PERMIT":"alfred_vintage","HOUST":"alfred_vintage",
 "W875":"alfred_vintage"}  # all 9 present members are alfred_vintage class (none unrevised present)
asof_note=("Of the 9 present headline members ALL are alfred_vintage class; the 4 unrevised "
 "creditequity members (NASDAQ/VIX/BAA10Y/BAAAAA) are ABSENT from the store universe. The "
 "remaining ~6,911 universe survivors have NO vintage lane (as-of class 'none') — so a "
 "factor derived from the universe is overwhelmingly backed by revised-only series and is "
 "NOT as-of instrumentable in real time. FLAG per §4.8.6 (do not fix).")

# ---- DE-DUPLICATED variant: collapse vintage snapshots (base = id before first '.') ----
seen=set(); dedup_j=[]
for j,s in enumerate(kept):
    base=s.split(".")[0]
    if base in seen: continue
    seen.add(base); dedup_j.append(j)
Xd=X[:,dedup_j]; kept_d=[kept[j] for j in dedup_j]
kept_d_base=[s.split(".")[0] for s in kept_d]
Xds=(Xd-Xd.mean(0))/Xd.std(0)
nd=Xds.shape[1]
Gd=Xds@Xds.T/n_obs
evd,evecd=np.linalg.eigh(Gd); o=np.argsort(evd)[::-1]; evd=np.clip(evd[o],0,None); evecd=evecd[:,o]
rankd=min(nd,n_obs)
randd=np.zeros((NSIM,rankd))
for k in range(NSIM):
    R=np.random.standard_normal((n_obs,nd)); Rs=(R-R.mean(0))/R.std(0)
    ev=np.linalg.eigvalsh(Rs@Rs.T/n_obs)[::-1]; randd[k,:min(len(ev),rankd)]=ev[:rankd]
p95d=np.percentile(randd,95,axis=0)
# compare only real, non-trivial eigenvalues (>1e-6) within rank
n_parallel_d=int(np.sum((evd[:rankd]>p95d[:rankd]) & (evd[:rankd]>1e-6)))
n_eig1_d=int(np.sum(evd>1))
NFd=min(8,nd); Ld=(Xds.T@evecd[:,:NFd])/np.sqrt(n_obs)
posd_base={b:i for i,b in enumerate(kept_d_base)}
fom_d={}
for mem,sid in MEMBER_IDS.items():
    if sid in posd_base: fom_d[mem]=int(np.argmax(np.abs(Ld[posd_base[sid]])))
dedup={"n_series_dedup":nd,"parallel_analysis_factors":n_parallel_d,"eig_over1":n_eig1_d,
  "var_share_top10":[round(float(e/evd.sum()),4) for e in evd[:10]],
  "factor_of_present_member":fom_d,
  "note":"vintage snapshots (id.ASOF*, id.*) collapsed to base series; one representative per base. This removes the duplicate-vintage cluster contamination in the raw store universe."}

OUT={"section4_factor_structure":{
  "STORE_UNIVERSE_CAVEAT":"the 11,838-series store counts as-of VINTAGE SNAPSHOTS as distinct series (e.g. CMRMTSPL.ASOF20200828, IURSA.ASOF20230420). raw parallel analysis is contaminated by near-duplicate vintage clusters; factor0 top-loaders are CMRMTSPL vintages, factor1 is IURSA vintages. de-duplicated variant reported alongside. also: the 8 base members flagged absent in §3 exist as .ASOF* vintage variants (base current id absent).",
  "dedup_variant":dedup,
  "pca_universe":{"survivors_total":len(survivors),
    "pca_universe_monthly_weekly_daily":len(pca_ids),
    "excluded_quarterly_annual_no_interpolation":len(excluded_quarterly),
    "complete_over_window_kept":n_ser,
    "analysis_window":f"{WIN_START} .. {WIN_END} monthly, yoy warmup dropped -> {n_obs} months from {used_months[0]}",
    "transform_rule":"per-series: ADF(const) on level (post-warmup rows); if level stationary (t<-2.86) use level, else 12-month %-change (yoy). Non-stationary series with uncomputable yoy are DROPPED, not forced to level (avoids spurious level correlation). No interpolation; require full window coverage.",
    "transform_counts":{t:sum(1 for v in transform_used.values() if v==t) for t in set(transform_used.values())},
    "dropped_nonstationary_no_yoy":dropped_nonstat_no_yoy},
  "how_many_channels_data_supports":{
    "parallel_analysis_Horn_95pct":n_parallel,
    "eigenvalue_over_1_Kaiser":n_eig_over1,
    "scree_top15":scree,
    "parallel_random_p95_top15":rand_p95_top15,
    "inherited_channel_count":5,
    "finding":f"data supports {n_parallel} factors by parallel analysis (Kaiser>1 gives {n_eig_over1}); inherited structure asserts 5 channels."},
  "variance_share_top15":var_share,
  "headline_member_loadings":member_loadings,
  "top_series_per_factor_first6":top_series_per_factor,
  "collinear_pairs_ch1":pair_report,
  "asof_representability_4p8":{"present_member_asof_class":ASOF,"finding":asof_note},
  "note":"factors named ONLY by top-loading members (no economic label, per §4.6/§23). membership follows loading. correlations on stationary-transformed series to avoid spurious level correlation."}}
json.dump(OUT,open(REPO+"/research/universe_ch2/scratch/ch2_factor_results.json","w"),indent=1,default=str)
print("=== §4 ===")
print("pca universe (m/w/d survivors):",len(pca_ids)," excluded quarterly/annual:",len(excluded_quarterly))
print("complete over window kept:",n_ser," obs months:",n_obs)
print("transform counts:",{t:sum(1 for v in transform_used.values() if v==t) for t in set(transform_used.values())})
print("parallel-analysis factors:",n_parallel," eig>1:",n_eig_over1)
print("scree top15:",scree)
print("var share top15:",var_share)
print("factor of each present member:",factor_of_member)
print("collinear pairs:")
for p in pair_report: print("  ",p)
