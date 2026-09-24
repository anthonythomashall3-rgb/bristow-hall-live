#!/usr/bin/env python3
"""CH-R63 — IS THE REAL-TIME FACTOR COLLAPSE MECHANICAL? (window 3, read-only, §20-class).
Reuses CH3's proven assembly (exec ch3_factor.py) to get the transformed matrix X
(n_obs x 121 bases), `kept` base list, VINT_BASES (18 instrumentable), n_obs.
Then, NOVEL measurement (labelled ours, not literature-supported):
  1. Random-18 control  : distribution of Horn/Kaiser/elbow over random 18-base subsets.
  2. Size-matched sweep  : factor count vs N=10..121.
  3. Boivin-Ng check     : idiosyncratic residual cross-correlations, fraction |r|>0.5.
  4. Pre-screened 40     : communality-ranked top-40 subset factor count.
numpy only. Zero store writes; research/ outputs only."""
import os, sys, io, json, csv
import numpy as np

REPO="/Users/anthonyhall/Desktop/RecessionMonitor 2/Recession Monitor V2"

# --- reuse CH3 assembly verbatim (globs store once, builds X/kept/VINT_BASES) ---
_stdout=sys.stdout; sys.stdout=io.StringIO()          # silence CH3's prints
g={}
exec(compile(open(REPO+"/research/ch3_factor.py").read(),"ch3_factor.py","exec"),g)
sys.stdout=_stdout
X=g["X"]; kept=g["kept"]; VINT=set(g["VINT_BASES"]); n_obs,n_ser=X.shape
inst_idx=[i for i in range(n_ser) if kept[i] in VINT]

RNG=np.random.RandomState(20260806)   # stated seed
NSIM=200                              # parallel-analysis reps per size (cached by size)

def standardize(M):
    return (M-M.mean(0))/M.std(0)

def eigvals_desc(M):
    Xs=standardize(M); m=M.shape[0]
    G=Xs@Xs.T/m
    ev=np.linalg.eigvalsh(G)[::-1]
    return np.clip(ev,0,None), Xs

# Horn parallel-analysis threshold depends only on (m,p): cache p95 curve by p.
_p95={}
def horn_p95(m,p):
    if p in _p95: return _p95[p]
    rank=min(p,m); rnd=np.zeros((NSIM,rank))
    for k in range(NSIM):
        R=RNG.standard_normal((m,p)); Rs=standardize(R)
        e=np.linalg.eigvalsh(Rs@Rs.T/m)[::-1]
        rnd[k,:min(len(e),rank)]=e[:rank]
    v=np.percentile(rnd,95,axis=0); _p95[p]=v; return v

def counts(M):
    ev,_=eigvals_desc(M); p=M.shape[1]; m=M.shape[0]
    kaiser=int(np.sum(ev>1))
    p95=horn_p95(m,p); q=min(len(ev),len(p95))
    horn=int(np.sum((ev[:q]>p95[:q])&(ev[:q]>1e-6)))
    top=ev[:min(15,min(p,m))]; gaps=top[:-1]-top[1:]
    elbow=int(np.argmax(gaps))+1 if len(gaps)>0 else 0
    return kaiser,horn,elbow

# ---- reference points ----
k_full,h_full,e_full=counts(X)
k_inst,h_inst,e_inst=counts(X[:,inst_idx])

# ============ 1. RANDOM-18 CONTROL (decisive test) ============
NDRAW=400
rand18=[]
for _ in range(NDRAW):
    idx=RNG.choice(n_ser,18,replace=False)
    rand18.append(counts(X[:,idx]))
rand18=np.array(rand18)   # cols: kaiser,horn,elbow
def dist(a):
    a=np.asarray(a,float)
    return {"mean":round(float(a.mean()),3),"sd":round(float(a.std()),3),
            "min":int(a.min()),"p05":float(np.percentile(a,5)),
            "median":float(np.percentile(a,50)),"p95":float(np.percentile(a,95)),
            "max":int(a.max())}
# where does instrumentable-18 sit? percentile of its value in the random distribution
def pctile_of(val,arr):
    arr=np.asarray(arr,float); return round(float((arr<val).mean()+0.5*(arr==val).mean()),3)
