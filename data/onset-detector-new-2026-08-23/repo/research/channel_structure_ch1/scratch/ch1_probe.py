#!/usr/bin/env python3
"""PROBE CH1 — channel structure on TRANSFORMED signed-deterioration z-values.
Read-only. Imports method_source/index_v1.py (NOWCAST_DISABLE=1) and measures the
transformed daily z exactly as channel_score() receives them. Writes nothing to the
vault; emits JSON evidence to stdout for the receipt builder. Section numbers follow
the probe brief."""
import os, sys, json, datetime as dt, bisect
import numpy as np

REPO = "/Users/anthonyhall/Desktop/RecessionMonitor 2/Recession Monitor V2"
MSRC = REPO + "/method_source"
WORK = REPO + "/research/channel_structure_ch1/scratch/work"

os.environ["NOWCAST_DISABLE"] = "1"                 # pure carry-forward transformed history
os.environ["INDEX_OUT"] = WORK + "/index_v1_out.scratch.json"
os.chdir(WORK)                                       # raw/ symlink -> current_revised_and_spatial
sys.path.insert(0, MSRC)
import index_v1 as m                                 # runs module build (prints AUROC etc.)

# ---------- shared handles ----------
CHAN = m.CHANNELS                                     # ordered dict: name -> (w, [members])
CH_ORDER = list(CHAN.keys())
MEMBERS = []
for c in CH_ORDER:
    MEMBERS += CHAN[c][1]
assert len(MEMBERS) == 17, MEMBERS
DAYS = m.DAYS
START, END = m.START, m.END

def asof(zdict, keys, d):
    i = bisect.bisect_right(keys, d) - 1
    return zdict[keys[i]] if i >= 0 else None

# transformed native series T[name]; z series Z[name]=(zdict, keys)
T = m.T
Z = {name: (Z0, ks) for name, (Z0, ks) in m.Z.items()}

# ---------- §0.1 transformed span + non-null count per member ----------
span = {}
for name in MEMBERS:
    ks = sorted(T[name])
    span[name] = {"first": ks[0].isoformat(), "last": ks[-1].isoformat(),
                  "n_transformed_obs": len(ks)}

# ---------- §0.2 single sample window: full daily grid START..END, pairwise-complete ----------
WINDOW = {"start": START.isoformat(), "end": END.isoformat(), "n_days": len(DAYS),
          "rule": "daily asof step-carried z exactly as channel_score/zval receives; "
                  "pairwise-complete deletion; NaN before a member's first transformed obs",
          "excludes": "pre-1976-06-01 obs of members that start earlier; edge nowcast fills "
                      "(NOWCAST_DISABLE=1, so none present)"}

# daily matrix of transformed z, exactly as channel_score sees them
Xz = np.full((len(DAYS), len(MEMBERS)), np.nan)
for j, name in enumerate(MEMBERS):
    zd, ks = Z[name]
    for i, d in enumerate(DAYS):
        v = asof(zd, ks, d)
        if v is not None:
            Xz[i, j] = v
nn_daily = {name: int(np.sum(~np.isnan(Xz[:, j]))) for j, name in enumerate(MEMBERS)}

# ---------- helpers ----------
def pear(a, b):
    ok = ~np.isnan(a) & ~np.isnan(b)
    if ok.sum() < 3: return None, int(ok.sum())
    aa, bb = a[ok], b[ok]
    if aa.std() == 0 or bb.std() == 0: return None, int(ok.sum())
    return float(np.corrcoef(aa, bb)[0, 1]), int(ok.sum())

def rankdata(v):
    # average ranks, ties handled
    order = np.argsort(v, kind="mergesort")
    r = np.empty(len(v)); r[order] = np.arange(1, len(v)+1)
    # tie averaging
    sv = v[order]
    i = 0
    while i < len(sv):
        j = i
        while j+1 < len(sv) and sv[j+1] == sv[i]:
            j += 1
        if j > i:
            r[order[i:j+1]] = (i+1 + j+1)/2.0
        i = j+1
    return r

def spear(a, b):
    ok = ~np.isnan(a) & ~np.isnan(b)
    if ok.sum() < 3: return None, int(ok.sum())
    ra, rb = rankdata(a[ok]), rankdata(b[ok])
    if ra.std() == 0 or rb.std() == 0: return None, int(ok.sum())
    return float(np.corrcoef(ra, rb)[0, 1]), int(ok.sum())

# ---------- §1.1 full 17x17 Pearson (transformed) ----------
P = np.full((17, 17), np.nan)
for i in range(17):
    for j in range(17):
        if i == j: P[i, j] = 1.0
        elif j > i:
            r, n = pear(Xz[:, i], Xz[:, j]); P[i, j] = P[j, i] = (r if r is not None else np.nan)
