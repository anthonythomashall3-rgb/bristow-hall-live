#!/usr/bin/env python3
"""Summarize retained non-series and spatial datasets without duplicating bytes."""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Mapping


SCHEMA_VERSION = "recession-monitor-v2.dataset-catalog.v1"
FIELDS = (
    "schema_version",
    "dataset_id",
    "title",
    "scope",
    "publisher_or_origin",
    "provider",
    "expected_frequency",
    "file_count",
    "byte_count",
    "parsed_row_count",
    "first_observation",
    "last_observation",
    "extensions_json",
    "content_kinds_json",
    "parse_statuses_json",
    "lanes_json",
    "sample_paths_json",
    "release_clock_status",
    "vintage_status",
    "rights_status",
    "notes",
)


METADATA: Mapping[str, Mapping[str, str]] = {
    "data": {
        "title": "Browser/runtime data artifacts",
        "scope": "runtime derived outputs",
        "publisher": "recession-monitor-v2",
        "provider": "local-build",
        "frequency": "mixed",
        "rights": "derived_output_rights_follow_inputs",
    },
    "data_archive/current_revised_and_spatial/__root__": {
        "title": "National current-revised and reference series",
        "scope": "national",
        "publisher": "mixed",
        "provider": "mostly-fred-plus-publisher-direct",
        "frequency": "daily_to_annual",
        "rights": "source_specific_rights_review_required",
    },
    "data_archive/current_revised_and_spatial/cand": {
        "title": "Exploratory national candidate series",
        "scope": "national research",
        "publisher": "mixed",
        "provider": "fred",
        "frequency": "mixed",
        "rights": "source_specific_rights_review_required",
    },
    "data_archive/current_revised_and_spatial/county_econ": {
        "title": "County GDP, income, poverty, and house-price measurements",
        "scope": "county",
        "publisher": "bea+census+fhfa",
        "provider": "fred",
        "frequency": "annual_or_quarterly",
        "rights": "public_source_reuse_terms_and_attribution_review_required",
    },
    "data_archive/current_revised_and_spatial/hist": {
        "title": "Long-history national series",
        "scope": "national historical",
        "publisher": "mixed",
        "provider": "fred",
        "frequency": "monthly_or_quarterly",
        "rights": "source_specific_rights_review_required",
    },
    "data_archive/current_revised_and_spatial/ind_metro": {
        "title": "Metro employment by industry",
        "scope": "metro industry",
        "publisher": "bls",
        "provider": "fred",
        "frequency": "monthly",
        "rights": "public_source_reuse_terms_and_attribution_review_required",
    },
    "data_archive/current_revised_and_spatial/ind_state": {
        "title": "State employment by industry",
        "scope": "state industry",
        "publisher": "bls",
        "provider": "fred",
        "frequency": "monthly",
        "rights": "public_source_reuse_terms_and_attribution_review_required",
    },
    "data_archive/current_revised_and_spatial/laucnty_annual": {
        "title": "Local Area Unemployment Statistics county annual files",
        "scope": "county labor",
        "publisher": "bls",
        "provider": "publisher-direct",
        "frequency": "annual",
        "rights": "public_source_reuse_terms_and_attribution_review_required",
    },
    "data_archive/current_revised_and_spatial/metro": {
        "title": "Selected metro labor-market series",
        "scope": "metro labor",
        "publisher": "bls",
        "provider": "fred",
        "frequency": "monthly",
        "rights": "public_source_reuse_terms_and_attribution_review_required",
    },
    "data_archive/current_revised_and_spatial/metro_all": {
        "title": "Broad metro labor-market series",
        "scope": "metro labor",
        "publisher": "bls",
        "provider": "fred",
        "frequency": "monthly",
        "rights": "public_source_reuse_terms_and_attribution_review_required",
    },
    "data_archive/current_revised_and_spatial/metro_econ": {
        "title": "Metro economic activity measurements",
        "scope": "metro economy",
        "publisher": "mixed",
        "provider": "fred",
        "frequency": "mixed",
        "rights": "source_specific_rights_review_required",
    },
    "data_archive/current_revised_and_spatial/phci": {
        "title": "State coincident economic activity indexes",
        "scope": "state composite",
        "publisher": "philadelphia-fed",
        "provider": "fred",
        "frequency": "monthly",
        "rights": "public_source_reuse_terms_and_attribution_review_required",
    },
    "data_archive/current_revised_and_spatial/qcew": {
        "title": "Quarterly Census of Employment and Wages area files",
        "scope": "county and area labor",
        "publisher": "bls",
        "provider": "publisher-direct",
        "frequency": "quarterly",
        "rights": "public_source_reuse_terms_and_attribution_review_required",
    },
    "data_archive/current_revised_and_spatial/qcew_ind": {
        "title": "Quarterly Census of Employment and Wages industry files",
        "scope": "county and area industry",
        "publisher": "bls",
        "provider": "publisher-direct",
        "frequency": "quarterly",
        "rights": "public_source_reuse_terms_and_attribution_review_required",
    },
    "data_archive/current_revised_and_spatial/quarantine": {
        "title": "Quarantined source candidates and error responses",
        "scope": "nonadmissible",
        "publisher": "mixed",
        "provider": "mixed",
        "frequency": "not_applicable",
        "rights": "not_admissible",
    },
    "data_archive/current_revised_and_spatial/source_watch": {
        "title": "Spatial-source refresh state",
        "scope": "operational metadata",
        "publisher": "recession-monitor-v2",
        "provider": "local-refresh",
        "frequency": "per_refresh",
        "rights": "local_metadata",
    },
    "data_archive/current_revised_and_spatial/states": {
        "title": "State labor, claims, permits, income, GDP, prices, and population",
        "scope": "state economy",
        "publisher": "bls+bea+census+fhfa+philadelphia-fed",
        "provider": "fred",
        "frequency": "weekly_to_annual",
        "rights": "public_source_reuse_terms_and_attribution_review_required",
    },
    "data_archive/current_revised_and_spatial/vintages": {
        "title": "Named provider-vintage snapshots",
        "scope": "national point-in-time candidates",
        "publisher": "mixed",
        "provider": "alfred",
        "frequency": "snapshot",
        "rights": "source_specific_rights_review_required",
    },
    "data_archive/additional_vintages/ohw3": {
        "title": "Dense provider snapshot panel",
        "scope": "national point-in-time candidates",
        "publisher": "mixed",
        "provider": "alfred-compatible-provider",
        "frequency": "snapshot",
        "rights": "source_specific_rights_review_required",
    },
    "data_archive/additional_vintages/bea_cache": {
        "title": "BEA historical release workbooks",
        "scope": "national publisher releases",
        "publisher": "bea",
        "provider": "publisher-direct",
        "frequency": "release",
        "rights": "public_source_reuse_terms_and_attribution_review_required",
    },
    "data_archive/additional_vintages/bea_extracted": {
        "title": "Parsed BEA historical release tables",
        "scope": "national publisher releases",
        "publisher": "bea",
        "provider": "local-parser",
        "frequency": "release",
        "rights": "derived_from_public_source_review_required",
    },
    "data_archive/additional_vintages/fred_md_official": {
        "title": "Official FRED-MD historical vintage panels",
        "scope": "national monthly provider-vintage panel",
        "publisher": "federal-reserve-bank-of-st-louis",
        "provider": "fred-md",
        "frequency": "monthly_vintage",
        "rights": "fred_terms_and_underlying_publisher_rights_control",
    },
    "data_archive/additional_vintages/fred_qd_official": {
        "title": "Official FRED-QD historical vintage panels",
        "scope": "national quarterly provider-vintage panel",
        "publisher": "federal-reserve-bank-of-st-louis",
        "provider": "fred-qd",
        "frequency": "monthly_vintage_of_quarterly_panel",
        "rights": "fred_terms_and_underlying_publisher_rights_control",
    },
    "data_archive/derived_original": {
        "title": "Original monitor derived artifacts",
        "scope": "derived model outputs",
        "publisher": "bristow-hall",
        "provider": "local-build",
        "frequency": "mixed",
        "rights": "derived_output_rights_follow_inputs",
    },
    "method_source": {
        "title": "Original methods, code, fixtures, and research artifacts",
        "scope": "methods and provenance",
        "publisher": "bristow-hall",
        "provider": "local-filesystem",
        "frequency": "not_applicable",
        "rights": "local_project_material",
    },
}


