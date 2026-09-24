"""B-LAND-7 — land the Atlanta Fed GDPNow nowcast track-record as a FORECAST-class
CURRENT-value offline lane via the generic offline-current binder (B-OFFLINE-2 infra).

Authority: B-LAND-7_FORECAST_ARCHIVES.md (priority item 2) + CH-R34 survey
(research/forecast_sources_survey_v1.csv: atlanta_gdpnow route FRED:GDPNOW clean 200,
public Fed, comparator+input-candidate, MEASUREMENT firewall class).

FORECAST FIREWALL: GDPNow is a forecast (nowcast) of a MEASUREMENT (current-quarter real
GDP growth) -> eligible as a LABELED substituted_diagnostic input; it is NOT a recession-
LABEL product. The firewall + forecast identity is carried in the source label and bound
to the registry forecast family `atlanta_gdpnow` (role forecast_comparator, access_class B),
NEVER to a measurement provider family.

Offline, zero-network: the CH-R37 prefetch cache bytes ARE the source object, normalized
through the proven live parse_fred_json_api (current lane). enabled:false + archival:true
(a frozen forecast-track snapshot). Reuses the B-OFFLINE-2 land_fred contract verbatim.
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
CACHE = ROOT / "research/prefetch/forecasts/gdpnow"
AS_OF = "2026-08-06T00:00:00Z"
ATT = "2026-08-06T05:00:00Z"

SERIES_ID = "GDPNOW"
SOURCE_ID = "gdpnow_atlanta_fred_forecast_current_offline"
FORECAST_FAMILY = "atlanta_gdpnow"
FETCH_UTC = "2026-08-04T00:00:00Z"  # FRED realtime_start of the cached observations


def build_source():
    return {
        "adapter": "fred_json_api",
        "allowed_hosts": ["api.stlouisfed.org"],
        "archival": True,
        "coverage_source_ids": [FORECAST_FAMILY],
        "enabled": False,
        "endpoint": (
            "https://api.stlouisfed.org/fred/series/observations?series_id=%s"
            "&file_type=json" % SERIES_ID
        ),
        "expected_content_types": ["application/json"],
        "frequency": "quarterly",
        "information_set_mode": "current_revised",
        "label": (
            "Atlanta Fed GDPNow nowcast track record (current-quarter real GDP "
            "growth, via FRED GDPNOW) [FORECAST class: nowcast of a MEASUREMENT "
            "-> eligible LABELED substituted_diagnostic input, comparator; NOT a "
            "recession-LABEL product] [OFFLINE-CURRENT frozen snapshot; CH-R37 "
            "cache; family atlanta_gdpnow]"
        ),
        "max_bytes": 33554432,
        "method_version": "gdpnow_fred_json_api_forecast_current_offline.v1",
        "poll_seconds": 3600,
        "publisher": "Federal Reserve Bank of Atlanta (via FRED provider)",
        "publisher_release_clock": (
            "GDPNow updates ~6-7 times per month after inputs; the FRED GDPNOW "
            "series carries one value per target quarter; exact publisher release "
            "time remains null unless separately proven"
        ),
        "rights_status": "FRED_terms_and_Atlanta_Fed_published_output_rights_control",
        "secret_env": "FRED_API_KEY",
        "secret_required": True,
        "series": {
            "label": "Atlanta Fed GDPNow (current-quarter real GDP growth nowcast)",
            "series_id": SERIES_ID,
            "unit": "Percent",
        },
        "source_id": SOURCE_ID,
        "value_status": "actual",
    }


def load_cache():
    body = (CACHE / "GDPNOW.observations.json").read_bytes()
    sha = hashlib.sha256(body).hexdigest()
    man = json.load(open(CACHE / "MANIFEST.sha256.json"))
    row = [f for f in man["files"] if f["path"] == "GDPNOW.observations.json"][0]
    if sha != row["sha256"] or len(body) != row["bytes"]:
        raise SystemExit("CACHE MISMATCH: sha/len vs manifest")
    manifest = {
        "fetch_utc": FETCH_UTC,
        "source_bytes_length": len(body),
        "source_sha256": sha,
        "url": (
            "https://api.stlouisfed.org/fred/series/observations?"
            "series_id=%s&file_type=json" % SERIES_ID
        ),
    }
    return body, manifest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()

    cfg = load_config(CFG_PATH)
    existing_ids = {s["source_id"] for s in cfg["sources"]}
    if SOURCE_ID in existing_ids:
        raise SystemExit("COLLISION: %s already in config" % SOURCE_ID)

    pipeline = RefreshPipeline(ROOT, cfg)
    pipeline.store.initialize()

    src = build_source()
    # append-only family + registry-binding gate BEFORE any write (also proves
    # GDPNOW series id is absent from the active generation).
    feed_factory._validate_source_candidate(ROOT, cfg, src)
    body, manifest = load_cache()

    if a.dry:
        from rmv2_live.adapters import normalize
        recs = normalize(src, body, AS_OF)
        periods = sorted(r["observation_period"] for r in recs
                         if r["observation_period"])
        out = {
            "source_id": SOURCE_ID, "series_id": SERIES_ID,
            "records": len(recs), "obs_min": periods[0], "obs_max": periods[-1],
            "bytes": manifest["source_bytes_length"], "family": FORECAST_FAMILY,
        }
        json.dump(out, open("research/BLAND7_gdpnow_plan.json", "w"), indent=1)
        print("DRY:", json.dumps(out))
        return

    oc = bind_offline_current(pipeline, src, body, manifest, AS_OF)
    cfg["sources"].append(src)

    raw = json.load(open(CFG_PATH))
    raw["sources"] = cfg["sources"]
    tmp = str(CFG_PATH) + ".tmp"
    json.dump(raw, open(tmp, "w"), indent=1, sort_keys=True)
    os.replace(tmp, CFG_PATH)

    snap = pipeline.build_snapshot(ATT)
    cov = pipeline.build_coverage(ATT)
    st = pipeline.build_status(ATT, [], snap, cov)
    ptr = pipeline.store.publish_generation(snap, st, cov)
    out = {
        "source_id": SOURCE_ID, "series_id": SERIES_ID,
        "records": oc["record_count"],
        "latest": oc["latest_observation_period"],
        "receipt_sha256": oc["receipt_sha256"],
        "generation_sha256": ptr.get("generation_sha256"),
        "n_sources": len(raw["sources"]),
    }
    json.dump({"bound": out, "pointer": ptr},
              open("research/BLAND7_gdpnow_land_out.json", "w"), indent=1)
    print("PUBLISHED", json.dumps(out))


if __name__ == "__main__":
    main()
