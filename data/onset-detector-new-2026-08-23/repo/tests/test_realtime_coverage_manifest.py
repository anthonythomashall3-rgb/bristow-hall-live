from __future__ import absolute_import

import json
from pathlib import Path

from live_data.rmv2_live.config import load_config
from model_authority.temporal.build_realtime_coverage_manifest import (
    MEMBER_SERIES,
    vintage_sources_by_series,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = (
    PROJECT_ROOT
    / "model_authority"
    / "temporal"
    / "realtime_coverage_manifest.v1.json"
)


def _manifest():
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def test_committed_member_source_bindings_match_live_config():
    config = load_config(
        PROJECT_ROOT / "live_data" / "config" / "sources.v1.json"
    )
    expected_by_series = vintage_sources_by_series(config)
    expected = {
        member: sorted(expected_by_series.get(series_id, []))
        for member, series_id in MEMBER_SERIES.items()
    }
    actual = {
        member: _manifest()["members"][member]["store_vintage_sources"]
        for member in MEMBER_SERIES
    }
    assert actual == expected


def test_deployed_replay_uses_landed_deep_vintage_members():
    manifest = _manifest()
    rows = {
        row["month"]: set(row["covered_members"])
        for row in manifest["monthly_coverage"]
        if row["month"] in {"2012-06", "2015-09"}
    }
    assert {"ICSA", "IURSA", "NFCI", "W875"}.issubset(rows["2012-06"])
    assert {
        "CMRMT",
        "ICSA",
        "IURSA",
        "NFCI",
        "PHILLY",
        "W875",
    }.issubset(rows["2015-09"])


def test_reported_available_weight_preserves_coverage_thinness():
    manifest = _manifest()
    total_channel_weight = sum(
        channel["weight"] for channel in manifest["channels"].values()
    )
    assert total_channel_weight > 0

    for row in manifest["monthly_coverage"]:
        expected = round(
            row["available_channel_weight_raw"] / total_channel_weight, 10
        )
        assert row["renormalized_available_weight"] == expected, row["month"]

    first = manifest["monthly_coverage"][0]
    assert first["renormalized_available_weight"] < 1.0
