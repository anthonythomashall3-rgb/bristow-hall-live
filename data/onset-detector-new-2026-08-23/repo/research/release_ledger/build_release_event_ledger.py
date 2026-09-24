#!/usr/bin/env python3
"""B-RELEASE-LEDGER-1: release-event ledger, as-of-capable lanes first.

One row per (series, release_datetime, evidence). No network. No store write.
Partial coverage recorded; no silent caps (S19.4).

Tiers
- asof_member : the 24 archive_snapshot_asof labeled source_matrix lanes. Their
  knowledge-date release events live IN THE STORE: each normalized record's
  series_id carries a `.ASOF<yyyymmdd>` (or `.DEEPASOF<yyyymmdd>`) suffix = the
  provider-vintage availability date. One event per distinct knowledge date.
  Evidence = the normalized payload (content-addressed sha256) + provenance_url.
- extended   : every other locally-retained ALFRED vintage series
  (research/prefetch/alfred_meta/*.vintages.json). Each vintage_date = a release
  event. As-of-CAPABLE evidence, not a labeled member.
- spf        : SPF_MEDIAN_* ALFRED vintage dumps.

release TIME: store as-of records carry release_at=null and ALFRED vintage_dates
are date-only. Every row time_precision='date', release_time_utc=null (unknown,
S19.1, never fabricated). A real-time claim needing intra-day timing is NOT
certifiable from this ledger alone.
"""
import glob
import json
import os
import re
import subprocess

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
META = os.path.join(REPO, "research/prefetch/alfred_meta")
HEADS = os.path.join(REPO, "live_data/runtime/source_heads")
OUT_JSONL = os.path.join(REPO, "research/release_ledger/release_event_ledger.v1.jsonl")
OUT_SUM = os.path.join(REPO, "research/release_ledger/release_event_ledger.summary.v1.json")

# 24 archive_snapshot_asof labeled source_ids -> underlying FRED base symbol.
# (source_matrix rows with information_set_mode=archive_snapshot_asof.)
ASOF_LANES = {
    "cdc_resp_publication_history": None,       # non-FRED publisher; no dated vintage lane
    "fred_cmrmtspl_api_vintages": "CMRMTSPL",
    "fred_gacdfsa066msfrbphi_api_vintages": "GACDFSA066MSFRBPHI",
    "fred_gdpc1_api_vintages": "GDPC1",
    "fred_gdpc1_api_vintages_deep": "GDPC1",
    "fred_houst_api_vintages": "HOUST",
    "fred_houst_api_vintages_deep": "HOUST",
    "fred_icsa_api_vintages": "ICSA",
    "fred_indpro_api_vintages": "INDPRO",
    "fred_indpro_api_vintages_deep": "INDPRO",
    "fred_iursa_api_vintages": "IURSA",
    "fred_nfci_api_vintages": "NFCI",
    "fred_payems_api_vintages": "PAYEMS",
    "fred_payems_api_vintages_deep": "PAYEMS",
    "fred_permit_api_vintages": "PERMIT",
    "fred_permit_api_vintages_deep": "PERMIT",
    "fred_sahmrealtime_api_vintages": "SAHMREALTIME",
    "fred_tcu_api_vintages": "TCU",
    "fred_tcu_api_vintages_deep": "TCU",
    "fred_umcsent_api_vintages": "UMCSENT",
    "fred_umcsent_api_vintages_deep": "UMCSENT",
    "fred_unrate_api_vintages": "UNRATE",
    "fred_unrate_api_vintages_deep": "UNRATE",
    "fred_w875rx1_api_vintages": "W875RX1",
}

DATE_RE = re.compile(r"ASOF(\d{8})")


def norm_path(sha):
    return os.path.join(REPO, "live_data/store/normalized/sha256", sha[:2], sha + ".json")


def grep_distinct(pattern, path):
    """Distinct capture matches; collapse with sort -u at C speed (huge files)."""
    try:
        p = subprocess.run(f"grep -oE '{pattern}' {path!r} | sort -u",
                           shell=True, capture_output=True, text=True, check=False)
    except Exception:
        return set()
    return set(p.stdout.split())


def first_match(pattern, path):
    out = subprocess.run(["grep", "-oE", pattern, path],
                         capture_output=True, text=True, check=False).stdout
    line = out.split("\n", 1)[0]
    return line or None


def iso(d8):
    return f"{d8[:4]}-{d8[4:6]}-{d8[6:8]}"


