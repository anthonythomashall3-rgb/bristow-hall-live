"""Unit tests for the as-of daily observed information-state surface (instrument.v2.g1).

Covers: cutoff-governed observed state (no future periods / no future revisions),
native-frequency preservation + typed staleness (no forward-fill of an actual),
g1 transform fidelity, E12 energy math, and the REQUIRED synthetic revision-flip
fixture (a known revision flip moves the as-of path and NOT the final path).
"""
import datetime as dt
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "model_authority" / "temporal"))

from asof_surface import (  # noqa: E402
    ObsRecord,
    daily_observed_information_state,
    daily_carry,
    MemberSpec,
    reconstruct_P_asof,
    reconstruct_E_asof,
    TRANSFORMS,
    BAR_E,
    RESET,
)
from asof_surface.surface import yoy, BAR_E as _BAR, RESET as _RESET  # noqa: E402

FIXTURE = ROOT / "tests" / "fixtures" / "asof_surface" / "revision_flip.v1.json"


def _daterange(a, b):
    d = a
    while d <= b:
        yield d
        d += dt.timedelta(days=1)


def _d(s):
    return dt.date.fromisoformat(s)


# --------------------------------------------------------------------------
# 1. observed information state — cutoff governance
# --------------------------------------------------------------------------

def _records():
    fx = json.loads(FIXTURE.read_text())
    recs = [
        ObsRecord(
            reference_period_end=_d(r["reference_period_end"]),
            value=r["value"],
            available_at=_d(r["available_at"]),
            vintage_label=r["vintage_label"],
        )
        for r in fx["asof_vintage_records"]
    ]
    return fx, recs


def test_observed_state_picks_asof_vintage_not_later_revision():
    fx, recs = _records()
    cutoff = _d(fx["decision_cutoff"])  # 2022-03-01
    state = daily_observed_information_state(recs, cutoff, native_frequency="monthly")
    flip = _d(fx["flip_reference_period"])  # 2022-01-01
    # the value in effect as-of the cutoff is the WEAK first release, not the
    # revised-up value that only becomes available after the cutoff.
    assert state["period_index"][flip] == fx["asof_value_before_cutoff"] == 95.0
    # the post-cutoff revision (available 2022-04-15) is invisible.
    assert all(o["available_at"] <= fx["decision_cutoff"] for o in state["observations"])


def test_observed_state_excludes_future_periods_and_future_releases():
    fx, recs = _records()
    cutoff = _d(fx["decision_cutoff"])  # 2022-03-01
    state = daily_observed_information_state(recs, cutoff)
    ends = [o["reference_period_end"] for o in state["observations"]]
    # 2022-02 exists as a period <= cutoff, but its first release (~2022-03-15) is
    # after the cutoff, so it must NOT appear (no future release leakage).
    assert "2022-02-01" not in ends
    # nothing dated after the cutoff appears.
    assert max(ends) == fx["flip_reference_period"]


def test_staleness_typed_and_nonnegative():
    fx, recs = _records()
    cutoff = _d(fx["decision_cutoff"])
    state = daily_observed_information_state(recs, cutoff)
    # last release is the flip period's first release, 2022-02-15.
    assert state["last_release_at"] == "2022-02-15"
    assert state["staleness_days"] == (cutoff - _d("2022-02-15")).days == 14


# --------------------------------------------------------------------------
# 2. no forward-fill of an actual; daily carry is typed
# --------------------------------------------------------------------------

def test_observations_are_native_actuals_only():
    fx, recs = _records()
    state = daily_observed_information_state(recs, _d(fx["decision_cutoff"]))
    assert all(o["value_status"] == "actual" for o in state["observations"])
    assert all(o["native_frequency"] == "monthly" for o in state["observations"])
    # one row per released reference period — NOT one row per day.
    ends = [o["reference_period_end"] for o in state["observations"]]
    assert len(ends) == len(set(ends))
    assert len(ends) < 60  # monthly cadence, not daily


def test_daily_carry_is_typed_projection_not_a_new_actual():
    fx, recs = _records()
    state = daily_observed_information_state(recs, _d(fx["decision_cutoff"]))
    carried = daily_carry(state, _d("2022-02-20"))  # between monthly periods
    assert carried["value_status"] == "carried_for_computation"
    assert carried["carried"] is True
    assert carried["as_of_reference_period_end"] == "2022-01-01"
    assert carried["value"] == 95.0
    assert carried["carry_age_days"] == (_d("2022-02-20") - _d("2022-01-01")).days
    # before the first released period -> None (never fabricate an actual).
    assert daily_carry(state, _d("2018-01-01")) is None