r18={
 "n_draws":NDRAW,"seed":20260806,
 "instrumentable_18":{"kaiser":k_inst,"horn":h_inst,"elbow":e_inst},
 "random_18_kaiser":dist(rand18[:,0]),
 "random_18_horn":dist(rand18[:,1]),
 "random_18_elbow":dist(rand18[:,2]),
 "inst_horn_percentile_in_random":pctile_of(h_inst,rand18[:,1]),
 "inst_kaiser_percentile_in_random":pctile_of(k_inst,rand18[:,0]),
 "frac_random18_horn_le_inst":round(float((rand18[:,1]<=h_inst).mean()),3),
 "frac_random18_kaiser_le_inst":round(float((rand18[:,0]<=k_inst).mean()),3),
}
mechanical = r18["frac_random18_horn_le_inst"]>=0.5   # inst not below typical random-18
r18["VERDICT"]=("MECHANICAL: random 18-base subsets yield <= the instrumentable-18 Horn count "
  "at least half the time; the collapse is a size artifact, not real-time honesty."
  if mechanical else
  "SUBSTANTIVE: the instrumentable 18 yields materially FEWER Horn factors than random 18s; "
  "the collapse reflects the instrumentable set's structure, not just its size.")

# ============ 2. SIZE-MATCHED SWEEP ============
sizes=[10,15,18,20,25,30,40,50,60,70,80,90,100,110,121]
DR=60
sweep=[]
for N in sizes:
    if N>n_ser: continue
    if N==n_ser:
        rows=[counts(X)]
    else:
        rows=[counts(X[:,RNG.choice(n_ser,N,replace=False)]) for _ in range(DR)]
    a=np.array(rows,float)
    sweep.append({"N":N,"draws":len(rows),
      "kaiser_mean":round(float(a[:,0].mean()),3),"kaiser_p05":float(np.percentile(a[:,0],5)),"kaiser_p95":float(np.percentile(a[:,0],95)),
      "horn_mean":round(float(a[:,1].mean()),3),"horn_p05":float(np.percentile(a[:,1],5)),"horn_p95":float(np.percentile(a[:,1],95)),
      "elbow_mean":round(float(a[:,2].mean()),3)})
# instrumentable-18 vs the N=18 mechanical band
band18=next(s for s in sweep if s["N"]==18)

# ============ 3. BOIVIN-NG idiosyncratic cross-correlation ============
# common component from top r_full factors (r=Horn on full panel), residual cross-corr.
ev,Xs=eigvals_desc(X)
R=Xs.T@Xs/n_obs
w,V=np.linalg.eigh(R); o=np.argsort(w)[::-1]; V=V[:,o]; w=w[o]
def resid_crosscorr(r):
    Xhat=(Xs@V[:,:r])@V[:,:r].T
    E=Xs-Xhat
    Ec=(E-E.mean(0))/E.std(0)
    C=Ec.T@Ec/n_obs
    iu=np.triu_indices(n_ser,1)
    off=np.abs(C[iu])
    comm=1.0-E.var(0)   # communality per series (var(Xs col)=1)
    return off,comm
bn={}
for r in sorted(set([h_full,8,k_full])):    # Horn=11, McCracken-Ng 8, Kaiser=18
    off,comm=resid_crosscorr(r)
    bn[f"r={r}"]={"frac_absresidcorr_gt_0.5":round(float((off>0.5).mean()),4),
                  "frac_gt_0.3":round(float((off>0.3).mean()),4),
                  "mean_abs":round(float(off.mean()),4),
                  "median_communality":round(float(np.median(comm)),4)}
# Boivin-Ng reference: 115/147=0.782 of series had idio corr >0.5 (their panel).
bn_ref_frac=round(115/147,3)

