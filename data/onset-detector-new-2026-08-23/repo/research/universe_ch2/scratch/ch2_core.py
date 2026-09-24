#!/usr/bin/env python3
"""PROBE CH2 core compute — §1 (variance decomposition 4 ways + labor internal + ERC
stability), §6 (windows/persistence), §7 (staircase). Read-only. Imports
method_source/index_v1.py with NOWCAST_DISABLE=1 (pure carry-forward transformed
history), reuses CH1's exact variance-decomposition and ERC method as treatment (a).
Writes ONLY to research/universe_ch2/scratch/. Emits JSON evidence to stdout + file."""
import os, sys, json, datetime as dt, bisect
import numpy as np

REPO = "/Users/anthonyhall/Desktop/RecessionMonitor 2/Recession Monitor V2"
MSRC = REPO + "/method_source"
WORK = REPO + "/research/universe_ch2/scratch/work"

os.environ["NOWCAST_DISABLE"] = "1"
os.environ["INDEX_OUT"] = WORK + "/index_v1_out.scratch.json"
os.chdir(WORK)
sys.path.insert(0, MSRC)
import index_v1 as m

np.random.seed(20260805)

CHAN = m.CHANNELS
CH_ORDER = list(CHAN.keys())
MEMBERS = []
for c in CH_ORDER:
    MEMBERS += CHAN[c][1]
assert len(MEMBERS) == 17, MEMBERS
DAYS = m.DAYS
START, END = m.START, m.END
T = m.T
Z = {name: (Z0, ks) for name, (Z0, ks) in m.Z.items()}
W = np.array([CHAN[c][0] for c in CH_ORDER])  # 0.30,0.25,0.20,0.10,0.15

def asof(zdict, keys, d):
    i = bisect.bisect_right(keys, d) - 1
    return zdict[keys[i]] if i >= 0 else None

# daily transformed-z matrix, exactly as channel_score/zval sees them (carry-forward)
Xz = np.full((len(DAYS), len(MEMBERS)), np.nan)
for j, name in enumerate(MEMBERS):
    zd, ks = Z[name]
    for i, d in enumerate(DAYS):
        v = asof(zd, ks, d)
        if v is not None:
            Xz[i, j] = v

DAYS_ARR = np.array([d.toordinal() for d in DAYS])
labels = np.array([1 if m.in_recession(DAYS[i]) else 0 for i in range(len(DAYS))])
is_2020 = np.array([dt.date(2020,1,1) <= DAYS[i] <= dt.date(2021,12,31) for i in range(len(DAYS))])

# ---- channel scores (mean of present member z), current renorm headline ----
def channel_scores(Xin):
    CS = np.full((len(DAYS), len(CH_ORDER)), np.nan)
    for ci, c in enumerate(CH_ORDER):
        idx = [MEMBERS.index(x) for x in CHAN[c][1]]
        sub = Xin[:, idx]
        for i in range(len(DAYS)):
            row = sub[i][~np.isnan(sub[i])]
            if len(row): CS[i, ci] = row.mean()
    return CS
CS = channel_scores(Xz)
full_cov = ~np.isnan(CS).any(axis=1)

def headline_from_CS(CSin):
    line = np.full(len(DAYS), np.nan)
    for i in range(len(DAYS)):
        present = ~np.isnan(CSin[i])
        if not present.any(): continue
        wsum = W[present].sum()
        line[i] = np.sum(W[present]*CSin[i][present]) / wsum
    return line

# =====================================================================
# §1  VARIANCE DECOMPOSITION — FOUR TREATMENTS
# =====================================================================
def winsorize_cols(A, p):
    B = A.copy()
    for j in range(B.shape[1]):
        col = B[:, j]; ok = ~np.isnan(col)
        if ok.sum() < 10: continue
        lo, hi = np.nanpercentile(col, p), np.nanpercentile(col, 100-p)
        col[ok & (col < lo)] = lo; col[ok & (col > hi)] = hi
        B[:, j] = col
    return B

