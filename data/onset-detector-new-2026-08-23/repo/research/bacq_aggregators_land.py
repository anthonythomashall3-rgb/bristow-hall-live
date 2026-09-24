"""B-ACQ-AGGREGATORS (Window 1) — land the DBnomics ISM breadth series as
offline-current aggregator-tier sources via the proven generic offline-current
binder + dbnomics_json adapter.

Authority: B-ACQ-AGGREGATORS.md (gate: AFTER B-ACQ-PUBLISHER-DIRECT COMPLETE —
satisfied by DONE row 'B-ACQ-PUBLISHER-DIRECT 20260809T105644Z COMPLETE').
Prefetch: B-FETCH-AGGREGATORS staged 4 DBnomics/ISM series into
research/_staging/aggregators/dbnomics/ (tier=aggregator, upstream=ISM).

PRECEDENCE FIXED (§3.1): publisher-direct > FRED > aggregator. FRED's national
ISM route is DEAD (metric_catalog NAPM = quarantine html_masquerading_as_csv;
no usable FRED counterpart), so these DBnomics ISM series fill a current_revised
breadth gap no higher-precedence route reaches — they are NOT duplicate lineage.

IDENTITY / §5.6 CROSS-CHECK RESULT — 4 staged, 3 LANDED, 1 REJECTED:
  ISM/neword/in      Manufacturing New Orders  60 obs 2021-01..2025-12  min42.5 max68.0  CLEAN -> land
  ISM/nm-neword/in   Services New Orders        60 obs 2021-01..2025-12  min45.2 max69.0  CLEAN -> land
  ISM/nm-pmi/pm      Services PMI               64 obs 2020-05..2025-08  min45.4 max68.4  CLEAN -> land
  ISM/pmi/pm         Manufacturing PMI headline 68 obs 2020-05..2025-12  tail 2025-09..12 = 11.1/10.0/10.0/10.3
                     while prior month 48.7 -> IMPOSSIBLE for a diffusion index; DBnomics tail
                     CORRUPT. Identity FAILS on its face; batch rule "a NEAR result means the
                     aggregator lane does NOT land" -> REJECTED, not bound. Typed defect filed:
                     blockers/DEFECT__dbnomics_ism_pmi_corrupt_tail__*.json

§22.4 NOT crossed: nothing derived; no channel/member/weight/transform/threshold.
Universe open (§22) -> acquisition breadth only, admitted to NO channel, enabled:false archival.
Rights: DBnomics no-key free acquisition; underlying ISM terms bar RAW republish; owner ruling
20260808 PUBLISH_ALL_GOOD_DATA clears USE. publish_class=internal_only (no raw republish).
"""
import argparse
import csv
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
REGISTRY = ROOT / "data_vault/catalog/external_source_registry.csv"
STAGE = ROOT / "research/_staging/aggregators/dbnomics"
FETCH_UTC = "2026-08-08T18:16:46Z"   # sidecar fetch_utc (staged prefetch)
AS_OF = "2026-08-09T00:00:00Z"

FAMILY_ID = "dbnomics_ism_business_surveys"
RIGHTS = ("ISM_terms_of_use_USE_cleared_no_raw_republish (DBnomics no-key free "
          "acquisition; underlying ISM terms bar raw redistribution; owner ruling "
          "20260808 PUBLISH_ALL_GOOD_DATA clears USE)")
FIREWALL = ("AGGREGATOR TIER (§3.1): DBnomics mirror of ISM, ranks BELOW any "
            "publisher-direct/FRED counterpart; shallow current_revised breadth "
            "only (no vintage/episode-replay); admitted to NO channel, sets no "
            "weight (§22.4). family %s." % FAMILY_ID)

