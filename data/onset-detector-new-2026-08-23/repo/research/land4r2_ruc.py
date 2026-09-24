"""B-LAND-4-R2 — land the Philadelphia Fed RTDSM unemployment-rate (RUC) deep
as-of vintages as an OWN-BASE lane RTDSM_RUC.DEEPASOF*, NEVER aliased to UNRATE.

Authority: owner answer _mailbox/answers/20260805T232615Z_B-LAND-4_RTDSM.md
(Option 2, own-base) + batch B-LAND-4-R2_RTDSM_RUC_PROOF.md. Offline, no network:
reuses the proven append-only family gate, the RTDSM xlsx->output_type=2
transcoder (rtdsm_offline_transcoder), the proven deep parser (window+cap) and
the proven offline binder. Source bytes come from the CH-R24 prefetch cache
(research/prefetch/rtdsm/ruc/rucQvMd.xlsx, sha f9328e69...).
"""
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, "live_data")
from rmv2_live.config import load_config
from rmv2_live.store import LiveStore
from rmv2_live.pipeline import RefreshPipeline
from rmv2_live import feed_factory
from rmv2_live import rtdsm_offline_transcoder as rot
from rmv2_live.offline_binding import bind_offline_vintage

ROOT = Path(".").resolve()
CFG_PATH = ROOT / "live_data/config/sources.v1.json"
XLSX = "research/prefetch/rtdsm/ruc/rucQvMd.xlsx"
AS_OF = "2026-08-06T00:00:00Z"
ATT = "2026-08-06T04:30:00Z"
SOURCE_ID = "philadelphia_rtdsm_ruc_vintages_deep"
BASE = "RTDSM_RUC"


def source_for():
    return {
        "adapter": "fred_json_api_vintages_deep",
        "allowed_hosts": ["www.philadelphiafed.org"],
        "archival": True,
        "coverage_source_ids": ["philadelphia_rtdsm"],
        "enabled": False,
        "endpoint": (
            "https://www.philadelphiafed.org/-/media/FRBP/Assets/Surveys-And-Data/"
            "real-time-data/data-files/xlsx/rucQvMd.xlsx"
        ),
        "expected_content_types": [
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ],
        "frequency": "quarterly",
        "information_set_mode": "archive_snapshot_asof",
        "label": (
            "Unemployment rate (Philadelphia Fed Real-Time Data Set, "
            "quarterly-vintage as-of snapshots) [DEEP pre-2020 as-of window, "
            "own-base RTDSM lane, NEAR of UNRATE — never aliased]"
        ),
        "max_bytes": 33554432,
        "method_version": "philadelphia_rtdsm_ruc_vintages_deep.v1",
        "poll_seconds": 21600,
        "publisher": "Federal Reserve Bank of Philadelphia",
        "publisher_release_clock": (
            "RTDSM quarterly vintage release; underlying publisher release time "
            "null unless separately proven"
        ),
        "rights_status": "publisher_terms_and_source_rights",
        "secret_env": None,
        "secret_required": False,
        "series": {
            "label": "Unemployment rate (RTDSM real-time as-of snapshots)",
            "series_id": BASE,
            "unit": "Percent",
        },
        "source_id": SOURCE_ID,
        "value_status": "actual",
    }


def measure_plan(src):
    """Transcode + window-gate WITHOUT writing: what would land."""
    from rmv2_live.adapters import parse_fred_json_api_vintages_deep
    from rmv2_live.vintage_csv_transcoder import body_bytes
    body, prov = rot.transcode_base([XLSX], source=src)
    src_vintages = sorted({e["vintage"] for e in prov})
    records = parse_fred_json_api_vintages_deep(src, body_bytes(body), AS_OF)
    landed_vintages = sorted({r["series_id"].split("DEEPASOF")[1] for r in records})
    periods = sorted({r["observation_period"] for r in records})
    return {
        "workbook_vintages": len(src_vintages),
        "workbook_vmin": src_vintages[0],
        "workbook_vmax": src_vintages[-1],
        "landed_vintages": len(landed_vintages),
        "landed_vmin": landed_vintages[0] if landed_vintages else None,
        "landed_vmax": landed_vintages[-1] if landed_vintages else None,
        "dropped_out_of_window": len(src_vintages) - len(landed_vintages),
        "landed_records": len(records),
        "obs_periods": len(periods),
        "obs_min": periods[0] if periods else None,
        "obs_max": periods[-1] if periods else None,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    cfg = load_config(CFG_PATH)
    src = source_for()
    # prove the append-only family + registry-binding gate BEFORE any write.
    feed_factory._validate_source_candidate(ROOT, cfg, src)
    plan = measure_plan(src)
    print("GATE PASS; plan=%s" % json.dumps(plan))
    if a.dry:
        json.dump(plan, open("research/BLAND4R2_plan.json", "w"), indent=1)
        print("DRY — no writes")
        return

    pipeline = RefreshPipeline(ROOT, cfg)
    pipeline.store.initialize()
    oc = bind_offline_vintage(pipeline, src, [XLSX], AS_OF, transcoder=rot)
    print("BOUND RTDSM_RUC records=%d series=%d receipt=%s"
          % (oc["record_count"], len(oc["landed_series"]), oc["receipt_sha256"][:12]))
    cfg["sources"].append(src)
    raw = json.load(open(CFG_PATH))
    raw["sources"] = cfg["sources"]
    tmp = str(CFG_PATH) + ".tmp"
    json.dump(raw, open(tmp, "w"), indent=1, sort_keys=True)
    os.replace(tmp, CFG_PATH)
    print("CONFIG written; n_sources", len(raw["sources"]))
    snap = pipeline.build_snapshot(ATT)
    cov = pipeline.build_coverage(ATT)
    st = pipeline.build_status(ATT)
    ptr = pipeline.store.publish_generation(snap, st, cov)
    print("PUBLISHED generation", ptr.get("generation_sha256"))
    json.dump(
        {"outcome": oc, "plan": plan, "pointer": ptr,
         "landed_series_sample": sorted(oc["landed_series"])[:3]},
        open("research/BLAND4R2_land_out.json", "w"), indent=1,
    )


main()
