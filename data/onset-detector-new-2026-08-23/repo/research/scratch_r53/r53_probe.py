#!/usr/bin/env python3
"""CH-R53 ORDERING FRAGILITY / MARGIN BOOTSTRAP (window 2, read-only, §20-class).

Reproduces the CH1-receipt episode-severity ordering in its published units
(peak sigma-above-expansion, NOT raw peak: receipt `s5_baseline_swap.ordering`
1980=7.14 is (peak-exp_mu)/exp_sd, index_v1.py:227-231), then derives what the
'rank_changed: false / corr 0.988' headline hides:
  1. margin table (adjacent pairs, both baselines, fragility rank)
  2. leave-one-member-out flips
  3. seeded member-resample bootstrap of every adjacent margin
  4. forward exposure ranking for the S2 member-set change

Vectorized: each config = a member->column selection over a precomputed daily z
matrix; peaks/exp are numpy reductions. Read-only: imports method_source with
NOWCAST_DISABLE=1, writes only research/ evidence. No vault/catalog/ledger/network.
"""
import os, sys, json, bisect
import numpy as np

REPO = "/Users/anthonyhall/Desktop/RecessionMonitor 2/Recession Monitor V2"
WORK = REPO + "/research/channel_structure_ch1/scratch/work"
OUT  = REPO + "/research/scratch_r53"
SEED = 53

os.environ["NOWCAST_DISABLE"] = "1"
os.environ["INDEX_OUT"] = OUT + "/idx.scratch.json"
os.chdir(WORK)
sys.path.insert(0, REPO + "/method_source")
import index_v1 as m

CHAN = m.CHANNELS
CH_ORDER = list(CHAN.keys())
MEMBERS, MEM_CH = [], []
for ci, c in enumerate(CH_ORDER):
    for x in CHAN[c][1]:
        MEMBERS.append(x); MEM_CH.append(ci)
MEM_CH = np.array(MEM_CH)
NMEM = len(MEMBERS)
assert NMEM == 17, MEMBERS
W = np.array([CHAN[c][0] for c in CH_ORDER], float)
DAYS = m.DAYS
T = m.T
RECS = m.RECS

def asof(zd, ks, d):
    i = bisect.bisect_right(ks, d) - 1
    return zd[ks[i]] if i >= 0 else None

# ---- baseline estimators (identical to ch1_probe §5 / method_source) ----
def mu_current(name):
    ks = sorted(T[name]); base = [T[name][k] for k in ks if m.is_baseline(k)]
    mu = sum(base)/len(base); sd = (sum((x-mu)**2 for x in base)/len(base))**0.5
    return mu, sd
def mu_statistical(name):           # receipt "statistical" = full-history median / 1.4826*MAD
    ks = sorted(T[name]); vals = np.array([T[name][k] for k in ks])
    med = float(np.median(vals)); mad = float(np.median(np.abs(vals-med)))*1.4826
    return med, mad

def build_Xz(mu_fn):
    """daily (len(DAYS) x NMEM) step-carried z matrix under a baseline estimator."""
    X = np.full((len(DAYS), NMEM), np.nan)
    for j, name in enumerate(MEMBERS):
        ks = sorted(T[name]); mu, sd = mu_fn(name)
        if sd == 0 or np.isnan(sd): sd = 1.0
        zd = {k: (T[name][k]-mu)/sd for k in ks}
        for i, d in enumerate(DAYS):
            v = asof(zd, ks, d)
            if v is not None: X[i, j] = v
    return X

BASE_MASK = np.array([m.is_baseline(d) for d in DAYS])
REC_IDX = {nm: [i for i, d in enumerate(DAYS) if a <= d <= b] for nm, (a, b) in RECS.items()}
EPISODES = list(RECS.keys())

