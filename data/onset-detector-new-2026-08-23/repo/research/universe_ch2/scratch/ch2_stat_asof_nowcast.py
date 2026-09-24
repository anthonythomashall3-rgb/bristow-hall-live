#!/usr/bin/env python3
"""PROBE CH2 — §5 stationarity (ADF+KPSS, numpy), §2 as-of frontier, §8 nowcast divergence.
Read-only. ADF/KPSS implemented in numpy with stated lag rules and cited critical values.
Writes only to research/universe_ch2/scratch/."""
import os, sys, json, datetime as dt, bisect, subprocess
import numpy as np

REPO = "/Users/anthonyhall/Desktop/RecessionMonitor 2/Recession Monitor V2"
MSRC = REPO + "/method_source"
WORK = REPO + "/research/universe_ch2/scratch/work"
os.environ["NOWCAST_DISABLE"] = "1"
os.environ["INDEX_OUT"] = WORK + "/index_v1_out.scratch.json"
os.chdir(WORK)
sys.path.insert(0, MSRC)
import index_v1 as m

MEMBERS = []
for c in m.CHANNELS: MEMBERS += m.CHANNELS[c][1]

# ---------------- ADF (constant, no trend) ----------------
# critical values: MacKinnon (1996/2010) asymptotic, model with constant (c): 1% -3.43, 5% -2.86, 10% -2.57
ADF_CV = {"1%": -3.43, "5%": -2.86, "10%": -2.57}
def adf(y, pmax=None):
    y = np.asarray(y, float); n = len(y)
    if n < 20: return None
    if pmax is None: pmax = int(np.floor(12*(n/100.0)**0.25))
    pmax = min(pmax, n//3)
    dy = np.diff(y)
    best = None
    for p in range(0, pmax+1):
        # rows: from index p+1.. ; regressors: const, y_{t-1}, dy_{t-1..t-p}
        T = n-1-p
        if T < 10: break
        yl = y[p:n-1]                       # y_{t-1}, length T
        X = [np.ones(T), yl]
        for i in range(1, p+1):
            X.append(dy[p-i:n-1-i])         # dy_{t-i}
        X = np.column_stack(X); Y = dy[p:]  # length T
        beta, *_ = np.linalg.lstsq(X, Y, rcond=None)
        resid = Y - X@beta; k = X.shape[1]
        s2 = resid@resid/(T-k)
        XtX_inv = np.linalg.pinv(X.T@X)
        se = np.sqrt(s2*XtX_inv[1,1])
        tstat = beta[1]/se if se>0 else np.nan
        # AIC for lag selection
        aic = T*np.log(resid@resid/T) + 2*k
        if best is None or aic < best[0]:
            best = (aic, tstat, p)
    return {"tstat": round(float(best[1]),3), "lag": best[2], "pmax": pmax,
            "reject_unitroot_5pct": bool(best[1] < ADF_CV["5%"]),
            "stationary_by_adf_5pct": bool(best[1] < ADF_CV["5%"])}

# ---------------- KPSS (level) ----------------
# critical values: Kwiatkowski et al (1992) level-stationary: 10% .347, 5% .463, 2.5% .574, 1% .739
KPSS_CV = {"10%":0.347,"5%":0.463,"2.5%":0.574,"1%":0.739}
def kpss(y):
    y = np.asarray(y, float); n = len(y)
    if n < 20: return None
    e = y - y.mean()
    S = np.cumsum(e)
    l = int(np.floor(4*(n/100.0)**0.25))
    s2 = (e@e)/n
    for j in range(1, l+1):
        w = 1 - j/(l+1)
        s2 += 2*w*(e[j:]@e[:-j])/n
    stat = (S@S)/(n*n)/s2 if s2>0 else np.nan
    return {"stat": round(float(stat),3), "bandwidth": l,
            "reject_stationary_5pct": bool(stat > KPSS_CV["5%"]),
            "stationary_by_kpss_5pct": bool(stat <= KPSS_CV["5%"])}

RAW_UNDERLYING = {
 "ICSA":"ICSA","IURSA":"IURSA","SAHM":"SAHMREALTIME","UNRATEv":"UNRATE","INDPRO":"INDPRO",
 "CMRMT":"CMRMTSPL","TCU":"TCU","PHILLY":"GACDFSA066MSFRBPHI","NASDAQ":"NASDAQCOM","VIX":"VIXCLS",
 "BAA10Y":"BAA10Y","NFCI":"NFCI","PERMIT":"PERMIT","HOUST":"HOUST","UMCSENT":"UMCSENT","W875":"W875RX1"}
def raw_native(member):
    s = m.BAAAAA if member=="BAAAAA" else m.S[RAW_UNDERLYING[member]]
    ks = sorted(s); return np.array([s[k] for k in ks])
def transformed_native(member):
    s = m.T[member]; ks=sorted(s); return np.array([s[k] for k in ks])

def verdict(a, k):
    if a is None or k is None: return "insufficient"
    st_a = a["stationary_by_adf_5pct"]; st_k = k["stationary_by_kpss_5pct"]
    if st_a and st_k: return "stationary"
    if (not st_a) and (not st_k): return "nonstationary"
    return "disagree"
def borderline(a,k):
    b=[]
    if a and abs(a["tstat"]-ADF_CV["5%"])<0.35: b.append("adf_near_5pct")
    if k and abs(k["stat"]-KPSS_CV["5%"])<0.10: b.append("kpss_near_5pct")
    return b

WINDOW_OF={"ICSA":"yoy","IURSA":"rise_floor","SAHM":"none","UNRATEv":"rise_floor","INDPRO":"yoy",
 "CMRMT":"yoy","TCU":"yoy","PHILLY":"none","NASDAQ":"drawdown","BAAAAA":"none","BAA10Y":"none",
 "NFCI":"none","VIX":"none","PERMIT":"yoy","HOUST":"yoy","UMCSENT":"drawdown","W875":"yoy"}

stationarity={}
for mem in MEMBERS:
    rv=raw_native(mem); tv=transformed_native(mem)
    a_raw,k_raw=adf(rv),kpss(rv); a_tr,k_tr=adf(tv),kpss(tv)
    v_raw=verdict(a_raw,k_raw); v_tr=verdict(a_tr,k_tr)
    applied=WINDOW_OF[mem]
    implied = "transform_needed" if v_raw in ("nonstationary","disagree") else "no_transform_ok"
    code_applies = "transform" if applied!="none" else "none"
    # disagreement between implied and applied
    disagreement=None
    if implied=="transform_needed" and applied=="none": disagreement="raw_nonstationary_but_no_transform_applied"
    if implied=="no_transform_ok" and applied!="none": disagreement="raw_stationary_but_transform_applied"
    transform_fixes = (v_raw!="stationary" and v_tr=="stationary")
    stationarity[mem]={
      "applied_transform":applied,
      "raw":{"adf":a_raw,"kpss":k_raw,"verdict":v_raw},
      "transformed":{"adf":a_tr,"kpss":k_tr,"verdict":v_tr},
      "implied_rule":implied,"code_applies":code_applies,
      "implied_vs_applied_disagreement":disagreement,
      "transform_moves_to_stationary":bool(transform_fixes),
      "borderline_raw":borderline(a_raw,k_raw),"borderline_transformed":borderline(a_tr,k_tr)}

section5={"method":"ADF: OLS of Δy on const,y_{t-1},lagged Δy; lag by AIC up to pmax=floor(12*(n/100)^0.25); MacKinnon constant-model CV 5%=-2.86, reject unit-root (stationary) if t<CV. KPSS level: Bartlett long-run var, bandwidth floor(4*(n/100)^0.25); KPSS 5% CV=0.463, reject stationarity if stat>CV. Run on native-cadence raw and on the applied deterioration transform. verdict: stationary=ADF rejects & KPSS not-reject; nonstationary=both opposite; disagree otherwise.",
 "per_member":stationarity,
 "critical_values":{"adf":ADF_CV,"kpss":KPSS_CV}}

# =====================================================================
# §2  AS-OF FRONTIER
# =====================================================================
# measured floors (INPUT from RTDSM-1, not re-derived). only the 17 members.
UNREVISED = {"NASDAQ":"1971-02-05","VIX":"1990-01-02","BAA10Y":"1986-01-02","BAAAAA":"1919-01-01"}
# alfred_vintage floors (member -> first as-of resolvable date)
VINTAGE_FLOOR = {"INDPRO":"1927-01-26","UNRATEv":"1960-03-15","HOUST":"1960-07-21","TCU":"1996-11-01",
 "UMCSENT":"1998-07-01","PERMIT":"1999-08-01","ICSA":"2009-05-28","IURSA":"2009-09-10",
 "W875":"2010-05-01","NFCI":"2011-05-25","CMRMT":"2013-06-01","PHILLY":"2015-04-16",
 "SAHM":"2019-09-01"}  # SAHMREALTIME realtime-by-construction, floor 2019-09
def member_asof_class(mem):
    if mem in UNREVISED: return "unrevised", UNREVISED[mem]
    if mem in VINTAGE_FLOOR:
        return ("realtime_by_construction" if mem=="SAHM" else "alfred_vintage"), VINTAGE_FLOOR[mem]
    return "none", None
CH=m.CHANNELS
member_class={}
for mem in MEMBERS:
    cls,floor=member_asof_class(mem)
    member_class[mem]={"as_of_class":cls,"floor":floor,
      "floor_year":int(floor[:4]) if floor else None}
# channel earliest as-of year (earliest member floor) + weight
chan_asof={}
for c,(w,mems) in CH.items():
    yrs=[member_class[x]["floor_year"] for x in mems if member_class[x]["floor_year"]]
    chan_asof[c]={"weight":w,"earliest_asof_year":min(yrs) if yrs else None,
      "members_floor":{x:member_class[x]["floor_year"] for x in mems}}
# frontier by year: count channels resolvable + cumulative weight
years=list(range(1919, 2027))
frontier=[]
for y in years:
    res=[c for c in CH if chan_asof[c]["earliest_asof_year"] and chan_asof[c]["earliest_asof_year"]<=y]
    frontier.append({"year":y,"n_channels":len(res),"total_weight":round(sum(CH[c][0] for c in res),3),
                     "channels":res})
def first_year_n(n):
    for f in frontier:
        if f["n_channels"]>=n: return f["year"]
    return None
first_year={str(n):first_year_n(n) for n in [1,2,3,4,5]}
# FRED-MD deepening: members present in FRED-MD panel whose vintage floor > 1999-08
FREDMD_MEMBERS={"INDPRO","UNRATEv","HOUST","PERMIT","TCU","UMCSENT","ICSA","W875","CMRMT","VIX","BAAAAA"}
# (FRED-MD cols: INDPRO,UNRATE,HOUST,PERMIT,CUMFNS(TCU),UMCSENTx,CLAIMSx(ICSA),W875RX1,CMRMTSPLx,VIXCLSx,AAA,BAA)
FREDMD_FLOOR=dt.date(1999,8,1)
fredmd_deepen={}
for mem in FREDMD_MEMBERS:
    f=member_class[mem]["floor"]
    if not f: continue
    fd=dt.date(int(f[:4]),int(f[5:7]),int(f[8:10]))
    if fd>FREDMD_FLOOR:
        fredmd_deepen[mem]={"current_floor":f,"fredmd_floor":"1999-08-01",
          "years_deepened":round((fd-FREDMD_FLOOR).days/365.25,1)}
section2={"member_asof_class":member_class,
 "channel_asof":chan_asof,
 "frontier_by_year_sample":{str(y):next(f for f in frontier if f["year"]==y) for y in [1919,1927,1960,1990,1999,2009,2011,2015,2026]},
 "first_year_for_N_channels":first_year,
 "deepest_4channel_asof_year":first_year["4"],
 "deepest_5channel_asof_year":first_year["5"],
 "fredmd_deepening":fredmd_deepen,
 "fredmd_does_not_deepen":["NFCI(not in FRED-MD; 5-channel wall stays 2011)","PHILLY","SAHM","BAA10Y","NASDAQ","IURSA(not in FRED-MD panel)"],
 "fredmd_discrepancy":"batch says 305 vintages to 2024-12; on disk = 295 monthly vintages 1999-08..2024-02 (185+110) + 1 current panel. measured, not the stated figure.",
 "rtdsm_unverified":"RTDSM would extend first-release stitching below these ALFRED floors for ~8 series (RTDSM-1), but is RIGHTS_UNRESOLVED — labelled unverified, not measurement.",
 "note":"channel as-of resolvable = at least one member as-of resolvable at/after its floor; single-member channels are thin (e.g. labor via UNRATE alone until ICSA/IURSA 2009). NFCI(2011) binds the 5-channel frontier permanently."}

# =====================================================================
# §8  NOWCAST DIVERGENCE  (run index_v1 twice, compare lines)
# =====================================================================
def run_index(disable):
    env=dict(os.environ); env["PYTHONDONTWRITEBYTECODE"]="1"
    out=WORK+("/idx_off.json" if disable else "/idx_on.json")
    env["INDEX_OUT"]=out
    if disable: env["NOWCAST_DISABLE"]="1"
    else: env.pop("NOWCAST_DISABLE",None)
    subprocess.run([sys.executable,"-c",
      "import sys;sys.path.insert(0,'%s');import index_v1"%MSRC],
      cwd=WORK,env=env,capture_output=True)
    return json.load(open(out))
on=run_index(False); off=run_index(True)
lon=on["line"]; loff=off["line"]
common=sorted(set(lon)&set(loff))
a=np.array([lon[d] for d in common]); b=np.array([loff[d] for d in common])
corr=float(np.corrcoef(a,b)[0,1])
diff=np.abs(a-b); mi=int(np.argmax(diff))
nowcast_from=on.get("nowcast_from")
# days influenced = published days strictly after nowcast_from that differ
n_diff=int(np.sum(diff>1e-9))
# byte-identical before nowcast_from?
pre=[i for i,d in enumerate(common) if nowcast_from and d<nowcast_from]
pre_identical=bool(all(diff[i]<1e-12 for i in pre)) if pre else None
section8={"fill_members":["CMRMT","INDPRO","TCU","HOUST","W875","SAHM","UNRATEv","BAAAAA","NFCI"],
 "nowcast_from":nowcast_from,
 "n_common_published_days":len(common),
 "n_days_influenced":n_diff,
 "corr_on_vs_off":round(corr,6),
 "max_abs_divergence":round(float(diff[mi]),4),"max_div_date":common[mi],
 "published_history_pre_nowcast_byte_identical":pre_identical,
 "revision_bias_fit_provenance":{
   "nber_labels_used":"not_directly (USRECD only sets MU/SD z-scale via is_baseline; no recession label in the revision regression)",
   "target_ledger_used":"not_used",
   "known_revised_values_as_target_used":"USED — b_hat target = (current-revised z) minus (first-print z), averaged over obs 24-120 months old; this is a second calibration channel against realized revisions (nowcast_harness.build_bhat).",
   "outcome_chosen_exclusion_window":"undeterminable — b_hat maturity window (24-120mo) is not outcome-chosen, but the MU/SD z-scale it runs in uses hardcoded EXCL 2020-01..2021-12 and 2023-01..2025-06 (outcome-adjacent).",
   "second_unlabeled_calibration_channel":True},
 "fills_append_only_confirmed":"CONFIRMED — index_v1 lines 217-226 insert only obs keys strictly after each member's last real obs (never overwrite a published key); baselines frozen before injection; days<=nowcast_from byte-identical (measured: %s)."%pre_identical}

OUT={"section5_stationarity":section5,"section2_asof_frontier":section2,"section8_nowcast":section8}
json.dump(OUT,open(REPO+"/research/universe_ch2/scratch/ch2_stat_asof_nowcast_results.json","w"),indent=1,default=str)
print("===WRITTEN===")
print("§5 verdicts (raw -> transformed | applied | disagreement | transform_fixes):")
for mem in MEMBERS:
    s=stationarity[mem]
    print(f"  {mem:8} raw={s['raw']['verdict']:13} tr={s['transformed']['verdict']:13} appl={s['applied_transform']:10} dis={str(s['implied_vs_applied_disagreement'])} fix={s['transform_moves_to_stationary']}")
print("\n§2 first year for N channels:", first_year)
print("§2 deepest 4-ch:",first_year['4']," 5-ch:",first_year['5'])
print("§2 fredmd deepen:",{k:v['years_deepened'] for k,v in fredmd_deepen.items()})
print("\n§8 nowcast_from:",nowcast_from,"n_influenced:",n_diff,"corr:",round(corr,6),
      "maxdiv:",round(float(diff[mi]),4),"@",common[mi],"pre_identical:",pre_identical)