def rank_cols(A):
    B = np.full_like(A, np.nan)
    for j in range(A.shape[1]):
        col = A[:, j]; ok = ~np.isnan(col)
        if ok.sum() < 3: continue
        v = col[ok]
        order = np.argsort(v, kind="mergesort")
        r = np.empty(len(v)); r[order] = np.arange(1, len(v)+1)
        # normalize ranks to [0,1] so weighting is comparable across columns
        B[np.where(ok)[0], j] = (r - 1)/(len(v)-1) if len(v) > 1 else 0.5
    return B

def var_decomp(CSin, mask):
    """CH1 method: comp = CS*W on rows in mask (full-cov so wsum=1); share=cov(comp_c,H)/var(H)."""
    idx = np.where(mask & full_cov)[0]
    if len(idx) < 30: return None
    comp = CSin[idx] * W
    H = comp.sum(axis=1)
    varH = H.var()
    shares = {}
    for ci, c in enumerate(CH_ORDER):
        cov = np.mean((comp[:, ci]-comp[:, ci].mean())*(H-H.mean()))
        shares[c] = round(float(cov/varH), 4)
    return {"n_days": int(len(idx)), "shares": shares}

def erc_weights(Sig, iters=20000, lr=0.01):
    n = Sig.shape[0]; w = np.ones(n)/n
    for _ in range(iters):
        mrc = Sig @ w
        rc = w*mrc
        grad = rc - rc.mean()
        w = w - lr*grad/(np.abs(mrc)+1e-9)
        w = np.clip(w, 1e-6, None); w = w/w.sum()
    return w

def erc_vec(CSin, mask):
    idx = np.where(mask & full_cov)[0]
    Sig = np.cov(CSin[idx].T)
    erc = erc_weights(Sig)
    return {c: round(float(erc[ci]), 4) for ci, c in enumerate(CH_ORDER)}

# treatment (a) as CH1: full history
CS_a = CS
mask_all = np.ones(len(DAYS), bool)
# (b) exclude 2020-01-01..2021-12-31
mask_b = ~is_2020
# (c) winsorised channel scores at 1%/99% (stated); full history
CS_c = winsorize_cols(CS, 1.0)
# (d) rank-transformed channel scores (normalized), full history
CS_d = rank_cols(CS)

treatments = {
 "a_as_ch1_full":            {"vd": var_decomp(CS_a, mask_all), "erc": erc_vec(CS_a, mask_all)},
 "b_exclude_2020_2021":      {"vd": var_decomp(CS_a, mask_b),   "erc": erc_vec(CS_a, mask_b)},
 "c_winsorised_1pct":        {"vd": var_decomp(CS_c, mask_all), "erc": erc_vec(CS_c, mask_all)},
 "d_rank_transformed":       {"vd": var_decomp(CS_d, mask_all), "erc": erc_vec(CS_d, mask_all)},
}
# labor share across treatments + stays-above-0.5 test
labor_share = {k: v["vd"]["shares"]["labor"] for k, v in treatments.items() if v["vd"]}
labor_structural = all(s > 0.5 for s in labor_share.values())

# §1.5 internal labor decomposition: members within labor channel score
LAB = CHAN["labor"][1]  # ICSA,IURSA,SAHM,UNRATEv
lab_idx = [MEMBERS.index(x) for x in LAB]
CS_lab = CS[:, CH_ORDER.index("labor")]
def internal_share(mask):
    idx = np.where(mask & ~np.isnan(CS_lab))[0]
    # only days where all 4 labor members present (so mean is over the 4 and decomposition is exact)
    sub = Xz[np.ix_(idx, lab_idx)]
    full = ~np.isnan(sub).any(axis=1)
    idx2 = idx[full]; sub = Xz[np.ix_(idx2, lab_idx)]
    csl = sub.mean(axis=1)  # = labor channel score on these days
    varL = csl.var()
    out = {}
    for mi2, mm in enumerate(LAB):
        comp = sub[:, mi2]/len(LAB)  # each member's additive contribution to the mean
        cov = np.mean((comp-comp.mean())*(csl-csl.mean()))
        out[mm] = round(float(cov/varL), 4)
    return {"n_days": int(len(idx2)), "shares": out}
