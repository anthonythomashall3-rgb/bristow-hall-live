"""B-REG-GEO — land the THREE explicit-axis geo files via the ONE new
`geo_grid_json` parser shape (§6.1): state_metrics, county_hist, county_industry.

Same landing contract as land_shape_a.py: own source id (§3.1, no aliasing),
current_revised + as-of BAR recorded (owner policy 2026-08-08), enabled:false +
archival:true, ZERO network, bytes ARE the source object (sha-manifested).

HONESTY (§5.1/§19.4):
- state_metrics VALUES ARE PREDECESSOR-DERIVED z-score transforms, NOT raw
  observations. Recorded in every unit string and the source note. It is landed
  as ACQUISITION only (§22.1 derive nothing); it is NOT admitted as a composite.
- county_hist last monthly key (2026-05) is PRELIMINARY per the file; recorded.
- state_metrics phci draws on the Philadelphia Fed state coincident index, which
  has no registered publisher family; omitted from coverage_source_ids (gap
  recorded, §3.5).

Run:  python3 research/geo_land/land_grid.py --dry
      python3 research/geo_land/land_grid.py --only <sid>
      python3 research/geo_land/land_grid.py
"""
import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(".").resolve()
sys.path.insert(0, str(ROOT / "live_data"))
from rmv2_live.config import load_config
from rmv2_live.pipeline import RefreshPipeline
from rmv2_live import feed_factory
from rmv2_live.adapters import normalize
from rmv2_live.offline_binding import bind_offline_current

CFG_PATH = ROOT / "live_data/config/sources.v1.json"
DATA = ROOT / "data"
AS_OF = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

AS_OF_BAR = (
    "CLOCK_UNRESOLVED: no provable vintage lane (CH-R101). Lands current_revised "
    "and is BARRED from backing any as-of / real-time / replay / Watch / index "
    "input (owner ruling 2026-08-08)."
)

MD5_PIN = {
    "state_metrics": "b1cf1f65",
    "county_hist": "61a71d8d",
    "county_industry": "6694bd75",
}

_Z = "(predecessor-derived z-score transform; NOT raw observation)"
STATE_METRICS = {
    "iclaims": "z initial unemployment claims, yoy change " + _Z,
    "insuredur": "z insured unemployment rate, yoy change " + _Z,
    "sahm": "z state Sahm indicator, 3mo-avg UR minus 12mo low " + _Z,
    "urv": "z unemployment rate, rise from trailing 120-day low " + _Z,
    "phci": "z Philadelphia Fed state coincident index, 6mo decline " + _Z,
    "payrolls": "z nonfarm payrolls, yoy change inverted " + _Z,
    "mfg": "z manufacturing employment, yoy change inverted " + _Z,
    "permits": "z building permits, yoy change inverted " + _Z,
    "hpi": "z FHFA house prices, yoy change inverted, quarterly " + _Z,
    "rincome": "z real personal income, CPI-deflated yoy inverted, quarterly " + _Z,
}
QCEW_SECTORS = {
    "1011": "Mining & logging", "1012": "Construction", "1013": "Manufacturing",
    "1021": "Trade, transportation & utilities", "1022": "Information",
    "1023": "Financial activities", "1024": "Professional & business services",
    "1025": "Education & health services", "1026": "Leisure & hospitality",
    "1027": "Other services",
}