pearson_matrix = {MEMBERS[i]: {MEMBERS[j]: (None if np.isnan(P[i, j]) else round(float(P[i, j]), 3))
                               for j in range(17)} for i in range(17)}

# ---------- §1.2 five named pairs: raw-level vs transformed, side by side ----------
def raw_daily(seriesdict):
    ks = sorted(seriesdict); arr = np.full(len(DAYS), np.nan)
    for i, d in enumerate(DAYS):
        k = bisect.bisect_right(ks, d) - 1
        if k >= 0: arr[i] = seriesdict[ks[k]]
    return arr
raw_series = {
    "INDPRO": raw_daily(m.S["INDPRO"]), "CMRMT": raw_daily(m.S["CMRMTSPL"]),
    "PERMIT": raw_daily(m.S["PERMIT"]), "HOUST": raw_daily(m.S["HOUST"]),
    "BAA10Y": raw_daily(m.S["BAA10Y"]), "BAAAAA": raw_daily(m.BAAAAA),
    "SAHM": raw_daily(m.S["SAHMREALTIME"]), "UNRATE": raw_daily(m.S["UNRATE"]),
    "IURSA": raw_daily(m.S["IURSA"]),
}
mi = {name: MEMBERS.index(name) for name in MEMBERS}
named_pairs = [
    ("INDPRO", "CMRMT", "INDPRO", "CMRMT", 0.967),
    ("PERMIT", "HOUST", "PERMIT", "HOUST", 0.953),
    ("BAA10Y", "BAAAAA", "BAA10Y", "BAAAAA", 0.810),
    ("SAHM", "UNRATEv", "SAHM", "UNRATE", 0.504),
    ("IURSA", "UNRATEv", "IURSA", "UNRATE", None),
]
pair_report = []
for a_t, b_t, a_r, b_r, chat_raw in named_pairs:
    rr, nr = pear(raw_series[a_r], raw_series[b_r])
    tr, nt = pear(Xz[:, mi[a_t]], Xz[:, mi[b_t]])
    sp, ns = spear(Xz[:, mi[a_t]], Xz[:, mi[b_t]])
    delta = None if (rr is None or tr is None) else round(tr - rr, 3)
    pair_report.append({
        "pair": f"{a_t}~{b_t}",
        "raw_level_r_probe": None if rr is None else round(rr, 3), "raw_n": nr,
        "raw_level_r_chatside": chat_raw,
        "transformed_r": None if tr is None else round(tr, 3), "transformed_n": nt,
        "spearman_r": None if sp is None else round(sp, 3),
        "change_transformed_minus_rawprobe": delta,
        "direction": ("n/a" if delta is None else ("falls" if delta < 0 else "rises")),
        "collinear_flag_ge_0p80": (tr is not None and abs(tr) >= 0.80),
    })

# ---------- §1.4 all transformed pairs |r|>=0.80 ----------
collinear = []
for i in range(17):
    for j in range(i+1, 17):
        if not np.isnan(P[i, j]) and abs(P[i, j]) >= 0.80:
            collinear.append({"a": MEMBERS[i], "b": MEMBERS[j], "r": round(float(P[i, j]), 3)})
collinear.sort(key=lambda x: -abs(x["r"]))

# ---------- §1.3 Spearman for all pairs (report full) ----------
spearman_named = {p["pair"]: p["spearman_r"] for p in pair_report}

# ---------- §2 effective independent members per channel ----------
def eff_n(members):
    idx = [MEMBERS.index(x) for x in members]
    k = len(idx)
    if k == 1: return 1.0, [1.0]
    C = np.eye(k)
    for a in range(k):
        for b in range(a+1, k):
            r, n = pear(Xz[:, idx[a]], Xz[:, idx[b]])
            C[a, b] = C[b, a] = (0.0 if r is None else r)
    ev = np.linalg.eigvalsh(C)
    ev = np.clip(ev, 0, None)
    pr = (ev.sum()**2) / (np.sum(ev**2))     # participation ratio
    return float(pr), [round(float(x), 3) for x in sorted(ev, reverse=True)]
effN = {}
for c in CH_ORDER:
    w, members = CHAN[c]
    pr, ev = eff_n(members)
    effN[c] = {"nominal_n": len(members), "eff_n": round(pr, 2), "eigenvalues": ev, "weight": w}
# §2.3 NFCI first non-null
nfci_ks = sorted(T["NFCI"])
nfci_first = nfci_ks[0].isoformat()

