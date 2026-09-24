"""B-OFFLINE-2 Part 2 item 1 — land the FRED never/negligible-revised MISS block
as CURRENT-value offline lanes via the generic offline-current binder.

Authority: B-OFFLINE-2_GENERIC_BIND.md (mandatory tranche item 1) + CH-R26/R29
certification (first-print == vintage == latest for these; note recorded per
series). Offline, no network: cache bytes ARE the source object, normalized
through the proven live parse_fred_json_api (current lane). Bound to the ALREADY
registered fred_current_provider family (no new family, no owner decision).
Each landed source is enabled:false + archival:true (a frozen current snapshot).
"""
import argparse
import glob
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
CACHE = ROOT / "research/prefetch/fred_miss"
AS_OF = "2026-08-06T00:00:00Z"
ATT = "2026-08-06T05:00:00Z"


def _manifest_notes():
    notes = {}
    for line in open(CACHE / "manifest.jsonl"):
        r = json.loads(line)
        if r.get("fred_id") and r.get("kind") == "fred_current_obs":
            notes[r["fred_id"]] = {
                "fetch_utc": r["fetch_utc"],
                "note": r.get("note"),
                "manifest_sha": r["sha256"],
            }
    return notes


def _series_meta(sid):
    meta = json.load(open(CACHE / ("%s.meta.json" % sid)))
    s = meta["seriess"][0]
    return s["title"], s["units"], s["frequency"]


def _freq_word(short):
    return {
        "Daily": "daily", "Weekly": "weekly", "Monthly": "monthly",
        "Quarterly": "quarterly", "Annual": "annual",
        "Daily, 7-Day": "daily", "Daily, Close": "daily",
    }.get(short, short.lower())


def source_for(sid, note):
    title, units, freq = _series_meta(sid)
    return {
        "adapter": "fred_json_api",
        "allowed_hosts": ["api.stlouisfed.org"],
        "archival": True,
        "coverage_source_ids": ["fred_current_provider"],
        "enabled": False,
        "endpoint": (
            "https://api.stlouisfed.org/fred/series/observations?series_id=%s"
            "&file_type=json" % sid
        ),
        "expected_content_types": ["application/json"],
        "frequency": _freq_word(freq),
        "information_set_mode": "current_revised",
        "label": (
            "%s (keyed FRED API, current vintage) [OFFLINE-CURRENT frozen "
            "snapshot; CH-R26 revision class: %s]" % (title, note)
        ),
        "max_bytes": 33554432,
        "method_version": "fred_%s_json_api_current_offline.v1" % sid.lower(),
        "poll_seconds": 3600,
        "publisher": "Federal Reserve Bank of St. Louis provider",
        "publisher_release_clock": (
            "provider availability is series-specific; exact underlying "
            "publisher release time remains null unless separately proven"
        ),
        "rights_status": "FRED_terms_and_underlying_publisher_rights_control",
        "secret_env": "FRED_API_KEY",
        "secret_required": True,
        "series": {"label": title, "series_id": sid, "unit": units},
        "source_id": "fred_%s_api_current_offline" % sid.lower(),
        "value_status": "actual",
    }


def cache_for(sid, note):
    body = (CACHE / ("%s.obs.json" % sid)).read_bytes()
    sha = hashlib.sha256(body).hexdigest()
    if sha != note["manifest_sha"]:
        raise SystemExit("SHA MISMATCH for %s: cache %s vs manifest %s"
                         % (sid, sha, note["manifest_sha"]))
    manifest = {
        "fetch_utc": note["fetch_utc"],
        "source_bytes_length": len(body),
        "source_sha256": sha,
        "url": ("https://api.stlouisfed.org/fred/series/observations?"
                "series_id=%s&file_type=json" % sid),
    }
    return body, manifest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    notes = _manifest_notes()
    sids = sorted(
        os.path.basename(p)[:-9]
        for p in glob.glob(str(CACHE / "*.obs.json"))
    )
    cfg = load_config(CFG_PATH)
    existing_ids = {s["source_id"] for s in cfg["sources"]}
    pipeline = RefreshPipeline(ROOT, cfg)
    pipeline.store.initialize()

    # clobber-proof: skip any cache series whose series_id already has a store
    # lane (DGS30, WALCL). The append-only gate would red-bar them anyway; we
    # filter + report so the tranche is exactly the genuinely-absent set.
    landed_series_ids = set()
    _snap0 = pipeline.build_snapshot(ATT)

    def _walk(o):
        if isinstance(o, dict):
            sid_ = o.get("series_id")
            if isinstance(sid_, str):
                landed_series_ids.add(sid_)
            for v in o.values():
                _walk(v)
        elif isinstance(o, list):
            for v in o:
                _walk(v)
    _walk(_snap0)
    skipped = [s for s in sids if s in landed_series_ids]
    sids = [s for s in sids if s not in landed_series_ids]
    print("SKIP already-present:", skipped, "| landable:", len(sids))

    plan = []
    bound = []
    for sid in sids:
        note = notes[sid]
        src = source_for(sid, note["note"])
        if src["source_id"] in existing_ids:
            raise SystemExit("COLLISION: %s already in config" % src["source_id"])
        # append-only family + registry-binding gate BEFORE any write.
        feed_factory._validate_source_candidate(ROOT, cfg, src)
        body, manifest = cache_for(sid, note)
        if a.dry:
            from rmv2_live.adapters import normalize
            recs = normalize(src, body, AS_OF)
            periods = sorted(r["observation_period"] for r in recs
                             if r["observation_period"])
            plan.append({
                "series_id": sid, "source_id": src["source_id"],
                "records": len(recs), "obs_min": periods[0],
                "obs_max": periods[-1], "note": note["note"],
                "bytes": manifest["source_bytes_length"],
            })
            continue
        oc = bind_offline_current(pipeline, src, body, manifest, AS_OF)
        cfg["sources"].append(src)
        bound.append({
            "series_id": sid, "source_id": src["source_id"],
            "records": oc["record_count"],
            "latest": oc["latest_observation_period"],
            "receipt": oc["receipt_sha256"][:12], "note": note["note"],
        })

    if a.dry:
        json.dump(plan, open("research/OFFLINE2_fred_plan.json", "w"), indent=1)
        print("DRY: %d series gated+parsed, no writes" % len(plan))
        print("total records:", sum(p["records"] for p in plan))
        return

    raw = json.load(open(CFG_PATH))
    raw["sources"] = cfg["sources"]
    tmp = str(CFG_PATH) + ".tmp"
    json.dump(raw, open(tmp, "w"), indent=1, sort_keys=True)
    os.replace(tmp, CFG_PATH)
    print("CONFIG written; n_sources", len(raw["sources"]),
          "archival", sum(1 for s in raw["sources"] if s.get("archival")))
    snap = pipeline.build_snapshot(ATT)
    cov = pipeline.build_coverage(ATT)
    st = pipeline.build_status(ATT, [], snap, cov)
    ptr = pipeline.store.publish_generation(snap, st, cov)
    gen = ptr.get("generation_sha256")
    print("PUBLISHED", gen, "bound", len(bound),
          "records", sum(b["records"] for b in bound))
    json.dump({"bound": bound, "pointer": ptr},
              open("research/OFFLINE2_fred_land_out.json", "w"), indent=1)


main()
