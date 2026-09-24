#!/usr/bin/env python3
"""CH-R125 — effN on the CYCLE-FREQUENCY component. READ-ONLY. Writes only research/effn_cycle/.

REUSES CH-R122's estimator + panel construction VERBATIM (copied byte-for-byte from
research/effn_realtime/effn_realtime.py). The ONLY change is the INPUT: each transformed
column on the monthly GRID is passed through a cycle-frequency filter BEFORE corr_matrix.
The estimator eff_n(), corr_matrix(), pear() are UNCHANGED. Changing both would make
nothing comparable (batch STOP).

Filters evaluated (report sensitivity, step 2):
  raw       : no filter (control; must reproduce CH-R122 3.689/3.089 cw, 3.248/2.874 deep)
  lowpass7  : centered moving-average window 7  (low-pass, kills high-freq noise, keeps trend+cycle)
  lowpass13 : centered moving-average window 13 (stronger low-pass)
  bk18_96_K12 : Baxter-King band-pass, business-cycle band 18-96 months, K=12 (removes trend AND noise)
  bk18_96_K18 : Baxter-King band-pass 18-96 months, K=18
"""
import os, sys, csv, json, datetime as dt, bisect
import numpy as np

REPO = "/Users/anthonyhall/Desktop/RecessionMonitor 2/Recession Monitor V2"
RAW  = REPO + "/data_archive/current_revised_and_spatial/"
MSRC = REPO + "/method_source"
OUT  = REPO + "/research/effn_cycle"
import re as _re
_LIVE = REPO + "/live_data"
_HEADS = _LIVE + "/runtime/source_heads"
_NORM = _LIVE + "/store/normalized/sha256"
_ASOF_RE = _re.compile(r"\.(?:DEEP)?ASOF(\d{8})$")
def asof_date(series_id):
    mo = _ASOF_RE.search(series_id or "")
    if not mo: return None
    s = mo.group(1); return dt.date(int(s[:4]), int(s[4:6]), int(s[6:8]))
_DEC = json.JSONDecoder()
def stream_records(source_id):
    h = json.load(open(f"{_HEADS}/{source_id}.json"))
    sha = h["normalized_sha256"]
    with open(f"{_NORM}/{sha[:2]}/{sha}.json") as f:
        s = f.read()
    i = s.index('"records":') + len('"records":')
    i = s.index('[', i) + 1
    n = len(s)
    while i < n:
        while i < n and s[i] in ' \t\r\n,': i += 1
        if i >= n or s[i] == ']': break
        obj, i = _DEC.raw_decode(s, i)
        yield obj

os.environ["NOWCAST_DISABLE"] = "1"
os.environ["INDEX_OUT"] = OUT + "/index_v1_out.scratch.json"
_work = REPO + "/research/channel_structure_ch1/scratch/work"
os.chdir(_work)
sys.path.insert(0, MSRC)
import index_v1 as m

START, END = m.START, m.END

def month_ends(a, b):
    out = []; y, mo = a.year, a.month
    while (y < b.year) or (y == b.year and mo <= b.month):
        nxt = dt.date(y+1,1,1) if mo == 12 else dt.date(y, mo+1, 1)
        out.append(nxt - dt.timedelta(days=1))
        y, mo = (y+1,1) if mo == 12 else (y, mo+1)
    return out
GRID = month_ends(START, END)
NG = len(GRID)

# ===== ESTIMATOR VERBATIM FROM CH-R122 (do not modify) =====
def eff_n(Rsub):
    Rf = np.nan_to_num(Rsub, nan=0.0); np.fill_diagonal(Rf, 1.0)
    Rf = (Rf + Rf.T)/2.0
    ev = np.clip(np.linalg.eigvalsh(Rf), 0, None)
    return float((ev.sum()**2)/np.sum(ev**2)) if ev.sum() else float('nan')
def pear(a, b):
    ok = ~np.isnan(a) & ~np.isnan(b)
    if ok.sum() < 48: return None
    aa, bb = a[ok], b[ok]
    if aa.std() == 0 or bb.std() == 0: return None
    return float(np.corrcoef(aa, bb)[0,1])
def corr_matrix(X):
    K = X.shape[1]; R = np.full((K, K), np.nan)
    for i in range(K):
        R[i, i] = 1.0
        for j in range(i+1, K):
            r = pear(X[:, i], X[:, j]); R[i, j] = R[j, i] = (r if r is not None else np.nan)
    return R
