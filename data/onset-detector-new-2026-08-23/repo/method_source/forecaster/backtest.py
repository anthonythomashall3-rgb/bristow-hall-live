"""Purged expanding-window helpers and deterministic nested model fitting."""

import datetime as dt
import dataclasses
import hashlib
import json
from typing import Any, Dict, List, Sequence, Tuple

import numpy as np

from .features import FeatureDataset
from .metrics import brier_score
from .models import (
    IdentityCalibrator,
    LogisticFit,
    PlattCalibrator,
    fit_logistic,
)
from .policy import select_threshold
from .releases import nber_peak_known
from .registry import spec_hash
from .targets import Episode, horizon_end, onset_label


def outcome_closed_at(
    issue_date: dt.date, horizon_months: int, embargo_days: int
) -> dt.date:
    return horizon_end(issue_date, horizon_months) + dt.timedelta(days=embargo_days)


def eligible_training_indices(
    issue_dates: Sequence[dt.date],
    outer_origin: dt.date,
    horizon_months: int,
    embargo_days: int = 21,
) -> List[int]:
    return [
        index
        for index, issue_date in enumerate(issue_dates)
        if issue_date < outer_origin
        and outcome_closed_at(issue_date, horizon_months, embargo_days) <= outer_origin
    ]


eligible_training_indices.outcome_closed_at = outcome_closed_at


