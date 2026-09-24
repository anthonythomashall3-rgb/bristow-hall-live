"""Typed, hashable contracts for point-in-time forecasting data."""

import dataclasses
import datetime as dt
from enum import Enum
import hashlib
import json
from typing import Any, Dict, List, Optional, Sequence


class VintageClass(str, Enum):
    EXACT_VINTAGE = "exact_vintage"
    INVARIANT = "invariant"
    REAL_TIME_BY_CONSTRUCTION = "real_time_by_construction"
    CURRENT_VINTAGE_LAGGED = "current_vintage_lagged"
    UNUSABLE = "unusable"


def _aware(value: dt.datetime, field: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")


def _canonical(value: Dict[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


@dataclasses.dataclass(frozen=True)
class SourceSpec:
    series_id: str
    provider: str
    title: str
    frequency: str
    units: str
    seasonal_adjustment: str
    vintage_class: VintageClass
    lag_days: int
    source_url: str
    license_note: str
    raw_filename: Optional[str] = None

    def __post_init__(self) -> None:
        if self.lag_days < 0:
            raise ValueError("lag_days cannot be negative")

    @property
    def filename(self) -> str:
        return self.raw_filename or f"{self.series_id}.csv"


@dataclasses.dataclass(frozen=True)
class Observation:
    series_id: str
    reference_date: dt.date
    value: float
    available_at: dt.datetime
    ingested_at: dt.datetime
    vintage_id: str
    vintage_class: VintageClass
    raw_checksum: str
    source_uri: str
    revision_of: Optional[str] = None
    missing: bool = False
    imputed: bool = False

    def __post_init__(self) -> None:
        _aware(self.available_at, "available_at")
        _aware(self.ingested_at, "ingested_at")
        if len(self.raw_checksum) != 64:
            raise ValueError("raw_checksum must be a SHA-256 hex digest")

    def as_dict(self) -> Dict[str, Any]:
        result = dataclasses.asdict(self)
        result["reference_date"] = self.reference_date.isoformat()
        result["available_at"] = self.available_at.isoformat()
        result["ingested_at"] = self.ingested_at.isoformat()
        result["vintage_class"] = self.vintage_class.value
        return result

    def lineage_hash(self) -> str:
        return hashlib.sha256(_canonical(self.as_dict()).encode("utf-8")).hexdigest()


@dataclasses.dataclass(frozen=True)
class FeatureValue:
    name: str
    issue_at: dt.datetime
    value: float
    transform: str
    dependencies: List[str]
    data_quality: str

    @classmethod
    def derive(
        cls,
        name: str,
        issue_at: dt.datetime,
        value: float,
        transform: str,
        observations: Sequence[Observation],
    ) -> "FeatureValue":
        _aware(issue_at, "issue_at")
        if not observations:
            raise ValueError("derived feature requires at least one observation")
        future = [
            item.series_id for item in observations if item.available_at > issue_at
        ]
        if future:
            raise ValueError("future dependencies at issue time: " + ", ".join(future))
        qualities = {item.vintage_class.value for item in observations}
        return cls(
            name=name,
            issue_at=issue_at,
            value=float(value),
            transform=transform,
            dependencies=[item.lineage_hash() for item in observations],
            data_quality=",".join(sorted(qualities)),
        )

    def as_dict(self) -> Dict[str, Any]:
        result = dataclasses.asdict(self)
        result["issue_at"] = self.issue_at.isoformat()
        return result

    def lineage_hash(self) -> str:
        return hashlib.sha256(_canonical(self.as_dict()).encode("utf-8")).hexdigest()


@dataclasses.dataclass(frozen=True)
class DatasetManifest:
    issue_at: dt.datetime
    mode: str
    code_version: str
    protocol_hash: str
    feature_hashes: Dict[str, str]
    source_checksums: Dict[str, str]
    warnings: List[str]

    def digest(self) -> str:
        _aware(self.issue_at, "issue_at")
        payload = dataclasses.asdict(self)
        payload["issue_at"] = self.issue_at.isoformat()
        return hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()
