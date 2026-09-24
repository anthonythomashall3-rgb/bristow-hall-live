"""B-ACQ-REALTIME-EXPECTATIONS item 4 — land the ATSIX inflation-expectations
term structure (Aruoba, Philadelphia Fed) as a FORECAST-COMPARATOR offline-current
EVIDENCE lane via the generic offline-current binder.

Authority: B-ACQ-REALTIME-EXPECTATIONS.md item 4 ("GDPplus + Aruoba
inflation-expectations term structure — verify route, land if clean"); owner
ruling answers/20260806T162209Z_B-LAND-12_ATSIX_EXPECTATIONS.md Option 1 (land as
forecast_comparator; construction set untouched; 4-horizon slice infexp12/24/60/120;
substituted_diagnostic; Real+Factors sheets present-but-not-landed).

Route PROVEN 2026-08-09T07:54:10Z: GET
https://www.philadelphiafed.org/-/media/FRBP/Assets/Surveys-And-Data/atsix/ATSIX_Vintages.xlsx
-> 200, sha256 362eaf7e72973ec09c55589f3c78ba366ce0122b1540a6675b10720f6ee82e3e,
1092093 bytes, InfExp sheet parses to 40474 records over 343 months (1998-01..2026-07);
the fresh fetch sha is byte-identical to the B-LAND-12 CH-R35 prefetch cache.

FIREWALL (owner ruling): ATSIX is a Nelson-Siegel MODEL OUTPUT expectation, a
forecast_comparator ONLY; it NEVER enters the instrumentable construction set
(moving it in is owner-only Option 2, not exercised). §22.4: nothing derives.
The temporal boundary (production date vs reference row date) is UNRESOLVED
offline and is STATED, not assumed.

Zero-network at land time: the freshly-fetched bytes ARE the source object,
sha-attested by the cache_manifest. One TARGETED refresh of the newly-bound
DISABLED source_id (never a full pipeline.refresh — the B-OFFLINE-2 incident)
publishes the generation and writes operational_status in the same step.
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
CACHE = ROOT / "research/prefetch/atsix/ATSIX_Vintages.xlsx"
FETCH_UTC = "2026-08-09T07:54:10Z"
AS_OF = "2026-08-09T07:54:10Z"
URL = ("https://www.philadelphiafed.org/-/media/FRBP/Assets/Surveys-And-Data/"
       "atsix/ATSIX_Vintages.xlsx")
FIREWALL = (
    "FORECAST-COMPARATOR: ATSIX Nelson-Siegel model expected-inflation term "
    "structure; eligible LABELED substituted_diagnostic comparator; NEVER an "
    "instrumentable construction input (owner ruling 20260806T162209Z Option 1; "
    "Option 2 owner-only, not exercised). Temporal boundary production-vs-row "
    "date UNRESOLVED offline. family philadelphia_atsix."
)

MEMBERS = [
    ("ATSIX_INFEXP12", "infexp12", 12),
    ("ATSIX_INFEXP24", "infexp24", 24),
    ("ATSIX_INFEXP60", "infexp60", 60),
    ("ATSIX_INFEXP120", "infexp120", 120),
]


def _source():
    members = [
        {
            "series_id": sid,
            "horizon_column": col,
            "horizon_months": months,
            "label": "ATSIX expected annualized CPI inflation %d months ahead "
                     "(Nelson-Siegel model output). %s" % (months, FIREWALL),
        }
        for sid, col, months in MEMBERS
    ]
    return {
        "adapter": "atsix_termstructure_xlsx",
        "allowed_hosts": ["www.philadelphiafed.org"],
        "archival": True,
        "coverage_source_ids": ["philadelphia_atsix"],
        "enabled": False,
        "endpoint": URL,
        "expected_content_types": [
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/octet-stream",
        ],
        "frequency": "monthly",
        "information_set_mode": "substituted_diagnostic",
        "label": (
            "Philadelphia Fed ATSIX (Aruoba Term Structure of Inflation "
            "Expectations) InfExp 4-horizon slice [OFFLINE-CURRENT frozen "
            "forecast_comparator snapshot; route proven %s; %s]" % (FETCH_UTC, FIREWALL)
        ),
        "max_bytes": 33554432,
        "method_version": "atsix_infexp_offline.v1",
        "poll_seconds": 86400,
        "publisher": "Federal Reserve Bank of Philadelphia",
        "publisher_release_clock": (
            "irregular ATSIX model production update; the exact model production "
            "date per reference month is not carried in the workbook (temporal "
            "boundary UNRESOLVED offline)"
        ),
        "rights_status": "published_research_data",
        "secret_env": None,
        "secret_required": False,
        "series": {
            "index_label": "ATSIX inflation-expectations term structure (InfExp sheet)",
            "unit": "percent annualized expected CPI inflation",
            "sheets_present_not_landed": ["Real", "Factors"],
            "members": members,
        },
        "source_id": "philadelphia_atsix_infexp_current_offline",
        "value_status": "forecast",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()

    body = CACHE.read_bytes()
    sha = hashlib.sha256(body).hexdigest()
    manifest = {
        "fetch_utc": FETCH_UTC,
        "source_bytes_length": len(body),
        "source_sha256": sha,
        "url": URL,
    }
    src = _source()

    cfg = load_config(CFG_PATH)
    if src["source_id"] in {s["source_id"] for s in cfg["sources"]}:
        raise SystemExit("COLLISION: %s already in config" % src["source_id"])

    pipeline = RefreshPipeline(ROOT, cfg)
    pipeline.store.initialize()

    running = dict(cfg)
    running["sources"] = list(cfg["sources"])
    feed_factory._validate_source_candidate(ROOT, running, src)
    recs = normalize(src, body, AS_OF)
    sids = sorted({r["series_id"] for r in recs})
    periods = [r["observation_period"] for r in recs if r["observation_period"]]
    report = {
        "source_id": src["source_id"],
        "records": len(recs),
        "n_series": len(sids),
        "series": sids,
        "first": min(periods),
        "last": max(periods),
        "sha256": sha,
        "bytes": len(body),
    }
    print("GATE PASS:", json.dumps(report))

    if a.dry:
        json.dump(report, open("research/BACQ_REALTIME_ATSIX_land_plan.json", "w"),
                  indent=1, sort_keys=True)
        print("DRY: gated + parsed, no writes.")
        return

    oc = bind_offline_current(pipeline, src, body, manifest, AS_OF)
    print("BOUND", src["source_id"], oc["record_count"], oc["receipt_sha256"][:12],
          "latest", oc["latest_observation_period"])

    raw = json.load(open(CFG_PATH))
    raw["sources"] = list(raw["sources"]) + [src]
    tmp = str(CFG_PATH) + ".tmp"
    json.dump(raw, open(tmp, "w"), indent=1, sort_keys=True)
    os.replace(tmp, CFG_PATH)
    print("CONFIG written; n_sources", len(raw["sources"]))

    cfg2 = load_config(CFG_PATH)
    pipe2 = RefreshPipeline(ROOT, cfg2)
    result = pipe2.refresh(source_ids=[src["source_id"]], due_only=False)
    outcomes = result.get("outcomes") if isinstance(result, dict) else None
    pointer = result.get("pointer") if isinstance(result, dict) else None
    print("TARGETED REFRESH outcomes:", json.dumps(outcomes))
    print("POINTER generation:", (pointer or {}).get("generation_sha256", "<none>"))
    out = {
        "bound": {
            "records": oc["record_count"],
            "receipt_sha256": oc["receipt_sha256"],
            "latest": oc["latest_observation_period"],
            "landed_series": oc["landed_series"],
        },
        "report": report,
        "refresh": {"outcomes": outcomes, "pointer": pointer},
    }
    json.dump(out, open("research/BACQ_REALTIME_ATSIX_land_out.json", "w"),
              indent=1, default=str, sort_keys=True)


if __name__ == "__main__":
    main()
