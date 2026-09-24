#!/usr/bin/env python3
"""THE recession-probability forecaster for the Monitor site (adopted 2026-07-25).

The site's number is the PAH3 publication-aware TOP-5-MEDIAN ENSEMBLE
probability -- five frozen ridge-logistic configs (all H=24: trained on
"recession onset within 24 months", our dating), fit on the augmented
interaction panel, combined by per-month median. The member list, feature
pools (screens), and machinery are byte-pinned to the PAH3-C1 registered
confirmation (research/confirm/pah3-c1, verdict PASS); forecaster_pah3/
holds sha-verified copies so production never imports from research/.

Nightly, this script:
  1. rebuilds the monthly panel FRESH from the production raw caches
     (pah2_data machinery; the one wiring change vs research is that the
     live raw/ cache is preferred over the frozen P-4 snapshot, so new
     months and agency revisions flow in -- the publication-aware lane's
     stated contract);
  2. rebuilds the interaction panel + derived-column screens
     (pah3_features, walk-forward, label-free where required);
  3. regenerates the ensemble's walk-forward OOS probability path (the
     graded history; nothing on the chart is a full-sample fit) and
     re-grades it against BOTH datings;
  4. computes today's live ensemble probability (full-sample fits of the
     five frozen members, last panel row -- the same construction as the
     research shadow ledger's pah3_pub clock);
  5. applies the site's coverage floor: displayed = max(ensemble, rising
     accumulated stress E12/7.5) -- identical to the retired hybrid's
     floor, so a COVID-class shock still trips the warning at onset;
  6. writes geo/forecaster.json and FAILS CLOSED (nonzero exit, refresh
     chain aborts before assemble) if the regenerated OOS AUC drifts more
     than 0.02 from the registered 0.9544, if any live member fit is not
     finite, or if the displayed series no longer crosses the lane's warn
     line for every recession in our dating.

The warn line is per-lane and derived on PAH3's own calibrated scale
(DEC-022): see WARN_LANES below. It is NOT the retired 0.75 carryover.

`--frozen` is accepted for refresh-chain symmetry (the spec is always
frozen). `--pinned-panel DIR` re-scores against an existing pah3 panel
dir (read-only; used to verify equality with the shadow ledger).
"""
import os

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")

import sys  # noqa: E402
import json  # noqa: E402
import hashlib  # noqa: E402
import datetime as dt  # noqa: E402

def _assert_complete_calendar(months, name="longline"):
    """A positional window (vals[i-11:i+1]) is only a 12-CALENDAR-MONTH window
    when the month list has no holes.  October 2025 has no household-survey
    value, and any series that inherits that hole will silently make positional
    windows average non-adjacent months.  Fail loudly instead.
    Added 2026-08-22 after that bug was found in ms_inhand_build.py."""
    idx = [int(str(m)[:4]) * 12 + int(str(m)[5:7]) - 1 for m in months]
    bad = [i for a, b, i in zip(idx, idx[1:], range(1, len(idx))) if b - a != 1]
    if bad:
        holes = [f"{idx[i-1]//12:04d}-{idx[i-1]%12+1:02d} -> {idx[i]//12:04d}-{idx[i]%12+1:02d}" for i in bad[:5]]
        raise ValueError(f"{name} is not a complete monthly calendar ({len(bad)} break(s): {holes}). "
                         f"Positional 12-month windows are unsafe; index by calendar month.")


sys.dont_write_bytecode = True

ROOT = os.path.dirname(os.path.abspath(__file__))
P3DIR = os.path.join(ROOT, "forecaster_pah3")
GEO = os.path.join(ROOT, "geo")
OUT_JSON = os.path.join(GEO, "forecaster.json")

PINNED_PANEL = None
if "--pinned-panel" in sys.argv:
    PINNED_PANEL = os.path.abspath(sys.argv[sys.argv.index("--pinned-panel") + 1])

