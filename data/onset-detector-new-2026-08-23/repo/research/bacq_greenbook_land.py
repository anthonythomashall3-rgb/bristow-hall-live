"""B-ACQ-GREENBOOK — land the Phil Fed Greenbook/Tealbook Row Format as two offline-current
EVIDENCE lanes via the generic offline-current binder. ZERO network.

The single Row Format workbook (documentation/GBweb_Row_Format.xlsx, staged + sha-manifested
by B-FETCH-GREENBOOK) is bound TWICE, both times as the byte-identical source object:

  * greenbook_row_hist_offline : the Bx real-time HISTORICAL values -> GB_<VAR>_HIST,
    information_set_mode=archive_snapshot_asof. Own-id NEAR/research as-of lanes; NEVER
    aliased onto a member (brief §3.5: "Greenbook IP is not necessarily FRED INDPRO").
  * greenbook_row_proj_offline : the Fx staff PROJECTIONS -> GB_<VAR>_PROJ,
    information_set_mode=substituted_diagnostic. forecast_comparator, never a member.

The two halves are NEVER mixed in one series (brief STOP; §3.1/§3.6). enabled:false +
archival:true (frozen evidence snapshot). Bound to the registered family
philadelphia_greenbook (access B, role forecast_comparator). Convergence via ONE targeted
zero-network refresh of the two DISABLED source_ids only (the B-OFFLINE-2 incident; the
B-LAND-3D gotcha: refresh republishes the generation AND writes operational_status).
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
from rmv2_live.greenbook_row import GREENBOOK_VARIABLES

ROOT = Path(".").resolve()
CFG_PATH = ROOT / "live_data/config/sources.v1.json"
BODY_PATH = (ROOT / "research/_staging/greenbook/greenbook-data/documentation/"
             "GBweb_Row_Format.xlsx")
FAMILY = "philadelphia_greenbook"
ENDPOINT = ("https://www.philadelphiafed.org/-/media/FRBP/Assets/Surveys-And-Data/"
            "greenbook-data/documentation/GBweb_Row_Format.xlsx?sc_lang=en&"
            "hash=3EA5A088DBD47823D75199F9A4A6BDBB")
FETCH_UTC = "20260808T172655Z"   # measured, from B-FETCH-GREENBOOK FETCH_MANIFEST
AS_OF = "2026-08-08T00:00:00Z"

FIREWALL = (
    "Greenbook is the Fed staff's real-time READ, NEVER the publisher's first release "
    "(no stitched_strict_first_release claim). GB_*_HIST are own-id NEAR/research as-of "
    "lanes, NEVER aliased onto a member (an identity map is an owner decision). "
    "GB_*_PROJ are staff projections: LABELED substituted_diagnostic / comparator, never "
    "an NBER recession-LABEL product, never a construction input unadmitted (§10, §22.4). "
    "B-ACQ-GREENBOOK.")


def _cache_manifest(body):
    sha = hashlib.sha256(body).hexdigest()
    return {
        "fetch_utc": FETCH_UTC,
        "source_bytes_length": len(body),
        "source_sha256": sha,
        "url": ENDPOINT,
    }


def _half_source(half, mode, kind_label):
    variables = list(GREENBOOK_VARIABLES)
    suffix = "HIST" if half == "hist" else "PROJ"
    outputs = [{"series_id": "GB_%s_%s" % (v, suffix)} for v in variables]
    return {
        "adapter": "greenbook_row_xlsx",
        "allowed_hosts": ["www.philadelphiafed.org"],
        "archival": True,
        "coverage_source_ids": [FAMILY],
        "enabled": False,
        "endpoint": ENDPOINT,
        "expected_content_types": [
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/octet-stream",
        ],
        "frequency": "event_driven",
        "information_set_mode": mode,
        "label": (
            "Phil Fed Greenbook/Tealbook Row Format — %s (15 variables) "
            "[OFFLINE-CURRENT frozen evidence; B-FETCH-GREENBOOK cache; %s]"
            % (kind_label, FIREWALL)),
        "max_bytes": 20000000,
        "method_version": "greenbook_row_%s_offline.v1" % half,
        "poll_seconds": 86400,
        "publisher": "Federal Reserve Bank of Philadelphia",
        "publisher_release_clock": (
            "Greenbook/Tealbook data released on a five-year lag, updated annually; the "
            "offline-current lane is a publisher-frozen snapshot keyed by the GBdate "
            "meeting vintage, not a live release clock"),
        "rights_status": "published_research_data",
        "secret_env": None,
        "secret_required": False,
        "series": {"half": half, "outputs": outputs},
        "snapshot_projection": "greenbook_vintage_panel.v1",
        "source_id": "greenbook_row_%s_offline" % half,
        "value_status": "actual",
    }


def build_plan():
    body = BODY_PATH.read_bytes()
    manifest = _cache_manifest(body)
    plan = [
        (_half_source("hist", "archive_snapshot_asof",
                      "real-time HISTORICAL values (Bx)"), body, manifest),
        (_half_source("proj", "substituted_diagnostic",
                      "staff PROJECTIONS (Fx)"), body, manifest),
    ]
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

    # clobber-proof: gate EVERY candidate against the live config BEFORE any write,
    # threading each accepted candidate into the running config so intra-batch
    # collisions are caught too. Assert parser-emitted ids == declared ids.
    running = dict(cfg)
    running["sources"] = list(cfg["sources"])
    report = {}
    all_series = set()
    for src, body, _m in plan:
        feed_factory._validate_source_candidate(ROOT, running, src)
        recs = normalize(src, body, AS_OF)
        emitted = sorted({r["series_id"] for r in recs})
        declared = sorted({o["series_id"] for o in src["series"]["outputs"]})
        if emitted != declared:
            raise SystemExit("ID DRIFT %s: emitted!=declared\n emit %r\n decl %r"
                             % (src["source_id"], emitted, declared))
        dup = all_series.intersection(emitted)
        if dup:
            raise SystemExit("SERIES COLLISION across halves: %r" % sorted(dup))
        all_series.update(emitted)
        avail = sum(1 for r in recs if r.get("value_status") != "unavailable")
        periods = [r["observation_period"] for r in recs if r["observation_period"]]
        vints = [r["greenbook_vintage"] for r in recs if r.get("greenbook_vintage")]
        report[src["source_id"]] = {
            "records": len(recs), "available": avail, "n_series": len(emitted),
            "first_period": min(periods), "last_period": max(periods),
            "first_vintage": min(vints), "last_vintage": max(vints),
            "n_vintages": len(set(vints)),
        }
        running["sources"] = list(running["sources"]) + [src]
    print("GATE PASS %d sources, %d distinct series." % (len(plan), len(all_series)))
    print("total records:", sum(v["records"] for v in report.values()))
    for k, v in report.items():
        print(" ", k, v)

    if a.dry:
        json.dump({"report": report, "n_series": len(all_series)},
                  open("research/BACQ_GREENBOOK_land_plan.json", "w"),
                  indent=1, sort_keys=True)
        print("DRY: gated + parsed, no writes.")
        return

    bound = {}
    for src, body, manifest in plan:
        oc = bind_offline_current(pipeline, src, body, manifest, AS_OF)
        bound[src["source_id"]] = {
            "records": oc["record_count"], "receipt": oc["receipt_sha256"],
            "latest": oc["latest_observation_period"],
            "source_bytes_sha256": oc["source_bytes_sha256"],
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
              open("research/BACQ_GREENBOOK_land_out.json", "w"), indent=1,
              default=str, sort_keys=True)


main()
