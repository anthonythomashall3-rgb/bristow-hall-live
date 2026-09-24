"""Load and validate the registered forecasting protocol."""

import json
from pathlib import Path
from typing import Any, Dict


ROOT = Path(__file__).resolve().parent.parent
PROTOCOL_PATH = Path(__file__).with_name("protocol_v2.json")


def load_protocol(path: Path = PROTOCOL_PATH) -> Dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def validate_protocol(protocol: Dict[str, Any]) -> None:
    required = {
        "schema", "registered_at", "target", "horizons_months", "issue_cadence",
        "eligibility", "data_tiers", "validation", "models", "calibration",
        "alert_policy", "metrics", "uncertainty", "success", "claims", "seed",
    }
    missing = sorted(required - set(protocol))
    if missing:
        raise ValueError("protocol missing fields: " + ", ".join(missing))
    if protocol["schema"] != "bh.forecaster.protocol.v2":
        raise ValueError("unsupported protocol schema")
    horizons = protocol["horizons_months"]
    if horizons != [1, 3, 6, 9, 12, 18, 24]:
        raise ValueError("horizons must remain the registered cumulative sequence")
    if protocol["target"]["label_source"] != "NBER":
        raise ValueError("primary target must use the NBER chronology")
    if protocol["target"]["onset_boundary"] != "first_day_of_peak_month":
        raise ValueError("primary onset boundary changed")
    if protocol["historical_evidence_status"] != "contaminated_nested_oos":
        raise ValueError("historical evidence may not be represented as untouched")
    if protocol["untouched_evidence"] != "prospective_only":
        raise ValueError("only prospective forecasts may be called untouched")
    if protocol["claims"]["allow_perfect_forecaster"]:
        raise ValueError("perfect-forecaster claims are prohibited")
    if not 0.0 < protocol["success"]["episode_recall_target"] <= 1.0:
        raise ValueError("invalid episode recall target")
    if protocol["seed"] != 20260722:
        raise ValueError("registered deterministic seed changed")


if __name__ == "__main__":
    value = load_protocol()
    validate_protocol(value)
    print(f"PROTOCOL OK: {PROTOCOL_PATH} ({value['schema']})")