os.environ["PAH2_OUT"] = os.path.join(P3DIR, "pah2", "out")
os.environ["PUSH95_OUT"] = PINNED_PANEL or os.path.join(P3DIR, "push95", "out")

for sub in ("pah1", "pah2", "push95"):
    sys.path.insert(0, os.path.join(P3DIR, sub))

# ---- the frozen spec (PAH3-C1 registration, verdict PASS 2026-07-25) ----
LANE = "publication_aware"
H = 24                     # every member: P(onset within 24 months)
MEMBERS = (("seeded", 15, 300.0), ("ranked", 15, 30.0), ("seeded", 8, 10.0),
           ("seeded", 15, 100.0), ("seeded", 15, 1000.0))
REGISTERED = {"auc": 0.9544, "auc_nber": 0.9255, "n_oos": 464}
AUC_DRIFT_TOL = 0.02       # fail-closed tripwire vs the registered number

# ---- the warn line: per-lane, derived on PAH3's own scale (DEC-022) ----
# The 0.75 line was a carryover from the retired leading_warn2 curve+NFCI
# probit, whose stress floor was engineered so the warning cleared 75% at
# every recession. PAH3 emits rank-to-frequency calibrated probabilities on
# a different scale, so the line was re-derived per lane on the walk-forward
# OOS paths (ALARM2 a1, research/alarm2/out/a1_warnline.json, W=24 grading —
# horizon-matched to H=24). ONE named constant per lane; never a literal.
#
#   publication_aware (the site's lane): RED 0.85 — 6/6 covered onsets,
#     2.043 false-alarm clusters/decade and month precision 0.7846, against
#     2.809 and 0.7312 at 0.75 with the same 6/6. Leads min/median/max
#     9/10/11 months (9/11/15 at 0.75). AMBER watch band 0.55-0.65: both
#     still 6/6 but at 3.319 FA clusters/decade, so they are a "watch the
#     band" tier, not a warning.
#   realtime_strict: RED 0.50 — DERIVED, not swept (DEC-025). The Bayes-optimal
#     threshold on a calibrated probability is tau* = 1/(1+K) with K the cost of
#     a miss over the cost of a false alarm; the neutral K=1 gives 0.50. It
#     weakly dominates the swept 0.55 it replaces: same 6/6 recall, same 1.532
#     FA clusters/decade, higher month precision (0.704 vs 0.692) and a longer
#     max lead (24 vs 22 months). 0.75 on this lane catches only 5/6, missing
#     2020-03, the exogenous shock the production stress floor covers. No amber
#     band was derived for this lane, so none is asserted.
#
# DISCLOSURE (DEC-025): the publication-aware red line of 0.85 implies K = 0.176,
# i.e. that a false alarm costs 5.67x a missed recession, which no reading of the
# loss-asymmetry literature supports. The real explanation is that episode recall
# on that lane is 6/6 at EVERY threshold from 0.09 to 0.85, so the line is a
# one-sided false-alarm dial and its implied K is an artefact of picking a point
# on a one-sided frontier, not a stated loss preference. Any K >= 1 would give
# tau <= 0.50, keep the same 6/6, and raise false alarms 60-125% for no coverage
# gain. The line stays; the claim that it encodes a cost preference does not.
WARN_LANES = {
    # DEC-028 (2026-07-26): the amber watch band is RETIRED. It was never much more
    # than a second, softer line on a one-sided frontier: DERIV found episode recall
    # on this lane is 6/6 at EVERY threshold from 0.09 to 0.85, so a band below the
    # red line buys no coverage and only trades false alarms (3.319 clusters/decade
    # inside the band against 2.043 at the red line). BAND1 then showed the displayed
    # series is not calibrated at all -- ECE 0.228, mean 0.383 against a base rate of
    # 0.155 -- so a second threshold on an uncalibrated scale was reading precision
    # into it that is not there. One line, honestly stated, beats two.
    "publication_aware": {"red": 0.85, "amber_lo": None, "amber_hi": None},
    "realtime_strict":   {"red": 0.50, "amber_lo": None, "amber_hi": None},
}
WARN = WARN_LANES[LANE]["red"]
AMBER_LO = WARN_LANES[LANE]["amber_lo"]
AMBER_HI = WARN_LANES[LANE]["amber_hi"]
WARN_PCT = int(round(WARN * 100))

