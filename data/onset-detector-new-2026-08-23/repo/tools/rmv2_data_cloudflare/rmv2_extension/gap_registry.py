"""Build a deterministic registry of Recession Monitor V2 data gaps.

The registry intentionally distinguishes absent economic observations from
metadata, timing, vintage, and rights capabilities. Publisher-first-release
proof is optional for ordinary collection and required only for strict
historical real-time claims.
"""
from __future__ import annotations

import json
from collections import Counter
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

SCHEMA_VERSION = "recession-monitor-v2.data-gap-registry.v1"

KNOWN_RESERVATIONS = (
    {
        "entity_id": "eia_930",
        "priority": "P0",
        "evidence": "V2 README identifies EIA-930 as a planned P0 adapter",
        "recommended_action": "add official EIA bulk/API collection with hourly clock and revision semantics",
        "source_url": "https://www.eia.gov/electricity/gridmonitor/about",
    },
    {
        "entity_id": "dol_ui_weekly_claims_release_archive",
        "priority": "P0",
        "evidence": "V2 README identifies the national Thursday claims release archive as planned",
        "recommended_action": "capture official archived releases separately from ETA-539 operational data",
        "source_url": "https://oui.doleta.gov/unemploy/archive.asp",
    },
    {
        "entity_id": "treasury_dts_legacy_withholding",
        "priority": "P1",
        "evidence": "V2 README keeps the pre-2023-02-14 withholding concept as a separate identity",
        "recommended_action": "collect and preserve the legacy concept without splicing it to the current concept",
        "source_url": "https://fiscaldata.treasury.gov/datasets/daily-treasury-statement/",
    },
    {
        "entity_id": "census_qss_release_archives",
        "priority": "P1",
        "evidence": "V2 README keeps QSS advance, full, and benchmark releases in separate planned lanes",
        "recommended_action": "add release-specific archive collectors and keep release stages distinct",
        "source_url": "https://www.census.gov/services/qss/reports.html",
    },
)

_PRIORITY_ORDER = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}


def _json_list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value
    if value in (None, ""):
        return []
    try:
        parsed = json.loads(str(value))
    except (TypeError, ValueError):
        return [str(value)]
    return parsed if isinstance(parsed, list) else [parsed]


def _item(
    gap_type: str,
    gap_class: str,
    entity_type: str,
    entity_id: str,
    priority: str,
    data_missing: bool,
    automatable: bool,
    evidence: str,
    recommended_action: str,
    blockers: Optional[Sequence[str]] = None,
    source_url: str = "",
) -> Dict[str, Any]:
    return {
        "gap_id": "%s:%s:%s" % (gap_class, gap_type, entity_id),
        "gap_type": gap_type,
        "gap_class": gap_class,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "priority": priority,
        "data_missing": bool(data_missing),
        "automatable": bool(automatable),
        "status": "OPEN",
        "evidence": evidence,
        "recommended_action": recommended_action,
        "blockers": sorted(set(blockers or [])),
        "source_url": source_url,
    }


