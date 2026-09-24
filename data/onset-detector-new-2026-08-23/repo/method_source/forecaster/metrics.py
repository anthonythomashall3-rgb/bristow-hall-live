"""Dependency-light probability and classification metrics."""

import math
from typing import Dict, Sequence

import numpy as np


EPSILON = 1e-12


def _check(labels: Sequence[int], probabilities: Sequence[float]) -> None:
    if len(labels) != len(probabilities) or not labels:
        raise ValueError("labels/probabilities must be nonempty and equal length")
    if any(label not in (0, 1) for label in labels):
        raise ValueError("labels must be binary")
    if any(not 0.0 <= value <= 1.0 for value in probabilities):
        raise ValueError("probabilities outside [0,1]")


def roc_auc(labels: Sequence[int], probabilities: Sequence[float]) -> float:
    _check(labels, probabilities)
    positive = [value for label, value in zip(labels, probabilities) if label]
    negative = [value for label, value in zip(labels, probabilities) if not label]
    if not positive or not negative:
        return float("nan")
    wins = sum(
        1.0 if pos > neg else 0.5 if pos == neg else 0.0
        for pos in positive for neg in negative
    )
    return wins / (len(positive) * len(negative))


def pr_auc(labels: Sequence[int], probabilities: Sequence[float]) -> float:
    _check(labels, probabilities)
    positives = sum(labels)
    if positives == 0:
        return float("nan")
    ordered = sorted(zip(probabilities, labels), reverse=True)
    true_positive = 0
    precision_sum = 0.0
    for rank, (_, label) in enumerate(ordered, start=1):
        if label:
            true_positive += 1
            precision_sum += true_positive / rank
    return precision_sum / positives


def brier_score(labels: Sequence[int], probabilities: Sequence[float]) -> float:
    _check(labels, probabilities)
    return sum((probability - label) ** 2 for label, probability in zip(labels, probabilities)) / len(labels)


def log_loss(labels: Sequence[int], probabilities: Sequence[float]) -> float:
    _check(labels, probabilities)
    total = 0.0
    for label, probability in zip(labels, probabilities):
        value = min(max(probability, EPSILON), 1.0 - EPSILON)
        total -= label * math.log(value) + (1 - label) * math.log(1.0 - value)
    return total / len(labels)


def binary_metrics(
    labels: Sequence[int], probabilities: Sequence[float], threshold: float = 0.5
) -> Dict[str, float]:
    _check(labels, probabilities)
    predicted = [int(value >= threshold) for value in probabilities]
    tp = sum(label == 1 and pred == 1 for label, pred in zip(labels, predicted))
    tn = sum(label == 0 and pred == 0 for label, pred in zip(labels, predicted))
    fp = sum(label == 0 and pred == 1 for label, pred in zip(labels, predicted))
    fn = sum(label == 1 and pred == 0 for label, pred in zip(labels, predicted))
    sensitivity = tp / (tp + fn) if tp + fn else 0.0
    specificity = tn / (tn + fp) if tn + fp else 0.0
    precision = tp / (tp + fp) if tp + fp else 0.0
    denominator = math.sqrt((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
    mcc = (tp * tn - fp * fn) / denominator if denominator else 0.0
    beta2 = 4.0
    f2 = (
        (1.0 + beta2) * precision * sensitivity
        / (beta2 * precision + sensitivity)
        if beta2 * precision + sensitivity
        else 0.0
    )
    return {
        "sensitivity": sensitivity,
        "specificity": specificity,
        "balanced_accuracy": (sensitivity + specificity) / 2.0,
        "precision": precision,
        "mcc": mcc,
        "f2": f2,
        "tp": float(tp),
        "tn": float(tn),
        "fp": float(fp),
        "fn": float(fn),
    }


def calibration_intercept_slope(
    labels: Sequence[int], probabilities: Sequence[float]
) -> Dict[str, float]:
    """Fit observed outcomes on logit(prediction) without recalibrating scores."""
    _check(labels, probabilities)
    if len(set(labels)) < 2:
        return {"intercept": float("nan"), "slope": float("nan")}
    clipped = np.clip(np.asarray(probabilities, dtype=float), 1e-6, 1.0 - 1e-6)
    logits = np.log(clipped / (1.0 - clipped))
    design = np.column_stack([np.ones(len(logits)), logits])
    target = np.asarray(labels, dtype=float)
    beta = np.array([math.log(target.mean() / (1.0 - target.mean())), 1.0])
    for _ in range(80):
        linear = np.clip(design @ beta, -35.0, 35.0)
        fitted = 1.0 / (1.0 + np.exp(-linear))
        gradient = design.T @ (target - fitted)
        weights = np.maximum(fitted * (1.0 - fitted), 1e-8)
        hessian = design.T @ (design * weights[:, None])
        try:
            step = np.linalg.solve(hessian, gradient)
        except np.linalg.LinAlgError:
            step = np.linalg.pinv(hessian) @ gradient
        beta += step
        if float(np.max(np.abs(step))) < 1e-8:
            break
    return {"intercept": float(beta[0]), "slope": float(beta[1])}


def expected_calibration_error(
    labels: Sequence[int], probabilities: Sequence[float], bins: int = 10
) -> float:
    _check(labels, probabilities)
    if bins < 2:
        raise ValueError("bins must be at least two")
    total = len(labels)
    error = 0.0
    for index in range(bins):
        low = index / bins
        high = (index + 1) / bins
        selected = [
            (label, probability)
            for label, probability in zip(labels, probabilities)
            if low <= probability < high or (index == bins - 1 and probability == 1.0)
        ]
        if not selected:
            continue
        observed = sum(label for label, _ in selected) / len(selected)
        forecast = sum(probability for _, probability in selected) / len(selected)
        error += len(selected) / total * abs(observed - forecast)
    return error