BAR = 7.5                  # sigma-months; the stress floor's denominator
LEAD_WINDOW_M = 24         # look up to 24 months before an onset (H=24)
COVID_PREFIX = "2020-03"


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build_panels():
    """Stage 1+2: fresh monthly panel from production raw, then the
    augmented interaction panel + derived screens. In-process, with ONE
    wiring change vs research: prefer the live production raw/ cache over
    the frozen P-4 snapshot so the panel actually refreshes."""
    import pah1_common as C
    import pah1_data as D

    def live_locate(sid, _orig=D.locate):
        p = os.path.join(C.PROJECT_RAW, sid + ".csv")
        if os.path.exists(p):
            return p, "project_raw"
        return _orig(sid)

    D.locate = live_locate
    import pah2_data
    assert pah2_data.OUT_DIR == os.environ["PAH2_OUT"]
    pah2_data.main()
    import pah3_features
    assert pah3_features.OUT_DIR == os.environ["PUSH95_OUT"]
    pah3_features.main()


def load_e12_monthly():
    """Monthly accumulated stress from the production recpage long line
    (trailing-12-month sum of positive readings, partial window at the
    start) -- byte-for-byte the construction the retired hybrid floored
    with, on the monthly grid. Returns {month_index: e12}."""
    import pah1_common as C
    ll = json.load(open(os.path.join(GEO, "recpage.json")))["longline"]
    out = {}
    _assert_complete_calendar([m for m, _v in ll], "forecaster_site longline")
    vals = [v for _m, v in ll]
    for i, (m, _v) in enumerate(ll):
        mi = C.month_index(int(m[0:4]), int(m[5:7]))
        out[mi] = sum(max(x, 0.0) for x in vals[max(0, i - 11):i + 1])
    return out


def floor_series(n_months):
    """clip(E12/7.5, 0, 1) while stress is RISING (higher than 3 months
    ago), else 0; None where the long line has no reading."""
    e12 = load_e12_monthly()
    fl = [None] * n_months
    for t in range(n_months):
        if t not in e12:
            continue
        rising = (t - 3) in e12 and e12[t] > e12[t - 3]
        fl[t] = min(max(e12[t] / BAR, 0.0), 1.0) if rising else 0.0
    return fl, e12


def fit_member_live(C, P2, P3, pools, ordering, K, lam):
    """Full-sample fit of one frozen ridge member (H=24) + live prob at
    the last panel row. Identical construction to the research shadow's
    pah3_pub clock (walk-forward numbers remain the grade)."""
    import numpy as np
    G = P3.G
    X = G["X"]
    cols = pools[ordering][H][:K]
    y, valid = G["targets"][H]
    Xs = X[np.ix_(valid, cols)]
    mu, sd = C.standardize_train(Xs)
    Z = C.apply_standardize(Xs, mu, sd)
    w = C.fit_ridge_logistic(Z, y[valid], lam)
    ptr = C.predict_logistic(Z, w)
    inner, vals = P2.calib_fit(ptr, y[valid].astype(float))
    z = C.apply_standardize(X[-1, cols][None, :], mu, sd)
    p = C.predict_logistic(z, w)[0]
    return float(P2.calib_apply(np.array([p]), inner, vals)[0])


def episodes_from(onsets, intervals):
    """(onset_mi, end_mi) per episode; the 1979-82 complex is one row."""
    out = []
    for on, en in intervals:
        if out and on == out[-1][0]:
            out[-1] = (on, max(en, out[-1][1]))
        else:
            out.append((on, en))
    return out


