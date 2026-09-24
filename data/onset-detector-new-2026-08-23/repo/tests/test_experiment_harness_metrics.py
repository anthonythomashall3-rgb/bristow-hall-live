"""RED-first tests for the pre-registered metric computer (B-EXP-0 deliverable 3).

These metrics are coded ONCE and pre-registered against SCIENCE_DOCKET_v1 S10 (the
2022 A/B experiment criteria) and S22 (the value-stream bake-off). The harness adopts
NOTHING: it scores whatever candidate rule output the caller passes in.
"""
import datetime as dt

from contrib.experiment_harness import metrics


def test_detection_lead_positive_when_signal_precedes_peak():
    # S10 criterion (4): detection lead on held-out historical episodes, as-of.
    onset = dt.date(2007, 8, 1)
    peak = dt.date(2007, 12, 1)
    assert metrics.detection_lead(onset, peak) == 122  # days peak - onset


def test_detection_lead_negative_when_signal_lags_peak():
    onset = dt.date(2008, 3, 1)
    peak = dt.date(2007, 12, 1)
    assert metrics.detection_lead(onset, peak) == -91


def test_detection_lead_none_when_never_fired():
    assert metrics.detection_lead(None, dt.date(2007, 12, 1)) is None


def test_false_alarm_rate_counts_windows_with_any_firing():
    # S10 criterion (2): false-positive rate on measured non-episodes (1966/1995/2015-16).
    firings = [dt.date(1995, 6, 1), dt.date(2016, 2, 1)]
    windows = [
        (dt.date(1966, 1, 1), dt.date(1966, 12, 31)),   # no firing
        (dt.date(1995, 1, 1), dt.date(1995, 12, 31)),   # fired
        (dt.date(2015, 1, 1), dt.date(2016, 12, 31)),   # fired
    ]
    assert metrics.false_alarm_rate(firings, windows) == 2 / 3


def test_false_alarm_rate_zero_when_no_firings():
    windows = [(dt.date(1995, 1, 1), dt.date(1995, 12, 31))]
    assert metrics.false_alarm_rate([], windows) == 0.0


def test_false_alarm_rate_empty_windows_is_none():
    assert metrics.false_alarm_rate([dt.date(1995, 6, 1)], []) is None


def test_boundary_stability_returns_bootstrap_variance():
    # S10 criterion (1): which threshold set is stabler (bootstrap variance of boundaries).
    samples = [10.0, 12.0, 14.0]  # mean 12, population variance 8/3
    assert abs(metrics.boundary_stability(samples) - (8.0 / 3.0)) < 1e-9


def test_boundary_stability_single_sample_is_zero():
    assert metrics.boundary_stability([5.0]) == 0.0


def test_boundary_stability_lower_variance_is_more_stable():
    tight = metrics.boundary_stability([10.0, 10.5, 11.0])
    loose = metrics.boundary_stability([5.0, 12.0, 20.0])
    assert tight < loose


def test_era_consistency_agreement_fraction_and_disagreements():
    # S10 criterion (3): rule fit excluding 2020s must admit/exclude 2022 the same way.
    full = {"2022": "disturbance", "2008": "recession", "2001": "recession"}
    excl = {"2022": "recession", "2008": "recession", "2001": "recession"}
    res = metrics.era_consistency(full, excl)
    assert res["agreement"] == 2 / 3
    assert res["disagreements"] == ["2022"]
    assert res["consistent"] is False


def test_era_consistency_full_agreement():
    full = {"2022": "disturbance", "2008": "recession"}
    res = metrics.era_consistency(full, dict(full))
    assert res["agreement"] == 1.0
    assert res["consistent"] is True
    assert res["disagreements"] == []


def test_detection_scorecard_aggregates_preregistered_metrics():
    # S22 bake-off: score a route on as-of detection metrics, one aggregate object.
    card = metrics.detection_scorecard(
        leads={"2008": 122, "2001": 60, "2020": None},
        firings=[dt.date(1995, 6, 1)],
        nonepisode_windows=[
            (dt.date(1966, 1, 1), dt.date(1966, 12, 31)),
            (dt.date(1995, 1, 1), dt.date(1995, 12, 31)),
        ],
        boundary_samples=[10.0, 12.0, 14.0],
    )
    assert card["median_lead"] == 91.0            # median of [122, 60]
    assert card["n_detected"] == 2
    assert card["n_missed"] == 1
    assert card["false_alarm_rate"] == 0.5
    assert abs(card["boundary_stability"] - (8.0 / 3.0)) < 1e-9
