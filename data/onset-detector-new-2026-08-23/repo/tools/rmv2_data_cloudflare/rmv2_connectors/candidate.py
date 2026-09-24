"""Build a Feed Factory candidate spec (recession-monitor-v2.feed-discovery-spec.v1)
for a resolved connector. Candidates are conservative by construction:
candidate_only / reviewed=false / scientific_admission=false / public_eligible=false,
and activation.scientific_effect="none". No credentials are ever included.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from .parsers import Normalized
from .registry import ConnectorSpec

SCHEMA = "recession-monitor-v2.feed-discovery-spec.v1"


def _observation_latest(coverage_last: str) -> str:
    # normalize "2025-M12" (BLS) / "2026-06" (OECD) / "2026-06-01" (FRED) to a display period
    return coverage_last


def build_candidate(
    spec: ConnectorSpec,
    normalized: Normalized,
    raw_sha256: str,
    raw_bytes: int,
    retrieval_ts: str,
    validation_ts: str,
    stale: bool = False,
    credential_free_endpoint: Optional[str] = None,
) -> Dict[str, Any]:
    endpoint = credential_free_endpoint if credential_free_endpoint is not None else spec.url_template
    if "{key}" in endpoint:
        endpoint = endpoint.replace("&api_key={key}", "").replace("api_key={key}&", "").replace("{key}", "")
    return {
        "schema_version": SCHEMA,
        "connector_id": spec.connector_id,
        "candidate_status": {
            "candidate_only": True,
            "reviewed": False,
            "scientific_admission": False,
            "public_eligible": False,
        },
        "activation": {
            "scientific_effect": "none",
            "website_effect": "none_until_reviewed",
        },
        "reservation": {
            "action": "supersede_legacy_identity",
            "legacy_source_id": spec.legacy_id,
            "canonical_source_id": spec.canonical_id,
        },
        "identity_transition": {
            "legacy_id": spec.legacy_id,
            "legacy_status": "malformed_html_orphan_superseded",
            "canonical_id": spec.canonical_id,
            "confidence": spec.identity_confidence,
            "evidence": list(spec.identity_evidence),
        },
        "source": {
            "adapter": spec.publisher_kind,
            "publisher": spec.originating_publisher,
            "survey": spec.survey,
            "provider_code": spec.provider_code,
            "endpoint": endpoint,
            "allowed_hosts": list(spec.allowed_hosts),
            "expected_content_types": list(spec.expected_content_types),
            "label": spec.title,
            "units": spec.units,
            "frequency": spec.frequency,
            "seasonal_adjustment": spec.seasonal_adjustment,
            "information_set_mode": spec.information_set_mode,
            "rights_status": spec.rights_status,
            "enabled": False,
        },
        "clocks": {
            "observation_latest": _observation_latest(normalized.coverage[1]),
            "provider_availability": normalized.provider_availability,
            "retrieval": retrieval_ts,
            "validation": validation_ts,
            "release_schedule": spec.publisher_release_clock,
            "stale": bool(stale),
        },
        "coverage": {"first": normalized.coverage[0], "last": normalized.coverage[1]},
        "observation_count": normalized.count,
        "latest_value": normalized.latest_value,
        "raw_sha256": raw_sha256,
        "raw_bytes": raw_bytes,
    }
