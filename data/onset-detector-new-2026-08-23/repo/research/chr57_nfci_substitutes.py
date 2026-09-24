#!/usr/bin/env python3
"""CH-R57 — NFCI financial-conditions substitutes (window 3, read-only, §20-class).
Zero store writes. numpy only. External comparator: NBER recession months (labeled)."""
import glob,json,collections,datetime as dt,csv
import numpy as np
NORM="live_data/store/normalized/sha256"

# ---- monthly grid 1971-01 .. 2026-06 ----
def mgrid():
    out=[];y,m=1971,1
    while (y,m)<=(2026,6):
        out.append(f"{y:04d}-{m:02d}");m+=1
        if m>12:m=1;y+=1
    return out
MG=mgrid(); MI={k:i for i,k in enumerate(MG)}; NM=len(MG)

# candidates: series_id -> (category, revision_class, certifying_probe)
CANDS={
 "NFCI":("target_nfci","heavily_revised_99.7pct","CH-R20/R25"),
 "OFR.FSI.TOTAL":("fc_index","model_output_UNMEASURED_no_vintages","none-landed"),
 "OFR.FSI.CREDIT":("fc_credit","model_output_UNMEASURED","none-landed"),
 "OFR.FSI.VOLATILITY":("fc_volatility","model_output_UNMEASURED","none-landed"),
 "OFR.FSI.FUNDING":("fc_funding","model_output_UNMEASURED","none-landed"),
 "OFR.FSI.EQUITY_VALUATION":("fc_equity","model_output_UNMEASURED","none-landed"),
 "OFR.FSI.SAFE_ASSETS":("fc_safe","model_output_UNMEASURED","none-landed"),
 "T10Y2Y":("spread_term","never_revised","CH-R25/R26"),
 "T10Y3M":("spread_term","never_revised","CH-R25/R26"),
 "DGS10":("rate_long","never_revised","CH-R25/R26"),
 "DGS2":("rate_short","never_revised","CH-R25/R26"),
 "DFF":("rate_policy","negligible_revision","CH-R25/R26"),
 "DTB3":("rate_bill","never_revised","CH-R25/R26"),
 "DCPF3M":("cp_rate","never_revised_flag","CH-R26"),
 "RIFSPPFAAD90NB":("cp_rate","never_revised_flag","CH-R26"),
 "DTWEXBGS":("dollar","moderately_revised","CH-R25(2vint,share1.38)"),
 "DCOILWTICO":("oil","never_revised","CH-R25/R26"),
}
first_date={} # per series
monthly={} # sid -> np.array over MG (mean of dailies in month), current_revised only
acc=collections.defaultdict(lambda: collections.defaultdict(list))
for f in glob.glob(NORM+"/*/*.json"):
    try: d=json.load(open(f))
    except: continue
    recs=d.get("records",[])
    if not recs: continue
    if recs[0].get("series_id") not in CANDS: 
        # cheap skip: check any
        sids={r.get("series_id") for r in recs[:3]}
        if not (sids & set(CANDS)): continue
    for r in recs:
        sid=r.get("series_id")
        if sid not in CANDS: continue
        if r.get("information_set_mode")!="current_revised": continue
        per=r.get("observation_period") or ""
        ym=per[:7]
        if ym not in MI: continue
        try: v=float(r.get("value"))
        except: continue
        acc[sid][ym].append(v)
        if sid not in first_date or per<first_date[sid]: first_date[sid]=per
for sid in acc:
    a=np.full(NM,np.nan)
    for ym,vals in acc[sid].items(): a[MI[ym]]=np.mean(vals)
    monthly[sid]=a

# ---- NBER recession months (external comparator, labeled) ----
def recmask():
    peaks_troughs=[("1973-11","1975-03"),("1980-01","1980-07"),("1981-07","1982-11"),
                   ("1990-07","1991-03"),("2001-03","2001-11"),("2007-12","2009-06"),
                   ("2020-02","2020-04")]
    m=np.zeros(NM,bool)
    for a,b in peaks_troughs:
        for i,k in enumerate(MG):
            if a<=k<=b: m[i]=True
    return m
REC=recmask()

def r2(y,X,mask=None):
    # OLS with intercept; return R2 over rows where all present (and mask)
    good=~np.isnan(y)
    for j in range(X.shape[1]): good&=~np.isnan(X[:,j])
    if mask is not None: good&=mask
    if good.sum()<X.shape[1]+3: return None,int(good.sum())
    yy=y[good]; XX=np.column_stack([np.ones(good.sum()),X[good]])
    beta,_,_,_=np.linalg.lstsq(XX,yy,rcond=None)
    pred=XX@beta; ss_res=((yy-pred)**2).sum(); ss_tot=((yy-yy.mean())**2).sum()
    return (1-ss_res/ss_tot if ss_tot>0 else None),int(good.sum())

def fitset(name,y,cols):
    X=np.column_stack([monthly[c] for c in cols])
    over,no=r2(y,X); rin,ni=r2(y,X,REC); rout,no2=r2(y,X,~REC)
    return {"set":name,"predictors":cols,"r2_overall":round(over,4) if over is not None else None,"n_overall":no,
            "r2_in_recession":round(rin,4) if rin is not None else None,"n_in":ni,
            "r2_out_recession":round(rout,4) if rout is not None else None,"n_out":no2}