lab_internal_full = internal_share(mask_all)
lab_internal_ex2020 = internal_share(mask_b)
# how much of ICSA's variance is the 2020 move alone
icsa_col = Xz[:, MEMBERS.index("ICSA")]
ok_icsa = ~np.isnan(icsa_col)
var_icsa_full = np.nanvar(icsa_col[ok_icsa])
var_icsa_ex2020 = np.nanvar(icsa_col[ok_icsa & ~is_2020])
icsa_2020_variance_fraction = round(1 - (var_icsa_ex2020*(ok_icsa&~is_2020).sum())/(var_icsa_full*ok_icsa.sum()), 4)
icsa_max = float(np.nanmax(icsa_col)); icsa_max_day = DAYS[int(np.nanargmax(icsa_col))].isoformat()

section1 = {
 "method": "treatment(a)=CH1 exact: full-coverage days (all 5 channels present); comp=channel_score*weight (weights 0.30/0.25/0.20/0.10/0.15 sum 1); share_c=Cov(comp_c,H)/Var(H), sum to 1. (b) drops calendar days 2020-01-01..2021-12-31. (c) winsorises each channel-score column at 1st/99th pctile. (d) replaces each channel-score column by its within-column normalized rank in [0,1] (outlier-immune).",
 "variance_shares_by_treatment": {k: v["vd"] for k, v in treatments.items()},
 "labor_share_by_treatment": labor_share,
 "labor_dominance_structural_all_four_above_0p5": bool(labor_structural),
 "erc_by_treatment": {k: v["erc"] for k, v in treatments.items()},
 "erc_ch1_reference_treatment_a": {"labor":0.069,"realactivity":0.223,"creditequity":0.241,"finconditions":0.197,"housingincome":0.270},
 "labor_internal_decomposition_full": lab_internal_full,
 "labor_internal_decomposition_ex2020": lab_internal_ex2020,
 "icsa_2020_variance_fraction_of_icsa_total": icsa_2020_variance_fraction,
 "icsa_max_transformed_z": round(icsa_max,2), "icsa_max_day": icsa_max_day,
}

# =====================================================================
# §6  WINDOWS / PERSISTENCE
# =====================================================================
# native raw underlying series per member (the series the window operates on)
RAW_UNDERLYING = {
 "ICSA":"ICSA","IURSA":"IURSA","SAHM":"SAHMREALTIME","UNRATEv":"UNRATE",
 "INDPRO":"INDPRO","CMRMT":"CMRMTSPL","TCU":"TCU","PHILLY":"GACDFSA066MSFRBPHI",
 "NASDAQ":"NASDAQCOM","VIX":"VIXCLS","BAA10Y":"BAA10Y","NFCI":"NFCI",
 "PERMIT":"PERMIT","HOUST":"HOUST","UMCSENT":"UMCSENT","W875":"W875RX1",
}
def native_series(member):
    if member == "BAAAAA":
        s = m.BAAAAA
    else:
        s = m.S[RAW_UNDERLYING[member]]
    ks = sorted(s); return ks, np.array([s[k] for k in ks])

def median_cadence_days(ks):
    if len(ks) < 3: return None
    gaps = np.array([(ks[i+1]-ks[i]).days for i in range(len(ks)-1)])
    return float(np.median(gaps))

def acf(vals, maxlag):
    v = vals - vals.mean(); n = len(v); denom = np.sum(v*v)
    out = []
    for lag in range(1, maxlag+1):
        if lag >= n: break
        out.append(float(np.sum(v[lag:]*v[:-lag])/denom))
    return out