# ===========================================================

def apply_transform(base, level):
    y = m.yoy; rf = m.rise_floor; dd = m.drawdown
    if base == "ICSA":    return y(level)
    if base == "IURSA":   return rf(level)
    if base == "SAHM":    return dict(level)
    if base == "UNRATEv": return rf(level, 120)
    if base == "INDPRO":  return {k:-v for k,v in y(level).items()}
    if base == "CMRMT":   return {k:-v for k,v in y(level).items()}
    if base == "TCU":     return {k:-v for k,v in y(level).items()}
    if base == "PHILLY":  return {k:-v for k,v in level.items()}
    if base == "PERMIT":  return {k:-v for k,v in y(level).items()}
    if base == "HOUST":   return {k:-v for k,v in y(level).items()}
    if base == "UMCSENT": return {k:-v for k,v in dd(level).items()}
    if base == "W875":    return {k:-v for k,v in y(level).items()}
    if base == "NFCI":    return dict(level)
    return delta365(level)

def delta365(series):
    ks = sorted(series); out = {}
    for k in ks:
        prior = k - dt.timedelta(days=365)
        i = bisect.bisect_left(ks, prior)
        cand = [x for x in ks[max(0, i-1):i+2] if abs((x - prior).days) <= 45]
        if cand:
            p = min(cand, key=lambda x: abs((x - prior).days))
            out[k] = series[k] - series[p]
    return out

def asof_val(zd, keys, d):
    i = bisect.bisect_right(keys, d) - 1
    return zd[keys[i]] if i >= 0 else None

LANES = {
 "CMRMT":   (["fred_cmrmtspl_api_vintages"], True),
 "PHILLY":  (["fred_gacdfsa066msfrbphi_api_vintages"], True),
 "GDPC1":   (["fred_gdpc1_api_vintages","fred_gdpc1_api_vintages_deep"], False),
 "HOUST":   (["fred_houst_api_vintages","fred_houst_api_vintages_deep"], True),
 "ICSA":    (["fred_icsa_api_vintages"], True),
 "INDPRO":  (["fred_indpro_api_vintages","fred_indpro_api_vintages_deep"], True),
 "IURSA":   (["fred_iursa_api_vintages"], True),
 "NFCI":    (["fred_nfci_api_vintages"], True),
 "PAYEMS":  (["fred_payems_api_vintages","fred_payems_api_vintages_deep"], False),
 "PERMIT":  (["fred_permit_api_vintages","fred_permit_api_vintages_deep"], True),
 "SAHM":    (["fred_sahmrealtime_api_vintages"], True),
 "TCU":     (["fred_tcu_api_vintages","fred_tcu_api_vintages_deep"], True),
 "UMCSENT": (["fred_umcsent_api_vintages","fred_umcsent_api_vintages_deep"], True),
 "UNRATEv": (["fred_unrate_api_vintages","fred_unrate_api_vintages_deep"], True),
 "W875":    (["fred_w875rx1_api_vintages"], True),
 "cdc_resp":(["cdc_resp_publication_history"], False),
}
CR_RAW = {
 "CMRMT":"CMRMTSPL","PHILLY":"GACDFSA066MSFRBPHI","HOUST":"HOUST","ICSA":"ICSA",
 "INDPRO":"INDPRO","IURSA":"IURSA","NFCI":"NFCI","PERMIT":"PERMIT",
 "SAHM":"SAHMREALTIME","TCU":"TCU","UMCSENT":"UMCSENT","UNRATEv":"UNRATE","W875":"W875RX1",
 "GDPC1":"GDPC1","PAYEMS":"PAYEMS","cdc_resp":None,
}
N_SOURCE_LANES = sum(len(v[0]) for v in LANES.values())

def load_vintages(source_ids):
    vint = {}
    for sid in source_ids:
        if not os.path.exists(f"{_HEADS}/{sid}.json"): continue
        for r in stream_records(sid):
            a = asof_date(r.get("series_id"))
            if a is None: continue
            v = r.get("value")
            if v in (None, "", "."): continue
            try: val = float(v)
            except (TypeError, ValueError): continue
            op = r.get("observation_period")
            try:
                rp = dt.date(int(op[:4]), int(op[5:7]), int(op[8:10]))
            except (TypeError, ValueError): continue
            vint.setdefault(a, {})[rp] = val
    return vint