REGISTRY_ROW = {
    "schema_version": "recession-monitor-v2.external-source-registry.v1",
    "source_id": FAMILY_ID,
    "family": "ism_business_surveys",
    "publisher": "Institute for Supply Management (mirrored via DBnomics aggregator, provider ISM)",
    "measure": "ISM manufacturing & non-manufacturing PMI and new-orders diffusion indexes",
    "frequency": "monthly",
    "coverage": ("2020-05+ (DBnomics shallow mirror; ISM full 1948+ history behind ISM "
                 "terms, not on any free route)"),
    "typical_release_or_availability": "first_business_day_of_month_manufacturing_third_business_day_services",
    "revision_and_vintage_behavior": ("DBnomics current mirror; NO vintage lane; ISM annual "
                                      "seasonal re-benchmark restates history (assumption to verify)"),
    "role": "construction_or_diagnostic",
    "access_class": "B",
    "rights_status": RIGHTS,
    "primary_url": "https://db.nomics.world/ISM",
    "notes": ("Aggregator tier (DBnomics, no API key); precedence publisher-direct>FRED>aggregator "
              "(FRED national ISM route dead: NAPM quarantine html_masquerading_as_csv). Landed 3 "
              "shallow current_revised breadth series; DBnomics ISM/pmi/pm MANUFACTURING PMI headline "
              "REJECTED (corrupt tail 11.1/10.0/10.0/10.3 for 2025-09..12 vs prior 48.7); see typed "
              "blocker DEFECT__dbnomics_ism_pmi_corrupt_tail. §22.4 not crossed; enabled:false archival."),
    "publish_class": "internal_only",
}

# (source_id_suffix, dataset_code, series_code, series_id, human, unit, staged_file)
SERIES = [
    ("manufacturing_neworders", "neword", "in", "ISM_MFG_NEWORDERS",
     "ISM Manufacturing New Orders Index", STAGE / "ISM_neword_in.json"),
    ("services_neworders", "nm-neword", "in", "ISM_SVC_NEWORDERS",
     "ISM Non-manufacturing (Services) New Orders Index", STAGE / "ISM_nm-neword_in.json"),
    ("services_pmi", "nm-pmi", "pm", "ISM_SVC_PMI",
     "ISM Non-manufacturing (Services) PMI", STAGE / "ISM_nm-pmi_pm.json"),
]
UNIT = "Diffusion index (>50 = expansion; seasonally adjusted)"


def _source(suffix, dataset_code, series_code, series_id, human):
    sid = "dbnomics_ism_%s_current_offline" % suffix
    url = "https://api.db.nomics.world/v22/series/ISM/%s/%s?observations=true" % (
        dataset_code, series_code)
    member = {
        "series_id": series_id,
        "provider_code": "ISM",
        "dataset_code": dataset_code,
        "series_code": series_code,
        "upstream_publisher": "Institute for Supply Management (ISM)",
        "label": "%s [DBnomics ref ISM/%s/%s]. %s" % (human, dataset_code, series_code, FIREWALL),
    }
    return {
        "adapter": "dbnomics_json",
        "allowed_hosts": ["api.db.nomics.world"],
        "archival": True,
        "coverage_source_ids": [FAMILY_ID],
        "enabled": False,
        "endpoint": url,
        "expected_content_types": ["application/json"],
        "frequency": "monthly",
        "information_set_mode": "current_revised",
        "label": ("%s [OFFLINE-CURRENT frozen DBnomics aggregator snapshot; prefetch %s; %s]"
                  % (human, FETCH_UTC, FIREWALL)),
        "max_bytes": 33554432,
        "method_version": "dbnomics_ism_offline.v1",
        "poll_seconds": 86400,
        "publisher": "Institute for Supply Management (via DBnomics aggregator)",
        "publisher_release_clock": ("DBnomics mirror indexed date; exact ISM release time per "
                                    "reference month not carried by the API payload (unresolved)"),
        "rights_status": RIGHTS,
        "secret_env": None,
        "secret_required": False,
        "series": {"unit": UNIT, "members": [member]},
        "source_id": sid,
        "value_status": "actual",
    }


