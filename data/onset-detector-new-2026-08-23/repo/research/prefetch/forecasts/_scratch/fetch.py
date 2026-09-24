#!/usr/bin/env python3
# CH-R35 forecast-archive prefetch. Resume-safe, throttled ~1 req/s, 2 tries, exact bytes.
import os, sys, time, json, hashlib, urllib.request, urllib.error, datetime

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))  # forecasts/
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"

def utc():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def fetch(url, outpath):
    """Return dict record. Resume-safe: skip if already present & nonzero."""
    if os.path.exists(outpath) and os.path.getsize(outpath) > 0:
        b = open(outpath, "rb").read()
        return {"url": url, "path": os.path.relpath(outpath, ROOT), "bytes": len(b),
                "sha256": hashlib.sha256(b).hexdigest(), "fetch_utc": "cached", "status": "cached"}
    err = None
    for attempt in (1, 2):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=45) as r:
                data = r.read()
            os.makedirs(os.path.dirname(outpath), exist_ok=True)
            with open(outpath, "wb") as f:
                f.write(data)
            return {"url": url, "path": os.path.relpath(outpath, ROOT), "bytes": len(data),
                    "sha256": hashlib.sha256(data).hexdigest(), "fetch_utc": utc(),
                    "content_type": r.headers.get("Content-Type", ""), "status": "ok"}
        except urllib.error.HTTPError as e:
            err = f"HTTP {e.code}";
            if e.code in (404, 403): break  # don't retry hard misses
        except Exception as e:
            err = str(e)[:120]
        time.sleep(1.0)
    return {"url": url, "path": os.path.relpath(outpath, ROOT), "status": "FAIL", "error": err}

def run(source, items):
    outdir = os.path.join(ROOT, source)
    recs = []
    for name, url in items:
        rec = fetch(url, os.path.join(outdir, name))
        recs.append(rec)
        tag = rec.get("status")
        print(f"  [{source}] {tag:6} {name} {rec.get('bytes','')}", flush=True)
        if tag not in ("cached",):
            time.sleep(1.0)
    os.makedirs(outdir, exist_ok=True)
    with open(os.path.join(outdir, "MANIFEST.sha256.json"), "w") as f:
        json.dump({"source": source, "generated_utc": utc(), "files": recs}, f, indent=2)
    ok = sum(1 for r in recs if r["status"] in ("ok", "cached"))
    tb = sum(r.get("bytes", 0) for r in recs if r["status"] in ("ok", "cached"))
    print(f"== {source}: {ok}/{len(recs)} ok, {tb} bytes ==", flush=True)
    return recs

SPF_BASE = "https://www.philadelphiafed.org/-/media/frbp/assets/surveys-and-data/survey-of-professional-forecasters"
DF = SPF_BASE + "/data-files/files"
SPF_VARS = ["NGDP","PGDP","RGDP","RCONSUM","RNRESIN","RRESINV","RCBI","REXPORT","RIMPORT",
            "RFEDGOV","RSLGOV","HOUSING","UNEMP","EMP","INDPROD","TBILL","TBOND","AAA","BAA",
            "CPI","CORECPI","PCE","COREPCE","CPROF"]

def spf_items():
    items = []
    for v in SPF_VARS:
        lv = v.lower()
        for agg in ("mean","median"):
            for kind in ("level","growth"):
                items.append((f"{agg}_{lv}_{kind}.xlsx", f"{DF}/{agg}_{lv}_{kind}.xlsx"))
        items.append((f"individual_{lv}.xlsx", f"{DF}/individual_{lv}.xlsx"))
    # master micro archive + dispersion + error stats bundles
    items.append(("spfmicrodata.xlsx", SPF_BASE + "/historical-data/spfmicrodata.xlsx"))
    items.append(("mean_dispersion.xlsx", SPF_BASE + "/data-files/files/dispersion.xlsx"))
    return items

ANX = SPF_BASE + "/anxious-index"
def anxious_items():
    return [
        ("anxious_index_chart.xlsx", ANX + "/anxious_index_chart.xlsx"),
        ("mean_recession_prob.xlsx", DF + "/mean_recession_prob.xlsx"),
        ("median_recession_prob.xlsx", DF + "/median_recession_prob.xlsx"),
        ("individual_recess.xlsx", DF + "/individual_recess.xlsx"),
    ]

LIV = "https://www.philadelphiafed.org/-/media/frbp/assets/surveys-and-data/livingston-survey"
def livingston_items():
    items = [("livingston-release-dates.xlsx", LIV + "/livingston-release-dates.xlsx"),
             ("livingston_documentation.pdf", LIV + "/livingston-documentation.pdf")]
    for v in ["CPI","IPT","IPM","IPTM","LFPR","NFP","PGDP","RGDP","UGDP","UNEMP","AAA","CBI",
              "CPBP","DUR","GBP","GDP","IP","NHS","PPI","RCBI"]:
        items.append((f"{v.lower()}.xlsx", LIV + f"/{v.lower()}.xlsx"))
    return items

GB = SPF_BASE.replace("survey-of-professional-forecasters", "greenbook-data-sets")
def greenbook_items():
    # Greenbook/Tealbook release-based ROW/COL data-set spreadsheets
    items = [("greenbook_documentation.pdf", GB + "/greenbook-documentation.pdf")]
    for name in ["gbweb_row_format.xlsx","gbweb_column_format.xlsx",
                 "greenbook-reference-set-row.xlsx","greenbook-reference-set-column.xlsx",
                 "Gbweb_Row_Format.xlsx","Gbweb_Col_Format.xlsx"]:
        items.append((name, GB + "/" + name))
    return items

def nyfed_items():
    base = "https://www.newyorkfed.org/medialibrary/media/research/policy/nowcast"
    return [("nyfed_staff_nowcast_2002-present.xlsx",
             base + "/new-york-fed-staff-nowcast_data_2002-present.xlsx"),
            ("nyfed_nowcast_history.xlsx", base + "/nowcast_data.xlsx")]

def cleveland_items():
    base = "https://www.clevelandfed.org/-/media/files/indicators-and-data/inflation-nowcasting"
    return [("cleveland_inflation_nowcast.xlsx", base + "/inflation-nowcasting.xlsx"),
            ("cleveland_nowcast_data.csv", "https://www.clevelandfed.org/indicators-and-data/inflation-nowcasting/nowcast-data.csv")]

def sep_items():
    # FOMC SEP projection-materials landing already page-only; grab the tabulated history csv if present
    return [("fomc_sep_page.html", "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm")]

if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    jobs = {
        "spf": ("spf", spf_items()),
        "anxious": ("anxious_index", anxious_items()),
        "livingston": ("livingston", livingston_items()),
        "greenbook": ("greenbook", greenbook_items()),
        "nyfed": ("nyfed_nowcast", nyfed_items()),
        "cleveland": ("cleveland_nowcast", cleveland_items()),
        "sep": ("fomc_sep", sep_items()),
    }
    order = list(jobs) if which == "all" else [which]
    for k in order:
        src, items = jobs[k]
        run(src, items)
