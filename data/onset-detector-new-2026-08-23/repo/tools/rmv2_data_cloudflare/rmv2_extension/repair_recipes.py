"""Generate safe candidate-only repair recipes for malformed FRED payloads."""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping


def build_fred_repair_recipes(
    registry: Mapping[str, Any],
    metric_rows: Iterable[Mapping[str, Any]],
) -> Dict[str, Any]:
    metrics = {str(row.get("series_id") or ""): row for row in metric_rows}
    series_ids = sorted({
        str(item.get("entity_id"))
        for item in registry.get("items") or []
        if item.get("gap_type") == "malformed_payload" and item.get("entity_type") == "series"
    })
    recipes: List[Dict[str, Any]] = []
    skipped: List[Dict[str, str]] = []
    for series_id in series_ids:
        metric = metrics.get(series_id) or {}
        if str(metric.get("provider") or "").lower() != "fred":
            skipped.append({"series_id": series_id, "reason": "provider_not_fred"})
            continue
        recipes.append({
            "recipe_id": "fred_repair_%s" % series_id.lower(),
            "enabled": True,
            "candidate_only": True,
            "public_eligible": False,
            "series_id": series_id,
            "url": "https://fred.stlouisfed.org/graph/fredgraph.csv?id=%s" % series_id,
            "destination": "repair_candidates/fred/%s.csv" % series_id,
            "allowed_hosts": ["fred.stlouisfed.org"],
            "allowed_content_types": ["text/csv", "application/octet-stream"],
            "min_bytes": 30,
            "max_bytes": 50 * 1024 * 1024,
            "required_prefix": "observation_date,%s" % series_id,
            "retries": 2,
            "timeout_seconds": 60,
            "backoff_seconds": 1.0,
            "max_concurrency_per_host": 2,
            "rights_status": str(metric.get("rights_status") or "review_required"),
            "admission_note": "Candidate bytes only. Feed Factory review and exact identity validation are required before canonical replacement.",
        })
    return {
        "schema_version": "recession-monitor-v2.fred-malformed-repair-recipes.v1",
        "candidate_only": True,
        "recipes": recipes,
        "skipped": skipped,
    }
