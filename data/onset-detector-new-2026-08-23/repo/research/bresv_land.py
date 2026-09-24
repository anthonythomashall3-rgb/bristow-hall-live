"""B-RESV-PROVEN land — two net-new reservation instances as offline-current
frozen snapshots on PROVEN shapes (§6.2, zero new parser shapes). Zero network:
cache bytes ARE the source object. §22.4 acquisition only; owner ruling
2026-08-08 current_revised, BARRED from as-of/real-time claim.

  fred_recprousm156n_api_current_offline  RECPROUSM156N  fred_json_api
  census_eits_mwtsadv_current_offline     mwtsadv EITS   census_api
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
from rmv2_live.offline_binding import bind_offline_current

ROOT = Path(".").resolve()
CFG_PATH = ROOT / "live_data/config/sources.v1.json"
CACHE = ROOT / "research/prefetch/bresv"
AS_OF = os.environ["BRESV_ASOF"]
ATT = os.environ["BRESV_ATT"]

BAR = ("current_revised, BARRED from as-of / real-time claim per owner ruling "
       "2026-08-08; NOT admitted to any channel per section 22.4")

ROSTER = json.load(open(CACHE / "mwtsadv_roster.json"))


def _manifest(body_path, url):
    body = body_path.read_bytes()
    return body, {
        "fetch_utc": AS_OF,
        "source_bytes_length": len(body),
        "source_sha256": hashlib.sha256(body).hexdigest(),
        "url": url,
    }


FRED = {
    "adapter": "fred_json_api",
    "allowed_hosts": ["api.stlouisfed.org"],
    "archival": True,
    "coverage_source_ids": ["fred_current_provider"],
    "enabled": False,
    "endpoint": ("https://api.stlouisfed.org/fred/series/observations?"
                 "series_id=RECPROUSM156N&file_type=json&"
                 "observation_start=1967-06-01"),
    "expected_content_types": ["application/json"],
    "frequency": "monthly",
    "information_set_mode": "current_revised",
    "label": ("Smoothed U.S. Recession Probabilities (NSA) (keyed FRED API, "
              "current vintage) [OFFLINE-CURRENT frozen snapshot; B-RESV-PROVEN; "
              "EXTERNAL COMPARATOR (target-trained recession probability), NEVER "
              "a construction input per CLAUDE.md; " + BAR + "]"),
    "max_bytes": 8000000,
    "method_version": "fred_recprousm156n_json_api_current_offline.v1",
    "poll_seconds": 3600,
    "publisher": "Federal Reserve Bank of St. Louis provider",
    "publisher_release_clock": ("provider availability is series-specific; exact "
                                "underlying publisher release time remains null "
                                "unless separately proven"),
    "rights_status": "FRED_terms_and_underlying_publisher_rights_control",
    "secret_env": "FRED_API_KEY",
    "secret_required": True,
    "series": {"label": "Smoothed U.S. Recession Probabilities",
               "series_id": "RECPROUSM156N", "unit": "Percent"},
    "source_id": "fred_recprousm156n_api_current_offline",
    "value_status": "actual",
    "_cache": "fred_current_api.body",
    "_url": ("https://api.stlouisfed.org/fred/series/observations?"
             "series_id=RECPROUSM156N&file_type=json&"
             "observation_start=1967-06-01&api_key=<KEY>"),
}

CENSUS = {
    "adapter": "census_api",
    "allowed_hosts": ["api.census.gov"],
    "archival": True,
    "coverage_source_ids": ["census_mtis_mwts"],
    "enabled": False,
    "endpoint": ("https://api.census.gov/data/timeseries/eits/mwtsadv?"
                 "get=cell_value,category_code,data_type_code,seasonally_adj,"
                 "geo_level_code,time_slot_id&time=from+1992"),
    "expected_content_types": ["application/json"],
    "frequency": "monthly",
    "information_set_mode": "current_revised",
    "label": ("Census Advance Monthly Wholesale Trade (MWTSADV) EITS timeseries "
              "(keyed Census API, current vintage) [OFFLINE-CURRENT frozen "
              "snapshot; B-RESV-PROVEN; distinct from MWTS; " + BAR + "]"),
    "max_bytes": 16000000,
    "method_version": "census_eits_mwtsadv_current_offline.v1",
    "poll_seconds": 3600,
    "publisher": "U.S. Census Bureau economic indicators (EITS)",
    "publisher_release_clock": ("Census EITS release schedule is series-specific; "
                                "exact underlying release time remains null unless "
                                "separately proven"),
    "rights_status": "government_data_with_API_terms",
    "secret_env": "CENSUS_API_KEY",
    "secret_required": True,
    "series": {"dataset": "mwtsadv",
               "items": [{"series_id": s} for s in ROSTER],
               "unit": "index_or_count"},
    "source_id": "census_eits_mwtsadv_current_offline",
    "value_status": "actual",
    "_cache": "census_economic_indicators_current_api.body",
    "_url": ("https://api.census.gov/data/timeseries/eits/mwtsadv?"
             "get=cell_value,category_code,data_type_code,seasonally_adj,"
             "geo_level_code,time_slot_id&time=from+1992&key=<KEY>"),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    cfg = load_config(CFG_PATH)
    existing_ids = {s["source_id"] for s in cfg["sources"]}
    pipeline = RefreshPipeline(ROOT, cfg)
    pipeline.store.initialize()
    _snap0 = pipeline.build_snapshot(ATT)
    landed_series = feed_factory._collect_series_ids(_snap0)

    bound = []
    for spec in (FRED, CENSUS):
        src = {k: v for k, v in spec.items() if not k.startswith("_")}
        if src["source_id"] in existing_ids:
            raise SystemExit("COLLISION source_id %s" % src["source_id"])
        # net-new series guard
        want = feed_factory._collect_series_ids({"s": src["series"]})
        clash = want & landed_series
        if clash:
            raise SystemExit("COLLISION series %r" % sorted(clash)[:8])
        feed_factory._validate_source_candidate(ROOT, cfg, src)
        body, manifest = _manifest(CACHE / spec["_cache"], spec["_url"])
        from rmv2_live.adapters import normalize
        recs = normalize(src, body, AS_OF)
        periods = sorted(r["observation_period"] for r in recs
                         if r.get("observation_period"))
        info = {"source_id": src["source_id"], "records": len(recs),
                "series": len(feed_factory._collect_series_ids({"s": src["series"]})),
                "obs_min": periods[0], "obs_max": periods[-1],
                "bytes": manifest["source_bytes_length"]}
        if a.dry:
            bound.append(info)
            print("DRY", info)
            continue
        oc = bind_offline_current(pipeline, src, body, manifest, AS_OF)
        cfg["sources"].append(src)
        existing_ids.add(src["source_id"])
        info["receipt_sha12"] = oc["receipt_sha256"][:12]
        info["latest"] = oc["latest_observation_period"]
        bound.append(info)
        print("BOUND", info)

    if a.dry:
        json.dump(bound, open("research/BRESV_plan.json", "w"), indent=1)
        print("DRY complete, no writes")
        return

    raw = json.load(open(CFG_PATH))
    raw["sources"] = cfg["sources"]
    tmp = str(CFG_PATH) + ".tmp"
    json.dump(raw, open(tmp, "w"), indent=1, sort_keys=True)
    os.replace(tmp, CFG_PATH)
    print("CONFIG written; n_sources", len(raw["sources"]))
    snap = pipeline.build_snapshot(ATT)
    cov = pipeline.build_coverage(ATT)
    st = pipeline.build_status(ATT, [], snap, cov)
    ptr = pipeline.store.publish_generation(snap, st, cov)
    print("PUBLISHED", ptr.get("generation_sha256"))
    json.dump({"bound": bound, "pointer_generation": ptr.get("generation_sha256")},
              open("research/BRESV_land_out.json", "w"), indent=1)


main()