def _metric_items(row: Mapping[str, Any], include_strict_realtime: bool) -> List[Dict[str, Any]]:
    sid = str(row.get("series_id") or "UNKNOWN")
    items: List[Dict[str, Any]] = []
    parse_statuses = {str(v).lower() for v in _json_list(row.get("parse_statuses_json"))}
    if any("html" in value or "nonadmissible" in value or "parse_error" in value for value in parse_statuses):
        items.append(_item(
            "malformed_payload", "evidence", "series", sid, "P0", True, True,
            "local bytes exist but parse status is %s" % sorted(parse_statuses),
            "re-fetch from the official route, validate identity/content, and quarantine malformed bytes",
        ))
    if str(row.get("local_1950_coverage_status") or "") == "unknown_unparsed":
        items.append(_item(
            "coverage_unknown", "coverage", "series", sid, "P0", True, True,
            "coverage is unknown because the local payload is unparsed",
            "repair parsing and recompute first/last observation coverage",
        ))
    if str(row.get("observation_frequency") or "") in ("", "unresolved", "unknown"):
        items.append(_item(
            "frequency_metadata", "metadata", "series", sid, "P1", False, True,
            "observation frequency is unresolved",
            "resolve frequency from the originating publisher or exact provider metadata",
        ))
    if str(row.get("publisher") or "") in ("", "unknown", "unresolved"):
        items.append(_item(
            "publisher_metadata", "metadata", "series", sid, "P1", False, True,
            "originating publisher is unresolved",
            "resolve the publisher while retaining provider as a separate field",
        ))
    if str(row.get("category") or "") in ("", "unclassified_quantitative"):
        items.append(_item(
            "semantic_category", "metadata", "series", sid, "P2", False, True,
            "economic category is unclassified",
            "assign a reviewed economic channel without changing source observations",
        ))
    release = str(row.get("release_clock_status") or "")
    if release in ("", "unknown", "unresolved") or "pending" in release:
        items.append(_item(
            "release_event_ledger", "timing", "series", sid, "P2", False, True,
            "exact release-event ledger is pending",
            "capture future releases prospectively and link historical events when available",
        ))
    rights = str(row.get("rights_status") or "")
    if any(word in rights for word in ("restricted", "licensing", "source_specific")):
        items.append(_item(
            "rights_review", "rights", "series", sid, "P1", False, False,
            "rights status requires source-specific or licensing review: %s" % rights,
            "review exact terms before public or scientific promotion", blockers=["rights"],
        ))
    elif "review_required" in rights:
        items.append(_item(
            "rights_review", "rights", "series", sid, "P2", False, False,
            "attribution/reuse review remains open: %s" % rights,
            "record attribution and public-export eligibility", blockers=["rights"],
        ))
    if include_strict_realtime:
        named = str(row.get("named_vintage_local_status") or "")
        if named in ("", "not_locally_retained"):
            items.append(_item(
                "named_vintage", "capability", "series", sid, "P3", False, True,
                "no locally retained named provider-vintage lane",
                "add provider snapshots only where strict historical replay justifies the cost",
            ))
        strict = str(row.get("strict_first_release_local_status") or "")
        if strict not in ("supported", "complete", "proven"):
            items.append(_item(
                "strict_first_release", "capability", "series", sid, "P3", False, False,
                "strict publisher-first-release proof is not locally complete",
                "retain as an optional real-time-validation capability; do not classify the economic data as missing",
                blockers=["historical_release_evidence"],
            ))
    return items


def _dataset_items(row: Mapping[str, Any]) -> List[Dict[str, Any]]:
    dataset_id = str(row.get("dataset_id") or "UNKNOWN")
    items: List[Dict[str, Any]] = []
    if str(row.get("publisher_or_origin") or "") in ("", "unresolved"):
        items.append(_item(
            "dataset_origin_metadata", "metadata", "dataset", dataset_id, "P1", False, True,
            "dataset publisher/origin is unresolved",
            "resolve dataset lineage from constituent files and receipts",
        ))
    if str(row.get("provider") or "") in ("", "unresolved"):
        items.append(_item(
            "dataset_provider_metadata", "metadata", "dataset", dataset_id, "P1", False, True,
            "dataset provider is unresolved",
            "resolve retrieval route independently from publisher origin",
        ))
    if str(row.get("expected_frequency") or "") in ("", "unresolved"):
        items.append(_item(
            "dataset_frequency_metadata", "metadata", "dataset", dataset_id, "P2", False, True,
            "dataset frequency is unresolved",
            "resolve the dataset grain or explicitly retain mixed frequency",
        ))
    statuses = {str(v).lower() for v in _json_list(row.get("parse_statuses_json"))}
    if any("html" in value or "parse_error" in value for value in statuses):
        items.append(_item(
            "dataset_malformed_payload", "evidence", "dataset", dataset_id, "P0", True, True,
            "dataset contains malformed or HTML-as-data payloads",
            "identify affected files, quarantine them, and re-fetch from official routes",
        ))
    return items