def dataset_id(path: str) -> str:
    parts = Path(path).parts
    if parts[0] in {"data", "method_source"}:
        return parts[0]
    if parts[:2] == ("data_archive", "derived_original"):
        return "data_archive/derived_original"
    if parts[:3] == ("data_archive", "additional_vintages", "ohw3"):
        return "data_archive/additional_vintages/ohw3"
    if parts[:3] == ("data_archive", "additional_vintages", "bea_cache"):
        return "data_archive/additional_vintages/bea_cache"
    if parts[:3] == ("data_archive", "additional_vintages", "bea_extracted"):
        return "data_archive/additional_vintages/bea_extracted"
    if parts[:3] == (
        "data_archive",
        "additional_vintages",
        "fred_md_official",
    ):
        return "data_archive/additional_vintages/fred_md_official"
    if parts[:3] == (
        "data_archive",
        "additional_vintages",
        "fred_qd_official",
    ):
        return "data_archive/additional_vintages/fred_qd_official"
    if parts[:2] == ("data_archive", "current_revised_and_spatial"):
        if len(parts) == 3:
            return "data_archive/current_revised_and_spatial/__root__"
        return "/".join(parts[:3])
    return "/".join(parts[:-1]) if len(parts) > 1 else parts[0]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
    )
    args = parser.parse_args()
    root = args.root.resolve()
    input_path = root / "data_vault/manifests/local_file_inventory.csv"
    with input_path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    groups: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    for row in rows:
        groups[dataset_id(row["path"])].append(row)

    output_rows: List[Dict[str, object]] = []
    for identifier, members in sorted(groups.items()):
        meta = METADATA.get(identifier, {})
        dates = [
            (row["first_observation_date"], row["last_observation_date"])
            for row in members
            if row["first_observation_date"] and row["last_observation_date"]
        ]
        lanes = sorted({row["lane"] for row in members})
        output_rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "dataset_id": identifier,
                "title": meta.get("title", identifier),
                "scope": meta.get("scope", "unclassified"),
                "publisher_or_origin": meta.get("publisher", "unresolved"),
                "provider": meta.get("provider", "unresolved"),
                "expected_frequency": meta.get("frequency", "unresolved"),
                "file_count": len(members),
                "byte_count": sum(int(row["byte_count"]) for row in members),
                "parsed_row_count": sum(
                    int(row["row_count"])
                    for row in members
                    if row["row_count"].isdigit()
                ),
                "first_observation": min(first for first, _ in dates) if dates else "",
                "last_observation": max(last for _, last in dates) if dates else "",
                "extensions_json": json.dumps(
                    sorted({row["extension"] for row in members}), separators=(",", ":")
                ),
                "content_kinds_json": json.dumps(
                    sorted({row["content_kind"] for row in members}), separators=(",", ":")
                ),
                "parse_statuses_json": json.dumps(
                    sorted({row["parse_status"] for row in members}), separators=(",", ":")
                ),
                "lanes_json": json.dumps(lanes, separators=(",", ":")),
                "sample_paths_json": json.dumps(
                    sorted(row["path"] for row in members)[:10],
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
                "release_clock_status": "dataset_specific_release_ledger_pending",
                "vintage_status": (
                    "retained_snapshots_not_automatically_first_release"
                    if any("vintage" in lane or "snapshot" in lane for lane in lanes)
                    else "current_or_not_applicable"
                ),
                "rights_status": meta.get(
                    "rights", "source_specific_rights_review_required"
                ),
                "notes": (
                    "Contains nonadmissible HTML/empty/error objects; see anomaly manifest."
                    if any(
                        row["parse_status"] in {"html_masquerading_as_csv", "empty_file"}
                        or row["parse_status"].startswith("csv_error:")
                        for row in members
                    )
                    else ""
                ),
            }
        )

    output_path = root / "data_vault/catalog/dataset_catalog.csv"
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(output_rows)
    print(
        json.dumps(
            {
                "schema_version": SCHEMA_VERSION,
                "datasets": len(output_rows),
                "files": sum(int(row["file_count"]) for row in output_rows),
                "bytes": sum(int(row["byte_count"]) for row in output_rows),
                "output": output_path.relative_to(root).as_posix(),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
