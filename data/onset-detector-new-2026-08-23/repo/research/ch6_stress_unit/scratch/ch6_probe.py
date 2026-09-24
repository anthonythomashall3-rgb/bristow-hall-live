#!/usr/bin/env python3
"""PROBE CH6 — S8 STRESS-UNIT CANDIDATE TABLE. Read-only, §20-class.
Evidence only, NO adoption. On the current members over their CH4 derived
(transformed) histories, compute three candidate stress-unit variants and
compare them. Parameters estimated on each of two sets: FULL sample and
EX-2020 (COVID window 2020-01-01..2021-12-31 removed, = index_v1.EXCL[0]),
then applied to the full transformed series.

Variants (each member's transform is already oriented higher = more stress,
same as index_v1 / CH7):
  (a) symmetric_z   : (x - med) / (1.4826*MAD)                 both tails count
  (b) deterioration : max(0, x-med) / (1.4826*MAD_upside)      S8 asymmetry test
                      (improvements clipped to 0; scale = stress-side dispersion)
  (c) percentile    : empirical percentile rank in [0,100]     distribution-free

Per variant/set:
  - distribution shape of the member stress-units (skew, excess kurtosis,
    clipped-fraction for deterioration)
  - recession-window behaviour: composite peak per 1948-> NBER episode
    (+ non-NBER 2022-24* watch), using index_v1's channel-mean + weighted
    renorm headline
  - cross-variant severity-ORDERING agreement (Spearman rho / Kendall tau),
    reported on the full-coverage episode tier (wsum>=0.99) where all channels
    are present, plus all-episodes for contrast; and full-vs-ex2020 stability.

Writes research/ch6_stress_unit_candidates_v1.csv + scratch JSON. Vault untouched.
"""
import os, sys, json, datetime as dt, bisect
import numpy as np

REPO = "/Users/anthonyhall/Desktop/RecessionMonitor 2/Recession Monitor V2"
MSRC = REPO + "/method_source"
WORK = REPO + "/research/ch6_stress_unit/scratch/work"

os.environ["NOWCAST_DISABLE"] = "1"                 # pure carry-forward transformed history
os.environ["INDEX_OUT"] = WORK + "/index_v1_out.scratch.json"
os.chdir(WORK)                                       # raw/ symlink -> current_revised_and_spatial
sys.path.insert(0, MSRC)
import index_v1 as m                                 # runs module build (prints AUROC etc.)

CHAN = m.CHANNELS
CH_ORDER = list(CHAN.keys())
MEMBERS = []
for c in CH_ORDER:
    MEMBERS += CHAN[c][1]
W = np.array([CHAN[c][0] for c in CH_ORDER])
T = m.T
END = m.END
USRECD = m.S["USRECD"]
COVID = m.EXCL[0]                                     # (2020-01-01, 2021-12-31)

member_first = {name: min(T[name]) for name in MEMBERS}
member_last  = {name: max(T[name]) for name in MEMBERS}
GRID_START = min(member_first.values())
DAYS = []
d = GRID_START
while d <= END:
    DAYS.append(d); d += dt.timedelta(days=1)
NDAYS = len(DAYS)

def asof(zd, ks, day):
    i = bisect.bisect_right(ks, day) - 1
    return zd[ks[i]] if i >= 0 else None

def in_covid(k):
    return COVID[0] <= k <= COVID[1]

# ---------- per-member parameter estimation on a value set ----------
def est_params(name, exclude_covid):
    ks = sorted(T[name])
    vals = np.array([T[name][k] for k in ks
                     if not (exclude_covid and in_covid(k))], float)
    med = float(np.median(vals))
    dev = np.abs(vals - med)
    mad = float(np.median(dev)) * 1.4826
    up = vals[vals > med]
    mad_up = float(np.median(np.abs(up - med))) * 1.4826 if len(up) else 0.0
    return dict(med=med,
                mad=mad if mad > 0 else 1.0,
                mad_up=mad_up if mad_up > 0 else (mad if mad > 0 else 1.0),
                sorted_vals=np.sort(vals), n=len(vals))

