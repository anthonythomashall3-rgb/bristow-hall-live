"""B-GEO-LAND-4 producer: stage BEA Regional SAGDP state annual GDP.

One publisher-direct zip (route proven this run by B-ACQ-GEO-EXPAND, re-verified
byte-exact at fetch: SAGDP.zip 10,161,333 B, application/x-zip-compressed,
sha256 5a90e0e6e03082089048d8f78e8a4df9993465c4f34f9de471258fed2a908183) carries
TWO ALL_AREAS tables:

  * SAGDP1 -- state GDP summary (8 LineCodes: real GDP, chain qty index,
    current-dollar GDP, compensation, gross operating surplus, TOPI, subsidies).
  * SAGDP2 -- current-dollar GDP by industry (~94 industry LineCodes).

Each table mixes the U.S. aggregate, the eight BEA regions, and 50 states + DC,
across ANNUAL columns 1997-2025. It is split into six distinct cross-sections,
one source id each (section 3.1) -- the ALL_AREAS file is never collapsed:

  bea_sagdp1_national_current_offline    SAGDP1 national_us
  bea_sagdp1_bearegion_current_offline   SAGDP1 bea_region  (8 BEA regions)
  bea_sagdp1_state_current_offline       SAGDP1 state_or_dc (50 states + DC)
  bea_sagdp2_national_current_offline    SAGDP2 national_us
  bea_sagdp2_bearegion_current_offline   SAGDP2 bea_region
  bea_sagdp2_state_current_offline       SAGDP2 state_or_dc

CORRECTION (section 21.3, unprompted): the B-GEO-LAND-4 brief titled this "state
QUARTERLY GDP". The proven route SAGDP.zip delivers ANNUAL tables (SAGDP1/SAGDP2,
1997-2025). Quarterly BEA state GDP is a SEPARATE, UNPROVEN route (SQGDP.zip) --
NOT landed here, candidate for a future batch. We land what the proven route
actually delivers and label it annual; we do not relabel annual data as quarterly.

Constraints honored:
  * shared adapter bea_regional_cainc_zip -- generalised this batch to select the
    ALL_AREAS member matching series.table, so a multi-table zip (SAGDP1+SAGDP2)
    is honest. 3 SAGDP tests written RED first, then GREEN; 7 CAINC tests still
    pass unchanged.
  * each geography = its own series, each LineCode = its own series, each year =
    its own observation (section 3.1); distinct source id per (table, geo).
    series_id = BEA.{table}.{GeoFIPS}.L{LineCode} -- table in the prefix keeps
    SAGDP1 and SAGDP2 ids disjoint at the same GeoFIPS/LineCode.
  * current_revised OFFLINE-CURRENT snapshot, enabled:false, archival:true
    (annual BEA Regional benchmark revisions).
  * section 22.4 land-only: derives NOTHING -- every published LineCode landed
    raw. WE author no composite and compute nothing.
  * publisher '(NA)'/'(D)' lands value_status=unavailable, never dropped (19.4).
  * OUTPUT-axis content: CH-R122 found the labor/output cluster mutually
    redundant in real time; SAGDP is ranked BELOW housing/income and is NOT
    off-axis breadth. Admission to any channel/member/weight DEFERRED
    (section 22.2 universe open).
  * Rights: BEA public, cite BEA.

produce = NO store write. Stages drafts only. bh commit-staged is the one
config/store writer.
"""
import json
import sys
from pathlib import Path

REPO = Path("/Users/anthonyhall/Projects/bristow-hall/repo")
sys.path.insert(0, str(REPO))

ENDPOINT = "https://apps.bea.gov/regional/zip/SAGDP.zip"

LABEL_BAR = (
    "[OFFLINE-CURRENT frozen snapshot; B-GEO-LAND-4 BEA Regional %s %s "
    "cross-section (ANNUAL 1997-2025), section 3.1 distinct source; "
    "current_revised; OUTPUT-axis (CH-R122 labor/output redundant in real "
    "time); NOT admitted to any channel and sets no weight per section 22.4]"
)


def _spec(source_id, table, geography_type, geo_label):
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
            "BEA Regional %s state annual GDP, %s " % (table, geo_label)
            + LABEL_BAR % (table, geography_type)
        ),
        "max_bytes": 12000000,
        "method_version": "bea_regional_%s_current.v1" % table.lower(),
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
            "series_id_prefix": "BEA.%s" % table,
            "table": table,
        },
        "source_id": source_id,
        "value_status": "actual",
    }


SPECS = [
    _spec("bea_sagdp1_national_current_offline", "SAGDP1", "national_us",
          "U.S. aggregate"),
    _spec("bea_sagdp1_bearegion_current_offline", "SAGDP1", "bea_region",
          "8 BEA regions"),
    _spec("bea_sagdp1_state_current_offline", "SAGDP1", "state_or_dc",
          "50 states + DC"),
    _spec("bea_sagdp2_national_current_offline", "SAGDP2", "national_us",
          "U.S. aggregate"),
    _spec("bea_sagdp2_bearegion_current_offline", "SAGDP2", "bea_region",
          "8 BEA regions"),
    _spec("bea_sagdp2_state_current_offline", "SAGDP2", "state_or_dc",
          "50 states + DC"),
]


def main():
    from bh import produce as bhp
    out = REPO / "research/geo_land_4/specs.v1.json"
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
