"""B-OFFLINE-3 item 1 — land the Dallas Fed WEI native workbook as ONE flat
offline-current EVIDENCE lane (8 series), per owner ruling 2026-08-06
(question 20260806T065219Z_B-OFFLINE-3, APPROVED Option 1).

The 7 embedded as-of columns are preserved as DIAGNOSTIC EVIDENCE — they are NOT
store-native archive_snapshot_asof vintages and are NOT engine-replayable (the
single-vintage offline-current binder cannot represent multi-vintage as-of lanes;
that is the deferred B-OFFLINE-6). Every as-of series carries the plain-words
owner-mandated catalog note. Column B duplicates fred_wei_current in content and
is landed anyway so the native file is a self-contained evidence artifact; the
duplication is recorded in its note.

Zero network. Cache bytes ARE the source object (sha-manifested). Bound to the
already-registered `dallas_wei` family (registry role diagnostic_and_replay,
access B) — no new family, no owner family admission. enabled:false + archival:true.
Converge via a TARGETED refresh of THIS disabled source only (never a full
refresh — that was the B-OFFLINE-2 incident), which republishes the generation
AND writes operational_status in the same step (the B-LAND-3D gotcha).
"""
import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, "live_data")
from rmv2_live.config import load_config
from rmv2_live.pipeline import RefreshPipeline
from rmv2_live import feed_factory
from rmv2_live.adapters import normalize
from rmv2_live.offline_binding import bind_offline_current

ROOT = Path(".").resolve()
CFG_PATH = ROOT / "live_data/config/sources.v1.json"
CACHE = ROOT / "research/prefetch/wei/weekly-economic-index.xlsx"
MANIFEST = ROOT / "research/prefetch/wei/_manifest.jsonl"
SOURCE_ID = "dallas_wei_native_current"
UNIT = "percent scaled to four-quarter GDP growth"
SHEET = "2008-current"
AS_OF = "2026-08-06T07:45:00Z"

ASOF_DATES = {
    "WEI_DALLAS_ASOF_20250925": "2025-09-25",
    "WEI_DALLAS_ASOF_20240926": "2024-09-26",
    "WEI_DALLAS_ASOF_20230928": "2023-09-28",
    "WEI_DALLAS_ASOF_20220929": "2022-09-29",
    "WEI_DALLAS_ASOF_20220125": "2022-01-25",
    "WEI_DALLAS_ASOF_20210729": "2021-07-29",
    "WEI_DALLAS_ASOF_20200728": "2020-07-28",
}

DIAG_NOTE = (
    "Publisher as-of snapshot preserved as DIAGNOSTIC EVIDENCE. This is NOT a "
    "store-native archive_snapshot_asof vintage and is NOT engine-replayable. "
    "It may not be used as an as-of input by any replay, Watch, or index path "
    "until re-landed as a true vintage (see B-OFFLINE-6)."
)


def _members():
    members = [{
        "series_id": "WEI_DALLAS_NATIVE",
        "column_kind": "current",
        "asof_date": None,
        "label": (
            "Weekly Economic Index (Lewis-Mertens-Stock), Dallas Fed native "
            "workbook current column. DIAGNOSTIC EVIDENCE, not a clean "
            "construction input. DUPLICATES the fred_wei_current headline lane "
            "(registry row 59) in content; landed so the native file is a "
            "self-contained evidence artifact."
        ),
    }]
    for sid, iso in ASOF_DATES.items():
        members.append({
            "series_id": sid,
            "column_kind": "asof",
            "asof_date": iso,
            "label": "WEI publisher as-of %s snapshot. %s" % (iso, DIAG_NOTE),
        })
    return members