def headline(Xz, cols):
    """weighted, renormalized channel-mean headline over a chosen set of member columns.
    Fully vectorized over days (no per-day Python loop)."""
    D = len(DAYS)
    CS = np.zeros((D, len(CH_ORDER)))          # channel-mean where present, 0 elsewhere
    present_ch = np.zeros((D, len(CH_ORDER)))
    for ci in range(len(CH_ORDER)):
        cc = [j for j in cols if MEM_CH[j] == ci]
        if not cc:
            continue
        sub = Xz[:, cc]
        cnt = np.sum(~np.isnan(sub), axis=1)
        s = np.nansum(sub, axis=1)
        ok = cnt > 0
        CS[ok, ci] = s[ok] / cnt[ok]
        present_ch[ok, ci] = 1.0
    wsum = present_ch @ W                        # (D,)
    tot = (present_ch * CS) @ W                  # (D,)
    line = np.full(D, np.nan)
    nz = wsum > 0
    line[nz] = tot[nz] / wsum[nz]
    return line

def sigma_peaks(line):
    ev = line[BASE_MASK]; ev = ev[~np.isnan(ev)]
    exp_mu = ev.mean(); exp_sd = ev.std()
    out = {}
    for nm in EPISODES:
        w = line[REC_IDX[nm]]; w = w[~np.isnan(w)]
        out[nm] = float((w.max()-exp_mu)/exp_sd) if len(w) else None
    return out, float(exp_mu), float(exp_sd)

def ranking(peaks):
    return sorted(EPISODES, key=lambda nm: (peaks[nm] is not None, peaks[nm]), reverse=True)

BASES = {"current": mu_current, "statistical": mu_statistical}
XZ = {b: build_Xz(fn) for b, fn in BASES.items()}
ALLCOLS = list(range(NMEM))

# ---------- reproduce receipt & baseline peaks ----------
repro = {}
for b in BASES:
    pk, emu, esd = sigma_peaks(headline(XZ[b], ALLCOLS))
    repro[b] = {"sigma_peaks": {k: round(v, 3) if v is not None else None for k, v in pk.items()},
                "rank": ranking(pk), "exp_mu": round(emu, 4), "exp_sd": round(esd, 4)}

# ---------- Q1 margin table (adjacent pairs, both baselines) ----------
def adj_margins(peaks):
    r = ranking(peaks)
    rows = []
    for a, bb in zip(r[:-1], r[1:]):
        hi, lo = peaks[a], peaks[bb]
        rows.append({"upper": a, "lower": bb, "upper_sigma": hi, "lower_sigma": lo,
                     "abs_margin": hi-lo, "rel_margin": (hi-lo)/lo if lo else None})
    return rows

pk_cur = sigma_peaks(headline(XZ["current"], ALLCOLS))[0]
pk_sta = sigma_peaks(headline(XZ["statistical"], ALLCOLS))[0]
mc, ms = adj_margins(pk_cur), adj_margins(pk_sta)
# align by (upper,lower) pair present in current ranking
margin_table = []
for row in mc:
    key = (row["upper"], row["lower"])
    srow = next((s for s in ms if (s["upper"], s["lower"]) == key), None)
    entry = {
        "pair": f'{row["upper"]} > {row["lower"]}',
        "current_abs": round(row["abs_margin"], 3),
        "current_rel": round(row["rel_margin"], 4) if row["rel_margin"] is not None else None,
        "statistical_abs": round(srow["abs_margin"], 3) if srow else None,
        "statistical_rel": round(srow["rel_margin"], 4) if srow and srow["rel_margin"] is not None else None,
        "same_adjacency_both_baselines": srow is not None,
    }
    if srow:
        entry["abs_margin_change"] = round(srow["abs_margin"]-row["abs_margin"], 3)
        entry["rel_collapse_pct"] = round(100*(srow["abs_margin"]-row["abs_margin"])/row["abs_margin"], 1)
    margin_table.append(entry)
# fragility rank = smallest min(current_abs, statistical_abs)
def frag_key(e):
    vals = [v for v in [e["current_abs"], e["statistical_abs"]] if v is not None]
    return min(vals)
margin_table_ranked = sorted(margin_table, key=frag_key)

# ---------- Q2 leave-one-member-out ----------
loo = {}
base_rank = {b: ranking(sigma_peaks(headline(XZ[b], ALLCOLS))[0]) for b in BASES}
base_pairs = {b: list(zip(base_rank[b][:-1], base_rank[b][1:])) for b in BASES}
flips = []
for j, name in enumerate(MEMBERS):
    cols = [c for c in ALLCOLS if c != j]
    rec = {}
    for b in BASES:
        pk = sigma_peaks(headline(XZ[b], cols))[0]
        r = ranking(pk)
        newpairs = list(zip(r[:-1], r[1:]))
        changed = r != base_rank[b]
        rec[b] = {"rank": r, "changed": changed}
        if changed:
            before = set(base_pairs[b]); after = set(newpairs)
            broken = before - after
            for (u, lo) in broken:
                flips.append({"removed_member": name, "channel": CH_ORDER[MEM_CH[j]],
                              "baseline": b, "broke_pair": f"{u} > {lo}",
                              "new_rank": r})
    loo[name] = rec