# ============ 4. PRE-SCREENED 40 (highest communality = least idiosyncratic) ============
_,comm_full=resid_crosscorr(h_full)
order=np.argsort(comm_full)[::-1]
screen40=sorted(order[:40].tolist())
k40,h40,e40=counts(X[:,screen40])
# also random-40 band for contrast
rand40=np.array([counts(X[:,RNG.choice(n_ser,40,replace=False)]) for _ in range(DR)],float)
prescreen={
 "screen_rule":"rank 121 bases by communality (var explained by full-panel Horn=%d factors), take top 40 (Boivin-Ng noise-screen intent)"%h_full,
 "screened_40":{"kaiser":k40,"horn":h40,"elbow":e40},
 "random_40_horn":dist(rand40[:,1]),"random_40_kaiser":dist(rand40[:,0]),
 "screened40_bases":[kept[i] for i in screen40],
 "n_instrumentable_in_screened40":int(sum(kept[i] in VINT for i in screen40)),
 "interpretation":("A screened 40 gives Horn=%d. If this is near the instrumentable-18's Horn=%d, "
   "the instrumentable set is not impoverished, just smaller."%(h40,h_inst))}

OUT={"CH_R63_factor_collapse_decomposition":{
 "novelty_label":"NOVEL, OURS. No published paper found comparing estimated factor count of "
   "real-time vintages vs revised data (searched, not found). Mechanical/size controls below "
   "are standard; the real-time application is our own and must not be cited as literature-backed.",
 "universe":{"n_bases":n_ser,"n_obs_rows":n_obs,
   "window":"2001-01..2024-12 monthly (from CH3 assembly)",
   "instrumentable_18":sorted([kept[i] for i in inst_idx]),
   "note":"X, kept, transform rule inherited verbatim from ch3_factor.py (per-base ADF level-or-yoy)."},
 "reference_counts":{"full_121":{"kaiser":k_full,"horn":h_full,"elbow":e_full},
   "instrumentable_18":{"kaiser":k_inst,"horn":h_inst,"elbow":e_inst}},
 "test1_random18_control":r18,
 "test2_size_sweep":sweep,
 "test2_instrumentable_vs_N18_band":{"inst_horn":h_inst,"randomN18_horn_mean":band18["horn_mean"],
   "randomN18_horn_p05":band18["horn_p05"],"randomN18_horn_p95":band18["horn_p95"]},
 "test3_boivin_ng_idiosyncratic":{"by_r":bn,"their_ref_frac_gt0.5":bn_ref_frac,
   "reading":"If our frac_gt_0.5 approaches their 0.78, our 121-panel is oversampled and the "
     "11-18 count should NOT be treated as truth being lost. If near 0, the extra factors are real."},
 "test4_prescreened_40":prescreen,
 "HEADLINE":r18["VERDICT"],
 "NO_ADOPTION":"evidence only; no factor count adopted. Informs S2 interpretation of the 11-18 vs 2-3 gap."}}

json.dump(OUT,open(REPO+"/research/factor_collapse_decomposition_v1.json","w"),indent=1,default=str)

with open(REPO+"/research/factor_collapse_decomposition_sweep_v1.csv","w",newline="") as fh:
    w=csv.writer(fh)
    w.writerow(["N","draws","kaiser_mean","kaiser_p05","kaiser_p95","horn_mean","horn_p05","horn_p95","elbow_mean"])
    for s in sweep:
        w.writerow([s["N"],s["draws"],s["kaiser_mean"],s["kaiser_p05"],s["kaiser_p95"],
                    s["horn_mean"],s["horn_p05"],s["horn_p95"],s["elbow_mean"]])

print("=== CH-R63 ===")
print("full121 K/H/elbow:",k_full,h_full,e_full)
print("inst18  K/H/elbow:",k_inst,h_inst,e_inst)
print("random18 Horn dist:",r18["random_18_horn"])
print("inst Horn pctile in random18:",r18["inst_horn_percentile_in_random"],
      " frac random18 Horn<=inst:",r18["frac_random18_horn_le_inst"])
print("VERDICT:",r18["VERDICT"][:60])
print("Boivin-Ng frac|resid|>0.5:",{k:v["frac_absresidcorr_gt_0.5"] for k,v in bn.items()}," their ref:",bn_ref_frac)
print("screened40 K/H/elbow:",k40,h40,e40," random40 Horn mean:",prescreen["random_40_horn"]["mean"])
print("sweep Horn means:",[(s["N"],s["horn_mean"]) for s in sweep])
