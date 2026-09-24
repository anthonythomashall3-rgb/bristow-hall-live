"""B-EXT-1948 guard: the 1948 lane must stay a DISTINCT, never-merged, never-fitted
validation lane (CH-R102 DIFFERENT-INSTRUMENT verdict + owner never-merged ruling).

Guards STRUCTURE/SEPARATION only. Does NOT pin detector sigma values or thresholds
(pinning those would risk §18.1 masking a real change to index_v1)."""
import json
from pathlib import Path

R = Path(__file__).resolve().parents[1] / "research" / "ext1948"


def _load(name):
    return json.loads((R / name).read_text())


def test_validation_lane_is_distinct_never_merged_never_fitted():
    vl = _load("validation_lane.v1.json")
    assert vl["lane_label"] == "validation_only_1948_analog_lane"
    assert vl["information_set_mode"] == "validation_only"
    assert vl["distinct_third_lane"] is True
    assert vl["never_merged_into_headline"] is True
    assert vl["never_fitted"] is True
    assert vl["carries_no_realtime_claim"] is True


def test_1948_is_three_member_three_channel_different_instrument():
    vl = _load("validation_lane.v1.json")
    cov = vl["anchor_coverage"]["1948-01-01"]
    assert cov["n_members"] == 3
    assert cov["weight_share"] == 0.75
    assert set(cov["channels_nonempty"]) == {"creditequity", "labor", "realactivity"}


def test_coverage_manifest_and_gap_map_are_distinct_lane_scoped():
    for name in ("coverage_manifest.v1.json", "gap_map.v1.json"):
        d = _load(name)
        assert d["lane_label"] == "validation_only_1948_analog_lane"
        assert d["distinct_third_lane"] is True
        assert d["never_merged"] is True


def test_detector_fires_on_all_three_added_recessions():
    vl = _load("validation_lane.v1.json")
    for theta in ("0.5sigma", "1.0sigma"):
        fires = vl["detector_results"][theta]["recession_fires"]
        assert set(fires) == {"1948-49", "1953-54", "1957-58"}
        assert all(f["fired"] for f in fires.values())
