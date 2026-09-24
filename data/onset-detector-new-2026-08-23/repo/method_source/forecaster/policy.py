"""Training-only probability-threshold selection."""

import dataclasses
from typing import Iterable, Sequence


@dataclasses.dataclass(frozen=True)
class ThresholdSelection:
    threshold: float
    expected_loss: float
    warning_fraction: float
    misses: int
    false_positives: int


def select_threshold(
    labels: Sequence[int],
    probabilities: Sequence[float],
    thresholds: Iterable[float],
    miss_cost: float = 10.0,
    false_positive_cost: float = 3.0,
    warning_fraction_cost: float = 1.0,
) -> ThresholdSelection:
    if len(labels) != len(probabilities) or not labels:
        raise ValueError("labels and probabilities must be nonempty and equal length")
    candidates = []
    for threshold in thresholds:
        predicted = [value >= threshold for value in probabilities]
        misses = sum(label == 1 and not prediction for label, prediction in zip(labels, predicted))
        false_positives = sum(
            label == 0 and prediction for label, prediction in zip(labels, predicted)
        )
        warning_fraction = sum(predicted) / len(predicted)
        loss = (
            misses * miss_cost
            + false_positives * false_positive_cost
            + warning_fraction * warning_fraction_cost
        ) / len(labels)
        candidates.append(
            ThresholdSelection(
                float(threshold),
                float(loss),
                float(warning_fraction),
                misses,
                false_positives,
            )
        )
    if not candidates:
        raise ValueError("at least one threshold is required")
    return min(candidates, key=lambda value: (value.expected_loss, value.warning_fraction, -value.threshold))
