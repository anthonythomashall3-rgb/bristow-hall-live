#!/usr/bin/env python3
"""CH-R37 route repair fetcher. Read-only network; caches to research/prefetch/forecasts/.
Skip-on-2-failures per route. Sha-manifests everything. Writes R37B_REPORT.json."""
import os, sys, json, hashlib, re, time, urllib.request, urllib.error

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # forecasts/
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"

def fred_key():
    p = os.path.join(BASE, "..", "..", "..", "live_data", "config", "local.env")
    for line in open(os.path.abspath(p)):
        line = line.strip()
        if line.startswith("FRED_API_KEY=") and not line.startswith("#"):
            v = line.split("=", 1)[1].strip()
            if v and v != "<SET>":
                return v
    return None

def get(url, timeout=45):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(), r.headers.get("Content-Type", ""), r.geturl()

def sha(b):
    return hashlib.sha256(b).hexdigest()

def looks_html(b):
    h = b[:512].lstrip().lower()
    return h.startswith(b"<!doctype") or h.startswith(b"<html") or b"<title>error" in h

def save(rel, b):
    fp = os.path.join(BASE, rel)
    os.makedirs(os.path.dirname(fp), exist_ok=True)
    open(fp, "wb").write(b)
    return {"path": rel, "bytes": len(b), "sha256": sha(b)}

report = {"batch": "CH-R37_FORECAST_ROUTE_REPAIR", "routes": {}}
KEY = fred_key()

def run_route(name, targets):
    """targets: list of (url, relpath, kind) ; kind in {json,binary,html}. stop after 2 fails."""
    recs, fails = [], 0
    for url, rel, kind in targets:
        if fails >= 2:
            recs.append({"url": url, "status": "SKIPPED", "reason": "2-failure cap"})
            continue
        try:
            b, ct, final = get(url)
            entry = {"url": url, "final_url": final, "content_type": ct, "bytes": len(b)}
            if kind in ("json", "binary") and looks_html(b):
                entry["status"] = "HTML"
                entry["note"] = "expected data, got HTML (gated/404/challenge)"
                fails += 1
            else:
                m = save(rel, b)
                entry.update(m)
                entry["status"] = "ok"
            recs.append(entry)
        except Exception as e:
            recs.append({"url": url, "status": "FAIL", "error": str(e)[:200]})
            fails += 1
        time.sleep(1)
    report["routes"][name] = {"records": recs}
    return recs

# ---- 1. GDPNow via FRED API (keyed) ----
g = []
if KEY:
    g = [
        (f"https://api.stlouisfed.org/fred/series/observations?series_id=GDPNOW&api_key={KEY}&file_type=json",
         "gdpnow/GDPNOW.observations.json", "json"),
        (f"https://api.stlouisfed.org/fred/series/vintagedates?series_id=GDPNOW&api_key={KEY}&file_type=json",
         "gdpnow/GDPNOW.vintagedates.json", "json"),
    ]
# one atlanta native attempt (documented xlsx)
g.append(("https://www.atlantafed.org/-/media/documents/cqer/researchcq/gdpnow/GDPTrackingModelDataAndForecasts.xlsx",
          "gdpnow/GDPTrackingModelDataAndForecasts.xlsx", "binary"))
run_route("gdpnow", g)
report["routes"]["gdpnow"]["fred_key_present"] = bool(KEY)

# ---- 2. Cleveland inflation nowcast (documented JSON endpoints) ----
cl = [(f"https://www.clevelandfed.org/-/media/files/webcharts/inflationnowcasting/nowcast_{p}.json?sc_lang=en",
       f"cleveland_nowcast/nowcast_{p}.json", "json") for p in ("month", "quarter", "year")]
# also documented xlsx download
cl.append(("https://www.clevelandfed.org/-/media/files/webcharts/inflationnowcasting/inflation-nowcast-data.xlsx",
           "cleveland_nowcast/inflation-nowcast-data.xlsx", "binary"))
run_route("cleveland_nowcast", cl)