WINDOW_OF = {  # member -> (transform, window_days)
 "ICSA":("yoy",365),"IURSA":("rise_floor",370),"SAHM":("none",None),"UNRATEv":("rise_floor",120),
 "INDPRO":("yoy",365),"CMRMT":("yoy",365),"TCU":("yoy",365),"PHILLY":("none",None),
 "NASDAQ":("drawdown",370),"BAAAAA":("none",None),"BAA10Y":("none",None),"NFCI":("none",None),
 "VIX":("none",None),"PERMIT":("yoy",365),"HOUST":("yoy",365),"UMCSENT":("drawdown",370),
 "W875":("yoy",365),
}
persistence = {}
for mem in MEMBERS:
    ks, vals = native_series(mem)
    cad = median_cadence_days(ks)
    ac = acf(vals, min(60, len(vals)-2))
    # lag where ACF first crosses 1/e (~0.368) and 0.2
    def first_cross(ac, thr):
        for i, a in enumerate(ac, 1):
            if a < thr: return i
        return None
    l_e = first_cross(ac, 1/np.e); l_02 = first_cross(ac, 0.2)
    tr, win = WINDOW_OF[mem]
    persistence[mem] = {
      "transform": tr, "window_days": win, "native_cadence_days": cad,
      "n_obs": len(ks), "acf_lag1": round(ac[0],3) if ac else None,
      "acf_lag_cross_1_over_e_obs": l_e, "acf_lag_cross_0p2_obs": l_02,
      "acf_cross_1_over_e_days": (round(l_e*cad,1) if (l_e and cad) else None),
      "window_vs_persistence_days": (round(win-(l_e*cad),1) if (win and l_e and cad) else None),
    }

# §6.3 window sensitivity: recompute member z at alternative windows, report latest-z + headline shift
def rebuild_member_z(mem, transform, win):
    src = m.BAAAAA if mem=="BAAAAA" else m.S[RAW_UNDERLYING[mem]]
    if transform=="yoy":
        native = m.yoy(src)
        if mem in ("INDPRO","CMRMT","TCU","PERMIT","HOUST","W875"): native={k:-v for k,v in native.items()}
    elif transform=="rise_floor":
        native = m.rise_floor(src, win)
    elif transform=="drawdown":
        mx,ks,vv = m._window_extreme(src, win, max)
        native = {k:(src[k]/mx[k]-1)*100 if mx[k] else 0 for k in ks}
        native = {k:-v for k,v in native.items()}  # NASDAQ/UMCSENT flip
    else:
        return None
    base=[native[k] for k in sorted(native) if m.is_baseline(k)]
    mu=sum(base)/len(base); sd=(sum((x-mu)**2 for x in base)/len(base))**.5 or 1.0
    zd={k:(native[k]-mu)/sd for k in native}; ks=sorted(zd)
    return zd, ks

WINDOW_GRID = {
 "rise_floor":{"IURSA":[120,250,370,500],"UNRATEv":[60,120,250,370]},
 "drawdown":{"NASDAQ":[250,370,500,730],"UMCSENT":[250,370,500,730]},
 "yoy":{},  # handled by tolerance section; yoy window fixed at 365
}
window_sensitivity = {}
for mem in MEMBERS:
    tr, win = WINDOW_OF[mem]
    grid = WINDOW_GRID.get(tr,{}).get(mem)
    if not grid: continue
    jcol = MEMBERS.index(mem)
    rows = {}
    for w2 in grid:
        rb = rebuild_member_z(mem, tr, w2)
        if not rb: continue
        zd, ks = rb
        # latest z (asof END) and headline shift if we swap only this member
        latest = asof(zd, ks, END)
        Xz2 = Xz.copy()
        col = np.full(len(DAYS), np.nan)
        for i,d in enumerate(DAYS):
            vv=asof(zd,ks,d)
            if vv is not None: col[i]=vv
        Xz2[:,jcol]=col
        line2 = headline_from_CS(channel_scores(Xz2))
        line0 = headline_from_CS(CS)
        ok=~np.isnan(line0)&~np.isnan(line2)
        rows[str(w2)] = {"latest_member_z":round(float(latest),3) if latest is not None else None,
                         "headline_corr_vs_current":round(float(np.corrcoef(line0[ok],line2[ok])[0,1]),4),
                         "headline_max_abs_shift":round(float(np.nanmax(np.abs(line2-line0))),3)}
    window_sensitivity[mem]={"transform":tr,"current_window":win,"grid":rows}