y=monthly["NFCI"]
present=[c for c in CANDS if c in monthly and c!="NFCI"]
sets=[]
# Set A: rates/spreads only (long reach, no OFR)
A=[c for c in ["T10Y2Y","T10Y3M","DGS10","DGS2","DFF","DTB3","DCPF3M","DCOILWTICO"] if c in monthly]
sets.append(fitset("A_rates_spreads_neverrevised",y,A))
# Set B: add OFR FSI components (rich, model-output, 2000+)
B=A+[c for c in ["OFR.FSI.TOTAL","OFR.FSI.CREDIT","OFR.FSI.VOLATILITY","OFR.FSI.FUNDING","OFR.FSI.EQUITY_VALUATION","OFR.FSI.SAFE_ASSETS"] if c in monthly]
sets.append(fitset("B_plus_OFR_FSI_components",y,B))
# Set C: OFR TOTAL alone
sets.append(fitset("C_OFR_FSI_TOTAL_alone",y,["OFR.FSI.TOTAL"]))
# Set D: single best univariate scan
uni=[]
for c in present:
    r,n=r2(y,monthly[c][:,None])
    if r is not None: uni.append((c,round(r,4),n))
uni.sort(key=lambda x:-x[1])

# pairwise corr NFCI vs each (level)
corr={}
for c in present:
    good=~np.isnan(y)&~np.isnan(monthly[c])
    if good.sum()>24: corr[c]=round(float(np.corrcoef(y[good],monthly[c][good])[0,1]),4)

# ---- F7 survival: PCA on financial panel, with NFCI vs with OFR substitute ----
def zpca(cols,label):
    X=np.column_stack([monthly[c] for c in cols])
    good=np.all(~np.isnan(X),axis=1)
    Xs=X[good]
    Z=(Xs-Xs.mean(0))/Xs.std(0)
    C=np.corrcoef(Z.T); ev,evec=np.linalg.eigh(C); order=np.argsort(-ev); ev=ev[order]; evec=evec[:,order]
    return {"label":label,"cols":cols,"n_obs":int(good.sum()),"eig_over1":int((ev>1).sum()),
            "eig_top6":[round(float(x),3) for x in ev[:6]],
            "top_pc_loadings":{cols[i]:round(float(evec[i,0]),3) for i in range(len(cols))}}
core=["T10Y2Y","DGS10","DFF","DCPF3M"]  # rates/credit block reaching 1997+
core=[c for c in core if c in monthly]
with_nfci=zpca(core+["NFCI"],"panel_with_NFCI")
with_ofr =zpca(core+["OFR.FSI.TOTAL"],"panel_with_OFR_substitute")
# does NFCI/OFR sit apart? measure min |corr| of NFCI (resp OFR) to core members
def apartness(target):
    good=~np.isnan(monthly[target])
    cs=[]
    for c in core:
        g=good&~np.isnan(monthly[c])
        if g.sum()>24: cs.append(abs(float(np.corrcoef(monthly[target][g],monthly[c][g])[0,1])))
    return {"target":target,"max_abs_corr_to_core":round(max(cs),3),"mean_abs_corr_to_core":round(float(np.mean(cs)),3)}

out={
 "batch":"CH-R57_NFCI_SUBSTITUTES","generated":"read-only §20",
 "nfci_facts":{"share_revised":0.9969,"asof_floor":"2011","own_factor_ch3r2":"F7 load_f7=0.185(max)"},
 "series_first_dates":{k:first_date.get(k) for k in CANDS if k in monthly},
 "reconstruction_sets":sets,
 "univariate_r2_ranked":uni,
 "level_corr_to_nfci":corr,
 "f7_survival":{"with_nfci":with_nfci,"with_ofr":with_ofr,
                "nfci_apartness":apartness("NFCI"),"ofr_apartness":apartness("OFR.FSI.TOTAL"),
                "note":"low max_abs_corr_to_core => distinct axis survives"},
}
json.dump(out,open("research/nfci_substitutes_v1.json","w"),indent=1)

# csv
with open("research/nfci_candidates_v1.csv","w",newline="") as fh:
    w=csv.writer(fh); w.writerow(["series_id","category","revision_class","certifying_probe","first_date","cadence","level_corr_to_nfci","univar_r2_nfci"])
    ur={c:r for c,r,n in uni}
    cad={"NFCI":"weekly"}
    for sid,(cat,rc,pr) in CANDS.items():
        if sid not in monthly: continue
        w.writerow([sid,cat,rc,pr,first_date.get(sid),cad.get(sid,"daily/monthly"),corr.get(sid,""),ur.get(sid,"")])
print("WROTE json+csv")
print("SETS:")
for s in sets: print(" ",s["set"],"overall",s["r2_overall"],"in",s["r2_in_recession"],"out",s["r2_out_recession"],"n",s["n_overall"])
print("TOP UNIVAR:",uni[:6])
print("F7 with_nfci top_pc:",with_nfci["top_pc_loadings"])
print("F7 with_ofr top_pc:",with_ofr["top_pc_loadings"])
print("apart nfci",apartness("NFCI"),"apart ofr",apartness("OFR.FSI.TOTAL"))
