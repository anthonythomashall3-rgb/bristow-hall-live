#!/usr/bin/env python3
"""B-SYNTH-BATTERY — synthetic machinery battery (Window 3, code/ops, NO store write).

Builds PREREGISTRATION v1.1 §8 planted-signal machinery test:
  generator (factor structure + plantable recession-like signal, strength dial
  spanning the CH-R126 MDES threshold ~=0.85 SD) + placebo panels (no signal) ->
  run the frozen pipeline (factor step -> Bai-Ng rank -> supervised ridge map ->
  two-tier AMBER/RED detection) end-to-end on both -> report detection lag /
  false-alarm / recovery curves vs strength, with AMBER/RED two-tier replay
  support per the TRIPWIRE ruling.

BINDING (prereg v1.1 §8, §19.1/§21.3): the FIRST LINE of EVERY output states this
validates MACHINERY, NOT real-world recession detection. A machinery pass reported
as accuracy is a rule violation.

Universe stays OPEN (§22.2). Nothing here derives a real channel, member, weight,
transform, threshold or dimension: the pipeline fits ONLY on synthetic planted
truth. No store read, no store write, no network. numpy only.

Threshold reference: CH-R126.v1.json MDES_single_factor_SD N11=0.845 (~0.85 SD).
"""
import json
import datetime as dt
import numpy as np

# The binding disclaimer. Every emitted artifact (JSON + markdown + stdout) leads
# with this verbatim. Prereg v1.1 §8 hard constraint.
DISCLAIMER = "validates machinery, NOT real-world recession detection."

# CH-R126 published minimum detectable standardized single-factor effect (SD).
MDES_THRESHOLD_SD = 0.845

# Default strength grid straddles the MDES threshold: placebo(0), below, at, above.
DEFAULT_STRENGTHS = (0.0, 0.4, 0.6, 0.845, 1.1, 1.5)


# --------------------------------------------------------------------------- #
# Generator                                                                    #
# --------------------------------------------------------------------------- #
def default_episodes(n_months):
    """Planted onset months + lengths, spaced across the panel (machinery only)."""
    # Mean episode length ~10 months (CH-R126 inputs_cited mean_episode_len 10.27).
    # Several episodes so BOTH the train and held-out windows carry a few (lower
    # variance on the out-of-sample detection curve).
    onsets = [int(n_months * f) for f in (0.10, 0.27, 0.44, 0.63, 0.83)]
    lengths = [9, 11, 8, 10, 9]
    return list(zip(onsets, lengths))


def recession_state(n_months, episodes):
    """Binary planted recession indicator z_t (1 during a planted episode)."""
    z = np.zeros(n_months, dtype=float)
    for onset, length in episodes:
        z[onset:min(onset + length, n_months)] = 1.0
    return z


def _ar1(n, rho, sd, rng):
    x = np.zeros(n)
    innov = rng.normal(0.0, sd * np.sqrt(1.0 - rho * rho), size=n)
    for t in range(1, n):
        x[t] = rho * x[t - 1] + innov[t]
    return x


def roc_auc(scores, labels):
    """Mann-Whitney rank AUC of `scores` separating labels==1 from labels==0.

    Robust, smooth per-month detection metric (the headline machinery-recovery
    number). 0.5 == chance. Returns nan if either class is empty.
    """
    scores = np.asarray(scores, dtype=float)
    labels = np.asarray(labels, dtype=float)
    pos = scores[labels == 1]
    neg = scores[labels == 0]
    if len(pos) == 0 or len(neg) == 0:
        return float("nan")
    order = np.argsort(scores, kind="mergesort")
    ranks = np.empty(len(scores), dtype=float)
    ranks[order] = np.arange(1, len(scores) + 1)
    # average ties
    _, inv, counts = np.unique(scores, return_inverse=True, return_counts=True)
    tie_mean = np.zeros(len(counts))
    sums = np.zeros(len(counts))
    np.add.at(sums, inv, ranks)
    tie_mean = sums / counts
    ranks = tie_mean[inv]
    r_pos = ranks[labels == 1].sum()
    n_pos, n_neg = len(pos), len(neg)
    auc = (r_pos - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg)
    return float(auc)