def realtime_column(base, vint):
    asofs = sorted(vint)
    col = np.full(NG, np.nan)
    if not asofs: return col, None
    edge = {}
    for a in asofs:
        lvl = vint[a]
        t = apply_transform(base, lvl)
        if not t: edge[a] = None; continue
        tk = sorted(t)
        i = bisect.bisect_right(tk, a) - 1
        edge[a] = t[tk[i]] if i >= 0 else None
    floor = None
    for gi, d in enumerate(GRID):
        j = bisect.bisect_right(asofs, d) - 1
        if j < 0: continue
        val = edge[asofs[j]]
        if val is not None:
            col[gi] = val
            if floor is None: floor = d
    return col, floor

def load_raw(sid):
    out = {}
    p = RAW + sid + ".csv"
    if not os.path.exists(p): return out
    for r in csv.reader(open(p)):
        if r and r[0][0:1].isdigit() and len(r) > 1 and r[1] not in ("", "."):
            try: out[dt.date(int(r[0][:4]), int(r[0][5:7]), int(r[0][8:10]))] = float(r[1])
            except ValueError: pass
    return out

def cr_column(base):
    raw_id = CR_RAW[base]
    if raw_id is None: return np.full(NG, np.nan)
    lvl = load_raw(raw_id)
    if not lvl: return np.full(NG, np.nan)
    t = apply_transform(base, lvl)
    tk = sorted(t)
    col = np.full(NG, np.nan)
    for gi, d in enumerate(GRID):
        v = asof_val(t, tk, d)
        if v is not None: col[gi] = v
    return col

# ===== BUILD PANELS (verbatim) =====
bases = list(LANES.keys())
RT = np.full((NG, len(bases)), np.nan)
CR = np.full((NG, len(bases)), np.nan)
floors = {}; nobs_rt = {}
for j, b in enumerate(bases):
    src_ids, is_mem = LANES[b]
    vint = load_vintages(src_ids)
    col_rt, floor = realtime_column(b, vint)
    RT[:, j] = col_rt
    floors[b] = floor.isoformat() if floor else None
    CR[:, j] = cr_column(b)
    nobs_rt[b] = int(np.sum(~np.isnan(RT[:, j])))
keep = [j for j in range(len(bases)) if nobs_rt[bases[j]] >= 60]
dropped_lt60 = [(bases[j], nobs_rt[bases[j]]) for j in range(len(bases)) if nobs_rt[bases[j]] < 60]
kb = [bases[j] for j in keep]
RTk = RT[:, keep]; CRk = CR[:, keep]
np.save(OUT + "/RTk.npy", RTk); np.save(OUT + "/CRk.npy", CRk)

# ============================================================================
# CYCLE-FREQUENCY FILTERS  (the ONLY change vs CH-R122: the input)
# ============================================================================
def lowpass_ma(col, w):
    """Centered moving average, window w (odd). Output NaN where window incomplete/has NaN."""
    n = len(col); out = np.full(n, np.nan); half = w // 2
    for i in range(n):
        lo, hi = i - half, i + half
        if lo < 0 or hi >= n: continue
        seg = col[lo:hi+1]
        if np.isnan(seg).any(): continue
        out[i] = seg.mean()
    return out

def _bk_weights(K, pl, pu):
    """Baxter-King band-pass ideal weights truncated at +-K, demeaned to sum 0 (unit-root safe).
       Passband = periods in [pl, pu] months."""
    wl = 2*np.pi/pu   # low angular frequency (long period)
    wu = 2*np.pi/pl   # high angular frequency (short period)
    a = np.zeros(K+1)
    a[0] = (wu - wl)/np.pi
    for j in range(1, K+1):
        a[j] = (np.sin(j*wu) - np.sin(j*wl))/(j*np.pi)
    b = np.concatenate([a[:0:-1], a])   # symmetric length 2K+1
    b = b - b.mean()                    # enforce sum-zero (removes trend/unit root)
    return b

def bandpass_bk(col, K, pl, pu):
    b = _bk_weights(K, pl, pu); n = len(col); out = np.full(n, np.nan)
    for i in range(K, n-K):
        seg = col[i-K:i+K+1]
        if np.isnan(seg).any(): continue
        out[i] = float(np.dot(b, seg))
    return out

