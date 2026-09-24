"""B-GEO-LAND-5 producer: stage BEA Regional SAINC state annual personal income.

Route PROVEN by B-GEO-MAP-1948, re-verified byte-exact at fetch this batch:
SAINC.zip 17,478,048 B, application/x-zip-compressed,
sha256 339a3d3d6a283eea3f5647ea5b33570da73801d4248c5e2209c1e196428d9a9a.
The zip carries 19 TABLE__ALL_AREAS tables (enumerated to zip_enumeration.json).

Shared adapter bea_regional_cainc_zip REUSED UNCHANGED (§24.7 one-value-one-home);
it already selects the ALL_AREAS member matching series.table and classifies each
GeoFIPS into national_us / bea_region / state_or_dc / county. SAINC is state-level:
no county rows. Each (table, geography_type) present is a distinct source (§3.1);
series_id = BEA.{table}.{GeoFIPS}.L{LineCode}. current_revised OFFLINE-CURRENT,
enabled:false, archival:true. §22.4 derives NOTHING; publisher (NA)/(D) land
value_status=unavailable, never dropped (§19.4). Income axis is OFF the redundant
labor/output cluster (CH-R122); revised data-time SANCTIONED for site MAP / DAMAGE
INDEX only (OWNER_RULING REVISED_PANEL_USES), BARRED from any as-of/real-time claim
(no vintage lane) — recorded on every label.

SELECTED_TABLES is set from the director ruling on question
_mailbox/questions/20260809T184618Z_B-GEO-LAND-5.md. Deferred tables are recorded
in the receipt with exact series counts (§19.4 non-silent), NOT dropped.

produce = NO store write. Stages drafts only. bh commit-staged is the one writer.
"""
import json
import sys
from pathlib import Path

REPO = Path("/Users/anthonyhall/Projects/bristow-hall/repo")
sys.path.insert(0, str(REPO))

ENDPOINT = "https://apps.bea.gov/regional/zip/SAINC.zip"
ENUM = json.loads((REPO / "research/geo_land_5/zip_enumeration.json").read_text())

# Human labels per table (BEA Regional SAINC family).
TABLE_DESC = {
    "SAINC1": "personal income summary",
    "SAINC4": "per-capita personal income",
    "SAINC30": "economic profile",
    "SAINC11": "personal income by major component",
    "SAINC12": "personal income (BEA benchmark)",
    "SAINC35": "personal current transfer receipts",
    "SAINC40": "property income",
    "SAINC50": "personal current transfer receipts detail",
    "SAINC51": "disposable personal income",
    "SAINC70": "wages and salaries by place of work",
    "SAINC91": "gross flow of earnings",
    "SAINC5H": "earnings by industry, historical 1929-1957",
    "SAINC7H": "wage and salary employment by industry, historical",
    "SAINC5N": "earnings by industry (NAICS)",
    "SAINC5S": "earnings by industry (SIC)",
    "SAINC6N": "compensation by industry (NAICS)",
    "SAINC6S": "compensation by industry (SIC)",
    "SAINC7N": "wage and salary employment by industry (NAICS)",
    "SAINC7S": "wage and salary employment by industry (SIC)",
}

GEO_LABEL = {
    "national_us": "U.S. aggregate",
    "bea_region": "8 BEA regions",
    "state_or_dc": "50 states + DC",
}

# Set by ruling. Default = Option 2 (brief-named minimum).
SELECTED_TABLES = ["SAINC1", "SAINC4", "SAINC30"]

LABEL_BAR = (
    "[OFFLINE-CURRENT frozen snapshot; B-GEO-LAND-5 BEA Regional %s %s "
    "cross-section (ANNUAL %s-%s), section 3.1 distinct source; current_revised; "
    "INCOME-axis off the CH-R122 labor/output cluster; revised data-time sanctioned "
    "for MAP/DAMAGE INDEX only, BARRED from as-of/real-time (no vintage lane); "
    "NOT admitted to any channel and sets no weight per section 22.4]"
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
        "frequency": "annual",
        "information_set_mode": "current_revised",
        "label": (
            "BEA Regional %s %s, %s " % (
                table, TABLE_DESC.get(table, "state annual income"),
                GEO_LABEL[geo_type])
            + LABEL_BAR % (table, geo_type, span[0], span[1])
        ),
        "max_bytes": 19000000,
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
        span = meta["year_span"]
        for geo_type in ("national_us", "bea_region", "state_or_dc"):
            if meta["geo_rowcounts"].get(geo_type, 0) > 0:
                specs.append(_spec(table, geo_type, span))
    return specs


def main():
    selected = SELECTED_TABLES
    if len(sys.argv) > 1:
        selected = sys.argv[1].split(",")
    specs = build_specs(selected)
    out = REPO / "research/geo_land_5/specs.v1.json"
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
