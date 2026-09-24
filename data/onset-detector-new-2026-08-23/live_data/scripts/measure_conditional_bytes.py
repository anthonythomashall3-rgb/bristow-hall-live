#!/usr/bin/env python3
"""Measured bytes/day, before vs after conditional-304 gating (batch R1A section 4).

Uses REAL stored content_lengths (latest receipt per source), the REAL scheduler
poll rate (same _is_due gate as the polls/day measurement), and the MEASURED
304-honoring set. A 304-honoring source downloads a body only on a CHANGED poll
(~once per release cycle); everything else downloads a full body every poll.

  before (no 304): every poll downloads the full body.
  after  (304 on the measured-honoring set): honoring sources download only on
          changed polls (min(polls, releases)/day); the rest are unchanged.
"""
from __future__ import annotations

import glob
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "live_data/ops/poll_history"))
from live_data.rmv2_live.pipeline import _release_boundary, load_release_calendar  # noqa
from poll_history import _period_for_cadence  # noqa

HORIZON_DAYS = 92
TICK = 300
START = datetime(2026, 8, 4, 12, 0, 0, tzinfo=timezone.utc)


def _due(source, entry, attempted, now):
    if attempted is None:
        return True
    if entry is not None:
        b = _release_boundary(entry, now)
        if b is not None:
            return attempted < b
    return (now - attempted).total_seconds() >= source["poll_seconds"]


def polls_per_day():
    config = json.load(open(ROOT / "live_data/config/sources.v1.json"))
    sources = {s["source_id"]: s for s in config["sources"] if s.get("enabled")}
    calendar = load_release_calendar(str(ROOT))
    attempted = {sid: START for sid in sources}
    polls = {sid: 0 for sid in sources}
    now, end = START + timedelta(seconds=TICK), START + timedelta(days=HORIZON_DAYS)
    while now <= end:
        for sid, s in sources.items():
            if _due(s, calendar.get(sid), attempted[sid], now):
                polls[sid] += 1
                attempted[sid] = now
        now += timedelta(seconds=TICK)
    return {sid: polls[sid] / HORIZON_DAYS for sid in polls}, calendar


def content_lengths():
    latest = {}
    for rp in glob.glob(str(ROOT / "live_data/store/receipts/*/*.json")):
        try:
            d = json.load(open(rp))
        except Exception:
            continue
        sid = d.get("source_id")
        t = d.get("clocks", {}).get("retrieved_at") or ""
        if sid and (sid not in latest or t > latest[sid][0]):
            latest[sid] = (t, d.get("response", {}).get("content_length") or 0)
    return {sid: cl for sid, (t, cl) in latest.items()}


def main():
    policy = json.load(open(ROOT / "live_data/config/conditional_http.v1.json"))
    honor_adapters = set(policy["honors_304"]["adapters"])
    honor_ids = set(policy["honors_304"]["source_ids"])
    config = {s["source_id"]: s for s in
              json.load(open(ROOT / "live_data/config/sources.v1.json"))["sources"]}
    cal_cadence = {sid: e.get("cadence") for sid, e in
                   load_release_calendar(str(ROOT)).items()}

    pd, _ = polls_per_day()
    cl = content_lengths()

    before = after = 0.0
    honoring_savings = []
    for sid, ppd in pd.items():
        body = cl.get(sid, 0)
        before += ppd * body
        s = config.get(sid, {})
        honors = (s.get("adapter") in honor_adapters) or (sid in honor_ids)
        if honors:
            period = _period_for_cadence(cal_cadence.get(sid)) or 1.0
            releases_pd = 1.0 / period
            downloads = min(ppd, releases_pd)
            saved = (ppd - downloads) * body
            if saved > 0:
                honoring_savings.append((saved, sid, round(ppd, 2), body))
        else:
            downloads = ppd
        after += downloads * body

    honoring_savings.sort(reverse=True)
    print(json.dumps({
        "method": "measured content_lengths x scheduler poll rate; 304-honoring sources download only on changed (release) polls",
        "full_sweep_body_bytes": sum(cl.values()),
        "bytes_per_day_before_no_304": int(before),
        "bytes_per_day_after_304_gated": int(after),
        "bytes_per_day_saved": int(before - after),
        "pct_saved": round(100 * (before - after) / before, 1) if before else 0,
        "mib_per_day_before": round(before / 1024**2, 1),
        "mib_per_day_after": round(after / 1024**2, 1),
        "top_savings": [{"source_id": s, "bytes_saved_per_day": int(v),
                         "polls_per_day": p, "body_bytes": b}
                        for v, s, p, b in honoring_savings[:10]],
    }, indent=2))


if __name__ == "__main__":
    main()
