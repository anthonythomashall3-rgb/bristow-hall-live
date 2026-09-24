#!/usr/bin/env python3
"""CH-R105 — effective-N / redundancy re-measure across the EXPANDED universe.
READ-ONLY. Writes only under research/effn/. Derives NOTHING (chooses no cluster
count, sets no membership). Measures redundancy structure so Phase-3 clustering can
rest on evidence, not the inherited 5-channel layout.

METHOD NOTES (recorded in receipt):
 * 17 registered members use index_v1's EXACT hand-authored deterioration transforms T,
   then z vs the composite's expansion baseline (NBER recessions + COVID + 2022-24 excl).
 * Every OTHER candidate uses a single generic trend-removing transform Delta365
   (x(d) - x(d-365), nearest prior within 45d), then z vs the SAME baseline. Delta365 is a
   MEASUREMENT DEVICE, not an accepted transform; it is applied uniformly with NO per-series
   orientation choice.
 * Effective-N (participation ratio of the correlation-matrix eigenvalues) and pairwise |r|
   redundancy are INVARIANT to per-series orientation: a global sign flip of one variable is
   D R D with D diagonal +-1, which leaves the eigenvalue spectrum unchanged, and |r| is
   orientation-free. So no orientation is ever derived and none of the reported metrics depend
   on one. (§22.1 satisfied: measures, derives nothing.)
 * Sampling grid = MONTH-END (reduces daily carry-forward autocorrelation inflation; the
   17-member DAILY effN is separately reproduced as a calibration check against CH1).
"""
import os, sys, csv, json, math, datetime as dt, bisect
import numpy as np

REPO = "/Users/anthonyhall/Desktop/RecessionMonitor 2/Recession Monitor V2"
RAW  = REPO + "/data_archive/current_revised_and_spatial/"
MSRC = REPO + "/method_source"
OUT  = REPO + "/research/effn"

# ---- load index_v1 exactly as CH1 did (reproduces the 17-member transforms) ----
os.environ["NOWCAST_DISABLE"] = "1"
os.environ["INDEX_OUT"] = OUT + "/index_v1_out.scratch.json"
_work = REPO + "/research/channel_structure_ch1/scratch/work"
os.chdir(_work)
sys.path.insert(0, MSRC)
import index_v1 as m

CHAN = m.CHANNELS
CH_ORDER = list(CHAN.keys())
MEMBERS17 = []
for c in CH_ORDER: MEMBERS17 += CHAN[c][1]
assert len(MEMBERS17) == 17
START, END, DAYS = m.START, m.END, m.DAYS
is_baseline = m.is_baseline

# ---------- generic loader (same rule as index_v1.load) ----------
def load_raw(path):
    out = {}
    for r in csv.reader(open(path)):
        if r and r[0][0:1].isdigit() and len(r) > 1 and r[1] not in ("", "."):
            try:
                out[dt.date(int(r[0][:4]), int(r[0][5:7]), int(r[0][8:10]))] = float(r[1])
            except ValueError:
                pass
    return out

names = [l.strip() for l in open(OUT + "/universe_files.txt") if l.strip()]
RAWS = {}
for nm in names:
    d = load_raw(RAW + nm + ".csv")
    if d: RAWS[nm] = d

# ---------- generic Delta365 transform ----------
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

# ---------- z vs expansion baseline ----------
def zify(tseries):
    ks = sorted(tseries)
    base = [tseries[k] for k in ks if is_baseline(k)]
    if len(base) < 30: return None
    mu = sum(base)/len(base)
    sd = (sum((x-mu)**2 for x in base)/len(base))**0.5 or 1.0
    return {k: (tseries[k]-mu)/sd for k in ks}

# transformed z per candidate. 17 members -> exact T (already z in m.Z). others -> Delta365.
Zc = {}                      # name -> {date: z}
kind = {}                    # name -> "member17" | "generic"
# map member label -> store id used for its raw (for dedup vs generic copies)
for lbl in MEMBERS17:
    zd, ks = m.Z[lbl]
    Zc["M17:"+lbl] = zd
    kind["M17:"+lbl] = "member17"
for nm, series in RAWS.items():
    t = delta365(series)
    if len(t) < 40: continue
    z = zify(t)
    if z is None: continue
    Zc[nm] = z
    kind[nm] = "generic"

