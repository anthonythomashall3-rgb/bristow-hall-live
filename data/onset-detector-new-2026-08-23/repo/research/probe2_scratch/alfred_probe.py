"""B-PROBE-2 §1 ALFRED depth probe. Read-only GETs to FRED/ALFRED vintagedates.
Writes research/probe2_scratch/alfred_depth.json. No store write, no admission."""
import json, time, urllib.request, urllib.error, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.rmv2_data_cloudflare.rmv2_connectors import engine

KEY = engine._read_credential("FRED_API_KEY")
assert KEY, "no FRED key"

# 15 pinned vintage bases = existing_vintage_bases (superset of 7 B-LAND-2 families
# and of every FRED-backed coverage-manifest member; 4 market members have no ALFRED base).
SERIES = ["CMRMTSPL","GACDFSA066MSFRBPHI","GDPC1","HOUST","ICSA","INDPRO","IURSA",
          "NFCI","PAYEMS","PERMIT","SAHMREALTIME","TCU","UMCSENT","UNRATE","W875RX1"]

PIN = "2020-01-01"

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent":"rmv2-probe/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.status, r.read()

out = {}
for s in SERIES:
    url = (f"https://api.stlouisfed.org/fred/series/vintagedates?series_id={s}"
           f"&api_key={KEY}&file_type=json&realtime_start=1776-07-04&limit=10000")
    rec = {"series_id": s}
    try:
        status, body = get(url)
        j = json.loads(body)
        vds = j.get("vintage_dates", [])
        rec.update({"http_status": status, "vintage_count": len(vds),
                    "alfred_floor": (vds[0] if vds else None),
                    "alfred_latest": (vds[-1] if vds else None)})
    except urllib.error.HTTPError as e:
        rec.update({"http_status": e.code, "error": e.read().decode("utf-8","replace")[:200]})
    except Exception as e:
        rec.update({"http_status": None, "error": repr(e)[:200]})
    out[s] = rec
    print(s, rec.get("http_status"), rec.get("alfred_floor"), rec.get("vintage_count"))
    time.sleep(0.4)  # politeness

Path(__file__).with_name("alfred_depth.json").write_text(json.dumps(out, indent=1)+"\n")
print("WROTE alfred_depth.json")
