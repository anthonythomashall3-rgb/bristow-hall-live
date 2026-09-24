"""Release events and official NBER-label availability boundaries."""

import dataclasses
import datetime as dt
from typing import Dict


UTC = dt.timezone.utc


@dataclasses.dataclass(frozen=True)
class ReleaseEvent:
    source: str
    series_id: str
    reference_date: dt.date
    released_at: dt.datetime
    release_id: str

    def __post_init__(self) -> None:
        if self.released_at.tzinfo is None or self.released_at.utcoffset() is None:
            raise ValueError("released_at must be timezone-aware")


def is_available(event: ReleaseEvent, issue_at: dt.datetime) -> bool:
    if issue_at.tzinfo is None or issue_at.utcoffset() is None:
        raise ValueError("issue_at must be timezone-aware")
    return event.released_at <= issue_at


# Formal post-1978 NBER peak announcements, from the official archive.
# Earlier chronology is treated as known at the v2 evaluation floor (1967 labels
# are never used as features and the first scored origins require 15 years).
NBER_PEAK_ANNOUNCED_AT: Dict[str, dt.datetime] = {
    "1980-01": dt.datetime(1980, 6, 3, 17, 0, tzinfo=UTC),
    "1981-07": dt.datetime(1982, 1, 6, 17, 0, tzinfo=UTC),
    "1990-07": dt.datetime(1991, 4, 25, 16, 0, tzinfo=UTC),
    "2001-03": dt.datetime(2001, 11, 26, 17, 0, tzinfo=UTC),
    "2007-12": dt.datetime(2008, 12, 1, 17, 0, tzinfo=UTC),
    "2020-02": dt.datetime(2020, 6, 8, 16, 0, tzinfo=UTC),
}


def nber_peak_known(peak_month: str, issue_at: dt.datetime) -> bool:
    if issue_at.tzinfo is None or issue_at.utcoffset() is None:
        raise ValueError("issue_at must be timezone-aware")
    announced = NBER_PEAK_ANNOUNCED_AT.get(peak_month)
    if announced is None:
        return issue_at >= dt.datetime(1979, 1, 1, tzinfo=UTC)
    return issue_at >= announced
