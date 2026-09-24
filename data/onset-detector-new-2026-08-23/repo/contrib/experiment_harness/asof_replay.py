"""As-of replay engine for Phase-5 experiments (B-EXP-0 deliverable 1).

Given a date D, a member's store vintage lanes, and optional knowability-ledger release
lags, reconstruct the member's series exactly as it was KNOWABLE on D. Generalizes
CH-R28's one-off dry-run (research/_r28_lib.py + _r28_reconstruct.py) into a reusable,
injectable library.

Reconstruction precedence (records which class was used):
  * ``asof_vintage``    — at least one vintage lane observation with asof <= D exists;
                          per obs_period keep the value from the LATEST such vintage.
  * ``unrevised_current`` — no vintage lanes; the member is non-revising, so the current
                          series is knowable subject to a release lag.
  * ``no_data``         — nothing knowable as of D.

The engine takes an injected ``loader`` (source_id -> iterable of (asof_date, obs_period,
value) tuples) so callers wire it to the real store OR a synthetic fixture. It adopts no
member set, weight, or transform — pure reconstruction machinery.
"""
import datetime as dt
import json
import os
import re
from dataclasses import dataclass

_ASOF_RE = re.compile(r"\.(?:DEEP)?ASOF(\d{8})$")


def _parse_asof(series_id):
    m = _ASOF_RE.search(series_id or "")
    if not m:
        return None
    s = m.group(1)
    return dt.date(int(s[:4]), int(s[4:6]), int(s[6:8]))


def _parse_date(s):
    s = s[:10]
    return dt.date(int(s[:4]), int(s[5:7]), int(s[8:10]))


def build_store_loader(root="live_data"):
    """Concrete loader over the local publisher store (READ-ONLY).

    Returns ``loader(source_id) -> [(asof_date, obs_period, value), ...]`` by resolving the
    source head -> normalized sha256 blob -> records, parsing the as-of date out of each
    record's ``series_id`` (``.ASOF<YYYYMMDD>`` / ``.DEEPASOF<YYYYMMDD>``). Records without a
    parseable as-of or value are skipped. Never writes to the store.
    """
    heads = os.path.join(root, "runtime", "source_heads")
    norm = os.path.join(root, "store", "normalized", "sha256")

    def loader(source_id):
        head_path = os.path.join(heads, f"{source_id}.json")
        with open(head_path) as fh:
            head = json.load(fh)
        sha = head["normalized_sha256"]
        with open(os.path.join(norm, sha[:2], f"{sha}.json")) as fh:
            data = json.load(fh)
        out = []
        for r in data.get("records", []):
            asof = _parse_asof(r.get("series_id"))
            if asof is None:
                continue
            try:
                val = float(r["value"])
            except (KeyError, TypeError, ValueError):
                continue
            out.append((asof, _parse_date(r["observation_period"]), val))
        return out

    return loader


@dataclass
class ReplayResult:
    values: dict          # obs_period(date) -> value(float), as knowable on D
    frontier: object      # latest asof used (date) or None
    fallback_class: str   # asof_vintage | unrevised_current | no_data
    n_obs: int


class AsOfReplayEngine:
    def __init__(self, loader):
        """``loader(source_id)`` returns an iterable of (asof_date, obs_period, value)."""
        self._loader = loader

    def _tuples(self, sources):
        out = []
        for sid in sources:
            out.extend(self._loader(sid))
        return out

    def frontier(self, sources, asof):
        """Latest vintage asof at or before ``asof`` across ``sources`` (None if none)."""
        eligible = [a for a, _op, _v in self._tuples(sources) if a <= asof]
        return max(eligible) if eligible else None

    def reconstruct(self, sources, asof, current=None, lag_days=0):
        """Reconstruct the series knowable on ``asof``.

        ``sources`` are store vintage-lane ids. ``current`` (obs_period -> value) is the
        non-revising fallback series. ``lag_days`` is the knowability-ledger release lag
        applied to the current fallback (an obs for period P is knowable only when
        P + lag_days <= asof).
        """
        tuples = self._tuples(sources)
        eligible = [(a, op, v) for a, op, v in tuples if a <= asof]
        if eligible:
            best = {}
            for a, op, v in eligible:
                cur = best.get(op)
                if cur is None or a > cur[0]:
                    best[op] = (a, v)
            values = {op: v for op, (a, v) in best.items()}
            frontier = max(a for a, _op, _v in eligible)
            return ReplayResult(values, frontier, "asof_vintage", len(values))

        # no vintage lanes eligible -> non-revising current fallback
        if current:
            values = {
                op: val for op, val in current.items()
                if op + dt.timedelta(days=lag_days) <= asof
            }
            if values:
                frontier = max(values)
                return ReplayResult(values, frontier, "unrevised_current", len(values))

        return ReplayResult({}, None, "no_data", 0)
