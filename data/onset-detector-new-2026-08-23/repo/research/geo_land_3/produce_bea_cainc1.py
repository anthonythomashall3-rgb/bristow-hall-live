"""B-GEO-LAND-3 producer: stage BEA Regional CAINC1 personal income.

One publisher-direct zip (route-proof research/geo_expand/ROUTE_PROOFS.v1.json,
re-verified byte-exact at fetch this batch: 3467441 B) carries the U.S.
aggregate, the eight BEA regions, 50 states + DC, and ~3,149 counties, each with
three LineCodes (personal income, population, per-capita income) across annual
columns 1969-2024. It is split into four distinct geo cross-sections, one source
id each (section 3.1) -- the ALL_AREAS file is never collapsed:

  * bea_cainc1_national_current_offline   national_us   (US aggregate)
  * bea_cainc1_bearegion_current_offline  bea_region    (8 BEA regions)
  * bea_cainc1_state_current_offline      state_or_dc   (50 states + DC)
  * bea_cainc1_county_current_offline     county        (~3,149 counties)

Constraints honored:
  * new adapter bea_regional_cainc_zip -- no existing adapter reads this shape;
    parse_bea_api is the BEA statistics API (JSON), not the regional zip.
  * each geography = its own series, each LineCode = its own series, each year =
    its own observation (section 3.1); distinct source id per geography_type.
  * current_revised OFFLINE-CURRENT snapshot, enabled:false, archival:true
    (annual benchmark revisions; last updated Feb 5 2026 per the file).
  * section 22.4 land-only: derives NOTHING -- personal income, population, and
    BEA's own published per-capita line landed raw. WE compute no per-capita and
    author no geo composite.
  * publisher '(NA)' lands value_status=unavailable, never dropped (section 19.4).
  * OFF-AXIS income content (CH-R122 preferred axis); admission to any channel/
    member/weight DEFERRED (section 22.2 universe not closed).
  * Rights: BEA public, cite BEA.

produce = NO store write. Stages drafts only. The committer (bh commit-staged)
is the one config/store writer.
"""
import json
import sys
from pathlib import Path

REPO = Path("/Users/anthonyhall/Projects/bristow-hall/repo")
sys.path.insert(0, str(REPO))

ENDPOINT = "https://apps.bea.gov/regional/zip/CAINC1.zip"

LABEL_BAR = (
    "[OFFLINE-CURRENT frozen snapshot; B-GEO-LAND-3 BEA Regional CAINC1 %s "
    "personal-income cross-section (annual 1969-2024), section 3.1 distinct "
    "source; current_revised; OFF-AXIS income (CH-R122); NOT admitted to any "
    "channel and sets no weight per section 22.4]"
)


def _spec(source_id, geography_type, geo_label):
    return {
        "adapter": "bea_regional_cainc_zip",
        "allowed_hosts": ["apps.bea.gov"],
        "archival": True,
        "coverage_source_ids": ["bea_regional"],
        "enabled": False,
        "endpoint": ENDPOINT,
        "expected_content_types": [
            "application/x-zip-compressed",
            "application/zip",
        ],
        "frequency": "annual",
        "information_set_mode": "current_revised",
        "label": (
            "BEA Regional CAINC1 county personal income summary, %s "
            % geo_label + LABEL_BAR % geography_type
        ),
        "max_bytes": 4000000,
        "method_version": "bea_regional_cainc1_current.v1",
        "poll_seconds": 86400,
        "publisher": "U.S. Bureau of Economic Analysis",
        "publisher_release_clock": (
            "annual BEA Regional benchmark release; reference year, release, "
            "revision, retrieval, and validation clocks remain separate and "
            "exact time is null unless directly proven"
        ),
        "rights_status": "public_government_source_with_attribution",
        "secret_env": None,
        "secret_required": False,
        "series": {
            "geography_type": geography_type,
            "series_id_prefix": "BEA.CAINC1",
            "table": "CAINC1",
        },
        "source_id": source_id,
        "value_status": "actual",
    }


SPECS = [
    _spec("bea_cainc1_national_current_offline", "national_us",
          "U.S. aggregate"),
    _spec("bea_cainc1_bearegion_current_offline", "bea_region",
          "8 BEA regions"),
    _spec("bea_cainc1_state_current_offline", "state_or_dc",
          "50 states + DC"),
    _spec("bea_cainc1_county_current_offline", "county",
          "counties / county-equivalents"),
]


def main():
    from bh import produce as bhp
    out = REPO / "research/geo_land_3/specs.v1.json"
    out.write_text(json.dumps(SPECS, indent=1, sort_keys=True))
    print("authored %d specs -> %s" % (len(SPECS), out))
    for spec in SPECS:
        drafts = bhp.run_produce(
            REPO, spec["source_id"], source_specs=[spec])
        for d in drafts:
            print("produced %s %d bytes sha %s"
                  % (d["source_id"], d["payload"]["byte_length"],
                     d["payload"]["sha256"][:12]))
    print("STAGED; store/config/receipts untouched")


if __name__ == "__main__":
    main()
