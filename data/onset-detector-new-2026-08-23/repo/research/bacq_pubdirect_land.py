"""B-ACQ-PUBLISHER-DIRECT — land the DOL ETA-539 raw state report (ar539.csv)
as ONE deep offline-current frozen EVIDENCE lane via the generic offline-current
binder. ZERO network (consumes B-FETCH-PUBLISHER-DIRECT staged bytes).

The raw ar539.csv is the publisher's CURRENT operational database: current /
revised state values, NOT first-release vintages, NOT as-of snapshots. It lands
information_set_mode=current_revised and is BARRED from any as-of / real-time
claim (owner CLOCK ruling 2026-08-08). The enabled dol_eta539_live lane keeps the
last 160 rows/state; this frozen deep lane preserves the full 1984-06 .. 2026-07
span (max measured 2132 rows/state, retention 2200 => no silent cap). Proven
dol_eta539_csv shape (already used by dol_eta539_live) => ZERO new parser shape
(§6.1). Bound to registered family dol_ui_claims (access A). §3.1 each state
series is own-id (dol_eta539_deep_offline.<ST>.<label>), NEVER aliased onto ICSA.
enabled:false + archival:true (frozen evidence; a fetchable archival row would
clobber the audited offline bytes).
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
BODY_PATH = ROOT / "research/_staging/publisher_direct/dol_eta539/csv/ar539.csv"
FAMILY = "dol_ui_claims"
ENDPOINT = "https://oui.doleta.gov/unemploy/csv/ar539.csv"
FETCH_UTC = "2026-08-08T18:05:59Z"   # measured, B-FETCH-PUBLISHER-DIRECT manifest
AS_OF = "2026-08-08T00:00:00Z"
SOURCE_ID = "dol_eta539_deep_offline"

FIREWALL = (
    "Raw ar539 = publisher CURRENT operational DB (current/revised), NOT vintages "
    "and NOT as-of snapshots; current_revised, BARRED from as-of / real-time claim "
    "(owner CLOCK ruling 2026-08-08). Own-id state series, NEVER aliased onto ICSA / "
    "ICNSA. B-ACQ-PUBLISHER-DIRECT.")


def _cache_manifest(body):
    return {
        "fetch_utc": FETCH_UTC,
        "source_bytes_length": len(body),
        "source_sha256": hashlib.sha256(body).hexdigest(),
        "url": ENDPOINT,
    }


def _source():
    return {
        "adapter": "dol_eta539_csv",
        "allowed_hosts": ["oui.doleta.gov"],
        "archival": True,
        "coverage_source_ids": [FAMILY],
        "enabled": False,
        "endpoint": ENDPOINT,
        "expected_content_types": ["application/csv", "text/csv", "text/plain"],
        "frequency": "weekly_state_reporting",
        "information_set_mode": "current_revised",
        "label": (
            "DOL ETA-539 raw state UI reports — FULL 1984-06..2026-07 deep span "
            "[OFFLINE-CURRENT frozen evidence; B-FETCH-PUBLISHER-DIRECT cache; %s]"
            % FIREWALL),
        "max_bytes": 50000000,
        "method_version": "eta_539_raw_state_report_deep_offline_v1",
        "poll_seconds": 86400,
        "publisher": "U.S. Department of Labor, Employment and Training Administration",
        "publisher_release_clock": (
            "raw operational database frozen snapshot; distinct from the Thursday "
            "08:30 national release; not a live release clock"),
        "rights_status": "public_government_source_with_attribution",
        "secret_env": None,
        "secret_required": False,
        "series": {"retention_rows_per_state": 2200},
        "source_id": SOURCE_ID,
        "value_status": "actual",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()

    body = BODY_PATH.read_bytes()
    manifest = _cache_manifest(body)
    src = _source()

    cfg = load_config(CFG_PATH)
    if SOURCE_ID in {s["source_id"] for s in cfg["sources"]}:
        raise SystemExit("COLLISION: %s already in config" % SOURCE_ID)

    pipeline = RefreshPipeline(ROOT, cfg)
    pipeline.store.initialize()

    running = dict(cfg)
    running["sources"] = list(cfg["sources"])
    feed_factory._validate_source_candidate(ROOT, running, src)
    recs = normalize(src, body, AS_OF)
    states = sorted({r["state"] for r in recs})
    ids = sorted({r["series_id"] for r in recs})
    periods = [r["observation_period"] for r in recs if r["observation_period"]]
    avail = sum(1 for r in recs if r.get("value_status") != "unavailable")
    bad = [i for i in ids if not i.startswith(SOURCE_ID + ".")]
    if bad:
        raise SystemExit("ID DRIFT: %r" % bad[:5])
    report = {
        "records": len(recs), "available": avail, "n_series": len(ids),
        "n_states": len(states), "first_period": min(periods),
        "last_period": max(periods),
    }
    print("GATE PASS. report:", json.dumps(report))

    if a.dry:
        json.dump({"report": report, "states": states,
                   "sample_ids": ids[:10]},
                  open("research/BACQ_PUBDIRECT_land_plan.json", "w"),
                  indent=1, sort_keys=True)
        print("DRY: gated + parsed, no writes.")
        return

    oc = bind_offline_current(pipeline, src, body, manifest, AS_OF)
    bound = {
        "records": oc["record_count"], "receipt": oc["receipt_sha256"],
        "latest": oc["latest_observation_period"],
        "source_bytes_sha256": oc["source_bytes_sha256"],
    }
    print("BOUND", SOURCE_ID, oc["record_count"], oc["receipt_sha256"][:12])

    raw = json.load(open(CFG_PATH))
    raw["sources"] = list(raw["sources"]) + [src]
    tmp = str(CFG_PATH) + ".tmp"
    json.dump(raw, open(tmp, "w"), indent=1, sort_keys=True)
    os.replace(tmp, CFG_PATH)
    print("CONFIG written; n_sources", len(raw["sources"]))

    cfg2 = load_config(CFG_PATH)
    pipe2 = RefreshPipeline(ROOT, cfg2)
    result = pipe2.refresh(source_ids=[SOURCE_ID], due_only=False)
    outcomes = result.get("outcomes") if isinstance(result, dict) else None
    pointer = result.get("pointer") if isinstance(result, dict) else None
    print("TARGETED REFRESH outcomes:", json.dumps(outcomes, default=str))
    print("POINTER generation:", (pointer or {}).get("generation_sha256", "<none>"))
    json.dump({"bound": bound, "report": report, "states": states,
               "refresh": {"outcomes": outcomes, "pointer": pointer}},
              open("research/BACQ_PUBDIRECT_land_out.json", "w"), indent=1,
              default=str, sort_keys=True)


main()
