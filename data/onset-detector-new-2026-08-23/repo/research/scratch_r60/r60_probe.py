#!/usr/bin/env python3
"""CH-R60 RANKABILITY, TIES, RANK CONFIDENCE SETS (window 4, read-only, §20-class).

Consumes CH-R53's reproduction harness (same z-matrix, same member-resample
bootstrap seed) and extends it from ADJACENT-pair margins to the FULL rank
confidence problem per the batch's four method sources:

  * Goldstein-Spiegelhalter (1996)  -> overlap intervals / intervals on ranks
  * Mogstad-Romano-Shaikh-Wilhelm   -> simultaneous pairwise-difference CIs,
                                       inverted to simultaneous rank sets + tau-best
  * Al Mohamad et al. (2022)         -> rankability = fraction of separable pairs
  * Hall-Miller (2009) WARNING       -> the n-out-of-n bootstrap is INCONSISTENT for
                                       the RANK operator. RESOLUTION: we never bootstrap
                                       a rank. We bootstrap DIFFERENCES (consistent) and
                                       INVERT to rank bounds (Mogstad's device). An
                                       m-out-of-n subsample is run ONLY as a labeled
                                       sensitivity, m chosen by their sqrt rule.

Info-set modes: `current_revised` is computed directly (both CH1 baseline variants,
'current' and 'statistical'). A real-time PROXY drops NFCI -- the whole finconditions
channel, which has no pre-2011 vintage (S4/CH-R57) so is unreachable in an as-of
replay (CH-R28). A true archive_snapshot_asof rankability is NOT computable here (no
vintage lanes); that unavailability is itself reported.

Read-only: imports method_source with NOWCAST_DISABLE=1, writes only research/.
"""
import os, sys, bisect, json, csv, itertools
import numpy as np

REPO = "/Users/anthonyhall/Desktop/RecessionMonitor 2/Recession Monitor V2"
WORK = REPO + "/research/channel_structure_ch1/scratch/work"
OUT  = REPO + "/research/scratch_r60"
SEED = 60
NB   = 2500

os.environ["NOWCAST_DISABLE"] = "1"
os.environ["INDEX_OUT"] = OUT + "/idx.scratch.json"
os.makedirs(OUT, exist_ok=True)
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
W = np.array([CHAN[c][0] for c in CH_ORDER], float)
DAYS = m.DAYS
T = m.T
RECS = m.RECS
EPISODES = list(RECS.keys())
NE = len(EPISODES)

def asof(zd, ks, d):
    i = bisect.bisect_right(ks, d) - 1
    return zd[ks[i]] if i >= 0 else None

def mu_current(name):
    ks = sorted(T[name]); base = [T[name][k] for k in ks if m.is_baseline(k)]
    mu = sum(base)/len(base); sd = (sum((x-mu)**2 for x in base)/len(base))**0.5
    return mu, sd
def mu_statistical(name):
    ks = sorted(T[name]); vals = np.array([T[name][k] for k in ks])
    med = float(np.median(vals)); mad = float(np.median(np.abs(vals-med)))*1.4826
    return med, mad

def build_Xz(mu_fn):
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

def headline(Xz, cols):
    D = len(DAYS)
    CS = np.zeros((D, len(CH_ORDER))); present = np.zeros((D, len(CH_ORDER)))
    for ci in range(len(CH_ORDER)):
        cc = [j for j in cols if MEM_CH[j] == ci]
        if not cc: continue
        sub = Xz[:, cc]; cnt = np.sum(~np.isnan(sub), axis=1); s = np.nansum(sub, axis=1)
        ok = cnt > 0
        CS[ok, ci] = s[ok]/cnt[ok]; present[ok, ci] = 1.0
    wsum = present @ W; tot = (present*CS) @ W
    line = np.full(D, np.nan); nz = wsum > 0; line[nz] = tot[nz]/wsum[nz]
    return line

def sigma_vec(line):
    ev = line[BASE_MASK]; ev = ev[~np.isnan(ev)]
    emu, esd = ev.mean(), ev.std()
    out = np.full(NE, np.nan)
    for k, nm in enumerate(EPISODES):
        w = line[REC_IDX[nm]]; w = w[~np.isnan(w)]
        if len(w): out[k] = (w.max()-emu)/esd
    return out

BASES = {"current": mu_current, "statistical": mu_statistical}
XZ = {b: build_Xz(fn) for b, fn in BASES.items()}
ALLCOLS = list(range(NMEM))
ch_cols = {ci: [j for j in ALLCOLS if MEM_CH[j] == ci] for ci in range(len(CH_ORDER))}

def rank_of(sv):
    # rank 1 = most severe (largest sigma). higher sigma -> lower rank number.
    order = np.argsort(-sv)
    r = np.empty(NE, int)
    for pos, idx in enumerate(order): r[idx] = pos+1
    return r

