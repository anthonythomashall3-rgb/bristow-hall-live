"""Append-only prospective shadow forecasts and current experimental fitting."""

import datetime as dt
import hashlib
import json
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np

from .audit import run_audit
from .backtest import _target_episode, fit_family_bundle
from .features import FeatureBuilder
from .releases import nber_peak_known
from .runner import registered_run_spec_path
from .targets import episodes_from_usrecd, onset_label


GENESIS = "0" * 64
UTC = dt.timezone.utc


def canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def link_hash(sequence: int, issued_at: str, payload: object, previous: str) -> str:
    return hashlib.sha256(
        f"{sequence}|{issued_at}|{canonical(payload)}|{previous}".encode("utf-8")
    ).hexdigest()


class ForecastLedger:
    def __init__(self, path: Path):
        self.path = Path(path)

    def read(self) -> List[Dict[str, object]]:
        if not self.path.exists():
            return []
        return [
            json.loads(line)
            for line in self.path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    @staticmethod
    def verify(entries: Sequence[Mapping[str, object]]) -> Tuple[bool, Optional[int]]:
        previous = GENESIS
        for expected, entry in enumerate(entries):
            if entry.get("sequence") != expected or entry.get("previous") != previous:
                return False, expected
            digest = link_hash(
                expected,
                str(entry["issued_at"]),
                entry["payload"],
                previous,
            )
            if entry.get("hash") != digest:
                return False, expected
            previous = digest
        return True, None

    @staticmethod
    def prefix_is_preserved(
        older: Sequence[Mapping[str, object]],
        newer: Sequence[Mapping[str, object]],
    ) -> bool:
        return len(older) <= len(newer) and all(
            canonical(left) == canonical(right)
            for left, right in zip(older, newer)
        )

    def entry_for_local_day(
        self, issued_at: dt.datetime, local_timezone: dt.tzinfo = None
    ) -> Optional[Dict[str, object]]:
        if issued_at.tzinfo is None or issued_at.utcoffset() is None:
            raise ValueError("issued_at must be timezone-aware")
        timezone = local_timezone or dt.datetime.now().astimezone().tzinfo
        target = issued_at.astimezone(timezone).date()
        for entry in reversed(self.read()):
            existing = dt.datetime.fromisoformat(str(entry["issued_at"]))
            if existing.astimezone(timezone).date() == target:
                return entry
        return None

    def append(
        self, issued_at: dt.datetime, payload: Mapping[str, object]
    ) -> Dict[str, object]:
        if issued_at.tzinfo is None or issued_at.utcoffset() is None:
            raise ValueError("issued_at must be timezone-aware")
        entries = self.read()
        ok, bad = self.verify(entries)
        if not ok:
            raise RuntimeError(f"prospective ledger failed verification at {bad}")
        timestamp = issued_at.isoformat()
        existing = [entry for entry in entries if entry["issued_at"] == timestamp]
        if existing:
            if canonical(existing[0]["payload"]) != canonical(payload):
                raise RuntimeError("same issue timestamp already has different payload")
            return existing[0]
        sequence = len(entries)
        previous = entries[-1]["hash"] if entries else GENESIS
        entry = {
            "sequence": sequence,
            "issued_at": timestamp,
            "previous": previous,
            "payload": dict(payload),
        }
        entry["hash"] = link_hash(sequence, timestamp, entry["payload"], previous)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(canonical(entry) + "\n")
        return entry


def _legacy_nowcast(raw_root: Path) -> Dict[str, object]:
    path = Path(raw_root).parent / "geo" / "leading_final.json"
    if not path.is_file():
        return {
            "probability": None,
            "status": "unavailable",
            "owner": "legacy_incumbent_not_forecaster_v2",
        }
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        current = value.get("current", {}).get("0", {})
        return {
            "probability": current.get("probability"),
            "as_of": current.get("as_of"),
            "model": current.get("model"),
            "status": "separate_incumbent_comparator",
            "owner": "leading_final",
        }
    except (OSError, ValueError, TypeError):
        return {
            "probability": None,
            "status": "unavailable",
            "owner": "legacy_incumbent_not_forecaster_v2",
        }


def _policy_state(probability: float, threshold: float) -> str:
    if probability < 0.5 * threshold:
        return "normal"
    if probability < threshold:
        return "watch"
    if probability < 1.5 * threshold:
        return "warning"
    return "high_risk"


def _time_to_onset(
    probabilities: Mapping[str, float]
) -> List[Dict[str, object]]:
    horizons = sorted((int(key), float(value)) for key, value in probabilities.items())
    result = []
    previous_horizon = 0
    previous_probability = 0.0
    for horizon, probability in horizons:
        result.append(
            {
                "after_month": previous_horizon,
                "through_month": horizon,
                "probability": max(0.0, probability - previous_probability),
            }
        )
        previous_horizon = horizon
        previous_probability = probability
    result.append(
        {
            "after_month": previous_horizon,
            "through_month": None,
            "probability": max(0.0, 1.0 - previous_probability),
        }
    )
    return result


def build_shadow_payload(
    raw_root: Path,
    artifact_root: Path,
    issued_at: dt.datetime,
) -> Dict[str, object]:
    if issued_at.tzinfo is None or issued_at.utcoffset() is None:
        raise ValueError("issued_at must be timezone-aware")
    artifact_root = Path(artifact_root)
    scorecard = json.loads(
        (artifact_root / "scorecard_approximate.json").read_text(encoding="utf-8")
    )
    manifest = json.loads(
        (artifact_root / "manifest.json").read_text(encoding="utf-8")
    )
    run_spec = json.loads(registered_run_spec_path().read_text(encoding="utf-8"))
    audit = run_audit(Path(raw_root))
    base = {
        "schema": "bh.forecaster.prospective-shadow.v1",
        "run_id": run_spec["run_id"],
        "evidence_manifest_sha256": hashlib.sha256(
            (artifact_root / "manifest.json").read_bytes()
        ).hexdigest(),
        "issued_at": issued_at.isoformat(),
        "mode": "approximate_current_vintage_prospective_shadow",
        "historical_evidence_status": "contaminated_nested_oos",
        "deployment_eligible": False,
        "adoption_status": "rejected_historical_gate_shadow_only",
        "data_audit_ok": bool(audit["ok"]),
        "source_status": audit["source_status"],
        "uncertainty": {
            "status": "unestablished_below_8_independent_episodes",
            "interval": None,
        },
        "current_regime_nowcast": _legacy_nowcast(Path(raw_root)),
    }
    if not audit["ok"]:
        return {
            **base,
            "status": "abstained",
            "abstention_reason": "critical source or leakage audit failed",
            "horizon_probabilities": {},
            "time_to_onset_distribution": [],
            "policy_states": {},
        }
    builder = FeatureBuilder(Path(raw_root))
    start = dt.date.fromisoformat(
        run_spec["modes"]["approximate_current_vintage"]["issue_start"]
    )
    feature_end = dt.date.fromisoformat(run_spec["feature_issue_end"])
    historical = builder.build_dataset(
        start, feature_end, "approximate_current_vintage"
    )
    current = builder.build_row(issued_at, "approximate_current_vintage")
    episodes = episodes_from_usrecd(Path(raw_root) / "USRECD.csv")
    cutoff = dt.date.fromisoformat(run_spec["data_cutoff"])
    matrix = historical.matrix()
    issues = historical.issue_dates()
    probabilities: Dict[str, float] = {}
    policies = {}
    model_records = {}
    for horizon in run_spec["horizons_months"]:
        family = scorecard["selection"][str(horizon)]
        labels = [onset_label(day, horizon, episodes, cutoff) for day in issues]
        indices = []
        for index, label in enumerate(labels):
            if label is None:
                continue
            target_id = _target_episode(issues[index], horizon, episodes)
            if target_id:
                episode = next(item for item in episodes if item.episode_id == target_id)
                if not nber_peak_known(episode.peak_month, issued_at):
                    continue
            indices.append(index)
        if family is None or len(indices) < 40:
            continue
        selected = np.asarray(indices, dtype=int)
        bundle = fit_family_bundle(
            family,
            matrix[selected],
            np.asarray([labels[index] for index in indices], dtype=float),
        )
        probability = bundle.predict(
            np.asarray([current.values[name] for name in historical.feature_names])
        )
        probabilities[str(horizon)] = probability
        policies[str(horizon)] = {
            "threshold": bundle.threshold,
            "state": _policy_state(probability, bundle.threshold),
        }
        model_records[str(horizon)] = {
            "family": family,
            "training_rows": len(indices),
            "training_start": issues[indices[0]].isoformat(),
            "training_end": issues[indices[-1]].isoformat(),
            "spec_hash": bundle.spec_digest,
        }
    maximum = 0.0
    for horizon in sorted(probabilities, key=int):
        maximum = max(maximum, probabilities[horizon])
        probabilities[horizon] = maximum
        policies[horizon]["state"] = _policy_state(
            maximum, policies[horizon]["threshold"]
        )
    feature_manifest = {
        "issue_at": current.issue_at.isoformat(),
        "feature_hashes": current.feature_hashes,
        "source_checksums": current.source_checksums,
        "data_quality": current.data_quality,
    }
    return {
        **base,
        "status": "experimental_shadow_forecast",
        "horizon_probabilities": probabilities,
        "time_to_onset_distribution": _time_to_onset(probabilities),
        "policy_states": policies,
        "models": model_records,
        "feature_manifest": feature_manifest,
        "evidence_generator_sha256": manifest["evidence_generator_sha256"],
    }


def issue_shadow_forecast(
    raw_root: Path,
    artifact_root: Path,
    ledger_path: Path,
    issued_at: dt.datetime,
) -> Dict[str, object]:
    ledger = ForecastLedger(ledger_path)
    existing = ledger.entry_for_local_day(issued_at)
    if existing is not None:
        return existing
    payload = build_shadow_payload(raw_root, artifact_root, issued_at)
    return ledger.append(issued_at, payload)