# ---------- three variant transforms ----------
def unit_symmetric(x, p):   return (x - p["med"]) / p["mad"]
def unit_deterior(x, p):    return max(0.0, x - p["med"]) / p["mad_up"]
def unit_percentile(x, p):
    sv = p["sorted_vals"]
    # fraction of estimation-set values <= x, in [0,100]
    return 100.0 * bisect.bisect_right(sv, x) / len(sv)

VARIANTS = {
    "symmetric":   unit_symmetric,
    "deterioration": unit_deterior,
    "percentile":  unit_percentile,
}
SETS = {"full": False, "ex2020": True}

# precompute params[(set)][member]
PARAMS = {s: {name: est_params(name, exc) for name in MEMBERS}
          for s, exc in SETS.items()}

# ---------- distribution shape of member stress-units (full applied series) ----------
def moments(a):
    a = np.asarray(a, float)
    mu = a.mean(); sd = a.std()
    if sd == 0:
        return 0.0, 0.0
    z = (a - mu) / sd
    return float((z**3).mean()), float((z**4).mean() - 3.0)   # skew, excess kurt

member_shape = {}   # (variant,set,member) -> stats over full transformed series
for vname, fn in VARIANTS.items():
    for sname, exc in SETS.items():
        for name in MEMBERS:
            p = PARAMS[sname][name]
            ks = sorted(T[name])
            u = np.array([fn(T[name][k], p) for k in ks], float)
            sk, ku = moments(u)
            clip = float(np.mean(u == 0.0)) if vname == "deterioration" else None
            member_shape[(vname, sname, name)] = dict(
                skew=round(sk, 4), exkurt=round(ku, 4),
                clipped_frac=(round(clip, 4) if clip is not None else None),
                umax=round(float(u.max()), 3), umin=round(float(u.min()), 3))

# ---------- composite headline for a (variant,set) ----------
def build_headline(fn, sname):
    Xu = np.full((NDAYS, len(MEMBERS)), np.nan)
    for j, name in enumerate(MEMBERS):
        p = PARAMS[sname][name]
        ks = sorted(T[name])
        ud = {k: fn(T[name][k], p) for k in ks}
        for i, day in enumerate(DAYS):
            v = asof(ud, ks, day)
            if v is not None:
                Xu[i, j] = v
    CS = np.full((NDAYS, len(CH_ORDER)), np.nan)
    for ci, c in enumerate(CH_ORDER):
        idx = [MEMBERS.index(x) for x in CHAN[c][1]]
        sub = Xu[:, idx]
        for i in range(NDAYS):
            row = sub[i][~np.isnan(sub[i])]
            if len(row):
                CS[i, ci] = row.mean()
    line = np.full(NDAYS, np.nan); wsum_line = np.full(NDAYS, np.nan)
    for i in range(NDAYS):
        present = ~np.isnan(CS[i])
        if not present.any():
            continue
        wsum = W[present].sum()
        line[i] = np.sum(W[present] * CS[i][present]) / wsum
        wsum_line[i] = wsum
    return line, wsum_line

# ---------- NBER episode windows from USRECD runs (matches CH7) ----------
uks = sorted(USRECD)
episodes = []; run_start = None; prev = 0; prev_k = uks[0]
for k in uks:
    v = USRECD[k]
    if v == 1 and prev == 0: run_start = k
    if v == 0 and prev == 1: episodes.append((run_start, prev_k))
    prev = v; prev_k = k
if prev == 1: episodes.append((run_start, uks[-1]))
epi_named = {}
for a, b in episodes:
    if b < GRID_START: continue
    aa = max(a, GRID_START)
    epi_named[f"{a.year}-{b.year}" if a.year != b.year else f"{a.year}"] = (aa, b)
watch_2022 = m.RECS.get("2022-24*")

def severity(line):
    peaks = {}
    allwin = dict(epi_named)
    if watch_2022: allwin["2022-24*"] = watch_2022
    for nm, (a, b) in allwin.items():
        w = [line[i] for i, day in enumerate(DAYS) if a <= day <= b and not np.isnan(line[i])]
        peaks[nm] = round(float(max(w)), 4) if w else None
    order = [nm for nm, v in sorted(peaks.items(),
             key=lambda kv: (kv[1] is not None, kv[1]), reverse=True)]
    return peaks, order