# §6.4 yoy ±tolerance sensitivity (irregular series: weekly ICSA/IURSA)
def yoy_tol(series, tol):
    out={}; ks=sorted(series)
    for k in ks:
        prior=k-dt.timedelta(days=365); i=bisect.bisect_left(ks,prior)
        cand=[x for x in ks[max(0,i-1):i+2] if abs((x-prior).days)<=tol]
        if cand:
            p=min(cand,key=lambda x:abs((x-prior).days))
            if series[p]!=0: out[k]=(series[k]/series[p]-1)*100
    return out
tol_sensitivity={}
for mem in ["ICSA","INDPRO","PERMIT","HOUST"]:
    src=m.S[RAW_UNDERLYING[mem]]
    base_default=yoy_tol(src,20)
    row={}
    for tol in [5,10,20,40]:
        alt=yoy_tol(src,tol)
        common=[k for k in alt if k in base_default]
        n_extra=len([k for k in alt if k not in base_default])
        diffs=np.array([alt[k]-base_default[k] for k in common])
        row[str(tol)]={"n_obs":len(alt),"n_keys_vs_tol20":len(alt)-len(base_default),
                       "max_abs_diff_vs_tol20":round(float(np.max(np.abs(diffs))),4) if len(diffs) else 0.0,
                       "mean_abs_diff_vs_tol20":round(float(np.mean(np.abs(diffs))),4) if len(diffs) else 0.0}
    tol_sensitivity[mem]=row

section6={"persistence_vs_window":persistence,"window_sensitivity":window_sensitivity,
          "yoy_tolerance_sensitivity":tol_sensitivity,
          "note":"ACF computed on native-cadence raw underlying (not daily-carried) to avoid carry-forward autocorrelation inflation; lag thresholds 1/e and 0.2 stated; cadence=median day-gap."}

# =====================================================================
# §7  STAIRCASE
# =====================================================================
# native obs dates per member (transformed keys = when a new value appears)
member_keys = {mem: Z[mem][1] for mem in MEMBERS}
member_cad = {mem: median_cadence_days(member_keys[mem]) for mem in MEMBERS}
# §7.1 age in days of freshest obs backing each channel, per day
def freshest_age(d, members):
    ages=[]
    for mem in members:
        ks=member_keys[mem]; i=bisect.bisect_right(ks,d)-1
        if i>=0: ages.append((d-ks[i]).days)
    return min(ages) if ages else None   # channel refreshed when ANY member updates
chan_age_dist={}
for c in CH_ORDER:
    mems=CHAN[c][1]
    ages=[freshest_age(DAYS[i],mems) for i in range(len(DAYS)) if full_cov[i]]
    ages=[a for a in ages if a is not None]
    a=np.array(ages)
    chan_age_dist[c]={"median":float(np.median(a)),"p90":float(np.percentile(a,90)),
                      "max":int(a.max()),"mean":round(float(a.mean()),1)}
# coarsest contributing member cadence per era (headline effective resolution)
def cadence_label(days):
    if days is None: return "n/a"
    if days<=1.5: return "daily"
    if days<=8: return "weekly"
    if days<=45: return "monthly"
    return "quarterly"