# ---------- month-end sampling grid ----------
def month_ends(a, b):
    out = []; y, mo = a.year, a.month
    while (y < b.year) or (y == b.year and mo <= b.month):
        if mo == 12: nxt = dt.date(y+1,1,1)
        else: nxt = dt.date(y, mo+1, 1)
        out.append(nxt - dt.timedelta(days=1))
        y, mo = (y+1,1) if mo == 12 else (y, mo+1)
    return out
GRID = month_ends(START, END)

def asof(zd, keys, d):
    i = bisect.bisect_right(keys, d) - 1
    return zd[keys[i]] if i >= 0 else None

cols = list(Zc.keys())
KEYS = {c: sorted(Zc[c]) for c in cols}
X = np.full((len(GRID), len(cols)), np.nan)
for j, c in enumerate(cols):
    zd, ks = Zc[c], KEYS[c]
    for i, d in enumerate(GRID):
        v = asof(zd, ks, d)
        if v is not None: X[i, j] = v

# require >=60 non-null monthly obs
nn = np.array([np.sum(~np.isnan(X[:, j])) for j in range(len(cols))])
keep = [j for j in range(len(cols)) if nn[j] >= 60]
dropped = [(cols[j], int(nn[j])) for j in range(len(cols)) if nn[j] < 60]
cols_k = [cols[j] for j in keep]
Xk = X[:, keep]
K = len(cols_k)

# ---------- pairwise correlation (pairwise-complete, min overlap 48) ----------
def pear(a, b):
    ok = ~np.isnan(a) & ~np.isnan(b)
    if ok.sum() < 48: return None, int(ok.sum())
    aa, bb = a[ok], b[ok]
    if aa.std() == 0 or bb.std() == 0: return None, int(ok.sum())
    return float(np.corrcoef(aa, bb)[0,1]), int(ok.sum())

R = np.full((K, K), np.nan)
for i in range(K):
    R[i, i] = 1.0
    for j in range(i+1, K):
        r, n = pear(Xk[:, i], Xk[:, j])
        R[i, j] = R[j, i] = (r if r is not None else np.nan)

# ---------- effective N (participation ratio) on a matrix ----------
def eff_n(Rsub):
    Rf = np.nan_to_num(Rsub, nan=0.0)
    np.fill_diagonal(Rf, 1.0)
    Rf = (Rf + Rf.T)/2.0
    ev = np.linalg.eigvalsh(Rf)
    ev = np.clip(ev, 0, None)
    if ev.sum() == 0: return float('nan')
    return float((ev.sum()**2)/np.sum(ev**2))

# global effective N over full kept universe
effN_global = eff_n(R)

# ---------- per-candidate redundancy ----------
idx17 = [i for i, c in enumerate(cols_k) if kind[c] == "member17"]
lab = [c.replace("M17:","") if kind[c]=="member17" else c for c in cols_k]
def maxabs_to(iset, i):
    best, who = 0.0, None
    for j in iset:
        if j == i: continue
        v = R[i, j]
        if not np.isnan(v) and abs(v) > best: best, who = abs(v), j
    return best, (lab[who] if who is not None else None)

redund = []
allidx = list(range(K))
for i in range(K):
    mx_all, nn_all = maxabs_to(allidx, i)
    mx_17,  nn_17  = maxabs_to(idx17, i)
    redund.append({
        "name": lab[i], "kind": kind[cols_k[i]], "n_obs": int(np.sum(~np.isnan(Xk[:, i]))),
        "max_abs_r_any": round(mx_all, 3), "nn_any": nn_all,
        "max_abs_r_to17": round(mx_17, 3), "nn_17": nn_17,
    })

# classify NEW (generic) series vs the 17-member set
def bucket(x):
    if x >= 0.80: return "near_duplicate"
    if x >= 0.60: return "redundant"
    if x >= 0.30: return "partial"
    return "orthogonal"
new_series = [row for row in redund if row["kind"] == "generic"]
for row in new_series: row["bucket_vs17"] = bucket(row["max_abs_r_to17"])
from collections import Counter
buckets = Counter(row["bucket_vs17"] for row in new_series)

