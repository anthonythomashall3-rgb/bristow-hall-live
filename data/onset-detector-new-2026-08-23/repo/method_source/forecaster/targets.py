"""NBER episode extraction and registered cumulative-onset labels."""

import csv
import dataclasses
import datetime as dt
from pathlib import Path
from typing import Iterable, List, Optional

from .releases import NBER_PEAK_ANNOUNCED_AT


@dataclasses.dataclass(frozen=True)
class Episode:
    episode_id: str
    peak_month: str
    onset: dt.date
    trough_end: dt.date
    announced_at: Optional[dt.datetime]


def shift_months(day: dt.date, months: int) -> dt.date:
    month_index = day.year * 12 + day.month - 1 + months
    year, month_zero = divmod(month_index, 12)
    month = month_zero + 1
    if month == 12:
        next_month = dt.date(year + 1, 1, 1)
    else:
        next_month = dt.date(year, month + 1, 1)
    last_day = (next_month - dt.timedelta(days=1)).day
    return dt.date(year, month, min(day.day, last_day))


def horizon_end(issue_date: dt.date, months: int) -> dt.date:
    if months <= 0:
        raise ValueError("horizon months must be positive")
    return shift_months(issue_date, months)


def _excluded_by_episode(
    issue_date: dt.date, episode: Episode, recovery_exclusion_months: int
) -> bool:
    if episode.onset <= issue_date <= episode.trough_end:
        return True
    recovery_end = shift_months(episode.trough_end, recovery_exclusion_months)
    return episode.trough_end < issue_date <= recovery_end


def onset_label(
    issue_date: dt.date,
    horizon_months: int,
    episodes: Iterable[Episode],
    data_cutoff: dt.date,
    recovery_exclusion_months: int = 3,
) -> Optional[int]:
    end = horizon_end(issue_date, horizon_months)
    if end > data_cutoff:
        return None
    episode_list = list(episodes)
    if any(
        _excluded_by_episode(issue_date, episode, recovery_exclusion_months)
        for episode in episode_list
    ):
        return None
    return int(any(issue_date < episode.onset <= end for episode in episode_list))


def episodes_from_usrecd(path: Path) -> List[Episode]:
    observations = []
    with Path(path).open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        next(reader, None)
        for row in reader:
            if len(row) < 2 or row[1] in {"", "."}:
                continue
            try:
                observations.append(
                    (dt.date.fromisoformat(row[0][:10]), float(row[1]) > 0.5)
                )
            except ValueError:
                continue
    observations.sort()
    episodes: List[Episode] = []
    start: Optional[dt.date] = None
    previous: Optional[dt.date] = None
    for day, recession in observations:
        if recession and start is None:
            # FRED's daily USRECD state turns on after the NBER peak month.
            # The registered boundary is the first day of that peak month.
            start = shift_months(day, -1) if previous is not None else day
        if not recession and start is not None:
            end = previous or day - dt.timedelta(days=1)
            peak_month = start.strftime("%Y-%m")
            episodes.append(
                Episode(
                    episode_id=f"{peak_month}/{end.strftime('%Y-%m')}",
                    peak_month=peak_month,
                    onset=start,
                    trough_end=end,
                    announced_at=NBER_PEAK_ANNOUNCED_AT.get(peak_month),
                )
            )
            start = None
        previous = day
    if start is not None and previous is not None:
        peak_month = start.strftime("%Y-%m")
        episodes.append(
            Episode(
                episode_id=f"{peak_month}/{previous.strftime('%Y-%m')}",
                peak_month=peak_month,
                onset=start,
                trough_end=previous,
                announced_at=NBER_PEAK_ANNOUNCED_AT.get(peak_month),
            )
        )
    return episodes
