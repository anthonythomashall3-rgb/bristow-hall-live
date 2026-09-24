import csv
import json
from pathlib import Path

import pytest

from rmv2_extension.evidence_analysis import analyze_evidence, resolve_input


def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def metric(series_id, parse_status="parsed"):
    return {
        "series_id": series_id,
        "category": "labor_employment",
        "publisher": "bls",
        "provider": "fred",
        "observation_frequency": "monthly",
        "local_1950_coverage_status": "covers_1950",
        "parse_statuses_json": json.dumps([parse_status]),
        "named_vintage_local_status": "not_locally_retained",
        "strict_first_release_local_status": "not_locally_supported",
        "release_clock_status": "exact_release_event_ledger_pending",
        "rights_status": "public_source_reuse_terms_and_attribution_review_required",
    }


def prepare_root(root):
    write_csv(root / "metric_catalog.csv", [metric("PAYEMS"), metric("BROKEN", "html_as_csv")])
    write_csv(root / "local_series_inventory.csv", [{"series_id": "PAYEMS"}, {"series_id": "BROKEN"}])
    write_csv(root / "dataset_catalog.csv", [{
        "dataset_id": "vault", "publisher_or_origin": "recession-monitor-v2", "provider": "local-build",
        "expected_frequency": "mixed", "file_count": "3", "byte_count": "12", "parsed_row_count": "4",
        "parse_statuses_json": json.dumps(["parsed"]), "rights_status": "derived_output_rights_follow_inputs",
        "release_clock_status": "dataset_specific_release_ledger_pending",
    }])
    write_csv(root / "external_source_registry.csv", [{
        "source_id": "held", "access_class": "A", "rights_status": "public_government_data_with_attribution",
        "role": "construction_candidate", "primary_url": "https://example.invalid/held",
    }])
    (root / "county_econ.json").write_text(json.dumps({"data": {"01001": {"hpi": {}, "pcpi": {}, "gdp": {}, "mhi": {}, "poverty": {}}}}), encoding="utf-8")
    (root / "county_hist.json").write_text(json.dumps({"years": [2024, 2025], "annual": {"01001": [3, 4]}, "monthly": {"01001": []}, "mkeys": [], "lfm": {}, "prelim": {}}), encoding="utf-8")
    (root / "county_industry.json").write_text(json.dumps({"years": [2025], "sectors": [{"code": "1011"}], "data": {"01001": {}}}), encoding="utf-8")
    (root / "county_qcew.json").write_text(json.dumps({"qtrs": ["2025Q4"], "data": {"01001": []}}), encoding="utf-8")
    (root / "industry_geo.json").write_text(json.dumps({"sectors": [{"suf": "MFG"}], "m0": "2025-01", "states": {"AL": {}}, "metros": {}}), encoding="utf-8")
    (root / "metro_econ.json").write_text(json.dumps({"metros": {"AL": {"hpi": {}, "gdp": {}}}}), encoding="utf-8")
    (root / "metros.json").write_text(json.dumps({"metros": {"10000": {}}, "missing": [], "capitals": {"AL": "10000"}}), encoding="utf-8")
    (root / "state_econ.json").write_text(json.dumps({"states": {"AL": {}}}), encoding="utf-8")
    (root / "state_metrics.json").write_text(json.dumps({"months": ["2025-01"], "meta": [{"k": "mfg"}], "states": {"AL": {}}}), encoding="utf-8")
    records = [
        {"seq": 0, "as_of": "2025-01-01", "prev": "0" * 64, "hash": "a" * 64, "payload": {}},
        {"seq": 1, "as_of": "2025-01-02", "prev": "a" * 64, "hash": "b" * 64, "payload": {}},
    ]
    (root / "predlog.jsonl").write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")


def test_resolve_input_accepts_identical_numbered_duplicates(tmp_path):
    original = tmp_path / "metric_catalog.csv"
    duplicate = tmp_path / "metric_catalog(1).csv"
    original.write_bytes(b"same")
    duplicate.write_bytes(b"same")
    resolved = resolve_input(tmp_path, "metric_catalog.csv")
    assert resolved.path == original
    assert resolved.identical_duplicate_count == 1


def test_resolve_input_refuses_conflicting_duplicate(tmp_path):
    (tmp_path / "metric_catalog.csv").write_bytes(b"one")
    (tmp_path / "metric_catalog(1).csv").write_bytes(b"two")
    with pytest.raises(ValueError, match="conflicting duplicate"):
        resolve_input(tmp_path, "metric_catalog.csv")


def test_analysis_separates_data_gaps_from_first_release_capabilities(tmp_path):
    prepare_root(tmp_path)
    report = analyze_evidence(tmp_path, generated_at="2026-07-31T00:00:00Z")
    assert report["holdings"]["catalogs"]["represented_series"] == 2
    assert report["holdings"]["storage"]["file_count"] == 3
    assert report["gap_summary"]["data_missing_count"] == 5
    assert report["gap_summary"]["data_missing_entity_count"] == 5
    strict = [item for item in report["gap_registry"]["items"] if item["gap_type"] == "strict_first_release"]
    assert len(strict) == 2
    assert all(item["data_missing"] is False for item in strict)
    assert report["geography"]["county_econ"]["county_count"] == 1
    assert report["forecast_ledger"]["linked_chain"] is True


def test_generated_uploaded_evidence_receipt_has_expected_counts():
    receipt = Path(__file__).resolve().parents[1] / "generated" / "data_holdings_summary.json"
    data = json.loads(receipt.read_text(encoding="utf-8"))
    assert data["holdings"]["storage"]["file_count"] == 27276
    assert data["holdings"]["storage"]["byte_count"] == 842539101
    assert data["holdings"]["storage"]["parsed_row_count"] == 11072029
    assert data["holdings"]["catalogs"]["represented_series"] == 270
    assert data["holdings"]["catalogs"]["external_source_families"] == 134
    assert data["quality"]["malformed_payload_series"] == 17
    assert data["policy"]["publisher_first_release_required_for_data_acquisition"] is False
    assert data["geography"]["county_econ"]["county_count"] == 3142
    assert data["geography"]["metros"]["metro_count"] == 193
    assert data["runtime_reported_state"]["reserved_routes_reported"] == 67