# ---------- build channel-score daily series (current baseline) ----------
def chan_scores_current():
    CS = np.full((len(DAYS), len(CH_ORDER)), np.nan)
    for ci, c in enumerate(CH_ORDER):
        members = CHAN[c][1]
        idx = [MEMBERS.index(x) for x in members]
        sub = Xz[:, idx]
        for i in range(len(DAYS)):
            row = sub[i][~np.isnan(sub[i])]
            if len(row): CS[i, ci] = row.mean()
    return CS
CS = chan_scores_current()
W = np.array([CHAN[c][0] for c in CH_ORDER])

# headline current (renormalized) — matches module
def headline_from_CS(CS, renorm=True):
    line = np.full(len(DAYS), np.nan)
    for i in range(len(DAYS)):
        present = ~np.isnan(CS[i])
        if not present.any(): continue
        wsum = W[present].sum()
        tot = np.sum(W[present] * CS[i][present])
        line[i] = tot / wsum if renorm else tot / W.sum()
    return line
line_cur = headline_from_CS(CS, renorm=True)

# ---------- §3 variance contribution per channel (full-coverage days) ----------
full_cov = ~np.isnan(CS).any(axis=1)     # all five channels present
labels = np.array([1 if m.in_recession(DAYS[i]) else 0 for i in range(len(DAYS))])
def var_decomp(mask):
    idx = np.where(mask)[0]
    if len(idx) < 30: return None
    comp = CS[idx] * W                    # weighted contributions, wsum=1 on full cov
    H = comp.sum(axis=1)
    varH = H.var()
    shares = {}
    for ci, c in enumerate(CH_ORDER):
        cov = np.mean((comp[:, ci]-comp[:, ci].mean())*(H-H.mean()))
        shares[c] = round(float(cov/varH), 3)
    return {"n_days": int(len(idx)), "shares": shares}
vd_all = var_decomp(full_cov)
vd_rec = var_decomp(full_cov & (labels == 1))
vd_exp = var_decomp(full_cov & (labels == 0))
nominal_w = {c: CHAN[c][0] for c in CH_ORDER}
gaps = {c: round(vd_all["shares"][c]-nominal_w[c], 3) for c in CH_ORDER}

# §3.4 equal-variance-contribution (ERC) weight vector over channel scores (full-cov)
idx = np.where(full_cov)[0]
Sig = np.cov(CS[idx].T)
def erc_weights(Sig, iters=20000, lr=0.01):
    n = Sig.shape[0]; w = np.ones(n)/n
    for _ in range(iters):
        mrc = Sig @ w
        rc = w * mrc
        target = rc.mean()
        grad = (rc - target)
        w = w - lr*grad/ (np.abs(mrc)+1e-9)
        w = np.clip(w, 1e-6, None); w = w/w.sum()
    return w
erc = erc_weights(Sig)
erc_vec = {c: round(float(erc[ci]), 3) for ci, c in enumerate(CH_ORDER)}

# ---------- §4 lead/lag per channel per episode (NBER onset = external_comparator) ----------
urd = m.S["USRECD"]; uks = sorted(urd)
onsets = []
prev = 0
for k in uks:
    if urd[k] == 1 and prev == 0 and k >= START:
        onsets.append(k)
    prev = urd[k]
# label episodes by year
onset_named = {k.isoformat(): k for k in onsets}
# channel score full-history 80th percentile threshold; first crossing in [-24mo,+6mo] window
lead_pct = 80
ch_thresh = {}
for ci, c in enumerate(CH_ORDER):
    v = CS[:, ci][~np.isnan(CS[:, ci])]
    ch_thresh[c] = float(np.nanpercentile(v, lead_pct))
lead_report = {}
for on in onsets:
    row = {}
    w0 = on - dt.timedelta(days=730); w1 = on + dt.timedelta(days=183)
    for ci, c in enumerate(CH_ORDER):
        cross = None
        for i, d in enumerate(DAYS):
            if d < w0 or d > w1: continue
            if not np.isnan(CS[i, ci]) and CS[i, ci] >= ch_thresh[c]:
                cross = d; break
        row[c] = None if cross is None else (on - cross).days   # +=lead
    lead_report[on.isoformat()] = row
lead_stats = {}
for c in CH_ORDER:
    vals = [lead_report[o][c] for o in lead_report if lead_report[o][c] is not None]
    if vals:
        arr = np.array(vals)
        lead_stats[c] = {"n_episodes": len(vals), "median_lead_days": int(np.median(arr)),
                          "iqr_days": int(np.percentile(arr, 75)-np.percentile(arr, 25)),
                          "min": int(arr.min()), "max": int(arr.max())}
    else:
        lead_stats[c] = {"n_episodes": 0}
