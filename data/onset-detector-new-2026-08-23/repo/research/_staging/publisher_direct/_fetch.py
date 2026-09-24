#!/usr/bin/env python3
# B-FETCH-PUBLISHER-DIRECT — prefetch only, staging-only. No store/catalog/manifest touch.
import json, hashlib, time, os, urllib.request, urllib.error, ssl, datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
UA = "RMV2-publisher-direct-fetch/1 (research staging; verbatim mirror)"
CTX = ssl.create_default_context()

# (publisher, tier, url, relpath)  tier: publisher-direct for all here.
TARGETS = [
    # --- Federal Reserve G.17 (Board; DDP retiring) ---
    ("federal_reserve_g17", "publisher-direct",
     "https://www.federalreserve.gov/feeds/g17.xml", "feeds/g17.xml"),
    ("federal_reserve_g17", "publisher-direct",
     "https://www.federalreserve.gov/releases/g17/current/default.htm", "releases/g17/current/default.htm"),
    ("federal_reserve_g17", "publisher-direct",
     "https://www.federalreserve.gov/releases/g17/current/g17.pdf", "releases/g17/current/g17.pdf"),
    ("federal_reserve_g17", "publisher-direct",
     "https://www.federalreserve.gov/releases/g17/About.htm", "releases/g17/About.htm"),
    ("federal_reserve_g17", "publisher-direct",
     "https://www.federalreserve.gov/datadownload/Output.aspx?rel=G17&series=ip_totmfg&lastobs=&from=&to=&filetype=csv&label=include&layout=seriescolumn", "datadownload/g17_ip_totmfg.csv"),
    # --- DOL ETA-539 weekly claims (publisher-direct behind ICSA/IURSA) ---
    ("dol_eta539", "publisher-direct",
     "https://oui.doleta.gov/unemploy/csv/ar539.csv", "csv/ar539.csv"),
    ("dol_eta539", "publisher-direct",
     "https://oui.doleta.gov/unemploy/claims.asp", "claims.asp.html"),
    ("dol_eta539", "publisher-direct",
     "https://oui.doleta.gov/unemploy/DataDownload.asp", "DataDownload.asp.html"),
    ("dol_eta539", "publisher-direct",
     "https://oui.doleta.gov/unemploy/wkclaims/report.asp", "wkclaims/report.asp.html"),
    # --- Census New Residential Construction (HOUST/PERMIT) ---
    ("census_nrc", "publisher-direct",
     "https://www.census.gov/construction/nrc/pdf/newresconst.pdf", "pdf/newresconst.pdf"),
    ("census_nrc", "publisher-direct",
     "https://www.census.gov/construction/nrc/index.html", "index.html"),
    ("census_nrc", "publisher-direct",
     "https://www.census.gov/construction/nrc/xls/starts_cust.xlsx", "xls/starts_cust.xlsx"),
    ("census_nrc", "publisher-direct",
     "https://www.census.gov/construction/nrc/xls/permits_cust.xlsx", "xls/permits_cust.xlsx"),
    ("census_nrc", "publisher-direct",
     "https://www.census.gov/economic-indicators/calendar-listview.html", "release_calendar_listview.html"),
]

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    t0 = time.time()
    r = urllib.request.urlopen(req, timeout=45, context=CTX)
    body = r.read()
    return r.getcode(), dict(r.headers), body, round(time.time()-t0, 2)

def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

manifest = {"batch": "B-FETCH-PUBLISHER-DIRECT", "generated_utc": now(),
            "write_surface": "research/_staging/publisher_direct/ ONLY",
            "objects": [], "failures": [],
            "publisher_declared": {
                "federal_reserve_g17": "CLAIM (Board): G.17 releases Dec-1997 onward; FRASER carries G.17 back to Apr-1990; DDP being retired.",
                "dol_eta539": "CLAIM (DOL): ETA-539 state weekly claims; publisher-direct behind ICSA/IURSA (ALFRED vintage floors 2009-06/2009-09).",
                "census_nrc": "CLAIM (Census): New Residential Construction printed release IS the first release for HOUST/PERMIT."}}

for pub, tier, url, rel in TARGETS:
    dest = os.path.join(ROOT, pub, rel)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    try:
        code, hdrs, body, dt = fetch(url)
        with open(dest, "wb") as f:
            f.write(body)
        sha = hashlib.sha256(body).hexdigest()
        side = {"publisher": pub, "tier": tier, "url": url, "http_status": code,
                "last_modified": hdrs.get("Last-Modified"), "content_type": hdrs.get("Content-Type"),
                "bytes": len(body), "sha256": sha, "fetch_utc": now(), "fetch_secs": dt,
                "path": os.path.relpath(dest, ROOT)}
        with open(dest + ".sidecar.json", "w") as f:
            json.dump(side, f, indent=2)
        manifest["objects"].append(side)
        print(f"OK   {code} {len(body):>9}B {pub:24} {rel}")
    except urllib.error.HTTPError as e:
        fail = {"publisher": pub, "tier": tier, "url": url, "http_status": e.code,
                "reason": f"HTTPError {e.code} {e.reason}", "fetch_utc": now(), "path": os.path.relpath(dest, ROOT)}
        with open(dest + ".FAILED.json", "w") as f:
            json.dump(fail, f, indent=2)
        manifest["failures"].append(fail)
        print(f"FAIL {e.code} {pub:24} {rel} :: {e.reason}")
    except Exception as e:
        fail = {"publisher": pub, "tier": tier, "url": url, "http_status": None,
                "reason": f"{type(e).__name__}: {e}", "fetch_utc": now(), "path": os.path.relpath(dest, ROOT)}
        with open(dest + ".FAILED.json", "w") as f:
            json.dump(fail, f, indent=2)
        manifest["failures"].append(fail)
        print(f"FAIL  -- {pub:24} {rel} :: {type(e).__name__}: {e}")

manifest["counts"] = {"fetched": len(manifest["objects"]),
                      "failed": len(manifest["failures"]),
                      "total_bytes": sum(o["bytes"] for o in manifest["objects"])}
with open(os.path.join(ROOT, "FETCH_MANIFEST.v1.json"), "w") as f:
    json.dump(manifest, f, indent=2)
print("---")
print(json.dumps(manifest["counts"]))
