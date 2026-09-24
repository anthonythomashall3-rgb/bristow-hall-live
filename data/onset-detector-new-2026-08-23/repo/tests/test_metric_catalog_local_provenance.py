import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _catalog_row(series_id):
    with (ROOT / "data_vault/catalog/metric_catalog.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        return next(row for row in csv.DictReader(handle) if row["series_id"] == series_id)


def test_local_yield_curve_probability_is_not_attributed_to_new_york_fed():
    row = _catalog_row("nyfed_recession_prob")

    assert row["publisher"] == "bristow-hall-local-derivation"
    assert row["provider"] == "bristow-hall-local-derivation"
    assert row["title"] == "Locally derived 12-month yield-curve recession probability"
    assert row["rights_status"] == "locally_derived_from_public_inputs_with_attribution"
    assert "not the New York Fed published series" in row["notes"]


def test_fdic_failure_asset_unit_is_pinned_to_official_api_unit():
    row = _catalog_row("fdic_failures_by_year")

    assert row["units"] == "failures_count_and_assets_thousands_of_us_dollars"
    assert "QBFASSET" in row["notes"]