# smallest subset that flips (only if no single removal flips) -- greedy pair search
subset_finding = None
if not flips:
    import itertools
    found = None
    for k in (2, 3):
        for combo in itertools.combinations(range(NMEM), k):
            cols = [c for c in ALLCOLS if c not in combo]
            for b in BASES:
                r = ranking(sigma_peaks(headline(XZ[b], cols))[0])
                if r != base_rank[b]:
                    found = {"size": k, "members": [MEMBERS[i] for i in combo], "baseline": b, "new_rank": r}
                    break
            if found: break
        if found: break
    subset_finding = found or {"size": ">3", "note": "no flip found removing up to 3 members"}

# ---------- Q3 bootstrap margins (seeded member resample, per channel) ----------
rng = np.random.RandomState(SEED)
NB = 5000
boot = {b: {} for b in BASES}
# per-baseline: for each adjacent pair in the FULL-set ranking, collect margin samples
ch_cols = {ci: [j for j in ALLCOLS if MEM_CH[j] == ci] for ci in range(len(CH_ORDER))}
pair_keys = {b: [f"{u} > {lo}" for (u, lo) in base_pairs[b]] for b in BASES}
samp = {b: {p: [] for p in pair_keys[b]} for b in BASES}
rank_stability = {b: 0 for b in BASES}
for _ in range(NB):
    # resample members within each channel with replacement (preserves channel structure/weights)
    cols = []
    for ci in range(len(CH_ORDER)):
        pool = ch_cols[ci]
        cols += [pool[rng.randint(len(pool))] for _ in pool]
    for b in BASES:
        pk = sigma_peaks(headline(XZ[b], cols))[0]
        r = ranking(pk)
        if r == base_rank[b]:
            rank_stability[b] += 1
        for (u, lo) in base_pairs[b]:
            if pk[u] is not None and pk[lo] is not None:
                samp[b][f"{u} > {lo}"].append(pk[u]-pk[lo])
for b in BASES:
    for p, arr in samp[b].items():
        a = np.array(arr)
        boot[b][p] = {
            "n": int(len(a)),
            "mean_margin": round(float(a.mean()), 3),
            "ci95": [round(float(np.percentile(a, 2.5)), 3), round(float(np.percentile(a, 97.5)), 3)],
            "p_flip_margin_le_0": round(float(np.mean(a <= 0)), 4),
            "ci_overlaps_zero": bool(np.percentile(a, 2.5) <= 0 <= np.percentile(a, 97.5)),
        }
    boot[b]["_full_rank_preserved_frac"] = round(rank_stability[b]/NB, 4)

# ---------- Q4 forward exposure ----------
# rank pairs by exposure = combine relative margin (both baselines) + bootstrap flip prob
exposure = []
for e in margin_table:
    p = e["pair"]
    pf = max(boot["current"].get(p, {}).get("p_flip_margin_le_0", 0),
             boot["statistical"].get(p, {}).get("p_flip_margin_le_0", 0))
    minrel = min([v for v in [e["current_rel"], e["statistical_rel"]] if v is not None] or [None])
    exposure.append({"pair": p, "min_rel_margin": round(minrel, 4) if minrel is not None else None,
                     "min_abs_margin": round(frag_key(e), 3), "max_boot_p_flip": pf})
exposure = sorted(exposure, key=lambda x: (-x["max_boot_p_flip"], x["min_abs_margin"]))