PAIRS = list(itertools.combinations(range(NE), 2))  # 21 unordered pairs

def analyse(cols_full, drop_members=()):
    """Full Mogstad/AlMohamad/Hall-Miller analysis for a member column set."""
    keep = [c for c in cols_full if MEMBERS[c] not in drop_members]
    res = {}
    for b in BASES:
        s_hat = sigma_vec(headline(XZ[b], keep))
        # ---- member-resample bootstrap on the SEVERITY VECTOR (n-out-of-n within channel).
        # Consistent for DIFFERENCES; used only to form difference CIs, never a rank.
        rng = np.random.RandomState(SEED)
        boot = np.full((NB, NE), np.nan)
        present_ch = set(MEM_CH[c] for c in keep)
        for bi in range(NB):
            cols = []
            for ci in range(len(CH_ORDER)):
                pool = [c for c in ch_cols[ci] if c in keep]
                if not pool: continue
                cols += [pool[rng.randint(len(pool))] for _ in pool]
            boot[bi] = sigma_vec(headline(XZ[b], cols))
        # difference matrix stats
        diff_hat = s_hat[:, None] - s_hat[None, :]          # (NE,NE) i-j
        diff_boot = boot[:, :, None] - boot[:, None, :]     # (NB,NE,NE)
        se = np.nanstd(diff_boot, axis=0)                   # (NE,NE)
        se_safe = np.where(se > 0, se, np.nan)
        # studentized draws for max-t simultaneous critical value (over the 21 pairs).
        # Vectorized over the upper-triangular valid pairs.
        pmask = np.zeros((NE, NE), bool)
        for (i, j) in PAIRS:
            if not np.isnan(se_safe[i, j]): pmask[i, j] = True
        t_all = np.abs((diff_boot - diff_hat[None]) / se_safe[None])  # (NB,NE,NE)
        t_all = np.where(pmask[None], t_all, -np.inf)
        tmax = t_all.reshape(NB, -1).max(axis=1)
        c_sim = float(np.percentile(tmax, 95))              # studentized max-t crit (reported only)

        # ---- separability by PERCENTILE bootstrap (skew-robust). ----
        # The 2020 severity margin is severely right-skewed (COVID 52sigma): studentizing by
        # a bootstrap sd inflated by the favorable upper tail collapses the studentized stat
        # and FALSELY calls 2020's 41-51sigma gaps non-separable. The percentile flip
        # probability is the honest statistic (matches CH-R53's percentile CIs).
        #   pf[i,j] oriented toward the point winner = P(bootstrap margin <= 0).
        pf = {}                     # keyed (winner_idx, loser_idx) -> flip prob
        for (i, j) in PAIRS:
            d = diff_hat[i, j]
            hi, lo = (i, j) if d >= 0 else (j, i)
            ms = diff_boot[:, hi, lo]
            pf[(hi, lo)] = float(np.mean(ms <= 0))
        # marginal 95%: pf < 0.025 ; simultaneous: Holm step-down FWER=0.05 over 21 pairs
        K = len(PAIRS)
        ordered = sorted(pf.items(), key=lambda kv: kv[1])   # ascending flip prob
        holm_reject = {}
        passed_all = True
        for r, ((hi, lo), p) in enumerate(ordered, start=1):
            thr = 0.05 / (K - r + 1)
            if passed_all and p <= thr:
                holm_reject[(hi, lo)] = True
            else:
                passed_all = False
                holm_reject[(hi, lo)] = False
        marg_sep = {k: (v < 0.025) for k, v in pf.items()}   # (hi,lo)->bool
        pctl = {k: (float(np.percentile(diff_boot[:, k[0], k[1]], 2.5)),
                    float(np.percentile(diff_boot[:, k[0], k[1]], 97.5))) for k in pf}

        pair_rows = []
        sep_marg = sep_sim = 0
        for (hi, lo), p in pf.items():
            ms = bool(marg_sep[(hi, lo)]); ss = bool(holm_reject[(hi, lo)])
            if ms: sep_marg += 1
            if ss: sep_sim += 1
            pair_rows.append({
                "hi": EPISODES[hi], "lo": EPISODES[lo],
                "abs_diff_sigma": round(float(abs(diff_hat[hi, lo])), 3),
                "se_boot": round(float(se[hi, lo]), 3) if not np.isnan(se[hi, lo]) else None,
                "flip_prob": round(p, 4),
                "margin_ci95_pctile": [round(pctl[(hi, lo)][0], 3), round(pctl[(hi, lo)][1], 3)],
                "studentized_t": round(float(abs(diff_hat[hi, lo])/se[hi, lo]), 3) if se[hi, lo] > 0 else None,
                "separable_marginal": ms,
                "separable_simultaneous_holm": ss,
            })
        npair = len(PAIRS)
        # ---- Mogstad simultaneous rank sets (invert the simultaneous separability) ----
        # winner is MORE severe. i's rank bounds from how many are sim-sep more/less severe.
        rank_sets = {}
        for i in range(NE):
            n_sig_above = 0; n_sig_below = 0
            for j in range(NE):
                if i == j: continue
                key = (i, j) if diff_hat[i, j] >= 0 else (j, i)
                if not holm_reject.get(key, False): continue   # not sim-separable
                if diff_hat[i, j] < 0: n_sig_above += 1         # j more severe
                else:                   n_sig_below += 1         # j less severe
            rank_sets[EPISODES[i]] = {"point_rank": int(rank_of(s_hat)[i]),
                                       "rank_lower": int(1 + n_sig_above),
                                       "rank_upper": int(NE - n_sig_below),
                                       "n_sig_more_severe": n_sig_above,
                                       "n_sig_less_severe": n_sig_below}
        TAU = 3
        tau_best = [e for e in EPISODES if rank_sets[e]["rank_lower"] <= TAU]

        # ---- tie groups: connected components under NOT sim-separable (single-linkage; ----
        # NB single-linkage chains transitively -- reported with that caveat, rank sets are
        # the primary tie evidence.)
        adj = {i: set() for i in range(NE)}
        for (i, j) in PAIRS:
            key = (i, j) if diff_hat[i, j] >= 0 else (j, i)
            if not holm_reject.get(key, False):
                adj[i].add(j); adj[j].add(i)
        seen = set(); groups = []
        for i in range(NE):
            if i in seen: continue
            stack=[i]; comp=set()
            while stack:
                x=stack.pop()
                if x in seen: continue
                seen.add(x); comp.add(x); stack += [y for y in adj[x] if y not in seen]
            groups.append(sorted(comp, key=lambda k: -s_hat[k]))
        # order groups by max severity
        groups = sorted(groups, key=lambda g: -max(s_hat[k] for k in g))
        tie_groups = [[EPISODES[k] for k in g] for g in groups]

        # ---- Hall-Miller m-out-of-n subsample SENSITIVITY on the rank (labeled) ----
        # m chosen by sqrt rule: m = round(2*sqrt(n_members_kept)); keep >=1 member/channel.
        nkept = len(keep)
        m_sub = min(nkept, max(len(present_ch), int(round(2*np.sqrt(nkept)))))
        rng2 = np.random.RandomState(SEED+1)
        rankfreq = {e: np.zeros(NE+1) for e in EPISODES}  # index 1..NE
        NSUB = 1000
        keep_by_ch = {ci: [c for c in ch_cols[ci] if c in keep] for ci in range(len(CH_ORDER))}
        nonempty = [ci for ci in keep_by_ch if keep_by_ch[ci]]
        for _ in range(NSUB):
            # take 1 guaranteed per channel, then fill remaining up to m_sub from the pool w/o replacement
            chosen = [keep_by_ch[ci][rng2.randint(len(keep_by_ch[ci]))] for ci in nonempty]
            remaining = [c for c in keep if c not in chosen]
            extra = max(0, m_sub - len(chosen))
            if extra and remaining:
                idx = rng2.choice(len(remaining), size=min(extra, len(remaining)), replace=False)
                chosen += [remaining[k] for k in idx]
            sv = sigma_vec(headline(XZ[b], chosen))
            rk = rank_of(sv)
            for k, e in enumerate(EPISODES): rankfreq[e][rk[k]] += 1
        hm = {e: {"m_out_of_n": int(m_sub), "n": nkept,
                  "modal_rank": int(np.argmax(rankfreq[e][1:])+1),
                  "rank_dist": [round(float(x/NSUB), 3) for x in rankfreq[e][1:]]}
              for e in EPISODES}

        res[b] = {
            "sigma_peaks": {EPISODES[k]: round(float(s_hat[k]), 3) for k in range(NE)},
            "point_ranking": [EPISODES[k] for k in np.argsort(-s_hat)],
            "sim_crit_value_maxt": round(c_sim, 3),
            "n_pairs": npair,
            "rankability_marginal": round(sep_marg/npair, 3),
            "rankability_simultaneous": round(sep_sim/npair, 3),
            "n_separable_marginal": sep_marg,
            "n_separable_simultaneous": sep_sim,
            "pairs": pair_rows,
            "rank_sets_simultaneous": rank_sets,
            "tau_best_tau3": tau_best,
            "tie_groups_simultaneous": tie_groups,
            "hall_miller_mofn_rank_sensitivity": hm,
        }
    return res

