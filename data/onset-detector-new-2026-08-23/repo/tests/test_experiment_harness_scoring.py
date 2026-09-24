"""RED-first tests for the Phase-5 probabilistic evaluation scorer (B-TEST-HARNESS).

Phase 5 decides whether any rebuilt instrument is real. The scorer is built BEFORE there
is anything to evaluate (§22.3 architecture is data-independent) so the metric cannot be
picked after seeing the result. The harness adopts NO unit, threshold, chronology, member
set or severity order (CLAUDE.md boundary) — it scores whatever probabilistic forecast the
caller hands it.

Binding pins from the batch brief:
  * proper scoring: Brier, skill vs climatology (base rate 0.155), log score, reliability,
    ECE, sharpness. AUC reported but NEVER primary (rank-only, threshold-free — looks great
    while calibration is broken).
  * mandatory baselines: climatology + persistence as first-class competitors. A result
    that does not beat BOTH on leave-one-recession-out log-score is not an improvement.
  * information-set switch: every evaluation is LABELLED archive_snapshot_asof or
    pseudo_real_time; the label is emitted in the result object, never omitted.
  * decision-level metrics: crossing-date error, false crossings, missed crossings,
    lead-time distribution.
  * a deliberately-leaking split is DETECTED and refused; leave-one-day-out is rejected.
"""
import datetime as dt
import math

import pytest

from contrib.experiment_harness import scoring
from contrib.experiment_harness.era_cv import Split


# ---- proper scoring rules -------------------------------------------------

def test_brier_score_matches_mean_squared_error():
    assert scoring.brier_score([0.1, 0.9], [0, 1]) == pytest.approx(0.01)


def test_brier_score_perfect_forecast_is_zero():
    assert scoring.brier_score([1.0, 0.0], [1, 0]) == 0.0


def test_log_score_is_mean_log_likelihood_higher_is_better():
    # both forecasts assign 0.9 to the realised outcome -> ln(0.9)
    assert scoring.log_score([0.9, 0.1], [1, 0]) == pytest.approx(math.log(0.9))


def test_log_score_clips_to_avoid_negative_infinity():
    # a confident wrong forecast must not return -inf (would poison any mean)
    s = scoring.log_score([0.0], [1])
    assert math.isfinite(s)
    assert s < math.log(0.9)


def test_brier_skill_score_zero_when_model_equals_climatology():
    outcomes = [0, 0, 1, 0, 0, 1, 0]  # 2/7 ~ climatology-ish
    clim = scoring.climatology_forecast(len(outcomes))
    assert scoring.brier_skill_score(clim, outcomes) == pytest.approx(0.0, abs=1e-9)


def test_brier_skill_score_positive_when_model_beats_climatology():
    outcomes = [0, 1, 0, 1]
    good = [0.05, 0.95, 0.05, 0.95]
    assert scoring.brier_skill_score(good, outcomes) > 0.0


def test_brier_skill_score_uses_base_rate_0155_by_default():
    assert scoring.CLIMATOLOGY_BASE_RATE == 0.155


# ---- reliability / ECE / sharpness ---------------------------------------

def test_reliability_diagram_bins_forecasts_and_reports_observed_frequency():
    probs = [0.05, 0.15, 0.85, 0.95]
    outcomes = [0, 0, 1, 1]
    diag = scoring.reliability_diagram(probs, outcomes, n_bins=2)
    # low bin all-0, high bin all-1 -> perfectly reliable
    lo = [b for b in diag if b["count"] and b["mean_forecast"] < 0.5][0]
    hi = [b for b in diag if b["count"] and b["mean_forecast"] >= 0.5][0]
    assert lo["observed_freq"] == 0.0
    assert hi["observed_freq"] == 1.0
    assert lo["count"] == 2 and hi["count"] == 2


def test_ece_zero_for_perfectly_calibrated_forecast():
    probs = [0.0, 0.0, 1.0, 1.0]
    outcomes = [0, 0, 1, 1]
    assert scoring.ece(probs, outcomes, n_bins=10) == pytest.approx(0.0)


def test_ece_positive_when_overconfident():
    # forecasts 0.9 but outcomes only half positive -> miscalibrated
    probs = [0.9, 0.9, 0.9, 0.9]
    outcomes = [1, 0, 1, 0]
    assert scoring.ece(probs, outcomes, n_bins=10) == pytest.approx(0.4)


def test_sharpness_is_variance_of_forecasts():
    probs = [0.2, 0.8]
    assert scoring.sharpness(probs) == pytest.approx(0.09)  # pvariance([.2,.8])


# ---- AUC reported but NEVER primary --------------------------------------

def test_auc_rank_metric_value():
    probs = [0.1, 0.4, 0.35, 0.8]
    outcomes = [0, 0, 1, 1]
    assert scoring.auc(probs, outcomes) == pytest.approx(0.75)


