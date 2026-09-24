#!/usr/bin/env python3
"""Compact append-only poll-history log (batch R1A section 3).

R1 3c.3: store receipts/generations retain ~5 days, which made a release MISS
unmeasurable -- the self-correcting calendar's blocker. This keeps a few bytes per
poll (timestamp, changed/unchanged, response validator, outcome) in an append-only
NDJSON log that lives OUTSIDE the vault and OUTSIDE the store, so it survives store
pruning long enough to observe several release cycles of the slowest cadence present.

The horizon is DERIVED from the longest cadence in the calendar (not a chosen round
number): several (=3) release cycles of the slowest cadence present.

Record (compact NDJSON, one line per poll):
    {"t": <epoch_int>, "s": "<source_id>", "c": 0|1, "v": "e|l|b|n", "o": "<code>"}
      t  retrieved-at epoch seconds
      c  content changed (1) vs unchanged (0)
      v  validator advertised on the response: etag / last-modified / both / none
      o  short outcome code (ok, unc, 304, fail, blk)
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LOG_DIR = ROOT / "live_data" / "ops" / "poll_history"     # separate from vault + store
LOG = LOG_DIR / "history.ndjson"
CONFIG = ROOT / "live_data" / "config" / "poll_history.v1.json"
CALENDAR = ROOT / "live_data" / "config" / "release_calendar.v1.json"

CYCLES = 3  # "several" release cycles -- the minimum that lets a miss show against neighbours

# cadence keyword -> period in days (used to find the slowest cadence PRESENT)
_PERIOD_DAYS = [
    ("annual", 365.25),
    ("quarter", 91.31),
    ("biweek", 14.0),
    ("month", 30.44),
    ("week", 7.0),
    ("daily", 1.0),
    ("day", 1.0),
]

_OUTCOME_CODE = {
    "success": "ok", "retrieved_and_validated": "ok",
    "unchanged": "unc", "http_304_not_modified": "304",
    "failed": "fail", "blocked": "blk",
}


def _period_for_cadence(label):
    s = (label or "").lower()
    for kw, days in _PERIOD_DAYS:
        if kw in s:
            return days
    return None


def slowest_cadence_present(calendar):
    """(period_days, label) of the slowest cadence present in the calendar."""
    best = (0.0, None)
    for e in calendar.get("sources", {}).values():
        p = _period_for_cadence(e.get("cadence"))
        gap = e.get("cadence_gap_days")
        cand = max(p or 0.0, float(gap or 0.0))
        if cand > best[0]:
            best = (cand, e.get("cadence"))
    return best


def derive_horizon_days():
    cal = json.load(open(CALENDAR))
    period, label = slowest_cadence_present(cal)
    horizon = round(CYCLES * period, 2)  # non-round by construction
    return {
        "cycles": CYCLES,
        "slowest_cadence_period_days": period,
        "slowest_cadence_label": label,
        "horizon_days": horizon,
    }


def _validator_code(etag, last_modified):
    if etag and last_modified:
        return "b"
    if etag:
        return "e"
    if last_modified:
        return "l"
    return "n"


def _to_epoch(iso):
    if not iso:
        return None
    try:
        return int(datetime.fromisoformat(iso.replace("Z", "+00:00"))
                   .astimezone(timezone.utc).timestamp())
    except ValueError:
        return None


def make_record(source_id, retrieved_at_iso, changed, etag, last_modified, outcome):
    return {
        "t": _to_epoch(retrieved_at_iso),
        "s": source_id,
        "c": 1 if changed else 0,
        "v": _validator_code(etag, last_modified),
        "o": _OUTCOME_CODE.get(outcome, outcome[:4] if outcome else "?"),
    }


def append_records(records):
    """Append compact records (append-only). Best-effort; never raises to a caller."""
    if not records:
        return 0
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    lines = "".join(json.dumps(r, separators=(",", ":"), sort_keys=True) + "\n"
                    for r in records if r.get("t") is not None)
    with open(LOG, "a") as f:
        f.write(lines)
    return lines.count("\n")


def records_from_refresh_outcomes(outcomes, store, now_iso):
    """Map a pipeline refresh() outcomes list to poll-history records.

    Only real poll attempts are logged; not_due/disabled ticks are skipped so an
    idle tick writes nothing (preserving the idle-tick no-work invariant)."""
    recs = []
    for o in outcomes:
        oc = o.get("outcome")
        if oc in ("not_due", "disabled"):
            continue
        sid = o.get("source_id")
        if not sid:
            continue
        head = {}
        try:
            head = store.read_source_head(sid) or {}
        except Exception:
            head = {}
        recs.append(make_record(
            sid, now_iso,
            changed=(oc in ("success", "retrieved_and_validated")),
            etag=head.get("etag"), last_modified=head.get("last_modified"),
            outcome=oc))
    return recs


def prune(now_epoch=None):
    """Drop records older than the derived horizon (append-only + periodic prune)."""
    if not LOG.exists():
        return {"pruned": 0, "kept": 0}
    horizon_days = derive_horizon_days()["horizon_days"]
    if now_epoch is None:
        now_epoch = int(datetime.now(timezone.utc).timestamp())
    cutoff = now_epoch - int(horizon_days * 86400)
    kept, pruned = [], 0
    with open(LOG) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if r.get("t", 0) >= cutoff:
                kept.append(line)
            else:
                pruned += 1
    tmp = str(LOG) + ".tmp"
    with open(tmp, "w") as f:
        f.write("\n".join(kept) + ("\n" if kept else ""))
    os.replace(tmp, LOG)
    return {"pruned": pruned, "kept": len(kept), "cutoff_epoch": cutoff}


def _key(r):
    return (r.get("t"), r.get("s"), r.get("c"), r.get("v"), r.get("o"))


def _read_log_records():
    if not LOG.exists():
        return []
    out = []
    with open(LOG) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except ValueError:
                continue
    return out


def ingest_receipts(now_epoch=None):
    """Drain the store receipts into the durable log (idempotent union + prune).

    The pipeline already writes one receipt per poll; those receipts are pruned at
    ~5 days (R1 3c.3). This unions the CURRENT receipts with the records already in
    the durable log, de-duplicates, prunes to the derived horizon, and rewrites --
    so poll outcomes survive far longer than the receipt window WITHOUT touching the
    acquisition hot path. Append-only in effect: records persist until the horizon.
    """
    receipts_dir = ROOT / "live_data" / "store" / "receipts"
    recs = _read_log_records()
    for rp in receipts_dir.rglob("*.json"):
        try:
            d = json.load(open(rp))
        except Exception:
            continue
        resp = d.get("response", {})
        clocks = d.get("clocks", {})
        oc = d.get("outcome")
        recs.append(make_record(
            d.get("source_id"),
            clocks.get("retrieved_at") or clocks.get("validated_at"),
            changed=(oc in ("retrieved_and_validated", "success")),
            etag=resp.get("etag"), last_modified=resp.get("last_modified"),
            outcome=oc))
    # dedupe + drop unparseable + prune to horizon
    seen, uniq = set(), []
    for r in recs:
        if r.get("t") is None or not r.get("s"):
            continue
        k = _key(r)
        if k in seen:
            continue
        seen.add(k)
        uniq.append(r)
    horizon_days = derive_horizon_days()["horizon_days"]
    if now_epoch is None:
        now_epoch = int(datetime.now(timezone.utc).timestamp())
    cutoff = now_epoch - int(horizon_days * 86400)
    uniq = [r for r in uniq if r["t"] >= cutoff]
    uniq.sort(key=lambda r: r["t"])
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    tmp = str(LOG) + ".tmp"
    with open(tmp, "w") as f:
        for r in uniq:
            f.write(json.dumps(r, separators=(",", ":"), sort_keys=True) + "\n")
    os.replace(tmp, LOG)
    return uniq


# backward-compatible alias
seed_from_receipts = ingest_receipts


def project_size(polls_per_day):
    horizon = derive_horizon_days()
    # measured average record size from the seeded log, else a compact estimate
    if LOG.exists() and LOG.stat().st_size > 0:
        with open(LOG) as f:
            lines = [ln for ln in f.read().splitlines() if ln]
        avg = (sum(len(ln) + 1 for ln in lines) / len(lines)) if lines else 72.0
    else:
        avg = 72.0
    total = avg * polls_per_day * horizon["horizon_days"]
    return {
        **horizon,
        "avg_record_bytes": round(avg, 1),
        "polls_per_day": polls_per_day,
        "projected_bytes": int(total),
        "projected_mib": round(total / 1024**2, 1),
    }


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["horizon", "seed", "ingest", "prune", "project"])
    ap.add_argument("--polls-per-day", type=float, default=1721.3)
    a = ap.parse_args()
    if a.cmd == "horizon":
        print(json.dumps(derive_horizon_days(), indent=2))
    elif a.cmd in ("seed", "ingest"):
        recs = ingest_receipts()
        print(json.dumps({"records_in_log": len(recs),
                          "log": str(LOG.relative_to(ROOT)),
                          "bytes": LOG.stat().st_size}, indent=2))
    elif a.cmd == "prune":
        print(json.dumps(prune(), indent=2))
    elif a.cmd == "project":
        print(json.dumps(project_size(a.polls_per_day), indent=2))


if __name__ == "__main__":
    sys.exit(main())