def make_panel(strength, seed, n_series=40, n_months=300, n_factors=3,
               episodes=None, real_time=True):
    """Generate one synthetic panel.

    strength : recession dip amplitude in SD units on the cycle factor. 0 => placebo.
    Returns dict with the observed panel X (n_months x n_series), the planted
    recession label z, the cycle-factor truth, publication lags, and metadata.

    Factor structure: r AR(1) latent factors, gaussian loadings, idiosyncratic
    noise. The FIRST factor is the 'cycle' factor; during a planted episode it is
    depressed by `strength` SD. real_time=True injects vintage revision noise
    (early observations noisier) and ragged per-series publication lags matched in
    spirit to the measured panel (§8 'realistic real-time revision noise and
    ragged publication lags').
    """
    rng = np.random.default_rng(seed)
    if episodes is None:
        episodes = default_episodes(n_months)
    z = recession_state(n_months, episodes)

    # Latent factors.
    F = np.column_stack([_ar1(n_months, rho=0.6, sd=1.0, rng=rng)
                         for _ in range(n_factors)])
    # Plant the recession-like signal on the cycle (first) factor: a mean shift of
    # -strength SD during episodes, on top of its AR(1) fluctuation.
    F[:, 0] = F[:, 0] - strength * z

    # Loadings: cycle factor loads broadly (systematic), others sparser.
    Lam = rng.normal(0.0, 1.0, size=(n_series, n_factors))
    Lam[:, 0] = np.abs(Lam[:, 0]) + 0.5  # cycle loads positively & broadly

    common = F @ Lam.T                                  # n_months x n_series
    idio = rng.normal(0.0, 1.0, size=(n_months, n_series))
    X = common + idio

    lags = np.zeros(n_series, dtype=int)
    if real_time:
        # Vintage revision noise: extra noise decaying over the sample age is not
        # modelled per-vintage here (single-vintage machinery test); instead inject
        # heavier idiosyncratic noise on the most-recent tail to mimic first-release
        # instability, plus ragged publication lags (0..2 months) per series.
        tail = max(1, n_months // 12)
        X[-tail:, :] += rng.normal(0.0, 0.7, size=(tail, n_series))
        lags = rng.integers(0, 3, size=n_series)
        for j in range(n_series):
            if lags[j] > 0:
                col = X[:, j].copy()
                X[lags[j]:, j] = col[:-lags[j]]
                X[:lags[j], j] = col[0]

    return {
        "X": X,
        "z": z,
        "cycle_truth": F[:, 0],
        "episodes": episodes,
        "lags": lags,
        "strength": float(strength),
        "n_series": n_series,
        "n_months": n_months,
        "n_factors": n_factors,
        "placebo": strength == 0.0,
    }


# --------------------------------------------------------------------------- #
# Frozen pipeline  (blind to planted truth except supervised labels)           #
# --------------------------------------------------------------------------- #
def _standardize(X):
    mu = X.mean(axis=0)
    sd = X.std(axis=0)
    sd[sd == 0] = 1.0
    return (X - mu) / sd


def bai_ng_rank(X, kmax=8):
    """Bai & Ng (2002) ICp2 rank selection on a standardized panel.

    Returns r_hat in [1, kmax]. Machinery-test scope: standard ICp2 penalty.
    """
    Z = _standardize(X)
    T, N = Z.shape
    kmax = min(kmax, N - 1, T - 1)
    # SVD once; residual variance for k factors = mean squared residual.
    U, s, Vt = np.linalg.svd(Z, full_matrices=False)
    ics = []
    NT = N * T
    pen_unit = (N + T) / NT * np.log(min(N, T))
    for k in range(1, kmax + 1):
        approx = (U[:, :k] * s[:k]) @ Vt[:k, :]
        resid = Z - approx
        v = (resid ** 2).mean()
        ics.append(np.log(v) + k * pen_unit)
    return int(np.argmin(ics) + 1)


def extract_factors(X, r=None, kmax=8):
    """Factor step: standardize + PCA (SVD). Rank by Bai-Ng if r is None."""
    Z = _standardize(X)
    if r is None:
        r = bai_ng_rank(X, kmax=kmax)
    U, s, Vt = np.linalg.svd(Z, full_matrices=False)
    F_hat = U[:, :r] * s[:r]          # factor scores (T x r)
    return F_hat, r


def supervised_map(F_hat, labels, ridge=1.0, train_idx=None):
    """Supervised step: ridge (L2) linear map factors -> planted risk label.

    Ridge-regularised least squares (machinery test; §22.4 keeps this on synthetic
    labels only). The map is FIT on train_idx months only (leakage guard, prereg
    §8: the supervised step never sees the evaluation window's labels); the score
    is then produced for ALL months. Returns a risk score per month in [0,1] via a
    logistic squash of the fitted linear index (standardised on the train window),
    higher score = more recession.
    """
    T, r = F_hat.shape
    Xd = np.column_stack([np.ones(T), F_hat])
    y = np.asarray(labels, dtype=float)
    if train_idx is None:
        train_idx = np.arange(T)
    Xt, yt = Xd[train_idx], y[train_idx]
    P = Xd.shape[1]
    A = Xt.T @ Xt + ridge * np.eye(P)
    A[0, 0] -= ridge                      # do not penalise the intercept
    beta = np.linalg.solve(A, Xt.T @ yt)
    idx = Xd @ beta
    # Standardise the linear index using TRAIN-window moments (no eval-window peek).
    itr = idx[train_idx]
    mu, sd = itr.mean(), itr.std()
    if sd == 0:
        sd = 1.0
    risk = 1.0 / (1.0 + np.exp(-(idx - mu) / sd))
    return risk


def run_pipeline(panel, ridge=1.0, kmax=8, train_frac=0.6):
    """Frozen pipeline end-to-end: factor -> Bai-Ng rank -> supervised map.

    The unsupervised factor step uses the whole panel (it is label-blind); the
    supervised map is fit ONLY on the first `train_frac` of months so detection is
    scored out-of-sample on held-out planted episodes (prereg §8 leakage guard).
    `cut` is the train/test boundary index.
    """
    T = panel["n_months"]
    cut = int(T * train_frac)
    F_hat, r_hat = extract_factors(panel["X"], kmax=kmax)
    risk = supervised_map(F_hat, panel["z"], ridge=ridge,
                          train_idx=np.arange(cut))
    return {"risk": risk, "r_hat": r_hat, "cut": cut}


# --------------------------------------------------------------------------- #
# Two-tier AMBER / RED detection  (TRIPWIRE ruling A5)                          #
# --------------------------------------------------------------------------- #
def _episode_windows(z):
    """List of (start, end_exclusive) for each contiguous run of z==1."""
    wins = []
    t = 0
    n = len(z)
    while t < n:
        if z[t] == 1:
            s = t
            while t < n and z[t] == 1:
                t += 1
            wins.append((s, t))
        else:
            t += 1
    return wins


def derive_two_tier(risk, z, lead=3):
    """Derive AMBER and RED thresholds by the TRIPWIRE fixed rules on REPLAY.

    AMBER (never-late): highest threshold that still fires at or before every
      planted onset within a `lead`-month pre-window => leads every episode.
    RED (never-false): lowest threshold that produces ZERO firings outside any
      planted episode => zero false alarms in replay.
    Returns dict of thresholds (np.nan if the rule cannot be met at this signal).
    """
    risk = np.asarray(risk, dtype=float)
    wins = _episode_windows(z)
    # AMBER: for each episode, the max risk within [onset-lead, onset]. The amber
    # threshold that leads EVERY episode is the min over episodes of that per-episode
    # max (fire no later than onset for all).
    per_ep_lead_max = []
    for (s, _e) in wins:
        lo = max(0, s - lead)
        per_ep_lead_max.append(risk[lo:s + 1].max())
    amber_thr = float(min(per_ep_lead_max)) if per_ep_lead_max else np.nan

    # RED: never-false => threshold strictly above the max risk seen OUTSIDE every
    # episode. If that max is >= the in-episode signal, RED cannot fire in-episode
    # without a false alarm => mark unmet (nan) so it is reported, not hidden.
    in_ep = np.zeros(len(risk), dtype=bool)
    for (s, e) in wins:
        in_ep[s:e] = True
    out_max = risk[~in_ep].max() if (~in_ep).any() else -np.inf
    in_max = risk[in_ep].max() if in_ep.any() else -np.inf
    # A hair above the worst false candidate; unmet if no in-episode point clears it.
    red_thr = float(np.nextafter(out_max, np.inf))
    if in_max <= out_max:
        red_thr = np.nan
    return {"amber_thr": amber_thr, "red_thr": red_thr, "lead": lead}


def evaluate(risk, z, thresholds, recovery_frac=0.5):
    """Measure detection lag, false-alarm rate, recovery, and amber->red gap.

    All measured on the SAME replay (machinery test, in-sample by design).
      detection_lag_amber : mean(onset_month - first amber fire within pre-window),
        positive => amber leads; measured only where amber fires by onset.
      false_alarm_rate_amber/red : fraction of out-of-episode months that fire.
      recovery_months : mean months after episode end until risk falls below the
        amber threshold (machinery recovery curve).
      amber_red_gap : mean(red fire month - amber fire month) per episode (the
        PUBLISHED gap metric with standing minimize objective, A5).
    """
    risk = np.asarray(risk, dtype=float)
    n = len(risk)
    wins = _episode_windows(z)
    amber = thresholds["amber_thr"]
    red = thresholds["red_thr"]
    lead = thresholds.get("lead", 3)

    in_ep = np.zeros(n, dtype=bool)
    for (s, e) in wins:
        in_ep[s:e] = True
    out_n = int((~in_ep).sum())

    def far(thr):
        if not np.isfinite(thr) or out_n == 0:
            return float("nan")
        return float((risk[~in_ep] >= thr).sum()) / out_n

    lags, recov, gaps = [], [], []
    reds_fire = 0
    for (s, e) in wins:
        # amber lead: first month in [s-lead, s] where risk>=amber
        if np.isfinite(amber):
            lo = max(0, s - lead)
            fire = np.where(risk[lo:s + 1] >= amber)[0]
            if len(fire):
                lags.append(s - (lo + fire[0]))
        # recovery: months after e until risk drops below amber
        if np.isfinite(amber):
            tail = np.where(risk[e:] < amber)[0]
            recov.append(int(tail[0]) if len(tail) else (n - e))
        # amber->red gap within [s-lead, e]
        if np.isfinite(amber) and np.isfinite(red):
            lo = max(0, s - lead)
            a_fire = np.where(risk[lo:e] >= amber)[0]
            r_fire = np.where(risk[lo:e] >= red)[0]
            if len(a_fire) and len(r_fire):
                gaps.append(int(r_fire[0] - a_fire[0]))
                reds_fire += 1

    def _mean(a):
        return float(np.mean(a)) if len(a) else float("nan")

    return {
        "test_auc": roc_auc(risk, z),
        "detection_lag_amber_lead_months": _mean(lags),
        "amber_fired_episodes": len(lags),
        "n_episodes": len(wins),
        "false_alarm_rate_amber": far(amber),
        "false_alarm_rate_red": far(red),
        "recovery_months": _mean(recov),
        "amber_red_gap_months": _mean(gaps),
        "red_confirmed_episodes": reds_fire,
        "red_rule_met": bool(np.isfinite(red)),
    }


# --------------------------------------------------------------------------- #
# Battery — sweep strength, replicate, aggregate                               #
# --------------------------------------------------------------------------- #
def run_one(strength, seed, train_frac=0.6, **panel_kw):
    """One replicate: generate -> pipeline -> derive tiers on TRAIN replay ->
    evaluate detection on the HELD-OUT test window (out-of-sample, leakage-guarded).
    """
    panel = make_panel(strength, seed, **panel_kw)
    pipe = run_pipeline(panel, train_frac=train_frac)
    cut = pipe["cut"]
    risk, z = pipe["risk"], panel["z"]
    # Fixed-rule thresholds derived on the TRAIN replay only.
    thr = derive_two_tier(risk[:cut], z[:cut])
    # Detection / false-alarm / recovery / gap measured on the HELD-OUT window.
    ev = evaluate(risk[cut:], z[cut:], thr)
    ev["r_hat"] = pipe["r_hat"]
    ev["amber_thr"] = thr["amber_thr"]
    ev["red_thr"] = thr["red_thr"]
    ev["strength"] = float(strength)
    ev["test_episodes"] = ev["n_episodes"]
    return ev


def run_battery(strengths=DEFAULT_STRENGTHS, reps=8, seed0=20260809, **panel_kw):
    """Run the full battery: for each strength, replicate over seeds, aggregate.

    Returns a report dict keyed by strength with mean curves. strength 0.0 is the
    placebo arm. Deterministic given seed0.
    """
    curves = []
    for si, strength in enumerate(strengths):
        rows = [run_one(strength, seed0 + si * 1000 + k, **panel_kw)
                for k in range(reps)]

        def col(key):
            vals = [r[key] for r in rows if r[key] == r[key]]  # drop nan
            return float(np.mean(vals)) if vals else float("nan")

        curves.append({
            "strength": float(strength),
            "is_placebo": strength == 0.0,
            "straddles_mdes": abs(strength - MDES_THRESHOLD_SD) < 1e-9,
            "reps": reps,
            "mean_test_auc": col("test_auc"),
            "mean_r_hat": col("r_hat"),
            "mean_detection_lead_months": col("detection_lag_amber_lead_months"),
            "mean_false_alarm_rate_amber": col("false_alarm_rate_amber"),
            "mean_false_alarm_rate_red": col("false_alarm_rate_red"),
            "mean_recovery_months": col("recovery_months"),
            "mean_amber_red_gap_months": col("amber_red_gap_months"),
            "red_rule_met_fraction": float(
                np.mean([1.0 if r["red_rule_met"] else 0.0 for r in rows])),
            "amber_detected_fraction": float(np.mean(
                [r["amber_fired_episodes"] / max(1, r["n_episodes"]) for r in rows])),
        })
    return {
        "disclaimer": DISCLAIMER,
        "mdes_threshold_sd": MDES_THRESHOLD_SD,
        "mdes_source": "research/CH-R126.v1.json MDES_single_factor_SD.N11=0.845",
        "strengths": list(strengths),
        "reps": reps,
        "seed0": seed0,
        "curves": curves,
    }


# --------------------------------------------------------------------------- #
# Emit                                                                          #
# --------------------------------------------------------------------------- #
def _now_stamp():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def to_markdown(report):
    lines = [DISCLAIMER, "", "# B-SYNTH-BATTERY — planted-signal machinery report",
             "", f"MDES threshold (CH-R126): {report['mdes_threshold_sd']} SD "
             f"({report['mdes_source']})",
             f"reps/arm={report['reps']} seed0={report['seed0']}", "",
             "| strength SD | placebo | test AUC | r_hat | detect lead mo | "
             "FA amber | FA red | recovery mo | amber->red gap | red-rule met | "
             "amber detect |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for c in report["curves"]:
        lines.append(
            "| {strength:.3f}{star} | {pl} | {auc:.3f} | {r:.2f} | {lead:.2f} | "
            "{faa:.3f} | {far:.3f} | {rec:.2f} | {gap:.2f} | {rm:.2f} | "
            "{ad:.2f} |".format(
                strength=c["strength"], star="*" if c["straddles_mdes"] else "",
                pl="Y" if c["is_placebo"] else "-", auc=c["mean_test_auc"],
                r=c["mean_r_hat"],
                lead=c["mean_detection_lead_months"],
                faa=c["mean_false_alarm_rate_amber"],
                far=c["mean_false_alarm_rate_red"],
                rec=c["mean_recovery_months"], gap=c["mean_amber_red_gap_months"],
                rm=c["red_rule_met_fraction"], ad=c["amber_detected_fraction"]))
    lines += ["", "`* = strength straddles the CH-R126 MDES threshold`",
              "", DISCLAIMER, ""]
    return "\n".join(lines)


def main(outdir=None, reps=8):
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    outdir = outdir or here
    report = run_battery(reps=reps)
    stamp = _now_stamp()
    report["stamp"] = stamp
    js = {"first_line": DISCLAIMER, **report}
    jpath = os.path.join(outdir, "SYNTH_BATTERY.v1.json")
    mpath = os.path.join(outdir, "SYNTH_BATTERY.v1.md")
    with open(jpath, "w") as f:
        json.dump(js, f, indent=1)
    md = to_markdown(report)
    with open(mpath, "w") as f:
        f.write(md)
    print(DISCLAIMER)
    print(md)
    return report


if __name__ == "__main__":
    main()
