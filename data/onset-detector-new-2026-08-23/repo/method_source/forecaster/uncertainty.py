"""Episode-aware uncertainty helpers with registered support floors."""

import random
from typing import Callable, Optional, Sequence, Tuple


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values)


def bootstrap_interval(
    episode_values: Sequence[float],
    statistic: Callable[[Sequence[float]], float] = _mean,
    resamples: int = 2000,
    seed: int = 20260722,
    confidence: float = 0.9,
    minimum_units: int = 8,
) -> Optional[Tuple[float, float]]:
    if len(episode_values) < minimum_units:
        return None
    if resamples <= 0:
        raise ValueError("resamples must be positive")
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence must be inside (0,1)")
    generator = random.Random(seed)
    values = list(episode_values)
    samples = []
    for _ in range(resamples):
        draw = [generator.choice(values) for _ in values]
        samples.append(float(statistic(draw)))
    samples.sort()
    tail = (1.0 - confidence) / 2.0
    low_index = max(0, min(len(samples) - 1, int(tail * len(samples))))
    high_index = max(
        0, min(len(samples) - 1, int((1.0 - tail) * len(samples)) - 1)
    )
    return samples[low_index], samples[high_index]