eras=[(1976,1989),(1990,1999),(2000,2009),(2010,2019),(2020,2026)]
eff_res={}
for a,b in eras:
    di=[i for i in range(len(DAYS)) if a<=DAYS[i].year<=b and full_cov[i]]
    if not di: continue
    # coarsest = max median cadence among members that have started by then
    active=[mem for mem in MEMBERS if member_keys[mem] and member_keys[mem][0]<=DAYS[di[-1]]]
    coarsest=max((member_cad[mem] for mem in active if member_cad[mem]),default=None)
    eff_res[f"{a}-{b}"]={"coarsest_cadence_days":round(coarsest,1) if coarsest else None,
                         "effective_resolution":cadence_label(coarsest)}
# §7.3 carry-forward repeat fraction of headline (days where headline unchanged vs prior published day)
line_cur=headline_from_CS(CS)
pub_days=[i for i in range(len(DAYS)) if not np.isnan(line_cur[i])]
changes=0; repeats=0
prev=None
for i in pub_days:
    if prev is not None:
        if abs(line_cur[i]-prev)<1e-12: repeats+=1
        else: changes+=1
    prev=line_cur[i]
carry_fraction=round(repeats/(repeats+changes),4) if (repeats+changes) else None
# §7.4 fraction of days on which a genuinely daily unrevised member moves
DAILY_UNREVISED=["NASDAQ","VIX","BAA10Y"]  # daily cadence, unrevised (confirmed in §2)
def member_moved_on(d, mem):
    ks=member_keys[mem]
    return d in set(ks)  # a new native obs keyed exactly on d
daily_move_days=0; both_present_days=0
daily_key_sets={mem:set(member_keys[mem]) for mem in DAILY_UNREVISED}
for i in pub_days:
    d=DAYS[i]
    present=[mem for mem in DAILY_UNREVISED if member_keys[mem] and member_keys[mem][0]<=d]
    if not present: continue
    both_present_days+=1
    if any(d in daily_key_sets[mem] for mem in present): daily_move_days+=1
daily_move_fraction=round(daily_move_days/both_present_days,4) if both_present_days else None

section7={"channel_freshness_age_days":chan_age_dist,
          "effective_resolution_by_era":eff_res,
          "headline_carry_forward_repeat_fraction":carry_fraction,
          "n_published_days":len(pub_days),
          "daily_unrevised_members":DAILY_UNREVISED,
          "fraction_days_a_daily_unrevised_member_moves":daily_move_fraction,
          "member_native_cadence_days":{mem:round(member_cad[mem],1) if member_cad[mem] else None for mem in MEMBERS},
          "note":"channel freshness age = days since the MOST RECENT update among the channel's members (channel refreshes when any member updates). carry-forward repeat = published day whose headline equals the immediately prior published day's headline bit-for-bit."}

OUT={"section1_variance_decomposition":section1,
     "section6_windows_persistence":section6,
     "section7_staircase":section7}
outpath=REPO+"/research/universe_ch2/scratch/ch2_core_results.json"
json.dump(OUT, open(outpath,"w"), indent=1, default=str)
print("===CH2 CORE WRITTEN===", outpath)
print(json.dumps({
  "labor_share_by_treatment":labor_share,
  "labor_structural":labor_structural,
  "all_shares":{k:(v["vd"]["shares"] if v["vd"] else None) for k,v in treatments.items()},
  "erc":{k:v["erc"] for k,v in treatments.items()},
  "labor_internal_full":lab_internal_full["shares"],
  "labor_internal_ex2020":lab_internal_ex2020["shares"],
  "icsa_2020_var_fraction":icsa_2020_variance_fraction,
  "icsa_max":icsa_max,"icsa_max_day":icsa_max_day,
  "carry_fraction":carry_fraction,"daily_move_fraction":daily_move_fraction,
  "eff_res":eff_res,
}, indent=1, default=str))
