"""RED-first tests for the era cross-validation runner (B-EXP-0 deliverable 2).

The runner splits over 1948-> episodes (leave-one-era-out, leave-one-episode-out) and
drives ANY candidate rule passed to it via injected fit/eval callables. It hardcodes NO
episode dates and NO rule: the caller supplies episodes (NBER dates are external
comparators, not construction inputs — CLAUDE.md) and the fit/eval functions.
"""
import datetime as dt

import pytest

from contrib.experiment_harness import era_cv

EPISODES = [
    {"label": "1990", "era": "1990s", "peak": dt.date(1990, 7, 1), "trough": dt.date(1991, 3, 1)},
    {"label": "2001", "era": "2000s", "peak": dt.date(2001, 3, 1), "trough": dt.date(2001, 11, 1)},
    {"label": "2008", "era": "2000s", "peak": dt.date(2007, 12, 1), "trough": dt.date(2009, 6, 1)},
    {"label": "2020", "era": "2020s", "peak": dt.date(2020, 2, 1), "trough": dt.date(2020, 4, 1)},
]


def test_leave_one_episode_out_yields_each_as_test_once():
    splits = list(era_cv.leave_one_episode_out(EPISODES))
    assert len(splits) == 4
    test_labels = [s.test[0]["label"] for s in splits]
    assert test_labels == ["1990", "2001", "2008", "2020"]
    # train is everything else
    first = splits[0]
    assert {e["label"] for e in first.train} == {"2001", "2008", "2020"}
    assert len(first.test) == 1


def test_leave_one_era_out_groups_by_era():
    splits = list(era_cv.leave_one_era_out(EPISODES))
    # eras: 1990s, 2000s, 2020s  -> 3 splits
    assert [s.held_out for s in splits] == ["1990s", "2000s", "2020s"]
    # the 2000s split holds out BOTH 2001 and 2008
    s2000 = [s for s in splits if s.held_out == "2000s"][0]
    assert {e["label"] for e in s2000.test} == {"2001", "2008"}
    assert {e["label"] for e in s2000.train} == {"1990", "2020"}


def test_run_fits_on_train_and_evaluates_on_test_per_split():
    # A trivial candidate rule: "onset threshold = mean peak-month of the training episodes"
    # (rule-agnostic — the runner never inspects it).
    def fit_fn(train):
        return sum(e["peak"].month for e in train) / len(train)

    def eval_fn(rule, test):
        ep = test[0]
        return {"label": ep["label"], "rule": rule, "hit": ep["peak"].month <= rule}

    results = era_cv.run(EPISODES, fit_fn, eval_fn, mode="loo")
    assert len(results) == 4
    # each result carries the held-out label and the eval payload
    labels = [r["test_labels"] for r in results]
    assert labels == [["1990"], ["2001"], ["2008"], ["2020"]]
    assert all("rule" in r["eval"] for r in results)


def test_run_loeo_mode_uses_era_splits():
    def fit_fn(train):
        return len(train)

    def eval_fn(rule, test):
        return {"n_train": rule, "n_test": len(test)}

    results = era_cv.run(EPISODES, fit_fn, eval_fn, mode="loeo")
    assert len(results) == 3
    s2000 = [r for r in results if r["held_out"] == "2000s"][0]
    assert s2000["eval"]["n_train"] == 2
    assert s2000["eval"]["n_test"] == 2


def test_run_rejects_unknown_mode():
    with pytest.raises(ValueError):
        era_cv.run(EPISODES, lambda t: None, lambda r, t: None, mode="bogus")


def test_episodes_from_indicator_derives_peaks_and_troughs():
    # convenience loader: derive episode windows from a 0/1 recession indicator
    # (labelled EXTERNAL COMPARATOR, never construction evidence).
    series = {
        dt.date(2001, 2, 1): 0.0,
        dt.date(2001, 3, 1): 1.0,
        dt.date(2001, 11, 1): 1.0,
        dt.date(2001, 12, 1): 0.0,
        dt.date(2020, 1, 1): 0.0,
        dt.date(2020, 2, 1): 1.0,
        dt.date(2020, 4, 1): 1.0,
        dt.date(2020, 5, 1): 0.0,
    }
    eps = era_cv.episodes_from_indicator(series)
    assert [e["peak"] for e in eps] == [dt.date(2001, 3, 1), dt.date(2020, 2, 1)]
    assert [e["trough"] for e in eps] == [dt.date(2001, 11, 1), dt.date(2020, 4, 1)]
    assert all(e["provenance"] == "external_comparator" for e in eps)
