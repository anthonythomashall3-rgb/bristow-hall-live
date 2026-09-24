"""RED-first tests for the as-of replay engine (B-EXP-0 deliverable 1).

Generalizes CH-R28's dry-run into a reusable library: given a date D, a member's store
vintage lanes, and (optionally) knowability-ledger release lags, reconstruct the member's
series exactly as it was KNOWABLE on D, recording which fallback class was used.

The engine takes an injected ``loader`` callable (source_id -> [(asof, obs_period, value)])
so tests run against a tiny synthetic store, not the real multi-GB vault, and adopt nothing.
"""
import datetime as dt

from contrib.experiment_harness.asof_replay import AsOfReplayEngine


def make_loader(store):
    return lambda sid: store.get(sid, [])


D = dt.date(2015, 6, 15)


def test_reconstruct_picks_latest_vintage_at_or_before_asof():
    # obs 2015-03 has three vintages; only those with asof <= D are eligible; latest wins.
    store = {
        "SERIES.ASOF": [
            (dt.date(2015, 4, 1), dt.date(2015, 3, 1), 10.0),
            (dt.date(2015, 5, 1), dt.date(2015, 3, 1), 11.0),   # latest eligible
            (dt.date(2015, 7, 1), dt.date(2015, 3, 1), 99.0),   # after D, excluded
        ],
    }
    eng = AsOfReplayEngine(make_loader(store))
    res = eng.reconstruct(["SERIES.ASOF"], D)
    assert res.values[dt.date(2015, 3, 1)] == 11.0
    assert res.fallback_class == "asof_vintage"
    assert res.n_obs == 1


def test_reconstruct_frontier_is_latest_asof_at_or_before_D():
    store = {
        "S.ASOF": [
            (dt.date(2015, 5, 1), dt.date(2015, 3, 1), 11.0),
            (dt.date(2015, 6, 1), dt.date(2015, 4, 1), 12.0),
            (dt.date(2016, 1, 1), dt.date(2015, 5, 1), 13.0),   # after D
        ],
    }
    eng = AsOfReplayEngine(make_loader(store))
    res = eng.reconstruct(["S.ASOF"], D)
    assert res.frontier == dt.date(2015, 6, 1)
    assert set(res.values) == {dt.date(2015, 3, 1), dt.date(2015, 4, 1)}


def test_reconstruct_merges_multiple_sources():
    store = {
        "A.ASOF": [(dt.date(2015, 5, 1), dt.date(2015, 3, 1), 1.0)],
        "B.ASOF": [(dt.date(2015, 5, 1), dt.date(2015, 4, 1), 2.0)],
    }
    eng = AsOfReplayEngine(make_loader(store))
    res = eng.reconstruct(["A.ASOF", "B.ASOF"], D)
    assert res.values == {dt.date(2015, 3, 1): 1.0, dt.date(2015, 4, 1): 2.0}


def test_reconstruct_falls_back_to_current_when_no_vintage():
    # non-revising member: no vintage lanes, use the current series as knowable.
    current = {dt.date(2015, 3, 1): 5.0, dt.date(2015, 4, 1): 6.0, dt.date(2015, 9, 1): 7.0}
    eng = AsOfReplayEngine(make_loader({}))
    res = eng.reconstruct([], D, current=current)
    assert res.fallback_class == "unrevised_current"
    # obs after D are not knowable
    assert set(res.values) == {dt.date(2015, 3, 1), dt.date(2015, 4, 1)}
    assert res.frontier == dt.date(2015, 4, 1)


def test_current_fallback_applies_release_lag():
    # knowability ledger says this series releases 45 days after the period.
    # The 2015-05-01 obs is not knowable until 2015-06-15; on D exactly it is.
    current = {dt.date(2015, 5, 1): 8.0, dt.date(2015, 6, 1): 9.0}
    eng = AsOfReplayEngine(make_loader({}))
    res = eng.reconstruct([], D, current=current, lag_days=45)
    assert set(res.values) == {dt.date(2015, 5, 1)}   # 2015-06-01 + 45d > D


def test_reconstruct_reports_no_data_when_nothing_knowable():
    eng = AsOfReplayEngine(make_loader({}))
    res = eng.reconstruct([], dt.date(1900, 1, 1), current={dt.date(2015, 1, 1): 1.0})
    assert res.fallback_class == "no_data"
    assert res.values == {}
    assert res.frontier is None


def test_frontier_method_matches_reconstruct():
    store = {"S.ASOF": [
        (dt.date(2015, 5, 1), dt.date(2015, 3, 1), 1.0),
        (dt.date(2015, 6, 1), dt.date(2015, 4, 1), 2.0),
    ]}
    eng = AsOfReplayEngine(make_loader(store))
    assert eng.frontier(["S.ASOF"], D) == dt.date(2015, 6, 1)
