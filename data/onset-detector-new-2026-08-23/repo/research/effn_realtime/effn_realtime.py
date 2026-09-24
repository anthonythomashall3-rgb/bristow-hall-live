#!/usr/bin/env python3
"""CH-R122 — REAL-TIME effective N. READ-ONLY. Writes only research/effn_realtime/.

Reuses CH-R105's estimator EXACTLY:
  * effN = participation ratio of the correlation-matrix eigenvalues, eff_n():
      Rf=nan->0, diag=1, symmetrize, ev=eigvalsh clip>=0, (sum ev)^2 / sum ev^2.
  * month-end grid 1976-06-01..END, same as CH-R105.
  * 17-member transforms = index_v1's EXACT hand-authored T (yoy/rise_floor/drawdown/
    identity/negation). Non-member lanes -> generic Delta365 (measurement device).
  * keep >=60 monthly obs; pairwise-complete Pearson, min overlap 48.
NOTE effN is invariant to per-series affine maps (mean/sd, sign): the z-standardisation
and the sign negations in T DO NOT change the correlation spectrum. Kept for fidelity.

REAL-TIME panel: for each as-of lane, at grid date d use the vintage in force
(latest asof-date <= d); the transform at d is computed on THAT vintage's own
reference-period history (yoy/rise_floor/drawdown look back within the vintage,
never into a revised series). Value at d = transform evaluated at the vintage's
latest reference period <= d. No padding; per-lane floor recorded.
"""
import os, sys, csv, json, datetime as dt, bisect
import numpy as np

REPO = "/Users/anthonyhall/Desktop/RecessionMonitor 2/Recession Monitor V2"
RAW  = REPO + "/data_archive/current_revised_and_spatial/"
MSRC = REPO + "/method_source"
OUT  = REPO + "/research/effn_realtime"
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
    """Yield record dicts one at a time (raw_decode) to avoid loading GB files whole."""
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

# ---- import index_v1 exactly as CH-R105 did (gives T-functions, S, m.T, GRID) ----
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

# ============================================================================
# transform application (index_v1's exact functions) to an arbitrary level dict
# ============================================================================
def apply_transform(base, level):
    """Return transformed {date: value} using the member's EXACT index_v1 transform.
       For non-members return Delta365 (generic measurement device)."""
    y = m.yoy; rf = m.rise_floor; dd = m.drawdown
    if base == "ICSA":    return y(level)
    if base == "IURSA":   return rf(level)                 # default look=370
    if base == "SAHM":    return dict(level)               # already deterioration
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
    return delta365(level)                                 # generic

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

# ============================================================================
# 24 as-of lanes -> 16 distinct bases (deep+shallow merged). base->member transform
# ============================================================================
# (source_id list, base symbol used by apply_transform, is_headline_member)
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
# current-revised store id for the generic/base level (for matched CR set)
CR_RAW = {
 "CMRMT":"CMRMTSPL","PHILLY":"GACDFSA066MSFRBPHI","HOUST":"HOUST","ICSA":"ICSA",
 "INDPRO":"INDPRO","IURSA":"IURSA","NFCI":"NFCI","PERMIT":"PERMIT",
 "SAHM":"SAHMREALTIME","TCU":"TCU","UMCSENT":"UMCSENT","UNRATEv":"UNRATE","W875":"W875RX1",
 "GDPC1":"GDPC1","PAYEMS":"PAYEMS","cdc_resp":None,
}
N_SOURCE_LANES = sum(len(v[0]) for v in LANES.values())

# ---- load + merge vintages per base -> {asof_date: {rp_date: value}} ----
def load_vintages(source_ids):
    import time
    vint = {}
    for sid in source_ids:
        if not os.path.exists(f"{_HEADS}/{sid}.json"): continue
        t0 = time.time(); nrec = 0
        for r in stream_records(sid):
            nrec += 1
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
        print(f"  loaded {sid}: {nrec} recs, {len(vint)} vintages, {time.time()-t0:.1f}s", flush=True)
    return vint

# ---- build real-time transformed column on GRID ----
def realtime_column(base, vint):
    asofs = sorted(vint)
    col = np.full(NG, np.nan)
    if not asofs: return col, None
    # cache transform-edge per vintage (edge = value at latest rp <= that vintage's asof)
    edge = {}
    for a in asofs:
        lvl = vint[a]
        t = apply_transform(base, lvl)
        if not t: edge[a] = None; continue
        tk = sorted(t)
        # edge rp = latest rp <= a (vintage cannot know rp after its asof)
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

# ---- build matched current-revised transformed column on GRID ----
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

