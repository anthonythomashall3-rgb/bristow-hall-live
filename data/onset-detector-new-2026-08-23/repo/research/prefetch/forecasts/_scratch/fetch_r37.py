#!/usr/bin/env python3
# CH-R37 forecast ROUTE REPAIR. Read-only vs store. Cache under forecasts/.
# Fixes CH-R35's 3 blocked routes (gdpnow/greenbook/cleveland) + FOMC SEP pre-2021.
# Resume-safe, throttled ~1 req/s, 2 tries, exact bytes, sha-manifest, skip-on-2-fail.
import os, re, sys, time, json, hashlib, urllib.request, urllib.error, datetime

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))  # forecasts/
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
# Philly-Fed soft-404 placeholder shas seen by CH-R35 (18396 xlsx / 18282 zip). Reject.
DECOY_BYTES = {18396, 18282}

def utc():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def sha(b): return hashlib.sha256(b).hexdigest()

def get(url, timeout=45):
    """Return (data_bytes, content_type, http_status_or_err). Raises nothing."""
    err = None
    for attempt in (1, 2):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read(), r.headers.get("Content-Type", ""), "ok"
        except urllib.error.HTTPError as e:
            err = f"HTTP {e.code}"
            if e.code in (404, 403, 410): break
        except Exception as e:
            err = str(e)[:140]
        time.sleep(1.0)
    return None, None, err

def looks_like_html(b):
    head = b[:512].lstrip().lower()
    return head.startswith(b"<!doctype html") or head.startswith(b"<html") or b"<title" in head

def save(outpath, data, url, ct, extra=None):
    os.makedirs(os.path.dirname(outpath), exist_ok=True)
    with open(outpath, "wb") as f:
        f.write(data)
    rec = {"url": url, "path": os.path.relpath(outpath, ROOT), "bytes": len(data),
           "sha256": sha(data), "fetch_utc": utc(), "content_type": ct, "status": "ok"}
    if extra: rec.update(extra)
    return rec

def fetch_to(outpath, url, reject_html=False, reject_decoy=False):
    if os.path.exists(outpath) and os.path.getsize(outpath) > 0:
        b = open(outpath, "rb").read()
        return {"url": url, "path": os.path.relpath(outpath, ROOT), "bytes": len(b),
                "sha256": sha(b), "status": "cached"}
    data, ct, st = get(url)
    if data is None:
        return {"url": url, "path": os.path.relpath(outpath, ROOT), "status": "FAIL", "error": st}
    flags = {}
    if reject_decoy and len(data) in DECOY_BYTES:
        return {"url": url, "bytes": len(data), "sha256": sha(data),
                "status": "DECOY", "note": "philly-fed soft-404 placeholder"}
    if reject_html and looks_like_html(data):
        return {"url": url, "bytes": len(data), "sha256": sha(data),
                "status": "HTML", "note": "expected binary, got HTML (JS-gated/challenge)"}
    return save(outpath, data, url, ct, flags)

RESULTS = {"batch": "CH-R37_FORECAST_ROUTE_REPAIR", "utc": utc(), "routes": {}}

def route(name):
    RESULTS["routes"][name] = {"records": [], "verdict": None, "notes": []}
    return RESULTS["routes"][name]

# ---------- 1. GDPNow ----------
def do_gdpnow():
    r = route("gdpnow")
    d = os.path.join(ROOT, "gdpnow")
    # keyless FRED public CSV (full history of the published nowcast series)
    r["records"].append(fetch_to(os.path.join(d, "GDPNOW.fredgraph.csv"),
        "https://fred.stlouisfed.org/graph/fredgraph.csv?id=GDPNOW"))
    # ALFRED all-observations current (latest vintage; full-vintage matrix needs API key)
    r["records"].append(fetch_to(os.path.join(d, "GDPNOW.alfredgraph.csv"),
        "https://alfred.stlouisfed.org/graph/alfredgraph.csv?id=GDPNOW"))
    # Atlanta Fed native tracking xlsx — ONE attempt each host, reject HTML challenge
    for i, u in enumerate([
        "https://www.atlantafed.org/-/media/documents/cqer/researchcq/gdpnow/GDPTrackingModelDataAndForecasts.xlsx",
        "https://www.atlantafed.org/cqer/research/gdpnow.aspx",
    ]):
        rec = fetch_to(os.path.join(d, f"atlanta_native_{i}.bin"), u, reject_html=(i == 0))
        r["records"].append(rec)
    ok = [x for x in r["records"] if x.get("status") in ("ok", "cached")]
    r["verdict"] = f"{len(ok)} file(s) cached; FRED:GDPNOW published series is the clean value route"
    r["notes"].append("full per-vintage GDPNOW matrix requires FRED/ALFRED API key (not offline-keyless)")

