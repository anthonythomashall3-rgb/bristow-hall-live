"""B-LAND-10-R2 — land RTDSM tranche A1 (cpi / m1 / m2) as OWN-BASE deep as-of
lanes RTDSM_CPI / RTDSM_M1 / RTDSM_M2 .DEEPASOF*, NEVER aliased to a modern twin.

Authority: _mailbox/answers/20260806T120326Z_B-LAND-10_RTDSM_ROLLOUT_T1.md
(Option 2 — DEPTH/replay acquisition, NOT a channel-diversity claim) + batch
B-LAND-10-R2_RTDSM_A1_DEPTH.md. Offline, ZERO network: reuses the proven
append-only family gate, the RTDSM xlsx->output_type=2 transcoder
(rtdsm_offline_transcoder), the proven deep parser (window + cap) and the proven
offline binder. Source bytes come from the CH-R24 prefetch cache
(research/prefetch/rtdsm/<var>/<var>QvMd.xlsx). Do NOT proceed to A2/A3.

Publish via a TARGETED zero-network refresh of THE three disabled sources only
(never a full refresh); that writes operational_status in the same step.
"""
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, "live_data")
from rmv2_live.config import load_config
from rmv2_live.pipeline import RefreshPipeline
from rmv2_live import feed_factory
from rmv2_live import rtdsm_offline_transcoder as rot
from rmv2_live.offline_binding import bind_offline_vintage

ROOT = Path(".").resolve()
CFG_PATH = ROOT / "live_data/config/sources.v1.json"
AS_OF = "2026-08-06T00:00:00Z"
ATT = "2026-08-06T15:52:00Z"

# Owner-mandated catalog note, verbatim, on EVERY series (author into the label
# so it is visible wherever the source is enumerated; config._require_keys
# refuses any extra source field).
NOTE = (
    "Landed as real-time DEPTH / replay acquisition. NOT a channel-diversity "
    "claim -- CH-R58 measured RTDSM's diversity payoff as collinear with the "
    "already-covered output factor."
)

# tranche A1: (workbook var, prefetch file, series unit, human concept)
A1 = [
    ("CPI", "research/prefetch/rtdsm/cpi/cpiQvMd.xlsx", "Index", "Consumer Price Index (near of CPIAUCSL)"),
    ("M1", "research/prefetch/rtdsm/m1/m1QvMd.xlsx", "Billions of Dollars", "Money stock M1 (near of M1SL)"),
    ("M2", "research/prefetch/rtdsm/m2/m2QvMd.xlsx", "Billions of Dollars", "Money stock M2 (near of M2SL)"),
]


def source_for(var, xlsx, unit, concept):
    base = "RTDSM_%s" % var
    sid = "philadelphia_rtdsm_%s_vintages_deep" % var.lower()
    return {
        "adapter": "fred_json_api_vintages_deep",
        "allowed_hosts": ["www.philadelphiafed.org"],
        "archival": True,
        "coverage_source_ids": ["philadelphia_rtdsm"],
        "enabled": False,
        "endpoint": (
            "https://www.philadelphiafed.org/-/media/FRBP/Assets/Surveys-And-Data/"
            "real-time-data/data-files/xlsx/%sQvMd.xlsx" % var.lower()
        ),
        "expected_content_types": [
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ],
        "frequency": "quarterly",
        "information_set_mode": "archive_snapshot_asof",
        "label": (
            "%s (Philadelphia Fed Real-Time Data Set, quarterly-vintage as-of "
            "snapshots) [DEEP pre-2020 as-of window, own-base RTDSM lane -- "
            "never aliased]. %s" % (concept, NOTE)
        ),
        "max_bytes": 33554432,
        "method_version": "philadelphia_rtdsm_%s_vintages_deep.v1" % var.lower(),
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
            "label": "%s (RTDSM real-time as-of snapshots)" % concept,
            "series_id": base,
            "unit": unit,
        },
        "source_id": sid,
        "value_status": "actual",
    }


def measure_plan(src, xlsx):
    from rmv2_live.adapters import parse_fred_json_api_vintages_deep
    from rmv2_live.vintage_csv_transcoder import body_bytes
    body, prov = rot.transcode_base([xlsx], source=src)
    src_vintages = sorted({e["vintage"] for e in prov})
    records = parse_fred_json_api_vintages_deep(src, body_bytes(body), AS_OF)
    landed_vintages = sorted({r["series_id"].split("DEEPASOF")[1] for r in records})
    periods = sorted({r["observation_period"] for r in records})
    return {
        "base": src["series"]["series_id"],
        "source_id": src["source_id"],
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

    plans = []
    # 1) gate + plan every base BEFORE any write (each against fresh config).
    for var, xlsx, unit, concept in A1:
        cfg = load_config(CFG_PATH)
        src = source_for(var, xlsx, unit, concept)
        feed_factory._validate_source_candidate(ROOT, cfg, src)
        plan = measure_plan(src, xlsx)
        plans.append(plan)
        print("GATE PASS %s; plan=%s" % (src["source_id"], json.dumps(plan)))
    json.dump(plans, open("research/BLAND10R2_land_plan.json", "w"), indent=1)
    if a.dry:
        print("DRY -- gated + planned, no writes")
        return

    # 2) bind each base (fresh config reload per bind so the append-only gate
    #    sees the previously-appended sibling), append to config file.
    bound = []
    for var, xlsx, unit, concept in A1:
        cfg = load_config(CFG_PATH)
        src = source_for(var, xlsx, unit, concept)
        pipeline = RefreshPipeline(ROOT, cfg)
        pipeline.store.initialize()
        oc = bind_offline_vintage(pipeline, src, [xlsx], AS_OF, transcoder=rot)
        bound.append(oc)
        print("BOUND %s records=%d series=%d receipt=%s"
              % (src["series"]["series_id"], oc["record_count"],
                 len(oc["landed_series"]), oc["receipt_sha256"][:12]))
        raw = json.load(open(CFG_PATH))
        raw["sources"] = list(raw["sources"]) + [src]
        tmp = str(CFG_PATH) + ".tmp"
        json.dump(raw, open(tmp, "w"), indent=1, sort_keys=True)
        os.replace(tmp, CFG_PATH)
        print("CONFIG written; n_sources", len(raw["sources"]))

    # 3) TARGETED zero-network refresh of THE three disabled sources only ->
    #    republish generation + write operational_status in the same step.
    sids = ["philadelphia_rtdsm_%s_vintages_deep" % var.lower() for var, *_ in A1]
    cfg2 = load_config(CFG_PATH)
    pipe2 = RefreshPipeline(ROOT, cfg2)
    result = pipe2.refresh(source_ids=sids, due_only=False)
    outcomes = result.get("outcomes") if isinstance(result, dict) else None
    pointer = result.get("pointer") if isinstance(result, dict) else None
    print("TARGETED REFRESH outcomes:", json.dumps(outcomes))
    print("POINTER generation:", (pointer or {}).get("generation_sha256", "<none>"))
    json.dump(
        {"plans": plans, "bound": bound,
         "refresh": {"outcomes": outcomes, "pointer": pointer}},
        open("research/BLAND10R2_land_out.json", "w"), indent=1,
    )


main()