def filter_panel(P, kind):
    Q = np.full_like(P, np.nan)
    for j in range(P.shape[1]):
        col = P[:, j]
        if kind == "raw":            Q[:, j] = col
        elif kind == "lowpass7":     Q[:, j] = lowpass_ma(col, 7)
        elif kind == "lowpass13":    Q[:, j] = lowpass_ma(col, 13)
        elif kind == "bk18_96_K12":  Q[:, j] = bandpass_bk(col, 12, 18, 96)
        elif kind == "bk18_96_K18":  Q[:, j] = bandpass_bk(col, 18, 18, 96)
        else: raise ValueError(kind)
    return Q

FILTERS = ["raw","lowpass7","lowpass13","bk18_96_K12","bk18_96_K18"]

def common_window(RTf, CRf, cols_idx):
    sub_rt = RTf[:, cols_idx]; sub_cr = CRf[:, cols_idx]
    rows = np.where(~np.isnan(sub_rt).any(axis=1))[0]
    if len(rows) < 24: return None
    r_rt = corr_matrix(sub_rt[rows]); r_cr = corr_matrix(sub_cr[rows])
    e_rt = round(eff_n(r_rt), 3); e_cr = round(eff_n(r_cr), 3)
    return {"window": [GRID[rows[0]].isoformat(), GRID[rows[-1]].isoformat()],
            "n_months": int(len(rows)), "lanes": len(cols_idx),
            "effN_rt": e_rt, "effN_cr_matched": e_cr,
            "gap_cr_minus_rt": round(e_cr - e_rt, 3)}

all_idx = list(range(len(kb)))
deep_lanes = [b for b in kb if floors[b] and floors[b] < "2000"]
deep_idx = [kb.index(b) for b in deep_lanes]

results = {}
for kind in FILTERS:
    RTf = filter_panel(RTk, kind); CRf = filter_panel(CRk, kind)
    results[kind] = {
        "PRIMARY_common_window_all15": common_window(RTf, CRf, all_idx),
        "deep_subset_pre2000": common_window(RTf, CRf, deep_idx),
    }

# ---- leave-one-out under each filter, common-window all-15 pool ----
def loo(RTf, cols_idx):
    sub = RTf[:, cols_idx]
    rows = np.where(~np.isnan(sub).any(axis=1))[0]
    if len(rows) < 24: return None
    base_effN = eff_n(corr_matrix(sub[rows]))
    out = []
    for i in range(len(cols_idx)):
        idx = [x for x in range(len(cols_idx)) if x != i]
        e = eff_n(corr_matrix(sub[rows][:, idx]))
        out.append({"lane": kb[cols_idx[i]], "delta": round(base_effN - e, 3)})
    out.sort(key=lambda r: r["delta"], reverse=True)
    return {"base_effN": round(base_effN, 3), "lanes": out}

loo_by_filter = {}
for kind in FILTERS:
    RTf = filter_panel(RTk, kind)
    loo_by_filter[kind] = loo(RTf, all_idx)

# ---- sign-flip lanes: LOO delta sign raw vs primary cycle filter ----
CH_R122_RAW_LOO = {  # verbatim from CH-R122 receipt leave_one_out_realtime
 "UMCSENT":0.361,"NFCI":0.332,"PHILLY":0.292,"PERMIT":0.214,"HOUST":0.199,
 "W875":-0.226,"TCU":-0.203,"IURSA":-0.182,"INDPRO":-0.177,"SAHM":-0.106,"PAYEMS":-0.098,
}
PRIMARY = "bk18_96_K12"
def sign(x): return 0 if abs(x) < 1e-9 else (1 if x > 0 else -1)
signflip = []
prim_loo = {d["lane"]: d["delta"] for d in loo_by_filter[PRIMARY]["lanes"]}
for lane, raw_d in CH_R122_RAW_LOO.items():
    cyc_d = prim_loo.get(lane)
    if cyc_d is None: continue
    flip = sign(raw_d) != sign(cyc_d)
    signflip.append({"lane": lane, "raw_delta": raw_d, "cycle_delta": cyc_d, "sign_flip": flip})

