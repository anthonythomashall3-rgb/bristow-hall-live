"""B-ACQ-RTDSM-GDI — land the 24 Philadelphia Fed RTDSM Gross Domestic Income
(GDI-account) own-base deep as-of vintage lanes, NEVER aliased onto any GDP-side
FRED series (GDI is NOT GDP -- Phil Fed states so; §3.1).

Mechanism is IDENTICAL to B-RTDSM-ROLL_TRANCHE_A2 (the proven RTDSM shape -- ZERO
new shapes, §6.1): the RTDSM xlsx->output_type=2 transcoder, the proven deep
parser (window + cap), the proven offline binder, an own-base id per var. Source
bytes come from the CH-R24 prefetch cache; ZERO network. Quarterly-vintage QvQd
file per var (dossier cost rule: QvQd not MvQd for quarterly concepts).

Authority: acquisition only (§22.4 -- NOTHING DERIVES). Own-base ruling is the
roster-wide RTDSM ruling (L534 feed_factory) + the 2026-08-08 decision-delegation
ruling (reversible, evidence-backed, non-§22.4 acquisition decision). NEAR relation
to GDP-side concepts carried by coverage_source_ids=philadelphia_rtdsm, never an
alias.
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

ROOT = Path(".").resolve()
CFG_PATH = ROOT / "live_data/config/sources.v1.json"
AS_OF = "2026-08-08T00:00:00Z"

NOTE = (
    "Landed as real-time DEPTH / replay acquisition of the INCOME side of the "
    "national accounts (GDI). NOT a channel-diversity claim and NOT GDP -- GDI "
    "uses largely independent source data (Phil Fed gen_doc_GDI). Own-base "
    "RTDSM lane, NEVER aliased onto any GDP-side FRED series."
)

# The 24 RTDSM GDI-account variables (gen_doc_GDI). (var, unit, concept).
# All carry a quarterly-vintage QvQd workbook (verified present in prefetch).
GDI = [
    ("YNGDI",     "Billions of Dollars",          "Nominal gross domestic income"),
    ("YRGDI",     "Billions of Chained Dollars",  "Real gross domestic income"),
    ("YPDGDP",    "Index",                        "GDI-side price index / deflator"),
    ("YNCOMPEP",  "Billions of Dollars",          "Compensation of employees, paid"),
    ("YNWS",      "Billions of Dollars",          "Wage and salary disbursements"),
    ("YNSWS",     "Billions of Dollars",          "Supplements to wages and salaries"),
    ("YNSD",      "Billions of Dollars",          "Wage and salary, other (disbursements detail)"),
    ("YNTAXR",    "Billions of Dollars",          "Taxes on production and imports, receipts"),
    ("YNCTAX",    "Billions of Dollars",          "Corporate income taxes"),
    ("YNGSUB",    "Billions of Dollars",          "Subsidies (less)"),
    ("YNOS",      "Billions of Dollars",          "Net operating surplus"),
    ("YNOSG",     "Billions of Dollars",          "Net operating surplus, government enterprises"),
    ("YNOSP",     "Billions of Dollars",          "Net operating surplus, private enterprises"),
    ("YNCFC",     "Billions of Dollars",          "Consumption of fixed capital"),
    ("YNCFCG",    "Billions of Dollars",          "Consumption of fixed capital, government"),
    ("YNCFCP",    "Billions of Dollars",          "Consumption of fixed capital, private"),
    ("YNCPRFW",   "Billions of Dollars",          "Corporate profits with IVA & CCAdj"),
    ("YNCPRFATW", "Billions of Dollars",          "Corporate profits after tax with IVA & CCAdj"),
    ("YNUCPRFW",  "Billions of Dollars",          "Undistributed corporate profits with IVA & CCAdj"),
    ("YNIPAID",   "Billions of Dollars",          "Net interest and misc payments"),
    ("YNDPAID",   "Billions of Dollars",          "Net dividends paid"),
    ("YNPINCW",   "Billions of Dollars",          "Proprietors' income with IVA & CCAdj"),
    ("YNRINC",    "Billions of Dollars",          "Rental income of persons with CCAdj"),
    ("YNTRPAY",   "Billions of Dollars",          "Business current transfer payments"),
]


def xlsx_for(var):
    return "research/prefetch/rtdsm/%s/%sQvQd.xlsx" % (var.lower(), var.lower())


def source_for(var, unit, concept):
    base = "RTDSM_%s" % var
    sid = "philadelphia_rtdsm_%s_vintages_deep" % var.lower()
    fname = "%sQvQd.xlsx" % var.lower()
    return {
        "adapter": "fred_json_api_vintages_deep",
        "allowed_hosts": ["www.philadelphiafed.org"],
        "archival": True,
        "coverage_source_ids": ["philadelphia_rtdsm"],
        "enabled": False,
        "endpoint": (
            "https://www.philadelphiafed.org/-/media/FRBP/Assets/Surveys-And-Data/"
            "real-time-data/data-files/xlsx/%s" % fname
        ),
        "expected_content_types": [
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ],
        "frequency": "quarterly",
        "information_set_mode": "archive_snapshot_asof",
        "label": (
            "%s (Philadelphia Fed Real-Time Data Set, quarterly-vintage as-of "
            "snapshots) [DEEP pre-2020 as-of window, own-base RTDSM GDI lane -- "
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
        "workbook_vmin": src_vintages[0] if src_vintages else None,
        "workbook_vmax": src_vintages[-1] if src_vintages else None,
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
    ap.add_argument("--only", default=None, help="comma list of vars to land")
    a = ap.parse_args()

    todo = GDI
    if a.only:
        want = set(a.only.upper().split(","))
        todo = [t for t in GDI if t[0] in want]

    plans = []
    for var, unit, concept in todo:
        cfg = load_config(CFG_PATH)
        src = source_for(var, unit, concept)
        if not a.dry:
            feed_factory._validate_source_candidate(ROOT, cfg, src)
        plan = measure_plan(src, xlsx_for(var))
        plans.append(plan)
        print("GATE PASS %s; plan=%s" % (src["source_id"], json.dumps(plan)))
    json.dump(plans, open("research/BLAND_RTDSM_GDI_plan.json", "w"), indent=1)
    total_v = sum(p["landed_vintages"] for p in plans)
    total_r = sum(p["landed_records"] for p in plans)
    print("TOTALS landed_vintages=%d landed_records=%d est_MB=%.0f"
          % (total_v, total_r, total_v * 0.83))
    if a.dry:
        print("DRY -- gated + planned + measured, NO writes")
        return

    from rmv2_live.offline_binding import bind_offline_vintage
    bound = []
    for var, unit, concept in todo:
        cfg = load_config(CFG_PATH)
        src = source_for(var, unit, concept)
        pipeline = RefreshPipeline(ROOT, cfg)
        pipeline.store.initialize()
        oc = bind_offline_vintage(pipeline, src, [xlsx_for(var)], AS_OF, transcoder=rot)
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

    sids = ["philadelphia_rtdsm_%s_vintages_deep" % var.lower() for var, *_ in todo]
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
        open("research/BLAND_RTDSM_GDI_out.json", "w"), indent=1,
    )


main()
