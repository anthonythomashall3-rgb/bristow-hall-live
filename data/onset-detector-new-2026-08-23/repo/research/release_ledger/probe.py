import sys, json, time, csv, urllib.request, urllib.error, os

KEY = sys.argv[1]
OUT = "research/release_ledger"
BASE = "https://api.stlouisfed.org/fred"
FULL = "realtime_start=1776-07-04&realtime_end=9999-12-31"

def get(path):
    url = f"{BASE}/{path}&api_key={KEY}&file_type=json"
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(2); continue
            return {"__error__": f"HTTP {e.code}"}
        except Exception as e:
            if attempt < 3:
                time.sleep(1); continue
            return {"__error__": f"{type(e).__name__}"}
    return {"__error__": "retries_exhausted"}

# 1. all releases, full realtime window (397) -> lineage rows
rel = get(f"releases?{FULL}&limit=1000")
releases = rel.get("releases", [])
json.dump(rel, open(f"{OUT}/releases_full.json","w"), indent=0)
# id -> latest realtime row; also count succeeded (realtime_end != 9999)
rel_by_id = {}
succeeded = []
for r in releases:
    rel_by_id[r["id"]] = r
    if r.get("realtime_end","9999-12-31") != "9999-12-31":
        succeeded.append(r)
print(f"releases={len(releases)} distinct_ids={len(rel_by_id)} succeeded_rows={len(succeeded)}")

# 2. catalogue 268
rows = list(csv.DictReader(open("data_vault/catalog/metric_catalog.csv")))
print(f"catalogue rows={len(rows)}")
# provider distribution
from collections import Counter
prov = Counter(r["provider"] for r in rows)
print("provider dist:", dict(prov))

# 3. per-series governing release (only where provider gives a FRED-resolvable id)
mapping = {}
n = 0
for r in rows:
    sid = r["provider_series_id"] or r["series_id"]
    prov_r = r["provider"]
    if prov_r != "fred":
        mapping[r["series_id"]] = {"provider": prov_r, "release": None, "note": "non_fred_provider_no_series_release_query"}
        continue
    res = get(f"series/release?series_id={sid}")
    if "__error__" in res:
        mapping[r["series_id"]] = {"provider": prov_r, "sid": sid, "release": None, "note": res["__error__"]}
    else:
        rl = res.get("releases", [])
        if rl:
            mapping[r["series_id"]] = {"provider": prov_r, "sid": sid, "release_id": rl[0]["id"], "release_name": rl[0]["name"]}
        else:
            mapping[r["series_id"]] = {"provider": prov_r, "sid": sid, "release": None, "note": "no_release_returned"}
    n += 1
    if n % 50 == 0:
        print(f"  ...{n} series queried")
json.dump(mapping, open(f"{OUT}/series_release_map.json","w"), indent=0)

covered = [k for k,v in mapping.items() if v.get("release_id")]
uncovered = [k for k,v in mapping.items() if not v.get("release_id")]
print(f"COVERAGE: {len(covered)}/{len(rows)} metrics gain a release lineage; {len(uncovered)} do not")
# uncovered reasons
reasons = Counter(v.get("note","?") for k,v in mapping.items() if not v.get("release_id"))
print("uncovered reasons:", dict(reasons))
# distinct releases governing our metrics
gov_ids = sorted(set(v["release_id"] for v in mapping.values() if v.get("release_id")))
print(f"distinct governing releases among 268: {len(gov_ids)}")

# 4. 17 headline members
HEAD = {
 "ICSA":"ICSA","IURSA":"IURSA","SAHM":"SAHMREALTIME","UNRATEv":"UNRATE",
 "INDPRO":"INDPRO","CMRMT":"CMRMTSPL","TCU":"TCU","PHILLY":"GACDFSA066MSFRBPHI",
 "NASDAQ":"NASDAQCOM","BAAAAA":"BAAAAA","BAA10Y":"BAA10Y","VIX":"VIXCLS",
 "NFCI":"NFCI","PERMIT":"PERMIT","HOUST":"HOUST","UMCSENT":"UMCSENT","W875":"W875RX1",
}
head_out = {}
for member, sid in HEAD.items():
    res = get(f"series/release?series_id={sid}")
    if "__error__" in res or not res.get("releases"):
        head_out[member] = {"sid": sid, "error": res.get("__error__","no_release")}
        continue
    rl = res["releases"][0]
    rid = rl["id"]
    # release dates: first/last actual release event dates
    dts = get(f"release/dates?release_id={rid}&{FULL}&include_release_dates_with_no_data=false&sort_order=asc&limit=100000")
    dd = [x["date"] for x in dts.get("release_dates",[])] if "__error__" not in dts else []
    # succession: all release rows (realtime spans) for this release id
    succ = rel_by_id.get(rid, {})
    head_out[member] = {
        "sid": sid, "release_id": rid, "release_name": rl["name"],
        "release_realtime_start": succ.get("realtime_start"), "release_realtime_end": succ.get("realtime_end"),
        "n_release_dates": len(dd),
        "first_release_date": dd[0] if dd else None,
        "last_release_date": dd[-1] if dd else None,
    }
json.dump(head_out, open(f"{OUT}/headline_releases.json","w"), indent=1)
print("=== headline (member sid release_id first_rel last_rel n) ===")
for m,v in head_out.items():
    print(f"{m:8} {v.get('sid'):18} rid={v.get('release_id')} {str(v.get('first_release_date')):12} {str(v.get('last_release_date')):12} n={v.get('n_release_dates')} :: {v.get('release_name','')[:40]}{' ERR='+v['error'] if 'error' in v else ''}")

# 5. cross-check vs CH-R106 corpus 15 series
r106 = ["CMRMTSPL","GACDFSA066MSFRBPHI","GDPC1","HOUST","ICSA","INDPRO","IURSA","NFCI","PAYEMS","PERMIT","SAHMREALTIME","TCU","UMCSENT","UNRATE","W875RX1"]
xcheck = {}
for sid in r106:
    res = get(f"series/release?series_id={sid}")
    rl = res.get("releases",[{}])
    xcheck[sid] = {"release_id": rl[0].get("id") if rl else None, "release_name": rl[0].get("name") if rl else None}
json.dump(xcheck, open(f"{OUT}/ch_r106_crosscheck.json","w"), indent=1)
print("wrote all outputs")