# --------------------------------------------------------------------------
# 3. g1 transform + energy constants fidelity
# --------------------------------------------------------------------------

def test_yoy_matches_hand_computation():
    s = {dt.date(2020, 1, 1): 100.0, dt.date(2021, 1, 1): 110.0, dt.date(2022, 1, 1): 99.0}
    out = yoy(s)
    assert out[dt.date(2021, 1, 1)] == pytest.approx(10.0)
    assert out[dt.date(2022, 1, 1)] == pytest.approx(-10.0)
    # neg_yoy flips the sign (output down = recessionary up).
    neg = TRANSFORMS["neg_yoy"](s)
    assert neg[dt.date(2022, 1, 1)] == pytest.approx(10.0)


def test_energy_constants_match_energy_build():
    assert (BAR_E, RESET) == (7.5, 2.0)
    assert (_BAR, _RESET) == (7.5, 2.0)


# --------------------------------------------------------------------------
# 4. REQUIRED synthetic fixture — revision flip moves as-of, not final
# --------------------------------------------------------------------------

def _paths_for(flip_value):
    """Build E_asof (flip_value at the flip period) and E_final (revised value),
    identical code and identical period set, differing ONLY in the flip period."""
    fx = json.loads(FIXTURE.read_text())
    member = MemberSpec(**fx["member"])
    cutoff = _d(fx["decision_cutoff"])

    # as-of observed state gives the period set governed by the cutoff.
    recs = [
        ObsRecord(_d(r["reference_period_end"]), r["value"], _d(r["available_at"]), r["vintage_label"])
        for r in fx["asof_vintage_records"]
    ]
    state = daily_observed_information_state(recs, cutoff)
    period_index = dict(state["period_index"])
    flip_period = _d(fx["flip_reference_period"])

    asof_raw = dict(period_index)
    asof_raw[flip_period] = flip_value                       # governed as-of value
    final_raw = dict(period_index)
    final_raw[flip_period] = fx["revised_value_after_cutoff"]  # current_revised truth

    ex = fx["baseline_exclusion_window"]
    lo, hi = _d(ex["start"]), _d(ex["end"])
    is_baseline = lambda d: not (lo <= d <= hi)  # noqa: E731
    grid = list(_daterange(_d(fx["daily_grid"]["start"]), cutoff))

    def energy(raw):
        line = reconstruct_P_asof({member.series_id: raw}, [member], grid, is_baseline)
        return reconstruct_E_asof(line, is_baseline)

    E_asof = energy(asof_raw)
    E_final = energy(final_raw)
    last = max(E_asof)
    return E_asof[last], E_final[last]


def test_revision_flip_moves_asof_path_not_final_path():
    fx = json.loads(FIXTURE.read_text())
    asof_v = fx["asof_value_before_cutoff"]        # 95.0 (weak first release)

    e_asof, e_final = _paths_for(asof_v)
    # weak as-of release => strictly MORE accumulated recession stress than the
    # revised-up current_revised path.
    assert e_asof > e_final, (e_asof, e_final)

    # FLIP the vintage value only. The as-of path MOVES; the final path (which
    # never sees the vintage) is INVARIANT.
    e_asof_weaker, e_final_2 = _paths_for(asof_v - 6.0)   # even weaker release
    assert e_asof_weaker > e_asof                         # as-of responded
    assert e_final_2 == pytest.approx(e_final)            # final unchanged

    # setting the vintage equal to the revised value collapses the two lanes.
    e_asof_norev, e_final_3 = _paths_for(fx["revised_value_after_cutoff"])
    assert e_asof_norev == pytest.approx(e_final)
    assert e_final_3 == pytest.approx(e_final)


def test_asof_and_final_use_identical_code():
    # both lanes route through the SAME reconstruct_P_asof / reconstruct_E_asof;
    # equal inputs must give equal outputs (mode-integrity invariance).
    fx = json.loads(FIXTURE.read_text())
    a, b = _paths_for(fx["revised_value_after_cutoff"])
    assert a == pytest.approx(b)
