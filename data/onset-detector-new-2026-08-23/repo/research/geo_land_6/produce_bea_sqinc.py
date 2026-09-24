"""B-GEO-LAND-6 producer: stage BEA Regional SQINC state QUARTERLY personal income.

Route PROVEN by B-GEO-MAP-1948, re-verified byte-exact at fetch this batch:
SQINC.zip 18,134,176 B, application/x-zip-compressed,
sha256 62f5b13556bda989ce9fbe5e8ddc70427276a09209ad7aee27737988f56fe9e6.
The zip carries 13 TABLE__ALL_AREAS quarterly tables (enumerated to
zip_enumeration.json). SQINC1__ALL_AREAS_1948_2026.csv spans 1948:Q1..2026:Q1 —
the EARLIEST quarterly geo lane in the set.

Shared adapter bea_regional_cainc_zip REUSED (§24.7 one value one home). This
batch EXTENDED it (TDD, RED->GREEN) to canonicalize quarterly "YYYY:Qn" columns
to the project "YYYY-Qn" period (parse_bea_api convention), leaving annual
landing unchanged; a header mixing the two is rejected. Each (table,
geography_type) present is a distinct source (§3.1); series_id =
BEA.{table}.{GeoFIPS}.L{LineCode}. current_revised OFFLINE-CURRENT, enabled:false,
archival:true. §22.4 derives NOTHING; publisher (NA)/(D) land
value_status=unavailable, never dropped (§19.4). Income axis is OFF the redundant
labor/output cluster (CH-R122); revised data-time SANCTIONED for site MAP /
DAMAGE INDEX only (OWNER_RULING REVISED_PANEL_USES), BARRED from any
as-of/real-time claim (no vintage lane) — recorded on every label.

SCOPE: SQINC1 only (brief-named table; the 1948:Q1 lane). The other 12 SQINC
tables (17,640 series / 2,492,580 records) are DEFERRED with exact counts in the
receipt (§19.4 non-silent), shelved not deleted (Wave 14), landable once the OPEN
boot-budget REGRESSION is cleared by director/infra. Decision applies the
standing owner DELEGATION (2026-08-08) + the B-GEO-LAND-5 director precedent
(answer 20260809T184618Z): brief-named minimum, stay inside the boot-budget noise
band, never self-authorize a boot-budget decision.

produce = NO store write. Stages drafts only. bh commit-staged is the one writer.
"""
import json
import sys
from pathlib import Path

REPO = Path("/Users/anthonyhall/Projects/bristow-hall/repo")
sys.path.insert(0, str(REPO))

ENDPOINT = "https://apps.bea.gov/regional/zip/SQINC.zip"
ENUM = json.loads((REPO / "research/geo_land_6/zip_enumeration.json").read_text())

TABLE_DESC = {"SQINC1": "personal income summary"}
GEO_LABEL = {
    "national_us": "U.S. aggregate",
    "bea_region": "8 BEA regions",
    "state_or_dc": "50 states + DC",
}
SELECTED_TABLES = ["SQINC1"]

LABEL_BAR = (
    "[OFFLINE-CURRENT frozen snapshot; B-GEO-LAND-6 BEA Regional %s %s "
    "cross-section (QUARTERLY %s..%s), section 3.1 distinct source; "
    "current_revised; INCOME-axis off the CH-R122 labor/output cluster; revised "
    "data-time sanctioned for MAP/DAMAGE INDEX only, BARRED from as-of/real-time "
    "(no vintage lane); NOT admitted to any channel and sets no weight per "
    "section 22.4]"
)


def _tables_by_name():
    return {t["table"]: t for t in ENUM["tables"]}


def _geo_slug(geo_type):
    return {"national_us": "national", "bea_region": "bearegion",
            "state_or_dc": "state"}[geo_type]


def _spec(table, geo_type, span):
    source_id = "bea_%s_%s_current_offline" % (table.lower(), _geo_slug(geo_type))
    return {
        "adapter": "bea_regional_cainc_zip",
        "allowed_hosts": ["apps.bea.gov"],
        "archival": True,
        "coverage_source_ids": ["bea_regional"],
        "enabled": False,
        "endpoint": ENDPOINT,
        "expected_content_types": [
            "application/x-zip-compressed", "application/zip",
        ],
        "frequency": "quarterly",
        "information_set_mode": "current_revised",
        "label": (
            "BEA Regional %s %s, %s " % (
                table, TABLE_DESC.get(table, "state quarterly income"),
                GEO_LABEL[geo_type])
            + LABEL_BAR % (table, geo_type, span[0], span[1])
        ),
        "max_bytes": 19000000,
        "method_version": "bea_regional_%s_current.v1" % table.lower(),
        "poll_seconds": 86400,
        "publisher": "U.S. Bureau of Economic Analysis",
        "publisher_release_clock": (
            "quarterly BEA Regional benchmark release; reference quarter, "
            "release, revision, retrieval, and validation clocks remain separate "
            "and exact time is null unless directly proven"
        ),
        "rights_status": "public_government_source_with_attribution",
        "secret_env": None,
        "secret_required": False,
        "series": {
            "geography_type": geo_type,
            "series_id_prefix": "BEA.%s" % table,
            "table": table,
        },
        "source_id": source_id,
        "value_status": "actual",
    }


def build_specs(selected):
    by = _tables_by_name()
    specs = []
    for table in selected:
        meta = by[table]
        span = meta["span"]
        for geo_type in ("national_us", "bea_region", "state_or_dc"):
            if meta["geo_series"].get(geo_type, 0) > 0:
                specs.append(_spec(table, geo_type, span))
    return specs


def main():
    selected = SELECTED_TABLES
    if len(sys.argv) > 1:
        selected = sys.argv[1].split(",")
    specs = build_specs(selected)
    out = REPO / "research/geo_land_6/specs.v1.json"
    out.write_text(json.dumps(specs, indent=1, sort_keys=True))
    print("selected_tables=%s sources=%d -> %s"
          % (",".join(selected), len(specs), out))
    from bh import produce as bhp
    for spec in specs:
        drafts = bhp.run_produce(REPO, spec["source_id"], source_specs=[spec])
        for d in drafts:
            print("produced %s %d bytes sha %s"
                  % (d["source_id"], d["payload"]["byte_length"],
                     d["payload"]["sha256"][:12]))
    print("STAGED; store/config/receipts untouched")


if __name__ == "__main__":
    main()