# ---------- 2. Greenbook / Tealbook ----------
def do_greenbook():
    r = route("greenbook")
    d = os.path.join(ROOT, "greenbook")
    page_url = "https://www.philadelphiafed.org/surveys-and-data/real-time-data-research/greenbook-data-sets"
    page, ct, st = get(page_url)
    if page is None:
        r["verdict"] = f"landing page unreachable ({st})"; return
    save(os.path.join(d, "_greenbook_landing.html"), page, page_url, ct)
    html = page.decode("utf-8", "replace")
    # find hrefs pointing at real download assets
    hrefs = re.findall(r'href=["\']([^"\']+\.(?:xlsx|xls|zip|csv))["\']', html, re.I)
    hrefs = sorted(set(hrefs))
    r["notes"].append(f"{len(hrefs)} static asset href(s) in page HTML")
    for h in hrefs[:60]:
        url = h if h.startswith("http") else ("https://www.philadelphiafed.org" + (h if h.startswith("/") else "/" + h))
        base = re.sub(r'[^A-Za-z0-9._-]', '_', h.split("/")[-1])
        r["records"].append(fetch_to(os.path.join(d, base), url, reject_decoy=True))
    got = [x for x in r["records"] if x.get("status") in ("ok", "cached")]
    if not hrefs:
        r["verdict"] = "NEEDS-BROWSER-LANE: zero static download hrefs (JS-injected links)"
    else:
        r["verdict"] = f"{len(got)}/{len(hrefs)} static hrefs resolved to real bytes"

# ---------- 3. Cleveland inflation nowcast ----------
def do_cleveland():
    r = route("cleveland_nowcast")
    d = os.path.join(ROOT, "cleveland_nowcast")
    page_url = "https://www.clevelandfed.org/indicators-and-data/inflation-nowcasting"
    page, ct, st = get(page_url)
    if page is None:
        r["verdict"] = f"landing page unreachable ({st})"; return
    save(os.path.join(d, "_cleveland_landing.html"), page, page_url, ct)
    html = page.decode("utf-8", "replace")
    # documented endpoint patterns: /-/ media assets, /data/, download endpoints, .csv/.xlsx
    cand = set(re.findall(r'["\']([^"\']*(?:download|/data/|nowcast[^"\']*\.(?:csv|xlsx|json))[^"\']*)["\']', html, re.I))
    cand |= set(re.findall(r'href=["\']([^"\']+\.(?:csv|xlsx|json))["\']', html, re.I))
    cand = sorted(c for c in cand if not c.lower().endswith((".css", ".js")))
    r["notes"].append(f"{len(cand)} candidate data endpoint(s) in page HTML")
    for h in list(cand)[:30]:
        url = h if h.startswith("http") else ("https://www.clevelandfed.org" + (h if h.startswith("/") else "/" + h))
        base = re.sub(r'[^A-Za-z0-9._-]', '_', h.split("/")[-1])[:80] or "cleveland_asset"
        r["records"].append(fetch_to(os.path.join(d, base), url, reject_html=True))
    got = [x for x in r["records"] if x.get("status") in ("ok", "cached")]
    if got:
        r["verdict"] = f"{len(got)} data asset(s) cached from page HTML endpoints"
    else:
        r["verdict"] = "NEEDS-BROWSER-LANE: data behind JS /download endpoint, no static asset resolved"

# ---------- 4. FOMC SEP pre-2021 ----------
def do_fomc_sep():
    r = route("fomc_sep")
    d = os.path.join(ROOT, "fomc_sep", "pre2021")
    years = list(range(2007, 2021))  # SEP began 2007
    total_pdfs = 0
    for y in years:
        yr_url = f"https://www.federalreserve.gov/monetarypolicy/fomchistorical{y}.htm"
        page, ct, st = get(yr_url)
        if page is None:
            r["notes"].append(f"{y}: year page FAIL {st}"); time.sleep(0.5); continue
        html = page.decode("utf-8", "replace")
        # SEP artifacts: projection tables/materials pdfs. Match hrefs whose text/name signals SEP.
        pdfs = re.findall(r'href=["\']([^"\']+\.pdf)["\']', html, re.I)
        sep = [p for p in set(pdfs) if re.search(r'(proj|sep|SEP|EconProj|Tealbook|proj_table)', p, re.I)]
        r["notes"].append(f"{y}: {len(pdfs)} pdf href(s), {len(sep)} SEP-tagged")
        for p in sorted(sep):
            url = p if p.startswith("http") else ("https://www.federalreserve.gov" + (p if p.startswith("/") else "/" + p))
            base = f"{y}_" + re.sub(r'[^A-Za-z0-9._-]', '_', p.split("/")[-1])
            rec = fetch_to(os.path.join(d, base), url)
            if rec.get("status") in ("ok", "cached"): total_pdfs += 1
            r["records"].append(rec)
        time.sleep(0.6)
    r["verdict"] = f"{total_pdfs} SEP-class PDF(s) cached across 2007-2020 year pages"

def main():
    only = sys.argv[1:] if len(sys.argv) > 1 else ["gdpnow", "greenbook", "cleveland", "fomc"]
    if "gdpnow" in only: do_gdpnow()
    if "greenbook" in only: do_greenbook()
    if "cleveland" in only: do_cleveland()
    if "fomc" in only: do_fomc_sep()
    out = os.path.join(ROOT, "_scratch", "R37_REPORT.json")
    with open(out, "w") as f:
        json.dump(RESULTS, f, indent=2)
    # compact console summary only
    for name, r in RESULTS["routes"].items():
        n_ok = len([x for x in r["records"] if x.get("status") in ("ok", "cached")])
        n_bad = len([x for x in r["records"] if x.get("status") not in ("ok", "cached")])
        print(f"{name}: ok/cached={n_ok} other={n_bad} :: {r['verdict']}")
    print("report ->", os.path.relpath(out, ROOT))

if __name__ == "__main__":
    main()