def per_episode(disp, onsets, intervals, first_oos_mi):
    import pah1_common as C
    fire = [t for t, p in enumerate(disp) if p is not None and p >= WARN]
    rows = []
    prev_end = -1
    for a, b in episodes_from(onsets, intervals):
        # window clamped at the previous episode's end: a prior
        # recession's stress tail never counts as this one's warning
        lo = max(a - LEAD_WINDOW_M, prev_end + 1)
        w = [t for t in fire if lo <= t <= b]
        prev_end = b
        onset_iso = C.mi_to_str(a) + "-01"
        covid = onset_iso.startswith(COVID_PREFIX)
        if w:
            first = min(w)
            rows.append({"onset": onset_iso, "fired": True,
                         "first_cross": C.mi_to_str(first) + "-01",
                         "lead_months": float(a - first),
                         "ahead": bool(first < a),
                         "era": "OOS" if a >= first_oos_mi else "floor",
                         "coincidental": covid})
        else:
            rows.append({"onset": onset_iso, "fired": False,
                         "first_cross": None, "lead_months": None,
                         "ahead": False,
                         "era": "OOS" if a >= first_oos_mi else "floor",
                         "coincidental": covid})
    return rows


def mi_daynum(mi):
    import pah1_common as C
    y = C.BASE_YEAR + mi // 12
    m = mi % 12 + 1
    return (dt.date(y, m, 1) - dt.date(1970, 1, 1)).days


def spans_daynum(intervals, n_months):
    """[onset-month first day, end-month last day] in epoch day numbers.
    mi_daynum is pure calendar arithmetic, so en+1 is safe at the edge."""
    return [[mi_daynum(on), mi_daynum(en + 1) - 1] for on, en in intervals]


def dist_spans_daynum():
    """Sub-recession stress episodes, in epoch day numbers, for the chart's amber
    bands (DEC-028). Read straight from the published census so the forecaster can
    never disagree with the Recessions tab about when a disturbance ran. Recessions,
    their aftermaths and lead-ins are excluded: those are already drawn in red or
    belong to a recession's own span."""
    census = json.load(open(os.path.join(ROOT, "geo", "census.json")))
    epoch = dt.date(1970, 1, 1)
    out = []
    for e in census.get("events", []):
        if e.get("class") not in ("disturbance", "major"):
            continue
        try:
            a = dt.date(*[int(x) for x in e["start"][:10].split("-")])
            b = dt.date(*[int(x) for x in e["end"][:10].split("-")])
        except (KeyError, ValueError):
            continue
        out.append([(a - epoch).days, (b - epoch).days])
    return sorted(out)


