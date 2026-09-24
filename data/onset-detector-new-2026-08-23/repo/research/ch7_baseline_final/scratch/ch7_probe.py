#!/usr/bin/env python3
"""PROBE CH7 — S1 BASELINE FINAL NUMBERS. Read-only, §20-class.
Extends CH1 §5 to the COMPLETE store (each member's full transformed history,
composite grid from earliest member obs -> END). Compares two candidate S1
standardization baselines on ALL members:

  A) robust      : full-history median / (1.4826*MAD), no labels excluded
  B) nber_excl   : mean / std over NBER-expansion days only (USRECD==0),
                   NO extra COVID/2022-24 windows removed (that is the CURRENT
                   index's is_baseline; reported here as `current` for contrast).

Emits per-member deltas + composite severity-ordering agreement across every
NBER episode 1948-> (episode windows derived from USRECD runs) plus the
non-NBER 2022-24* watch window from index_v1.RECS. Writes nothing to the vault.
"""
import os, sys, json, datetime as dt, bisect
import numpy as np

REPO = "/Users/anthonyhall/Desktop/RecessionMonitor 2/Recession Monitor V2"
MSRC = REPO + "/method_source"
WORK = REPO + "/research/ch7_baseline_final/scratch/work"

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
T = m.T                                              # transformed native series name->{date:val}
END = m.END
USRECD = m.S["USRECD"]
in_recession = m.in_recession                        # USRECD-only NBER membership

# ---------- earliest usable member date (>=1948) ----------
member_first = {name: min(T[name]) for name in MEMBERS}
member_last  = {name: max(T[name]) for name in MEMBERS}
GRID_START = max(dt.date(1948, 1, 1), min(member_first.values()))
GRID_START = min(member_first.values())              # true earliest; report vs 1948 in brief
DAYS = []
d = GRID_START
while d <= END:
    DAYS.append(d); d += dt.timedelta(days=1)
NDAYS = len(DAYS)

def asof(zd, ks, day):
    i = bisect.bisect_right(ks, day) - 1
    return zd[ks[i]] if i >= 0 else None

# ---------- baselines per member over FULL transformed history ----------
def baseline_robust(name):
    vals = np.array(list(T[name].values()), float)
    med = float(np.median(vals)); mad = float(np.median(np.abs(vals - med))) * 1.4826
    return med, (mad if mad > 0 else 1.0), len(vals)

def baseline_nber_excl(name):
    ks = sorted(T[name])
    base = [T[name][k] for k in ks if not in_recession(k)]
    a = np.array(base, float)
    mu = float(a.mean()); sd = float(a.std())
    return mu, (sd if sd > 0 else 1.0), len(base)

def baseline_current(name):
    # index_v1's frozen baseline: NBER-expansion minus COVID minus 2022-24
    ks = sorted(T[name])
    base = [T[name][k] for k in ks if m.is_baseline(k)]
    a = np.array(base, float)
    mu = float(a.mean()); sd = float(a.std())
    return mu, (sd if sd > 0 else 1.0), len(base)

BASE = {}
for name in MEMBERS:
    rmu, rsd, nfull = baseline_robust(name)
    nmu, nsd, nbase = baseline_nber_excl(name)
    cmu, csd, cbase = baseline_current(name)
    BASE[name] = dict(robust_mu=rmu, robust_sd=rsd, nber_mu=nmu, nber_sd=nsd,
                      cur_mu=cmu, cur_sd=csd, n_full=nfull, n_nber_base=nbase,
                      n_cur_base=cbase,
                      first=member_first[name].isoformat(),
                      last=member_last[name].isoformat())

# ---------- per-member deltas (nber_excl relative to robust) ----------
for name in MEMBERS:
    b = BASE[name]
    b["d_mu"] = b["nber_mu"] - b["robust_mu"]
    b["d_sd"] = b["nber_sd"] - b["robust_sd"]
    # level shift expressed in robust-sd units (how far the two baselines move a z)
    b["mu_shift_in_robust_sd"] = b["d_mu"] / b["robust_sd"]
    b["sd_ratio_nber_over_robust"] = b["nber_sd"] / b["robust_sd"]

