import json

from rmv2_extension.gap_registry import build_registry, summarize_registry


def metric(series_id, **overrides):
    row = {
        "series_id": series_id,
        "category": "labor",
        "publisher": "bls",
        "provider": "fred",
        "observation_frequency": "monthly",
        "local_1950_coverage_status": "covers_1950",
        "parse_statuses_json": json.dumps(["parsed"]),
        "named_vintage_local_status": "not_locally_retained",
        "strict_first_release_local_status": "not_locally_supported",
        "release_clock_status": "exact_release_event_ledger_pending",
        "rights_status": "public_source_reuse_terms_and_attribution_review_required",
    }
    row.update(overrides)
    return row


def test_first_release_is_capability_gap_not_missing_data():
    registry = build_registry([metric("PAYEMS")], [], [], [], include_strict_realtime=True)
    item = next(i for i in registry["items"] if i["gap_type"] == "strict_first_release")
    assert item["data_missing"] is False
    assert item["gap_class"] == "capability"
    assert item["priority"] == "P3"


def test_malformed_html_payload_is_high_priority_evidence_gap():
    registry = build_registry(
        [metric("BROKEN", parse_statuses_json=json.dumps(["html_as_csv"]))],
        [], [], [], include_strict_realtime=False,
    )
    item = next(i for i in registry["items"] if i["gap_type"] == "malformed_payload")
    assert item["priority"] == "P0"
    assert item["data_missing"] is True
    assert item["automatable"] is True


def test_unknown_frequency_and_publisher_are_metadata_not_acquisition():
    registry = build_registry(
        [metric("UNKNOWN", observation_frequency="unresolved", publisher="unknown")],
        [], [], [], include_strict_realtime=False,
    )
    selected = [i for i in registry["items"] if i["gap_type"] in {"frequency_metadata", "publisher_metadata"}]
    assert {i["gap_type"] for i in selected} == {"frequency_metadata", "publisher_metadata"}
    assert all(not i["data_missing"] for i in selected)


def test_explicit_known_reservations_become_acquisition_queue():
    registry = build_registry([], [], [], [], include_known_reservations=True)
    ids = {i["entity_id"] for i in registry["items"] if i["gap_class"] == "acquisition"}
    assert ids == {
        "eia_930",
        "dol_ui_weekly_claims_release_archive",
        "treasury_dts_legacy_withholding",
        "census_qss_release_archives",
    }


def test_rights_blocker_is_not_silently_marked_automatable():
    registry = build_registry(
        [metric("LICENSED", rights_status="restricted_or_licensing_review_required")],
        [], [], [], include_strict_realtime=False,
    )
    item = next(i for i in registry["items"] if i["gap_type"] == "rights_review")
    assert item["automatable"] is False
    assert "rights" in item["blockers"]


def test_registry_is_deterministic_and_summary_separates_true_data_gaps():
    rows = [
        metric("B", parse_statuses_json=json.dumps(["html_as_csv"])),
        metric("A", observation_frequency="unresolved"),
    ]
    first = build_registry(rows, [], [], [], include_strict_realtime=False)
    second = build_registry(list(reversed(rows)), [], [], [], include_strict_realtime=False)
    assert first == second
    summary = summarize_registry(first)
    assert summary["data_missing_count"] == 1
    assert summary["data_missing_entity_count"] == 1
    assert summary["metadata_gap_count"] >= 1