def test_evaluate_marks_auc_not_primary_and_names_a_proper_primary():
    res = scoring.evaluate([0.1, 0.9], [0, 1], has_asof_lane=True)
    assert res["auc_is_primary"] is False
    assert res["primary_metric"] in ("log_score", "brier_score")
    assert "auc" in res  # still reported, §19.4 no silent drop


# ---- mandatory baselines --------------------------------------------------

def test_climatology_forecast_is_constant_base_rate():
    assert scoring.climatology_forecast(3) == [0.155, 0.155, 0.155]


def test_persistence_forecast_carries_prior_state_forward():
    # forecast_t = state_{t-1}; first uses the supplied prior (default base rate)
    assert scoring.persistence_forecast([0, 1, 1]) == [0.155, 0.0, 1.0]


def test_beats_baselines_requires_beating_both_on_log_score():
    # higher log-score (closer to 0) is better
    assert scoring.beats_baselines(model=-0.20, climatology=-0.30, persistence=-0.25)[
        "is_improvement"] is True
    # ties/losses to either baseline are NOT an improvement
    assert scoring.beats_baselines(model=-0.30, climatology=-0.20, persistence=-0.40)[
        "is_improvement"] is False
    assert scoring.beats_baselines(model=-0.25, climatology=-0.30, persistence=-0.25)[
        "is_improvement"] is False


# ---- information-set switch -----------------------------------------------

def test_information_set_label_archive_when_asof_lane_exists():
    assert scoring.label_information_set(has_asof_lane=True) == "archive_snapshot_asof"


def test_information_set_label_pseudo_real_time_when_no_lane():
    assert scoring.label_information_set(has_asof_lane=False) == "pseudo_real_time"


def test_evaluate_emits_information_set_label_always():
    r1 = scoring.evaluate([0.2], [0], has_asof_lane=True)
    r2 = scoring.evaluate([0.2], [0], has_asof_lane=False)
    assert r1["information_set"] == "archive_snapshot_asof"
    assert r2["information_set"] == "pseudo_real_time"


# ---- decision-level metrics -----------------------------------------------

def test_crossing_date_error_signed_days_for_matched_crossings():
    pred = [dt.date(2008, 1, 10)]
    ref = [dt.date(2008, 1, 1)]
    errs = scoring.crossing_date_error(pred, ref, tolerance_days=90)
    assert errs == [9]  # predicted 9 days late


def test_false_and_missed_crossings_counted():
    pred = [dt.date(2000, 1, 1), dt.date(2008, 1, 1)]  # 2000 is spurious
    ref = [dt.date(2008, 1, 3), dt.date(2020, 2, 1)]   # 2020 missed
    assert scoring.false_crossings(pred, ref, tolerance_days=90) == 1
    assert scoring.missed_crossings(pred, ref, tolerance_days=90) == 1


def test_lead_time_distribution_summary_skips_misses():
    dist = scoring.lead_time_distribution([120, None, 30, 60])
    assert dist["n"] == 3
    assert dist["median"] == 60
    assert dist["min"] == 30 and dist["max"] == 120


# ---- leak detection: DETECTED and REFUSED ---------------------------------

def test_leaking_split_is_detected_and_refused():
    # the same recession episode appears in BOTH train and test -> leakage
    train = [{"label": "2008", "era": "post-2008"}]
    test = [{"label": "2008", "era": "post-2008"}]
    leaky = Split(train=train, test=test, held_out="post-2008")
    assert scoring.detect_leak(leaky) is True
    with pytest.raises(scoring.LeakageError):
        scoring.assert_no_leakage(leaky)


def test_clean_leave_one_recession_out_split_passes():
    train = [{"label": "1990", "era": "great-moderation"}]
    test = [{"label": "2008", "era": "post-2008"}]
    clean = Split(train=train, test=test, held_out="post-2008")
    assert scoring.detect_leak(clean) is False
    scoring.assert_no_leakage(clean)  # no raise


def test_leave_one_day_out_granularity_is_rejected():
    # days are ~250x oversampled; day-level CV reports a fantasy (brief step 1)
    with pytest.raises(ValueError):
        scoring.require_episode_granularity("day")
    # episode/recession/era granularities are accepted
    for g in ("recession", "episode", "era"):
        scoring.require_episode_granularity(g)


# ---- standard four eras (brief step 2) ------------------------------------

def test_standard_era_partitions_into_the_four_named_eras():
    assert scoring.standard_era(dt.date(1975, 1, 1)) == "pre-1984"
    assert scoring.standard_era(dt.date(1990, 1, 1)) == "great-moderation"
    assert scoring.standard_era(dt.date(2009, 6, 1)) == "post-2008"
    assert scoring.standard_era(dt.date(2020, 4, 1)) == "post-2020"