# ============================================================================
# BUILD PANELS
# ============================================================================
bases = list(LANES.keys())
RT = np.full((NG, len(bases)), np.nan)
CR = np.full((NG, len(bases)), np.nan)
floors = {}; nobs_rt = {}; nobs_cr = {}; vintcount = {}
for j, b in enumerate(bases):
    src_ids, is_mem = LANES[b]
    print(f"[{j+1}/{len(bases)}] base {b} ...", flush=True)
    vint = load_vintages(src_ids)
    vintcount[b] = len(vint)
    col_rt, floor = realtime_column(b, vint)
    RT[:, j] = col_rt
    floors[b] = floor.isoformat() if floor else None
    CR[:, j] = cr_column(b)
    nobs_rt[b] = int(np.sum(~np.isnan(RT[:, j])))
    nobs_cr[b] = int(np.sum(~np.isnan(CR[:, j])))

# keep >=60 monthly obs (applied to RT pool; matched CR uses SAME kept set)
keep = [j for j in range(len(bases)) if nobs_rt[bases[j]] >= 60]
dropped_lt60 = [(bases[j], nobs_rt[bases[j]]) for j in range(len(bases)) if nobs_rt[bases[j]] < 60]
kb = [bases[j] for j in keep]
RTk = RT[:, keep]; CRk = CR[:, keep]

R_rt = corr_matrix(RTk)
R_cr = corr_matrix(CRk)
effN_rt = eff_n(R_rt)
effN_cr_matched = eff_n(R_cr)

# ---- RIGOROUS common-window: rows where ALL kept RT lanes present (true member-
#      for-member, same window for every pair). This is the defensible gap: the
#      full-grid pooled number mixes windows because 7/15 lanes have no vintage
#      before 2020, so their pairwise |r| is measured on 2020+ only. ----
rt_all = ~np.isnan(RTk).any(axis=1)
cw_rows = np.where(rt_all)[0]
if len(cw_rows):
    cw_start = GRID[cw_rows[0]].isoformat(); cw_end = GRID[cw_rows[-1]].isoformat()
    effN_rt_cw = round(eff_n(corr_matrix(RTk[cw_rows])), 3)
    effN_cr_cw = round(eff_n(corr_matrix(CRk[cw_rows])), 3)
    gap_cw = round(effN_cr_cw - effN_rt_cw, 3)
else:
    cw_start = cw_end = None; effN_rt_cw = effN_cr_cw = gap_cw = None
common_window = {"window": [cw_start, cw_end], "n_months": int(len(cw_rows)),
                 "effN_rt": effN_rt_cw, "effN_cr_matched": effN_cr_cw,
                 "gap_cr_minus_rt": gap_cw, "lanes": len(kb)}

# ---- DEEP subset: lanes whose RT floor is pre-2000 (long common history) ----
deep_lanes = [b for b in kb if floors[b] and floors[b] < "2000"]
di = [kb.index(b) for b in deep_lanes]
if len(di) >= 2:
    RTd = RTk[:, di]; CRd = CRk[:, di]
    drows = np.where(~np.isnan(RTd).any(axis=1))[0]
    deep_subset = {"lanes": deep_lanes,
                   "window": [GRID[drows[0]].isoformat(), GRID[drows[-1]].isoformat()] if len(drows) else [None,None],
                   "n_months": int(len(drows)),
                   "effN_rt": round(eff_n(corr_matrix(RTd[drows])), 3) if len(drows) else None,
                   "effN_cr_matched": round(eff_n(corr_matrix(CRd[drows])), 3) if len(drows) else None}
    if deep_subset["effN_rt"] is not None:
        deep_subset["gap_cr_minus_rt"] = round(deep_subset["effN_cr_matched"] - deep_subset["effN_rt"], 3)
else:
    deep_subset = {"lanes": deep_lanes, "note": "fewer than 2 pre-2000 lanes"}

# ---- leave-one-out effN (real-time pool) ----
loo = []
for i in range(len(kb)):
    idx = [x for x in range(len(kb)) if x != i]
    sub = R_rt[np.ix_(idx, idx)]
    loo.append({"lane": kb[i], "effN_without": round(eff_n(sub), 3),
                "delta": round(effN_rt - eff_n(sub), 3),
                "n_obs_rt": nobs_rt[kb[i]], "floor": floors[kb[i]]})
loo.sort(key=lambda r: r["delta"], reverse=True)

# ---- by-era effN at NBER peaks (real-time pool, expanding-to-peak window) ----
NBER_PEAKS = ["1980-01-31","1981-07-31","1990-07-31","2001-03-31","2007-12-31","2020-02-29"]
def effN_window(X, cols_idx, upto):
    up = dt.date(int(upto[:4]),int(upto[5:7]),int(upto[8:10]))
    rows = [gi for gi,d in enumerate(GRID) if d <= up]
    if len(rows) < 24: return None, 0
    Xw = X[np.ix_(rows, cols_idx)]
    nn = np.array([np.sum(~np.isnan(Xw[:,j])) for j in range(Xw.shape[1])])
    ck = [j for j in range(Xw.shape[1]) if nn[j] >= 24]
    if len(ck) < 2: return None, len(ck)
    return round(eff_n(corr_matrix(Xw[:, ck])), 3), len(ck)