def _external_items(row: Mapping[str, Any]) -> List[Dict[str, Any]]:
    source_id = str(row.get("source_id") or "UNKNOWN")
    items: List[Dict[str, Any]] = []
    if str(row.get("publisher") or "") in ("", "unknown", "unresolved"):
        items.append(_item(
            "source_publisher_metadata", "metadata", "source_family", source_id, "P2", False, True,
            "external source publisher is unresolved", "resolve publisher identity",
            source_url=str(row.get("primary_url") or ""),
        ))
    if str(row.get("frequency") or "") in ("", "unknown", "unresolved"):
        items.append(_item(
            "source_frequency_metadata", "metadata", "source_family", source_id, "P2", False, True,
            "external source frequency is unresolved", "resolve source cadence and observation grain",
            source_url=str(row.get("primary_url") or ""),
        ))
    access = str(row.get("access_class") or "")
    rights = str(row.get("rights_status") or "")
    if access == "D" or "not_cleared" in rights:
        items.append(_item(
            "source_rights_block", "rights", "source_family", source_id, "P3", False, False,
            "source is explicitly not cleared for storage or publication",
            "retain as a documented blocked family; do not acquire or proxy it",
            blockers=["rights"], source_url=str(row.get("primary_url") or ""),
        ))
    elif access == "C" or any(word in rights.lower() for word in ("licensed", "restricted")):
        items.append(_item(
            "source_access_review", "rights", "source_family", source_id, "P2", False, False,
            "source requires credentials, licensing, or controlled access",
            "do not automate until credentials and rights are explicitly authorized",
            blockers=["credentials_or_rights"], source_url=str(row.get("primary_url") or ""),
        ))
    return items


def build_registry(
    metric_rows: Iterable[Mapping[str, Any]],
    local_rows: Iterable[Mapping[str, Any]],
    dataset_rows: Iterable[Mapping[str, Any]],
    external_rows: Iterable[Mapping[str, Any]],
    include_strict_realtime: bool = True,
    include_known_reservations: bool = False,
    planned_rows: Optional[Iterable[Mapping[str, Any]]] = None,
) -> Dict[str, Any]:
    metrics = list(metric_rows)
    locals_ = list(local_rows)
    datasets = list(dataset_rows)
    externals = list(external_rows)
    items: List[Dict[str, Any]] = []
    for row in metrics:
        items.extend(_metric_items(row, include_strict_realtime))
    for row in datasets:
        items.extend(_dataset_items(row))
    for row in externals:
        items.extend(_external_items(row))

    planned = list(planned_rows or [])
    if planned:
        for row in planned:
            entity_id = str(row.get("source_id") or row.get("id") or "UNKNOWN")
            status = str(row.get("status") or row.get("state") or "planned").lower()
            if status in ("active", "enabled", "complete"):
                continue
            blockers: List[str] = []
            if row.get("requires_credentials") in (True, "true", "1", 1):
                blockers.append("credentials")
            if "review" in str(row.get("rights_status") or ""):
                blockers.append("rights")
            items.append(_item(
                "planned_source", "acquisition", "source", entity_id,
                str(row.get("priority") or "P1"), True, not blockers,
                "source is present in planned-source configuration but not active",
                "prepare and independently review the deterministic source connector",
                blockers=blockers, source_url=str(row.get("primary_url") or row.get("url") or ""),
            ))
    elif include_known_reservations:
        for reservation in KNOWN_RESERVATIONS:
            items.append(_item(
                "planned_source", "acquisition", "source", reservation["entity_id"],
                reservation["priority"], True, True, reservation["evidence"],
                reservation["recommended_action"], source_url=reservation["source_url"],
            ))

    deduped = {item["gap_id"]: item for item in items}
    ordered = sorted(deduped.values(), key=lambda item: (
        _PRIORITY_ORDER.get(item["priority"], 9), item["gap_class"], item["gap_type"], item["entity_id"],
    ))
    return {
        "schema_version": SCHEMA_VERSION,
        "source_counts": {
            "metric_rows": len(metrics), "local_series_rows": len(locals_),
            "dataset_rows": len(datasets), "external_source_rows": len(externals),
            "planned_rows": len(planned),
        },
        "policy": {
            "publisher_first_release_required_for_data_acquisition": False,
            "strict_realtime_capabilities_included": bool(include_strict_realtime),
        },
        "items": ordered,
    }


def summarize_registry(registry: Mapping[str, Any]) -> Dict[str, Any]:
    items = list(registry.get("items") or [])
    by_class = Counter(item["gap_class"] for item in items)
    by_priority = Counter(item["priority"] for item in items)
    return {
        "total_gap_items": len(items),
        "data_missing_count": sum(1 for item in items if item.get("data_missing")),
        "data_missing_entity_count": len({item.get("entity_id") for item in items if item.get("data_missing")}),
        "automatable_count": sum(1 for item in items if item.get("automatable")),
        "blocked_count": sum(1 for item in items if item.get("blockers")),
        "metadata_gap_count": by_class.get("metadata", 0),
        "capability_gap_count": by_class.get("capability", 0),
        "by_class": dict(sorted(by_class.items())),
        "by_priority": dict(sorted(by_priority.items())),
    }
