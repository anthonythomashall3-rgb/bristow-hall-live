import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {
    "census_acs": (
        "https://api.census.gov/data/2024/acs/acs1?get=NAME,B01003_001E,B23025_005E,B17001_002E&for=state:*",
        ["census_acs"],
        "CENSUS_API",
    ),
    "census_saipe": (
        "https://api.census.gov/data/timeseries/poverty/saipe?get=NAME,SAEPOVALL_PT,SAEPOVRTALL_PT,SAEMHI_PT&for=state:*&time=2024",
        ["census_saipe"],
        "CENSUS_API",
    ),
    "census_qwi": (
        "https://api.census.gov/data/timeseries/qwi/sa?get=Emp,FrmJbGn,FrmJbLs,EarnS&for=state:06&year=2024&quarter=1",
        ["census_qwi"],
        "CENSUS_API",
    ),
    "census_economic_indicators_current_api": (
        "https://api.census.gov/data/timeseries/eits/mwtsadv?get=cell_value,category_code,data_type_code,seasonally_adj,geo_level_code,time_slot_id&time=from+2024",
        ["census_mtis_mwts"],
        "CENSUS_API",
    ),
    "eia_current_api": (
        "https://api.eia.gov/v2/electricity/retail-sales/data/?frequency=monthly&data[0]=sales&data[1]=revenue&data[2]=price&facets[stateid][]=US&facets[sectorid][]=ALL&sort[0][column]=period&sort[0][direction]=desc&offset=0&length=5000",
        ["eia_electricity"],
        "EIA_V2_JSON",
    ),
    "fred_current_api": (
        "https://api.stlouisfed.org/fred/series/observations?series_id=RECPROUSM156N&file_type=json&observation_start=1967-06-01",
        ["fred_current_provider"],
        "FRED_JSON_API",
    ),
    "eia_930": (
        "https://api.eia.gov/v2/electricity/rto/daily-region-data/data/?frequency=daily&data[0]=value&facets[respondent][]=US48&facets[type][]=D&facets[type][]=DF&facets[type][]=NG&facets[type][]=TI&facets[timezone][]=Eastern&sort[0][column]=period&sort[0][direction]=desc&length=5000",
        ["eia_930"],
        "EIA_V2_JSON",
    ),
}


def test_credential_cleared_reservations_have_concrete_reviewed_routes():
    document = json.loads(
        (ROOT / "live_data/config/planned_sources.v1.json").read_text()
    )
    planned = {row["source_id"]: row for row in document["sources"]}
    for source_id, (endpoint, families, adapter) in EXPECTED.items():
        row = planned[source_id]
        assert row["endpoint"] == endpoint
        assert row["coverage_source_family_ids"] == families
        assert adapter in row["endpoint_status"]
        assert "key=" not in row["endpoint"].lower()
        assert row["enabled"] is False
