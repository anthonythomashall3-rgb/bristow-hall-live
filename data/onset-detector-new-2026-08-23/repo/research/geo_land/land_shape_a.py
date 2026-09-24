"""B-REG-GEO — land the THREE shape-A geo cross-section files as offline-current
archival sources via the ONE new `geo_panel_json` parser shape (§6.1).

Files (CH-R101 measurement of record, md5-pinned): metro_econ, state_econ,
county_econ. Each lands as its OWN source id (§3.1 no aliasing; geo ids stay
explicit). information_set_mode=current_revised (owner policy 2026-08-08:
CLOCK_UNRESOLVED no longer blocks admission; the source records the as-of BAR).
enabled:false + archival:true (frozen offline snapshot; the resident service
must never fetch it). ZERO network. Bytes ARE the source object (sha-manifested).

Provenance: these are predecessor-derived cross-section aggregations held in the
repo (data/<f>.json, byte-identical to data_archive/derived_original/<f>.json).
coverage_source_ids lists every registered publisher FAMILY the file draws on.
metric->publisher is recorded per metric in `series.metrics[*].publisher_family`.
Any metric whose publisher has NO registered family (phci = Philadelphia Fed
state coincident index) is landed but its family gap is recorded in the note and
it is omitted from coverage_source_ids (the family gate requires listed families
to be a subset of the registry, not completeness).

Run:  python3 research/geo_land/land_shape_a.py --dry           # measure, no writes
      python3 research/geo_land/land_shape_a.py --only <sid>    # land ONE
      python3 research/geo_land/land_shape_a.py                 # land all three
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
    "CLOCK_UNRESOLVED: no provable vintage lane (CH-R101 measured zero dated "
    "vintage evidence). Lands current_revised and is BARRED from backing any "
    "as-of / real-time / replay / Watch / index input (owner ruling 2026-08-08)."
)

# md5 (first 8) pins from CH-R101.v1.json — byte identity check (§5.1).
MD5_PIN = {
    "metro_econ": "84d84d0b",
    "state_econ": "c1a5c694",
    "county_econ": "8a5db144",
}

FILES = {
    "geo_metro_econ_current": {
        "file": "metro_econ",
        "container_key": "metros",
        "id_prefix": "GEO_METRO_ECON",
        "endpoint": "https://www.fhfa.gov/hpi",
        "allowed_hosts": ["www.fhfa.gov"],
        "coverage_source_ids": ["fhfa_hpi", "bea_regional"],
        "publisher": "FHFA / BEA (predecessor-derived metro cross-section)",
        "label": (
            "Biggest-city metro cross-section: FHFA house price index (quarterly)"
            " + BEA real GDP by metro (annual). Predecessor-derived local "
            "snapshot, byte-preserved; current_revised, offline-current archival."
        ),
        "metrics": {
            "hpi": {"offset_key": "q0", "freq": "q",
                    "unit": "FHFA all-transactions house price index (metro; index)",
                    "publisher_family": "fhfa_hpi"},
            "gdp": {"offset_key": "y0", "freq": "a",
                    "unit": "Real GDP by metropolitan area (BEA; chained dollars, millions)",
                    "publisher_family": "bea_regional"},
        },
        "skip_scalar_keys": ["cbsa"],
        "note": AS_OF_BAR,
    },
    "geo_state_econ_current": {
        "file": "state_econ",
        "container_key": "states",
        "id_prefix": "GEO_STATE_ECON",
        "endpoint": "https://www.bls.gov/lau/",
        "allowed_hosts": ["www.bls.gov"],
        "coverage_source_ids": [
            "bls_laus", "bea_regional", "census_saipe", "census_acs",
            "census_construction",
        ],
        "publisher": "BLS / BEA / Census / Philadelphia Fed (predecessor-derived state cross-section)",
        "label": (
            "State detail cross-section (BLS labor force, BEA GDP/income/pop, "
            "Census permits/SAIPE, Philadelphia Fed coincident index). "
            "CONTEXT layer per file note. Predecessor-derived local snapshot, "
            "byte-preserved; current_revised, offline-current archival."
        ),
        "metrics": {
            "lf": {"offset_key": "m0", "freq": "m",
                   "unit": "Civilian labor force (BLS LAUS; persons)",
                   "publisher_family": "bls_laus"},
            "nqgsp": {"offset_key": "q0", "freq": "q",
                      "unit": "Nominal state GDP (BEA; millions USD)",
                      "publisher_family": "bea_regional"},
            "rgsp": {"offset_key": "y0", "freq": "a",
                     "unit": "Real state GDP (BEA; chained dollars, millions)",
                     "publisher_family": "bea_regional"},
            "pcpi": {"offset_key": "y0", "freq": "a",
                     "unit": "Per-capita personal income (BEA; USD)",
                     "publisher_family": "bea_regional"},
            "pop": {"offset_key": "y0", "freq": "a",
                    "unit": "Resident population (Census; thousands)",
                    "publisher_family": "census_acs"},
            "mhi": {"offset_key": "y0", "freq": "a",
                    "unit": "Median household income (Census SAIPE; USD)",
                    "publisher_family": "census_saipe"},
            "poverty": {"offset_key": "y0", "freq": "a",
                        "unit": "Poverty rate (Census SAIPE; percent)",
                        "publisher_family": "census_saipe"},
            "bp": {"offset_key": "m0", "freq": "m",
                   "unit": "Private housing units authorized by building permits (Census; SAAR)",
                   "publisher_family": "census_construction"},
            "phci": {"offset_key": "m0", "freq": "m",
                     "unit": "State coincident index (Philadelphia Fed; index)",
                     "publisher_family": None},
        },
        "skip_scalar_keys": [],
        "note": (
            AS_OF_BAR + " FAMILY-ATTRIBUTION GAP: phci (Philadelphia Fed state "
            "coincident index) has no registered publisher family; it is landed "
            "but omitted from coverage_source_ids (recorded gap, §3.5). File's "
            "own note flags it CONTEXT, not a composite input."
        ),
    },
    "geo_county_econ_current": {
        "file": "county_econ",
        "container_key": "data",
        "id_prefix": "GEO_COUNTY_ECON",
        "endpoint": "https://www.census.gov/programs-surveys/saipe.html",
        "allowed_hosts": ["www.census.gov"],
        "coverage_source_ids": ["fhfa_hpi", "bea_regional", "census_saipe"],
        "publisher": "FHFA / BEA / Census SAIPE (predecessor-derived county cross-section)",
        "label": (
            "County cross-section (FHFA HPI, BEA per-capita income + real GDP, "
            "Census SAIPE median income + poverty), annual. Predecessor-derived "
            "local snapshot, byte-preserved; current_revised, offline-current "
            "archival. STORED depth is a shallow recent window (CH-R101 §5.1)."
        ),
        "metrics": {
            "hpi": {"offset_key": "y0", "freq": "a",
                    "unit": "FHFA county house price index (annual; index)",
                    "publisher_family": "fhfa_hpi"},
            "pcpi": {"offset_key": "y0", "freq": "a",
                     "unit": "Per-capita personal income (BEA; county; USD)",
                     "publisher_family": "bea_regional"},
            "gdp": {"offset_key": "y0", "freq": "a",
                    "unit": "Real GDP by county (BEA; chained dollars, thousands)",
                    "publisher_family": "bea_regional"},
            "mhi": {"offset_key": "y0", "freq": "a",
                    "unit": "Median household income (Census SAIPE; county; USD)",
                    "publisher_family": "census_saipe"},
            "poverty": {"offset_key": "y0", "freq": "a",
                        "unit": "Poverty rate (Census SAIPE; county; percent)",
                        "publisher_family": "census_saipe"},
        },
        "skip_scalar_keys": [],
        "note": (
            AS_OF_BAR + " CH-R101 §5.1 BYTE-VS-DOC: the file note claims hpi "
            "since 1975 / pcpi 1969 / gdp 2001, but STORED bytes are a shallow "
            "recent window (earliest hpi 2007, pcpi/gdp 2010). Landed depth is "
            "the STORED depth, not the source-series depth."
        ),
    },
}


def _cache_and_manifest(fname):
    path = DATA / (fname + ".json")
    body = path.read_bytes()
    md5 = hashlib.md5(body).hexdigest()
    if not md5.startswith(MD5_PIN[fname]):
        raise SystemExit("MD5 MISMATCH %s: %s vs pin %s" % (fname, md5, MD5_PIN[fname]))
    mtime = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    manifest = {
        "url": "local:data/%s.json (predecessor-derived; byte-identical to "
               "data_archive/derived_original/%s.json)" % (fname, fname),
        "fetch_utc": mtime,
        "source_sha256": hashlib.sha256(body).hexdigest(),
        "source_bytes_length": len(body),
    }
    return body, manifest


def _source(sid, spec):
    return {
        "adapter": "geo_panel_json",
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
        "method_version": "geo_panel_offline.v1",
        "poll_seconds": 86400,
        "publisher": spec["publisher"],
        "publisher_release_clock": (
            "no live release clock; frozen predecessor-derived offline snapshot"
        ),
        "rights_status": "public_government_data_with_attribution",
        "secret_env": None,
        "secret_required": False,
        "series": {
            "container_key": spec["container_key"],
            "id_prefix": spec["id_prefix"],
            "skip_scalar_keys": spec["skip_scalar_keys"],
            "metrics": spec["metrics"],
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
        feed_factory._validate_source_candidate(ROOT, cfg, src)  # gate BEFORE write
        recs = normalize(src, body, AS_OF)
        by_series = {}
        for r in recs:
            by_series[r["series_id"]] = by_series.get(r["series_id"], 0) + 1
        lo, hi = _span(recs)
        info = {
            "file": spec["file"],
            "sha256": manifest["source_sha256"],
            "bytes": manifest["source_bytes_length"],
            "records": len(recs),
            "series": len(by_series),
            "period_span": [lo, hi],
            "coverage_source_ids": spec["coverage_source_ids"],
        }
        plan["sources"][sid] = info
        print("GATE PASS %s records=%d series=%d span=%s..%s"
              % (sid, len(recs), len(by_series), lo, hi))

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
        out = ROOT / "research/geo_land/plan_shape_a.json"
        json.dump(plan, open(out, "w"), indent=1)
        print("DRY plan ->", out)
        return

    # single targeted zero-network refresh republishes the generation binding
    # the new archival heads AND writes operational_status (B-LAND-3D gotcha).
    landed = list(plan["sources"])
    if landed:
        cfg2 = load_config(CFG_PATH)
        pipe2 = RefreshPipeline(ROOT, cfg2)
        result = pipe2.refresh(source_ids=landed, due_only=False)
        outcomes = result.get("outcomes") if isinstance(result, dict) else None
        pointer = result.get("pointer") if isinstance(result, dict) else None
        print("TARGETED REFRESH outcomes:", json.dumps(outcomes))
        print("POINTER generation:", (pointer or {}).get("generation_sha256", "<none>"))
        json.dump(
            {"plan": plan, "refresh": {"outcomes": outcomes, "pointer": pointer}},
            open(ROOT / "research/geo_land/land_out_shape_a.json", "w"),
            indent=1, default=str,
        )


main()