def expanding_inner_splits(
    size: int, minimum_train: int, folds: int = 4
) -> List[Tuple[List[int], List[int]]]:
    if size <= minimum_train or minimum_train < 2 or folds < 2:
        return []
    remaining = size - minimum_train
    width = max(1, remaining // folds)
    result = []
    train_end = minimum_train
    while train_end < size:
        validation_end = min(size, train_end + width)
        if validation_end <= train_end:
            break
        result.append((list(range(train_end)), list(range(train_end, validation_end))))
        train_end = validation_end
    return result


def synthetic_walk_forward(
    issue_dates: Sequence[dt.date],
    values: np.ndarray,
    labels: np.ndarray,
    minimum_train: int,
    seed: int,
) -> Dict[str, object]:
    matrix = np.asarray(values, dtype=float)
    target = np.asarray(labels, dtype=float)
    if len(issue_dates) != len(matrix) or len(matrix) != len(target):
        raise ValueError("synthetic inputs must have equal length")
    predictions = []
    for index in range(minimum_train, len(issue_dates)):
        model = fit_logistic(matrix[:index], target[:index], l2=1.0, positive_weight=2.0)
        probability = float(model.predict_proba(matrix[index:index + 1])[0])
        predictions.append(
            {
                "issue_date": issue_dates[index].isoformat(),
                "probability": round(probability, 12),
                "label": int(target[index]),
            }
        )
    payload = {"seed": seed, "minimum_train": minimum_train, "predictions": predictions}
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    payload["artifact_hash"] = digest
    return payload


@dataclasses.dataclass(frozen=True)
class FamilyBundle:
    family: str
    raw_model: Any
    calibrator: Any
    threshold: float
    parameters: Dict[str, float]
    inner_brier: float
    spec_digest: str

    def predict(self, values: np.ndarray) -> float:
        raw = _predict_raw(self.family, self.raw_model, values.reshape(1, -1))
        return float(self.calibrator.transform(raw)[0])


def _parameter_grid(family: str) -> List[Dict[str, float]]:
    if family in {"climatology", "persistence"}:
        return [{}]
    if family in {"term_spread_logit", "ridge_channel_logit"}:
        return [
            {"l2": l2, "positive_weight": weight}
            for l2 in [0.1, 1.0, 10.0]
            for weight in [1.0, 2.0, 5.0]
        ]
    raise ValueError(f"unknown model family {family}")


def _family_matrix(family: str, values: np.ndarray) -> np.ndarray:
    matrix = np.asarray(values, dtype=float)
    if family == "term_spread_logit":
        return matrix[:, :1]
    return matrix


def _fit_raw(
    family: str, values: np.ndarray, labels: np.ndarray, parameters: Dict[str, float]
) -> Any:
    if family == "climatology":
        return float(np.clip(labels.mean(), 1e-6, 1.0 - 1e-6))
    if family == "persistence":
        prevalence = float(np.clip(labels.mean(), 1e-6, 1.0 - 1e-6))
        return prevalence, float(labels[-1])
    return fit_logistic(
        _family_matrix(family, values),
        labels,
        l2=parameters["l2"],
        positive_weight=parameters["positive_weight"],
    )


def _predict_raw(family: str, raw_model: Any, values: np.ndarray) -> np.ndarray:
    if family == "climatology":
        return np.full(len(values), raw_model, dtype=float)
    if family == "persistence":
        prevalence, last_label = raw_model
        return np.full(
            len(values),
            np.clip(0.25 * prevalence + 0.75 * last_label, 1e-6, 1.0 - 1e-6),
            dtype=float,
        )
    if not isinstance(raw_model, LogisticFit):
        raise TypeError("logistic family missing LogisticFit")
    return raw_model.predict_proba(_family_matrix(family, values))


def _inner_predictions(
    family: str,
    values: np.ndarray,
    labels: np.ndarray,
    parameters: Dict[str, float],
) -> Tuple[np.ndarray, np.ndarray]:
    minimum = max(24, int(len(values) * 0.55))
    splits = expanding_inner_splits(len(values), minimum_train=minimum, folds=4)
    probabilities = []
    outcomes = []
    for train_indices, validation_indices in splits:
        train = np.array(train_indices, dtype=int)
        validation = np.array(validation_indices, dtype=int)
        model = _fit_raw(family, values[train], labels[train], parameters)
        probabilities.extend(_predict_raw(family, model, values[validation]))
        outcomes.extend(labels[validation])
    if not probabilities:
        raise ValueError("insufficient rows for expanding inner validation")
    return np.asarray(probabilities, dtype=float), np.asarray(outcomes, dtype=float)


def fit_family_bundle(
    family: str,
    values: np.ndarray,
    labels: np.ndarray,
    threshold_grid: Sequence[float] = (0.1, 0.15, 0.2, 0.25, 0.3, 0.4, 0.5),
) -> FamilyBundle:
    matrix = np.asarray(values, dtype=float)
    target = np.asarray(labels, dtype=float)
    if len(matrix) < 40 or len(np.unique(target)) < 2:
        raise ValueError("family fit requires 40 rows and both classes")
    scored = []
    inner_cache = {}
    for parameters in _parameter_grid(family):
        probabilities, outcomes = _inner_predictions(
            family, matrix, target, parameters
        )
        score = brier_score(outcomes.astype(int).tolist(), probabilities.tolist())
        key = json.dumps(parameters, sort_keys=True)
        inner_cache[key] = (probabilities, outcomes)
        scored.append((score, len(parameters), key, parameters))
    _, _, key, selected = min(scored)
    raw_inner, inner_labels = inner_cache[key]
    calibrator: Any = IdentityCalibrator()
    calibrated_inner = calibrator.transform(raw_inner)
    if len(raw_inner) >= 20 and len(np.unique(inner_labels)) == 2:
        split = len(raw_inner) // 2
        if len(np.unique(inner_labels[:split])) == 2 and len(np.unique(inner_labels[split:])) == 2:
            trial = PlattCalibrator.fit(raw_inner[:split], inner_labels[:split])
            trial_score = brier_score(
                inner_labels[split:].astype(int).tolist(),
                trial.transform(raw_inner[split:]).tolist(),
            )
            identity_score = brier_score(
                inner_labels[split:].astype(int).tolist(), raw_inner[split:].tolist()
            )
            if trial_score + 1e-6 < identity_score:
                calibrator = PlattCalibrator.fit(raw_inner, inner_labels)
                calibrated_inner = calibrator.transform(raw_inner)
    threshold = select_threshold(
        inner_labels.astype(int).tolist(),
        calibrated_inner.tolist(),
        threshold_grid,
    )
    raw_model = _fit_raw(family, matrix, target, selected)
    specification = {
        "family": family,
        "parameters": selected,
        "calibration": calibrator.as_dict(),
        "threshold": threshold.threshold,
        "training_rows": len(matrix),
    }
    return FamilyBundle(
        family=family,
        raw_model=raw_model,
        calibrator=calibrator,
        threshold=threshold.threshold,
        parameters=selected,
        inner_brier=brier_score(
            inner_labels.astype(int).tolist(), calibrated_inner.tolist()
        ),
        spec_digest=spec_hash(specification),
    )


def _target_episode(
    issue_date: dt.date, horizon_months: int, episodes: Sequence[Episode]
) -> str:
    end = horizon_end(issue_date, horizon_months)
    for episode in episodes:
        if issue_date < episode.onset <= end:
            return episode.episode_id
    return ""


def _months_between(earlier: dt.date, later: dt.date) -> int:
    return (later.year - earlier.year) * 12 + later.month - earlier.month


def run_nested_backtest(
    dataset: FeatureDataset,
    episodes: Sequence[Episode],
    data_cutoff: dt.date,
    horizons: Sequence[int],
    families: Sequence[str],
    minimum_training_years: int = 15,
    minimum_training_episodes: int = 3,
    refit_months: int = 3,
) -> Dict[str, object]:
    issues = dataset.issue_dates()
    values = dataset.matrix()
    output: Dict[str, object] = {
        "schema": "bh.forecaster.backtest.v1",
        "mode": dataset.mode,
        "feature_names": dataset.feature_names,
        "skipped_issue_count": len(dataset.skipped),
        "horizons": {},
    }
    for horizon in horizons:
        labels = [
            onset_label(issue, horizon, episodes, data_cutoff)
            for issue in issues
        ]
        target_ids = [
            _target_episode(issue, horizon, episodes) if label == 1 else ""
            for issue, label in zip(issues, labels)
        ]
        horizon_result = {}
        for family in families:
            predictions = []
            bundle = None
            last_refit = None
            for outer_index, outer_issue in enumerate(issues):
                if labels[outer_index] is None:
                    continue
                candidates = eligible_training_indices(
                    issues, outer_issue, horizon, embargo_days=21
                )
                train_indices = []
                for index in candidates:
                    if labels[index] is None:
                        continue
                    target_id = target_ids[index]
                    if target_id:
                        episode = next(
                            item for item in episodes if item.episode_id == target_id
                        )
                        if not nber_peak_known(episode.peak_month, dt.datetime.combine(
                            outer_issue, dt.time.min, tzinfo=dt.timezone.utc
                        )):
                            continue
                    train_indices.append(index)
                if not train_indices:
                    continue
                train_span_days = (
                    issues[train_indices[-1]] - issues[train_indices[0]]
                ).days
                positive_episodes = {
                    target_ids[index] for index in train_indices if target_ids[index]
                }
                if train_span_days < int(minimum_training_years * 365.25):
                    continue
                if len(positive_episodes) < minimum_training_episodes:
                    continue
                needs_refit = (
                    bundle is None
                    or last_refit is None
                    or _months_between(last_refit, outer_issue) >= refit_months
                )
                if needs_refit:
                    index_array = np.array(train_indices, dtype=int)
                    try:
                        bundle = fit_family_bundle(
                            family,
                            values[index_array],
                            np.array([labels[index] for index in train_indices], dtype=float),
                        )
                    except ValueError:
                        bundle = None
                        continue
                    last_refit = outer_issue
                probability = bundle.predict(values[outer_index])
                predictions.append(
                    {
                        "issue_date": outer_issue.isoformat(),
                        "probability": round(probability, 12),
                        "label": int(labels[outer_index]),
                        "target_episode": target_ids[outer_index],
                        "threshold": bundle.threshold,
                        "spec_hash": bundle.spec_digest,
                        "inner_brier": bundle.inner_brier,
                        "training_rows": len(train_indices),
                        "training_start": issues[train_indices[0]].isoformat(),
                        "training_end": issues[train_indices[-1]].isoformat(),
                        "training_positive_episodes": sorted(positive_episodes),
                    }
                )
            horizon_result[family] = predictions
        output["horizons"][str(horizon)] = horizon_result
    enforce_horizon_coherence(output)
    canonical = json.dumps(output, sort_keys=True, separators=(",", ":"))
    output["artifact_hash"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return output


def enforce_horizon_coherence(result: Dict[str, object]) -> None:
    horizons = sorted(int(value) for value in result["horizons"])
    families = sorted(
        {
            family
            for horizon in result["horizons"].values()
            for family in horizon
        }
    )
    for family in families:
        by_issue: Dict[str, List[Tuple[int, Dict[str, object]]]] = {}
        for horizon in horizons:
            for row in result["horizons"][str(horizon)].get(family, []):
                by_issue.setdefault(row["issue_date"], []).append((horizon, row))
        for rows in by_issue.values():
            maximum = 0.0
            for _, row in sorted(rows):
                maximum = max(maximum, float(row["probability"]))
                row["probability"] = round(maximum, 12)
