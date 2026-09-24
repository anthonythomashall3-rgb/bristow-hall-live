"""Fail-closed temporal, source-quality, and registration audit."""

import csv
import datetime as dt
import json
from pathlib import Path
from typing import Dict

from .catalog import SOURCES, audit_catalog, raw_root
from .features import FEATURE_SERIES
from .protocol import load_protocol, validate_protocol
from .schema import FeatureValue, Observation, VintageClass


UTC = dt.timezone.utc


def future_canary_is_rejected() -> bool:
    issue = dt.datetime(2026, 1, 1, tzinfo=UTC)
    observation = Observation(
        series_id="FUTURE_CANARY",
        reference_date=dt.date(2026, 2, 1),
        value=999.0,
        available_at=dt.datetime(2026, 2, 1, tzinfo=UTC),
        ingested_at=dt.datetime(2026, 2, 1, tzinfo=UTC),
        vintage_id="impossible",
        vintage_class=VintageClass.EXACT_VINTAGE,
        raw_checksum="f" * 64,
        source_uri="canary://future",
    )
    try:
        FeatureValue.derive(
            "future_canary", issue, observation.value, "identity", [observation]
        )
    except ValueError:
        return True
    return False


def assess_source_file(
    path: Path,
    issue_at: dt.datetime,
    maximum_age_days: int = 60,
    maximum_reference_age_days: int = None,
) -> Dict[str, object]:
    path = Path(path)
    if issue_at.tzinfo is None or issue_at.utcoffset() is None:
        raise ValueError("issue_at must be timezone-aware")
    if not path.is_file():
        return {"path": str(path), "status": "missing"}
    try:
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.reader(handle)
            header = next(reader)
            latest_reference = None
            for row in reader:
                if len(row) < 2 or row[1] in {"", "."}:
                    continue
                reference = dt.date.fromisoformat(row[0][:10])
                float(row[1])
                latest_reference = max(latest_reference, reference) if latest_reference else reference
            if len(header) < 2 or latest_reference is None:
                return {"path": str(path), "status": "corrupt"}
    except (UnicodeDecodeError, ValueError, StopIteration, OSError):
        return {"path": str(path), "status": "corrupt"}
    modified = dt.datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)
    age_days = max(0.0, (issue_at - modified).total_seconds() / 86400.0)
    reference_age_days = max(0, (issue_at.date() - latest_reference).days)
    status = "ok"
    if age_days > maximum_age_days or (
        maximum_reference_age_days is not None
        and reference_age_days > maximum_reference_age_days
    ):
        status = "stale"
    return {
        "path": str(path),
        "status": status,
        "age_days": age_days,
        "latest_reference_date": latest_reference.isoformat(),
        "reference_age_days": reference_age_days,
    }


def run_audit(root: Path = None) -> Dict[str, object]:
    protocol = load_protocol()
    validate_protocol(protocol)
    data_root = Path(root or raw_root())
    catalog = audit_catalog(data_root)
    now = dt.datetime.now(UTC)
    source_status = {}
    for series_id, spec in SOURCES.items():
        if spec.vintage_class == VintageClass.UNUSABLE:
            continue
        maximum_age = 370 if spec.frequency == "monthly" else 40
        reference_age = {
            "T10Y3M": 10,
            "GS10": 90,
            "TB3MS": 90,
            "ICSA": 21,
            "INDPRO": 90,
            "HOUST": 90,
            "W875RX1": 120,
        }[series_id]
        source_status[series_id] = assess_source_file(
            data_root / spec.filename,
            now,
            maximum_age_days=maximum_age,
            maximum_reference_age_days=reference_age,
        )
    checks = {
        "protocol_valid": True,
        "catalog_valid": bool(catalog["ok"]),
        "future_canary_rejected": future_canary_is_rejected(),
        "target_not_feature": "USRECD" not in set(FEATURE_SERIES.values()),
        "strict_fallback_prohibited": (
            protocol["data_tiers"]["strict_vintage"]["fallback"] == "prohibited"
        ),
        "historical_claim_contaminated": (
            protocol["historical_evidence_status"] == "contaminated_nested_oos"
        ),
        "prospective_only_untouched": protocol["untouched_evidence"] == "prospective_only",
        "source_failures_visible": all(
            item["status"] in {"ok", "stale"} for item in source_status.values()
        ),
    }
    return {
        "schema": "bh.forecaster.leakage-audit.v1",
        "audited_at": now.isoformat(),
        "ok": all(checks.values()),
        "checks": checks,
        "catalog": catalog,
        "source_status": source_status,
    }


if __name__ == "__main__":
    value = run_audit()
    print(json.dumps(value, indent=2, sort_keys=True))
    raise SystemExit(0 if value["ok"] else 1)