# ---- current_revised (full 17 members) ----
full = analyse(ALLCOLS)
# ---- real-time PROXY: drop NFCI (whole finconditions channel; no pre-2011 vintage) ----
proxy = analyse(ALLCOLS, drop_members=("NFCI",))

result = {
    "batch_id": "CH-R60_RANKABILITY_AND_TIES",
    "writes_vault": False, "network": False, "seed": SEED,
    "n_bootstrap_diff": NB, "n_subsample_hallmiller": 1000,
    "n_members": NMEM, "n_episodes": NE, "episodes": EPISODES,
    "pairs_total": len(PAIRS),
    "units_note": ("severity = peak headline per RECS window in sigma-above-expansion "
                   "((peak-exp_mu)/exp_sd), CH1 receipt unit (index_v1.py:227-231). "
                   "Same estimator/harness as CH-R53; extends adjacent-pair margins to "
                   "all 21 pairs + rank confidence sets."),
    "method": {
        "difference_bootstrap": ("member resample WITH REPLACEMENT within channel, seed=60, "
                                 "NB=2500 -- consistent for pairwise DIFFERENCES (Hall-Miller: a "
                                 "difference is a smooth functional; only the RANK operator is "
                                 "the inconsistent case, and it is never bootstrapped here)."),
        "separability_stat": ("PERCENTILE flip probability oriented toward the point winner "
                              "P(bootstrap margin<=0), NOT a studentized t. Rationale: the 2020 "
                              "COVID margin is severely right-skewed (52sigma), so a studentized "
                              "max-t divides by a bootstrap sd inflated by the favorable upper "
                              "tail and FALSELY calls 2020's 41-51sigma gaps non-separable. The "
                              "max-t critical value is still computed and reported (sim_crit_value_"
                              "maxt) but is NOT used for the separability decision."),
        "simultaneous_ci": ("family-wise control over the 21 pairs via Holm step-down on the "
                            "percentile flip probabilities (FWER=0.05); Goldstein-Spiegelhalter "
                            "overlap-interval logic. Simultaneous rank sets (Mogstad-Romano-"
                            "Shaikh-Wilhelm) obtained by INVERTING the simultaneous pairwise "
                            "separability -- rank_lower=1+#(sim-more-severe), rank_upper=NE-#(sim-"
                            "less-severe). The rank operator itself is never bootstrapped."),
        "hall_miller_note": ("Hall-Miller (2009): n-out-of-n bootstrap is INCONSISTENT for the "
                             "rank statistic, so the primary rank sets use difference-inversion "
                             "(no rank is ever bootstrapped). An m-out-of-n subsample (m=round("
                             "2*sqrt(kept members)), >=1/channel, no replacement) is reported "
                             "ONLY as a labeled sensitivity."),
        "rankability_def": ("Al Mohamad et al. (2022): fraction of the 21 episode pairs whose "
                            "severity difference is statistically separable. Reported both "
                            "marginal (per-pair 95%) and simultaneous (family-wise 95%)."),
        "info_set_modes": ("current_revised computed directly under both CH1 baseline variants. "
                           "archive_snapshot_asof is NOT directly computable (no member vintage "
                           "lanes pre-2011; CH-R28 blocker). Real-time PROXY = drop NFCI (sole "
                           "finconditions member, no pre-2011 vintage: S4/CH-R57)."),
    },
    "current_revised": full,
    "realtime_proxy_drop_NFCI": proxy,
}
json.dump(result, open(OUT+"/rankability_v1.json", "w"), indent=1)