# ---------- z series under each baseline, then composite headline ----------
def z_series(name, mu, sd):
    ks = sorted(T[name])
    zd = {k: (T[name][k] - mu) / sd for k in ks}
    return zd, ks

def build_headline(key_mu, key_sd):
    # daily member-z matrix
    Xz = np.full((NDAYS, len(MEMBERS)), np.nan)
    for j, name in enumerate(MEMBERS):
        zd, ks = z_series(name, BASE[name][key_mu], BASE[name][key_sd])
        for i, day in enumerate(DAYS):
            v = asof(zd, ks, day)
            if v is not None:
                Xz[i, j] = v
    # channel scores = mean of present member z within channel
    CS = np.full((NDAYS, len(CH_ORDER)), np.nan)
    for ci, c in enumerate(CH_ORDER):
        idx = [MEMBERS.index(x) for x in CHAN[c][1]]
        sub = Xz[:, idx]
        for i in range(NDAYS):
            row = sub[i][~np.isnan(sub[i])]
            if len(row):
                CS[i, ci] = row.mean()
    # renormalized weighted headline (matches module partial-coverage handling)
    line = np.full(NDAYS, np.nan)
    wsum_line = np.full(NDAYS, np.nan)
    for i in range(NDAYS):
        present = ~np.isnan(CS[i])
        if not present.any():
            continue
        wsum = W[present].sum()
        line[i] = np.sum(W[present] * CS[i][present]) / wsum
        wsum_line[i] = wsum
    return line, wsum_line

line_rob, wsum_rob = build_headline("robust_mu", "robust_sd")
line_nber, wsum_nber = build_headline("nber_mu", "nber_sd")

def line_corr(a, b):
    ok = ~np.isnan(a) & ~np.isnan(b)
    return round(float(np.corrcoef(a[ok], b[ok])[0, 1]), 5), int(ok.sum())

def max_div(a, b):
    ok = ~np.isnan(a) & ~np.isnan(b)
    diff = np.abs(a - b); diff[~ok] = -1
    i = int(np.argmax(diff))
    return round(float(diff[i]), 4), DAYS[i].isoformat()

# ---------- NBER episode windows derived from USRECD runs (1948->) ----------
uks = sorted(USRECD)
episodes = []
run_start = None
prev = 0
for k in uks:
    v = USRECD[k]
    if v == 1 and prev == 0:
        run_start = k
    if v == 0 and prev == 1:
        episodes.append((run_start, prev_k))
    prev = v; prev_k = k
if prev == 1:
    episodes.append((run_start, uks[-1]))
# clip to grid & label by peak year of window
epi_named = {}
for a, b in episodes:
    if b < GRID_START:
        continue
    aa = max(a, GRID_START)
    epi_named[f"{a.year}-{b.year}" if a.year != b.year else f"{a.year}"] = (aa, b)
# add the non-NBER 2022-24* watch window from index_v1.RECS (flagged separately)
watch_2022 = m.RECS.get("2022-24*")

def severity(line):
    peaks = {}
    for nm, (a, b) in epi_named.items():
        w = [line[i] for i, day in enumerate(DAYS) if a <= day <= b and not np.isnan(line[i])]
        peaks[nm] = round(float(max(w)), 3) if w else None
    if watch_2022:
        a, b = watch_2022
        w = [line[i] for i, day in enumerate(DAYS) if a <= day <= b and not np.isnan(line[i])]
        peaks["2022-24*"] = round(float(max(w)), 3) if w else None
    order = [nm for nm, v in sorted(peaks.items(),
             key=lambda kv: (kv[1] is not None, kv[1]), reverse=True)]
    return peaks, order

peaks_rob, order_rob = severity(line_rob)
peaks_nber, order_nber = severity(line_nber)

# ordering agreement: exact match + Spearman rho + Kendall tau + swapped pairs
common = [nm for nm in peaks_rob if peaks_rob[nm] is not None and peaks_nber[nm] is not None]
def ranks(peaks, names):
    vals = np.array([peaks[n] for n in names], float)
    order = np.argsort(-vals, kind="mergesort")
    r = np.empty(len(names)); r[order] = np.arange(1, len(names) + 1)
    return {names[i]: int(r[i]) for i in range(len(names))}
