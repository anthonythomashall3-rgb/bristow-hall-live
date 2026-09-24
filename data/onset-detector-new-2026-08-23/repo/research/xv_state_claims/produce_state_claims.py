"""B-XV-LAND-STATE-CLAIMS producer: stage 51 state {ST}ICLAIMS FRED current_revised sources.

Clones the proven fred_icsa_api_current shape (adapter fred_json_api,
method_version fred_json_api_current.v1 => 0 new shapes). Fetches real FRED
/series metadata per state for honest label/unit. produce = NO store write.
"""
import json
import os
import sys
import urllib.request
from pathlib import Path

REPO = Path("/Users/anthonyhall/Projects/bristow-hall/repo")
sys.path.insert(0, str(REPO))

STATES = ("AK AL AR AZ CA CO CT DC DE FL GA HI IA ID IL IN KS KY LA MA MD ME MI "
          "MN MO MS MT NC ND NE NH NJ NM NV NY OH OK OR PA RI SC SD TN TX UT VA "
          "VT WA WI WV WY").split()
assert len(STATES) == 51, len(STATES)


def _key():
    for line in (REPO / "live_data/config/local.env").read_text().splitlines():
        if line.startswith("FRED_API_KEY="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("no FRED_API_KEY")


def _series_meta(sid, key):
    url = ("https://api.stlouisfed.org/fred/series?series_id=%s&file_type=json&api_key=%s"
           % (sid, key))
    with urllib.request.urlopen(url, timeout=30) as r:
        d = json.loads(r.read())["seriess"][0]
    return d["title"], d["units"]


def build_spec(sid, title, unit):
    return {
        "adapter": "fred_json_api",
        "allowed_hosts": ["api.stlouisfed.org"],
        "coverage_source_ids": ["fred_current_provider"],
        "enabled": True,
        "endpoint": ("https://api.stlouisfed.org/fred/series/observations?"
                     "series_id=%s&file_type=json" % sid),
        "expected_content_types": ["application/json"],
        "frequency": "weekly",
        "information_set_mode": "current_revised",
        "label": "%s (keyed FRED API, current vintage)" % title,
        "max_bytes": 8000000,
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
        "source_id": "fred_%s_api_current" % sid.lower(),
        "value_status": "actual",
    }


def main():
    from bh import produce as bhp
    key = _key()
    specs = []
    for st in STATES:
        sid = "%sICLAIMS" % st
        title, unit = _series_meta(sid, key)
        specs.append(build_spec(sid, title, unit))
    # persist the authored spec set for the receipt + audit
    out = REPO / "research/xv_state_claims/specs.v1.json"
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