def build_asof_member(rows, per_lane):
    covered_symbols = set()
    for sid, sym in ASOF_LANES.items():
        head = os.path.join(HEADS, sid + ".json")
        rec = {"source_id": sid, "symbol": sym}
        if not os.path.exists(head):
            rec["status"] = "no_source_head"
            per_lane.append(rec)
            continue
        h = json.load(open(head))
        nsha = h.get("normalized_sha256")
        np = norm_path(nsha) if nsha else None
        if not np or not os.path.exists(np):
            rec["status"] = "no_normalized_payload"
            per_lane.append(rec)
            continue
        # knowledge dates from series_id suffix (ASOF / DEEPASOF)
        dates = sorted({iso(m) for m in
                        {DATE_RE.search(t).group(1)
                         for t in grep_distinct(r"\.(DEEP)?ASOF[0-9]{8}", np)
                         if DATE_RE.search(t)}})
        prov = first_match(r'"provenance_url":"[^"]*"', np)
        deep = sid.endswith("_deep")
        rec.update({
            "status": "ok",
            "knowledge_date_events": len(dates),
            "first": dates[0] if dates else None,
            "last": dates[-1] if dates else None,
            "normalized_sha256": nsha,
            "source_bytes_sha256": h.get("source_bytes_sha256"),
        })
        per_lane.append(rec)
        if sym and dates:
            covered_symbols.add(sym)
        for d in dates:
            rows.append({
                "series": sym or sid,
                "source_id": sid,
                "release_datetime": d,
                "time_precision": "date",
                "release_time_utc": None,
                "tier": "asof_member",
                "as_of_member": True,
                "vintage_depth": "deep" if deep else "standard",
                "evidence_kind": "store_asof_vintage_snapshot",
                "evidence_normalized_sha256": nsha,
                "evidence_source_bytes_sha256": h.get("source_bytes_sha256"),
                "evidence_provenance_sample": prov,
            })
    return covered_symbols


def build_alfred(rows):
    files = sorted(glob.glob(os.path.join(META, "*.vintages.json")))
    ext_series = spf_series = 0
    for path in files:
        series = os.path.basename(path)[:-len(".vintages.json")]
        d = json.load(open(path))
        vds = d.get("vintage_dates") or []
        rel = os.path.relpath(path, REPO)
        tier = "spf" if series.startswith("SPF_") else "extended"
        if vds:
            if tier == "spf":
                spf_series += 1
            else:
                ext_series += 1
        for vd in vds:
            rows.append({
                "series": series,
                "source_id": "alfred_meta/" + os.path.basename(path),
                "release_datetime": vd,
                "time_precision": "date",
                "release_time_utc": None,
                "tier": tier,
                "as_of_member": False,
                "vintage_depth": "alfred_vintage_dates",
                "evidence_kind": "alfred_vintage_dates",
                "evidence_file": rel,
                "evidence_provenance_sample":
                    "fred/series/vintagedates (ALFRED realtime)",
            })
    return len(files), ext_series, spf_series


def main():
    rows = []
    per_lane = []
    covered_symbols = build_asof_member(rows, per_lane)
    n_files, ext_series, spf_series = build_alfred(rows)

    rows.sort(key=lambda r: (r["tier"], r["series"], r["release_datetime"]))
    with open(OUT_JSONL, "w") as fh:
        for r in rows:
            fh.write(json.dumps(r, sort_keys=True) + "\n")

    tier_counts = {}
    for r in rows:
        tier_counts[r["tier"]] = tier_counts.get(r["tier"], 0) + 1

    asof_symbols = sorted({s for s in ASOF_LANES.values() if s})
    missing = sorted(set(asof_symbols) - covered_symbols)
    cdc = next(x for x in per_lane if x["source_id"] == "cdc_resp_publication_history")

    summary = {
        "batch": "B-RELEASE-LEDGER-1",
        "artifact": os.path.relpath(OUT_JSONL, REPO),
        "row_key": "(series, release_datetime, evidence)",
        "total_release_events": len(rows),
        "events_by_tier": tier_counts,
        "asof_member_pool": {
            "labeled_source_ids": len(ASOF_LANES),
            "fred_base_symbols": asof_symbols,
            "symbols_covered": sorted(covered_symbols),
            "symbols_missing": missing,
            "coverage_pct_asof_symbols":
                round(100.0 * len(covered_symbols) / max(1, len(asof_symbols)), 1),
            "cdc_publication_history_status":
                f"carried, {cdc.get('knowledge_date_events', 0)} dated knowledge "
                "events (single snapshot lane; no per-vintage date encoding) - "
                "NOT counted covered (S19.4)",
            "per_lane": per_lane,
        },
        "extended_alfred": {
            "vintage_files_scanned": n_files,
            "extended_series_with_events": ext_series,
            "spf_series_with_events": spf_series,
        },
        "sources_named_in_brief_status": {
            "alfred_release_date_dumps": "USED - store as-of lanes (knowledge dates) "
            "+ alfred_meta vintage_dates",
            "spf_release_dates_txt": "ABSENT on disk; SPF via ALFRED SPF_MEDIAN_* "
            "vintage dumps",
            "fraser_bea_histdata_publisher_calendars": "NOT parsed this batch "
            "(partial coverage allowed; deferred to B-RELEASE-LEDGER-2)",
        },
        "caveats": [
            "release_time_utc=null for EVERY row (store release_at null; ALFRED "
            "vintage_dates date-only). time_precision=date. Sub-day real-time claims "
            "NOT certifiable from this ledger (S19.1).",
            "asof_member events are provider-vintage AVAILABILITY dates (ALFRED "
            "realtime boundaries), not proven underlying-publisher first-release "
            "timestamps (strict_publisher_first_release_proven=false in store bytes).",
            "extended/spf tiers are as-of-CAPABLE evidence, not labeled as-of members.",
        ],
    }
    json.dump(summary, open(OUT_SUM, "w"), indent=1, sort_keys=True)
    print(json.dumps(summary, indent=1, sort_keys=True))


if __name__ == "__main__":
    main()