rr = ranks(peaks_rob, common); rn = ranks(peaks_nber, common)
n = len(common)
def spearman(a, b, names):
    x = np.array([a[nm] for nm in names]); y = np.array([b[nm] for nm in names])
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
swapped = []
for i in range(len(common)):
    for j in range(i + 1, len(common)):
        a, b = common[i], common[j]
        if np.sign(rr[a] - rr[b]) != np.sign(rn[a] - rn[b]):
            swapped.append([a, b])
agreement = {
    "n_episodes_compared": n,
    "order_robust": [nm for nm in order_rob if nm in common],
    "order_nber_excl": [nm for nm in order_nber if nm in common],
    "exact_order_identical": [nm for nm in order_rob if nm in common] ==
                             [nm for nm in order_nber if nm in common],
    "spearman_rho": spearman(rr, rn, common),
    "kendall_tau": kendall(rr, rn, common),
    "swapped_pairs": swapped,
}

# ---------- coverage-tiered agreement (the tier S1 actually adopts) ----------
# thin pre-1948/pre-1973 episodes are driven by a single member; report tiers.
def tier_agreement(subset):
    sub = [nm for nm in order_rob if nm in subset and peaks_rob.get(nm) is not None
           and peaks_nber.get(nm) is not None]
    o_r = [nm for nm in order_rob if nm in sub]
    o_n = [nm for nm in order_nber if nm in sub]
    rr2 = ranks(peaks_rob, sub); rn2 = ranks(peaks_nber, sub)
    sw = []
    for i in range(len(sub)):
        for j in range(i + 1, len(sub)):
            a, b = sub[i], sub[j]
            if np.sign(rr2[a] - rr2[b]) != np.sign(rn2[a] - rn2[b]):
                sw.append([a, b])
    return {"n": len(sub), "order_robust": o_r, "order_nber_excl": o_n,
            "identical": o_r == o_n,
            "spearman_rho": spearman(rr2, rn2, sub) if len(sub) > 1 else None,
            "kendall_tau": kendall(rr2, rn2, sub) if len(sub) > 1 else None,
            "swapped_pairs": sw}


# ---------- coverage per episode (how many channels present at peak) ----------
def episode_coverage():
    cov = {}
    allwin = dict(epi_named)
    if watch_2022:
        allwin["2022-24*"] = watch_2022
    for nm, (a, b) in allwin.items():
        ws = [wsum_rob[i] for i, day in enumerate(DAYS) if a <= day <= b and not np.isnan(wsum_rob[i])]
        cov[nm] = round(float(np.max(ws)), 3) if ws else None
    return cov
epi_cov = episode_coverage()

# tiers by max channel-weight coverage inside the episode window
tier_full = {nm for nm, c in epi_cov.items() if c is not None and c >= 0.99}   # modern, all 5 ch
tier_1948 = {nm for nm, c in epi_cov.items() if c is not None and c >= 0.75}   # 1948-> usable
agreement_tiers = {
    "note": "pre-1973 episodes rest on partial channel coverage (see episode_coverage); "
            "S1 adopts the ordering that is stable where coverage is complete.",
    "full_coverage_wsum_ge_0p99": tier_agreement(tier_full),
    "usable_1948on_wsum_ge_0p75": tier_agreement(tier_1948),
    "all_episodes": {"identical": agreement["exact_order_identical"],
                     "spearman_rho": agreement["spearman_rho"],
                     "kendall_tau": agreement["kendall_tau"],
                     "n": agreement["n_episodes_compared"]},
}

# headline correlation restricted to 1948-> (drops the thin single-member early tail)
mask48 = np.array([d >= dt.date(1948, 1, 1) for d in DAYS])
def line_corr_mask(a, b, mask):
    ok = (~np.isnan(a)) & (~np.isnan(b)) & mask
    return round(float(np.corrcoef(a[ok], b[ok])[0, 1]), 5), int(ok.sum())

