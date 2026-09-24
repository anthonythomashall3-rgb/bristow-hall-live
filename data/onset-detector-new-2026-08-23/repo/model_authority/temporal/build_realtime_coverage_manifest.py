#!/usr/bin/env python3
"""Emit realtime_coverage_manifest.v1.json — store-read only, AI-free.

For every calendar month from the earliest available vintage to the present this
records which of the composite members (method_source/index_v1.py::CHANNELS) have
real, as-of vintage coverage in the live store, and rolls that up to channels,
non-empty channel count, and the share of total fixed channel weight that is
available.  The availability share deliberately remains below 1.0 when any
channel is missing so downstream thin-coverage disclaimers can fire.

Member realtime_status (per the B1.4 contract):
  * vintage             — the store holds ASOF (archive_snapshot_asof) vintages;
                          as-of coverage begins at the member's FIRST vintage month.
  * unrevised_certified — an unrevised series (current == first release) that needs
                          no vintages, but whose certificate is PENDING until B1.4;
                          conservatively NOT counted as covered yet.
  * none                — no as-of coverage and not certifiable.
  * contaminated        — applies to NFCI in months BEFORE its first vintage: the
                          Chicago Fed re-estimates NFCI's whole history weekly, so
                          pre-vintage NFCI is look-ahead, not absence — never
                          substitute it. NFCI counts as covered only from its first
                          vintage month onward.

Nothing is hand-written: CHANNELS is parsed from index_v1.py (never executed), the
member->store mapping is derived from the live config's FRED series ids, and every
first-vintage month is read from the immutable normalized store objects.
"""
from __future__ import annotations

import argparse
import ast
import datetime as dt
import json
import re
import sys
import urllib.parse
from pathlib import Path


# Regular vintages encode the as-of date as `<SERIES>.ASOF<YYYYMMDD>`; the deep
# lane uses `<SERIES>.DEEPASOF<YYYYMMDD>`. Matching bare `ASOF(\d{8})` captures the
# vintage date in BOTH (DEEPASOF contains ASOF), so the deep lane's earlier
# vintages are not silently dropped.
ASOF_RE = re.compile(rb"ASOF(\d{8})")
SCHEMA_VERSION = "recession-monitor-v2.realtime-coverage-manifest.v1"