# episode coverage (max wsum inside window) from symmetric/full headline
_line_ref, _wsum_ref = build_headline(unit_symmetric, "full")
def episode_coverage():
    cov = {}
    allwin = dict(epi_named)
    if watch_2022: allwin["2022-24*"] = watch_2022
    for nm, (a, b) in allwin.items():
        ws = [_wsum_ref[i] for i, day in enumerate(DAYS) if a <= day <= b and not np.isnan(_wsum_ref[i])]
        cov[nm] = round(float(np.max(ws)), 3) if ws else None
    return cov
epi_cov = episode_coverage()
tier_full = {nm for nm, c in epi_cov.items() if c is not None and c >= 0.99}

# ---------- build all six configs ----------
peaks_all = {}; order_all = {}
for vname, fn in VARIANTS.items():
    for sname in SETS:
        line, _ = build_headline(fn, sname)
        pk, od = severity(line)
        peaks_all[(vname, sname)] = pk
        order_all[(vname, sname)] = od

# ---------- ranking + rank-correlation helpers ----------
def ranks(peaks, names):
    vals = np.array([peaks[n] for n in names], float)
    order = np.argsort(-vals, kind="mergesort")
    r = np.empty(len(names)); r[order] = np.arange(1, len(names) + 1)
    return {names[i]: int(r[i]) for i in range(len(names))}
def spearman(a, b, names):
    x = np.array([a[nm] for nm in names]); y = np.array([b[nm] for nm in names])
    if len(names) < 2 or x.std() == 0 or y.std() == 0: return None
    return round(float(np.corrcoef(x, y)[0, 1]), 4)
def kendall(a, b, names):
    conc = disc = 0
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            s = np.sign((a[names[i]] - a[names[j]]) * (b[names[i]] - b[names[j]]))
            if s > 0: conc += 1
            elif s < 0: disc += 1
    tot = conc + disc
    return round((conc - disc) / tot, 4) if tot else None
def swapped(rA, rB, names):
    sw = []
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = names[i], names[j]
            if np.sign(rA[a] - rA[b]) != np.sign(rB[a] - rB[b]):
                sw.append([a, b])
    return sw

def compare(cfgA, cfgB, subset):
    pA, pB = peaks_all[cfgA], peaks_all[cfgB]
    names = [nm for nm in order_all[cfgA]
             if nm in subset and pA.get(nm) is not None and pB.get(nm) is not None]
    rA = ranks(pA, names); rB = ranks(pB, names)
    oA = [nm for nm in order_all[cfgA] if nm in names]
    oB = [nm for nm in order_all[cfgB] if nm in names]
    return dict(n=len(names), order_A=oA, order_B=oB, identical=(oA == oB),
                spearman=spearman(rA, rB, names), kendall=kendall(rA, rB, names),
                swapped_pairs=swapped(rA, rB, names))

# cross-variant agreement on FULL estimation set, full-coverage tier + all
allset = set(peaks_all[("symmetric", "full")].keys())
cross = {"full_coverage_tier": {}, "all_episodes": {}}
pairs = [("symmetric", "deterioration"), ("symmetric", "percentile"),
         ("deterioration", "percentile")]
for a, b in pairs:
    key = f"{a}_vs_{b}"
    cross["full_coverage_tier"][key] = compare((a, "full"), (b, "full"), tier_full)
    cross["all_episodes"][key] = compare((a, "full"), (b, "full"), allset)

# full-vs-ex2020 stability per variant (full-coverage tier)
stability = {}
for v in VARIANTS:
    stability[v] = compare((v, "full"), (v, "ex2020"), tier_full)

