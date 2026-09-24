#!/usr/bin/env python3
"""Generate live_data/config/release_calendar.v1.json from publisher release evidence.

AI-free and deterministic given the fetched evidence. For every configured source
this emits: a cadence, the next expected release (UTC), the evidence it was
derived from, and a confidence tier. A source whose next release cannot be
derived from real evidence is marked confidence="unknown" with its cadence taken
from config and a conservative fixed-interval fallback (= the source's own
configured poll_seconds). No schedule is invented; unknown stays unknown.

Evidence used (all free, no scraping of prose):
  * FRED fred/release/dates for the RIDs the batch verified — per-release actual
    release dates INCLUDING the publisher's already-scheduled future dates, on the
    reliable api.stlouisfed.org host (the ALFRED download-dates file is the same
    data but throttles under repeated automated access, so we use the API twin).
  * FRED fred/release/series membership — assigns each FRED series to its release
    (FRED's own mapping, not an assumption) so the dates attach to the right sources.
  * config.frequency / config.poll_seconds — the conservative fallback only.

The scheduler treats the calendar as strictly additive: sources with a derived
next_expected_release poll when that release is due; everything else falls back to
its fixed interval, i.e. exactly the pre-existing poll_seconds behaviour.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import ssl
import sys
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

# --- verified release identifiers -------------------------------------------
# RIDs verified in the batch brief. release_time_et is attached ONLY where the
# batch explicitly verified a publish clock; every other release keeps the DATE
# from ALFRED but a conservative end-of-day ET time (time_confidence="date_only")
# so the scheduler never polls before the publisher's release day has closed.
VERIFIED_TIME_ET = {
    221: "08:30",   # NFCI — Wed 08:30 ET (batch verified)
    180: "08:30",   # UI weekly claims — Thu 08:30 ET (batch verified)
    351: "08:30",   # MBOS — 3rd Thu 08:30 ET (batch verified)
    13: "09:15",    # G.17 — monthly 09:15 ET (batch verified)
}
RID_NAME = {
    13: "G.17 Industrial Production and Capacity Utilization",
    27: "New Residential Construction",
    50: "Employment Situation",
    54: "Personal Income and Outlays",
    91: "Surveys of Consumers",
    180: "Unemployment Insurance Weekly Claims",
    200: "CBOE Market Statistics",
    221: "Chicago Fed National Financial Conditions Index",
    282: "CMRMTSPL (Real Manufacturing and Trade Industries Sales, supplemental)",
    304: "Interest Rate Spreads",
    328: "NASDAQ",
    351: "Manufacturing Business Outlook Survey (Philadelphia Fed)",
    427: "Moody's Seasoned Corporate Bond Yields",
    456: "Sahm Rule Recession Indicators",
}
ALFRED_RIDS = sorted(RID_NAME)

FRED_ADAPTERS = {
    "fred_json_api",
    "fred_graph_csv",
    "fred_json_api_vintages",
    "fred_json_api_vintages_deep",
}
SCHEMA_VERSION = "recession-monitor-v2.release-calendar.v1"

# US Eastern offset is handled without zoneinfo (py3.8 base image may lack tzdata):
# release_time_et is interpreted at the standard/daylight offset for the release
# month. We compute the offset from a fixed US DST rule (2nd Sun Mar - 1st Sun Nov).


def _et_utc_offset_hours(date):
    """US Eastern UTC offset (hours, negative) for a given date, DST-aware."""
    year = date.year
    # 2nd Sunday of March
    mar1 = dt.date(year, 3, 1)
    second_sun_mar = mar1 + dt.timedelta(days=(6 - mar1.weekday()) % 7 + 7)
    # 1st Sunday of November
    nov1 = dt.date(year, 11, 1)
    first_sun_nov = nov1 + dt.timedelta(days=(6 - nov1.weekday()) % 7)
    return -4 if second_sun_mar <= date < first_sun_nov else -5


def _et_to_utc(date, hhmm):
    hh, mm = (int(x) for x in hhmm.split(":"))
    offset = _et_utc_offset_hours(date)
    naive = dt.datetime(date.year, date.month, date.day, hh, mm)
    return (naive - dt.timedelta(hours=offset)).replace(tzinfo=dt.timezone.utc)


def _http_get(url, timeout=30):
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, headers={"User-Agent": "rmv2-release-calendar/1.0"})
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
        return resp.read().decode("utf-8", errors="strict")


def fetch_release_dates(rid, api_key, timeout=30):
    """Return (public_url, sorted dates) for a FRED release via fred/release/dates.

    This is the FRED API twin of the ALFRED release download-dates file, on the
    reliable api.stlouisfed.org host, and — crucially — it returns the publisher's
    already-scheduled FUTURE release dates too, so next_expected is a genuine
    published date rather than a projection. The evidence URL stored in the
    manifest omits the API key.
    """
    base = "https://api.stlouisfed.org/fred/release/dates"
    params = {
        "release_id": str(rid),
        "api_key": api_key,
        "file_type": "json",
        "include_release_dates_with_no_data": "true",
        "sort_order": "asc",
        "limit": "10000",
    }
    url = base + "?" + urllib.parse.urlencode(params)
    data = json.loads(_http_get(url, timeout=timeout))
    dates = []
    for row in data.get("release_dates", []):
        d = row.get("date")
        if d and len(d) == 10:
            try:
                dates.append(dt.date(int(d[:4]), int(d[5:7]), int(d[8:10])))
            except ValueError:
                continue
    public_url = base + "?release_id=%d&file_type=json&include_release_dates_with_no_data=true" % rid
    return public_url, sorted(set(dates))


def modal_gap_days(dates):
    gaps = [(b - a).days for a, b in zip(dates, dates[1:]) if (b - a).days > 0]
    if not gaps:
        return None
    return Counter(gaps).most_common(1)[0][0]


def cadence_label(gap):
    if gap is None:
        return "unknown"
    if gap <= 2:
        return "business_daily"
    if 6 <= gap <= 8:
        return "weekly"
    if 13 <= gap <= 16:
        return "biweekly"
    if 27 <= gap <= 33:
        return "monthly"
    if 88 <= gap <= 95:
        return "quarterly"
    if 360 <= gap <= 370:
        return "annual"
    return "irregular_%dd" % gap


def next_expected_from_dates(dates, today, rid):
    """Compute the next expected release UTC from a release's actual dates.

    Prefer a genuine future date already listed by ALFRED; otherwise project the
    last historical date forward by the modal gap until it is strictly after
    today. Attach the batch-verified ET publish clock where known, else a
    conservative end-of-day ET time so the scheduler waits out the release day.
    """
    if not dates:
        return None, None, None, None
    gap = modal_gap_days(dates)
    future = [d for d in dates if d > today]
    if future:
        nxt = future[0]
        projected = False
    else:
        if gap is None:
            return None, dates[-1], gap, None
        nxt = dates[-1]
        while nxt <= today:
            nxt = nxt + dt.timedelta(days=gap)
        projected = True
    time_et = VERIFIED_TIME_ET.get(rid)
    if time_et is not None:
        when = _et_to_utc(nxt, time_et)
        time_conf = "batch_verified_cadence"
    else:
        when = _et_to_utc(nxt, "23:59")
        time_conf = "date_only_conservative_eod_et"
    return when, dates[-1], gap, {"projected": projected, "time_confidence": time_conf}


def fetch_fred_release_membership(rid, api_key, timeout=30):
    """Return the set of FRED series ids in a release (fred/release/series)."""
    base = "https://api.stlouisfed.org/fred/release/series"
    params = {
        "release_id": str(rid),
        "api_key": api_key,
        "file_type": "json",
        "limit": "1000",
    }
    out = set()
    offset = 0
    while True:
        params["offset"] = str(offset)
        url = base + "?" + urllib.parse.urlencode(params)
        data = json.loads(_http_get(url, timeout=timeout))
        batch = data.get("seriess", [])
        for s in batch:
            out.add(s["id"].upper())
        if len(batch) < 1000:
            break
        offset += 1000
    return out


def fetch_bea_release_dates(timeout=30):
    url = "https://apps.bea.gov/API/signup/release_dates.json"
    try:
        data = json.loads(_http_get(url, timeout=timeout))
    except Exception:
        return url, []
    return url, data


def fred_series_id(source):
    series = source.get("series")
    if isinstance(series, dict) and series.get("series_id"):
        return str(series["series_id"]).upper()
    qs = urllib.parse.parse_qs(urllib.parse.urlparse(source["endpoint"]).query)
    for key in ("series_id", "id"):
        if qs.get(key):
            return str(qs[key][0]).upper()
    return None


def build(config, api_key, today, timeout=30, offline=False):
    sources = config["sources"]

    # --- gather evidence ----------------------------------------------------
    alfred = {}      # rid -> {url, dates, next_expected_utc, last, gap, meta}
    membership = {}  # rid -> set(series_id)
    fetch_errors = []
    if not offline and api_key:
        for rid in ALFRED_RIDS:
            try:
                url, dates = fetch_release_dates(rid, api_key, timeout=timeout)
                # cadence from the recent regime, not decades of history
                recent = [d for d in dates if d <= today][-24:] or dates[:24]
                gap = modal_gap_days(recent)
                nxt, last, _g, meta = next_expected_from_dates(dates, today, rid)
                past = [d for d in dates if d <= today]
                alfred[rid] = {
                    "url": url,
                    "recent_dates": [d.isoformat() for d in past[-4:]],
                    "next_expected_utc": nxt.strftime("%Y-%m-%dT%H:%M:%SZ") if nxt else None,
                    "last_observed_release_date": (past[-1].isoformat() if past else None),
                    "cadence_gap_days": gap,
                    "meta": meta,
                }
            except Exception as exc:  # noqa: BLE001 — evidence is best-effort
                fetch_errors.append("release/dates rid=%d: %s: %s" % (rid, type(exc).__name__, exc))
            if api_key:
                try:
                    membership[rid] = fetch_fred_release_membership(rid, api_key, timeout=timeout)
                except Exception as exc:  # noqa: BLE001
                    fetch_errors.append(
                        "release/series rid=%d: %s: %s" % (rid, type(exc).__name__, exc)
                    )

    series_to_rid = {}
    for rid, members in membership.items():
        for sid in members:
            # first verified release wins; releases are disjoint enough for our set
            series_to_rid.setdefault(sid, rid)

    # --- per-source entries -------------------------------------------------
    entries = {}
    conf_counts = Counter()
    for source in sources:
        sid = source["source_id"]
        poll_seconds = source["poll_seconds"]
        freq = source["frequency"]
        entry = {
            "source_id": sid,
            "adapter": source["adapter"],
            "config_frequency": freq,
            "fallback_interval_seconds": poll_seconds,
        }
        assigned_rid = None
        if source["adapter"] in FRED_ADAPTERS:
            fsid = fred_series_id(source)
            if fsid and fsid in series_to_rid:
                assigned_rid = series_to_rid[fsid]

        rec = alfred.get(assigned_rid) if assigned_rid is not None else None
        if rec and rec.get("next_expected_utc"):
            meta = rec.get("meta") or {}
            time_conf = meta.get("time_confidence")
            confidence = "high" if time_conf == "batch_verified_cadence" else "medium"
            entry.update({
                "cadence": cadence_label(rec["cadence_gap_days"]),
                "cadence_gap_days": rec["cadence_gap_days"],
                "next_expected_release_utc": rec["next_expected_utc"],
                "last_observed_release_date": rec["last_observed_release_date"],
                "confidence": confidence,
                "evidence": {
                    "kind": "alfred_release_downloaddates+fred_release_series",
                    "release_id": assigned_rid,
                    "release_name": RID_NAME.get(assigned_rid),
                    "url": rec["url"],
                    "recent_release_dates": rec["recent_dates"],
                    "next_release_projected": bool(meta.get("projected")),
                    "release_time_confidence": time_conf,
                },
            })
        else:
            confidence = "unknown"
            entry.update({
                "cadence": freq,
                "cadence_gap_days": None,
                "next_expected_release_utc": None,
                "last_observed_release_date": None,
                "confidence": "unknown",
                "evidence": {
                    "kind": "config_frequency_fallback",
                    "note": (
                        "no verified publisher release-date evidence mapped to this "
                        "source; scheduler falls back to fallback_interval_seconds"
                    ),
                },
            })
        conf_counts[confidence] += 1
        entries[sid] = entry

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "no_ai": True,
        "generated_from": {
            "config_sources": len(sources),
            "release_dates_ids_fetched": sorted(alfred),
            "fred_release_membership_ids": sorted(membership),
            "evidence_endpoints": {
                "release_dates": "https://api.stlouisfed.org/fred/release/dates",
                "release_series": "https://api.stlouisfed.org/fred/release/series",
            },
            "fetch_errors": fetch_errors,
        },
        "confidence_counts": dict(conf_counts),
        "scheduler_contract": {
            "known": (
                "poll when now >= next_expected_release_utc and the source has not "
                "yet been polled for that release (last attempt precedes it)"
            ),
            "unknown": "poll on fallback_interval_seconds (pre-existing poll_seconds)",
        },
        "sources": dict(sorted(entries.items())),
    }
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description="build release_calendar.v1.json")
    parser.add_argument("--project-root", default=None)
    parser.add_argument("--out", default=None)
    parser.add_argument("--offline", action="store_true", help="no network; all unknown")
    parser.add_argument("--asof", default=None, help="YYYY-MM-DD 'today' override for determinism")
    args = parser.parse_args(argv)

    root = Path(args.project_root or Path(__file__).resolve().parents[2]).resolve()
    sys.path.insert(0, str(root))
    from live_data.rmv2_live.config import load_config, load_env_file

    config_path = root / "live_data" / "config" / "sources.v1.json"
    load_env_file(root / "live_data" / "config" / "local.env")
    config = load_config(config_path)
    api_key = os.environ.get("FRED_API_KEY")

    if args.asof:
        today = dt.date.fromisoformat(args.asof)
    else:
        today = dt.datetime.now(dt.timezone.utc).date()

    manifest = build(config, api_key, today, offline=args.offline)
    out = Path(args.out) if args.out else (root / "live_data" / "config" / "release_calendar.v1.json")
    text = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    out.write_text(text, encoding="utf-8")
    cc = manifest["confidence_counts"]
    print("wrote %s" % out)
    print("confidence:", cc)
    print("release/dates fetched:", manifest["generated_from"]["release_dates_ids_fetched"])
    if manifest["generated_from"]["fetch_errors"]:
        print("fetch_errors:", manifest["generated_from"]["fetch_errors"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
