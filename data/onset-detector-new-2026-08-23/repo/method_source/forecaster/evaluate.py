"""Complete episode, probability, calibration, and robustness scorecards."""

import datetime as dt
import math
import statistics
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

from .alerts import (
    AlertEpisode,
    PolicyPoint,
    build_policy_alert_episodes,
    match_alerts,
)
from .metrics import (
    brier_score,
    calibration_intercept_slope,
    expected_calibration_error,
    log_loss,
    pr_auc,
    roc_auc,
)
from .stress import era_partition, leave_one_episode_influence, placebo_episodes
from .targets import Episode, onset_label, shift_months
from .uncertainty import bootstrap_interval


UTC = dt.timezone.utc
PANDEMIC_EPISODE = "2020-02/2020-04"


def _finite(value: float) -> Optional[float]:
    return float(value) if math.isfinite(value) else None


def _point(day: str, probability: float, threshold: float) -> PolicyPoint:
    return PolicyPoint(
        dt.datetime.combine(dt.date.fromisoformat(day), dt.time.min, tzinfo=UTC),
        float(probability),
        float(threshold),
    )


def _confusion(labels: Sequence[int], predicted: Sequence[bool]) -> Dict[str, float]:
    tp = sum(label == 1 and value for label, value in zip(labels, predicted))
    tn = sum(label == 0 and not value for label, value in zip(labels, predicted))
    fp = sum(label == 0 and value for label, value in zip(labels, predicted))
    fn = sum(label == 1 and not value for label, value in zip(labels, predicted))
    sensitivity = tp / (tp + fn) if tp + fn else 0.0
    specificity = tn / (tn + fp) if tn + fp else 0.0
    precision = tp / (tp + fp) if tp + fp else 0.0
    denominator = math.sqrt((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
    mcc = (tp * tn - fp * fn) / denominator if denominator else 0.0
    f2_denominator = 4.0 * precision + sensitivity
    return {
        "sensitivity": sensitivity,
        "specificity": specificity,
        "balanced_accuracy": (sensitivity + specificity) / 2.0,
        "precision": precision,
        "mcc": mcc,
        "f2": 5.0 * precision * sensitivity / f2_denominator
        if f2_denominator else 0.0,
        "tp": tp,
        "tn": tn,
        "fp": fp,
        "fn": fn,
    }


def _probability_metrics(rows: Sequence[Mapping[str, object]]) -> Dict[str, object]:
    labels = [int(row["label"]) for row in rows]
    probabilities = [float(row["probability"]) for row in rows]
    thresholds = [float(row["threshold"]) for row in rows]
    prevalence = sum(labels) / len(labels)
    brier = brier_score(labels, probabilities)
    reference_brier = prevalence * (1.0 - prevalence)
    calibration = calibration_intercept_slope(labels, probabilities)
    result: Dict[str, object] = {
        "row_count": len(rows),
        "positive_row_count": sum(labels),
        "prevalence": prevalence,
        "roc_auc": _finite(roc_auc(labels, probabilities)),
        "pr_auc": _finite(pr_auc(labels, probabilities)),
        "brier": brier,
        "climatology_brier": reference_brier,
        "brier_skill": 1.0 - brier / reference_brier if reference_brier else None,
        "log_loss": log_loss(labels, probabilities),
        "calibration_intercept": _finite(calibration["intercept"]),
        "calibration_slope": _finite(calibration["slope"]),
        "expected_calibration_error": expected_calibration_error(
            labels, probabilities
        ),
        "sharpness_standard_deviation": statistics.pstdev(probabilities),
    }
    result.update(
        _confusion(
            labels,
            [
                probability >= threshold
                for probability, threshold in zip(probabilities, thresholds)
            ],
        )
    )
    return result


def _union_days(
    alerts: Sequence[AlertEpisode], start: dt.date, end: dt.date
) -> int:
    intervals: List[Tuple[dt.date, dt.date]] = []
    for alert in alerts:
        left = max(start, alert.start.date())
        right = min(end, alert.end.date())
        if left <= right:
            intervals.append((left, right))
    intervals.sort()
    merged: List[Tuple[dt.date, dt.date]] = []
    for left, right in intervals:
        if merged and left <= merged[-1][1] + dt.timedelta(days=1):
            merged[-1] = (merged[-1][0], max(merged[-1][1], right))
        else:
            merged.append((left, right))
    return sum((right - left).days + 1 for left, right in merged)


def _alert_payload(alert: AlertEpisode, late: bool = False) -> Dict[str, object]:
    return {
        "start": alert.start.isoformat(),
        "end": alert.end.isoformat(),
        "duration_days": alert.duration_days,
        "peak_probability": alert.peak_probability,
        "forecast_point_count": alert.point_count,
        "late_nowcast_or_detection": late,
    }


def _late_alert(alert: AlertEpisode, episodes: Sequence[Episode]) -> bool:
    return any(
        episode.onset <= alert.start.date() <= episode.trough_end
        for episode in episodes
    )


def _row_subset_metrics(
    rows: Sequence[Mapping[str, object]]
) -> Optional[Dict[str, object]]:
    if not rows or len({int(row["label"]) for row in rows}) < 2:
        return None
    return _probability_metrics(rows)


def _robustness(
    rows: Sequence[Mapping[str, object]],
    episodes: Sequence[Episode],
    horizon: int,
    data_cutoff: dt.date,
    caught: Mapping[str, float],
    seed: int,
) -> Dict[str, object]:
    labels = [int(row["label"]) for row in rows]
    probabilities = [float(row["probability"]) for row in rows]
    observed_auc = roc_auc(labels, probabilities)
    shuffled = []
    if len(set(labels)) == 2:
        import random

        generator = random.Random(seed + horizon)
        for _ in range(500):
            values = labels[:]
            generator.shuffle(values)
            shuffled.append(roc_auc(values, probabilities))
        shuffled.sort()
    placebo = placebo_episodes(episodes, 365)
    placebo_rows = []
    for row in rows:
        issue = dt.date.fromisoformat(str(row["issue_date"]))
        label = onset_label(issue, horizon, placebo, data_cutoff)
        if label is not None:
            placebo_rows.append({**row, "label": label})
    era_metrics = {}
    for era in ["pre_1984", "great_moderation_to_gfc", "post_2008"]:
        subset = [
            row
            for row in rows
            if era_partition(dt.date.fromisoformat(str(row["issue_date"]))) == era
        ]
        era_metrics[era] = _row_subset_metrics(subset)
    without_pandemic = [
        row
        for row in rows
        if str(row.get("target_episode", "")) != PANDEMIC_EPISODE
        and dt.date.fromisoformat(str(row["issue_date"])) < dt.date(2020, 2, 1)
    ]
    return {
        "shuffled_outcome_auc": {
            "permutations": len(shuffled),
            "observed": _finite(observed_auc),
            "null_mean": statistics.mean(shuffled) if shuffled else None,
            "null_p95": shuffled[int(0.95 * (len(shuffled) - 1))]
            if shuffled else None,
        },
        "placebo_onsets_shifted_365_days": _row_subset_metrics(placebo_rows),
        "pandemic_excluded": _row_subset_metrics(without_pandemic),
        "era_partitions": era_metrics,
        "leave_one_episode_recall": leave_one_episode_influence(caught)
        if len(caught) >= 2 else None,
    }


def evaluate_candidate(
    rows: Sequence[Mapping[str, object]],
    episodes: Sequence[Episode],
    horizon: int,
    data_cutoff: dt.date,
    seed: int = 20260722,
) -> Dict[str, object]:
    if not rows:
        return {
            "status": "unestablished_no_outer_predictions",
            "reason": "Training/vintage floors yielded no scoreable outer forecasts.",
            "row_metrics": None,
            "episode_metrics": None,
            "episodes": [],
            "false_alarms": [],
            "robustness": None,
            "joint_gate_pass": False,
        }
    ordered = sorted(rows, key=lambda row: str(row["issue_date"]))
    points = [
        _point(str(row["issue_date"]), row["probability"], row["threshold"])
        for row in ordered
    ]
    alerts = build_policy_alert_episodes(points)
    eligible_ids = {
        str(row["target_episode"])
        for row in ordered
        if str(row.get("target_episode", ""))
    }
    eligible = [episode for episode in episodes if episode.episode_id in eligible_ids]
    match = match_alerts(alerts, eligible, horizon)
    matches = {item.episode_id: item for item in match.matches}
    late_ids = {item.episode_id for item in match.late}
    matched_starts = {item.alert_start for item in match.matches}
    false_alerts = [alert for alert in alerts if alert.start not in matched_starts]
    episode_table = []
    caught: Dict[str, float] = {}
    for episode in eligible:
        target_rows = [
            row for row in ordered if row.get("target_episode") == episode.episode_id
        ]
        window_start = shift_months(episode.onset, -horizon)
        pre_onset = [
            row for row in ordered
            if window_start
            <= dt.date.fromisoformat(str(row["issue_date"]))
            < episode.onset
        ]
        item = matches.get(episode.episode_id)
        status = "caught" if item else "late" if episode.episode_id in late_ids else "missed"
        caught[episode.episode_id] = float(status == "caught")
        alert = next(
            (value for value in alerts if item and value.start == item.alert_start),
            None,
        )
        first_target = target_rows[0] if target_rows else {}
        episode_table.append(
            {
                "episode_id": episode.episode_id,
                "nber_peak_month": episode.peak_month,
                "onset_cutoff": episode.onset.isoformat(),
                "eligibility": "eligible_nested_outer_oos",
                "status": status,
                "training_start": first_target.get("training_start"),
                "training_end": first_target.get("training_end"),
                "training_rows": first_target.get("training_rows"),
                "training_positive_episodes": first_target.get(
                    "training_positive_episodes", []
                ),
                "first_valid_alert": item.alert_start.isoformat() if item else None,
                "lead_days": item.lead_days if item else None,
                "lead_months_approx": item.lead_days / 30.4375 if item else None,
                "probability_at_first_alert": item.probability if item else None,
                "maximum_pre_onset_probability": max(
                    (float(row["probability"]) for row in pre_onset), default=None
                ),
                "data_vintage_cutoff": item.alert_start.isoformat() if item else None,
                "alert_duration_days": alert.duration_days if alert else None,
                "contributing_channels": "No post-hoc episode attribution is claimed.",
                "uncertainty": "Episode count is below the registered interval floor."
                if len(eligible) < 8 else "See episode-aware interval.",
                "caveat": "Historical evidence was inspected previously and is not an untouched holdout.",
            }
        )
    early = [
        {
            "episode_id": episode.episode_id,
            "nber_peak_month": episode.peak_month,
            "eligibility": "ineligible_training_or_coverage_floor",
        }
        for episode in episodes
        if episode.onset <= data_cutoff and episode.episode_id not in eligible_ids
    ]
    row_metrics = _probability_metrics(ordered)
    start = dt.date.fromisoformat(str(ordered[0]["issue_date"]))
    end = dt.date.fromisoformat(str(ordered[-1]["issue_date"]))
    warning_days = _union_days(alerts, start, end)
    eligible_days = (end - start).days + 1
    leads = [item.lead_days for item in match.matches]
    recall = len(match.matches) / len(eligible) if eligible else 0.0
    precision = len(match.matches) / len(alerts) if alerts else 0.0
    false_duration = sum(item.duration_days for item in false_alerts)
    years = eligible_days / 365.25
    costs = {
        "miss": 10.0,
        "false_alarm_start": 3.0,
        "false_alarm_month": 1.0,
        "late_per_30_days": 1.0,
        "late_cap": 3.0,
        "churn_after_second": 0.5,
        "churn_cap": 2.0,
    }
    misses = len(eligible) - len(match.matches)
    churn = min(costs["churn_cap"], max(0, len(alerts) - 2) * costs["churn_after_second"])
    base_loss = (
        misses * costs["miss"]
        + len(false_alerts) * costs["false_alarm_start"]
        + false_duration / 30.4375 * costs["false_alarm_month"]
        + len(late_ids) * costs["late_per_30_days"]
        + churn
    ) / max(1, len(eligible))
    support = len(eligible_ids)
    slope = row_metrics["calibration_slope"]
    intercept = row_metrics["calibration_intercept"]
    calibration_gate = bool(
        support >= 3
        and slope is not None
        and 0.8 <= slope <= 1.25
        and intercept is not None
        and abs(intercept) <= 0.3
    )
    episode_metrics = {
        "eligible_episode_count": len(eligible),
        "caught_episode_count": len(match.matches),
        "missed_episode_count": sum(item["status"] == "missed" for item in episode_table),
        "late_episode_count": sum(item["status"] == "late" for item in episode_table),
        "episode_recall": recall,
        "episode_precision": precision,
        "alert_episode_count": len(alerts),
        "false_alarm_episode_count": len(false_alerts),
        "false_alarm_episodes_per_decade": len(false_alerts) / years * 10.0,
        "false_alarm_duration_days": false_duration,
        "time_under_warning_days": warning_days,
        "time_under_warning_fraction": warning_days / eligible_days,
        "lead_days": leads,
        "median_lead_days": statistics.median(leads) if leads else None,
        "mean_lead_days": statistics.mean(leads) if leads else None,
        "minimum_lead_days": min(leads) if leads else None,
        "warning_churn_alert_starts": len(alerts),
        "average_alert_duration_days": statistics.mean(
            [item.duration_days for item in alerts]
        ) if alerts else 0.0,
        "expected_loss": base_loss,
        "cost_sensitivity": [
            {
                "miss_cost": miss_cost,
                "false_alarm_start_cost": 3.0,
                "expected_loss": (
                    misses * miss_cost
                    + len(false_alerts) * 3.0
                    + false_duration / 30.4375
                    + len(late_ids)
                    + churn
                ) / max(1, len(eligible)),
            }
            for miss_cost in [20.0, 10.0, 5.0]
        ],
        "episode_recall_interval_90": bootstrap_interval(
            list(caught.values()), seed=seed
        ),
        "interval_status": "available" if len(caught) >= 8 else "refused_below_8_units",
    }
    brier_skill = row_metrics["brier_skill"]
    joint_gate = bool(
        recall >= 0.95
        and precision >= 0.5
        and episode_metrics["false_alarm_episodes_per_decade"] <= 1.0
        and episode_metrics["time_under_warning_fraction"] <= 0.25
        and episode_metrics["median_lead_days"] is not None
        and episode_metrics["median_lead_days"] >= 30
        and brier_skill is not None
        and brier_skill > 0.0
        and calibration_gate
    )
    return {
        "status": "evaluated_contaminated_nested_oos",
        "coverage": {
            "first_issue": start.isoformat(),
            "last_issue": end.isoformat(),
            "elapsed_days": eligible_days,
            "ineligible_episodes": early,
        },
        "row_metrics": row_metrics,
        "episode_metrics": episode_metrics,
        "calibration_gate_pass": calibration_gate,
        "episodes": episode_table,
        "false_alarms": [
            _alert_payload(alert, _late_alert(alert, eligible))
            for alert in false_alerts
        ],
        "robustness": _robustness(
            ordered, eligible, horizon, data_cutoff, caught, seed
        ),
        "joint_gate_pass": joint_gate,
        "prospective_confirmation_complete": False,
        "deployment_eligible": False,
    }


def evaluate_backtest(
    backtest: Mapping[str, object],
    episodes: Sequence[Episode],
    data_cutoff: dt.date,
    seed: int = 20260722,
) -> Dict[str, object]:
    result: Dict[str, object] = {
        "schema": "bh.forecaster.scorecard.v1",
        "mode": backtest["mode"],
        "historical_evidence_status": "contaminated_nested_oos",
        "horizons": {},
        "selection": {},
    }
    for horizon_key, families in backtest["horizons"].items():
        scored = {
            family: evaluate_candidate(
                rows, episodes, int(horizon_key), data_cutoff, seed
            )
            for family, rows in families.items()
        }
        result["horizons"][horizon_key] = scored
        candidates = [
            (
                score["episode_metrics"]["expected_loss"],
                0 if family == "term_spread_logit" else 1,
                family,
            )
            for family, score in scored.items()
            if score["episode_metrics"] is not None
        ]
        result["selection"][horizon_key] = min(candidates)[2] if candidates else None
    selected_scores = [
        result["horizons"][horizon][family]
        for horizon, family in result["selection"].items()
        if family is not None
    ]
    result["historical_joint_gate_pass"] = bool(
        selected_scores and all(item["joint_gate_pass"] for item in selected_scores)
    )
    result["prospective_confirmation_complete"] = False
    result["deployment_eligible"] = False
    result["claim"] = (
        "No prospective reliability claim. Historical results are contaminated "
        "nested walk-forward evidence only."
    )
    return result
