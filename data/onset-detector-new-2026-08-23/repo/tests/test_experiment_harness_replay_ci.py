"""RED-first tests for the replay-CI prototype (B-EXP-0 deliverable 4, improvement 49) and
the concrete store loader.

The CI prototype picks a random past date, replays, and asserts the replayed artifact is
byte-identical to the published one. It is wired to NOTHING yet: replay_fn/publish_fn are
injected, and the defaults raise so the not-yet-adopted status is explicit and safe. Nightly
adoption is a later owner-approved batch.
"""
import datetime as dt
import os
import random

import pytest

from contrib.experiment_harness import replay_ci
from contrib.experiment_harness.asof_replay import build_store_loader


def test_select_replay_date_is_deterministic_with_seed_and_in_past():
    rng = random.Random(1234)
    today = dt.date(2026, 8, 5)
    d1 = replay_ci.select_replay_date(rng, dt.date(2012, 1, 1), today)
    rng2 = random.Random(1234)
    d2 = replay_ci.select_replay_date(rng2, dt.date(2012, 1, 1), today)
    assert d1 == d2
    assert dt.date(2012, 1, 1) <= d1 < today


def test_canonicalize_is_key_order_independent():
    a = replay_ci.canonicalize({"b": 2, "a": 1})
    b = replay_ci.canonicalize({"a": 1, "b": 2})
    assert a == b
    assert isinstance(a, bytes)


def test_compare_detects_byte_identical():
    obj = {"index": [1, 2, 3], "asof": "2015-06-15"}
    rep = replay_ci.compare_replay(obj, dict(obj))
    assert rep["byte_identical"] is True
    assert rep["replay_sha256"] == rep["published_sha256"]


def test_compare_detects_divergence():
    rep = replay_ci.compare_replay({"index": [1, 2, 3]}, {"index": [1, 2, 9]})
    assert rep["byte_identical"] is False
    assert rep["replay_sha256"] != rep["published_sha256"]


def test_run_replay_ci_with_injected_fns():
    def replay_fn(d):
        return {"asof": str(d), "v": 1}

    def publish_fn(d):
        return {"asof": str(d), "v": 1}

    rep = replay_ci.run_replay_ci(dt.date(2015, 6, 15), replay_fn, publish_fn)
    assert rep["byte_identical"] is True
    assert rep["asof"] == "2015-06-15"


def test_run_replay_ci_defaults_are_unwired():
    # Not adopted yet: calling without providing the hooks must fail loudly, never silently
    # "pass" a comparison against nothing.
    with pytest.raises(NotImplementedError):
        replay_ci.run_replay_ci(dt.date(2015, 6, 15))


STORE_HEAD = "live_data/runtime/source_heads/fred_w875rx1_fredmd_panel_vintages_deep.json"


@pytest.mark.skipif(not os.path.exists(STORE_HEAD), reason="deep vintage lane not present")
def test_build_store_loader_parses_real_vintage_lane():
    loader = build_store_loader()
    tuples = loader("fred_w875rx1_fredmd_panel_vintages_deep")
    assert len(tuples) > 1000
    asof, obs, val = tuples[0]
    assert isinstance(asof, dt.date)
    assert isinstance(obs, dt.date)
    assert isinstance(val, float)
    # this lane's earliest as-of is 2004 (DEEPASOF20040101)
    assert min(a for a, _o, _v in tuples) <= dt.date(2004, 1, 1)