def _source():
    return {
        "adapter": "dallas_wei_xlsx",
        "allowed_hosts": ["www.dallasfed.org"],
        "archival": True,
        "coverage_source_ids": ["dallas_wei"],
        "enabled": False,
        "endpoint": (
            "https://www.dallasfed.org/-/media/documents/research/wei/"
            "weekly-economic-index.xlsx"
        ),
        "expected_content_types": [
            "application/octet-stream",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ],
        "frequency": "weekly",
        "information_set_mode": "substituted_diagnostic",
        "label": (
            "Dallas Fed Weekly Economic Index native workbook (current column + "
            "7 embedded publisher as-of snapshots) [OFFLINE-CURRENT flat "
            "EVIDENCE lane; substituted_diagnostic; as-of columns are NOT "
            "store-native vintages, see per-series notes; B-OFFLINE-3]"
        ),
        "max_bytes": 3000000,
        "method_version": "dallas_wei_native_offline.v1",
        "poll_seconds": 86400,
        "publisher": "Federal Reserve Bank of Dallas",
        "publisher_release_clock": (
            "current column released Thursday ~11:30 America/New_York; the 7 "
            "as-of columns are publisher-fixed historical snapshots dated in "
            "their headers, not a live release clock"
        ),
        "rights_status": "published_output_with_component_rights",
        "secret_env": None,
        "secret_required": False,
        "series": {
            "index_label": "Dallas Fed Weekly Economic Index native workbook",
            "unit": UNIT,
            "vintage_sheet": SHEET,
            "members": _members(),
        },
        "source_id": SOURCE_ID,
        "value_status": "actual",
    }


def _manifest():
    rec = None
    for line in open(MANIFEST):
        line = line.strip()
        if line:
            rec = json.loads(line)
    body = CACHE.read_bytes()
    sha = hashlib.sha256(body).hexdigest()
    if sha != rec["sha256"]:
        raise SystemExit("SHA MISMATCH: cache %s vs manifest %s" % (sha, rec["sha256"]))
    if len(body) != rec["bytes"]:
        raise SystemExit("LENGTH MISMATCH")
    manifest = {
        "fetch_utc": rec["fetch_utc"],
        "source_bytes_length": len(body),
        "source_sha256": sha,
        "url": rec["url"],
    }
    return body, manifest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    src = _source()
    body, manifest = _manifest()
    cfg = load_config(CFG_PATH)
    if SOURCE_ID in {s["source_id"] for s in cfg["sources"]}:
        raise SystemExit("COLLISION: %s already in config" % SOURCE_ID)
    pipeline = RefreshPipeline(ROOT, cfg)
    pipeline.store.initialize()
    # clobber-proof: append-only family + registry-binding gate BEFORE any write.
    feed_factory._validate_source_candidate(ROOT, cfg, src)
    recs = normalize(src, body, AS_OF)
    by_series = {}
    for r in recs:
        by_series[r["series_id"]] = by_series.get(r["series_id"], 0) + 1
    print("GATE PASS. records=%d series=%d" % (len(recs), len(by_series)))
    print("series counts:", json.dumps(by_series, sort_keys=True))
    if a.dry:
        json.dump({"series_counts": by_series, "records": len(recs)},
                  open("research/OFFLINE3_wei_plan.json", "w"), indent=1)
        print("DRY: gated + parsed, no writes")
        return

    oc = bind_offline_current(pipeline, src, body, manifest, AS_OF)
    print("BOUND", oc["outcome"], "records", oc["record_count"],
          "receipt", oc["receipt_sha256"][:12])
    # append to config and persist
    raw = json.load(open(CFG_PATH))
    raw["sources"] = list(raw["sources"]) + [src]
    tmp = str(CFG_PATH) + ".tmp"
    json.dump(raw, open(tmp, "w"), indent=1, sort_keys=True)
    os.replace(tmp, CFG_PATH)
    print("CONFIG written; n_sources", len(raw["sources"]),
          "archival", sum(1 for s in raw["sources"] if s.get("archival")))
    # TARGETED zero-network refresh of THIS disabled source only -> republish
    # generation (now binding the WEI archival head) + write operational_status.
    cfg2 = load_config(CFG_PATH)
    pipe2 = RefreshPipeline(ROOT, cfg2)
    result = pipe2.refresh(source_ids=[SOURCE_ID], due_only=False)
    outcomes = result.get("outcomes") if isinstance(result, dict) else None
    pointer = result.get("pointer") if isinstance(result, dict) else None
    print("TARGETED REFRESH outcomes:", json.dumps(outcomes))
    print("POINTER generation:",
          (pointer or {}).get("generation_sha256", "<none>"))
    json.dump({"bound": oc, "refresh": {"outcomes": outcomes, "pointer": pointer}},
              open("research/OFFLINE3_wei_land_out.json", "w"), indent=1, default=str)


main()
