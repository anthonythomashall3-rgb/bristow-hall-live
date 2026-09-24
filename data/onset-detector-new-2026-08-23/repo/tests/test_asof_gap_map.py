from __future__ import absolute_import

import json
from pathlib import Path

from tools.rmv2_data_cloudflare.generated_live.build_asof_gap_map import build


PROJECT_ROOT = Path(__file__).resolve().parents[1]
GAP_MAP_PATH = (
    PROJECT_ROOT
    / "model_authority"
    / "temporal"
    / "asof_surface_gap_map.v1.json"
)
REPLAY_MANIFEST_PATH = (
    PROJECT_ROOT
    / "model_authority"
    / "temporal"
    / "realtime_coverage_manifest.v1.json"
)


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_gap_map_roster_and_vintage_sources_come_from_replay_manifest():
    gap_map = _load(GAP_MAP_PATH)
    replay = _load(REPLAY_MANIFEST_PATH)

    mapped = {member["member_id"]: member for member in gap_map["headline_members"]}
    assert set(mapped) == set(replay["members"])
    assert gap_map["summary"]["headline_member_count"] == replay["member_count"]

    for member_id, replay_member in replay["members"].items():
        assert mapped[member_id]["vintage_sources"] == sorted(
            replay_member["store_vintage_sources"]
        )

    assert "fred_icsa_api_vintages_deep" in mapped["ICSA"]["vintage_sources"]


def test_gap_map_episode_blockers_equal_deployed_replay_coverage():
    gap_map = _load(GAP_MAP_PATH)
    replay = _load(REPLAY_MANIFEST_PATH)
    all_members = set(replay["members"])
    coverage_by_month = {
        row["month"]: set(row["covered_members"])
        for row in replay["monthly_coverage"]
    }
    disturbance = next(
        row
        for row in gap_map["coverage_grid_disturbances"]
        if row["episode_id"] == "dist_2012_13"
    )

    assert set(disturbance["blocking_members"]) == (
        all_members - coverage_by_month["2012-12"]
    )
    assert set(disturbance["available_members"]) == coverage_by_month["2012-12"]


def test_committed_gap_map_matches_canonical_builder():
    assert _load(GAP_MAP_PATH) == build(PROJECT_ROOT)
