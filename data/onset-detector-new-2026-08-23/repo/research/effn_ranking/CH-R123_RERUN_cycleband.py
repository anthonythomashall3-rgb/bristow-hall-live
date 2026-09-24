#!/usr/bin/env python3
"""CH-R123 RE-RUN — rank acquisitions on the CYCLE-BAND metric CH-R125 recommends.
READ-ONLY. Writes only under research/effn_ranking/. Derives NOTHING (no channel/member/
weight/transform/threshold/dimension). §22.4 NOT crossed.

WHY THIS RE-RUN EXISTS
  PASTE_ORDER waves 10/11/12 RE-GATED CH-R123: "now AFTER CH-R125 COMPLETE, not CH-R122.
  Rank on whichever metric CH-R125 recommends. Ranking on raw effN is now known to reward
  noise. The first run's raw-effN ranking is superseded." CH-R125 COMPLETE 20260809T040636Z
  and its receipt sets `primary_filter = bk18_96_K12` (Baxter-King band-pass, business-cycle
  band 18-96 months, K=12 -- removes trend AND high-freq noise).

WHAT CHANGES vs the first run (research/effn_ranking/CH-R123_*.json, PRESERVED, not deleted)
  The FIRST run ranked on RAW participation-ratio LOO. This run band-passes every panel column
  to the 18-96 month business-cycle band BEFORE the correlation, then re-ranks. Estimator
  (eff_n participation ratio, corr_matrix pairwise min-overlap 48, keep>=60) is BYTE-IDENTICAL
  to CH-R105/CH-R122/CH-R125; ONLY the input filter changed (exactly CH-R125's discipline).

METHOD
  cr table : rebuild CH-R105's 294-pool cr panel VERBATIM (index_v1 17-member T + Delta365
             generic, z vs expansion baseline, month-end grid). Band-pass each column with
             bandpass_bk(.,12,18,96). Full-pool effN + per-series LOO delta on the band-passed
             pairwise-corr. Control: RAW cr effN must reproduce CH-R105's 8.85 (estimator pin).
  rt table : taken DIRECTLY from CH-R125_summary.json leave_one_out_by_filter[bk18_96_K12]
             (15 lanes, MEASURED, no recompute).
  LOO delta = base_effN - effN(pool minus series). POSITIVE = independent contributor;
              NEGATIVE = redundant drag (removing it RAISES effN).
"""
import os, sys, csv, json, bisect, datetime as dt
import numpy as np

# --- source tree (data + method_source), exactly as CH-R105/CH-R122/CH-R125 ---
REPO = "/Users/anthonyhall/Desktop/RecessionMonitor 2/Recession Monitor V2"
RAW  = REPO + "/data_archive/current_revised_and_spatial/"
MSRC = REPO + "/method_source"
# write surface = Projects repo research/effn_ranking ONLY
OUT  = "/Users/anthonyhall/Projects/bristow-hall/repo/research/effn_ranking"
UNIV = "/Users/anthonyhall/Projects/bristow-hall/repo/research/effn/universe_files.txt"
CH_R125 = "/Users/anthonyhall/Projects/bristow-hall/repo/research/effn_cycle/CH-R125_summary.json"

os.environ["NOWCAST_DISABLE"] = "1"
os.environ["INDEX_OUT"] = OUT + "/index_v1_out.scratch.json"
os.chdir(REPO + "/research/channel_structure_ch1/scratch/work")
sys.path.insert(0, MSRC)
import index_v1 as m

CHAN = m.CHANNELS
MEMBERS17 = []
for c in list(CHAN.keys()): MEMBERS17 += CHAN[c][1]
assert len(MEMBERS17) == 17
START, END = m.START, m.END
is_baseline = m.is_baseline

# ---------- estimator + filter, VERBATIM from effn_probe / effn_cycle ----------
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
def _bk_weights(K, pl, pu):
    wl = 2*np.pi/pu; wu = 2*np.pi/pl
    a = np.zeros(K+1); a[0] = (wu - wl)/np.pi
    for j in range(1, K+1):
        a[j] = (np.sin(j*wu) - np.sin(j*wl))/(j*np.pi)
    b = np.concatenate([a[:0:-1], a]); b = b - b.mean()
    return b
def bandpass_bk(col, K, pl, pu):
    b = _bk_weights(K, pl, pu); n = len(col); out = np.full(n, np.nan)
    for i in range(K, n-K):
        seg = col[i-K:i+K+1]
        if np.isnan(seg).any(): continue
        out[i] = float(np.dot(b, seg))
    return out

# ---------- panel loaders, VERBATIM from effn_probe ----------
def load_raw(path):
    out = {}
    for r in csv.reader(open(path)):
        if r and r[0][0:1].isdigit() and len(r) > 1 and r[1] not in ("", "."):
            try: out[dt.date(int(r[0][:4]), int(r[0][5:7]), int(r[0][8:10]))] = float(r[1])
            except ValueError: pass
    return out
def delta365(series):
    ks = sorted(series); out = {}
    for k in ks:
        prior = k - dt.timedelta(days=365); i = bisect.bisect_left(ks, prior)
        cand = [x for x in ks[max(0, i-1):i+2] if abs((x - prior).days) <= 45]
        if cand:
            p = min(cand, key=lambda x: abs((x - prior).days)); out[k] = series[k] - series[p]
    return out
def zify(tseries):
    ks = sorted(tseries); base = [tseries[k] for k in ks if is_baseline(k)]
    if len(base) < 30: return None
    mu = sum(base)/len(base); sd = (sum((x-mu)**2 for x in base)/len(base))**0.5 or 1.0
    return {k: (tseries[k]-mu)/sd for k in ks}
