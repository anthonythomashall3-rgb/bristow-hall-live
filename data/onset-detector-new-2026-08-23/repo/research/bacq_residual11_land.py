"""B-ACQ-RESIDUAL-11 — land the truly-actionable absent FRED series as CURRENT-value
offline-current frozen snapshots. Same proven shape as B-ACQ-NFCI-COMPONENTS /
B-ACQ-5 / B-ACQ-LEI-CEI (adapter fred_json_api, enabled:false + archival:true, bound
to already-registered fred_current_provider; ZERO new parser shapes, section 6.2).
section 3.1 each series its own id. section 22.4 ACQUISITION ONLY — sets no weight,
creates no channel. Owner ruling 2026-08-08: current_revised, BARRED from as-of /
real-time claim; bar recorded in each label.

LAND SET (5) — only ids in ROLE are landed:
  JTSQUL    JOLTS quits (leading labor flow)
  DRALACBN  delinquency rate all loans, all commercial banks
  CORCACBS  charge-off rate consumer loans, all commercial banks (realized loss)
  BAAFFM    Moody's Baa minus fed funds (policy-stance credit spread)
  USPHCI    US coincident economic activity index (Phil Fed; distinct from state siblings)

EXCLUDED (recorded in receipt, NOT landed):
  TOTCI     NEAR-IDENTITY with in-store BUSLOANS (median |%diff| 0.061%) — section 3.5 STOP
  GACDISA066MSFRBNY (corrected Empire id) ALREADY IN STORE — clobber-skip
  Richmond  brief id RCPHBS is BLS compensation (wrong); no free FRED Richmond composite
  ADSINDEX  parser job (B-UNBLOCK-3)
  OECD / World Bank international  owner deferral
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
CACHE = ROOT / "research/prefetch/bacq_residual11"
AS_OF = os.environ["BRES11_ASOF"]
ATT = os.environ["BRES11_ATT"]

ROLE = {
    "JTSQUL": ("JOLTS quits (Quits: Total Nonfarm) — the leading labor flow; "
               "JOLTS hires + layoffs already enabled, quits was the absent third"),
    "DRALACBN": ("delinquency rate on all loans, all commercial banks — "
                 "credit distress, realized"),
    "CORCACBS": ("charge-off rate on consumer loans, all commercial banks — "
                 "realized loss, not anticipated"),
    "BAAFFM": ("Moody's Seasoned Baa Corporate Bond minus Federal Funds Rate — "
               "policy-stance credit spread"),
    "USPHCI": ("US Coincident Economic Activity Index (Philadelphia Fed) — "
               "national aggregate, section 3.1 distinct from the state coincident "
               "siblings; no coincident-index member in store"),
}


def _fetch_notes():
    notes = {}
    for line in open(CACHE / "fetch_manifest.jsonl"):
        r = json.loads(line)
        if r.get("status") == "ok" and r["fred_id"] in ROLE:
            notes[r["fred_id"]] = r
    return notes


def _series_meta(sid):
    meta = json.load(open(CACHE / ("%s.meta.json" % sid)))
    s = meta["seriess"][0]
    return s["title"], s["units"], s["frequency"], s["seasonal_adjustment_short"]


def _freq_word(short):
    return {"Daily": "daily", "Weekly": "weekly", "Monthly": "monthly",
            "Quarterly": "quarterly", "Annual": "annual"}.get(
                short.split(",")[0].strip(), short.split(",")[0].strip().lower())


def source_for(sid):
    title, units, freq, sa = _series_meta(sid)
    return {
        "adapter": "fred_json_api",
        "allowed_hosts": ["api.stlouisfed.org"],
        "archival": True,
        "coverage_source_ids": ["fred_current_provider"],
        "enabled": False,
        "endpoint": ("https://api.stlouisfed.org/fred/series/observations?"
                     "series_id=%s&file_type=json" % sid),
        "expected_content_types": ["application/json"],
        "frequency": _freq_word(freq),
        "information_set_mode": "current_revised",
        "label": (
            "%s (%s) (keyed FRED API, current vintage) [OFFLINE-CURRENT frozen "
            "snapshot; B-ACQ-RESIDUAL-11 %s; current_revised, BARRED from "
            "as-of / real-time claim per owner ruling 2026-08-08; NOT admitted to "
            "any channel and sets no weight per section 22.4]"
            % (title, sa, ROLE[sid])),
        "max_bytes": 33554432,
        "method_version": "fred_%s_json_api_current_offline.v1" % sid.lower(),
        "poll_seconds": 3600,
        "publisher": "Federal Reserve Bank of St. Louis provider",
        "publisher_release_clock": (
            "provider availability is series-specific; exact underlying "
            "publisher release time remains null unless separately proven"),
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
    if sha != note["sha256"]:
        raise SystemExit("SHA MISMATCH %s: %s vs %s" % (sid, sha, note["sha256"]))
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
    notes = _fetch_notes()
    sids = sorted(notes)
    cfg = load_config(CFG_PATH)
    existing_ids = {s["source_id"] for s in cfg["sources"]}
    pipeline = RefreshPipeline(ROOT, cfg)
    pipeline.store.initialize()

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
    print("SKIP already-present:", skipped, "| landable:", len(sids), sids)

    plan, bound = [], []
    for sid in sids:
        src = source_for(sid)
        if src["source_id"] in existing_ids:
            raise SystemExit("COLLISION: %s already in config" % src["source_id"])
        feed_factory._validate_source_candidate(ROOT, cfg, src)
        body, manifest = cache_for(sid, notes[sid])
        if a.dry:
            from rmv2_live.adapters import normalize
            recs = normalize(src, body, AS_OF)
            periods = sorted(r["observation_period"] for r in recs
                             if r["observation_period"])
            plan.append({"series_id": sid, "source_id": src["source_id"],
                         "records": len(recs), "obs_min": periods[0],
                         "obs_max": periods[-1],
                         "bytes": manifest["source_bytes_length"]})
            continue
        oc = bind_offline_current(pipeline, src, body, manifest, AS_OF)
        cfg["sources"].append(src)
        bound.append({"series_id": sid, "source_id": src["source_id"],
                      "records": oc["record_count"],
                      "latest": oc["latest_observation_period"],
                      "receipt": oc["receipt_sha256"][:12]})

    if a.dry:
        json.dump(plan, open("research/BRES11_plan.json", "w"), indent=1)
        print("DRY: %d series gated+parsed, no writes" % len(plan))
        for p in plan:
            print(" ", p["series_id"], p["records"], p["obs_min"], "->", p["obs_max"])
        return

    raw = json.load(open(CFG_PATH))
    raw["sources"] = cfg["sources"]
    tmp = str(CFG_PATH) + ".tmp"
    json.dump(raw, open(tmp, "w"), indent=1, sort_keys=True)
    os.replace(tmp, CFG_PATH)
    print("CONFIG written; n_sources", len(raw["sources"]))
    snap = pipeline.build_snapshot(ATT)
    cov = pipeline.build_coverage(ATT)
    st = pipeline.build_status(ATT, [], snap, cov)
    ptr = pipeline.store.publish_generation(snap, st, cov)
    print("PUBLISHED", ptr.get("generation_sha256"), "bound", len(bound))
    json.dump({"bound": bound, "pointer": ptr},
              open("research/BRES11_land_out.json", "w"), indent=1)


main()
