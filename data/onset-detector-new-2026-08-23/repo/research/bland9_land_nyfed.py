"""B-LAND-9 item 2 — land the New York Fed Staff Nowcast as a FORECAST-class
offline-current EVIDENCE lane (three horizon series from one cached xlsx), via
the generic offline-current binder.

Priority 1 (Livingston 1946+) is NOT landable from this cache: CH-R35 recorded the
per-variable livingston__*.xlsx as soft-404 DECOYS (all sha 8d779811..., 18396 B) and
the consolidated pre-1991 spreadsheet as "not statically discoverable"; only 71 survey
PDFs + release-dates.xlsx were cached. Cleveland + Greenbook = ROUTE-UNRESOLVED (0
files). FOMC SEP = PDF projection tables only. Zero network binds this batch to the
cache, so NY Fed (CH-R35 verdict LANDING-READY) is the one cleanly landable numeric
source this sitting; the batch sanctions STOP after a single source.

FORECAST FIREWALL (CLAUDE.md): a forecast of a MEASUREMENT (real GDP growth) ->
eligible LABELED substituted_diagnostic input AND forecast_comparator; NEVER an NBER
recession-LABEL product. Bound to the registered family `nyfed_nowcast` (role
forecast_comparator, access B, published_output_under_NY_Fed_terms).

Zero network. The cache xlsx bytes ARE the source object (sha-manifested from CH-R35),
normalized through the `forecast_xlsx` adapter's new `nyfed_nowcast` shape (in-memory
core.xml repair path; ORIGINAL bytes bound). enabled:false + archival:true. Converge
via ONE TARGETED zero-network refresh of the newly-bound DISABLED source_id only.
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
FAMILY = "nyfed_nowcast"
NOWCAST_PAGE = "https://www.newyorkfed.org/research/policy/nowcast"

FIREWALL = (
    "FORECAST class: forecast of a MEASUREMENT (real GDP growth) -> eligible "
    "LABELED substituted_diagnostic input AND forecast_comparator; NOT an NBER "
    "recession-LABEL product. Never a construction input unadmitted. family "
    "nyfed_nowcast. B-LAND-9."
)


def _manifest_index(subdir):
    man = json.load(open(CACHE / subdir / "MANIFEST.sha256.json"))
    idx = {f["path"].split("/")[-1]: f for f in man["files"]}
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


def _nyfed_source(filename):
    return {
        "adapter": "forecast_xlsx",
        "allowed_hosts": ["www.newyorkfed.org"],
        "archival": True,
        "coverage_source_ids": [FAMILY],
        "enabled": False,
        "endpoint": "%s#%s" % (NOWCAST_PAGE, filename),
        "expected_content_types": [
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/octet-stream",
        ],
        "frequency": "weekly",
        "information_set_mode": "substituted_diagnostic",
        "label": (
            "New York Fed Staff Nowcast of real GDP growth (backcast/nowcast/"
            "forecast horizons, By-Horizon tidy sheet; coverage 2002-01-04 to "
            "2021-08-27 = the reconstructed+real-time history through the 2021 "
            "suspension, the full extent of the CH-R35 cache) [OFFLINE-CURRENT "
            "frozen forecast snapshot; CH-R35 cache; %s]" % FIREWALL
        ),
        "max_bytes": 33554432,
        "method_version": "nyfed_nowcast_offline.v1",
        "poll_seconds": 86400,
        "publisher": "Federal Reserve Bank of New York",
        "publisher_release_clock": (
            "weekly Friday about 1245 ET named vintage; exact media download URL "
            "not captured by CH-R35"
        ),
        "rights_status": "published_output_under_NY_Fed_terms",
        "secret_env": None,
        "secret_required": False,
        "series": {
            "forecast_shape": "nyfed_nowcast",
            "sheet": "Forecasts By Horizon",
            "id_base": "NYFED_STAFF_GDP",
            "unit": "percent, annualized real GDP growth (SAAR)",
            "label": (
                "New York Fed Staff Nowcast of real GDP growth. %s" % FIREWALL
            ),
        },
        "source_id": "nyfed_staff_nowcast",
        "value_status": "actual",
    }


def build_plan():
    gen, idx = _manifest_index("nyfed_nowcast")
    filename = "nyfed_staff_nowcast_2002-present.xlsx"
    body, man = _cache_manifest("nyfed_nowcast", filename, gen, idx,
                                "%s#%s" % (NOWCAST_PAGE, filename))
    return [(_nyfed_source(filename), body, man)]


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
            "series_ids": sids,
            "first": min(periods), "last": max(periods),
        }
        running["sources"] = list(running["sources"]) + [src]
    print("GATE PASS all %d sources, %d distinct series." % (len(plan), len(all_series)))
    print("total records:", sum(v["records"] for v in report.values()))
    print(json.dumps(report, indent=1, sort_keys=True))

    if a.dry:
        json.dump({"report": report, "n_series": len(all_series)},
                  open("research/BLAND9_land_plan.json", "w"), indent=1, sort_keys=True)
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
              open("research/BLAND9_land_out.json", "w"), indent=1, default=str,
              sort_keys=True)


main()
