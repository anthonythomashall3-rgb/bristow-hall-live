"""Source catalog for v2's registered public-data feature set."""

import json
import os
from pathlib import Path
from typing import Dict, List

from .schema import SourceSpec, VintageClass


ROOT = Path(__file__).resolve().parent.parent


SOURCES: Dict[str, SourceSpec] = {
    "T10Y3M": SourceSpec(
        "T10Y3M", "Federal Reserve Board via FRED", "10Y minus 3M Treasury spread",
        "daily", "percentage points", "not seasonally adjusted",
        VintageClass.INVARIANT, 1, "https://fred.stlouisfed.org/series/T10Y3M",
        "FRED terms; underlying public Treasury/Board rates",
    ),
    "GS10": SourceSpec(
        "GS10", "Federal Reserve Board via FRED", "10-Year Treasury rate",
        "monthly", "percent", "not seasonally adjusted", VintageClass.INVARIANT, 32,
        "https://fred.stlouisfed.org/series/GS10",
        "FRED terms; public Federal Reserve H.15 rate",
    ),
    "TB3MS": SourceSpec(
        "TB3MS", "Federal Reserve Board via FRED", "3-Month Treasury bill rate",
        "monthly", "percent", "not seasonally adjusted", VintageClass.INVARIANT, 32,
        "https://fred.stlouisfed.org/series/TB3MS",
        "FRED terms; public Federal Reserve H.15 rate",
    ),
    "ICSA": SourceSpec(
        "ICSA", "U.S. Department of Labor via ALFRED", "Initial unemployment claims",
        "weekly", "number", "seasonally adjusted", VintageClass.EXACT_VINTAGE, 6,
        "https://fred.stlouisfed.org/series/ICSA", "FRED/ALFRED terms",
    ),
    "INDPRO": SourceSpec(
        "INDPRO", "Federal Reserve Board via ALFRED", "Industrial production index",
        "monthly", "index", "seasonally adjusted", VintageClass.EXACT_VINTAGE, 45,
        "https://fred.stlouisfed.org/series/INDPRO", "FRED/ALFRED terms",
    ),
    "HOUST": SourceSpec(
        "HOUST", "Census/HUD via ALFRED", "Housing starts",
        "monthly", "thousands SAAR", "seasonally adjusted",
        VintageClass.EXACT_VINTAGE, 48, "https://fred.stlouisfed.org/series/HOUST",
        "FRED/ALFRED terms",
    ),
    "W875RX1": SourceSpec(
        "W875RX1", "BEA via ALFRED", "Real personal income excluding transfers",
        "monthly", "billions chained dollars", "seasonally adjusted",
        VintageClass.EXACT_VINTAGE, 55, "https://fred.stlouisfed.org/series/W875RX1",
        "FRED/ALFRED terms",
    ),
    "USRECD": SourceSpec(
        "USRECD", "NBER via FRED", "NBER recession indicator",
        "daily", "0/1", "not applicable", VintageClass.UNUSABLE, 0,
        "https://fred.stlouisfed.org/series/USRECD",
        "label only; prohibited as a feature",
    ),
}


# The V2 external read-set is DECLARED, not hand-listed (§1.6). The forecaster's
# raw tree lives OUTSIDE the repo; its authoritative in-repo name is
# live_data/config/external_read_roots.v1.json. Resolving from that file makes
# the declaration load-bearing, so it cannot silently rot.
EXTERNAL_READ_ROOTS_CONFIG = ROOT.parent / "live_data" / "config" / "external_read_roots.v1.json"


def declared_forecaster_raw_root() -> Path:
    """The FORECASTER_RAW_ROOT declared in external_read_roots.v1.json, or None
    if the manifest is absent or does not declare it."""
    try:
        data = json.loads(EXTERNAL_READ_ROOTS_CONFIG.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    for entry in data.get("roots", []):
        if entry.get("env_var") == "FORECASTER_RAW_ROOT":
            path = entry.get("path")
            if isinstance(path, str) and path:
                return Path(path)
    return None


def raw_root() -> Path:
    env = os.environ.get("FORECASTER_RAW_ROOT")
    if env:
        return Path(env).resolve()
    declared = declared_forecaster_raw_root()
    if declared is not None:
        return declared.resolve()
    return (ROOT / "raw").resolve()


def audit_catalog(root: Path = None) -> Dict[str, object]:
    root = Path(root or raw_root())
    issues: List[str] = []
    details = {}
    vintages = root / "vintages"
    for series_id, spec in SOURCES.items():
        current = root / spec.filename
        snapshots = list(vintages.glob(f"{series_id}_????-??-??.csv"))
        nonempty = sum(path.stat().st_size > 0 for path in snapshots)
        if spec.vintage_class != VintageClass.UNUSABLE and not current.is_file():
            issues.append(f"missing current file: {current}")
        if spec.vintage_class == VintageClass.EXACT_VINTAGE and nonempty == 0:
            issues.append(f"no nonempty exact vintages: {series_id}")
        details[series_id] = {
            "class": spec.vintage_class.value,
            "current": current.is_file(),
            "snapshot_count": len(snapshots),
            "nonempty_snapshot_count": nonempty,
        }
    return {
        "schema": "bh.forecaster.catalog-audit.v1",
        "raw_root": str(root),
        "ok": not issues,
        "issues": issues,
        "sources": details,
    }


if __name__ == "__main__":
    result = audit_catalog()
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["ok"] else 1)