# ---- CSV: one row per (mode, baseline, pair) ----
with open(OUT+"/rank_confidence_sets_v1.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["mode","baseline","hi_episode","lo_episode","abs_diff_sigma","se_boot",
                "flip_prob","margin_ci95_lo","margin_ci95_hi","studentized_t",
                "separable_marginal","separable_simultaneous_holm"])
    for mode, blob in (("current_revised", full), ("realtime_proxy_drop_NFCI", proxy)):
        for b in BASES:
            for pr in blob[b]["pairs"]:
                cm = pr["margin_ci95_pctile"] or [None,None]
                w.writerow([mode,b,pr["hi"],pr["lo"],pr["abs_diff_sigma"],pr["se_boot"],
                            pr["flip_prob"],cm[0],cm[1],pr["studentized_t"],
                            pr["separable_marginal"],pr["separable_simultaneous_holm"]])

# console summary
for mode, blob in (("current_revised", full), ("realtime_proxy_drop_NFCI", proxy)):
    for b in BASES:
        r = blob[b]
        print(f"[{mode}/{b}] rankability marg={r['rankability_marginal']} sim={r['rankability_simultaneous']} "
              f"({r['n_separable_simultaneous']}/{r['n_pairs']} sim)  tau3={r['tau_best_tau3']}")
        print("   tie groups:", r["tie_groups_simultaneous"])
print("wrote", OUT+"/rankability_v1.json + rank_confidence_sets_v1.csv")
