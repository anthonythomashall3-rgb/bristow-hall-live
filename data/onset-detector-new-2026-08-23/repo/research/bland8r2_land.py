"""B-LAND-8-R3 — land the 21 SPF INDIVIDUAL-FORECASTER panels as FORECAST-class
offline-current EVIDENCE lanes (one source per cached individual_*.xlsx), via the
generic offline-current binder and the new ``spf_individual`` forecast_shape.

Authority: B-LAND-8's brief sanctioned this split (items 1-2 committed 2b0aa2d;
item 3 = these panels, deferred pending the panel-model shape). CH-R49 identity
gate RESOLVED: research/spf_identity_preflight_v1.json identity_finding.verdict =
ANONYMOUS_ID_ONLY — forecasters are anonymous integer IDs, no human names.

FORECAST FIREWALL (CLAUDE.md): forecasts of MEASUREMENTS are eligible LABELED
substituted_diagnostic inputs AND comparators; never a construction input
unadmitted, never aliased to a modern twin. Bound to the registered forecast
family ``philadelphia_spf`` (role forecast_comparator, access B).

Zero network. The cache xlsx bytes ARE the source object (sha-manifested from
CH-R35 / B-LAND-8), normalized through ``forecast_xlsx`` spf_individual (in-memory
core.xml repair; ORIGINAL bytes bound). enabled:false + archival:true (frozen
forecast-track snapshot). Converge via ONE TARGETED zero-network refresh of the
newly-bound DISABLED source_ids only (never a full pipeline.refresh — the
B-OFFLINE-2 incident), which republishes the generation AND writes
operational_status in the same step (the B-LAND-3D gotcha).
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
CACHE = ROOT / "research/prefetch/forecasts"
AS_OF = "2026-08-06T10:00:00Z"
FAMILY = "philadelphia_spf"
SPF_PAGE = ("https://www.philadelphiafed.org/surveys-and-data/real-time-data-"
            "research/survey-of-professional-forecasters")

FIREWALL = (
    "FORECAST class: individual-forecaster point forecasts of MEASUREMENTS -> "
    "eligible LABELED substituted_diagnostic input AND comparator; NOT an NBER "
    "recession-LABEL product; anonymous integer forecaster IDs only (CH-R49 "
    "ANONYMOUS_ID_ONLY). Never a construction input unadmitted, never aliased. "
    "family philadelphia_spf. B-LAND-8-R2."
)


def _manifest_index(subdir, manifest_name="MANIFEST.sha256.json"):
    man = json.load(open(CACHE / subdir / manifest_name))
    idx = {}
    for f in man["files"]:
        idx[f["path"].split("/")[-1]] = f
    return man.get("generated_utc"), idx


def _cache_manifest(subdir, filename, gen_utc, idx, url):
    path = CACHE / subdir / filename
    body = path.read_bytes()
    sha = hashlib.sha256(body).hexdigest()
    row = idx.get(filename)
    if row is None:
        raise SystemExit("NO MANIFEST ROW for %s/%s" % (subdir, filename))
    if sha != row["sha256"] or len(body) != row["bytes"]:
        raise SystemExit("CACHE MISMATCH %s: sha/len vs manifest" % filename)
    manifest = {
        "fetch_utc": gen_utc,
        "source_bytes_length": len(body),
        "source_sha256": sha,
        "url": url,
    }
    return body, manifest


def _detect_sheet(body):
    from rmv2_live.forecast_xlsx import repair_core_xml_bytes
    import openpyxl
    wb = openpyxl.load_workbook(repair_core_xml_bytes(body), read_only=True)
    try:
        return wb.sheetnames[0]
    finally:
        wb.close()


def _individual_source(filename, sheet):
    varcode = sheet.strip().upper()
    stem = filename[:-5]  # drop .xlsx  -> individual_corecpi
    return {
        "adapter": "forecast_xlsx",
        "allowed_hosts": ["www.philadelphiafed.org"],
        "archival": True,
        "coverage_source_ids": [FAMILY],
        "enabled": False,
        "endpoint": "%s#%s" % (SPF_PAGE, filename),
        "expected_content_types": [
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/octet-stream",
        ],
        "frequency": "quarterly",
        "information_set_mode": "substituted_diagnostic",
        "label": (
            "SPF individual-forecaster panel %s (%s) [OFFLINE-CURRENT frozen "
            "forecast snapshot; CH-R35 cache; %s]" % (varcode, filename, FIREWALL)
        ),
        "max_bytes": 33554432,
        "method_version": "spf_individual_forecast_offline.v1",
        "poll_seconds": 86400,
        "publisher": "Federal Reserve Bank of Philadelphia",
        "publisher_release_clock": (
            "quarterly named survey vintage (individual responses release edition);"
            " exact media download URL not captured by CH-R35"
        ),
        "rights_status": "published_survey_data",
        "secret_env": None,
        "secret_required": False,
        "snapshot_projection": "archival_panel.v1",
        "series": {
            "forecast_shape": "spf_individual",
            "sheet": sheet,
            "spf_target_code": varcode,
            "id_prefix": "SPF_",
            "unit": "SPF individual-forecaster point forecast (units per varcode)",
            "label": "SPF individual %s panel. %s" % (varcode, FIREWALL),
        },
        "source_id": "philadelphia_spf_%s" % stem,
        "value_status": "actual",
    }


def build_plan():
    gen_spf, idx_spf = _manifest_index("spf")
    files = sorted(f for f in os.listdir(CACHE / "spf")
                   if f.startswith("individual_") and f.endswith(".xlsx"))
    plan = []  # (src, body, manifest)
    for filename in files:
        body, man = _cache_manifest("spf", filename, gen_spf, idx_spf,
                                    "%s#%s" % (SPF_PAGE, filename))
        sheet = _detect_sheet(body)
        plan.append((_individual_source(filename, sheet), body, man))
    return plan


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()

    plan = build_plan()
    cfg = load_config(CFG_PATH)
    existing = {s["source_id"] for s in cfg["sources"]}
    for src, _b, _m in plan:
        if src["source_id"] in existing:
            raise SystemExit("COLLISION: %s already in config" % src["source_id"])

    pipeline = RefreshPipeline(ROOT, cfg)
    pipeline.store.initialize()

    running = dict(cfg)
    running["sources"] = list(cfg["sources"])
    report = {}
    all_series = set()
    for src, body, _m in plan:
        feed_factory._validate_source_candidate(ROOT, running, src)
        recs = normalize(src, body, AS_OF)
        avail = sum(1 for r in recs if r.get("value_status") != "unavailable")
        sids = sorted(set(r["series_id"] for r in recs))
        dup = all_series.intersection(sids)
        if dup:
            raise SystemExit("SERIES COLLISION across files: %r" % sorted(dup))
        all_series.update(sids)
        periods = [r["observation_period"] for r in recs if r["observation_period"]]
        report[src["source_id"]] = {
            "records": len(recs), "available": avail, "n_series": len(sids),
            "first": min(periods), "last": max(periods),
        }
        running["sources"] = list(running["sources"]) + [src]
    print("GATE PASS all %d sources, %d distinct series." % (len(plan), len(all_series)))
    print("total records:", sum(v["records"] for v in report.values()))

    if a.dry:
        json.dump({"report": report, "n_series": len(all_series),
                   "total_records": sum(v["records"] for v in report.values())},
                  open("research/BLAND8R2_land_plan.json", "w"), indent=1,
                  sort_keys=True)
        print("DRY: gated + parsed, no writes.")
        return

    bound = {}
    for src, body, manifest in plan:
        oc = bind_offline_current(pipeline, src, body, manifest, AS_OF)
        bound[src["source_id"]] = {
            "records": oc["record_count"], "receipt": oc["receipt_sha256"],
            "latest": oc["latest_observation_period"],
        }
        print("BOUND", src["source_id"], oc["record_count"], oc["receipt_sha256"][:12])

    raw = json.load(open(CFG_PATH))
    raw["sources"] = list(raw["sources"]) + [src for src, _b, _m in plan]
    tmp = str(CFG_PATH) + ".tmp"
    json.dump(raw, open(tmp, "w"), indent=1, sort_keys=True)
    os.replace(tmp, CFG_PATH)
    print("CONFIG written; n_sources", len(raw["sources"]),
          "archival", sum(1 for s in raw["sources"] if s.get("archival")))

    ids = [src["source_id"] for src, _b, _m in plan]
    cfg2 = load_config(CFG_PATH)
    pipe2 = RefreshPipeline(ROOT, cfg2)
    result = pipe2.refresh(source_ids=ids, due_only=False)
    outcomes = result.get("outcomes") if isinstance(result, dict) else None
    pointer = result.get("pointer") if isinstance(result, dict) else None
    print("TARGETED REFRESH outcomes:", json.dumps(outcomes))
    print("POINTER generation:", (pointer or {}).get("generation_sha256", "<none>"))
    json.dump({"bound": bound, "report": report,
               "refresh": {"outcomes": outcomes, "pointer": pointer},
               "n_series": len(all_series)},
              open("research/BLAND8R2_land_out.json", "w"), indent=1, default=str,
              sort_keys=True)


if __name__ == "__main__":
    main()
