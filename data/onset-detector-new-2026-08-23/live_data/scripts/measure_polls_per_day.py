#!/usr/bin/env python3
"""Measure actual polls/day of the applied release calendar (batch R1A section 2).

Not a projection: this steps a synthetic clock over a real multi-day horizon and
counts how many polls the REAL scheduler gate (pipeline._is_due / _release_boundary)
would fire, starting each source freshly polled at t0. The horizon spans the slowest
derived cadence so gated sources are averaged over whole release cycles, then divided
by days for a per-day rate. Reports total, the gated vs fixed-interval split, and the
top contributors, next to R1's projected 325.3.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from live_data.rmv2_live.pipeline import _release_boundary, load_release_calendar  # noqa

HORIZON_DAYS = 92          # >= quarterly (slowest derived class); whole-cycle average
TICK_SECONDS = 300         # == min config poll_seconds; resolves every fallback gate
START = datetime(2026, 8, 4, 12, 0, 0, tzinfo=timezone.utc)


def _due(source, entry, attempted, now):
    """Faithful reproduction of pipeline._is_due for outcome=='ok' (no sim failures)."""
    if attempted is None:
        return True
    if entry is not None:
        boundary = _release_boundary(entry, now)
        if boundary is not None:
            return attempted < boundary
    return (now - attempted).total_seconds() >= source["poll_seconds"]


def main():
    config = json.load(open(ROOT / "live_data/config/sources.v1.json"))
    sources = {s["source_id"]: s for s in config["sources"] if s.get("enabled")}
    calendar = load_release_calendar(str(ROOT))

    attempted = {sid: START for sid in sources}          # freshly polled at t0
    polls = {sid: 0 for sid in sources}
    horizon = timedelta(days=HORIZON_DAYS)
    step = timedelta(seconds=TICK_SECONDS)

    now = START + step
    end = START + horizon
    while now <= end:
        for sid, s in sources.items():
            if _due(s, calendar.get(sid), attempted[sid], now):
                polls[sid] += 1
                attempted[sid] = now
        now += step

    total = sum(polls.values())
    per_day = total / HORIZON_DAYS
    gated_ids = {sid for sid, e in calendar.items()
                 if e.get("next_expected_release_utc") and e.get("cadence_gap_days")}
    gated_pd = sum(polls[s] for s in polls if s in gated_ids) / HORIZON_DAYS
    fallback_pd = per_day - gated_pd
    top = sorted(((round(polls[s] / HORIZON_DAYS, 3), s) for s in polls), reverse=True)[:15]

    print(json.dumps({
        "horizon_days": HORIZON_DAYS,
        "tick_seconds": TICK_SECONDS,
        "measured_polls_per_day": round(per_day, 1),
        "r1_projected_polls_per_day": 325.3,
        "delta_vs_r1": round(per_day - 325.3, 1),
        "gated_polls_per_day": round(gated_pd, 1),
        "fallback_polls_per_day": round(fallback_pd, 1),
        "n_gated_sources": len(gated_ids),
        "n_fallback_sources": len(sources) - len(gated_ids),
        "top15_contributors_per_day": [{"source_id": s, "polls_per_day": v} for v, s in top],
    }, indent=2))


if __name__ == "__main__":
    main()