reachable = [o.isoformat() for o in onsets]
unreachable = {"1973-75": "NBER onset before 1976-06 window start",
               "2022-24*": "no NBER recession day (USRECD never 1); no NBER onset to reference"}

# ---------- §5 baseline swap ----------
def rebuild_Z(mu_fn):
    Zalt = {}
    for name in MEMBERS + ["NFCI"]:
        ks = sorted(T[name]); vals = np.array([T[name][k] for k in ks])
        mu, sd = mu_fn(name, ks, vals)
        if sd == 0 or np.isnan(sd): sd = 1.0
        zd = {k: (T[name][k]-mu)/sd for k in ks}
        Zalt[name] = (zd, ks, mu, sd)
    return Zalt
def mu_current(name, ks, vals):
    base = [T[name][k] for k in ks if m.is_baseline(k)]
    mu = sum(base)/len(base); sd = (sum((x-mu)**2 for x in base)/len(base))**0.5
    return mu, sd
def mu_stat_mean(name, ks, vals):
    return float(vals.mean()), float(vals.std())
def mu_stat_median(name, ks, vals):
    med = float(np.median(vals)); mad = float(np.median(np.abs(vals-med)))*1.4826
    return med, mad
Z_variants = {"current": rebuild_Z(mu_current),
              "stat_mean": rebuild_Z(mu_stat_mean),
              "stat_median_mad": rebuild_Z(mu_stat_median)}

def build_line(Zalt, renorm=True):
    Xa = np.full((len(DAYS), len(MEMBERS)), np.nan)
    for j, name in enumerate(MEMBERS):
        zd, ks = Zalt[name][0], Zalt[name][1]
        for i, d in enumerate(DAYS):
            v = asof(zd, ks, d)
            if v is not None: Xa[i, j] = v
    CSa = np.full((len(DAYS), len(CH_ORDER)), np.nan)
    for ci, c in enumerate(CH_ORDER):
        idx2 = [MEMBERS.index(x) for x in CHAN[c][1]]
        sub = Xa[:, idx2]
        for i in range(len(DAYS)):
            row = sub[i][~np.isnan(sub[i])]
            if len(row): CSa[i, ci] = row.mean()
    return headline_from_CS(CSa, renorm=renorm), CSa
lines = {}
musd = {}
for k, Zalt in Z_variants.items():
    ln, _ = build_line(Zalt, renorm=True)
    lines[k] = ln
    musd[k] = {name: {"mu": round(Zalt[name][2], 4), "sd": round(Zalt[name][3], 4)} for name in MEMBERS}

def line_corr(a, b):
    ok = ~np.isnan(a) & ~np.isnan(b)
    return float(np.corrcoef(a[ok], b[ok])[0, 1]), int(ok.sum())
def max_div(a, b):
    ok = ~np.isnan(a) & ~np.isnan(b)
    d = np.abs(a-b); d[~ok] = -1
    i = int(np.argmax(d))
    return round(float(d[i]), 4), DAYS[i].isoformat()

# per-member mu/sd change current->stat
musd_change = {}
for name in MEMBERS:
    cu = musd["current"][name]; sm = musd["stat_mean"][name]; md = musd["stat_median_mad"][name]
    musd_change[name] = {"current": cu, "stat_mean": sm, "stat_median_mad": md,
                         "d_mu_mean": round(sm["mu"]-cu["mu"], 4), "d_sd_mean": round(sm["sd"]-cu["sd"], 4)}

# severity ordering under each baseline (peak headline in each RECS window)
RECS = m.RECS
def severity(line):
    out = {}
    for nm, (a, b) in RECS.items():
        w = [line[i] for i, d in enumerate(DAYS) if a <= d <= b and not np.isnan(line[i])]
        out[nm] = round(float(max(w)), 3) if w else None
    order = [nm for nm, _ in sorted(out.items(), key=lambda kv: (kv[1] is not None, kv[1]), reverse=True)]
    return out, order
sev = {k: severity(lines[k]) for k in lines}
baseline_swap = {
    "estimators": {"current": "mean/std over NBER-expansion baseline minus COVID(2020-21) minus 2022-24(2023..2025-06)",
                   "stat_mean": "full-distribution mean/std, no labels excluded",
                   "stat_median_mad": "full-distribution median / (1.4826*MAD), no labels excluded",
                   "note_5_6": "two robust variants reported because choice is otherwise arbitrary"},
    "per_member_mu_sd": musd_change,
    "headline_corr_current_vs_stat_mean": line_corr(lines["current"], lines["stat_mean"]),
    "headline_corr_current_vs_stat_median": line_corr(lines["current"], lines["stat_median_mad"]),
    "maxdiv_current_vs_stat_mean": max_div(lines["current"], lines["stat_mean"]),
    "maxdiv_current_vs_stat_median": max_div(lines["current"], lines["stat_median_mad"]),
    "severity_peaks": {k: sev[k][0] for k in lines},
    "severity_order": {k: sev[k][1] for k in lines},
}

