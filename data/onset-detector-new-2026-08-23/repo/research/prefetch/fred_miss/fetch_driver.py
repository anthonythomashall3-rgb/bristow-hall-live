#!/usr/bin/env python3
"""CH-R29 MISS-backlog prefetch. Read-only vs store. Output -> this dir only.
Resume-safe (skip if target file already present + non-empty), throttle ~1 req/s,
2 tries then record-and-move-on. Sha-manifest per fetched file."""
import csv, os, sys, time, json, hashlib, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
SURVEY = os.path.join(ROOT, "research", "hf_universe_survey_v1.csv")
MANIFEST = os.path.join(HERE, "manifest.jsonl")
LOG = os.path.join(HERE, "fetch.log")

def load_key(name):
    for line in open(os.path.join(ROOT, "live_data", "config", "local.env")):
        line = line.strip()
        if line.startswith(name + "="):
            return line.split("=", 1)[1].strip()
    return None

FRED_KEY = load_key("FRED_API_KEY")
EIA_KEY = load_key("EIA_API_KEY")

def utcnow():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def redact(s):
    import re
    return re.sub(r"api_key=[0-9a-fA-F]+", "api_key=<KEY>", s)

def logline(msg):
    with open(LOG, "a") as f:
        f.write(f"{utcnow()} {redact(msg)}\n")

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(65536), b""):
            h.update(b)
    return h.hexdigest()

def record(entry):
    with open(MANIFEST, "a") as f:
        f.write(json.dumps(entry) + "\n")

def fetch(url, dest, tries=2):
    """Return (ok, http, bytes). Resume-safe: skip if dest exists non-empty."""
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        return ("cached", 0, os.path.getsize(dest))
    req = urllib.request.Request(url, headers={"User-Agent": "RMV2-research/1.0"})
    for attempt in range(1, tries + 1):
        try:
            with urllib.request.urlopen(req, timeout=45) as r:
                data = r.read()
                code = r.getcode()
            if not data:
                logline(f"EMPTY {url} attempt{attempt}")
                time.sleep(1.0); continue
            with open(dest, "wb") as f:
                f.write(data)
            return ("ok", code, len(data))
        except urllib.error.HTTPError as e:
            logline(f"HTTP{e.code} {url} attempt{attempt}")
            if e.code in (400, 401, 403, 404):
                return ("http_err", e.code, 0)
            time.sleep(1.0)
        except Exception as e:
            logline(f"ERR {type(e).__name__} {url} attempt{attempt}")
            time.sleep(1.0)
    return ("fail", 0, 0)

def do_fred(cand, fid, note):
    # values via FRED API observations (reliable host; fredgraph host times out from urllib)
    csv_url = (f"https://api.stlouisfed.org/fred/series/observations?series_id={fid}"
               f"&api_key={FRED_KEY}&file_type=json")
    csv_dest = os.path.join(HERE, f"{fid}.obs.json")
    st, code, nb = fetch(csv_url, csv_dest)
    ent = {"candidate": cand, "fred_id": fid, "kind": "fred_current_obs",
           "url": csv_url.replace(FRED_KEY, "<KEY>"), "fetch_utc": utcnow(),
           "status": st, "http": code, "bytes": nb, "note": note}
    if st in ("ok", "cached"):
        ent["sha256"] = sha256(csv_dest)
    record(ent)
    if st == "ok":
        time.sleep(1.0)
    # metadata via FRED API (has key)
    if FRED_KEY:
        meta_url = (f"https://api.stlouisfed.org/fred/series?series_id={fid}"
                    f"&api_key={FRED_KEY}&file_type=json")
        meta_dest = os.path.join(HERE, f"{fid}.meta.json")
        st2, code2, nb2 = fetch(meta_url, meta_dest)
        ment = {"candidate": cand, "fred_id": fid, "kind": "fred_series_meta",
                "url": meta_url.replace(FRED_KEY, "<KEY>"), "fetch_utc": utcnow(),
                "status": st2, "http": code2, "bytes": nb2}
        if st2 in ("ok", "cached"):
            ment["sha256"] = sha256(meta_dest)
        record(ment)
        if st2 == "ok":
            time.sleep(1.0)
    return st

def do_url(cand, url, fname, kind, note):
    dest = os.path.join(HERE, fname)
    st, code, nb = fetch(url, dest)
    ent = {"candidate": cand, "kind": kind, "url": url, "fetch_utc": utcnow(),
           "status": st, "http": code, "bytes": nb, "note": note}
    if st in ("ok", "cached"):
        ent["sha256"] = sha256(dest)
    record(ent)
    if st == "ok":
        time.sleep(1.0)
    return st