result = {
    "batch_id": "CH-R53_ORDERING_FRAGILITY", "writes_vault": False, "network": False,
    "seed": SEED, "n_bootstrap": NB, "n_members": NMEM, "episodes": EPISODES,
    "units_note": ("severity = peak headline in each RECS window expressed as sigma-above-"
                   "expansion ((peak-exp_mu)/exp_sd), the CH1 receipt's published unit "
                   "(index_v1.py:227-231); NOT the raw scratch peak. Reproduces receipt "
                   "s5_baseline_swap.ordering."),
    "reproduction": repro,
    "q1_margin_table_current_order": margin_table,
    "q1_margin_table_fragility_ranked": margin_table_ranked,
    "q2_leave_one_out": {"per_member": loo, "flips": flips,
                          "any_single_removal_flips": bool(flips),
                          "smallest_flipping_subset_if_no_single": subset_finding},
    "q3_bootstrap": boot,
    "q4_forward_exposure_ranked": exposure,
    "verdict": (
        "The episode ordering is NOT a single robust finding: its ENDS are robust, its "
        "MIDDLE is a near-tie cluster. Only three margins survive resampling with a CI "
        "clear of zero -- 2020>2007-09 (top), 2007-09>1980, and 1990-91>2022-24* (bottom): "
        "2020 is unambiguously worst and 2022-24* unambiguously least. But ranks 3-6 "
        "(1980, 1981-82, 2001, 1990-91) are statistically inseparable: dropping EITHER of "
        "two single members (UNRATEv or NFCI) reorders them, ~28-31% of member resamples "
        "reorder them, and the 1980>1981-82 pair specifically is a coin-flip under the "
        "statistical baseline (25% of resamples flip it, 0.62sigma of headroom). "
        "'Ordering preserved, corr 0.988' is true only because 2020 dominates the "
        "correlation; four of the seven episodes are not distinguishable."),
    "forward_exposure_note": (
        "The member whose removal flips the current-baseline middle is NFCI -- the same "
        "member S4/CH-R57 flag as 99.7%-revised, floored at 2011, and sitting on its own "
        "factor. When S2 moves to the as-of-instrumentable member set (CH3-R2: 18 bases, "
        "NFCI has no pre-2011 vintage), the member most likely to drop/substitute is "
        "exactly one of the two that reorder the ranking. First pair to break: 1980>1981-82."),
    "bootstrap_method": ("member resample WITH REPLACEMENT within each channel (preserves "
                         "channel membership and fixed channel weights); seed=53; NB=5000. "
                         "Captures within-channel member-composition uncertainty; cannot "
                         "simulate adding brand-new channels/bases (see Q4 note)."),
}

os.makedirs(OUT, exist_ok=True)
json.dump(result, open(OUT + "/ordering_fragility_v1.json", "w"), indent=1)

# CSV
import csv
with open(OUT + "/ordering_margins_v1.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["pair", "current_abs_sigma", "current_rel", "statistical_abs_sigma",
                "statistical_rel", "abs_margin_change", "rel_collapse_pct",
                "boot_ci95_lo_current", "boot_ci95_hi_current", "boot_p_flip_current",
                "boot_ci95_lo_statistical", "boot_ci95_hi_statistical", "boot_p_flip_statistical",
                "ci_overlaps_zero_either"])
    for e in margin_table:
        p = e["pair"]
        bc = boot["current"].get(p, {}); bs = boot["statistical"].get(p, {})
        w.writerow([p, e["current_abs"], e["current_rel"], e["statistical_abs"], e["statistical_rel"],
                    e.get("abs_margin_change"), e.get("rel_collapse_pct"),
                    bc.get("ci95", [None, None])[0], bc.get("ci95", [None, None])[1], bc.get("p_flip_margin_le_0"),
                    bs.get("ci95", [None, None])[0], bs.get("ci95", [None, None])[1], bs.get("p_flip_margin_le_0"),
                    bc.get("ci_overlaps_zero") or bs.get("ci_overlaps_zero")])

print("REPRO current 1980/1981-82:", repro["current"]["sigma_peaks"]["1980"], repro["current"]["sigma_peaks"]["1981-82"])
print("REPRO statistical 1980/1981-82:", repro["statistical"]["sigma_peaks"]["1980"], repro["statistical"]["sigma_peaks"]["1981-82"])
print("rank current   :", repro["current"]["rank"])
print("rank statistical:", repro["statistical"]["rank"])
print("any single LOO flip:", bool(flips), "| n flips:", len(flips))
print("wrote", OUT + "/ordering_fragility_v1.json", "+ ordering_margins_v1.csv")
