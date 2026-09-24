"""B-GEO-LAND-1 producer: stage the 50-state + DC coincident-index siblings.

Fills the B-REG-GEO phci family gap by landing the REAL publisher family
(Philadelphia Fed state coincident indexes, FRED release rid=109) as
current_revised OFFLINE-CURRENT snapshots, EXACT siblings of the already-landed
national ``fred_usphci_api_current_offline`` (B-ACQ-RESIDUAL-11).

Route (brief B-GEO-LAND-1, route_proofs research/geo_expand/ROUTE_PROOFS.v1.json):
publisher-direct coincident-revised.xls is OLE2 (no xlrd/olefile in the pinned
interpreter -> unreadable this batch); the brief's REAL-TIME lane names ALFRED
release rid=109, landable via the already-admitted fred_json_api route. This
producer takes that route for the current_revised snapshot.

Constraints honored:
  * clones the proven fred_json_api current shape (method_version
    fred_json_api_current.v1) => 0 new shapes (CLAUDE.md six-file note untouched).
  * each state = its own source_id (section 3.1); NEVER aliased to USPHCI or any
    national series.
  * current_revised only; BARRED from as-of / real-time claim per owner ruling
    2026-08-08 (same bar carried on USPHCI). ALFRED-vintage / release-event
    ledger as-of lane is DEFERRED (reported, not silently capped -- section 19.4).
  * section 22.4 land-only: derives NOTHING -- no state composite, no renorm,
    no channel/member/weight/threshold.

produce = NO store write. Stages drafts only.
"""
import json
import sys
import urllib.request
from pathlib import Path

REPO = Path("/Users/anthonyhall/Projects/bristow-hall/repo")
sys.path.insert(0, str(REPO))

RELEASE_ID = 109  # Philadelphia Fed -- State Coincident Indexes


def _key():
    for line in (REPO / "live_data/config/local.env").read_text().splitlines():
        if line.startswith("FRED_API_KEY="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("no FRED_API_KEY")


def _release_series(key):
    """The measured rid=109 membership -- ids taken from FRED, not assumed."""
    url = ("https://api.stlouisfed.org/fred/release/series?release_id=%d"
           "&file_type=json&api_key=%s&limit=1000" % (RELEASE_ID, key))
    with urllib.request.urlopen(url, timeout=30) as r:
        d = json.loads(r.read())
    return d["seriess"]  # id, title, units, frequency, observation_start/end


LABEL_BAR = (
    "[OFFLINE-CURRENT frozen snapshot; B-GEO-LAND-1 state coincident sibling of "
    "USPHCI (Philadelphia Fed state coincident index, FRED release rid=109), "
    "section 3.1 distinct source; current_revised, BARRED from as-of / real-time "
    "claim per owner ruling 2026-08-08; NOT admitted to any channel and sets no "
    "weight per section 22.4]"
)


def build_spec(meta):
    sid = meta["id"]
    title = meta["title"]
    unit = meta["units"]
    return {
        "adapter": "fred_json_api",
        "allowed_hosts": ["api.stlouisfed.org"],
        "archival": True,
        "coverage_source_ids": ["fred_current_provider"],
        "enabled": False,
        "endpoint": ("https://api.stlouisfed.org/fred/series/observations?"
                     "series_id=%s&file_type=json" % sid),
        "expected_content_types": ["application/json"],
        "frequency": "monthly",
        "information_set_mode": "current_revised",
        "label": "%s (keyed FRED API, current vintage) %s" % (title, LABEL_BAR),
        "max_bytes": 33554432,
        "method_version": "fred_json_api_current.v1",
        "poll_seconds": 3600,
        "publisher": "Federal Reserve Bank of St. Louis provider",
        "publisher_release_clock": ("provider availability is series-specific; "
                                    "exact underlying publisher release time "
                                    "remains null unless separately proven"),
        "rights_status": "FRED_terms_and_underlying_publisher_rights_control",
        "secret_env": "FRED_API_KEY",
        "secret_required": True,
        "series": {"label": title, "series_id": sid, "unit": unit},
        "source_id": "fred_%s_api_current_offline" % sid.lower(),
        "value_status": "actual",
    }


def main():
    from bh import produce as bhp
    key = _key()
    members = _release_series(key)
    members.sort(key=lambda m: m["id"])
    # USPHCI is the national aggregate already landed -- exclude, keep only states/DC.
    members = [m for m in members if m["id"] != "USPHCI"]
    specs = [build_spec(m) for m in members]
    print("release %d members (ex-USPHCI): %d" % (RELEASE_ID, len(specs)))

    out = REPO / "research/geo_land_1/specs.v1.json"
    out.write_text(json.dumps(specs, indent=1, sort_keys=True))
    print("authored %d specs -> %s" % (len(specs), out))

    landed = []
    for spec in specs:
        drafts = bhp.run_produce(REPO, spec["source_id"], source_specs=[spec])
        for d in drafts:
            landed.append((d["source_id"], d["payload"]["byte_length"],
                           d["payload"]["sha256"][:12]))
            print("produced %s %d bytes sha %s"
                  % (d["source_id"], d["payload"]["byte_length"],
                     d["payload"]["sha256"][:12]))
    print("STAGED %d drafts; store/config/receipts untouched" % len(landed))


if __name__ == "__main__":
    main()
