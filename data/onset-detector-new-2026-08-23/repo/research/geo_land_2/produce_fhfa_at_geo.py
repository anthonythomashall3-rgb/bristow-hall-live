"""B-GEO-LAND-2 producer: stage FHFA all-transactions HPI, state + metro.

Two publisher-direct quarterly datasets (route-proof research/geo_expand/
ROUTE_PROOFS.v1.json, re-verified at fetch this batch: state 187060 B, metro
4165719 B -- byte-exact matches):
  * hpi_at_state.csv  -> fhfa_hpi_at_state_current_offline  (51 places, 1 series each)
  * hpi_at_metro.csv  -> fhfa_hpi_at_metro_current_offline  (410 CBSAs, index + rstderr)

Constraints honored:
  * new adapter fhfa_hpi_at_geo_csv (headerless state/metro layouts) -- the
    existing fhfa_hpi_csv adapter is hard-filtered to national monthly USA rows
    and cannot read these files.
  * each geography = its own series (section 3.1); each FILE = its own source id;
    state and metro are distinct geo cross-sections (never merged/aliased).
  * current_revised OFFLINE-CURRENT snapshot, enabled:false, archival:true.
  * section 22.4 land-only: derives NOTHING -- the all-transactions index is
    publisher output landed raw; the metro standard error is landed as its own
    RSTDERR series, unstripped-parens normalized to the publisher decimal.
  * OFF-AXIS housing content (CH-R122 labor/output redundancy); admission to any
    channel/member/weight DEFERRED (section 22.2 universe not closed).

produce = NO store write. Stages drafts only.
"""
import json
import sys
from pathlib import Path

REPO = Path("/Users/anthonyhall/Projects/bristow-hall/repo")
sys.path.insert(0, str(REPO))

LABEL_BAR = (
    "[OFFLINE-CURRENT frozen snapshot; B-GEO-LAND-2 FHFA all-transactions HPI "
    "%s cross-section (quarterly), section 3.1 distinct source; current_revised; "
    "OFF-AXIS housing (CH-R122); NOT admitted to any channel and sets no weight "
    "per section 22.4]"
)

SPECS = [
    {
        "adapter": "fhfa_hpi_at_geo_csv",
        "allowed_hosts": ["www.fhfa.gov"],
        "archival": True,
        "coverage_source_ids": ["fhfa_hpi"],
        "enabled": False,
        "endpoint": (
            "https://www.fhfa.gov/hpi/download/quarterly_datasets/"
            "hpi_at_state.csv"
        ),
        "expected_content_types": ["text/csv"],
        "frequency": "quarterly",
        "information_set_mode": "current_revised",
        "label": (
            "FHFA all-transactions House Price Index, 50 states + DC (quarterly) "
            + LABEL_BAR % "state"
        ),
        "max_bytes": 4000000,
        "method_version": "fhfa_hpi_at_state_current.v1",
        "poll_seconds": 21600,
        "publisher": "Federal Housing Finance Agency",
        "publisher_release_clock": (
            "quarterly HPI release on the FHFA calendar; reference quarter, "
            "release, revision, retrieval, and validation clocks remain separate "
            "and exact time is null unless directly proven"
        ),
        "rights_status": "public_government_index_output_with_attribution",
        "secret_env": None,
        "secret_required": False,
        "series": {
            "layout": "state",
            "geography_type": "state_or_dc",
            "index_semantics": "all_transactions_purchase_and_refinance",
            "series_id_prefix": "FHFA.HPI.AT.STATE",
            "index_unit": "index",
        },
        "source_id": "fhfa_hpi_at_state_current_offline",
        "value_status": "actual",
    },
    {
        "adapter": "fhfa_hpi_at_geo_csv",
        "allowed_hosts": ["www.fhfa.gov"],
        "archival": True,
        "coverage_source_ids": ["fhfa_hpi"],
        "enabled": False,
        "endpoint": (
            "https://www.fhfa.gov/hpi/download/quarterly_datasets/"
            "hpi_at_metro.csv"
        ),
        "expected_content_types": ["text/csv"],
        "frequency": "quarterly",
        "information_set_mode": "current_revised",
        "label": (
            "FHFA all-transactions House Price Index, CBSA metro (quarterly) "
            + LABEL_BAR % "metro"
        ),
        "max_bytes": 8000000,
        "method_version": "fhfa_hpi_at_metro_current.v1",
        "poll_seconds": 21600,
        "publisher": "Federal Housing Finance Agency",
        "publisher_release_clock": (
            "quarterly HPI release on the FHFA calendar; reference quarter, "
            "release, revision, retrieval, and validation clocks remain separate "
            "and exact time is null unless directly proven"
        ),
        "rights_status": "public_government_index_output_with_attribution",
        "secret_env": None,
        "secret_required": False,
        "series": {
            "layout": "metro",
            "geography_type": "cbsa_metro",
            "index_semantics": "all_transactions_purchase_and_refinance",
            "series_id_prefix": "FHFA.HPI.AT.METRO",
            "index_unit": "index",
            "stderr_unit": "index standard error",
        },
        "source_id": "fhfa_hpi_at_metro_current_offline",
        "value_status": "actual",
    },
]


def main():
    from bh import produce as bhp
    out = REPO / "research/geo_land_2/specs.v1.json"
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