# ---------- clustering on 1-|r| (average linkage) at K=2..12 ----------
D = 1.0 - np.abs(np.nan_to_num(R, nan=0.0))
np.fill_diagonal(D, 0.0)
def avg_linkage(D, kmax=12):
    n = D.shape[0]
    clusters = {i: [i] for i in range(n)}
    Dm = D.copy(); active = set(range(n))
    snapshots = {}
    def cur_labels():
        lab_ = np.full(n, -1); cl = list(active)
        for ci, c in enumerate(cl):
            for member in clusters[c]: lab_[member] = ci
        return lab_
    snapshots[len(active)] = cur_labels()
    while len(active) > 1:
        best = None
        al = list(active)
        for a_i in range(len(al)):
            for b_i in range(a_i+1, len(al)):
                a, b = al[a_i], al[b_i]
                if best is None or Dm[a, b] < best[0]: best = (Dm[a, b], a, b)
        _, a, b = best
        merged = clusters[a] + clusters[b]
        for c in active:
            if c in (a, b): continue
            na, nb = len(clusters[a]), len(clusters[b])
            Dm[a, c] = Dm[c, a] = (na*Dm[a, c] + nb*Dm[b, c])/(na+nb)
        clusters[a] = merged; del clusters[b]; active.discard(b)
        if len(active) <= kmax: snapshots[len(active)] = cur_labels()
    return snapshots
snaps = avg_linkage(D, 12)

def silhouette(labels, D):
    n = len(labels); uniq = set(labels)
    if len(uniq) < 2: return float('nan')
    sil = []
    for i in range(n):
        same = [j for j in range(n) if labels[j]==labels[i] and j!=i]
        a = np.mean([D[i,j] for j in same]) if same else 0.0
        bvals = []
        for c in uniq:
            if c == labels[i]: continue
            oth = [j for j in range(n) if labels[j]==c]
            if oth: bvals.append(np.mean([D[i,j] for j in oth]))
        b = min(bvals) if bvals else 0.0
        denom = max(a, b)
        sil.append((b-a)/denom if denom > 0 else 0.0)
    return float(np.mean(sil))

cluster_options = []
for kk in range(2, 13):
    if kk not in snaps: continue
    labels = snaps[kk]
    sizes = sorted(Counter(labels).values(), reverse=True)
    cluster_options.append({
        "k": kk, "silhouette_1minusabsr": round(silhouette(labels, D), 4),
        "eff_n_within_reference": round(effN_global, 3),
        "sizes": sizes,
    })

# ---------- calibration: reproduce CH1 per-channel effN on DAILY grid ----------
def daily_matrix(members):
    Xd = np.full((len(DAYS), len(members)), np.nan)
    for j, lbl in enumerate(members):
        zd, ks = m.Z[lbl]
        for i, d in enumerate(DAYS):
            v = asof(zd, ks, d)
            if v is not None: Xd[i, j] = v
    return Xd
cal = {}
for c in CH_ORDER:
    w, mem = CHAN[c]
    Xd = daily_matrix(mem)
    Rc = np.full((len(mem), len(mem)), np.nan)
    for i in range(len(mem)):
        Rc[i, i] = 1.0
        for j in range(i+1, len(mem)):
            ok = ~np.isnan(Xd[:, i]) & ~np.isnan(Xd[:, j])
            if ok.sum() >= 3 and Xd[ok, i].std() > 0 and Xd[ok, j].std() > 0:
                rr = float(np.corrcoef(Xd[ok, i], Xd[ok, j])[0,1]); Rc[i, j] = Rc[j, i] = rr
    cal[c] = {"nominal": len(mem), "eff_n_daily": round(eff_n(Rc), 2)}

# effN over the 17 members alone on the MONTHLY grid (for comparability w/ expanded)
R17 = R[np.ix_(idx17, idx17)]
effN17_monthly = eff_n(R17)

# ---------- write full artifacts ----------
np.save(OUT + "/corr_matrix.npy", R)
with open(OUT + "/labels.json", "w") as f: json.dump({"labels": lab, "kind": [kind[c] for c in cols_k]}, f)
with open(OUT + "/redundancy_rows.json", "w") as f: json.dump(redund, f, indent=0)

summary = {
    "grid": "month-end", "grid_n": len(GRID), "window": [START.isoformat(), END.isoformat()],
    "candidates_loaded": len(RAWS), "candidates_transformed": len(cols),
    "kept_ge60obs": K, "dropped_lt60obs": len(dropped),
    "members17_present": len(idx17),
    "effN_global_kept_universe": round(effN_global, 2),
    "effN_17_members_monthly": round(effN17_monthly, 2),
    "ch1_perchannel_daily_calibration": cal,
    "orthogonality_buckets_vs17": dict(buckets),
    "n_new_generic": len(new_series),
    "cluster_option_set": cluster_options,
}
with open(OUT + "/CH-R105_summary.json", "w") as f: json.dump(summary, f, indent=1)
print(json.dumps(summary, indent=1))
print("DROPPED_LT60 (first 30):", dropped[:30])
