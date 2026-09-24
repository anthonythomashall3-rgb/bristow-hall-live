"""B-RESV-PROVEN probe — read-only network fetch + measure for the 7 reservation
instances that carry a concrete verified route on a proven adapter. Zero writes
to the store; bytes cached under research/prefetch/bresv for the land step.
Key read via engine (never shell env, never written to disk); url redacts <KEY>.
"""
import hashlib
import json
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, ".")
from tools.rmv2_data_cloudflare.rmv2_connectors import engine

OUT = Path("research/prefetch/bresv")
OUT.mkdir(parents=True, exist_ok=True)


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _get(url, ua="rmv2-bresv/1.0"):
    req = urllib.request.Request(url, headers={"User-Agent": ua})
    with urllib.request.urlopen(req, timeout=90) as r:
        return r.getcode(), r.read()


# instance -> (adapter, url_builder(key)->(url, redacted_url), auth_env or None)
FRED = engine._read_credential("FRED_API_KEY")
CENSUS = engine._read_credential("CENSUS_API_KEY")
EIA = engine._read_credential("EIA_API_KEY")

INSTANCES = {
    "fred_current_api": {
        "adapter": "fred_json_api",
        "url": "https://api.stlouisfed.org/fred/series/observations?series_id=RECPROUSM156N&file_type=json&observation_start=1967-06-01&api_key=%s" % FRED,
        "meta": "https://api.stlouisfed.org/fred/series?series_id=RECPROUSM156N&file_type=json&api_key=%s" % FRED,
        "auth": "FRED_API_KEY", "key": FRED,
    },
    "census_economic_indicators_current_api": {
        "adapter": "census_api",
        "url": "https://api.census.gov/data/timeseries/eits/mwtsadv?get=cell_value,category_code,data_type_code,seasonally_adj,geo_level_code,time_slot_id&time=from+2024&key=%s" % CENSUS,
        "auth": "CENSUS_API_KEY", "key": CENSUS,
    },
    "census_acs": {
        "adapter": "census_api",
        "url": "https://api.census.gov/data/2024/acs/acs1?get=NAME,B01003_001E,B23025_005E,B17001_002E&for=state:*&key=%s" % CENSUS,
        "auth": "CENSUS_API_KEY", "key": CENSUS,
    },
    "census_saipe": {
        "adapter": "census_api",
        "url": "https://api.census.gov/data/timeseries/poverty/saipe?get=NAME,SAEPOVALL_PT,SAEPOVRTALL_PT,SAEMHI_PT&for=state:*&time=2024&key=%s" % CENSUS,
        "auth": "CENSUS_API_KEY", "key": CENSUS,
    },
    "census_qwi": {
        "adapter": "census_api",
        "url": "https://api.census.gov/data/timeseries/qwi/sa?get=Emp,FrmJbGn,FrmJbLs,EarnS&for=state:06&year=2024&quarter=1&key=%s" % CENSUS,
        "auth": "CENSUS_API_KEY", "key": CENSUS,
    },
    "eia_current_api": {
        "adapter": "eia_v2_json",
        "url": "https://api.eia.gov/v2/electricity/retail-sales/data/?frequency=monthly&data[0]=sales&data[1]=revenue&data[2]=price&facets[stateid][]=US&facets[sectorid][]=ALL&sort[0][column]=period&sort[0][direction]=desc&offset=0&length=5000&api_key=%s" % EIA,
        "auth": "EIA_API_KEY", "key": EIA,
    },
    "bts_tsi": {
        "adapter": "socrata_json",
        "url": "https://data.bts.gov/resource/bw6n-ddqk.json?$limit=50000",
        "auth": None, "key": None,
    },
}


def _redact(url, key):
    return url.replace(key, "<KEY>") if key else url


def main():
    man = []
    for name, spec in INSTANCES.items():
        rec = {"instance": name, "adapter": spec["adapter"], "auth_env": spec["auth"],
               "fetch_utc": _now()}
        try:
            code, body = _get(spec["url"])
            sha = hashlib.sha256(body).hexdigest()
            (OUT / (name + ".body")).write_bytes(body)
            rec.update(http=code, bytes=len(body), sha256=sha,
                       url=_redact(spec["url"], spec["key"]),
                       head=body[:180].decode("utf-8", "replace"))
            if spec.get("meta"):
                mc, mb = _get(spec["meta"])
                (OUT / (name + ".meta.json")).write_bytes(mb)
                rec["meta_http"] = mc
        except urllib.error.HTTPError as e:
            rec.update(http=e.code, error="HTTPError", detail=e.read()[:200].decode("utf-8", "replace"))
        except Exception as e:
            rec.update(error=type(e).__name__, detail=str(e)[:200])
        man.append(rec)
        print(name, rec.get("http"), rec.get("bytes"), rec.get("error", ""))
    json.dump(man, open(OUT / "manifest.json", "w"), indent=1)
    print("MANIFEST", OUT / "manifest.json")


main()
