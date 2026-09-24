"""B-GEO-LAND-7 producer: stage BEA Regional SQGDP1 state QUARTERLY GDP.

Route PROVEN by B-GEO-MAP-1948, re-verified byte-exact at fetch this batch:
SQGDP.zip 3,639,953 B, application/x-zip-compressed, 255 table files,
sha256 d16ce7d14c6b... (route_verify.json). The zip carries 5 TABLE__ALL_AREAS
quarterly tables (SQGDP1/SQGDP2/SQGDP8/SQGDP9/SQGDP11, enumerated to
zip_enumeration.json). SQGDP1__ALL_AREAS_2005_2026.csv spans 2005:Q1..2026:Q1 —
the brief-named lane. NEW lane, distinct from the landed ANNUAL SAGDP
(B-GEO-LAND-4).

Shared adapter bea_regional_cainc_zip REUSED (§24.7 one value one home); the
quarterly "YYYY:Qn" -> project "YYYY-Qn" canonicalization already landed under
B-GEO-LAND-6 (TDD). NO adapter change this batch. Each (table, geography_type)
present is a distinct source (§3.1); series_id = BEA.{table}.{GeoFIPS}.L{LineCode}.
current_revised OFFLINE-CURRENT, enabled:false, archival:true. §22.4 derives
NOTHING; publisher (NA)/(D) land value_status=unavailable, never dropped (§19.4).
OUTPUT axis; revised data-time SANCTIONED for site MAP / DAMAGE INDEX only
(OWNER_RULING REVISED_PANEL_USES), BARRED from any as-of/real-time claim (no
vintage lane) — recorded on every label.

SCOPE: SQGDP1 only (brief-named table). The other 4 SQGDP tables
(SQGDP2/SQGDP8/SQGDP9/SQGDP11 = 6,482 state-geo series) are DEFERRED with exact
counts in deferred_tables.v1.json (§19.4 non-silent), shelved not deleted
(Wave 14), landable once the OPEN boot-budget REGRESSION is cleared by
director/infra. Decision applies the standing owner DELEGATION (2026-08-08) + the
B-GEO-LAND-5/6 director precedent: brief-named minimum, stay inside the
boot-budget noise band, never self-authorize a boot-budget decision.

produce = NO store write. Stages drafts only. bh commit-staged is the one writer.
"""
import json
import sys
from pathlib import Path

REPO = Path("/Users/anthonyhall/Projects/bristow-hall/repo")
sys.path.insert(0, str(REPO))

ENDPOINT = "https://apps.bea.gov/regional/zip/SQGDP.zip"
ENUM = json.loads((REPO / "research/geo_land_7/zip_enumeration.json").read_text())

TABLE_DESC = {"SQGDP1": "gross domestic product (GDP) summary"}
GEO_LABEL = {
    "national_us": "U.S. aggregate",
    "bea_region": "8 BEA regions",
    "state_or_dc": "50 states + DC",
}
SELECTED_TABLES = ["SQGDP1"]

LABEL_BAR = (
    "[OFFLINE-CURRENT frozen snapshot; B-GEO-LAND-7 BEA Regional %s %s "
    "cross-section (QUARTERLY %s..%s), section 3.1 distinct source; "
    "current_revised; OUTPUT-axis (lower priority than income/off-axis); revised "
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
                table, TABLE_DESC.get(table, "state quarterly GDP"),
                GEO_LABEL[geo_type])
            + LABEL_BAR % (table, geo_type, span[0], span[1])
        ),
        "max_bytes": 5000000,
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


def build_deferred():
    by = _tables_by_name()
    deferred = {}
    total_series = 0
    total_records_est = 0
    for t in ENUM["tables"]:
        if t["table"] in SELECTED_TABLES:
            continue
        s = t["series_ex_other_ex_county"]
        r = t["records_est_state_geo"]
        deferred[t["table"]] = {"state_geo_series": s, "records_est": r,
                                "span": t["span"], "periods": t["periods"]}
        total_series += s
        total_records_est += r
    return {
        "note": "4 SQGDP tables DEFERRED per the OPEN boot-budget REGRESSION "
                "blocker + standing owner delegation + B-GEO-LAND-5/6 precedent. "
                "NOT dropped, NOT silently capped (section 19.4); recorded with "
                "exact measured state-geo series counts. Shelved not deleted "
                "(Wave 14). Land once boot-budget REGRESSION cleared by "
                "director/infra (same proven route, unchanged adapter).",
        "deferred_series_total": total_series,
        "deferred_records_est_total": total_records_est,
        "tables": deferred,
        "reconciliation": "landed SQGDP1 %d + deferred %d = %d total SQGDP.zip "
        "state-geo series across all 5 ALL_AREAS tables."
        % (by["SQGDP1"]["series_ex_other_ex_county"], total_series,
           by["SQGDP1"]["series_ex_other_ex_county"] + total_series),
    }


def main():
    selected = SELECTED_TABLES
    if len(sys.argv) > 1:
        selected = sys.argv[1].split(",")
    specs = build_specs(selected)
    out = REPO / "research/geo_land_7/specs.v1.json"
    out.write_text(json.dumps(specs, indent=1, sort_keys=True))
    (REPO / "research/geo_land_7/deferred_tables.v1.json").write_text(
        json.dumps(build_deferred(), indent=1))
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
