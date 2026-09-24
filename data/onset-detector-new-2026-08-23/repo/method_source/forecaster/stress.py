"""Falsification and episode-influence helpers."""

import dataclasses
import datetime as dt
import random
from typing import Dict, List, Mapping, Sequence

from .metrics import roc_auc
from .targets import Episode


def shuffled_auc_distribution(
    labels: Sequence[int],
    probabilities: Sequence[float],
    permutations: int,
    seed: int,
) -> List[float]:
    generator = random.Random(seed)
    values = list(labels)
    result = []
    for _ in range(permutations):
        shuffled = values[:]
        generator.shuffle(shuffled)
        result.append(roc_auc(shuffled, probabilities))
    return result


def placebo_episodes(
    episodes: Sequence[Episode], shift_days: int
) -> List[Episode]:
    delta = dt.timedelta(days=shift_days)
    return [
        dataclasses.replace(
            episode,
            episode_id=f"placebo-{episode.episode_id}",
            peak_month=(episode.onset + delta).strftime("%Y-%m"),
            onset=episode.onset + delta,
            trough_end=episode.trough_end + delta,
            announced_at=(
                episode.announced_at + delta if episode.announced_at is not None else None
            ),
        )
        for episode in episodes
    ]


def exclude_episode(
    episodes: Sequence[Episode], episode_id: str
) -> List[Episode]:
    return [episode for episode in episodes if episode.episode_id != episode_id]


def leave_one_episode_influence(
    caught: Mapping[str, float]
) -> Dict[str, float]:
    if len(caught) < 2:
        raise ValueError("at least two episodes are required")
    return {
        omitted: sum(value for key, value in caught.items() if key != omitted)
        / (len(caught) - 1)
        for omitted in caught
    }


def era_partition(day: dt.date) -> str:
    if day < dt.date(1984, 1, 1):
        return "pre_1984"
    if day < dt.date(2008, 1, 1):
        return "great_moderation_to_gfc"
    return "post_2008"