# ---------- emit ----------
out = {
    "batch_id": "CH7_BASELINE_FINAL",
    "window": "read-only, §20-class, research/ only",
    "writes_vault": False, "network": False,
    "grid": {"start": GRID_START.isoformat(), "end": END.isoformat(),
             "n_days": NDAYS,
             "note_1948": "grid starts at earliest member transformed obs; "
                          "pre-1948 obs kept (SAHM/UNRATE reach 1948-01). "
                          "coverage thin before members come online (see episode_coverage)."},
    "members": MEMBERS, "n_members": len(MEMBERS),
    "channels": {c: {"weight": CHAN[c][0], "members": CHAN[c][1]} for c in CH_ORDER},
    "baselines": {
        "A_robust": "full-history median / (1.4826*MAD); no labels excluded",
        "B_nber_excl": "mean/std over USRECD==0 days (NBER expansions); "
                       "NO COVID/2022-24 removal",
        "current_for_contrast": "index_v1.is_baseline: NBER-expansion minus "
                                "COVID(2020-21) minus 2022-24(2023..2025-06)",
    },
    "per_member": BASE,
    "headline_corr_robust_vs_nber_fullgrid": line_corr(line_rob, line_nber),
    "headline_corr_robust_vs_nber_1948on": line_corr_mask(line_rob, line_nber, mask48),
    "headline_maxdiv_robust_vs_nber": max_div(line_rob, line_nber),
    "severity_peaks_robust": peaks_rob,
    "severity_peaks_nber_excl": peaks_nber,
    "severity_order_robust": order_rob,
    "severity_order_nber_excl": order_nber,
    "ordering_agreement_all": agreement,
    "ordering_agreement_by_coverage_tier": agreement_tiers,
    "episode_coverage_max_wsum": epi_cov,
}
outjson = REPO + "/research/ch7_baseline_final/scratch/ch7_results.json"
json.dump(out, open(outjson, "w"), indent=1, default=str)

# ---------- CSV (per-member S1 numbers) ----------
csv_path = REPO + "/research/ch7_baseline_final_v1.csv"
cols = ["member", "channel", "first", "last", "n_full", "n_nber_base",
        "robust_mu", "robust_sd", "nber_mu", "nber_sd",
        "d_mu", "d_sd", "mu_shift_in_robust_sd", "sd_ratio_nber_over_robust",
        "cur_mu", "cur_sd"]
mem_chan = {}
for c in CH_ORDER:
    for x in CHAN[c][1]:
        mem_chan[x] = c
lines_csv = [",".join(cols)]
for name in MEMBERS:
    b = BASE[name]
    row = [name, mem_chan[name], b["first"], b["last"], b["n_full"], b["n_nber_base"],
           f'{b["robust_mu"]:.4f}', f'{b["robust_sd"]:.4f}',
           f'{b["nber_mu"]:.4f}', f'{b["nber_sd"]:.4f}',
           f'{b["d_mu"]:.4f}', f'{b["d_sd"]:.4f}',
           f'{b["mu_shift_in_robust_sd"]:.4f}', f'{b["sd_ratio_nber_over_robust"]:.4f}',
           f'{b["cur_mu"]:.4f}', f'{b["cur_sd"]:.4f}']
    lines_csv.append(",".join(str(x) for x in row))
# episode ordering block appended as commented section
lines_csv.append("")
lines_csv.append("# EPISODE,peak_robust,peak_nber_excl,rank_robust,rank_nber_excl,max_wsum_coverage")
rr_all = {nm: i + 1 for i, nm in enumerate(order_rob)}
rn_all = {nm: i + 1 for i, nm in enumerate(order_nber)}
for nm in order_rob:
    lines_csv.append(f'# {nm},{peaks_rob.get(nm)},{peaks_nber.get(nm)},'
                     f'{rr_all.get(nm)},{rn_all.get(nm)},{epi_cov.get(nm)}')
open(csv_path, "w").write("\n".join(lines_csv) + "\n")

print("===CH7 RESULTS WRITTEN===")
print("json:", outjson)
print("csv :", csv_path)
print(json.dumps({
    "grid": out["grid"],
    "headline_corr_fullgrid": out["headline_corr_robust_vs_nber_fullgrid"],
    "headline_corr_1948on": out["headline_corr_robust_vs_nber_1948on"],
    "maxdiv": out["headline_maxdiv_robust_vs_nber"],
    "tier_full_coverage": agreement_tiers["full_coverage_wsum_ge_0p99"],
    "tier_1948on": agreement_tiers["usable_1948on_wsum_ge_0p75"],
    "tier_all": agreement_tiers["all_episodes"],
    "epi_cov": epi_cov,
}, indent=1, default=str))
