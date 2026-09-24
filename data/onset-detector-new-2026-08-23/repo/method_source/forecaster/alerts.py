"""Alert-state construction and one-to-one episode matching."""

import dataclasses
import datetime as dt
from typing import List, Sequence

from .targets import Episode, shift_months


@dataclasses.dataclass(frozen=True)
class ForecastPoint:
    issued_at: dt.datetime
    probability: float

    def __post_init__(self) -> None:
        if self.issued_at.tzinfo is None or self.issued_at.utcoffset() is None:
            raise ValueError("issued_at must be timezone-aware")
        if not 0.0 <= self.probability <= 1.0:
            raise ValueError("probability outside [0,1]")


@dataclasses.dataclass(frozen=True)
class PolicyPoint:
    issued_at: dt.datetime
    probability: float
    threshold: float

    def __post_init__(self) -> None:
        if self.issued_at.tzinfo is None or self.issued_at.utcoffset() is None:
            raise ValueError("issued_at must be timezone-aware")
        if not 0.0 <= self.probability <= 1.0:
            raise ValueError("probability outside [0,1]")
        if not 0.0 < self.threshold <= 1.0:
            raise ValueError("threshold outside (0,1]")


@dataclasses.dataclass(frozen=True)
class AlertEpisode:
    start: dt.datetime
    end: dt.datetime
    peak_probability: float
    point_count: int

    @property
    def duration_days(self) -> int:
        return max(1, (self.end.date() - self.start.date()).days + 1)


@dataclasses.dataclass(frozen=True)
class EpisodeMatch:
    episode_id: str
    alert_start: dt.datetime
    lead_days: int
    probability: float


@dataclasses.dataclass(frozen=True)
class MatchResult:
    matches: List[EpisodeMatch]
    false_alarms: List[AlertEpisode]
    missed: List[Episode]
    late: List[Episode]


def build_alert_episodes(
    points: Sequence[ForecastPoint],
    enter_threshold: float,
    exit_multiplier: float = 0.7,
    merge_gap_days: int = 30,
) -> List[AlertEpisode]:
    if not 0.0 < enter_threshold <= 1.0:
        raise ValueError("enter threshold outside (0,1]")
    exit_threshold = enter_threshold * exit_multiplier
    ordered = sorted(points, key=lambda point: point.issued_at)
    raw: List[AlertEpisode] = []
    active: List[ForecastPoint] = []
    for point in ordered:
        if not active and point.probability >= enter_threshold:
            active = [point]
        elif active and point.probability >= exit_threshold:
            active.append(point)
        elif active:
            raw.append(
                AlertEpisode(
                    active[0].issued_at,
                    active[-1].issued_at,
                    max(item.probability for item in active),
                    len(active),
                )
            )
            active = []
    if active:
        raw.append(
            AlertEpisode(
                active[0].issued_at,
                active[-1].issued_at,
                max(item.probability for item in active),
                len(active),
            )
        )
    merged: List[AlertEpisode] = []
    for alert in raw:
        if merged and (alert.start.date() - merged[-1].end.date()).days <= merge_gap_days:
            previous = merged.pop()
            merged.append(
                AlertEpisode(
                    previous.start,
                    alert.end,
                    max(previous.peak_probability, alert.peak_probability),
                    previous.point_count + alert.point_count,
                )
            )
        else:
            merged.append(alert)
    return merged


def build_policy_alert_episodes(
    points: Sequence[PolicyPoint],
    exit_multiplier: float = 0.7,
    merge_gap_days: int = 30,
) -> List[AlertEpisode]:
    """Build alerts when each refit can carry its own training-only threshold.

    An active alert remains in force until the day before the first issue that
    falls below that issue's hysteresis threshold.  This prevents monthly
    forecast spacing from understating time spent in warning.
    """
    if not 0.0 < exit_multiplier <= 1.0:
        raise ValueError("exit multiplier outside (0,1]")
    ordered = sorted(points, key=lambda point: point.issued_at)
    raw: List[AlertEpisode] = []
    active: List[PolicyPoint] = []
    for point in ordered:
        if not active and point.probability >= point.threshold:
            active = [point]
        elif active and point.probability >= point.threshold * exit_multiplier:
            active.append(point)
        elif active:
            end = point.issued_at - dt.timedelta(days=1)
            raw.append(
                AlertEpisode(
                    active[0].issued_at,
                    end,
                    max(item.probability for item in active),
                    len(active),
                )
            )
            active = []
    if active:
        raw.append(
            AlertEpisode(
                active[0].issued_at,
                active[-1].issued_at,
                max(item.probability for item in active),
                len(active),
            )
        )
    merged: List[AlertEpisode] = []
    for alert in raw:
        if merged and (alert.start.date() - merged[-1].end.date()).days <= merge_gap_days:
            previous = merged.pop()
            merged.append(
                AlertEpisode(
                    previous.start,
                    alert.end,
                    max(previous.peak_probability, alert.peak_probability),
                    previous.point_count + alert.point_count,
                )
            )
        else:
            merged.append(alert)
    return merged


def match_alerts(
    alerts: Sequence[AlertEpisode],
    episodes: Sequence[Episode],
    horizon_months: int,
    minimum_lead_days: int = 1,
) -> MatchResult:
    unmatched = {episode.episode_id: episode for episode in episodes}
    matches: List[EpisodeMatch] = []
    used_alerts = set()
    for alert_index, alert in enumerate(sorted(alerts, key=lambda item: item.start)):
        for episode in sorted(unmatched.values(), key=lambda item: item.onset):
            window_start = shift_months(episode.onset, -horizon_months)
            lead = (episode.onset - alert.start.date()).days
            if window_start <= alert.start.date() < episode.onset and lead >= minimum_lead_days:
                matches.append(
                    EpisodeMatch(
                        episode.episode_id,
                        alert.start,
                        lead,
                        alert.peak_probability,
                    )
                )
                used_alerts.add(alert_index)
                unmatched.pop(episode.episode_id)
                break
    late_ids = set()
    for alert_index, alert in enumerate(sorted(alerts, key=lambda item: item.start)):
        if alert_index in used_alerts:
            continue
        for episode in unmatched.values():
            if episode.onset <= alert.start.date() <= episode.trough_end:
                late_ids.add(episode.episode_id)
                used_alerts.add(alert_index)
                break
    late = [episode for episode in episodes if episode.episode_id in late_ids]
    missed = [
        episode
        for episode in episodes
        if episode.episode_id in unmatched and episode.episode_id not in late_ids
    ]
    ordered_alerts = sorted(alerts, key=lambda item: item.start)
    false_alarms = [
        alert for index, alert in enumerate(ordered_alerts) if index not in used_alerts
    ]
    return MatchResult(matches, false_alarms, missed, late)