# ---------- §6 missing-channel treatment ----------
line_renorm = headline_from_CS(CS, renorm=True)
line_zero = headline_from_CS(CS, renorm=False)
wsum_series = np.full(len(DAYS), np.nan)
for i in range(len(DAYS)):
    present = ~np.isnan(CS[i])
    if present.any(): wsum_series[i] = W[present].sum()
# boundary: dates where wsum<1
below1 = [(DAYS[i].isoformat(), round(float(wsum_series[i]), 3)) for i in range(len(DAYS)) if not np.isnan(wsum_series[i]) and wsum_series[i] < 0.999]
first_full = next((DAYS[i].isoformat() for i in range(len(DAYS)) if not np.isnan(wsum_series[i]) and wsum_series[i] >= 0.999), None)
sev_renorm = severity(line_renorm); sev_zero = severity(line_zero)
missing_channel = {
    "corr_renorm_vs_zero": line_corr(line_renorm, line_zero),
    "maxdiv_renorm_vs_zero": max_div(line_renorm, line_zero),
    "severity_order_renorm": sev_renorm[1],
    "severity_order_zero": sev_zero[1],
    "orders_identical": sev_renorm[1] == sev_zero[1],
    "wsum_first_full_1p00": first_full,
    "wsum_below_1_count_days": len(below1),
    "wsum_distinct_values": sorted(set(round(float(x), 3) for x in wsum_series if not np.isnan(x))),
    "wsum_below1_first": below1[0] if below1 else None,
    "wsum_below1_last": below1[-1] if below1 else None,
    "severity_peaks_renorm": sev_renorm[0],
    "severity_peaks_zero": sev_zero[0],
}

# ---------- emit ----------
out = {
    "s0_span": span, "s0_window": WINDOW, "s0_nn_daily": nn_daily,
    "s1_pearson_matrix": pearson_matrix, "s1_named_pairs": pair_report,
    "s1_collinear_ge_0p80": collinear, "s1_spearman_named": spearman_named,
    "s2_effective_n": effN, "s2_nfci_first_nonnull": nfci_first,
    "s3_var_decomp": {"all": vd_all, "recession": vd_rec, "expansion": vd_exp,
                       "nominal_weight": nominal_w, "gap_realized_minus_nominal": gaps,
                       "equal_contribution_weights_ERC": erc_vec},
    "s4_lead_lag": {"evidence_kind": "external_comparator",
                     "chronology": "NBER recession onsets via USRECD (raw/USRECD.csv)",
                     "rule": f"first day channel score >= its full-history {lead_pct}th pct within [onset-24mo, onset+6mo]; +days = lead",
                     "channel_thresholds_pct80": {c: round(ch_thresh[c], 3) for c in CH_ORDER},
                     "per_episode_lead_days": lead_report, "per_channel_stats": lead_stats,
                     "reachable_onsets": reachable, "unreachable": unreachable,
                     "n_reachable": len(reachable)},
    "s5_baseline_swap": baseline_swap,
    "s6_missing_channel": missing_channel,
}
outpath = REPO + "/research/channel_structure_ch1/scratch/ch1_results.json"
json.dump(out, open(outpath, "w"), indent=1, default=str)
print("\n===CH1 RESULTS WRITTEN===", outpath)
print(json.dumps({
    "window": WINDOW, "collinear_ge_0p80": collinear,
    "named_pairs": pair_report, "effN": effN, "nfci_first": nfci_first,
    "vd_all": vd_all, "vd_rec": vd_rec, "vd_exp": vd_exp, "gaps": gaps, "erc": erc_vec,
    "lead_stats": lead_stats, "n_reachable": len(reachable), "unreachable": unreachable,
    "baseline_corr_mean": baseline_swap["headline_corr_current_vs_stat_mean"],
    "baseline_corr_median": baseline_swap["headline_corr_current_vs_stat_median"],
    "maxdiv_mean": baseline_swap["maxdiv_current_vs_stat_mean"],
    "maxdiv_median": baseline_swap["maxdiv_current_vs_stat_median"],
    "sev_order": baseline_swap["severity_order"], "sev_peaks": baseline_swap["severity_peaks"],
    "missing": missing_channel,
}, indent=1, default=str))
