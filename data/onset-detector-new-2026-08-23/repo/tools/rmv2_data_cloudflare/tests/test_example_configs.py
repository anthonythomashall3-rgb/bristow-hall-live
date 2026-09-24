import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_fetch_examples_only_include_unacquired_direct_bulk_candidates():
    doc = json.loads((ROOT / "config/fetch_recipes.example.json").read_text(encoding="utf-8"))
    ids = {row["recipe_id"] for row in doc["recipes"]}
    assert ids == {
        "eia_930_bulk_2019_present_candidate",
        "eia_930_bulk_pre2019_candidate",
    }
    for row in doc["recipes"]:
        assert "application/x-zip-compressed" in row["allowed_content_types"]


def test_archive_examples_allow_actual_download_hosts_and_paths():
    doc = json.loads((ROOT / "config/archive_discovery.example.json").read_text(encoding="utf-8"))
    rows = {row["archive_id"]: row for row in doc["archives"]}
    for archive_id in ("census_qss_full", "census_qss_advance", "census_qss_benchmark"):
        assert "www2.census.gov" in rows[archive_id]["allowed_hosts"]
    assert rows["dol_ui_weekly_release_archive"]["include_pattern"] == r"/press/"
