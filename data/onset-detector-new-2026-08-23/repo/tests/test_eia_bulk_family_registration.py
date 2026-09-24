import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FAMILIES = {
    "eia_bulk_elec": ("eia_electricity", "ELEC.zip"),
    "eia_bulk_coal": ("eia_coal", "COAL.zip"),
    "eia_bulk_intl": ("eia_international", "INTL.zip"),
    "eia_bulk_seds": ("eia_seds", "SEDS.zip"),
    "eia_bulk_total": ("eia_total_energy", "TOTAL.zip"),
    "eia_bulk_emiss": ("eia_emissions", "EMISS.zip"),
    "eia_bulk_nuc_status": ("eia_nuclear_outages", "NUC_STATUS.zip"),
    "eia_bulk_aeo2026": ("eia_aeo", "AEO2026.zip"),
}


def test_prepared_eia_bulk_products_have_distinct_registered_families():
    with (ROOT / "data_vault/catalog/external_source_registry.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        registry = {row["source_id"]: row for row in csv.DictReader(handle)}
    planned_doc = json.loads(
        (ROOT / "live_data/config/planned_sources.v1.json").read_text()
    )
    planned = {row["source_id"]: row for row in planned_doc["sources"]}

    for source_id, (family_id, archive) in FAMILIES.items():
        assert family_id in registry
        assert registry[family_id]["publisher"] == "EIA"
        assert registry[family_id]["rights_status"] == (
            "EIA_use_with_attribution_and_third_party_exceptions"
        )
        assert planned[source_id]["coverage_source_family_ids"] == [family_id]
        assert planned[source_id]["endpoint"] == f"https://api.eia.gov/bulk/{archive}"
        assert planned[source_id]["enabled"] is False

    assert planned_doc["scope"]["reservation_count"] == len(planned_doc["sources"])