# ---- 3. Greenbook: crawl the real page for hrefs ----
gb = {"records": [], "crawled": []}
gb_pages = [
    "https://www.philadelphiafed.org/surveys-and-data/real-time-data-research/greenbook-data-sets",
    "https://www.philadelphiafed.org/surveys-and-data/real-time-data-research/philadelphia-data-set",
]
hrefs = set()
for pg in gb_pages:
    try:
        b, ct, final = get(pg)
        save(f"greenbook/_page_{len(gb['crawled'])}.html", b)
        gb["crawled"].append({"url": pg, "final": final, "bytes": len(b), "status": "ok"})
        for m in re.findall(rb'href="([^"]+)"', b):
            h = m.decode("latin1")
            if re.search(r'greenbook|tealbook|row[_-]?output|\.xlsx|\.xls|\.zip', h, re.I):
                if h.startswith("/"):
                    h = "https://www.philadelphiafed.org" + h
                if h.startswith("http"):
                    hrefs.add(h)
    except Exception as e:
        gb["crawled"].append({"url": pg, "status": "FAIL", "error": str(e)[:200]})
gb["candidate_hrefs"] = sorted(hrefs)
# fetch data files only (xlsx/xls/zip), cap 2 failures
fails = 0
for h in sorted(hrefs):
    if not re.search(r'\.(xlsx|xls|zip)(\?|$)', h, re.I):
        continue
    if fails >= 2:
        gb["records"].append({"url": h, "status": "SKIPPED", "reason": "2-failure cap"})
        continue
    try:
        b, ct, final = get(h)
        fn = re.sub(r'[^A-Za-z0-9._-]', '_', h.split("/")[-1].split("?")[0])
        if looks_html(b):
            gb["records"].append({"url": h, "status": "HTML", "bytes": len(b)})
            fails += 1
        else:
            gb["records"].append({"url": h, **save(f"greenbook/{fn}", b), "status": "ok"})
    except Exception as e:
        gb["records"].append({"url": h, "status": "FAIL", "error": str(e)[:200]})
        fails += 1
    time.sleep(1)
report["routes"]["greenbook"] = gb

# ---- 4. FOMC SEP pre-2021: crawl calendar year pages for SEP pdf links ----
sep = {"records": [], "crawled": []}
sep_hrefs = set()
for yr in (2019, 2020):
    pg = f"https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"  # single hist page
    break
# use the historical materials page which lists per-year
for yr in range(2019, 2021):
    pg = f"https://www.federalreserve.gov/monetarypolicy/fomchistorical{yr}.htm"
    try:
        b, ct, final = get(pg)
        save(f"fomc_sep/_cal_{yr}.html", b)
        sep["crawled"].append({"url": pg, "bytes": len(b), "status": "ok"})
        for m in re.findall(rb'href="([^"]+)"', b):
            h = m.decode("latin1")
            if re.search(r'SEP.*\.pdf', h, re.I):
                if h.startswith("/"):
                    h = "https://www.federalreserve.gov" + h
                if h.startswith("http"):
                    sep_hrefs.add((yr, h))
    except Exception as e:
        sep["crawled"].append({"url": pg, "status": "FAIL", "error": str(e)[:200]})
sep["candidate_hrefs"] = sorted(h for _, h in sep_hrefs)
fails = 0
for yr, h in sorted(sep_hrefs):
    if fails >= 2:
        sep["records"].append({"url": h, "status": "SKIPPED"})
        continue
    try:
        b, ct, final = get(h)
        fn = f"{yr}_" + re.sub(r'[^A-Za-z0-9._-]', '_', h.split("/")[-1])
        if looks_html(b):
            sep["records"].append({"url": h, "status": "HTML"})
            fails += 1
        else:
            sep["records"].append({"url": h, **save(f"fomc_sep/pre2021/{fn}", b), "status": "ok"})
    except Exception as e:
        sep["records"].append({"url": h, "status": "FAIL", "error": str(e)[:200]})
        fails += 1
    time.sleep(1)
report["routes"]["fomc_sep"] = sep

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "R37B_REPORT.json")
json.dump(report, open(out, "w"), indent=2)
print("REPORT:", out)
for name, r in report["routes"].items():
    recs = r.get("records", [])
    ok = sum(1 for x in recs if x.get("status") == "ok")
    print(f"  {name}: {ok} ok / {len(recs)} attempts")
