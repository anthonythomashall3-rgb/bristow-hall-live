"""CH-R55 S10 pre-registration DRY-RUN.

Exercises the B-EXP-0 harness end-to-end against a DELIBERATELY TRIVIAL placeholder
rule ("index value above a fixed percentile"). Scores NOTHING real; adopts NOTHING.
Its only job: prove metrics.py / era_cv.py / replay_ci.py execute, record seeds, and
surface any harness defect or silent-pass path. Read-only §20-class: writes only the
JSON artifact under research/.
"""
import datetime as dt
import json
import random

from contrib.experiment_harness import metrics, era_cv, replay_ci

SEEDS = {"bootstrap": 20260806, "era_cv_synth": 424242, "replay_date": 999}
report = {"note": "CH-R55 dry-run; placeholder rule; adopts nothing; scores nothing real",
          "seeds": SEEDS, "criteria": {}, "s22_scorecard": {}, "era_cv": {},
          "replay_ci": {}, "defects": []}

# ---- synthetic placeholder rule + synthetic data (NOT the real index) --------
# Placeholder rule: fire when the synthetic "index" is above its 80th percentile.
rng_data = random.Random(1)
synth_index = {dt.date(1960, 1, 1) + dt.timedelta(days=90 * i): rng_data.random()
               for i in range(260)}  # ~65 years quarterly toy series
sorted_vals = sorted(synth_index.values())
PCTL = 0.80
threshold = sorted_vals[int(PCTL * (len(sorted_vals) - 1))]
firings = [d for d, v in synth_index.items() if v > threshold]

# ---- Criterion (1): boundary_stability + bootstrap_boundaries ----------------
def pctl_estimator(sample):
    s = sorted(sample)
    return s[int(PCTL * (len(s) - 1))]

boot = metrics.bootstrap_boundaries(sorted_vals, pctl_estimator,
                                    n_resamples=200, seed=SEEDS["bootstrap"])
report["criteria"]["boundary_stability"] = {
    "boundary_stability": metrics.boundary_stability(boot),
    "n_resamples": 200,
    "single_sample_is_zero": metrics.boundary_stability([threshold]),
}

# ---- Criterion (2): false_alarm_rate on 1966 / 1995 / 2015-16 ----------------
nonepisode_windows = [
    (dt.date(1966, 1, 1), dt.date(1966, 12, 31)),
    (dt.date(1995, 1, 1), dt.date(1995, 12, 31)),
    (dt.date(2015, 1, 1), dt.date(2016, 12, 31)),
]
report["criteria"]["false_alarm_rate"] = {
    "false_alarm_rate": metrics.false_alarm_rate(firings, nonepisode_windows),
    "windows": [[str(a), str(b)] for a, b in nonepisode_windows],
    "empty_windows_returns_none": metrics.false_alarm_rate(firings, []),
}

# ---- Criterion (3): era_consistency (2020s excluded vs full) -----------------
# Toy label maps: does the rule admit/exclude each target the same both ways?
labels_full = {"1980": "recession", "1990": "recession", "2001": "recession",
               "2020": "recession", "2022": "disturbance"}
labels_excluded = dict(labels_full)  # trivial: identical -> consistent
labels_excluded_flip = dict(labels_full); labels_excluded_flip["2022"] = "none"
report["criteria"]["era_consistency"] = {
    "consistent_case": metrics.era_consistency(labels_full, labels_excluded),
    "disagreement_case": metrics.era_consistency(labels_full, labels_excluded_flip),
}

# ---- Criterion (4): detection_lead on held-out episodes ----------------------
ref_peak = dt.date(2020, 2, 1)
onset_hit = dt.date(2020, 1, 10)
report["criteria"]["detection_lead"] = {
    "hit_lead_days": metrics.detection_lead(onset_hit, ref_peak),
    "miss_returns_none": metrics.detection_lead(None, ref_peak),
}

# ---- S22 detection_scorecard -------------------------------------------------
leads = {"1980": 42, "1990": 15, "2001": None, "2020": 3, "2022": None}
report["s22_scorecard"] = metrics.detection_scorecard(
    leads, firings, nonepisode_windows, boot)

# ---- era_cv.run: LOO + LOEO with injected trivial fit/eval -------------------
synth_indicator = {}
for d, v in synth_index.items():
    synth_indicator[d] = 1.0 if v > threshold else 0.0
episodes = era_cv.episodes_from_indicator(synth_indicator)
def fit_fn(train):
    return {"n_train": len(train)}
def eval_fn(rule, test):
    return {"n_train_seen": rule["n_train"], "n_test": len(test)}
loo = era_cv.run(episodes, fit_fn, eval_fn, mode="loo")
loeo = era_cv.run(episodes, fit_fn, eval_fn, mode="loeo")
report["era_cv"] = {
    "n_episodes_derived": len(episodes),
    "provenance_stamp": episodes[0]["provenance"] if episodes else None,
    "loo_n_splits": len(loo),
    "loeo_n_splits": len(loeo),
    "loeo_eras": sorted({r["held_out"] for r in loeo}),
}

# ---- replay_ci: confirm the NotImplementedError silent-pass guard ------------
rc = {}
try:
    replay_ci.run_replay_ci(dt.date(2022, 1, 1))  # unwired -> must raise
    rc["unwired_raises"] = False
    report["defects"].append(
        "SERIOUS: replay_ci.run_replay_ci silently passed while unwired")
except NotImplementedError:
    rc["unwired_raises"] = True
# wired to trivial byte-identical fns -> should compare
wired = replay_ci.run_replay_ci(
    dt.date(2022, 1, 1),
    replay_fn=lambda d: {"x": 1, "asof": str(d)},
    publish_fn=lambda d: {"asof": str(d), "x": 1})
rc["wired_byte_identical"] = wired["byte_identical"]
mism = replay_ci.run_replay_ci(
    dt.date(2022, 1, 1),
    replay_fn=lambda d: {"x": 2},
    publish_fn=lambda d: {"x": 1})
rc["wired_mismatch_detected"] = not mism["byte_identical"]
rng_rd = random.Random(SEEDS["replay_date"])
rc["select_replay_date"] = str(
    replay_ci.select_replay_date(rng_rd, dt.date(2020, 1, 1), dt.date(2026, 8, 5)))
report["replay_ci"] = rc

with open("research/s10_harness_dryrun_v1.json", "w") as fh:
    json.dump(report, fh, indent=2, default=str)
print(json.dumps(report, indent=2, default=str))