def do_skip(cand, reason, rights):
    record({"candidate": cand, "kind": "skip", "reason": reason,
            "rights": rights, "fetch_utc": utcnow()})

def do_needs_route(cand, reason):
    record({"candidate": cand, "kind": "needs_route", "reason": reason,
            "fetch_utc": utcnow()})

# ---- explicit non-FRED plan (unambiguous free direct-file URLs only) ----
# WALCL is the FRED mirror named in the H.4.1 route.
EXTRA_FRED = {
    "Fed H.4.1 weekly 1914 (FRASER)": ("WALCL", "H.4.1 FRED mirror; FRASER scans need vintage lane later"),
}
URL_PLAN = {
    "S&P composite Cowles/Shiller 1871": (
        "http://www.econ.yale.edu/~shiller/data/ie_data.xls",
        "shiller_ie_data.xls", "shiller_xls", "public_academic; monthly; never-revised"),
    "ADS business conditions index": (
        "https://www.philadelphiafed.org/-/media/frbp/assets/surveys-and-data/ads/ads_index_most_current_vintage.xlsx",
        "phillyfed_ads.xlsx", "ads_xlsx", "model_output(revised); needs vintage lane later"),
    "EIA gasoline demand": (
        f"https://api.eia.gov/v2/petroleum/cons/wpsup/data/?api_key={EIA_KEY or 'NOKEY'}"
        "&frequency=weekly&data[0]=value&facets[series][]=WGFUPUS2"
        "&sort[0][column]=period&sort[0][direction]=asc",
        "eia_wgfupus2.json", "eia_v2_json", "revised weekly; needs vintage lane later"),
}
NEEDS_ROUTE = {
    "EIA electricity output (weekly)": "EIA v2 series path for weekly electricity output not pinned by CH-R26; NEEDS-ROUTE",
    "Baker Hughes rig count": "BKR site xlsx URL rotates per-release; NEEDS-ROUTE",
    "TSA checkpoint throughput": "TSA.gov HTML table, no clean file endpoint; NEEDS-ROUTE (needs scraper)",
    "WARN layoff notices": "50 state portals, mixed formats; NEEDS-ROUTE (per-state parsers)",
    "Call money rate 1890s (NBER)": "route says NBER Macrohistory/FRED but no FRED id pinned; NEEDS-ROUTE",
    "Dept store sales 1919 (NBER)": "NBER/FRED + FRASER SCB, no single FRED id pinned; NEEDS-ROUTE",
    "Money stock Friedman-Schwartz 1907": "NBER Macrohistory, no FRED id pinned; NEEDS-ROUTE",
    "Unemployment Lebergott/Weir 1890": "academic annual tables, no clean file endpoint; NEEDS-ROUTE",
}

def is_rights_blocked(rights):
    r = rights.upper()
    return any(t in r for t in ("PROPRIETARY", "LICENSED", "MIXED_"))

def main():
    rows = list(csv.DictReader(open(SURVEY)))
    miss = [r for r in rows if r.get("held", "").strip().upper() == "MISS"]
    counts = {"fred": 0, "url": 0, "skip": 0, "needs_route": 0}
    for r in miss:
        cand = r["candidate"].strip()
        fid = r["fred_id"].strip()
        rights = r["rights_rung"].strip()
        if fid:
            do_fred(cand, fid, r["revision_class"]); counts["fred"] += 1
        elif cand in EXTRA_FRED:
            xfid, note = EXTRA_FRED[cand]
            do_fred(cand, xfid, note); counts["fred"] += 1
        elif is_rights_blocked(rights):
            do_skip(cand, "rights-blocked (proprietary/licensed)", rights); counts["skip"] += 1
        elif cand in URL_PLAN:
            url, fname, kind, note = URL_PLAN[cand]
            do_url(cand, url, fname, kind, note); counts["url"] += 1
        elif cand in NEEDS_ROUTE:
            do_needs_route(cand, NEEDS_ROUTE[cand]); counts["needs_route"] += 1
        else:
            do_needs_route(cand, f"unclassified route={r['route']!r} rights={rights}")
            counts["needs_route"] += 1
    logline(f"DONE counts={counts}")
    print(json.dumps(counts))

if __name__ == "__main__":
    # fresh manifest each full run (resume via cached files, not manifest)
    open(MANIFEST, "w").close()
    open(LOG, "w").close()
    main()