FILES = {
    "geo_state_metrics_current": {
        "file": "state_metrics",
        "id_prefix": "GEO_STATE_METRICS",
        "endpoint": "https://www.bls.gov/lau/",
        "allowed_hosts": ["www.bls.gov"],
        "coverage_source_ids": [
            "bls_laus", "bls_ces", "fhfa_hpi", "bea_regional", "census_construction",
        ],
        "publisher": "Predecessor-derived state pressure composite (BLS/BEA/Census/Philadelphia Fed inputs)",
        "label": (
            "State pressure composite (50 states; 10 z-scored channel metrics, "
            "monthly 1976-. PREDECESSOR-DERIVED TRANSFORMS, not raw. Landed as "
            "acquisition only; NOT admitted as a V2 composite. current_revised, "
            "offline-current archival."
        ),
        "blocks": [{
            "axis_key": "months", "container_key": "states", "metric_level": True,
            "metrics": {k: {"unit": v} for k, v in STATE_METRICS.items()},
        }],
        "note": (
            AS_OF_BAR + " VALUES ARE PREDECESSOR-DERIVED z-score transforms, not "
            "raw observations (§5.1). phci has no registered publisher family; "
            "omitted from coverage_source_ids (gap recorded, §3.5)."
        ),
    },
    "geo_county_hist_current": {
        "file": "county_hist",
        "id_prefix": "GEO_COUNTY_HIST",
        "endpoint": "https://www.bls.gov/lau/",
        "allowed_hosts": ["www.bls.gov"],
        "coverage_source_ids": ["bls_laus"],
        "publisher": "BLS Local Area Unemployment Statistics (predecessor-derived county cross-section)",
        "label": (
            "County BLS LAUS: unemployment rate x10 annual 1990-2025 (3144 "
            "counties) + 14 current monthly + monthly labor force. "
            "Predecessor-derived local snapshot; current_revised, archival."
        ),
        "blocks": [
            {"axis_key": "years", "container_key": "annual", "metric_level": False,
             "metric_suffix": "ur", "unit": "BLS LAUS unemployment rate x10, annual county average (rate x10)"},
            {"axis_key": "mkeys", "container_key": "monthly", "metric_level": False,
             "metric_suffix": "ur_m", "unit": "BLS LAUS unemployment rate x10, monthly (rate x10; final month preliminary)"},
            {"axis_key": "mkeys", "container_key": "lfm", "metric_level": False,
             "metric_suffix": "lf_m", "unit": "BLS LAUS labor force, monthly (persons; final month preliminary)"},
        ],
        "note": (
            AS_OF_BAR + " The final monthly key (per file 2026-05) is "
            "PRELIMINARY. Legacy county shapes (CT planning-region, "
            "Valdez-Cordova) carried through as-published."
        ),
    },
    "geo_county_industry_current": {
        "file": "county_industry",
        "id_prefix": "GEO_COUNTY_INDUSTRY",
        "endpoint": "https://www.bls.gov/cew/",
        "allowed_hosts": ["www.bls.gov"],
        "coverage_source_ids": ["bls_qcew"],
        "publisher": "BLS Quarterly Census of Employment and Wages (predecessor-derived county cross-section)",
        "label": (
            "County BLS QCEW private employment by 10 NAICS supersectors, annual "
            "2014-2025 (3146 counties). Predecessor-derived local snapshot; "
            "current_revised, offline-current archival."
        ),
        "blocks": [{
            "axis_key": "years", "container_key": "data", "metric_level": True,
            "metrics": {
                code: {"unit": "QCEW private employment: %s (persons)" % name}
                for code, name in QCEW_SECTORS.items()
            },
        }],
        "note": AS_OF_BAR,
    },
}


def _cache_and_manifest(fname):
    path = DATA / (fname + ".json")
    body = path.read_bytes()
    md5 = hashlib.md5(body).hexdigest()
    if not md5.startswith(MD5_PIN[fname]):
        raise SystemExit("MD5 MISMATCH %s: %s vs %s" % (fname, md5, MD5_PIN[fname]))
    mtime = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ")
    return body, {
        "url": "local:data/%s.json (predecessor-derived; byte-identical to "
               "data_archive/derived_original/%s.json)" % (fname, fname),
        "fetch_utc": mtime,
        "source_sha256": hashlib.sha256(body).hexdigest(),
        "source_bytes_length": len(body),
    }


