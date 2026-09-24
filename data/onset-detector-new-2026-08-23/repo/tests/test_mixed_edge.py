"""B-MODE-MIXED — mixed_edge composition contract.

Pins the owner's third data-time as a NAMED, DISCLOSED composition: a mixed series
missing a provenance stamp on any point FAILS here (contract rule 6), the four
canonical modes stay untouched, and mixed is never usable for a real-time claim.
"""

import json
from pathlib import Path

import pytest

from bh import mixed_edge as m


ROOT = Path(__file__).resolve().parents[1]
TIMING = ROOT / "data_vault/catalog/timing_model.json"
SCHEMA = ROOT / "data_vault/catalog/mixed_edge_composition.v1.json"

CANONICAL_MODES = [
    "current_revised",
    "archive_snapshot_asof",
    "stitched_strict_first_release",
    "substituted_diagnostic",
]


# ---- rule 1 & 6: per-observation provenance stamp is mandatory --------------

def test_mixed_point_requires_stamp():
    with pytest.raises(m.MixedEdgeError):
        m.MixedPoint("2020-01", 1.0, "")


def test_mixed_point_rejects_foreign_stamp():
    with pytest.raises(m.MixedEdgeError):
        m.MixedPoint("2020-01", 1.0, "made_up_lane")


def test_validate_fails_on_unstamped_point():
    # a mixed series missing a provenance stamp on any point must FAIL (rule 6)
    series = [
        {"reference_period": "2020-01", "value": 1.0, "source_mode": "current_revised"},
        {"reference_period": "2020-02", "value": 2.0},  # no stamp — prohibited
    ]
    with pytest.raises(m.MixedEdgeError):
        m.validate(series)


def test_validate_passes_on_fully_stamped_series():
    series = m.compose({"current_revised": {"2020-01": 1.0, "2020-02": 2.0}})
    m.validate(series)  # must not raise


def test_compose_never_emits_unstamped_point():
    pts = m.compose(
        {
            "stitched_strict_first_release": {"2020-01": 1.0},
            "current_revised": {"2020-02": 2.0},
            "nowcast": {"2020-03": 3.0},
        }
    )
    assert all(p.source_mode in m.STAMP_DOMAIN for p in pts)
    assert len(pts) == 3


# ---- rule 2: fixed precedence, declared not inferred -----------------------

def test_precedence_order_is_pinned():
    assert m.PRECEDENCE == (
        "stitched_strict_first_release",
        "archive_snapshot_asof",
        "current_revised",
        "nowcast",
    )


def test_higher_precedence_lane_wins_same_period():
    pts = m.compose(
        {
            "stitched_strict_first_release": {"2020-01": 10.0},
            "archive_snapshot_asof": {"2020-01": 20.0},
            "current_revised": {"2020-01": 30.0},
        }
    )
    assert len(pts) == 1
    assert pts[0].source_mode == "stitched_strict_first_release"
    assert pts[0].value == 10.0


def test_falls_through_to_next_lane_when_higher_absent():
    pts = m.compose(
        {
            "archive_snapshot_asof": {"2020-02": 20.0},
            "current_revised": {"2020-01": 30.0, "2020-02": 99.0},
        }
    )
    by_period = {p.reference_period: p for p in pts}
    assert by_period["2020-01"].source_mode == "current_revised"
    assert by_period["2020-02"].source_mode == "archive_snapshot_asof"


# ---- rule 3: nowcast fills only uncovered periods --------------------------

def test_nowcast_fills_only_where_no_observed_lane():
    pts = m.compose(
        {
            "current_revised": {"2020-01": 1.0},
            "nowcast": {"2020-01": 99.0, "2020-02": 2.0},
        }
    )
    by_period = {p.reference_period: p for p in pts}
    assert by_period["2020-01"].source_mode == "current_revised"  # observed wins
    assert by_period["2020-02"].source_mode == "nowcast"          # edge fill


def test_reference_periods_argument_fixes_set_and_order():
    pts = m.compose(
        {"current_revised": {"2020-01": 1.0, "2020-03": 3.0}},
        reference_periods=["2020-03", "2020-01", "2020-02"],
    )
    # 2020-02 has no value in any lane -> skipped; order preserved otherwise
    assert [p.reference_period for p in pts] == ["2020-03", "2020-01"]


def test_unknown_lane_rejected():
    with pytest.raises(m.MixedEdgeError):
        m.compose({"not_a_mode": {"2020-01": 1.0}})


# ---- rule 4: coverage summary is the honesty disclosure --------------------

def test_coverage_summary_counts_and_fractions():
    pts = m.compose(
        {
            "stitched_strict_first_release": {"2020-01": 1.0},
            "archive_snapshot_asof": {"2020-02": 2.0},
            "current_revised": {"2020-03": 3.0},
            "nowcast": {"2020-04": 4.0},
        }
    )
    cov = m.coverage_summary(pts)
    assert cov["n_points"] == 4
    assert cov["by_source_mode_counts"] == {
        "stitched_strict_first_release": 1,
        "archive_snapshot_asof": 1,
        "current_revised": 1,
        "nowcast": 1,
    }
    assert abs(sum(cov["by_source_mode_fraction"].values()) - 1.0) < 1e-9


def test_coverage_summary_rejects_unstamped():
    with pytest.raises(m.MixedEdgeError):
        m.coverage_summary([{"reference_period": "2020-01", "value": 1.0}])


# ---- rule 5: never usable for a real-time claim; backtest is pseudo_real_time

def test_official_use_barred_for_realtime_claim():
    assert m.official_use_permitted(for_realtime_claim=True) is False
    assert m.official_use_permitted(for_realtime_claim=False) is True


def test_evaluation_label_is_pseudo_real_time():
    assert m.evaluation_label() == "pseudo_real_time"


# ---- the four canonical modes stay untouched; mixed is a composition -------

def test_four_canonical_modes_unchanged():
    timing = json.loads(TIMING.read_text(encoding="utf-8"))
    assert timing["information_set_modes"] == CANONICAL_MODES


def test_mixed_declared_as_composition_not_a_mode():
    timing = json.loads(TIMING.read_text(encoding="utf-8"))
    mixed = timing["composition_over_modes"]["mixed_edge"]
    assert mixed["is_canonical_mode"] is False
    assert "mixed_edge" not in timing["information_set_modes"]
    assert mixed["schema_ref"] == "data_vault/catalog/mixed_edge_composition.v1.json"


def test_schema_precedence_matches_module():
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    # schema and module agree byte-for-byte on the fixed precedence order.
    assert tuple(schema["fixed_precedence"]["order_high_to_low"]) == m.PRECEDENCE
    assert tuple(
        schema["per_observation_provenance_stamp"]["stamp_domain"]
    ) == m.PRECEDENCE
    assert schema["official_use"][
        "official_use_permitted_for_realtime_claim"
    ] is False
    assert schema["official_use"]["evaluation_timing_label"] == "pseudo_real_time"
