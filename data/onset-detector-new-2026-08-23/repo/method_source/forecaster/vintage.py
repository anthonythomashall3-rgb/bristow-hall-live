"""Read immutable ALFRED snapshots and conservative current-vintage fallbacks."""

import csv
import datetime as dt
import hashlib
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

from .schema import Observation, SourceSpec, VintageClass


UTC = dt.timezone.utc


class DataUnavailable(RuntimeError):
    """Raised when an issue-time information set cannot lawfully use a value."""


def _ensure_aware(value: dt.datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("issue_at must be timezone-aware")


def _parse(path: Path) -> List[Tuple[dt.date, float]]:
    rows: List[Tuple[dt.date, float]] = []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        next(reader, None)
        for row in reader:
            if len(row) < 2 or row[1] in {"", "."}:
                continue
            try:
                rows.append((dt.date.fromisoformat(row[0][:10]), float(row[1])))
            except (ValueError, TypeError):
                continue
    if not rows:
        raise DataUnavailable(f"{path} contains no valid observations")
    return sorted(rows)


def _checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class SnapshotVintageStore:
    """A conservative store: a dated snapshot becomes usable the next UTC day."""

    def __init__(self, vintage_root: Path, current_root: Optional[Path] = None):
        self.vintage_root = Path(vintage_root)
        self.current_root = Path(current_root) if current_root else None

    @staticmethod
    def snapshot_available_at(vintage_date: dt.date) -> dt.datetime:
        return dt.datetime.combine(
            vintage_date + dt.timedelta(days=1), dt.time.min, tzinfo=UTC
        )

    def _snapshots(self, series_id: str) -> Iterable[Tuple[dt.date, Path]]:
        for path in self.vintage_root.glob(f"{series_id}_????-??-??.csv"):
            try:
                vintage_date = dt.date.fromisoformat(path.stem[-10:])
            except ValueError:
                continue
            yield vintage_date, path

    def latest_snapshot(
        self, series_id: str, issue_at: dt.datetime
    ) -> Tuple[dt.date, Path]:
        _ensure_aware(issue_at)
        eligible = [
            item
            for item in self._snapshots(series_id)
            if self.snapshot_available_at(item[0]) <= issue_at
            and item[1].stat().st_size > 0
        ]
        if not eligible:
            raise DataUnavailable(f"no exact {series_id} vintage available by {issue_at}")
        return max(eligible, key=lambda item: item[0])

    def latest_observation(
        self, series_id: str, issue_at: dt.datetime
    ) -> Observation:
        vintage_date, path = self.latest_snapshot(series_id, issue_at)
        available_at = self.snapshot_available_at(vintage_date)
        rows = [
            row for row in _parse(path)
            if dt.datetime.combine(row[0], dt.time.min, tzinfo=UTC) <= issue_at
        ]
        if not rows:
            raise DataUnavailable(f"{series_id} snapshot has no issue-time observation")
        reference_date, value = rows[-1]
        return Observation(
            series_id=series_id,
            reference_date=reference_date,
            value=value,
            available_at=available_at,
            ingested_at=available_at,
            vintage_id=vintage_date.isoformat(),
            vintage_class=VintageClass.EXACT_VINTAGE,
            raw_checksum=_checksum(path),
            source_uri=str(path),
        )

    def snapshot_observations(
        self, series_id: str, issue_at: dt.datetime
    ) -> List[Observation]:
        vintage_date, path = self.latest_snapshot(series_id, issue_at)
        available_at = self.snapshot_available_at(vintage_date)
        digest = _checksum(path)
        return [
            Observation(
                series_id=series_id,
                reference_date=reference_date,
                value=value,
                available_at=available_at,
                ingested_at=available_at,
                vintage_id=vintage_date.isoformat(),
                vintage_class=VintageClass.EXACT_VINTAGE,
                raw_checksum=digest,
                source_uri=str(path),
            )
            for reference_date, value in _parse(path)
            if dt.datetime.combine(reference_date, dt.time.min, tzinfo=UTC) <= issue_at
        ]

    def from_current(
        self, spec: SourceSpec, issue_at: dt.datetime, strict: bool
    ) -> Observation:
        _ensure_aware(issue_at)
        if strict and spec.vintage_class == VintageClass.CURRENT_VINTAGE_LAGGED:
            raise DataUnavailable(
                f"strict mode prohibits current-vintage fallback for {spec.series_id}"
            )
        if spec.vintage_class == VintageClass.UNUSABLE:
            raise DataUnavailable(f"{spec.series_id} is unusable")
        if self.current_root is None:
            raise DataUnavailable("current_root is not configured")
        path = self.current_root / spec.filename
        if not path.is_file():
            raise DataUnavailable(f"missing current series {path}")
        eligible = []
        for reference_date, value in _parse(path):
            available_date = reference_date + dt.timedelta(days=spec.lag_days)
            available_at = dt.datetime.combine(available_date, dt.time.min, tzinfo=UTC)
            if available_at <= issue_at:
                eligible.append((reference_date, value, available_at))
        if not eligible:
            raise DataUnavailable(f"{spec.series_id} has no value by {issue_at}")
        reference_date, value, available_at = eligible[-1]
        return Observation(
            series_id=spec.series_id,
            reference_date=reference_date,
            value=value,
            available_at=available_at,
            ingested_at=dt.datetime.fromtimestamp(path.stat().st_mtime, tz=UTC),
            vintage_id=f"current-file-{_checksum(path)[:12]}",
            vintage_class=spec.vintage_class,
            raw_checksum=_checksum(path),
            source_uri=str(path),
        )

    def current_observations(
        self, spec: SourceSpec, issue_at: dt.datetime, strict: bool
    ) -> List[Observation]:
        _ensure_aware(issue_at)
        if strict and spec.vintage_class == VintageClass.CURRENT_VINTAGE_LAGGED:
            raise DataUnavailable(
                f"strict mode prohibits current-vintage fallback for {spec.series_id}"
            )
        if self.current_root is None:
            raise DataUnavailable("current_root is not configured")
        path = self.current_root / spec.filename
        if not path.is_file():
            raise DataUnavailable(f"missing current series {path}")
        digest = _checksum(path)
        ingested_at = dt.datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)
        observations = []
        for reference_date, value in _parse(path):
            available_at = dt.datetime.combine(
                reference_date + dt.timedelta(days=spec.lag_days),
                dt.time.min,
                tzinfo=UTC,
            )
            if available_at <= issue_at:
                observations.append(
                    Observation(
                        series_id=spec.series_id,
                        reference_date=reference_date,
                        value=value,
                        available_at=available_at,
                        ingested_at=ingested_at,
                        vintage_id=f"current-file-{digest[:12]}",
                        vintage_class=spec.vintage_class,
                        raw_checksum=digest,
                        source_uri=str(path),
                    )
                )
        if not observations:
            raise DataUnavailable(f"{spec.series_id} has no values by {issue_at}")
        return observations

    def observation(
        self, spec: SourceSpec, issue_at: dt.datetime, strict: bool
    ) -> Observation:
        if spec.vintage_class == VintageClass.EXACT_VINTAGE:
            try:
                return self.latest_observation(spec.series_id, issue_at)
            except DataUnavailable:
                if strict:
                    raise
        return self.from_current(spec, issue_at, strict=strict)