def parse_channels(index_path):
    """Parse the CHANNELS literal from index_v1.py WITHOUT importing (no model run)."""
    tree = ast.parse(Path(index_path).read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "CHANNELS":
                    channels = ast.literal_eval(node.value)
                    # {channel: (weight, [members])}
                    return {k: (float(v[0]), list(v[1])) for k, v in channels.items()}
    raise SystemExit("CHANNELS not found in %s" % index_path)


def fred_series_of(source):
    series = source.get("series")
    if isinstance(series, dict) and series.get("series_id"):
        return str(series["series_id"]).upper()
    qs = urllib.parse.parse_qs(urllib.parse.urlparse(source["endpoint"]).query)
    for key in ("series_id", "id"):
        if qs.get(key):
            return str(qs[key][0]).upper()
    return None


def vintage_sources_by_series(config):
    """Map FRED series id -> [vintage source_ids] (regular + deep)."""
    out = {}
    for source in config["sources"]:
        if source["adapter"] in ("fred_json_api_vintages", "fred_json_api_vintages_deep"):
            fsid = fred_series_of(source)
            if fsid:
                out.setdefault(fsid, []).append(source["source_id"])
    return out


def normalized_path(store, source_id):
    head = store.read_source_head(source_id)
    digest = head["normalized_sha256"]
    return store.root / "normalized" / "sha256" / digest[:2] / (digest + ".json"), head


def earliest_vintage_month(path):
    """Stream the immutable normalized object for the minimum ASOF date.

    Reads raw bytes in chunks and regex-scans for `.ASOF<YYYYMMDD>` so a
    multi-hundred-MB vintage object never has to be parsed into Python objects.
    Returns (min_date, max_date) as date objects, or (None, None).
    """
    lo = hi = None
    tail = b""
    with open(path, "rb") as handle:
        while True:
            chunk = handle.read(4 * 1024 * 1024)
            if not chunk:
                break
            buf = tail + chunk
            for match in ASOF_RE.finditer(buf):
                token = match.group(1)
                try:
                    d = dt.date(int(token[:4]), int(token[4:6]), int(token[6:8]))
                except ValueError:
                    continue
                if lo is None or d < lo:
                    lo = d
                if hi is None or d > hi:
                    hi = d
            # keep a small overlap so a token split across the boundary is caught
            tail = buf[-16:]
    return lo, hi


def month_key(d):
    return "%04d-%02d" % (d.year, d.month)


def month_iter(start, end):
    """Inclusive month strings from start-month to end-month."""
    y, m = start.year, start.month
    out = []
    while (y, m) <= (end.year, end.month):
        out.append("%04d-%02d" % (y, m))
        m += 1
        if m > 12:
            m = 1
            y += 1
    return out


# Members that carry NO vintage source but are UNREVISED market/derived series:
# current value == first release, so they are usable as-of once certified. Their
# certificate is PENDING until B1.4, so they are reported unrevised_certified and
# are conservatively NOT counted as covered yet.
UNREVISED_CERTIFIED_PENDING = {"NASDAQ", "BAAAAA", "BAA10Y", "VIX"}
# member -> the FRED series whose vintage source carries it (when different from
# the member label used in CHANNELS).
MEMBER_SERIES = {
    "ICSA": "ICSA", "IURSA": "IURSA", "SAHM": "SAHMREALTIME", "UNRATEv": "UNRATE",
    "INDPRO": "INDPRO", "CMRMT": "CMRMTSPL", "TCU": "TCU",
    "PHILLY": "GACDFSA066MSFRBPHI", "NFCI": "NFCI",
    "PERMIT": "PERMIT", "HOUST": "HOUST", "UMCSENT": "UMCSENT", "W875": "W875RX1",
}
CONTAMINATED_MEMBERS = {"NFCI"}
# B1.4 unrevised certificates live here; the manifest is REGENERATED from them so
# nothing certificate-related is hand-written into the manifest (§14.5). An
# unrevised member is counted as covered only when its certificate status is
# "certified"; "pending"/"partial"/absent stay uncovered. covered_from_month is the
# earliest month the unrevised series can back an as-of cutoff (its first obs month).
CERT_DIR = Path("model_authority") / "temporal" / "unrevised_certificates"


def load_unrevised_certificate(root, member):
    """Return (status, covered_from_month, cert_relpath) for an unrevised member.

    status defaults to 'pending' when no certificate artifact exists.
    """
    path = Path(root) / CERT_DIR / (member + ".v1.json")
    if not path.exists():
        return "pending", None, None
    cert = json.loads(path.read_text(encoding="utf-8"))
    rel = str(CERT_DIR / (member + ".v1.json"))
    return cert.get("status", "pending"), cert.get("covered_from_month"), rel


def build(project_root):
    root = Path(project_root).resolve()
    sys.path.insert(0, str(root))
    from live_data.rmv2_live.config import load_config
    from live_data.rmv2_live.store import LiveStore

    config = load_config(root / "live_data" / "config" / "sources.v1.json")
    store = LiveStore(root, config)
    channels = parse_channels(root / "method_source" / "index_v1.py")
    vintage_by_series = vintage_sources_by_series(config)

    member_channel = {}
    channel_weight = {}
    channel_member_total = {}
    for channel, (weight, members) in channels.items():
        channel_weight[channel] = weight
        channel_member_total[channel] = len(members)
        for member in members:
            member_channel[member] = channel

    members_out = {}
    first_month = {}   # member -> first vintage month (str) for covered members
    for member, channel in member_channel.items():
        series = MEMBER_SERIES.get(member)
        sources = vintage_by_series.get(series, []) if series else []
        entry = {
            "channel": channel,
            "channel_weight": channel_weight[channel],
            "store_vintage_sources": sorted(sources),
            "fred_series": series,
        }
        if sources:
            lo = hi = None
            per_source = {}
            for source_id in sorted(sources):
                path, _head = normalized_path(store, source_id)
                s_lo, s_hi = earliest_vintage_month(path)
                per_source[source_id] = {
                    "first_vintage": s_lo.isoformat() if s_lo else None,
                    "latest_vintage": s_hi.isoformat() if s_hi else None,
                }
                if s_lo and (lo is None or s_lo < lo):
                    lo = s_lo
                if s_hi and (hi is None or s_hi > hi):
                    hi = s_hi
            entry["first_vintage_date"] = lo.isoformat() if lo else None
            entry["latest_vintage_date"] = hi.isoformat() if hi else None
            entry["per_source_vintage_span"] = per_source
            entry["first_vintage_month"] = month_key(lo) if lo else None
            if member in CONTAMINATED_MEMBERS:
                entry["realtime_status"] = "vintage"
                entry["contaminated_before_month"] = month_key(lo) if lo else None
                entry["contamination_note"] = (
                    "Chicago Fed re-estimates NFCI's whole history weekly; months "
                    "before the first vintage are look-ahead (contaminated), not "
                    "absence — never substitute pre-vintage NFCI."
                )
            else:
                entry["realtime_status"] = "vintage"
            first_month[member] = entry["first_vintage_month"]
        elif member in UNREVISED_CERTIFIED_PENDING:
            entry["realtime_status"] = "unrevised_certified"
            cert_status, covered_from, cert_rel = load_unrevised_certificate(
                root, member
            )
            if cert_status == "certified":
                entry["certificate"] = "certified"
                entry["certificate_artifact"] = cert_rel
                entry["covered_from_month"] = covered_from
                entry["certified_note"] = (
                    "B1.4 unrevised certificate issued: measured zero historical "
                    "movement across local snapshots; counted as covered from "
                    "covered_from_month onward."
                )
            else:
                entry["certificate"] = "pending"
                if cert_rel:
                    entry["certificate_artifact"] = cert_rel
                entry["covered_from_month"] = covered_from
                entry["pending_note"] = (
                    "unrevised series (current == first release); certificate is "
                    "pending (measured historical movement or no certificate) — not "
                    "counted as covered yet; barred from backing an as-of claim."
                )
        else:
            entry["realtime_status"] = "none"
        members_out[member] = entry

    # earliest covered month across all vintage members -> present month
    covered_first_months = [m for m in first_month.values() if m]
    if not covered_first_months:
        raise SystemExit("no vintage coverage found in store")
    earliest = min(covered_first_months)
    ey, em = int(earliest[:4]), int(earliest[5:7])
    latest_dates = [
        e.get("latest_vintage_date") for e in members_out.values()
        if e.get("latest_vintage_date")
    ]
    present = max(latest_dates)
    present_d = dt.date.fromisoformat(present)

    months = month_iter(dt.date(ey, em, 1), present_d)
    total_channel_weight = sum(channel_weight.values())
    if total_channel_weight <= 0:
        raise SystemExit("total channel weight must be positive")
    grid = []
    prev_key = None
    tiers = []
    for month in months:
        member_states = {}
        covered = []
        for member, channel in member_channel.items():
            entry = members_out[member]
            status = entry["realtime_status"]
            if status == "vintage":
                fvm = entry.get("first_vintage_month")
                if fvm and month >= fvm:
                    member_states[member] = "vintage"
                    covered.append(member)
                elif member in CONTAMINATED_MEMBERS:
                    member_states[member] = "contaminated"
                else:
                    member_states[member] = "absent_before_first_vintage"
            elif status == "unrevised_certified":
                cfm = entry.get("covered_from_month")
                if entry.get("certificate") == "certified" and (
                    not cfm or month >= cfm
                ):
                    member_states[member] = "unrevised_certified"
                    covered.append(member)
                else:
                    member_states[member] = "unrevised_certified_pending"
            else:
                member_states[member] = "none"
        channels_nonempty = sorted({member_channel[m] for m in covered})
        members_per_channel = {}
        for ch in channels:
            members_per_channel[ch] = sorted(
                m for m in covered if member_channel[m] == ch
            )
        available_weight_raw = round(
            sum(channel_weight[ch] for ch in channels_nonempty), 10
        )
        # available_channel_weight_raw counts a channel as fully available when >=1
        # member exists, hiding WITHIN-channel thinness (the §57.1 defect class one
        # level down: labor 1-of-4 read as a fully-available 0.30 channel at 2007-12).
        # Emit BOTH: the >=1-member weight above, and a member-fraction-weighted
        # weight that scales each channel's weight by the fraction of its members
        # actually covered as-of that month.
        within_channel_member_fraction = {}
        member_weighted_weight = 0.0
        for ch in channels:
            covered_n = len(members_per_channel[ch])
            total_n = channel_member_total[ch]
            frac = round(covered_n / total_n, 10) if total_n else 0.0
            within_channel_member_fraction[ch] = {
                "covered": covered_n,
                "total": total_n,
                "fraction": frac,
            }
            member_weighted_weight += channel_weight[ch] * frac
        member_weighted_weight = round(member_weighted_weight, 10)
        row = {
            "month": month,
            "covered_members": sorted(covered),
            "members_per_channel": members_per_channel,
            "within_channel_member_fraction": within_channel_member_fraction,
            "channels_nonempty": channels_nonempty,
            "nonempty_channel_count": len(channels_nonempty),
            "available_channel_weight_raw": available_weight_raw,
            "renormalized_available_weight": round(
                available_weight_raw / total_channel_weight, 10
            ),
            "member_weighted_channel_weight_raw": member_weighted_weight,
            "member_weighted_available_weight_share": round(
                member_weighted_weight / total_channel_weight, 10
            ),
            "member_states": member_states,
        }
        grid.append(row)
        # tier boundary = the covered-member SET changed
        key = tuple(sorted(covered))
        if key != prev_key:
            tiers.append({
                "tier_index": len(tiers),
                "from_month": month,
                "covered_members": sorted(covered),
                "nonempty_channel_count": len(channels_nonempty),
                "available_channel_weight_raw": available_weight_raw,
                "member_weighted_channel_weight_raw": member_weighted_weight,
                "within_channel_member_fraction": within_channel_member_fraction,
            })
            prev_key = key
    # close each tier's span: it runs until the month before the next tier begins.
    for i, tier in enumerate(tiers):
        if i + 1 < len(tiers):
            tier["to_month"] = _prev_month(tiers[i + 1]["from_month"])
        else:
            tier["to_month"] = months[-1]

    channel_summary = {
        ch: {"weight": channel_weight[ch], "members": members}
        for ch, (weight, members) in channels.items()
    }

    return {
        "schema_version": SCHEMA_VERSION,
        "no_ai": True,
        "generated_note": (
            "store-read only; CHANNELS parsed from index_v1.py (not executed); "
            "member count is authoritative from CHANNELS"
        ),
        "channels": channel_summary,
        "member_count": len(member_channel),
        "coverage_window": {"earliest_month": months[0], "present_month": months[-1]},
        "members": dict(sorted(members_out.items())),
        "coverage_tiers": tiers,
        "monthly_coverage": grid,
    }


def _prev_month(month):
    y, m = int(month[:4]), int(month[5:7])
    m -= 1
    if m < 1:
        m = 12
        y -= 1
    return "%04d-%02d" % (y, m)


def main(argv=None):
    parser = argparse.ArgumentParser(description="build realtime_coverage_manifest.v1.json")
    parser.add_argument("--project-root", default=None)
    parser.add_argument("--out", default=None)
    args = parser.parse_args(argv)
    root = Path(args.project_root or Path(__file__).resolve().parents[2]).resolve()
    manifest = build(root)
    out = Path(args.out) if args.out else (
        root / "model_authority" / "temporal" / "realtime_coverage_manifest.v1.json"
    )
    text = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    out.write_text(text, encoding="utf-8")
    import hashlib
    sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    print("wrote %s" % out)
    print("sha256 %s" % sha)
    print("member_count %d" % manifest["member_count"])
    print("window %s -> %s" % (
        manifest["coverage_window"]["earliest_month"],
        manifest["coverage_window"]["present_month"]))
    print("tiers %d" % len(manifest["coverage_tiers"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
