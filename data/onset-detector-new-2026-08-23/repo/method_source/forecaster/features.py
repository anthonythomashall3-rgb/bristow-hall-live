"""Release-aware construction of the registered five-feature monthly panel."""

import dataclasses
import datetime as dt
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import numpy as np

from .catalog import SOURCES
from .schema import FeatureValue, Observation, SourceSpec, VintageClass
from .vintage import DataUnavailable, SnapshotVintageStore, UTC


FEATURE_NAMES = [
    "term_spread_10y3m",
    "initial_claims_yoy",
    "industrial_production_yoy",
    "housing_starts_yoy",
    "real_income_yoy",
]

FEATURE_SERIES = {
    "term_spread_10y3m": "GS10_MINUS_TB3MS",
    "initial_claims_yoy": "ICSA",
    "industrial_production_yoy": "INDPRO",
    "housing_starts_yoy": "HOUST",
    "real_income_yoy": "W875RX1",
}


@dataclasses.dataclass(frozen=True)
class FeatureRow:
    issue_at: dt.datetime
    values: Dict[str, float]
    feature_hashes: Dict[str, str]
    data_quality: Dict[str, str]
    source_checksums: Dict[str, str]


@dataclasses.dataclass(frozen=True)
class FeatureDataset:
    rows: List[FeatureRow]
    feature_names: List[str]
    mode: str
    skipped: Dict[str, str]

    def matrix(self) -> np.ndarray:
        return np.array(
            [[row.values[name] for name in self.feature_names] for row in self.rows],
            dtype=float,
        )

    def issue_dates(self) -> List[dt.date]:
        return [row.issue_at.date() for row in self.rows]


def monthly_issues(start: dt.date, end: dt.date, day: int = 21) -> List[dt.datetime]:
    values = []
    cursor = dt.date(start.year, start.month, 1)
    while cursor <= end:
        if cursor.month == 12:
            following = dt.date(cursor.year + 1, 1, 1)
        else:
            following = dt.date(cursor.year, cursor.month + 1, 1)
        last_day = (following - dt.timedelta(days=1)).day
        issue = dt.date(cursor.year, cursor.month, min(day, last_day))
        if start <= issue <= end:
            values.append(dt.datetime.combine(issue, dt.time.min, tzinfo=UTC))
        cursor = following
    return values


def _approximate_spec(spec: SourceSpec) -> SourceSpec:
    if spec.vintage_class == VintageClass.INVARIANT:
        return spec
    return dataclasses.replace(spec, vintage_class=VintageClass.CURRENT_VINTAGE_LAGGED)


def _prior_year(
    observations: Sequence[Observation], latest: Observation, tolerance_days: int
) -> Observation:
    target = latest.reference_date - dt.timedelta(days=365)
    eligible = [
        item
        for item in observations
        if item.reference_date < latest.reference_date
        and abs((item.reference_date - target).days) <= tolerance_days
    ]
    if not eligible:
        raise DataUnavailable(f"{latest.series_id} lacks a prior-year observation")
    return min(eligible, key=lambda item: abs((item.reference_date - target).days))


class FeatureBuilder:
    def __init__(self, raw_root: Path):
        root = Path(raw_root)
        self.store = SnapshotVintageStore(root / "vintages", current_root=root)

    def _series(
        self, spec: SourceSpec, issue_at: dt.datetime, mode: str
    ) -> List[Observation]:
        if mode == "strict_vintage" and spec.vintage_class == VintageClass.EXACT_VINTAGE:
            values = self.store.snapshot_observations(spec.series_id, issue_at)
            if not values:
                raise DataUnavailable(f"empty exact vintage for {spec.series_id}")
            return values
        effective = spec if mode == "strict_vintage" else _approximate_spec(spec)
        return self.store.current_observations(
            effective, issue_at, strict=(mode == "strict_vintage")
        )

    def build_row(self, issue_at: dt.datetime, mode: str) -> FeatureRow:
        if mode not in {"strict_vintage", "approximate_current_vintage"}:
            raise ValueError(f"unsupported feature mode {mode}")
        features: Dict[str, FeatureValue] = {}
        checksums: Dict[str, str] = {}
        for name in FEATURE_NAMES:
            series_id = FEATURE_SERIES[name]
            if name == "term_spread_10y3m":
                long_rate = self._series(SOURCES["GS10"], issue_at, mode)[-1]
                short_rate = self._series(SOURCES["TB3MS"], issue_at, mode)[-1]
                features[name] = FeatureValue.derive(
                    name,
                    issue_at,
                    long_rate.value - short_rate.value,
                    "GS10_minus_TB3MS",
                    [long_rate, short_rate],
                )
                checksums["GS10"] = long_rate.raw_checksum
                checksums["TB3MS"] = short_rate.raw_checksum
                continue
            observations = self._series(SOURCES[series_id], issue_at, mode)
            latest = observations[-1]
            checksums[series_id] = latest.raw_checksum
            prior = _prior_year(
                observations,
                latest,
                tolerance_days=45 if series_id == "ICSA" else 62,
            )
            if prior.value == 0:
                raise DataUnavailable(f"{series_id} prior-year value is zero")
            value = 100.0 * (latest.value / prior.value - 1.0)
            dependencies = [prior, latest]
            transform = "year_over_year_percent"
            features[name] = FeatureValue.derive(
                name, issue_at, value, transform, dependencies
            )
        return FeatureRow(
            issue_at=issue_at,
            values={name: features[name].value for name in FEATURE_NAMES},
            feature_hashes={name: features[name].lineage_hash() for name in FEATURE_NAMES},
            data_quality={name: features[name].data_quality for name in FEATURE_NAMES},
            source_checksums=checksums,
        )

    def build_dataset(
        self, start: dt.date, end: dt.date, mode: str
    ) -> FeatureDataset:
        rows = []
        skipped = {}
        for issue_at in monthly_issues(start, end):
            try:
                rows.append(self.build_row(issue_at, mode))
            except DataUnavailable as error:
                skipped[issue_at.date().isoformat()] = str(error)
        return FeatureDataset(rows, list(FEATURE_NAMES), mode, skipped)