def month_ends(a, b):
    out = []; y, mo = a.year, a.month
    while (y < b.year) or (y == b.year and mo <= b.month):
        nxt = dt.date(y+1,1,1) if mo == 12 else dt.date(y, mo+1, 1)
        out.append(nxt - dt.timedelta(days=1)); y, mo = (y+1,1) if mo == 12 else (y, mo+1)
    return out
def asof(zd, keys, d):
    i = bisect.bisect_right(keys, d) - 1
    return zd[keys[i]] if i >= 0 else None

names = [l.strip() for l in open(UNIV) if l.strip()]
RAWS = {}
for nm in names:
    d = load_raw(RAW + nm + ".csv")
    if d: RAWS[nm] = d

Zc, kind = {}, {}
for lbl in MEMBERS17:
    zd, ks = m.Z[lbl]; Zc["M17:"+lbl] = zd; kind["M17:"+lbl] = "member17"
for nm, series in RAWS.items():
    t = delta365(series)
    if len(t) < 40: continue
    z = zify(t)
    if z is None: continue
    Zc[nm] = z; kind[nm] = "generic"

GRID = month_ends(START, END)
cols = list(Zc.keys()); KEYS = {c: sorted(Zc[c]) for c in cols}
X = np.full((len(GRID), len(cols)), np.nan)
for j, c in enumerate(cols):
    zd, ks = Zc[c], KEYS[c]
    for i, d in enumerate(GRID):
        v = asof(zd, ks, d)
        if v is not None: X[i, j] = v
lab_all = [c.replace("M17:","") if kind[c]=="member17" else c for c in cols]

def build(Xin, keep_min=60):
    nn = np.array([np.sum(~np.isnan(Xin[:, j])) for j in range(Xin.shape[1])])
    keep = [j for j in range(Xin.shape[1]) if nn[j] >= keep_min]
    Xk = Xin[:, keep]; labk = [lab_all[j] for j in keep]; kk = [kind[cols[j]] for j in keep]
    R = corr_matrix(Xk)
    base = eff_n(R)
    loo = []
    K = len(labk)
    for i in range(K):
        idx = [x for x in range(K) if x != i]
        e = eff_n(R[np.ix_(idx, idx)])
        loo.append({"name": labk[i], "kind": kk[i], "delta": round(base - e, 4),
                    "n_obs": int(np.sum(~np.isnan(Xk[:, i])))})
    loo.sort(key=lambda r: r["delta"], reverse=True)
    return round(base, 4), K, loo

# RAW control (must reproduce CH-R105 effN 8.85)
raw_base, raw_K, raw_loo = build(X)
# BAND-PASS cr (the recommended metric)
Xbp = np.column_stack([bandpass_bk(X[:, j], 12, 18, 96) for j in range(X.shape[1])])
bp_base, bp_K, bp_loo = build(Xbp)

# rt table: DIRECT from CH-R125 (measured), no recompute
r125 = json.load(open(CH_R125))
rt_bp = r125["leave_one_out_by_filter"]["bk18_96_K12"]           # 15 lanes
rt_raw = r125["leave_one_out_by_filter"]["raw"]
signflip = r125["signflip_vs_CH_R122_raw_primary_bk18_96_K12"]

out = {
 "batch_id": "CH-R123_EFFN_MARGINAL_RANKING (RE-RUN, cycle-band)",
 "recommended_metric": "bk18_96_K12 (Baxter-King band-pass 18-96mo, K=12) -- CH-R125 primary_filter",
 "supersedes": "research/effn_ranking/CH-R123_*.json first run (raw-effN LOO), PRESERVED on disk",
 "cr_current_revised": {
   "raw_control": {"base_effN": raw_base, "K": raw_K,
                   "reproduces_CH_R105_8.85": abs(raw_base - 8.85) < 0.02},
   "cycleband_bk18_96_K12": {"base_effN": bp_base, "K": bp_K},
   "cycleband_top15_contributors": bp_loo[:15],
   "cycleband_bottom15_drags": bp_loo[-15:],
 },
 "rt_realtime": {
   "metric": "bk18_96_K12 LOO, 15 lanes, common window 2020-01..2026-07 (CH-R125 measured)",
   "base_effN": rt_bp["base_effN"], "lanes_ranked": rt_bp["lanes"],
   "sign_flips_vs_raw": [s for s in signflip if s["sign_flip"]],
 },
}
json.dump(out, open(OUT + "/CH-R123_RERUN_cycleband.json", "w"), indent=1)
# also dump the full cr band-pass LOO for the record
json.dump({"base_effN": bp_base, "K": bp_K, "loo": bp_loo,
           "raw_control_base_effN": raw_base, "raw_control_K": raw_K},
          open(OUT + "/CH-R123_RERUN_cr_cycleband_LOO.json", "w"), indent=1)

print("RAW cr control base_effN=%.4f K=%d reproduces_8.85=%s" % (raw_base, raw_K, abs(raw_base-8.85)<0.02))
print("BAND-PASS cr base_effN=%.4f K=%d" % (bp_base, bp_K))
print("cr cycle-band TOP5:", [(r["name"], r["delta"]) for r in bp_loo[:5]])
print("cr cycle-band BOT5:", [(r["name"], r["delta"]) for r in bp_loo[-5:]])
print("rt bk18_96_K12 base_effN=%.3f" % rt_bp["base_effN"])
print("rt sign-flips vs raw:", [s["lane"] for s in signflip if s["sign_flip"]])
