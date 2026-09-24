#!/usr/bin/env python3
"""Apply R1's frozen release-calendar proposal to live_data/config/release_calendar.v1.json.

Batch R1A section 2. This does NOT re-derive, adjust, or round anything. It reads
the FROZEN proposal (R1_RELEASE_CALENDAR_DEEPEN.v1.json) and overlays each source's
derived values onto the current calendar (which supplies adapter / source_id /
config_frequency). The only computation performed is formatting R1's frozen
(proposed_next_release_date, proposed_clock_time, proposed_timezone) into a UTC
instant using the repo's existing deterministic ET->UTC rule -- this is FORMATTING,
not schedule derivation. Any entry that cannot be applied verbatim is skip-and-recorded.

Preserved per entry (batch 2): confidence, evidence.kind, evidence URL/measurement,
derived interval, derived offset. An observed-behaviour entry never carries an
evidence kind that reads as publisher-stated (asserted by the test).

The scheduler (pipeline._is_due) consumes next_expected_release_utc + cadence_gap_days
for gating and config poll_seconds as the fallback; the derived fallback_interval_seconds
+ fallback_offset_seconds are preserved as metadata (no scheduler change in this batch).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_data" / "scripts"))
# reuse the SAME deterministic ET->UTC rule the builder uses (formatting only)
from build_release_calendar import _et_to_utc  # noqa: E402
sys.path.insert(0, str(ROOT))
from live_data.rmv2_live.canonical import atomic_write_json  # noqa: E402

PROPOSAL = ROOT / "tools/rmv2_data_cloudflare/generated_live/R1_RELEASE_CALENDAR_DEEPEN.v1.json"
CALENDAR = ROOT / "live_data/config/release_calendar.v1.json"
SCHEMA = "recession-monitor-v2.release-calendar.v1"  # keep -- scheduler gates on this

# evidence kinds R1 emits; both are measurement / publisher-page labels, never
# the literal "publisher_stated" (which would misrepresent observed behaviour).
KNOWN_EVIDENCE_KINDS = {
    "fred_series_release+fred_release_dates",  # observed release-date measurement
    "publisher_schedule_page",                 # read from the publisher's schedule page
}


def _read(p):
    with open(p) as f:
        return json.load(f)


def _strip_none(d):
    return {k: v for k, v in d.items() if v is not None}


def build_entry(sid, base, p, skips):
    """Return the applied calendar entry for one source, or None to keep base+record."""
    entry = dict(base)  # adapter, source_id, config_frequency, last_observed_release_date, ...
    entry["source_id"] = sid
    entry["confidence"] = p["proposed_confidence"]
    entry["cadence"] = p.get("proposed_cadence", base.get("cadence"))
    entry["config_frequency"] = p.get("config_frequency", base.get("config_frequency"))
    # cadence_gap_days: apply R1's value VERBATIM (null stays null -> no gating; that
    # divergence from R1's projection is a measured finding, not something we patch).
    entry["cadence_gap_days"] = p.get("cadence_gap_days")

    # evidence: kind + URL/measurement + release identity + time basis, from R1
    ev = _strip_none({
        "kind": p.get("evidence_kind"),
        "url": p.get("evidence_url"),
        "release_id": p.get("release_id"),
        "release_name": p.get("release_name"),
        "time_basis": p.get("time_basis"),
        "fallback_basis": p.get("fallback_basis"),
    })
    entry["evidence"] = ev

    # preserved derived interval + offset (metadata; not consumed by the scheduler)
    if p.get("proposed_fallback_interval_seconds") is not None:
        entry["fallback_interval_seconds"] = p["proposed_fallback_interval_seconds"]
    # else keep base fallback_interval_seconds
    if p.get("proposed_fallback_offset_seconds") is not None:
        entry["fallback_offset_seconds"] = p["proposed_fallback_offset_seconds"]

    entry["scheduler_mode"] = p.get("scheduler_mode")

    # next_expected_release_utc: format R1's frozen date+clock+tz (never re-derive the date)
    mode = p.get("scheduler_mode")
    date_s = p.get("proposed_next_release_date")
    if mode == "calendar_gated" and date_s:
        tz = p.get("proposed_timezone")
        if tz not in (None, "America/New_York"):
            # the repo formatter is ET-only; do not invent tz math -> skip-and-record.
            skips.append({
                "source_id": sid, "field": "next_expected_release_utc",
                "reason": "proposed_timezone %r unsupported by ET-only formatter; "
                          "next_expected left as base (confidence/evidence still applied)" % tz,
            })
            entry["next_expected_release_utc"] = base.get("next_expected_release_utc")
        else:
            date = dt.date.fromisoformat(date_s)
            clock = p.get("proposed_clock_time") or "23:59"  # conservative EOD ET, builder convention
            entry["next_expected_release_utc"] = _et_to_utc(date, clock).strftime(
                "%Y-%m-%dT%H:%M:%SZ")
    else:
        entry["next_expected_release_utc"] = None
    return entry


def apply(write=True):
    prop = _read(PROPOSAL)
    cal = _read(CALENDAR)
    proposals = prop["proposals"]
    base_sources = cal["sources"]

    skips = []
    unapplied = []
    new_sources = {}
    for sid in base_sources:
        if sid not in proposals:
            unapplied.append({"source_id": sid, "reason": "no proposal entry"})
            new_sources[sid] = base_sources[sid]
            continue
        new_sources[sid] = build_entry(sid, base_sources[sid], proposals[sid], skips)

    # confidence counts (after) -- must equal R1's summary.after or it's a finding
    from collections import Counter
    after = Counter(e.get("confidence") for e in new_sources.values())
    after_counts = {k: after.get(k, 0) for k in ("high", "medium", "unknown")}

    # invariant: no observed-behaviour entry masquerades as publisher-stated evidence
    invariant_violations = []
    for sid, e in new_sources.items():
        k = e.get("evidence", {}).get("kind")
        if k and "publisher_stated" in k.replace("-", "_"):
            invariant_violations.append(sid)

    doc = dict(cal)
    doc["schema_version"] = SCHEMA
    doc["sources"] = new_sources
    doc["confidence_counts"] = after_counts
    gf = dict(cal.get("generated_from", {}))
    gf["applied_from_proposal"] = os.path.relpath(PROPOSAL, ROOT)
    gf["applied_proposal_schema"] = prop.get("schema_version")
    doc["generated_from"] = gf
    sc = dict(cal.get("scheduler_contract", {}))
    sc["preserved_metadata"] = (
        "fallback_interval_seconds and fallback_offset_seconds carry R1's derived "
        "values; the scheduler gates on next_expected_release_utc+cadence_gap_days "
        "and falls back to config poll_seconds -- the derived interval/offset are "
        "preserved metadata, not consumed by _is_due in this batch."
    )
    doc["scheduler_contract"] = sc
    doc["unresolved_sources"] = prop.get("unresolved_sources", [])
    # float-free distillation of R1's per-class fallback policy (the canonical
    # contract forbids floats; period/jitter fractions stay in the proposal).
    fbc = prop.get("fallback_by_cadence_class", {})
    doc["fallback_class_policy"] = {
        cls: {
            "derivable": bool(v.get("derivable")),
            "interval_seconds": int(v.get("interval_seconds")),
            "reason": v.get("reason"),
        }
        for cls, v in fbc.items()
    }

    report = {
        "applied_sources": len(new_sources),
        "after_confidence_counts": after_counts,
        "r1_summary_after": prop.get("summary", {}).get("after"),
        "counts_match_r1": after_counts == prop.get("summary", {}).get("after"),
        "skips": skips,
        "unapplied": unapplied,
        "invariant_violations": invariant_violations,
        "gated_entries": sum(1 for e in new_sources.values()
                             if e.get("next_expected_release_utc") and e.get("cadence_gap_days")),
        "calendar_gated_without_gap": sorted(
            sid for sid, e in new_sources.items()
            if e.get("scheduler_mode") == "calendar_gated" and not e.get("cadence_gap_days")),
    }

    if write:
        # atomic_write_json enforces the canonical contract (float-free, finite,
        # string keys) -- it raises rather than write a file the scheduler rejects.
        atomic_write_json(str(CALENDAR), doc, pretty=True)
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    rep = apply(write=not a.dry_run)
    print(json.dumps(rep, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