def _manifest(path):
    body = path.read_bytes()
    return body, {
        "fetch_utc": FETCH_UTC,
        "source_bytes_length": len(body),
        "source_sha256": hashlib.sha256(body).hexdigest(),
        "url": "https://api.db.nomics.world/v22/series/ISM/%s/%s?observations=true",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()

    srcs = [_source(s[0], s[1], s[2], s[3], s[4]) for s in SERIES]
    bodies = {}
    reports = []

    cfg = load_config(CFG_PATH)
    existing = {s["source_id"] for s in cfg["sources"]}
    for src in srcs:
        if src["source_id"] in existing:
            raise SystemExit("COLLISION: %s already in config" % src["source_id"])

    # registry family must exist on disk before validate/bind (family gate reads CSV)
    reg_rows = list(csv.DictReader(open(REGISTRY, newline="")))
    reg_ids = {r["source_id"] for r in reg_rows}
    reg_needs_write = FAMILY_ID not in reg_ids
    if not a.dry and reg_needs_write:
        cols = list(reg_rows[0].keys())
        tmp = str(REGISTRY) + ".tmp"
        with open(tmp, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=cols)
            w.writeheader()
            w.writerows(reg_rows)
            w.writerow({c: REGISTRY_ROW[c] for c in cols})
        os.replace(tmp, REGISTRY)
        print("REGISTRY family appended:", FAMILY_ID, "count", len(reg_rows) + 1)

    pipeline = RefreshPipeline(ROOT, cfg)
    pipeline.store.initialize()
    running = dict(cfg)
    running["sources"] = list(cfg["sources"])

    for src, meta in zip(srcs, SERIES):
        body = meta[5].read_bytes()
        bodies[src["source_id"]] = body
        if not a.dry:
            feed_factory._validate_source_candidate(ROOT, running, src)
        recs = normalize(src, body, AS_OF)
        pers = [r["observation_period"] for r in recs if r["observation_period"]]
        rep = {"source_id": src["source_id"], "series_id": src["series"]["members"][0]["series_id"],
               "records": len(recs), "first": min(pers), "last": max(pers),
               "values_min": min(float(r["value"]) for r in recs),
               "values_max": max(float(r["value"]) for r in recs),
               "sha256": hashlib.sha256(body).hexdigest(), "bytes": len(body)}
        reports.append(rep)
        print("GATE PASS:", json.dumps(rep))

    if a.dry:
        json.dump({"reports": reports, "registry_family": REGISTRY_ROW,
                   "rejected": {"series": "ISM/pmi/pm", "reason": "corrupt tail 11.1/10.0/10.0/10.3"}},
                  open("research/BACQ_AGGREGATORS_land_plan.json", "w"), indent=1, sort_keys=True)
        print("DRY: gated + parsed, no writes.")
        return

    bound = []
    for src in srcs:
        body = bodies[src["source_id"]]
        manifest = {"fetch_utc": FETCH_UTC, "source_bytes_length": len(body),
                    "source_sha256": hashlib.sha256(body).hexdigest(), "url": src["endpoint"]}
        oc = bind_offline_current(pipeline, src, body, manifest, AS_OF)
        print("BOUND", src["source_id"], oc["record_count"], oc["receipt_sha256"][:12],
              "latest", oc["latest_observation_period"])
        bound.append({"source_id": src["source_id"], "records": oc["record_count"],
                      "receipt_sha256": oc["receipt_sha256"], "latest": oc["latest_observation_period"],
                      "landed_series": oc["landed_series"]})

    raw = json.load(open(CFG_PATH))
    raw["sources"] = list(raw["sources"]) + srcs
    tmp = str(CFG_PATH) + ".tmp"
    json.dump(raw, open(tmp, "w"), indent=1, sort_keys=True)
    os.replace(tmp, CFG_PATH)
    print("CONFIG written; n_sources", len(raw["sources"]))

    cfg2 = load_config(CFG_PATH)
    pipe2 = RefreshPipeline(ROOT, cfg2)
    result = pipe2.refresh(source_ids=[s["source_id"] for s in srcs], due_only=False)
    outcomes = result.get("outcomes") if isinstance(result, dict) else None
    pointer = result.get("pointer") if isinstance(result, dict) else None
    print("TARGETED REFRESH outcomes:", json.dumps(outcomes))
    print("POINTER generation:", (pointer or {}).get("generation_sha256", "<none>"))
    json.dump({"bound": bound, "reports": reports, "registry_family": FAMILY_ID,
               "refresh": {"outcomes": outcomes, "pointer": pointer}},
              open("research/BACQ_AGGREGATORS_land_out.json", "w"), indent=1, default=str, sort_keys=True)


if __name__ == "__main__":
    main()