era = []
for pk in NBER_PEAKS:
    # lane-matched: use only lanes whose RT floor <= peak (present in real time then).
    matched = [i for i,b in enumerate(kb) if floors[b] and floors[b] <= pk]
    rt_v, rt_k = effN_window(RTk, matched, pk)
    cr_v, cr_k = effN_window(CRk, matched, pk)  # SAME lane subset, so member-for-member
    era.append({"nber_peak": pk, "lanes_matched": [kb[i] for i in matched],
                "n_lanes": len(matched), "effN_rt": rt_v, "effN_cr_matched": cr_v,
                "gap_cr_minus_rt": (round(cr_v-rt_v,3) if (rt_v is not None and cr_v is not None) else None)})

# ============================================================================
# CONTROL: reproduce CH-R105 full-universe effN 8.85 (independent recompute)
# ============================================================================
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

# ============================================================================
# WRITE
# ============================================================================
np.save(OUT + "/rt_corr_matrix.npy", R_rt)
np.save(OUT + "/cr_matched_corr_matrix.npy", R_cr)
summary = {
  "batch": "CH-R122_EFFN_REALTIME_BASELINE",
  "estimator": "participation ratio (sum ev)^2/sum(ev^2) of correlation matrix; month-end grid; 17-member exact index_v1 T, others Delta365; keep>=60 monthly obs; pairwise Pearson min overlap 48 (CH-R105 estimator verbatim)",
  "grid": "month-end", "grid_n": NG, "window": [START.isoformat(), END.isoformat()],
  "as_of_source_lanes": N_SOURCE_LANES,
  "distinct_as_of_bases": len(bases),
  "note_24_to_16": "24 source_matrix archive_snapshot_asof lanes collapse to 16 distinct real-time series: 8 lanes are DEEP vintage extensions of another lane's base (GDPC1,HOUST,INDPRO,PAYEMS,PERMIT,TCU,UMCSENT,UNRATE) and are MERGED, not double-counted. effN over 24 raw columns would be inflated-redundant nonsense (8 exact-duplicate pairs).",
  "pool_kept_ge60": len(kb),
  "pool_kept_members": kb,
  "dropped_lt60obs": dropped_lt60,
  "admission_rule": "series enters pool only if bytes came verbatim from a named publisher (FRED/ALFRED api_vintages, CDC) with a knowledge date (ASOF vintage label); level -> exact index_v1 member transform (or Delta365 for non-members) -> month-end grid.",
  "effN_realtime_fullgrid_pooled": round(effN_rt, 3),
  "effN_current_revised_matched_fullgrid_pooled": round(effN_cr_matched, 3),
  "gap_cr_minus_rt_fullgrid_pooled": round(effN_cr_matched - effN_rt, 3),
  "WARN_fullgrid_pooled": "mixes windows: 7/15 lanes have no vintage pre-2020, so their pairwise |r| is measured on 2020+ only. Use common_window/deep_subset for defensible member-for-member gaps.",
  "PRIMARY_common_window": common_window,
  "deep_subset_pre2000": deep_subset,
  "trap_note": "effN rises for orthogonal NOISE as fast as orthogonal SIGNAL. Real-time revisions ADD independent noise, which can lift effN above the revised set (seen here). A higher real-time effN is NOT more usable signal.",
  "control_full_universe_effN": ctrl_effN,
  "control_full_universe_kept": ctrl_K,
  "control_target": 8.85,
  "control_reproduced": abs(ctrl_effN - 8.85) < 0.01,
  "per_lane_vintage_count": vintcount,
  "per_lane_floor_rt": floors,
  "per_lane_nobs_rt": nobs_rt,
  "per_lane_nobs_cr": nobs_cr,
  "leave_one_out_rt": loo,
  "by_era_nber_peaks": era,
}
with open(OUT + "/CH-R122_summary.json", "w") as f: json.dump(summary, f, indent=1)
print(json.dumps({k:summary[k] for k in [
  "effN_realtime_fullgrid_pooled","effN_current_revised_matched_fullgrid_pooled",
  "gap_cr_minus_rt_fullgrid_pooled","PRIMARY_common_window","deep_subset_pre2000",
  "control_full_universe_effN","control_reproduced","pool_kept_ge60","distinct_as_of_bases",
  "as_of_source_lanes","dropped_lt60obs"]}, indent=1))
print("BY_ERA:", json.dumps(summary["by_era_nber_peaks"]))
print("KEPT:", kb)
print("FLOORS:", floors)
