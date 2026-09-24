#!/usr/bin/env python3
"""CH-R24 RTDSM pre-fetch. Scrapes 115 var pages for tokenized xlsx links, downloads
vintage-history files to research/prefetch/rtdsm/<var>/. Manifest JSONL. Resume-safe.
ZERO store writes. Preserves exact bytes (no unzip/convert)."""
import os, re, sys, time, json, hashlib, html, urllib.request, urllib.error

ROOT = os.path.dirname(os.path.abspath(__file__))
PF = os.path.abspath(os.path.join(ROOT, ".."))          # research/prefetch
RTDSM = os.path.join(PF, "rtdsm")
MAN = os.path.join(RTDSM, "_manifest.jsonl")
BASE = "https://www.philadelphiafed.org"
IDX = BASE + "/surveys-and-data/real-time-data-research/real-time-data-set-full-time-series-history"
UA = "Mozilla/5.0 RMV2-research"
# member-mapped bases first (preflight §1): RUC EMPLOY IPT/IPM CUT/CUM HSTARTS + CPI M1 M2
PRIORITY = ["ruc","employ","ipt","ipm","cut","cum","hstarts","cpi","m1","m2"]

def get(url, tries=2, timeout=45):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.getcode(), r.read()
        except Exception as e:
            last = e
            code = getattr(e, "code", None)
            if code and 400 <= code < 500:      # client error: don't retry
                return code, b""
            time.sleep(2)
    return (getattr(last, "code", 0) or 0), b""

def load_done():
    seen = {}
    if os.path.exists(MAN):
        for ln in open(MAN):
            try:
                r = json.loads(ln)
                if r.get("sha256"):
                    seen[r["path"]] = r["sha256"]
            except Exception:
                pass
    return seen

def manw(rec):
    with open(MAN, "a") as f:
        f.write(json.dumps(rec) + "\n")

def main():
    idx_html = open(os.path.join(ROOT, "rtdsm_index.html"), encoding="utf-8", errors="replace").read()
    slugs = []
    for m in re.finditer(r'real-time-data-research/([a-z0-9_-]+)', idx_html):
        s = m.group(1)
        if s not in slugs and s != "real-time-data-set-full-time-series-history":
            slugs.append(s)
    # non-vintage products to skip (surveys, not xlsx vintage matrices)
    skip = {"livingston-survey","survey-of-professional-forecasters","aruoba-diebold-scotti-business-conditions-index",
            "greenbook-data-sets","partisan-conflict-index"}
    slugs = [s for s in slugs if s not in skip]
    ordered = [s for s in PRIORITY if s in slugs] + [s for s in slugs if s not in PRIORITY]
    print(f"vars_to_scan={len(ordered)} priority={[s for s in PRIORITY if s in slugs]}", flush=True)

    seen = load_done()
    n_files=n_skip=n_fail=0; total_bytes=0; pages_ok=0; pages_novintage=0; fails=[]
    for i, var in enumerate(ordered):
        purl = f"{BASE}/surveys-and-data/real-time-data-research/{var}"
        code, body = get(purl)
        time.sleep(1.0)
        if code != 200 or not body:
            fails.append({"kind":"page","var":var,"url":purl,"http":code}); n_fail+=1
            print(f"[{i+1}/{len(ordered)}] {var} PAGE_FAIL http={code}", flush=True); continue
        pages_ok+=1
        page = body.decode("utf-8", errors="replace")
        links = set()
        for m in re.finditer(r'/-/media/[^"\'> ]*\.xlsx[^"\'> ]*', page):
            links.add(html.unescape(m.group(0)))
        if not links:
            pages_novintage+=1
            print(f"[{i+1}/{len(ordered)}] {var} no_xlsx", flush=True); continue
        vdir = os.path.join(RTDSM, var); os.makedirs(vdir, exist_ok=True)
        for link in sorted(links):
            fname = link.split("?")[0].split("/")[-1]
            dpath = os.path.join(vdir, fname)
            rel = os.path.relpath(dpath, PF)
            furl = BASE + link
            if os.path.exists(dpath) and os.path.getsize(dpath) > 0 and rel in seen:
                n_skip+=1; continue
            fc, fb = get(furl); time.sleep(1.0)
            if fc != 200 or not fb:
                fails.append({"kind":"file","var":var,"file":fname,"url":furl,"http":fc}); n_fail+=1
                print(f"    {var}/{fname} FILE_FAIL http={fc}", flush=True); continue
            with open(dpath, "wb") as f: f.write(fb)
            sha = hashlib.sha256(fb).hexdigest()
            manw({"var":var,"file":fname,"path":rel,"url":furl,
                  "fetch_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                  "sha256":sha,"bytes":len(fb),"http":fc})
            n_files+=1; total_bytes+=len(fb)
        print(f"[{i+1}/{len(ordered)}] {var} files={len(links)}", flush=True)

    summ = {"target":"rtdsm","vars_scanned":len(ordered),"pages_ok":pages_ok,
            "pages_no_vintage":pages_novintage,"files_downloaded":n_files,"files_skipped_cached":n_skip,
            "failures":n_fail,"total_bytes":total_bytes,"fail_list":fails}
    json.dump(summ, open(os.path.join(PF,"_scratch","rtdsm_summary.json"),"w"), indent=1)
    print("SUMMARY " + json.dumps({k:v for k,v in summ.items() if k!="fail_list"}), flush=True)

if __name__ == "__main__":
    main()