# ---------- emit JSON ----------
out = {
    "batch_id": "CH6_STRESS_UNIT_CANDIDATES",
    "window": "read-only, §20-class, research/ only",
    "writes_vault": False, "network": False,
    "git_head": open(REPO + "/research/ch6_stress_unit/scratch/git_head.txt").read().strip(),
    "grid": {"start": GRID_START.isoformat(), "end": END.isoformat(), "n_days": NDAYS},
    "members": MEMBERS, "n_members": len(MEMBERS),
    "channels": {c: {"weight": CHAN[c][0], "members": CHAN[c][1]} for c in CH_ORDER},
    "variants": {
        "symmetric": "(x-med)/(1.4826*MAD); both tails",
        "deterioration": "max(0,x-med)/(1.4826*MAD_upside); improvements clipped, "
                         "scaled by stress-side dispersion (S8 asymmetry test)",
        "percentile": "empirical percentile rank in [0,100]; distribution-free",
    },
    "estimation_sets": {"full": "all obs",
                        "ex2020": f"exclude {COVID[0]}..{COVID[1]} (index_v1.EXCL[0]) "
                                  "from parameter estimation, apply to full series"},
    "episode_coverage_max_wsum": epi_cov,
    "full_coverage_tier": sorted(tier_full),
    "severity_peaks": {f"{v}|{s}": peaks_all[(v, s)] for v in VARIANTS for s in SETS},
    "severity_order": {f"{v}|{s}": order_all[(v, s)] for v in VARIANTS for s in SETS},
    "cross_variant_ordering_agreement": cross,
    "full_vs_ex2020_stability": stability,
}
outjson = REPO + "/research/ch6_stress_unit/scratch/ch6_results.json"
json.dump(out, open(outjson, "w"), indent=1, default=str)

# ---------- CSV: per-member distribution shape (variant x set) ----------
csv_path = REPO + "/research/ch6_stress_unit_candidates_v1.csv"
mem_chan = {}
for c in CH_ORDER:
    for x in CHAN[c][1]:
        mem_chan[x] = c
lines = ["member,channel,variant,est_set,skew,exkurt,clipped_frac,umax,umin"]
for name in MEMBERS:
    for v in VARIANTS:
        for s in SETS:
            d = member_shape[(v, s, name)]
            lines.append(f"{name},{mem_chan[name]},{v},{s},{d['skew']},{d['exkurt']},"
                         f"{d['clipped_frac']},{d['umax']},{d['umin']}")
# episode severity block (all six configs, per episode) as commented section
lines.append("")
hdr = "# EPISODE," + ",".join(f"{v}|{s}" for v in VARIANTS for s in SETS) + ",max_wsum_cov"
lines.append(hdr)
for nm in order_all[("symmetric", "full")]:
    cells = [str(peaks_all[(v, s)].get(nm)) for v in VARIANTS for s in SETS]
    lines.append(f"# {nm}," + ",".join(cells) + f",{epi_cov.get(nm)}")
# cross-variant agreement summary
lines.append("")
lines.append("# CROSS-VARIANT ORDERING AGREEMENT (full est set, full-coverage tier)")
lines.append("# pair,n,spearman,kendall,identical")
for a, b in pairs:
    c = cross["full_coverage_tier"][f"{a}_vs_{b}"]
    lines.append(f"# {a}_vs_{b},{c['n']},{c['spearman']},{c['kendall']},{c['identical']}")
lines.append("# FULL-vs-EX2020 stability per variant (full-coverage tier)")
lines.append("# variant,n,spearman,kendall,identical")
for v in VARIANTS:
    c = stability[v]
    lines.append(f"# {v},{c['n']},{c['spearman']},{c['kendall']},{c['identical']}")
open(csv_path, "w").write("\n".join(lines) + "\n")

print("===CH6 RESULTS WRITTEN===")
print("json:", outjson)
print("csv :", csv_path)
print(json.dumps({
    "grid": out["grid"],
    "full_coverage_tier": sorted(tier_full),
    "cross_full_tier": {k: {"spearman": v["spearman"], "kendall": v["kendall"],
                            "identical": v["identical"], "n": v["n"]}
                        for k, v in cross["full_coverage_tier"].items()},
    "stability_full_tier": {v: {"spearman": stability[v]["spearman"],
                                "kendall": stability[v]["kendall"],
                                "identical": stability[v]["identical"]}
                            for v in VARIANTS},
    "order_symmetric_full": order_all[("symmetric", "full")],
    "order_deterioration_full": order_all[("deterioration", "full")],
    "order_percentile_full": order_all[("percentile", "full")],
}, indent=1, default=str))