def main():
    import numpy as np
    t0 = dt.datetime.now()
    if PINNED_PANEL is None:
        print("forecaster: rebuilding panels from production raw")
        sys.stdout.flush()
        build_panels()
    else:
        print("forecaster: VERIFY mode against pinned panel %s" % PINNED_PANEL)

    import pah1_common as C
    import pah2_search as P2
    import pah3_search as P3
    P3.load_globals()
    G = P3.G
    n = G["mi_arr"].size
    pools, _seed_note = P3.build_push_pools(LANE)

    # ---- walk-forward OOS path of the frozen 5-member ensemble ----
    # PAH3-C1 convention exactly: each member's scored mask is the
    # intersection over ALL six horizons {6,9,12,15,18,24}; the plotted /
    # graded path is the per-month median of the H=24 calibrated paths on
    # the rows common to all five members.
    paths, common = [], np.ones(n, dtype=bool)
    for (ordering, K, lam) in MEMBERS:
        cols = pools[ordering]
        m_common = np.ones(n, dtype=bool)
        p24 = None
        for Hh in P3.HORIZONS:
            info = P2.walkforward_horizon(cols[Hh][:K], lam, Hh,
                                          keep_train=False)
            m_common &= info["scored"]
            if Hh == H:
                p24 = info["probs"]
        paths.append(p24)
        common &= m_common
    med = np.median(np.vstack(paths), axis=0)

    y12, valid12 = G["targets"][P3.PRIMARY_H]
    yn12, vn12 = G["nber_target"]
    rows = common & valid12
    seln = common & vn12
    e_auc = float(C.rank_auc(med[rows], y12[rows]))
    e_nber = float(C.rank_auc(med[seln], yn12[seln]))
    print("  ensemble walk-forward AUC ours=%.4f (registered %.4f) "
          "NBER=%.4f (registered %.4f) over %d rows"
          % (e_auc, REGISTERED["auc"], e_nber, REGISTERED["auc_nber"],
             int(rows.sum())))

    # ---- today's live ensemble probability (the clock) ----
    member_live = [fit_member_live(C, P2, P3, pools, o, K, lam)
                   for (o, K, lam) in MEMBERS]
    live = float(np.median(member_live))
    print("  live member probs %s -> ensemble median %.5f"
          % ([round(p, 5) for p in member_live], live))

    # ---- the coverage floor and the displayed series ----
    fl, e12 = floor_series(n)
    scored_idx = np.flatnonzero(common)
    first_oos_mi = int(scored_idx[0]) if scored_idx.size else n
    last_scored = int(scored_idx[-1]) if scored_idx.size else -1
    disp = [None] * n
    for t in range(n):
        if t > last_scored:
            break  # right-censored tail: 24-month outcomes not yet decidable
        cands = []
        if common[t] and np.isfinite(med[t]):
            cands.append(float(med[t]))
        if fl[t] is not None:
            cands.append(fl[t])
        if cands:
            disp[t] = round(max(cands), 4)

    last_e12_mi = max(e12) if e12 else None
    floor_now = 0.0
    if last_e12_mi is not None:
        rising = (last_e12_mi - 3) in e12 and \
            e12[last_e12_mi] > e12[last_e12_mi - 3]
        floor_now = min(max(e12[last_e12_mi] / BAR, 0.0), 1.0) if rising \
            else 0.0
    cur_p = max(live, floor_now)

    pz = np.load(os.path.join(os.environ["PUSH95_OUT"], "pah3_panel.npz"),
                 allow_pickle=False)
    our_onsets = [int(v) for v in pz["our_onsets"]]
    our_intervals = [(int(a), int(b)) for a, b in pz["our_intervals"]]
    nber_onsets = [int(v) for v in pz["nber_onsets"]]
    nber_intervals = [(int(a), int(b)) for a, b in pz["nber_intervals"]]

    eps_inst = per_episode(disp, our_onsets, our_intervals, first_oos_mi)
    eps_nber = per_episode(disp, nber_onsets, nber_intervals, first_oos_mi)
    ci = sum(1 for e in eps_inst if e["fired"])
    cn = sum(1 for e in eps_nber if e["fired"])

    panel_month = C.mi_to_str(n - 1)
    out = {
        "model": ("THE recession forecaster: publication-aware top-5-median "
                  "ridge ensemble on the interaction panel (all members "
                  "H=24), floored by the instrument's rising accumulated "
                  "stress."),
        "lane": LANE, "horizon_months": H, "warn": WARN, "bar": BAR,
        "warn_amber": ([AMBER_LO, AMBER_HI]
                       if AMBER_LO is not None else None),
        "warn_lanes": WARN_LANES, "warn_decision": "DEC-022",
        "primary_chronology": "instrument (our dating)",
        "current": {
            "p": round(cur_p, 4), "date": dt.date.today().isoformat(),
            "panel_month": panel_month,
            "above_warn": bool(cur_p >= WARN),
            "band": ("red" if cur_p >= WARN else
                     ("amber" if (AMBER_LO is not None
                                  and cur_p >= AMBER_LO) else "clear")),
            "ensemble_component": round(live, 4),
            "floor_component": round(floor_now, 4),
            "member_probs": [round(p, 5) for p in member_live]},
        "ensemble": {
            "members": [{"family": "ridge", "ordering": o, "K": K,
                         "lam": lam, "H": H} for (o, K, lam) in MEMBERS],
            "registered": dict(REGISTERED),
            "auc": round(e_auc, 4), "auc_nber": round(e_nber, 4),
            "n_oos": int(rows.sum()), "n_nber": int(seln.sum())},
        "auc_oos": round(e_auc, 3), "auc_nber_oos": round(e_nber, 3),
        "coverage_inst": "%d/%d" % (ci, len(eps_inst)),
        "coverage_nber": "%d/%d" % (cn, len(eps_nber)),
        "per_episode": eps_inst, "per_episode_nber": eps_nber,
        "history_m": {str(mi_daynum(t)): disp[t] for t in range(n)
                      if disp[t] is not None},
        "path_end": C.mi_to_str(last_scored) if last_scored >= 0 else None,
        "censor_note": ("The plotted walk-forward path ends where "
                        "24-month outcomes are not yet decidable; the "
                        "live number above is today's ensemble reading."),
        "bands": {"inst": spans_daynum(our_intervals, n),
                  "nber": spans_daynum(nber_intervals, n),
                  # DEC-028: the chart has always been able to draw disturbance
                  # bands; the spans were simply never emitted. Now that the amber
                  # watch band is retired, amber is free to mean what it means
                  # everywhere else on the site: a sub-recession stress episode.
                  "dist": dist_spans_daynum()},
        "method": ("The line is the ensemble's walk-forward OUT-OF-SAMPLE "
                   "probability (expanding refits from 1975-12, "
                   "training-only standardization/calibration), taken as "
                   "the higher of the model and the rising-stress floor "
                   "E12/7.5. Warning at %d%%%s (DEC-022: both lines "
                   "derived on this lane's own calibrated scale, not "
                   "carried over from the retired model). Probabilities "
                   "are 24-month-horizon odds."
                   % (WARN_PCT,
                      ("" if AMBER_LO is None else
                       ", with an amber watch band from %d%% to %d%%"
                       % (int(round(AMBER_LO * 100)),
                          int(round(AMBER_HI * 100)))))),
        # DISP1 (2026-07-25) graded max(model, floor) -- the series actually shown --
        # for the first time. These are the disclosures it forced. They are published
        # rather than quietly held because every AUC on this page grades the model LEG,
        # not the number the reader sees.
        "displayed_series_disclosure": {
            "graded": "research/disp1 (spec a20fc974), nothing fit or swept",
            "reads_as_probability": False,
            "calibration": {
                "publication_aware": {"ece": 0.2278, "mce": 0.610,
                                      "mean_p": 0.383, "base_rate": 0.155},
                "realtime_strict": {"ece": 0.1192}},
            "note": ("The displayed value is the HIGHER of two series and is not "
                     "calibrated: it should be read as a warning level, not as the "
                     "probability of a recession. The dominant miscalibration is the "
                     "model's own (ECE 0.212), not the floor's."),
            "displayed_vs_leg": {
                "realtime_strict": {"displayed_auc": 0.8856, "leg_auc": 0.9075,
                                    "displayed_fa_clusters_per_decade": 3.103,
                                    "leg_fa_clusters_per_decade": 2.328},
                "publication_aware": {"displayed_auc": 0.9523, "leg_auc": 0.9544,
                                      "displayed_fa_clusters_per_decade": 2.586,
                                      "leg_fa_clusters_per_decade": 2.586}},
            "floor_adds_no_lead": ("The floor's own first crossing arrives 1-4 months "
                                   "AFTER onset in five of six out-of-sample episodes, "
                                   "and it gains zero lead months in all six. Its real "
                                   "contribution is the four pre-1976 episodes, where "
                                   "the model has no path."),
            # BAND1 (research/band1): every AUC this project quotes has been a bare
            # point estimate. With six OOS onsets the intervals are wide, and the
            # width is the point. Block bootstrap (Politis-White b*=21-28 months) is
            # 1.7-2.9x wider than DeLong, which is the measured price of DeLong's
            # independence assumption on serially correlated monthly data.
            "auc_intervals_95": {
                "publication_aware": [0.915, 0.984],
                "realtime_strict": [0.822, 0.967],
                "nber_target": [0.762, 0.976]},
            "brier_skill_displayed_publication_aware": -0.0196,
            "skill_note": ("On the lane the site displays, the shown series has "
                           "NEGATIVE Brier skill: it is worse than always quoting the "
                           "base rate of 15.5%. Its miscalibration is a one-directional "
                           "level shift, not a binning artefact -- every bin "
                           "over-forecasts."),
            "recalibration": ("A monotone recalibration changes the flag set by ZERO "
                              "months: it changes what the line is called, not what it "
                              "does. A calibrated 0.85 is never attained on either lane "
                              "(ceilings 0.771 and 0.839), and the warn line's implied "
                              "cost ratio falls from 5.667 to 3.375 (pub) and 1.188 "
                              "(rt), so most of the apparent asymmetry behind DEC-022 "
                              "was calibration artefact."),
            "grading_blind_spot": ("The floor crosses the warn line in 158 months and "
                                   "150 of them are masked off the comparability rows, "
                                   "so only 8 reach any published statistic. The masked "
                                   "set includes the eleven consecutive recovery months "
                                   "2020-05..2021-03."),
        },
        "provenance": {
            "built": t0.isoformat(timespec="seconds"),
            "spec": "PAH3-C1 publication_aware 5-member ensemble (frozen)",
            "registration": "research/confirm/pah3-c1 (verdict PASS)",
            "panel_mode": "pinned" if PINNED_PANEL else
                          "fresh from production raw",
            "panel_sha256": sha256_file(os.path.join(
                os.environ["PUSH95_OUT"], "pah3_panel.npz"))},
    }

    # ---- fail-closed gates (production mode) ----
    fails = []
    if not (0.0 <= cur_p <= 1.0):
        fails.append("current p %r outside [0,1]" % cur_p)
    if len(member_live) != 5 or any(not np.isfinite(p)
                                    for p in member_live):
        fails.append("live member fits incomplete: %s" % member_live)
    if abs(e_auc - REGISTERED["auc"]) > AUC_DRIFT_TOL:
        fails.append("OOS AUC %.4f drifted > %.2f from registered %.4f"
                     % (e_auc, AUC_DRIFT_TOL, REGISTERED["auc"]))
    if ci != len(eps_inst):
        missed = [e["onset"] for e in eps_inst if not e["fired"]]
        fails.append("coverage broken: recessions without a %d%% warn-line "
                     "crossing: %s" % (WARN_PCT, missed))
    if len(out["history_m"]) < 500:
        fails.append("history too short: %d points" % len(out["history_m"]))
    if PINNED_PANEL is not None:
        print("VERIFY: live ensemble median %.5f (shadow ledger pah3_pub "
              "should match within rounding); NOT writing the blob" % live)
        return 0
    if fails:
        for f in fails:
            print("FORECASTER FAIL: %s" % f)
        return 1

    def _np(o):
        if isinstance(o, np.bool_):
            return bool(o)
        if isinstance(o, np.integer):
            return int(o)
        if isinstance(o, np.floating):
            return float(o)
        raise TypeError(str(type(o)))

    json.dump(out, open(OUT_JSON, "w"), indent=1, default=_np)
    el = (dt.datetime.now() - t0).total_seconds()
    print("wrote geo/forecaster.json (%.0fs)" % el)
    print("  current p=%.4f (ensemble %.4f, floor %.4f) above_warn=%s "
          "panel=%s" % (cur_p, live, floor_now, cur_p >= WARN, panel_month))
    print("  crossed the %d%% warn line: OUR dating %s | NBER %s"
          % (WARN_PCT, out["coverage_inst"], out["coverage_nber"]))
    for e in eps_inst:
        print("    %s  %s  lead %smo  %s%s"
              % (e["onset"][:7], "CROSSED" if e["fired"] else "MISS",
                 e["lead_months"], e["era"],
                 "  (COVID shock)" if e["coincidental"] else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