def _source(sid, spec):
    return {
        "adapter": "geo_grid_json",
        "allowed_hosts": spec["allowed_hosts"],
        "archival": True,
        "coverage_source_ids": spec["coverage_source_ids"],
        "enabled": False,
        "endpoint": spec["endpoint"],
        "expected_content_types": ["application/json"],
        "frequency": "mixed",
        "information_set_mode": "current_revised",
        "label": spec["label"],
        "max_bytes": 4000000,
        "method_version": "geo_grid_offline.v1",
        "poll_seconds": 86400,
        "publisher": spec["publisher"],
        "publisher_release_clock": "no live release clock; frozen predecessor-derived offline snapshot",
        "rights_status": "public_government_data_with_attribution",
        "secret_env": None,
        "secret_required": False,
        "series": {
            "id_prefix": spec["id_prefix"],
            "blocks": spec["blocks"],
            "as_of_bar": AS_OF_BAR,
            "note": spec["note"],
        },
        "source_id": sid,
        "value_status": "actual",
    }


def _span(recs):
    ps = sorted(r["observation_period"] for r in recs)
    return (ps[0], ps[-1]) if ps else (None, None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--only", default=None)
    a = ap.parse_args()
    targets = [a.only] if a.only else list(FILES)
    plan = {"as_of": AS_OF, "sources": {}}

    for sid in targets:
        spec = FILES[sid]
        body, manifest = _cache_and_manifest(spec["file"])
        src = _source(sid, spec)
        cfg = load_config(CFG_PATH)
        if sid in {s["source_id"] for s in cfg["sources"]}:
            print("SKIP already active:", sid)
            continue
        pipeline = RefreshPipeline(ROOT, cfg)
        pipeline.store.initialize()
        feed_factory._validate_source_candidate(ROOT, cfg, src)
        recs = normalize(src, body, AS_OF)
        by = {}
        for r in recs:
            by[r["series_id"]] = by.get(r["series_id"], 0) + 1
        lo, hi = _span(recs)
        plan["sources"][sid] = {
            "file": spec["file"], "sha256": manifest["source_sha256"],
            "bytes": manifest["source_bytes_length"], "records": len(recs),
            "series": len(by), "period_span": [lo, hi],
            "coverage_source_ids": spec["coverage_source_ids"],
        }
        print("GATE PASS %s records=%d series=%d span=%s..%s"
              % (sid, len(recs), len(by), lo, hi))
        if a.dry:
            continue
        oc = bind_offline_current(pipeline, src, body, manifest, AS_OF)
        print("  BOUND", oc.get("outcome"), "records", oc.get("record_count"),
              "receipt", oc.get("receipt_sha256", "")[:12])
        raw = json.load(open(CFG_PATH))
        raw["sources"] = list(raw["sources"]) + [src]
        tmp = str(CFG_PATH) + ".tmp"
        json.dump(raw, open(tmp, "w"), indent=1, sort_keys=True)
        os.replace(tmp, CFG_PATH)
        print("  CONFIG appended; n_sources", len(raw["sources"]))

    if a.dry:
        json.dump(plan, open(ROOT / "research/geo_land/plan_grid.json", "w"), indent=1)
        print("DRY plan -> research/geo_land/plan_grid.json")
        return

    landed = list(plan["sources"])
    if landed:
        cfg2 = load_config(CFG_PATH)
        result = RefreshPipeline(ROOT, cfg2).refresh(source_ids=landed, due_only=False)
        outcomes = result.get("outcomes") if isinstance(result, dict) else None
        pointer = result.get("pointer") if isinstance(result, dict) else None
        print("TARGETED REFRESH outcomes:", json.dumps(outcomes))
        print("POINTER generation:", (pointer or {}).get("generation_sha256", "<none>"))
        json.dump({"plan": plan, "refresh": {"outcomes": outcomes, "pointer": pointer}},
                  open(ROOT / "research/geo_land/land_out_grid.json", "w"),
                  indent=1, default=str)


main()
