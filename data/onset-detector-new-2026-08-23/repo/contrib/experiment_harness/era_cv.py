"""Era cross-validation runner for Phase-5 experiments (B-EXP-0 deliverable 2).

Splits a caller-supplied list of episodes (1948->) into fit/test windows —
leave-one-episode-out (LOO) and leave-one-era-out (LOEO) — and drives ANY candidate rule
through them via injected ``fit_fn``/``eval_fn`` callables. The runner adopts nothing:

  * it hardcodes no episode dates. Episodes come from the caller; the convenience loader
    ``episodes_from_indicator`` derives them from a 0/1 recession indicator and stamps
    provenance="external_comparator" (NBER dates are external comparators, never clean
    construction inputs — CLAUDE.md);
  * it hardcodes no rule, threshold, or chronology. ``fit_fn(train)`` returns whatever the
    experiment's rule object is; ``eval_fn(rule, test)`` returns whatever metrics dict the
    experiment wants. The runner only orchestrates the splits.

An episode is a dict with at least ``label``, ``era``, ``peak``, ``trough``.
"""
from dataclasses import dataclass
from typing import Callable


@dataclass
class Split:
    """One fit/test partition. ``held_out`` names the era for LOEO, else None."""
    train: list
    test: list
    held_out: str = None


def leave_one_episode_out(episodes):
    """Yield one Split per episode: that episode is the test set, the rest are train."""
    for i, ep in enumerate(episodes):
        train = [e for j, e in enumerate(episodes) if j != i]
        yield Split(train=train, test=[ep], held_out=None)


def leave_one_era_out(episodes):
    """Yield one Split per distinct era (first-seen order): all episodes of that era are the
    test set, the rest are train."""
    seen = []
    for ep in episodes:
        if ep["era"] not in seen:
            seen.append(ep["era"])
    for era in seen:
        test = [e for e in episodes if e["era"] == era]
        train = [e for e in episodes if e["era"] != era]
        yield Split(train=train, test=test, held_out=era)


def run(episodes, fit_fn: Callable, eval_fn: Callable, mode="loo"):
    """Fit on each split's train set, evaluate on its test set, collect the results.

    ``mode`` is "loo" (leave-one-episode-out) or "loeo" (leave-one-era-out). Returns a list
    of dicts: ``{held_out, test_labels, eval}`` where ``eval`` is whatever ``eval_fn``
    returned. The runner never inspects the rule or the eval payload.
    """
    if mode == "loo":
        splitter = leave_one_episode_out
    elif mode == "loeo":
        splitter = leave_one_era_out
    else:
        raise ValueError(f"unknown mode {mode!r}; use 'loo' or 'loeo'")
    results = []
    for split in splitter(episodes):
        rule = fit_fn(split.train)
        payload = eval_fn(rule, split.test)
        results.append({
            "held_out": split.held_out,
            "test_labels": [e["label"] for e in split.test],
            "eval": payload,
        })
    return results


def episodes_from_indicator(indicator, era_fn=None):
    """Derive episode windows from a 0/1 recession indicator (date -> value).

    A run of consecutive 1.0 observations becomes one episode: ``peak`` = first in-run
    date, ``trough`` = last in-run date. Each episode is stamped
    ``provenance="external_comparator"`` — this is a benchmark, NOT construction evidence
    (CLAUDE.md). ``era_fn(peak) -> str`` labels the era; default is the peak decade.
    """
    if era_fn is None:
        era_fn = lambda d: f"{(d.year // 10) * 10}s"
    dates = sorted(indicator)
    episodes = []
    run_dates = []
    for d in dates:
        on = float(indicator[d]) >= 0.5
        if on:
            run_dates.append(d)
        elif run_dates:
            episodes.append(_episode(run_dates, era_fn))
            run_dates = []
    if run_dates:
        episodes.append(_episode(run_dates, era_fn))
    return episodes


def _episode(run_dates, era_fn):
    peak, trough = run_dates[0], run_dates[-1]
    return {
        "label": str(peak.year),
        "era": era_fn(peak),
        "peak": peak,
        "trough": trough,
        "provenance": "external_comparator",
    }
