import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_all_src1_candidates_have_owner_ruled_identity_rights_and_handoff():
    candidates = json.loads(
        (ROOT / "live_data/catalog/source_candidates.v1.json").read_text()
    )["candidates"]
    planned = {
        row["source_id"]: row
        for row in json.loads(
            (ROOT / "live_data/config/planned_sources.v1.json").read_text()
        )["sources"]
    }
    with (ROOT / "data_vault/catalog/external_source_registry.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        registered = {row["source_id"] for row in csv.DictReader(handle)}

    pursued = []
    dropped = []
    for candidate in candidates:
        resolution = candidate["resolution"]
        assert resolution["rights_disposition"] != "UNRESOLVED"
        assert "owner 2026-08-05" in resolution["authority"]
        if resolution["ruling"].startswith("PURSUE"):
            pursued.append(candidate["proposed_source_id"])
            reservation_id = resolution["reservation_source_id"]
            family_id = resolution["registered_family"]
            assert family_id in registered
            assert reservation_id in planned
            assert planned[reservation_id]["coverage_source_family_ids"] == [
                family_id
            ]
        else:
            dropped.append(candidate["proposed_source_id"])
            assert resolution["identity"].startswith("NON-IDENTITY")
            assert resolution["registered_family"] is None
            assert resolution["reservation_source_id"] is None

    assert len(pursued) == 4
    assert len(dropped) == 6