# ---- CONTROL: reproduce CH-R105/CH-R122 full-universe effN 8.85 (estimator unchanged) ----
def control_full_universe():
    names = [l.strip() for l in open(REPO + "/research/effn/universe_files.txt") if l.strip()]
    Zc = {}
    for lbl in [x for c in m.CHANNELS for x in m.CHANNELS[c][1]]:
        zd, ks = m.Z[lbl]; Zc["M17:"+lbl] = zd
    for nm in names:
        d = load_raw(nm)
        if not d: continue
        t = delta365(d)
        if len(t) < 40: continue
        ks = sorted(t)
        base = [t[k] for k in ks if m.is_baseline(k)]
        if len(base) < 30: continue
        mu = sum(base)/len(base); sd = (sum((x-mu)**2 for x in base)/len(base))**0.5 or 1.0
        Zc[nm] = {k:(t[k]-mu)/sd for k in ks}
    cols = list(Zc.keys())
    Xu = np.full((NG, len(cols)), np.nan)
    for j, c in enumerate(cols):
        zd = Zc[c]; ks = sorted(zd)
        for i, d in enumerate(GRID):
            v = asof_val(zd, ks, d)
            if v is not None: Xu[i, j] = v
    nn = np.array([np.sum(~np.isnan(Xu[:, j])) for j in range(len(cols))])
    kk = [j for j in range(len(cols)) if nn[j] >= 60]
    return round(eff_n(corr_matrix(Xu[:, kk])), 2), len(kk)
ctrl_effN, ctrl_K = control_full_universe()

# ---- raw-filter control: must reproduce CH-R122 common-window/deep numbers ----
raw_cw = results["raw"]["PRIMARY_common_window_all15"]
raw_deep = results["raw"]["deep_subset_pre2000"]
control_ok = (raw_cw["effN_rt"] == 3.689 and raw_cw["effN_cr_matched"] == 3.089
              and raw_deep["effN_rt"] == 3.248 and raw_deep["effN_cr_matched"] == 2.874
              and abs(ctrl_effN - 8.85) < 0.01)

# ---- gap-sign-flip decision across filters ----
def gap_flipped(kind):
    cw = results[kind]["PRIMARY_common_window_all15"]
    return (cw["gap_cr_minus_rt"] >= 0) if cw else None
gap_flip_table = {k: {"gap_cw": results[k]["PRIMARY_common_window_all15"]["gap_cr_minus_rt"],
                      "gap_deep": results[k]["deep_subset_pre2000"]["gap_cr_minus_rt"],
                      "rt_no_longer_exceeds_cw": gap_flipped(k)} for k in FILTERS}

summary = {
  "batch": "CH-R125_EFFN_CYCLE_FREQUENCY",
  "read_only": True, "derives_nothing": True, "no_network": True, "no_store_mutation": True,
  "estimator": "CH-R105/CH-R122 participation ratio VERBATIM (sum ev)^2/sum(ev^2); pairwise Pearson min overlap 48; keep>=60 obs. ONLY the input changed (cycle-frequency filter).",
  "pool": {"kept_ge60": len(kb), "members": kb, "dropped_lt60": dropped_lt60,
           "admission_rule": "identical to CH-R122: verbatim publisher bytes with ASOF knowledge date; exact index_v1 member T (Delta365 non-members); month-end grid."},
  "deep_lanes_pre2000": deep_lanes,
  "control_full_universe_effN": ctrl_effN, "control_full_universe_kept": ctrl_K, "control_target": 8.85,
  "control_raw_reproduces_CH_R122": control_ok,
  "raw_common_window_check": raw_cw, "raw_deep_check": raw_deep,
  "filters_evaluated": FILTERS,
  "filter_definitions": {
    "lowpass7":"centered MA window 7 (low-pass ~<7mo cut)","lowpass13":"centered MA window 13",
    "bk18_96_K12":"Baxter-King band-pass 18-96 months, K=12 (trend+noise removed)",
    "bk18_96_K18":"Baxter-King band-pass 18-96 months, K=18"},
  "results_by_filter": results,
  "gap_sign_by_filter": gap_flip_table,
  "leave_one_out_by_filter": loo_by_filter,
  "signflip_vs_CH_R122_raw_primary_bk18_96_K12": signflip,
  "primary_filter": PRIMARY,
}
with open(OUT + "/CH-R125_summary.json", "w") as f: json.dump(summary, f, indent=1)
print(json.dumps({
  "control_raw_reproduces_CH_R122": control_ok,
  "control_full_universe_effN": ctrl_effN,
  "raw_cw": raw_cw, "raw_deep": raw_deep,
  "gap_sign_by_filter": gap_flip_table}, indent=1))
print("SIGNFLIP:", json.dumps(signflip))
print("KEPT:", kb, "DEEP:", deep_lanes)
